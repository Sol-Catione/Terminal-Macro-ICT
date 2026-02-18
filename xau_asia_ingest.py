from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any


def _norm_key(k: str) -> str:
    return (k or "").strip().lower().replace(" ", "_")


def _get(row: dict[str, Any], *keys: str) -> str | None:
    for k in keys:
        if k in row and row[k] is not None and str(row[k]).strip() != "":
            return str(row[k]).strip()
    return None


def _parse_float(v: str | None) -> float | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    # Support comma as decimal separator in some exports.
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_date(v: str) -> str | None:
    s = (v or "").strip()
    if not s:
        return None
    # Prefer ISO date.
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date().isoformat()
    except ValueError:
        pass
    # Common BR formats.
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def read_asia_open_daily_csv(file_bytes: bytes, source: str | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Expected columns (minimum): date + open
    Optional: open_ts_utc/timestamp, h1_high/h1_low/h1_close, h3_high/h3_low/h3_close, atr14

    Column name variants are accepted (case/space insensitive).
    """
    notes: list[str] = []
    text = io.TextIOWrapper(io.BytesIO(file_bytes), encoding="utf-8-sig", newline="")
    reader = csv.DictReader(text)
    if not reader.fieldnames:
        return [], ["CSV sem cabecalho."]

    # Normalize headers.
    field_map: dict[str, str] = {_norm_key(f): f for f in reader.fieldnames}

    def col(*names: str) -> str | None:
        for n in names:
            nk = _norm_key(n)
            if nk in field_map:
                return field_map[nk]
        return None

    date_col = col("trade_date", "date", "day")
    open_col = col("open", "open_price")
    ts_col = col("open_ts_utc", "timestamp", "ts", "time")

    if not date_col or not open_col:
        return [], ["Colunas obrigatorias: date (ou trade_date) e open."]

    out: list[dict[str, Any]] = []
    bad_rows = 0

    for idx, raw in enumerate(reader, start=2):
        trade_date = _parse_date(_get(raw, date_col) or "")
        open_px = _parse_float(_get(raw, open_col))
        if not trade_date or open_px is None:
            bad_rows += 1
            continue

        row: dict[str, Any] = {
            "trade_date": trade_date,
            "open_ts_utc": _get(raw, ts_col) if ts_col else None,
            "open": open_px,
            "h1_high": _parse_float(_get(raw, col("h1_high", "high_60m", "h1high") or "")),
            "h1_low": _parse_float(_get(raw, col("h1_low", "low_60m", "h1low") or "")),
            "h1_close": _parse_float(_get(raw, col("h1_close", "close_60m", "h1close") or "")),
            "h3_high": _parse_float(_get(raw, col("h3_high", "high_180m", "h3high") or "")),
            "h3_low": _parse_float(_get(raw, col("h3_low", "low_180m", "h3low") or "")),
            "h3_close": _parse_float(_get(raw, col("h3_close", "close_180m", "h3close") or "")),
            "atr14": _parse_float(_get(raw, col("atr14", "atr_14", "atr") or "")),
            "source": source,
        }
        out.append(row)

    if bad_rows:
        notes.append(f"Ignoradas {bad_rows} linhas invalidas (sem date/open).")
    if len(out) < 10:
        notes.append("Poucos registros importados; verifique se o CSV esta no formato esperado.")

    return out, notes
