from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class DbStats:
    rows: int
    min_date: str | None
    max_date: str | None


def db_path() -> Path:
    data_dir = Path(__file__).resolve().parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "xauusd_asia.sqlite3"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS asia_open_daily (
            trade_date TEXT PRIMARY KEY,
            open_ts_utc TEXT,
            open REAL NOT NULL,
            h1_high REAL,
            h1_low REAL,
            h1_close REAL,
            h3_high REAL,
            h3_low REAL,
            h3_close REAL,
            atr14 REAL,
            source TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_asia_open_daily_date ON asia_open_daily(trade_date)")
    # Lightweight migration for older DBs.
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(asia_open_daily)").fetchall()}
    if "atr14" not in cols:
        conn.execute("ALTER TABLE asia_open_daily ADD COLUMN atr14 REAL")
    conn.commit()


def upsert_asia_open_daily(conn: sqlite3.Connection, rows: Iterable[dict[str, Any]]) -> int:
    sql = """
        INSERT INTO asia_open_daily (
            trade_date, open_ts_utc, open, h1_high, h1_low, h1_close, h3_high, h3_low, h3_close, atr14, source
        ) VALUES (
            :trade_date, :open_ts_utc, :open, :h1_high, :h1_low, :h1_close, :h3_high, :h3_low, :h3_close, :atr14, :source
        )
        ON CONFLICT(trade_date) DO UPDATE SET
            open_ts_utc=excluded.open_ts_utc,
            open=excluded.open,
            h1_high=excluded.h1_high,
            h1_low=excluded.h1_low,
            h1_close=excluded.h1_close,
            h3_high=excluded.h3_high,
            h3_low=excluded.h3_low,
            h3_close=excluded.h3_close,
            atr14=excluded.atr14,
            source=excluded.source
    """
    cur = conn.cursor()
    count = 0
    for row in rows:
        cur.execute(sql, row)
        count += 1
    conn.commit()
    return count


def get_stats(conn: sqlite3.Connection) -> DbStats:
    row = conn.execute(
        "SELECT COUNT(*) AS c, MIN(trade_date) AS min_d, MAX(trade_date) AS max_d FROM asia_open_daily"
    ).fetchone()
    return DbStats(rows=int(row["c"]), min_date=row["min_d"], max_date=row["max_d"])


def fetch_last(conn: sqlite3.Connection, limit: int = 1200) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT * FROM asia_open_daily ORDER BY trade_date DESC LIMIT ?",
        (int(limit),),
    )
    return [dict(r) for r in cur.fetchall()]


def fetch_all(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    cur = conn.execute("SELECT * FROM asia_open_daily ORDER BY trade_date ASC")
    return [dict(r) for r in cur.fetchall()]
