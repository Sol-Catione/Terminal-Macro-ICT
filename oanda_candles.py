from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterator


@dataclass(frozen=True)
class Candle:
    time_utc: datetime
    o: float
    h: float
    l: float
    c: float


def _parse_oanda_time(s: str) -> datetime:
    # Example: 2024-01-01T00:00:00.000000000Z (nanoseconds)
    v = (s or "").strip()
    if not v:
        raise ValueError("Empty time")
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    if "." in v:
        head, tail = v.split(".", 1)
        # tail: "000000000+00:00" or "000000000"
        if "+" in tail:
            frac, tz = tail.split("+", 1)
            tz = "+" + tz
        elif "-" in tail:
            # timezone with minus
            frac, tz = tail.split("-", 1)
            tz = "-" + tz
        else:
            frac, tz = tail, ""
        frac6 = (frac + "000000")[:6]
        v = f"{head}.{frac6}{tz}"
    dt = datetime.fromisoformat(v)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def oanda_base_url(env: str) -> str:
    e = (env or "").strip().lower()
    if e in ("live", "fxtrade", "trade"):
        return "https://api-fxtrade.oanda.com"
    return "https://api-fxpractice.oanda.com"


def iter_candles(
    *,
    api_key: str,
    instrument: str,
    granularity: str,
    start_utc: datetime,
    end_utc: datetime,
    env: str = "practice",
    price: str = "M",
    max_per_request: int = 5000,
    timeout_s: int = 20,
) -> Iterator[Candle]:
    """
    Fetch candles from OANDA official REST API.
    Uses pagination with `includeFirst=false` to avoid duplicates.
    """
    import requests

    base = oanda_base_url(env)
    url = f"{base}/v3/instruments/{instrument}/candles"
    headers = {"Authorization": f"Bearer {api_key}"}

    cursor = start_utc.astimezone(timezone.utc)
    include_first = True
    end_utc = end_utc.astimezone(timezone.utc)

    while cursor < end_utc:
        params = {
            "from": _to_iso(cursor),
            "to": _to_iso(end_utc),
            "granularity": granularity,
            "price": price,
            "count": int(max_per_request),
            "includeFirst": "true" if include_first else "false",
        }
        resp = requests.get(url, headers=headers, params=params, timeout=int(timeout_s))
        resp.raise_for_status()
        data = resp.json()
        candles = data.get("candles") or []
        if not candles:
            return

        last_time = None
        for c in candles:
            if not c.get("complete", True):
                continue
            t = _parse_oanda_time(c["time"])
            m = c.get("mid") or {}
            yield Candle(
                time_utc=t,
                o=float(m["o"]),
                h=float(m["h"]),
                l=float(m["l"]),
                c=float(m["c"]),
            )
            last_time = t

        if last_time is None:
            return

        # Advance cursor a tiny amount to be safe even if includeFirst gets ignored.
        cursor = last_time + timedelta(microseconds=1)
        include_first = False


def test_oanda_market_data_access(
    *,
    api_key: str,
    instrument: str = "XAU_USD",
    env: str = "practice",
    timeout_s: int = 15,
) -> str:
    """
    Lightweight health check: fetch 1 candle.
    Returns a short human-readable status string.
    """
    import requests

    base = oanda_base_url(env)
    url = f"{base}/v3/instruments/{instrument}/candles"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"count": 1, "granularity": "M5", "price": "M"}

    resp = requests.get(url, headers=headers, params=params, timeout=int(timeout_s))
    if resp.status_code == 401:
        return "401 Unauthorized: token invalido/nao aceito para este ambiente."
    if resp.status_code == 403:
        return "403 Forbidden: token sem permissao para este recurso/conta."
    if resp.status_code >= 400:
        return f"{resp.status_code}: {resp.text[:200]}"
    data = resp.json()
    candles = data.get("candles") or []
    if not candles:
        return "OK, mas sem candles retornados (verifique instrumento)."
    return "OK: acesso ao market data confirmado."
