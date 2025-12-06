# Lighter FX Weekend Pricing Analysis

## Overview
This project analyzes Lighter FX weekend pricing mechanisms to understand how they maintain price feeds during traditional FX market closures (Friday 22:00 GMT to Sunday 22:00 GMT).

## Key Analysis Components

### 1. Data Collection
- **Lighter FX Data**: Weekend pricing data from Lighter protocol
- **Spot FX Control**: Traditional FX rates from Yahoo Finance
- **Crypto Data**: BTC rates for triangular arbitrage analysis

### 2. Core Research Questions
- How does Lighter maintain FX prices during weekends?
- Do they use crypto-implied FX rates (triangular arbitrage)?
- What triggers price updates (volume thresholds, trade sizes)?
- Is there time-dependent decay in pricing accuracy?
- How do they respond to significant events during market closures?

### 3. Analysis Methods
- **Triangular Arbitrage**: BTC/USD ÷ BTC/EUR = Implied EUR/USD
- **Volume Correlation**: Price changes vs trading volume analysis
- **Time Decay Modeling**: Exponential and linear decay fitting
- **Event Response**: Weekend event impact detection

## Files
- `lighter-fx.ipynb`: Main analysis notebook (16 cells)
- `lighter_assessment_data.csv`: Lighter FX weekend data
- `spot_fx_control_data.csv`: Traditional spot FX data
- `requirements.txt`: Python dependencies

## Key Findings
1. **Triangular Arbitrage Confirmation**: [Execute cells to populate]
2. **Volume-Price Correlations**: [Execute cells to populate] 
3. **Time-Dependent Decay**: [Execute cells to populate]
4. **Event-Driven Responses**: [Execute cells to populate]

## Usage
1. Install dependencies: `pip install -r requirements.txt`
2. Open `lighter-fx.ipynb` in Jupyter/VS Code
3. Execute all cells in sequence (1-16)
4. Review generated visualizations and analysis results

## Dependencies
- pandas
- numpy
- matplotlib
- seaborn
- yfinance
- requests
- scipy
- scikit-learn

## Output
- Comprehensive analysis charts (PNG format)
- Statistical correlations and model fits
- Professional quant research conclusions