import asyncio
import aiohttp
import logging
import json

# Configuration
BASE_URL = "https://mainnet.zklighter.elliot.ai"
OUTPUT_FILE = "lighter_market_ids.json"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def fetch_all_markets():
    url = f"{BASE_URL}/api/v1/orderBooks"
    
    async with aiohttp.ClientSession() as session:
        try:
            logger.info(f"Connecting to {url}...")
            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.error(f"Failed to fetch: HTTP {resp.status}")
                    text = await resp.text()
                    logger.error(f"Response: {text}")
                    return

                data = await resp.json()
                
                # Handle potential variations in API response keys
                books = data.get('orderBooks') or data.get('order_books') or []
                
                if not books:
                    logger.warning("No order books found in response.")
                    return

                logger.info(f"Successfully retrieved {len(books)} markets.")
                logger.info("-" * 40)
                logger.info(f"{'MARKET ID':<10} | {'SYMBOL':<20} | {'PRICE (approx)'}")
                logger.info("-" * 40)

                clean_list = []

                for b in books:
                    m_id = b.get('market_id')
                    symbol = b.get('symbol')
                    
                    # Sometimes simple APIs nest details, so let's try to grab a price if available
                    # to help identify what the asset actually is (e.g. is it 100k or 1.0?)
                    best_ask = b.get('best_ask_price', 'N/A')
                    
                    row = {
                        "id": m_id,
                        "symbol": symbol,
                        "raw_data": b  # keeping raw data in JSON just in case
                    }
                    clean_list.append(row)
                    
                    print(f"{str(m_id):<10} | {str(symbol):<20} | {str(best_ask)}")

                # Save to file for easy copy-pasting
                with open(OUTPUT_FILE, 'w') as f:
                    json.dump(clean_list, f, indent=2)
                
                logger.info("-" * 40)
                logger.info(f"Full dump saved to {OUTPUT_FILE}")

        except Exception as e:
            logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(fetch_all_markets())