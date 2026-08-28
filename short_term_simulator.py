#!/usr/bin/env python3
"""Intraday paper-trading book: 5-minute data, evaluated every 3 minutes."""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
STATE_PATH = ROOT / "data" / "short-term-state.json"
LEDGER_PATH = ROOT / "logs" / "short-term-ledger.jsonl"


def fetch_prices(asset_id: str) -> list[float]:
    url = f"https://api.coingecko.com/api/v3/coins/{asset_id}/market_chart?vs_currency=eur&days=1"
    request = urllib.request.Request(url, headers={"User-Agent": "OPUS-Short-Term-Paper-Lab/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)
    # CoinGecko returns sub-hour points for one day; collapse accidental duplicates.
    values = [point[1] for point in payload["prices"]]
    if len(values) < 20:
        raise RuntimeError("Dados intradiários insuficientes")
    return values


def read_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    starting = CONFIG["starting_capital_eur"]
    return {
        "started_at": datetime.now(timezone.utc).isoformat(), "cash_eur": starting,
        "holdings": {asset: 0.0 for asset in CONFIG["assets"]},
        "entry_price": {asset: 0.0 for asset in CONFIG["assets"]},
        "peak_value_eur": starting, "max_drawdown": 0.0, "session_date": None,
        "last_evaluation_at": None,
    }


def portfolio_value(state: dict, prices: dict[str, float]) -> float:
    return state["cash_eur"] + sum(state["holdings"][asset] * prices[asset] for asset in prices)


def log(entry: dict) -> None:
    with LEDGER_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def signal(prices: list[float]) -> dict:
    fast = sum(prices[-5:]) / 5
    slow = sum(prices[-15:]) / 15
    momentum = prices[-1] / prices[-15] - 1
    return {"price_eur": round(prices[-1], 4), "fast_ma_eur": round(fast, 4),
            "slow_ma_eur": round(slow, 4), "momentum_15": round(momentum, 5),
            "bullish": prices[-1] > fast > slow and momentum > 0}


def trade(state: dict, asset: str, price: float, prices: dict[str, float], item: dict, halted: bool) -> list[dict]:
    current = state["holdings"][asset]
    current_value = current * price
    entry = state["entry_price"][asset]
    stop = bool(entry and price <= entry * 0.988)
    take = bool(entry and price >= entry * 1.018)
    exit_signal = current > 0 and (not item["bullish"] or stop or take or halted)
    operations = []
    if exit_signal and current_value >= CONFIG["minimum_trade_eur"]:
        fee = current_value * CONFIG["fee_rate"]
        state["holdings"][asset] = 0.0
        state["entry_price"][asset] = 0.0
        state["cash_eur"] += current_value - fee
        reason = "STOP" if stop else "TAKE" if take else "RISCO" if halted else "SINAL"
        operations.append({"side": "SELL", "asset": asset, "eur": round(current_value, 2), "fee_eur": round(fee, 2), "quantity": current, "reason": reason})
    elif item["bullish"] and not halted and current == 0:
        # 45% maximum per asset, never deploy more than 90% of the book.
        gross = min(0.45 * portfolio_value(state, prices), state["cash_eur"] / (1 + CONFIG["fee_rate"]))
        if gross >= CONFIG["minimum_trade_eur"]:
            fee = gross * CONFIG["fee_rate"]
            quantity = gross / price
            state["cash_eur"] -= gross + fee
            state["holdings"][asset] += quantity
            state["entry_price"][asset] = price
            operations.append({"side": "BUY", "asset": asset, "eur": round(gross, 2), "fee_eur": round(fee, 2), "quantity": quantity, "reason": "ENTRADA"})
    return operations


def main() -> None:
    try:
        series = {asset: fetch_prices(asset) for asset in CONFIG["assets"]}
    except Exception as error:
        print(f"Preço intradiário não actualizado: {error}", file=sys.stderr)
        raise SystemExit(1)
    now = datetime.now(timezone.utc)
    state = read_state()
    prices = {asset: values[-1] for asset, values in series.items()}
    pre_value = portfolio_value(state, prices)
    if state["session_date"] != now.date().isoformat():
        state["session_date"] = now.date().isoformat()
        state["peak_value_eur"] = pre_value
    state["peak_value_eur"] = max(state["peak_value_eur"], pre_value)
    drawdown = 1 - pre_value / state["peak_value_eur"]
    state["max_drawdown"] = max(state["max_drawdown"], drawdown)
    halted = drawdown >= 0.03
    analysis = {asset: signal(values) for asset, values in series.items()}
    operations = []
    for asset in CONFIG["assets"]:
        operations.extend(trade(state, asset, prices[asset], prices, analysis[asset], halted))
    state["last_evaluation_at"] = now.isoformat()
    total = portfolio_value(state, prices)
    state["peak_value_eur"] = max(state["peak_value_eur"], total)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    entry = {"timestamp": now.isoformat(), "portfolio_value_eur": round(total, 2),
             "return_pct": round((total / CONFIG["starting_capital_eur"] - 1) * 100, 3),
             "drawdown_pct": round(drawdown * 100, 3), "risk_pause": halted,
             "analysis": analysis, "operations": operations}
    log(entry)
    public = {"generated_at": entry["timestamp"], "strategy": "short-term", "config": {
        "starting_capital_eur": CONFIG["starting_capital_eur"], "fee_rate": CONFIG["fee_rate"],
        "max_drawdown_pause": 0.03, "assets": CONFIG["assets"]}, "state": state, "snapshot": entry}
    (ROOT / "data" / "short-term-dashboard.json").write_text(json.dumps(public, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Short Term | {now.isoformat()} | Carteira: €{total:.2f} | Retorno: {entry['return_pct']:.2f}%")
    print("Operações:", ", ".join(f"{op['side']} {op['asset']} €{op['eur']:.2f}" for op in operations) or "nenhuma")


if __name__ == "__main__":
    main()
