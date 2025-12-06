import os
import asyncio
import logging
import pandas as pd
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict

# --- CONFIGURATION ---
BASE_URL = "https://mainnet.zklighter.elliot.ai"

# UPDATED SYMBOLS based on your API dump:
TARGET_SYMBOLS = [
    "EURUSD",  # ID 96
    "GBPUSD",  # ID 97
    "USDJPY",  # ID 98 (Note: API uses USDJPY, you may need to invert this for JPY/USD analysis)
    "BTC",     # ID 1  (API uses 'BTC', not 'BTCUSD')
    "ETH"      # ID 0  (API uses 'ETH', not 'ETHUSD')
]

OUTPUT_FILE = "lighter_assessment_data.csv"
RESOLUTION = "1m"  # High fidelity for detecting 1-minute clamps/drifts
DAYS_TO_FETCH = 30 # Fetch last 30 days to capture ~4 weekends
# ---------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LighterDataMiner:
    def __init__(self):
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        await self.session.close()

    async def get_market_map(self) -> Dict[str, int]:
        """Fetches all markets and maps Symbol -> MarketID"""
        url = f"{BASE_URL}/api/v1/orderBooks"
        market_map = {}
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    logger.error(f"Metadata Fetch Failed: {resp.status}")
                    return {}
                data = await resp.json()
                books = data.get('orderBooks') or data.get('order_books') or []
                
                logger.info("--- Available Markets on Lighter ---")
                for b in books:
                    # API returns clean symbols like 'BTC', 'EURUSD'
                    s = b.get('symbol', '') 
                    m_id = b.get('market_id')
                    
                    market_map[s] = int(m_id)
                    
                    if s in TARGET_SYMBOLS:
                        logger.info(f"✔ Found Target: {s} -> ID: {m_id}")
                return market_map
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return {}

    async def fetch_candles_chunk(self, market_id: int, start_ms: int, end_ms: int, count_back: int = 4000):
        """Fetches a single chunk of candles"""
        url = f"{BASE_URL}/api/v1/candlesticks"
        params = {
            "market_id": market_id,
            "resolution": RESOLUTION,
            "start_timestamp": start_ms,
            "end_timestamp": end_ms,
            "count_back": count_back
        }
        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('candlesticks', [])
                else:
                    logger.warning(f"Chunk failed {resp.status} for ID {market_id}")
                    return []
        except Exception as e:
            logger.error(f"Request Error: {e}")
            return []

    async def get_historical_data(self, symbol: str, market_id: int, start_dt: datetime, end_dt: datetime):
        """
        Iteratively fetches data to ensure we cover the whole time range 
        (since APIs usually limit candles per request).
        """
        all_candles = []
        current_end_dt = end_dt
        
        logger.info(f"Processing {symbol} (ID: {market_id})...")

        # Loop backwards from end_dt to start_dt
        while current_end_dt > start_dt:
            current_end_ms = int(current_end_dt.timestamp() * 1000)
            target_start_ms = int(start_dt.timestamp() * 1000)
            
            # Fetch a batch
            candles = await self.fetch_candles_chunk(market_id, target_start_ms, current_end_ms)
            
            if not candles:
                break

            all_candles.extend(candles)
            
            # Find the earliest timestamp in this batch to set as the new end point
            earliest_ts = min(c['timestamp'] for c in candles)
            earliest_dt = datetime.fromtimestamp(earliest_ts / 1000, timezone.utc)
            
            # If we aren't moving back in time, break to avoid infinite loop
            if earliest_dt >= current_end_dt:
                break
                
            current_end_dt = earliest_dt - timedelta(seconds=1)
            # small sleep to be nice to API
            await asyncio.sleep(0.1) 

        # Parse and formatting
        parsed = []
        for c in all_candles:
            ts = c.get('timestamp')
            if not ts: continue
            
            parsed.append({
                "symbol": symbol,
                "market_id": market_id,
                "timestamp_unix_ms": int(ts),
                "timestamp_iso": datetime.fromtimestamp(ts / 1000, timezone.utc).isoformat(),
                "open": float(c.get('open', 0)),
                "high": float(c.get('high', 0)),
                "low": float(c.get('low', 0)),
                "close": float(c.get('close', 0)),
                "volume": float(c.get('volume', 0))
            })
        
        return parsed

async def main():
    async with LighterDataMiner() as miner:
        # 1. Get Market IDs
        market_map = await miner.get_market_map()
        
        # 2. Define Time Window (Last X Days)
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=DAYS_TO_FETCH)
        
        all_data = []

        # 3. Fetch data for all targets
        for symbol in TARGET_SYMBOLS:
            if symbol not in market_map:
                logger.warning(f"Skipping {symbol} (Not found in API)")
                continue
            
            m_id = market_map[symbol]
            data = await miner.get_historical_data(symbol, m_id, start_dt, end_dt)
            all_data.extend(data)
            logger.info(f"Fetched {len(data)} candles for {symbol}")

        # 4. Save to CSV
        if all_data:
            df = pd.DataFrame(all_data)
            # Cleanup: sort and remove duplicates
            df.drop_duplicates(subset=['symbol', 'timestamp_unix_ms'], inplace=True)
            df.sort_values(by=['symbol', 'timestamp_unix_ms'], inplace=True)
            
            df.to_csv(OUTPUT_FILE, index=False)
            logger.info("=" * 50)
            logger.info(f"✔ COMPLETED. Saved {len(df)} rows to {OUTPUT_FILE}")
            logger.info("=" * 50)
        else:
            logger.error("No data collected.")

if __name__ == "__main__":
    asyncio.run(main())