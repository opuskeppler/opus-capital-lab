#!/usr/bin/env python3
"""Daily, non-custodial paper-trading simulation for OPUS Crypto Paper Lab."""

from __future__ import annotations

import json
import statistics
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
STATE_PATH = ROOT / "data" / "state.json"
LEDGER_PATH = ROOT / "logs" / "ledger.jsonl"


def fetch_prices(asset_id: str) -> list[float]:
    url = (
        "https://api.coingecko.com/api/v3/coins/"
        f"{asset_id}/market_chart?vs_currency=eur&days=90&interval=daily"
    )
    request = urllib.request.Request(url, headers={"User-Agent": "OPUS-Crypto-Paper-Lab/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)
    return [point[1] for point in payload["prices"]]


def read_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    starting = CONFIG["starting_capital_eur"]
    return {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "cash_eur": starting,
        "holdings": {asset: 0.0 for asset in CONFIG["assets"]},
        "peak_value_eur": starting,
        "max_drawdown": 0.0,
        "last_evaluation_at": None,
    }


def portfolio_value(state: dict, prices: dict[str, float]) -> float:
    return state["cash_eur"] + sum(state["holdings"][asset] * prices[asset] for asset in prices)


def log(entry: dict) -> None:
    with LEDGER_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def target_weights(series: dict[str, list[float]], paused: bool) -> tuple[dict[str, float], dict[str, dict]]:
    analysis = {}
    eligible = []
    for asset, prices in series.items():
        sma20 = statistics.mean(prices[-20:])
        sma60 = statistics.mean(prices[-60:])
        momentum = prices[-1] / prices[-20] - 1
        bullish = prices[-1] > sma20 > sma60 and momentum > 0
        analysis[asset] = {
            "price_eur": round(prices[-1], 4),
            "sma20_eur": round(sma20, 4),
            "sma60_eur": round(sma60, 4),
            "momentum_20d": round(momentum, 5),
            "bullish": bullish,
        }
        if bullish and not paused:
            eligible.append(asset)

    weights = {asset: 0.0 for asset in series}
    if eligible:
        allocation = min(CONFIG["max_asset_weight"], 0.90 / len(eligible))
        for asset in eligible:
            weights[asset] = allocation
    return weights, analysis


def rebalance(state: dict, prices: dict[str, float], weights: dict[str, float]) -> list[dict]:
    value = portfolio_value(state, prices)
    operations = []
    for asset, target_weight in weights.items():
        current_value = state["holdings"][asset] * prices[asset]
        target_value = value * target_weight
        difference = target_value - current_value
        if abs(difference) < CONFIG["minimum_trade_eur"]:
            continue
        if difference > 0:
            gross = min(difference, state["cash_eur"] / (1 + CONFIG["fee_rate"]))
            fee = gross * CONFIG["fee_rate"]
            quantity = gross / prices[asset]
            state["cash_eur"] -= gross + fee
            state["holdings"][asset] += quantity
            operations.append({"side": "BUY", "asset": asset, "eur": round(gross, 2), "fee_eur": round(fee, 2), "quantity": quantity})
        else:
            gross = min(-difference, current_value)
            quantity = gross / prices[asset]
            fee = gross * CONFIG["fee_rate"]
            state["holdings"][asset] -= quantity
            state["cash_eur"] += gross - fee
            operations.append({"side": "SELL", "asset": asset, "eur": round(gross, 2), "fee_eur": round(fee, 2), "quantity": quantity})
    return operations


def main() -> None:
    try:
        series = {asset: fetch_prices(asset) for asset in CONFIG["assets"]}
    except Exception as error:
        print(f"Preço não actualizado: {error}", file=sys.stderr)
        raise SystemExit(1)

    state = read_state()
    prices = {asset: values[-1] for asset, values in series.items()}
    pre_value = portfolio_value(state, prices)
    state["peak_value_eur"] = max(state["peak_value_eur"], pre_value)
    drawdown = 1 - pre_value / state["peak_value_eur"]
    state["max_drawdown"] = max(state["max_drawdown"], drawdown)
    paused = drawdown >= CONFIG["max_drawdown_pause"]
    weights, analysis = target_weights(series, paused)

    now = datetime.now(timezone.utc)
    operations = rebalance(state, prices, weights)
    state["last_evaluation_at"] = now.isoformat()

    total = portfolio_value(state, prices)
    state["peak_value_eur"] = max(state["peak_value_eur"], total)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    entry = {
        "timestamp": now.isoformat(),
        "portfolio_value_eur": round(total, 2),
        "return_pct": round((total / CONFIG["starting_capital_eur"] - 1) * 100, 3),
        "drawdown_pct": round(drawdown * 100, 3),
        "risk_pause": paused,
        "analysis": analysis,
        "operations": operations,
    }
    log(entry)
    public_state = {
        "generated_at": entry["timestamp"],
        "config": {
            "starting_capital_eur": CONFIG["starting_capital_eur"],
            "target_capital_eur": CONFIG["target_capital_eur"],
            "fee_rate": CONFIG["fee_rate"],
            "max_drawdown_pause": CONFIG["max_drawdown_pause"],
            "assets": CONFIG["assets"],
        },
        "state": state,
        "snapshot": entry,
    }
    (ROOT / "data" / "dashboard.json").write_text(
        json.dumps(public_state, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"OPUS Crypto Paper Lab | {now.isoformat()}")
    print(f"Carteira: €{total:.2f} | Retorno: {entry['return_pct']:.2f}% | Drawdown: {entry['drawdown_pct']:.2f}%")
    print("Operações:", ", ".join(f"{op['side']} {op['asset']} €{op['eur']:.2f}" for op in operations) or "nenhuma")
    for asset, item in analysis.items():
        print(f"{CONFIG['assets'][asset]['symbol']}: €{item['price_eur']:.2f} | tendência positiva: {item['bullish']}")


if __name__ == "__main__":
    main()
