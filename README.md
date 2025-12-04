# Lighter.xyz FX Pricing Analysis

This project aims to reverse-engineer the weekend pricing mechanism of Lighter.xyz FX perpetuals using historical data from Dune Analytics.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Dune Analytics Setup**:
    -   Create a query on Dune Analytics using the template in `dune_query.sql`.
    -   Get your **API Key** and the **Query ID**.

3.  **Configuration**:
    -   Set your Dune API Key as an environment variable:
        ```bash
        export DUNE_API_KEY="your_api_key_here"
        ```
    -   Open `data_collector.py` and update `DUNE_QUERY_ID` with your query ID.

## Usage

### Phase 1: Data Collection

Run the data collector to fetch historical data from Dune, process it (pivot, forward-fill, resample), and store it in a SQLite database (`lighter_fx_data.db`).

```bash
python data_collector.py
```

### Phase 2 & 3: Analysis

Run the analysis script to process the data, align it with external spot prices, and perform statistical modeling.

```bash
python analysis_notebook.py
```

**Note**: The `fetch_external_spot_data` function in `analysis_notebook.py` currently uses mock data. You should replace this with a real API call (e.g., OANDA, Yahoo Finance) to get accurate external spot prices for the corresponding time period.

## Output

-   **Database**: `lighter_fx_data.db` (SQLite)
-   **Analysis**:
    -   Clamp bounds (1st and 99th percentiles)
    -   AR(1) model summary
    -   Half-life of mean reversion
    -   Plots of price deviation
