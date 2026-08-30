#!/usr/bin/env python3
"""Collect auditable, keyless inputs for the short-term v2 research model.

This is deliberately a research feed. It writes a timestamped snapshot and
never changes a portfolio or submits an order.
"""

from __future__ import annotations

import json
import math
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "research-snapshot.json"
UA = {"User-Agent": "OPUS-Crypto-Research/1.0 (paper research)"}
RISK_TERMS = re.compile(r"hack|exploit|lawsuit|ban|sanction|liquidat|outage|fraud|crash|war", re.I)


def get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def get_text(url: str) -> str:
    request = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def standard_deviation(values: list[float]) -> float:
    average = mean(values)
    return math.sqrt(sum((value - average) ** 2 for value in values) / len(values))


def market_series(asset: str) -> tuple[list[float], list[float], str]:
    """Use exchange candles first; public aggregation is a rate-limit fallback."""
    pair = {"bitcoin": "BTC", "ethereum": "ETH"}[asset]
    try:
        candles = get_json(
            f"https://api.binance.com/api/v3/klines?symbol={pair}EUR&interval=1h&limit=1000"
        )
        return [float(candle[4]) for candle in candles], [float(candle[7]) for candle in candles], "Binance 1h"
    except Exception:
        chart = get_json(
            f"https://api.coingecko.com/api/v3/coins/{asset}/market_chart?vs_currency=eur&days=90"
        )
        return [point[1] for point in chart["prices"]], [point[1] for point in chart["total_volumes"]], "CoinGecko hourly"


def market_features(asset: str) -> dict:
    prices, volumes, source = market_series(asset)
    if len(prices) < 200:
        raise RuntimeError(f"Histórico insuficiente para {asset}: {len(prices)} pontos")
    returns = [prices[i] / prices[i - 1] - 1 for i in range(1, len(prices))]
    ma12, ma48 = mean(prices[-12:]), mean(prices[-48:])
    vol24 = standard_deviation(returns[-24:]) * math.sqrt(24)
    vol90 = standard_deviation(returns[-24 * 30:]) * math.sqrt(24)
    volume_ratio = mean(volumes[-24:]) / mean(volumes[-24 * 7:])
    return {
        "price_eur": round(prices[-1], 4),
        "return_4h": round(prices[-1] / prices[-5] - 1, 5),
        "return_24h": round(prices[-1] / prices[-25] - 1, 5),
        "ma_12h_eur": round(ma12, 4),
        "ma_48h_eur": round(ma48, 4),
        "trend_up": prices[-1] > ma12 > ma48,
        "realized_volatility_24h": round(vol24, 5),
        "realized_volatility_30d": round(vol90, 5),
        "volume_ratio_24h_vs_7d": round(volume_ratio, 3),
        "samples": len(prices),
        "source": source,
    }


def news_risk() -> dict:
    root = ET.fromstring(get_text(
        "https://news.google.com/rss/search?q=(bitcoin%20OR%20ethereum%20OR%20crypto)%20when%3A7d&hl=en-US&gl=US&ceid=US:en"
    ))
    headlines = [item.findtext("title", default="") for item in root.findall("./channel/item")][:30]
    risky = [headline for headline in headlines if RISK_TERMS.search(headline)]
    return {"items_scanned": len(headlines), "risk_headlines": risky[:8],
            "risk_score": round(len(risky) / max(len(headlines), 1), 3)}


def main() -> None:
    market = {asset: market_features(asset) for asset in ("bitcoin", "ethereum")}
    sentiment = get_json("https://api.alternative.me/fng/?limit=7&format=json")["data"]
    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "research-only; inputs for short-term v2, never execution",
        "market": market,
        "sentiment": {"current": sentiment[0], "history": sentiment[1:]},
        "news": news_risk(),
    }
    OUT.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Research snapshot: {snapshot['generated_at']} | {len(snapshot['news']['risk_headlines'])} risk headlines")


if __name__ == "__main__":
    main()
