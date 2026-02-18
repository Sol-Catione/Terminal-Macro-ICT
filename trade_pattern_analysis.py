from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from statistics import mean, median
from typing import Any

from trade_journal_db import TradeSample


@dataclass(frozen=True)
class TradeFeatures:
    trade_id: str
    hour: int
    timeframe_min: int
    direction_sign: int
    level_type: str | None
    touched_level: bool | None
    rejection: bool | None
    confirmation: bool | None
    rr: float
    risk: float
    reward: float
    atr14: float | None
    risk_atr: float | None
    reward_atr: float | None
    entry_round_dist: float | None
    entry_level_dist: float | None
    entry_level_dist_atr: float | None
    result_r: float | None


def _parse_iso(dt: str) -> datetime:
    # Accept "Z" suffix
    s = (dt or "").strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def _safe_div(a: float, b: float) -> float | None:
    if b == 0:
        return None
    return a / b


def extract_features(trades: list[TradeSample], default_round_step: float = 10.0) -> list[TradeFeatures]:
    out: list[TradeFeatures] = []
    for t in trades:
        dt = _parse_iso(t.dt_lisbon)
        hour = int(dt.hour)
        direction_sign = 1 if t.direction.upper() == "LONG" else -1

        risk = abs(float(t.entry) - float(t.sl))
        reward = abs(float(t.tp) - float(t.entry))
        rr = reward / risk if risk > 0 else 0.0

        atr = float(t.atr14) if t.atr14 is not None and float(t.atr14) > 0 else None
        risk_atr = _safe_div(risk, atr) if atr is not None else None
        reward_atr = _safe_div(reward, atr) if atr is not None else None

        entry_round_dist = None
        step = float(t.psych_step) if t.psych_step is not None and float(t.psych_step) > 0 else float(default_round_step)
        if step and step > 0:
            nearest = round(float(t.entry) / float(step)) * float(step)
            entry_round_dist = abs(float(t.entry) - nearest)

        entry_level_dist = None
        entry_level_dist_atr = None
        if t.psych_level is not None and float(t.psych_level) > 0:
            entry_level_dist = abs(float(t.entry) - float(t.psych_level))
            if atr is not None:
                entry_level_dist_atr = entry_level_dist / atr

        out.append(
            TradeFeatures(
                trade_id=t.trade_id,
                hour=hour,
                timeframe_min=int(t.timeframe_min),
                direction_sign=direction_sign,
                level_type=t.level_type,
                touched_level=t.touched_level,
                rejection=t.rejection,
                confirmation=t.confirmation,
                rr=float(rr),
                risk=float(risk),
                reward=float(reward),
                atr14=atr,
                risk_atr=risk_atr,
                reward_atr=reward_atr,
                entry_round_dist=entry_round_dist,
                entry_level_dist=entry_level_dist,
                entry_level_dist_atr=entry_level_dist_atr,
                result_r=t.result_r,
            )
        )
    return out


def summarize(features: list[TradeFeatures]) -> dict[str, Any]:
    if not features:
        return {"n": 0}

    rr = [f.rr for f in features if f.rr > 0]
    risk_atr = [f.risk_atr for f in features if f.risk_atr is not None]
    reward_atr = [f.reward_atr for f in features if f.reward_atr is not None]
    wins = [f for f in features if f.result_r is not None and f.result_r > 0]
    losses = [f for f in features if f.result_r is not None and f.result_r <= 0]

    return {
        "n": len(features),
        "rr_median": median(rr) if rr else None,
        "risk_atr_median": median(risk_atr) if risk_atr else None,
        "reward_atr_median": median(reward_atr) if reward_atr else None,
        "wins": len(wins),
        "losses": len(losses),
        "winrate": (len(wins) / (len(wins) + len(losses))) if (wins or losses) else None,
        "result_r_mean": mean([f.result_r for f in features if f.result_r is not None])
        if any(f.result_r is not None for f in features)
        else None,
    }


def _vec(f: TradeFeatures) -> list[float]:
    # Use only robust numeric signals. Missing ATR-dependent values become 0 and a penalty is applied via weights.
    touched = 1.0 if f.touched_level else 0.0 if f.touched_level is not None else 0.0
    rej = 1.0 if f.rejection else 0.0 if f.rejection is not None else 0.0
    conf = 1.0 if f.confirmation else 0.0 if f.confirmation is not None else 0.0
    lt = 1.0 if (f.level_type or "").upper() == "SUPORTE" else -1.0 if (f.level_type or "").upper() == "RESISTENCIA" else 0.0
    return [
        float(f.hour),
        float(f.timeframe_min),
        float(f.direction_sign),
        float(lt),
        float(touched),
        float(rej),
        float(conf),
        float(f.rr),
        float(f.risk_atr if f.risk_atr is not None else 0.0),
        float(f.reward_atr if f.reward_atr is not None else 0.0),
        float(f.entry_round_dist if f.entry_round_dist is not None else 0.0),
        float(f.entry_level_dist_atr if f.entry_level_dist_atr is not None else 0.0),
    ]


def nearest_neighbors(
    features: list[TradeFeatures],
    target_id: str,
    k: int = 8,
    weights: list[float] | None = None,
) -> list[tuple[str, float]]:
    """
    Returns list of (trade_id, distance) for nearest neighbors excluding the target itself.
    """
    weights = weights or [0.6, 0.2, 0.6, 0.5, 0.3, 0.3, 0.3, 0.8, 1.2, 1.2, 0.4, 1.0]
    by_id = {f.trade_id: f for f in features}
    target = by_id.get(target_id)
    if target is None:
        return []

    tv = _vec(target)
    out: list[tuple[str, float]] = []
    for f in features:
        if f.trade_id == target_id:
            continue
        v = _vec(f)
        d2 = 0.0
        for w, a, b in zip(weights, tv, v, strict=True):
            d2 += float(w) * (a - b) * (a - b)

        # Penalty if either side lacks ATR
        if (target.risk_atr is None) != (f.risk_atr is None):
            d2 += 2.0
        if (target.reward_atr is None) != (f.reward_atr is None):
            d2 += 2.0
        if (target.entry_level_dist_atr is None) != (f.entry_level_dist_atr is None):
            d2 += 1.0

        out.append((f.trade_id, sqrt(d2)))
    out.sort(key=lambda x: x[1])
    return out[: int(k)]
