import os, asyncio, logging, json
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional, Dict

import aiohttp
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configs
BASE = "https://mainnet.zklighter.elliot.ai"
TARGET_SYMBOL = "EURUSD"  # The symbol you want
SAMPLE_INTERVAL = 10      # Seconds between requests
OUT_CSV = "lighter_data.csv"

class REST:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self

    async def __aexit__(self, *args):
        await self.session.close()

    async def get(self, path):
        url = f"{self.base}{path}"
        for _ in range(3):
            try:
                async with self.session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        logger.warning(f"GET {url} -> {resp.status}")
                        # If 400, strictly return None to avoid loops
                        if resp.status == 400: return None
            except Exception as e:
                logger.warning(f"GET {url} error {e}")
            await asyncio.sleep(0.5)
        return None

    async def order_books(self):
        return await self.get("/api/v1/orderBooks")

    async def order_book_orders(self, market_id):
        # FIX: Endpoint uses 'market_id' and requires 'limit'
        return await self.get(f"/api/v1/orderBookOrders?market_id={market_id}&limit=100")

class Fetcher:
    def __init__(self, base: str = BASE):
        self.rest = REST(base)

    async def __aenter__(self):
        await self.rest.__aenter__()
        return self

    async def __aexit__(self, *args):
        await self.rest.__aexit__(*args)

    async def find_market_id(self, symbol_hint: str) -> Optional[int]:
        """Finds the integer market_id for a given symbol string."""
        data = await self.rest.order_books()
        if not data:
            logger.error("Failed to fetch orderbook metadata.")
            return None
            
        # Handle API response wrapper
        books = data.get('orderBooks') or data.get('order_books') or []
        if isinstance(books, list):
            for b in books:
                s = b.get("symbol", "").upper()
                if symbol_hint.upper() in s:
                    mid = b.get("market_id")
                    logger.info(f"Found {s} -> ID: {mid}")
                    return int(mid)
        
        logger.error(f"Market {symbol_hint} not found in metadata.")
        return None

    def parse_levels(self, orders: List[Dict]):
        """Parses a list of orders (bids or asks) from Lighter format."""
        levels = []
        for o in orders:
            try:
                # Lighter returns price/amount as strings
                p = float(o.get("price", 0))
                s = float(o.get("remaining_base_amount") or o.get("size") or 0)
                if p > 0 and s > 0:
                    levels.append((p, s))
            except:
                continue
        return levels

    def impact_price(self, bids, asks, notional=100_000):
        def consume(levels):
            rem = notional
            cost = 0.0
            base = 0.0
            for price, size in levels:
                if rem <= 0: break
                take = min(rem, price * size)
                cost += take
                base += take / price
                rem -= take
            return cost / base if base > 0 and rem < notional * 0.01 else None

        ib = consume(bids)
        ia = consume(asks)
        if ib and ia: return (ib + ia)/2
        if bids and asks: return (bids[0][0] + asks[0][0]) / 2
        return None

    async def sample(self, market_id: int, minutes=5):
        logger.info(f"Starting sampling for Market ID {market_id}...")
        end = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        rows = []
        
        while datetime.now(timezone.utc) < end:
            ts = datetime.now(timezone.utc)
            data = await self.rest.order_book_orders(market_id)
            
            if data:
                # Lighter separates them into 'asks' and 'bids' keys
                raw_asks = data.get("asks", [])
                raw_bids = data.get("bids", [])
                
                asks = self.parse_levels(raw_asks)
                bids = self.parse_levels(raw_bids)
                
                # Sort: Bids Descending, Asks Ascending
                bids.sort(key=lambda x: -x[0])
                asks.sort(key=lambda x: x[0])

                if bids and asks:
                    best_bid = bids[0][0]
                    best_ask = asks[0][0]
                    mid = (best_bid + best_ask) / 2
                    
                    row = {
                        "timestamp": ts.isoformat(),
                        "market_id": market_id,
                        "best_bid": best_bid,
                        "best_ask": best_ask,
                        "mid_price": mid,
                        "spread_bps": ((best_ask - best_bid) / mid) * 10000,
                        "impact_price": self.impact_price(bids, asks)
                    }
                    rows.append(row)
                    logger.info(f"Tick {ts.strftime('%H:%M:%S')} | Mid: {mid:.5f} | Spread: {row['spread_bps']:.2f} bps")
                else:
                    logger.warning("Empty orderbook (no bids/asks)")
            else:
                logger.warning("Failed to fetch orderbook state")

            await asyncio.sleep(SAMPLE_INTERVAL)
            
        return pd.DataFrame(rows)

async def main():
    async with Fetcher() as f:
        # 1. Get correct integer ID
        mid = await f.find_market_id(TARGET_SYMBOL)
        if mid is None:
            return

        # 2. Start sampling
        df = await f.sample(mid, minutes=10) # Runs for 10 mins
        
        # 3. Save
        if not df.empty:
            df.to_csv(OUT_CSV, index=False)
            logger.info(f"Success! Saved {len(df)} rows to {OUT_CSV}")
        else:
            logger.error("No data collected.")

if __name__ == "__main__":
    asyncio.run(main())