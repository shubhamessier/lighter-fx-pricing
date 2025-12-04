import sqlite3
import logging
import pandas as pd
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_PATH = "lighter_fx_data.db"
MARKET = "EURUSD"       # EURUSD, GBPUSD, JPYUSD
START_BLOCK = 110000000
END_BLOCK = 116600000
SLEEP = 0.12
MAX_RETRIES = 3
THREADS = 5  # Parallel fetching

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# --------------------------------------------------
# DB SETUP
# --------------------------------------------------
def setup_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            block_number INTEGER PRIMARY KEY,
            timestamp INTEGER,
            mark_price REAL,
            oracle_price REAL,
            funding_rate REAL,
            clamp REAL,
            open_interest REAL,
            premium REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            trade_id TEXT PRIMARY KEY,
            block_number INTEGER,
            timestamp INTEGER,
            price REAL,
            size REAL,
            side TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orderbook_data (
            block_number INTEGER PRIMARY KEY,
            timestamp INTEGER,
            best_bid REAL,
            best_ask REAL,
            mid_price REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS oracle_updates (
            block_number INTEGER PRIMARY KEY,
            timestamp INTEGER,
            oracle_price REAL,
            source TEXT
        )
    """)
    conn.commit()
    conn.close()
    logging.info("Database initialized.")

# --------------------------------------------------
# LIGHTER API CALLS
# --------------------------------------------------
def get_json(url, retries=MAX_RETRIES):
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                return r.json()
            logging.warning(f"Status {r.status_code} for {url}")
        except Exception as e:
            logging.warning(f"Attempt {attempt+1} failed for {url}: {e}")
        time.sleep(0.5)
    return None

def fetch_block(b):
    return get_json(f"https://app.lighter.xyz/api/blocks/{b}")

def fetch_market_state(b, market=MARKET):
    return get_json(f"https://app.lighter.xyz/api/markets/{market}/{b}")

def fetch_trades(b, market=MARKET):
    return get_json(f"https://app.lighter.xyz/api/markets/{market}/{b}/trades")

def fetch_orderbook(b, market=MARKET):
    return get_json(f"https://app.lighter.xyz/api/markets/{market}/{b}/orderbook")

def fetch_stork_oracle(b, market=MARKET):
    return get_json(f"https://app.lighter.xyz/api/markets/{market}/{b}/oracle")

# --------------------------------------------------
# PARSERS
# --------------------------------------------------
def parse_market_state(block_number, block_data, market_state):
    if not block_data or not market_state:
        return None
    ts = block_data.get("timestamp")
    mark = market_state.get("markPrice")
    oracle = market_state.get("indexPrice")
    funding = market_state.get("fundingRate")
    clamp = market_state.get("clamp")
    oi = market_state.get("openInterest")
    premium = (mark / oracle - 1) if mark and oracle else None
    return (block_number, ts, mark, oracle, funding, clamp, oi, premium)

def parse_trades(block_number, trades):
    if not trades:
        return []
    return [(t.get("id"), block_number, t.get("timestamp"), t.get("price"), t.get("size"), t.get("side")) for t in trades]

def parse_orderbook(block_number, block_data, ob):
    if not ob or not block_data:
        return None
    ts = block_data.get("timestamp")
    bid = ob.get("bestBid")
    ask = ob.get("bestAsk")
    mid = (bid + ask)/2 if bid and ask else None
    return (block_number, ts, bid, ask, mid)

def parse_oracle(block_number, oracle_data, block_data):
    if not oracle_data or not block_data:
        return None
    ts = block_data.get("timestamp")
    price = oracle_data.get("price")
    source = oracle_data.get("source", "stork")
    return (block_number, ts, price, source)

# --------------------------------------------------
# STORE FUNCTIONS
# --------------------------------------------------
def store_row(table, row):
    if not row:
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    placeholders = ",".join(["?"]*len(row))
    cur.execute(f"INSERT OR REPLACE INTO {table} VALUES ({placeholders})", row)
    conn.commit()
    conn.close()

def store_rows(table, rows):
    if not rows:
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    placeholders = ",".join(["?"]*len(rows[0]))
    cur.executemany(f"INSERT OR REPLACE INTO {table} VALUES ({placeholders})", rows)
    conn.commit()
    conn.close()

# --------------------------------------------------
# BLOCK FETCH & STORE
# --------------------------------------------------
def fetch_and_store_block(b):
    logging.info(f"Fetching block {b}")
    blk = fetch_block(b)
    if not blk:
        return
    mkt = fetch_market_state(b)
    trd = fetch_trades(b)
    ob = fetch_orderbook(b)
    ora = fetch_stork_oracle(b)

    store_row("market_data", parse_market_state(b, blk, mkt))
    store_rows("trades", parse_trades(b, trd))
    store_row("orderbook_data", parse_orderbook(b, blk, ob))
    store_row("oracle_updates", parse_oracle(b, ora, blk))
    time.sleep(SLEEP)

# --------------------------------------------------
# MAIN LOOP
# --------------------------------------------------
def main():
    setup_db()
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = [executor.submit(fetch_and_store_block, b) for b in range(START_BLOCK, END_BLOCK+1)]
        for f in as_completed(futures):
            pass  # all logging is inside fetch_and_store_block

if __name__ == "__main__":
    main()
