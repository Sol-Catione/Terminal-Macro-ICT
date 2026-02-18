from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Any


@dataclass(frozen=True)
class EntryPlan:
    direction: str  # LONG / SHORT / NEUTRAL
    entry: float
    stop: float
    take_profit: float
    rr: float
    lots: float | None
    risk_amount: float | None
    stop_distance: float
    notes: list[str]
    stats: dict[str, Any]


def _nearest_round(price: float, step: float) -> float:
    if step <= 0:
        return price
    return round(price / step) * step


def _round_to_step(price: float, step: float, direction: str) -> float:
    """
    Round price to nearest step in a favorable direction.
    LONG: round down for entry/stop, up for TP is handled by caller.
    SHORT: inverse.
    """
    if step <= 0:
        return price
    k = price / step
    if direction == "down":
        return (int(k) if k == int(k) else int(k)) * step
    return (int(k) + (0 if k == int(k) else 1)) * step


def build_entry_plan(
    history: list[dict[str, Any]],
    reference_price: float,
    round_step: float = 10.0,
    round_proximity: float = 1.5,
    min_rr: float = 1.0,
    account_balance: float | None = None,
    risk_percent: float | None = None,
    contract_size: float = 100.0,  # XAUUSD: 1 lot ~ 100 oz (typical), varies by broker.
) -> EntryPlan:
    """
    Pure heuristic plan based on Asia-open daily snapshots.
    It is NOT financial advice; it's a deterministic suggestion layer.
    """
    notes: list[str] = []
    if not history:
        return EntryPlan(
            direction="NEUTRAL",
            entry=reference_price,
            stop=reference_price,
            take_profit=reference_price,
            rr=0.0,
            lots=None,
            risk_amount=None,
            stop_distance=0.0,
            notes=["Sem dados no banco para calcular padroes."],
            stats={},
        )

    # Filter for rows that have at least H1 high/low/close.
    rows_h1 = [
        r
        for r in history
        if r.get("open") is not None
        and r.get("h1_high") is not None
        and r.get("h1_low") is not None
        and r.get("h1_close") is not None
    ]
    if len(rows_h1) < 50:
        notes.append("Poucos registros com H1 (h1_high/h1_low/h1_close). Melhor importar CSV com colunas H1.")

    rows_for_stats = rows_h1 if rows_h1 else [r for r in history if r.get("open") is not None]

    up_moves: list[float] = []
    down_moves: list[float] = []
    up_moves_atr: list[float] = []
    down_moves_atr: list[float] = []
    close_dir: list[int] = []

    for r in rows_h1:
        o = float(r["open"])
        up = float(r["h1_high"]) - o
        down = o - float(r["h1_low"])
        up_moves.append(up)
        down_moves.append(down)
        atr = r.get("atr14")
        if atr is not None and float(atr) > 0:
            up_moves_atr.append(up / float(atr))
            down_moves_atr.append(down / float(atr))
        close_dir.append(1 if float(r["h1_close"]) > o else -1)

    med_up = median(up_moves) if up_moves else None
    med_down = median(down_moves) if down_moves else None
    med_up_atr = median(up_moves_atr) if up_moves_atr else None
    med_down_atr = median(down_moves_atr) if down_moves_atr else None

    # Use the most recent ATR as current volatility regime reference.
    current_atr = None
    for r in history:
        atr = r.get("atr14")
        if atr is not None and float(atr) > 0:
            current_atr = float(atr)
    if current_atr is None and rows_h1:
        # Fallback: infer from median absolute moves.
        if med_up is not None and med_down is not None:
            current_atr = max(med_up, med_down) * 2.0
        elif med_up is not None:
            current_atr = med_up * 2.0
        elif med_down is not None:
            current_atr = med_down * 2.0

    nearest = _nearest_round(reference_price, round_step)
    near_round = abs(reference_price - nearest) <= float(round_proximity)

    # Round-number bias stats.
    near_rows = []
    if rows_h1:
        for r in rows_h1:
            o = float(r["open"])
            o_nearest = _nearest_round(o, round_step)
            if abs(o - o_nearest) <= float(round_proximity):
                near_rows.append(r)

    long_winrate = None
    if near_rows:
        wins = 0
        for r in near_rows:
            wins += 1 if float(r["h1_close"]) > float(r["open"]) else 0
        long_winrate = wins / len(near_rows)

    direction = "NEUTRAL"
    if long_winrate is not None and len(near_rows) >= 80:
        if long_winrate >= 0.55:
            direction = "LONG"
        elif long_winrate <= 0.45:
            direction = "SHORT"
    elif rows_h1:
        # Fallback to overall close direction.
        overall = sum(close_dir) / len(close_dir)
        if overall >= 0.05:
            direction = "LONG"
        elif overall <= -0.05:
            direction = "SHORT"

    # Entry/stop/TP selection.
    entry = nearest if near_round else reference_price
    if round_step > 0 and near_round:
        notes.append(f"Entrada ancorada em numero redondo: {nearest:.2f}")

    # Stop distance from historical adverse move if available.
    base_stop = None
    # Prefer ATR-normalized median adverse move when available.
    if current_atr is not None and med_up_atr is not None and med_down_atr is not None:
        base_norm = med_down_atr if direction == "LONG" else med_up_atr if direction == "SHORT" else max(med_up_atr, med_down_atr)
        base_stop = float(base_norm) * float(current_atr)
        notes.append("Stop baseado em mediana do movimento adverso normalizado por ATR14.")
    elif med_up is not None and med_down is not None:
        base_stop = med_down if direction == "LONG" else med_up if direction == "SHORT" else max(med_up, med_down)
    elif med_up is not None:
        base_stop = med_up
    elif med_down is not None:
        base_stop = med_down
    else:
        # Conservative default in absence of volatility.
        base_stop = max(1.0, round_step * 0.1) if round_step > 0 else 1.0
        notes.append("Stop default (sem H1 suficiente).")

    stop_distance = max(float(base_stop), 0.5)

    if direction == "LONG":
        stop = entry - stop_distance
        take_profit = entry + stop_distance * float(min_rr)
    elif direction == "SHORT":
        stop = entry + stop_distance
        take_profit = entry - stop_distance * float(min_rr)
    else:
        # Neutral: propose symmetric bracket.
        stop = entry - stop_distance
        take_profit = entry + stop_distance * float(min_rr)

    rr = float(min_rr) if stop_distance > 0 else 0.0

    # Round TP to a favorable round number (optional).
    if round_step > 0:
        if direction == "LONG":
            take_profit = _round_to_step(take_profit, round_step, direction="up")
        elif direction == "SHORT":
            take_profit = _round_to_step(take_profit, round_step, direction="down")

    # Ensure RR >= min_rr after rounding.
    effective_rr = abs(take_profit - entry) / abs(entry - stop) if abs(entry - stop) > 0 else 0.0
    if effective_rr + 1e-9 < float(min_rr):
        # Undo rounding if it violated RR.
        if direction == "LONG":
            take_profit = entry + stop_distance * float(min_rr)
        elif direction == "SHORT":
            take_profit = entry - stop_distance * float(min_rr)
        effective_rr = float(min_rr)

    lots = None
    risk_amount = None
    if account_balance is not None and risk_percent is not None:
        risk_amount = float(account_balance) * float(risk_percent) / 100.0
        denom = stop_distance * float(contract_size)
        if denom > 0:
            lots = risk_amount / denom

    stats = {
        "history_rows": len(history),
        "h1_rows": len(rows_h1),
        "near_round_rows": len(near_rows),
        "near_round_long_winrate": long_winrate,
        "median_up_h1": med_up,
        "median_down_h1": med_down,
        "median_up_h1_atr": med_up_atr,
        "median_down_h1_atr": med_down_atr,
        "current_atr14": current_atr,
        "reference_price": reference_price,
        "nearest_round": nearest,
        "reference_near_round": near_round,
    }

    if direction == "NEUTRAL":
        notes.append("Vies neutro (sem sinal forte). Use como checklist, nao como gatilho unico.")
    else:
        notes.append("Plano gerado por heuristica com base no historico importado.")

    if current_atr is not None and current_atr > 0:
        notes.append(f"Contexto ATR14: stop_distance = {stop_distance / current_atr:.2f} ATR.")

    return EntryPlan(
        direction=direction,
        entry=float(entry),
        stop=float(stop),
        take_profit=float(take_profit),
        rr=float(effective_rr),
        lots=lots,
        risk_amount=risk_amount,
        stop_distance=float(stop_distance),
        notes=notes,
        stats=stats,
    )
