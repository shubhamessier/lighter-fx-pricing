# filename: test_pyth_fetch.py

import requests
import json
import pandas as pd
from datetime import datetime, timedelta

# ------------- CONFIGURATION -------------
PYTH_BASE = "https://benchmarks.pyth.network/v1/shims/tradingview"
HISTORY_URL = PYTH_BASE + "/history"

# Tickers you want to test
SYMBOLS = {
    "EURUSD": "FX.EUR/USD",
    "BTCUSD": "Crypto.BTC/USD",
    "BTCEUR": "Crypto.BTC/EUR"
}

# Time range for history — adjust as needed
END = datetime.utcnow()
START = END - timedelta(days=7)  # last 7 days

# ------------ FUNCTIONS ------------

def fetch_history(symbol, t_from, t_to, resolution="5"):
    """Fetch history for a Pyth symbol; return raw JSON or raise."""
    params = {
        "symbol": symbol,
        "resolution": resolution,
        "from": t_from,
        "to": t_to
    }
    resp = requests.get(HISTORY_URL, params=params, timeout=(5, 30))
    resp.raise_for_status()
    return resp.json()

def test_symbol(internal_name, sym):
    print(f"\n▶ Testing {internal_name} → {sym}")
    t_from = int(START.timestamp())
    t_to = int(END.timestamp())
    try:
        result = fetch_history(sym, t_from, t_to)
    except Exception as e:
        print(f"   ❌ HTTP or network error for {sym}: {e}")
        return None

    fname = f"history_{sym.replace('/', '_')}.json"
    with open(fname, "w") as f:
        json.dump(result, f, indent=2)
    print(f"   📥 Response dumped to {fname}")

    status = result.get("s")
    if status != "ok":
        print(f"   ⚠️ Pyth returned status: {status}")
        return None

    times = result.get("t")
    closes = result.get("c")
    if not times or not closes:
        print("   ⚠️ Missing 't' or 'c' in response — no usable data")
        return None

    df = pd.DataFrame({
        "timestamp": pd.to_datetime(times, unit="s", utc=True),
        internal_name: closes
    }).set_index("timestamp")

    print(f"   ✅ Success: fetched {len(df)} rows; first rows:\n{df.head()}")
    return df

def main():
    print("=== Pyth Fetch Test ===")
    for name, sym in SYMBOLS.items():
        df = test_symbol(name, sym)
        if df is None:
            print(f"   → {sym} failed or no data.\n")
        else:
            print(f"   → {sym} OK. Time range: {df.index.min()} to {df.index.max()}\n")

if __name__ == "__main__":
    main()
