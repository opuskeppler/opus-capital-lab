#!/usr/bin/env python3
"""First out-of-sample-style baseline for short-term v2 (research only)."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / "data" / "historical"
OUT = ROOT / "data" / "short-term-v2-backtest.json"
FEE = 0.002


def average(values): return sum(values) / len(values)
def std(values):
    m = average(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / len(values))


def candles(asset):
    with (HISTORY / f"{asset}-eur-1h.csv").open() as handle:
        return list(csv.DictReader(handle))


def window_average(prefix, start, end):
    return (prefix[end] - prefix[start]) / (end - start)


def window_std(prefix, squares, start, end):
    avg = window_average(prefix, start, end)
    return max(0, window_average(squares, start, end) - avg * avg) ** .5


def score(close, volume, volume_prefix, returns_prefix, return_squares, i):
    value = .25
    trend = close[i] > average(close[i-11:i+1]) > average(close[i-47:i+1])
    if trend: value += .25
    if close[i] > close[i-4]: value += .10
    if close[i] > close[i-24]: value += .10
    if window_std(returns_prefix, return_squares, i - 23, i + 1) <= window_std(returns_prefix, return_squares, i - 719, i + 1) * 1.25: value += .10
    else: value -= .15
    if window_average(volume_prefix, i - 23, i + 1) >= window_average(volume_prefix, i - 167, i + 1) * .8: value += .05
    return value


def run(asset):
    rows = candles(asset)
    close = [float(row["close"]) for row in rows]
    volume = [float(row["volume_eur"]) for row in rows]
    returns = [0.0] + [close[i] / close[i - 1] - 1 for i in range(1, len(close))]
    def prefix(values):
        output = [0.0]
        for value in values: output.append(output[-1] + value)
        return output
    volume_prefix, returns_prefix = prefix(volume), prefix(returns)
    return_squares = prefix([value * value for value in returns])
    cash, qty, entry, fees, trades = 100.0, 0.0, 0.0, 0.0, 0
    peak, max_dd = cash, 0.0
    for i in range(720, len(rows)):
        price, probability = close[i], score(close, volume, volume_prefix, returns_prefix, return_squares, i)
        value = cash + qty * price
        peak = max(peak, value); max_dd = max(max_dd, 1 - value / peak)
        held_hours = i - entry[1] if isinstance(entry, tuple) else 0
        if qty and (probability < .55 or held_hours >= 24):
            gross = qty * price; cost = gross * FEE
            cash += gross - cost; fees += cost; qty = 0.0; entry = 0.0; trades += 1
        elif not qty and probability >= .65:
            gross = cash * .60 / (1 + FEE); cost = gross * FEE
            cash -= gross + cost; qty = gross / price; entry = (price, i); fees += cost; trades += 1
    final = cash + qty * close[-1]
    buy_hold = 100 * close[-1] / close[720]
    return {"start_capital_eur": 100, "final_value_eur": round(final, 2),
            "return_pct": round((final / 100 - 1) * 100, 2), "buy_hold_return_pct": round((buy_hold / 100 - 1) * 100, 2),
            "max_drawdown_pct": round(max_dd * 100, 2), "fees_eur": round(fees, 2), "operations": trades}


def main():
    assets = {asset: run(asset) for asset in ("bitcoin", "ethereum")}
    total = sum(item["final_value_eur"] for item in assets.values())
    report = {"method": "fixed v2 factor baseline; 24-month hourly walk-forward simulation with 0.20% fee",
              "warning": "News and sentiment are deliberately excluded: no point-in-time historical archive yet.",
              "assets": assets, "combined_final_eur": round(total, 2),
              "combined_return_pct": round((total / 200 - 1) * 100, 2)}
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__": main()
