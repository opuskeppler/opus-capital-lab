#!/usr/bin/env python3
"""Explainable probability model for the short-term v2 shadow book.

It produces a recommendation only. The current short-term simulator and its
portfolio state are intentionally not read or changed here.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESEARCH = ROOT / "data" / "research-snapshot.json"
OUT = ROOT / "data" / "short-term-v2-shadow.json"


def probability(features: dict, fear_greed: int, news_risk: float) -> tuple[float, list[str]]:
    """A transparent prior, to be calibrated only after walk-forward testing."""
    score = 0.25
    reasons = []
    if features["trend_up"]:
        score += 0.25
        reasons.append("tendência 12h/48h positiva")
    if features["return_4h"] > 0:
        score += 0.10
        reasons.append("momentum 4h positivo")
    if features["return_24h"] > 0:
        score += 0.10
        reasons.append("momentum 24h positivo")
    if features["realized_volatility_24h"] <= features["realized_volatility_30d"] * 1.25:
        score += 0.10
        reasons.append("volatilidade dentro do regime")
    else:
        score -= 0.15
        reasons.append("volatilidade anormal")
    if features["volume_ratio_24h_vs_7d"] >= 0.80:
        score += 0.05
        reasons.append("participação/volume suficiente")
    if 30 <= fear_greed <= 75:
        score += 0.05
        reasons.append("sentimento sem extremo")
    elif fear_greed > 80:
        score -= 0.10
        reasons.append("euforia: reduzir confiança")
    if news_risk > 0.15:
        score -= 0.15
        reasons.append("risco noticioso elevado")
    return max(0.0, min(1.0, score)), reasons


def main() -> None:
    if not RESEARCH.exists():
        raise SystemExit("Falta research-snapshot.json; execute research_pipeline.py primeiro.")
    research = json.loads(RESEARCH.read_text(encoding="utf-8"))
    fear_greed = int(research["sentiment"]["current"]["value"])
    news_risk = research["news"]["risk_score"]
    signals = {}
    for asset, features in research["market"].items():
        chance, reasons = probability(features, fear_greed, news_risk)
        eligible = chance >= 0.65 and features["trend_up"] and news_risk <= 0.15
        signals[asset] = {
            "probability_positive_next_24h": round(chance, 2),
            "decision": "candidate_entry" if eligible else "cash",
            "max_risk_per_position_pct": 0.5,
            "aggregate_exposure_cap_pct": 60,
            "reasons": reasons,
        }
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "shadow — no portfolio mutation or real-order authority",
        "calibration_status": "uncalibrated; not eligible to trade until walk-forward validation",
        "signals": signals,
    }
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
