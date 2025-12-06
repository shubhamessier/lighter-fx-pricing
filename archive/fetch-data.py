import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
# Base URL for Lighter API (mainnet)
LIGHTER_BASE_URL = "https://mainnet.zklighter.elliot.ai"  # from Lighter docs :contentReference[oaicite:0]{index=0}
lighter_orderbook_endpoint = LIGHTER_BASE_URL + "/order_book_details"  # adjust per actual API spec
pair = "EURUSD"  # example — change to actual Lighter pair symbol

# External FX index API (historical rates)
# We'll use https://api.exchangerate.host timeseries endpoint (free plan) :contentReference[oaicite:1]{index=1}
fx_index_api_url = "https://api.exchangerate.host/timeseries"

# External crypto‑FX (e.g. stablecoin FX) prices via a CEX — example: Binance
# Binance historical klines endpoint (spot) :contentReference[oaicite:2]{index=2}
binance_klines_url = "https://api.binance.com/api/v3/klines"
cex_symbol = "EURUSDT"  # example: EUR/USDT as proxy for EUR/USD in crypto markets

start_date = "2025-11-01"
end_date = "2025-11-05"
snapshot_interval_min = 10  # 10‑minute snapshots

# --- FUNCTIONS ---

def fetch_lighter_orderbook(symbol):
    params = {"ticker": symbol}
    r = requests.get(lighter_orderbook_endpoint, params=params)
    r.raise_for_status()
    data = r.json()
    bids = data.get("bids", [])
    asks = data.get("asks", [])
    return bids, asks

def compute_impact_price(bids, asks):
    bid_prices = [b[0] for b in bids] if bids else []
    ask_prices = [a[0] for a in asks] if asks else []
    if not bid_prices or not ask_prices:
        return None
    return (max(bid_prices) + min(ask_prices)) / 2

def fetch_fx_index(start, end, base="USD", symbols="EUR"):
    params = {
        "start_date": start,
        "end_date": end,
        "base": base,
        "symbols": symbols
    }
    r = requests.get(fx_index_api_url, params=params)
    r.raise_for_status()
    data = r.json()
    # data["rates"] is a dict keyed by date (YYYY-MM-DD)
    return {date: info.get(symbols) for date, info in data.get("rates", {}).items()}

def fetch_cex_prices(start_ts_ms, end_ts_ms, symbol, interval="1h"):
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_ts_ms,
        "endTime": end_ts_ms,
        "limit": 1000
    }
    r = requests.get(binance_klines_url, params=params)
    r.raise_for_status()
    data = r.json()
    prices = {}
    for d in data:
        ts = datetime.utcfromtimestamp(d[0]/1000).replace(tzinfo=timezone.utc)
        prices[ts.strftime("%Y-%m-%d %H:%M:%S")] = float(d[4])  # closing price
    return prices

# --- MAIN SCRIPT ---
timestamps = pd.date_range(start=start_date, end=end_date, freq=f"{snapshot_interval_min}min")
fx_index = fetch_fx_index(start_date, end_date, base="USD", symbols="EUR")
cex_prices = fetch_cex_prices(
    int(datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc).timestamp()*1000),
    int(datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc).timestamp()*1000),
    cex_symbol,
    interval="1h"
)

records = []
for ts in timestamps:
    bids, asks = fetch_lighter_orderbook(pair)
    if not bids or not asks:
        continue
    impact_price = compute_impact_price(bids, asks)
    index_price = fx_index.get(ts.strftime("%Y-%m-%d"))
    external_price = cex_prices.get(ts.strftime("%Y-%m-%d %H:%M:%S"))
    mark_price = np.nanmean([p for p in [impact_price, index_price, external_price] if p is not None])
    records.append({
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "impact_price": impact_price,
        "index_price": index_price,
        "external_price": external_price,
        "synthetic_mark": mark_price
    })

df = pd.DataFrame(records)
df.to_csv("lighter_proxy_mark_prices.csv", index=False)
print("Saved proxy mark price dataset.")
