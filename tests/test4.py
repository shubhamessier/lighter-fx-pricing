import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging

# --- CONFIGURATION ---
OUTPUT_FILE = "spot_fx_control_data.csv"
DAYS_TO_FETCH = 30
INTERVAL = "5m"  # Yahoo allows 5m resolution for the last 60 days

# MAPPING: Assignment Pair -> Yahoo Ticker
# Note: Yahoo provides USD/JPY (JPY=X). 
# You must invert this price (1/Price) during analysis to get JPY/USD.
TICKERS = {
    "EURUSD=X": "EURUSD",
    "GBPUSD=X": "GBPUSD",
    "JPY=X":    "USDJPY" 
}
# ---------------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_assignment_spot_data():
    logger.info(f"Fetching Spot FX data for {list(TICKERS.values())}...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=DAYS_TO_FETCH)

    # Download data
    raw_data = yf.download(
        list(TICKERS.keys()), 
        start=start_date, 
        end=end_date, 
        interval=INTERVAL, 
        group_by='ticker',
        progress=True
    )

    if raw_data.empty:
        logger.error("No data returned from Yahoo Finance.")
        return

    all_rows = []

    # Process each ticker
    for yahoo_symbol, clean_name in TICKERS.items():
        try:
            # Handle multi-index dataframe from yfinance
            if len(TICKERS) > 1:
                df = raw_data[yahoo_symbol][['Close']].copy()
            else:
                df = raw_data[['Close']].copy()

            df.columns = ['close']
            df['symbol'] = clean_name
            
            # Reset index to make Timestamp a column
            df = df.reset_index()
            
            # Standardize Timestamp column name
            if 'Datetime' in df.columns:
                df.rename(columns={'Datetime': 'timestamp_iso'}, inplace=True)
            elif 'Date' in df.columns:
                df.rename(columns={'Date': 'timestamp_iso'}, inplace=True)

            # Ensure UTC
            if df['timestamp_iso'].dt.tz is None:
                df['timestamp_iso'] = df['timestamp_iso'].dt.tz_localize('UTC')
            else:
                df['timestamp_iso'] = df['timestamp_iso'].dt.tz_convert('UTC')

            # Create Unix Timestamp (milliseconds) for matching with Lighter
            df['timestamp_unix_ms'] = df['timestamp_iso'].astype('int64') // 10**6
            
            all_rows.append(df)
            
        except KeyError as e:
            logger.warning(f"Could not process {yahoo_symbol}: {e}")

    # Combine all into one DataFrame
    final_df = pd.concat(all_rows)
    
    # Sort
    final_df.sort_values(by=['symbol', 'timestamp_unix_ms'], inplace=True)

    # Save
    final_df.to_csv(OUTPUT_FILE, index=False)
    
    logger.info("-" * 40)
    logger.info(f"✔ SUCCESS: Saved {len(final_df)} rows to {OUTPUT_FILE}")
    logger.info("  Included: EURUSD, GBPUSD, USDJPY")
    logger.info("  Note: Remember that Spot markets close on weekends (Fri 22:00 - Sun 21:00 UTC).")
    logger.info("        Gaps in this file during weekends are EXPECTED and CORRECT.")
    logger.info("-" * 40)

if __name__ == "__main__":
    fetch_assignment_spot_data()