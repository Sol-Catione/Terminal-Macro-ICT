from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import xau_asia_db


@dataclass(frozen=True)
class TradeSample:
    trade_id: str
    symbol: str
    timeframe_min: int
    dt_lisbon: str
    dt_utc: str
    direction: str  # LONG/SHORT
    psych_step: float | None
    psych_level: float | None
    level_type: str | None  # SUPORTE/RESISTENCIA
    touched_level: bool | None
    rejection: bool | None
    confirmation: bool | None
    entry: float
    sl: float
    tp: float
    atr14: float | None
    result_r: float | None
    notes: str | None
    image_name: str | None
    image_mime: str | None
    has_image: bool
    created_at: str


def connect() -> sqlite3.Connection:
    # Reuse the same data/ folder as xau_asia_db
    conn = sqlite3.connect(xau_asia_db.db_path())
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trade_samples (
            trade_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            timeframe_min INTEGER NOT NULL,
            dt_lisbon TEXT NOT NULL,
            dt_utc TEXT NOT NULL,
            direction TEXT NOT NULL,
            psych_step REAL,
            psych_level REAL,
            level_type TEXT,
            touched_level INTEGER,
            rejection INTEGER,
            confirmation INTEGER,
            entry REAL NOT NULL,
            sl REAL NOT NULL,
            tp REAL NOT NULL,
            atr14 REAL,
            result_r REAL,
            notes TEXT,
            image_name TEXT,
            image_mime TEXT,
            image_blob BLOB,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trade_samples_dt_utc ON trade_samples(dt_utc)")
    # Lightweight migrations for older DBs.
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(trade_samples)").fetchall()}
    if "psych_step" not in cols:
        conn.execute("ALTER TABLE trade_samples ADD COLUMN psych_step REAL")
    if "psych_level" not in cols:
        conn.execute("ALTER TABLE trade_samples ADD COLUMN psych_level REAL")
    if "level_type" not in cols:
        conn.execute("ALTER TABLE trade_samples ADD COLUMN level_type TEXT")
    if "touched_level" not in cols:
        conn.execute("ALTER TABLE trade_samples ADD COLUMN touched_level INTEGER")
    if "rejection" not in cols:
        conn.execute("ALTER TABLE trade_samples ADD COLUMN rejection INTEGER")
    if "confirmation" not in cols:
        conn.execute("ALTER TABLE trade_samples ADD COLUMN confirmation INTEGER")
    if "image_name" not in cols:
        conn.execute("ALTER TABLE trade_samples ADD COLUMN image_name TEXT")
    if "image_mime" not in cols:
        conn.execute("ALTER TABLE trade_samples ADD COLUMN image_mime TEXT")
    if "image_blob" not in cols:
        conn.execute("ALTER TABLE trade_samples ADD COLUMN image_blob BLOB")
    conn.commit()


def upsert_trade_samples(conn: sqlite3.Connection, rows: Iterable[dict[str, Any]]) -> int:
    sql = """
        INSERT INTO trade_samples (
            trade_id, symbol, timeframe_min, dt_lisbon, dt_utc, direction,
            psych_step, psych_level, level_type, touched_level, rejection, confirmation,
            entry, sl, tp, atr14, result_r, notes,
            image_name, image_mime, image_blob
        ) VALUES (
            :trade_id, :symbol, :timeframe_min, :dt_lisbon, :dt_utc, :direction,
            :psych_step, :psych_level, :level_type, :touched_level, :rejection, :confirmation,
            :entry, :sl, :tp, :atr14, :result_r, :notes,
            :image_name, :image_mime, :image_blob
        )
        ON CONFLICT(trade_id) DO UPDATE SET
            symbol=excluded.symbol,
            timeframe_min=excluded.timeframe_min,
            dt_lisbon=excluded.dt_lisbon,
            dt_utc=excluded.dt_utc,
            direction=excluded.direction,
            psych_step=excluded.psych_step,
            psych_level=excluded.psych_level,
            level_type=excluded.level_type,
            touched_level=excluded.touched_level,
            rejection=excluded.rejection,
            confirmation=excluded.confirmation,
            entry=excluded.entry,
            sl=excluded.sl,
            tp=excluded.tp,
            atr14=excluded.atr14,
            result_r=excluded.result_r,
            notes=excluded.notes,
            image_name=COALESCE(excluded.image_name, trade_samples.image_name),
            image_mime=COALESCE(excluded.image_mime, trade_samples.image_mime),
            image_blob=COALESCE(excluded.image_blob, trade_samples.image_blob)
    """
    cur = conn.cursor()
    count = 0
    for row in rows:
        cur.execute(sql, row)
        count += 1
    conn.commit()
    return count


def fetch_all(conn: sqlite3.Connection) -> list[TradeSample]:
    cur = conn.execute(
        """
        SELECT
            trade_id, symbol, timeframe_min, dt_lisbon, dt_utc, direction,
            psych_step, psych_level, level_type, touched_level, rejection, confirmation,
            entry, sl, tp, atr14, result_r, notes, created_at,
            image_name, image_mime,
            (image_blob IS NOT NULL) AS has_image
        FROM trade_samples
        ORDER BY dt_utc ASC
        """
    )
    out: list[TradeSample] = []
    for r in cur.fetchall():
        out.append(
            TradeSample(
                trade_id=str(r["trade_id"]),
                symbol=str(r["symbol"]),
                timeframe_min=int(r["timeframe_min"]),
                dt_lisbon=str(r["dt_lisbon"]),
                dt_utc=str(r["dt_utc"]),
                direction=str(r["direction"]),
                psych_step=float(r["psych_step"]) if r["psych_step"] is not None else None,
                psych_level=float(r["psych_level"]) if r["psych_level"] is not None else None,
                level_type=str(r["level_type"]) if r["level_type"] is not None else None,
                touched_level=bool(int(r["touched_level"])) if r["touched_level"] is not None else None,
                rejection=bool(int(r["rejection"])) if r["rejection"] is not None else None,
                confirmation=bool(int(r["confirmation"])) if r["confirmation"] is not None else None,
                entry=float(r["entry"]),
                sl=float(r["sl"]),
                tp=float(r["tp"]),
                atr14=float(r["atr14"]) if r["atr14"] is not None else None,
                result_r=float(r["result_r"]) if r["result_r"] is not None else None,
                notes=str(r["notes"]) if r["notes"] is not None else None,
                image_name=str(r["image_name"]) if r["image_name"] is not None else None,
                image_mime=str(r["image_mime"]) if r["image_mime"] is not None else None,
                has_image=bool(int(r["has_image"])),
                created_at=str(r["created_at"]),
            )
        )
    return out


def count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS c FROM trade_samples").fetchone()
    return int(row["c"])


def fetch_image(conn: sqlite3.Connection, trade_id: str) -> tuple[bytes | None, str | None, str | None]:
    row = conn.execute(
        "SELECT image_blob, image_mime, image_name FROM trade_samples WHERE trade_id = ?",
        (trade_id,),
    ).fetchone()
    if not row:
        return None, None, None
    blob = row["image_blob"]
    return (bytes(blob) if blob is not None else None), row["image_mime"], row["image_name"]
