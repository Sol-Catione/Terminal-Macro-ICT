from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Iterable
from zoneinfo import ZoneInfo

from oanda_candles import Candle, iter_candles


@dataclass(frozen=True)
class BuildResult:
    rows: list[dict]
    notes: list[str]


def _atr14_by_date(dates: list[str], high: list[float], low: list[float], close: list[float]) -> dict[str, float]:
    """
    ATR14 (Wilder) computed on local-day OHLC arrays.
    Returns mapping date -> atr14 (only once enough history exists).
    """
    if not dates:
        return {}
    tr: list[float] = []
    prev_close = None
    for h, l, c in zip(high, low, close, strict=True):
        if prev_close is None:
            tr.append(h - l)
        else:
            tr.append(max(h - l, abs(h - prev_close), abs(l - prev_close)))
        prev_close = c

    n = 14
    if len(tr) < n:
        return {}
    atr: list[float | None] = [None] * len(tr)
    first = mean(tr[:n])
    atr[n - 1] = first
    for i in range(n, len(tr)):
        atr[i] = (atr[i - 1] * (n - 1) + tr[i]) / n  # Wilder smoothing

    out: dict[str, float] = {}
    for d, a in zip(dates, atr, strict=True):
        if a is not None:
            out[d] = float(a)
    return out


def build_xau_asia_open_daily_from_oanda(
    *,
    api_key: str,
    env: str,
    years: int = 3,
    instrument: str = "XAU_USD",
    granularity: str = "M5",
    # Anchor mode:
    # - "utc": fixed UTC time-of-day (recommended for pattern comparability, no DST jumps)
    # - "local": fixed local time-of-day in tz_name (may shift in UTC during DST)
    anchor_mode: str = "utc",
    anchor_time: tuple[int, int] = (0, 0),
    tz_name: str = "Europe/Lisbon",
    now_utc: datetime | None = None,
    progress_cb: callable | None = None,
) -> BuildResult:
    """
    Downloads XAU_USD 5m candles, computes for each local date:
    - open at anchor_time (UTC or local)
    - H1/H3 window metrics after 02:00
    - ATR14 per day (computed from day OHLC built from the same 5m candles)
    """
    notes: list[str] = []
    anchor_mode = (anchor_mode or "").strip().lower()
    tz = ZoneInfo(tz_name) if anchor_mode == "local" else None
    now_utc = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start_utc = (now_utc - timedelta(days=365 * int(years) + 30)).astimezone(timezone.utc)

    candles: list[Candle] = []
    for idx, c in enumerate(
        iter_candles(
            api_key=api_key,
            env=env,
            instrument=instrument,
            granularity=granularity,
            start_utc=start_utc,
            end_utc=now_utc,
        ),
        start=1,
    ):
        candles.append(c)
        if progress_cb and idx % 2000 == 0:
            progress_cb({"stage": "download", "candles": idx})

    if not candles:
        return BuildResult(rows=[], notes=["OANDA: nenhum candle retornado. Verifique chave e simbolo."])

    # Build day OHLC for ATR (UTC by default; local if anchor_mode == "local").
    dates: list[str] = []
    day_high: list[float] = []
    day_low: list[float] = []
    day_close: list[float] = []

    cur_date = None
    cur_h = cur_l = cur_c = None
    for c in candles:
        if anchor_mode == "local":
            d = c.time_utc.astimezone(tz).date().isoformat()
        else:
            d = c.time_utc.date().isoformat()
        if cur_date is None:
            cur_date = d
            cur_h, cur_l, cur_c = c.h, c.l, c.c
            continue
        if d != cur_date:
            dates.append(cur_date)
            day_high.append(float(cur_h))
            day_low.append(float(cur_l))
            day_close.append(float(cur_c))
            cur_date = d
            cur_h, cur_l, cur_c = c.h, c.l, c.c
        else:
            cur_h = max(cur_h, c.h)
            cur_l = min(cur_l, c.l)
            cur_c = c.c
    if cur_date is not None:
        dates.append(cur_date)
        day_high.append(float(cur_h))
        day_low.append(float(cur_l))
        day_close.append(float(cur_c))

    atr14 = _atr14_by_date(dates, day_high, day_low, day_close)
    if not atr14:
        notes.append("ATR14: historico insuficiente para calcular (precisa de >= 14 dias).")

    # Find anchor candles.
    target_h, target_m = anchor_time
    open_indices: list[tuple[str, int, datetime]] = []  # (trade_date, index, open_ts_utc)
    seen_date: set[str] = set()
    for i, c in enumerate(candles):
        if anchor_mode == "local":
            lt = c.time_utc.astimezone(tz)
            match = lt.hour == int(target_h) and lt.minute == int(target_m)
            trade_date = lt.date().isoformat()
        else:
            match = c.time_utc.hour == int(target_h) and c.time_utc.minute == int(target_m)
            trade_date = c.time_utc.date().isoformat()

        if match:
            if trade_date in seen_date:
                # DST fallback can create two local occurrences; keep the first by skipping later ones.
                continue
            seen_date.add(trade_date)
            open_indices.append((trade_date, i, c.time_utc))

    if not open_indices:
        basis = f"{tz_name}" if anchor_mode == "local" else "UTC"
        return BuildResult(
            rows=[],
            notes=[f"Nao encontrei candles exatamente as {target_h:02d}:{target_m:02d} ({basis}). Verifique granularity."],
        )

    rows: list[dict] = []
    for n, (trade_date, i, ts_utc) in enumerate(open_indices, start=1):
        if progress_cb and n % 50 == 0:
            progress_cb({"stage": "build", "days": n, "total_days": len(open_indices)})

        # Ensure enough candles for H1 (12) and H3 (36) in M5.
        h1_n = 12
        h3_n = 36
        if i + h1_n - 1 >= len(candles):
            continue
        if i + h3_n - 1 >= len(candles):
            continue

        window_h1 = candles[i : i + h1_n]
        window_h3 = candles[i : i + h3_n]

        rows.append(
            {
                "trade_date": trade_date,
                "open_ts_utc": ts_utc.isoformat().replace("+00:00", "Z"),
                "open": float(candles[i].o),
                "h1_high": float(max(x.h for x in window_h1)),
                "h1_low": float(min(x.l for x in window_h1)),
                "h1_close": float(window_h1[-1].c),
                "h3_high": float(max(x.h for x in window_h3)),
                "h3_low": float(min(x.l for x in window_h3)),
                "h3_close": float(window_h3[-1].c),
                "atr14": float(atr14[trade_date]) if trade_date in atr14 else None,
                "source": f"oanda:{instrument}:{granularity}:{anchor_mode}:{tz_name}:{target_h:02d}{target_m:02d}",
            }
        )

    if len(rows) < 300:
        notes.append("Poucos dias gerados; valide se o periodo baixado cobre 3 anos completos.")

    return BuildResult(rows=rows, notes=notes)
