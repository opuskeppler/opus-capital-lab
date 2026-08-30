#!/usr/bin/env python3
"""Download a reproducible 24-month, hourly BTC/EUR and ETH/EUR dataset.

Public Binance candles are paginated at 1,000 observations. The output is a
research artifact only; it is never consumed by the paper-trading executor.
"""

from __future__ import annotations

import csv
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "historical"
INTERVAL_MS = 60 * 60 * 1000
LIMIT = 1000
PAIRS = {"bitcoin": "BTCEUR", "ethereum": "ETHEUR"}


def fetch(url: str) -> list:
    request = urllib.request.Request(url, headers={"User-Agent": "OPUS-Crypto-Research/1.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def download(symbol: str, start_ms: int, end_ms: int) -> list[list]:
    candles: list[list] = []
    cursor = start_ms
    while cursor < end_ms:
        query = urllib.parse.urlencode({"symbol": symbol, "interval": "1h", "limit": LIMIT,
                                         "startTime": cursor, "endTime": end_ms})
        batch = fetch(f"https://api.binance.com/api/v3/klines?{query}")
        if not batch:
            break
        candles.extend(batch)
        cursor = int(batch[-1][0]) + INTERVAL_MS
        print(f"{symbol}: {len(candles)} candles", flush=True)
        if len(batch) < LIMIT:
            break
        time.sleep(0.25)
    # Exchanges can return a boundary row twice; retain a unique chronological series.
    return list({int(row[0]): row for row in candles}.values())


def validate(rows: list[list], start_ms: int, end_ms: int) -> dict:
    timestamps = [int(row[0]) for row in rows]
    gaps = [right - left for left, right in zip(timestamps, timestamps[1:]) if right - left != INTERVAL_MS]
    expected_minimum = int((end_ms - start_ms) / INTERVAL_MS) - 2
    return {"candles": len(rows), "expected_minimum": expected_minimum,
            "first_open_time": timestamps[0] if timestamps else None,
            "last_open_time": timestamps[-1] if timestamps else None,
            "gaps": len(gaps), "complete": len(rows) >= expected_minimum and not gaps}


def main() -> None:
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=730)
    start_ms, end_ms = int(start.timestamp() * 1000), int(now.timestamp() * 1000)
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"source": "Binance public REST /api/v3/klines", "interval": "1h",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "requested_start": start.isoformat(), "requested_end": now.isoformat(), "assets": {}}
    for asset, symbol in PAIRS.items():
        rows = download(symbol, start_ms, end_ms)
        rows.sort(key=lambda row: int(row[0]))
        path = OUT / f"{asset}-eur-1h.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["open_time_ms", "open", "high", "low", "close", "volume_base", "close_time_ms", "volume_eur", "trades"])
            for row in rows:
                writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8]])
        manifest["assets"][asset] = {"symbol": symbol, "file": str(path.relative_to(ROOT)),
                                     **validate(rows, start_ms, end_ms)}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
