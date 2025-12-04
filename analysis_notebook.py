import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.formula.api as smf
import logging

# --- Configuration ---
DB_PATH = "lighter_fx_data.db"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_data():
    """Loads data from SQLite and converts timestamps."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM market_data", conn)
    conn.close()
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)
    return df

def fetch_external_spot_data(start_time, end_time):
    """
    Fetches external spot data.
    TODO: Replace with actual API call (e.g., OANDA, Yahoo Finance).
    Returns a DataFrame with a DatetimeIndex and a 'external_spot' column.
    """
    logging.info("Fetching external spot data (Mock)...")
    # Mock data generation for demonstration
    dates = pd.date_range(start=start_time, end=end_time, freq='10S')
    # Random walk for mock spot price
    prices = 1.05 + np.random.randn(len(dates)).cumsum() * 0.0001 
    external_df = pd.DataFrame({'external_spot': prices}, index=dates)
    return external_df

def align_data(lighter_df, external_df):
    """Aligns Lighter data with external spot data using merge_asof."""
    # Ensure both are sorted
    lighter_df = lighter_df.sort_index()
    external_df = external_df.sort_index()
    
    merged_df = pd.merge_asof(
        lighter_df, 
        external_df, 
        left_index=True, 
        right_index=True, 
        direction='nearest',
        tolerance=pd.Timedelta('1min') # Optional: don't match if too far apart
    )
    return merged_df

def analyze_drift(df):
    """Computes drift and lag variables."""
    df['drift_mark_vs_spot'] = df['mark_price'] - df['external_spot']
    df['drift_lag_1'] = df['drift_mark_vs_spot'].shift(1)
    df['deviation_pct'] = (df['mark_price'] / df['oracle_price']) - 1
    return df.dropna()

def statistical_analysis(df):
    """Performs clamp detection and AR(1) modeling."""
    # 1. Clamp Boundary Detection
    upper_bound = df['deviation_pct'].quantile(0.99)
    lower_bound = df['deviation_pct'].quantile(0.01)
    logging.info(f"Clamp Bounds (1st/99th percentile): {lower_bound:.6f} / {upper_bound:.6f}")

    # 2. Mean-Reversion Analysis (AR(1))
    model = smf.ols('drift_mark_vs_spot ~ drift_lag_1', data=df).fit()
    print(model.summary())
    
    phi = model.params['drift_lag_1']
    logging.info(f"AR(1) Coefficient (phi): {phi:.6f}")
    
    if 0 < phi < 1:
        # Assuming interval is approx 10s (based on polling)
        # Calculate average interval from data to be precise
        avg_interval = df.index.to_series().diff().mean().total_seconds()
        half_life = (np.log(0.5) / np.log(phi)) * avg_interval
        logging.info(f"Half-Life: {half_life:.2f} seconds")
    else:
        logging.warning("Mean reversion not confirmed (phi not in (0, 1))")

    return model

def plot_results(df):
    """Generates visualizations."""
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['deviation_pct'], label='Deviation %')
    
    upper_bound = df['deviation_pct'].quantile(0.99)
    lower_bound = df['deviation_pct'].quantile(0.01)
    plt.axhline(upper_bound, color='r', linestyle='--', label='99th Percentile')
    plt.axhline(lower_bound, color='r', linestyle='--', label='1st Percentile')
    
    plt.title('Mark Price Deviation from Oracle')
    plt.legend()
    plt.show()

def main():
    try:
        logging.info("Loading Lighter data...")
        lighter_df = load_data()
        
        if lighter_df.empty:
            logging.warning("No data found in database. Run data_collector.py first.")
            return

        logging.info(f"Loaded {len(lighter_df)} records.")
        
        # Fetch external data covering the same range
        start_time = lighter_df.index.min()
        end_time = lighter_df.index.max()
        external_df = fetch_external_spot_data(start_time, end_time)
        
        logging.info("Aligning data...")
        df = align_data(lighter_df, external_df)
        
        logging.info("Analyzing drift...")
        df = analyze_drift(df)
        
        logging.info("Running statistical analysis...")
        statistical_analysis(df)
        
        logging.info("Plotting results...")
        plot_results(df)
        
    except Exception as e:
        logging.error(f"Analysis failed: {e}")

if __name__ == "__main__":
    main()
