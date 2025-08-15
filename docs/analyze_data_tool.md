# Data Analysis Tool Documentation

## Overview

`analyze_data.py` is a command-line tool for analyzing whale and spoofing data collected by the Whale Analytics System.

## Usage

### Basic Commands

```bash
# Analyze specific trading pair
python analyze_data.py SYMBOL [DATE]

# Compare all trading pairs
python analyze_data.py compare [DATE]

# Examples
python analyze_data.py ARBUSDT                    # Today's ARBUSDT data
python analyze_data.py ARBUSDT 2025-08-15        # Specific date
python analyze_data.py compare                    # Compare all pairs today
python analyze_data.py compare 2025-08-15        # Compare all pairs on date
```

## Features

### 1. Single Symbol Analysis

Provides detailed statistics for a specific trading pair:

```bash
python analyze_data.py FETUSDT
```

Output includes:
- **Whale Statistics**
  - Total events detected
  - Unique whale count
  - Events per whale (activity level)
  - Average and maximum USD values
  - Average duration whales stay active

- **Spoofing Statistics**
  - Total spoofing events
  - Unique spoofers
  - Average time orders stay active
  - Flickering event count
  - Disappearance patterns

- **Manipulation Score** (0-100)
  - Calculated from spoof-to-whale ratio
  - Indicates market manipulation level

### 2. Comparative Analysis

Compare manipulation levels across all monitored pairs:

```bash
python analyze_data.py compare
```

Output includes:
- **Manipulation Ranking**: Pairs sorted by manipulation score
- **Event Counts**: Whale and spoofing events per pair
- **Status Indicators**:
  - 🔴 EXTREME (>80 score)
  - 🟠 HIGH (50-80)
  - 🟡 MODERATE (20-50)
  - 🟢 LOW (<20)
- **Aggregate Statistics**: Total events and overall spoof rate

## Metrics Explained

### Manipulation Score

A 0-100 scale indicating market manipulation intensity:

```
Score = (Spoofing Events / Whale Events) * 100
```

- **0-20**: Clean market, minimal manipulation
- **20-50**: Moderate manipulation, trade carefully
- **50-80**: High manipulation, avoid or fade
- **80-100**: Extreme manipulation, do not trade

### Events Per Whale

Average number of events generated per unique whale:

```
Events Per Whale = Total Events / Unique Whales
```

- **<10**: Normal behavior
- **10-50**: Active modifications
- **>50**: Likely algorithmic/spoofing

### Average Duration

How long whale orders remain in the book:

```
Average Duration = Sum(durations) / Count(whales)
```

- **<5 seconds**: Likely spoofing
- **5-30 seconds**: Suspicious
- **>30 seconds**: Probably legitimate

### Flickering Count

Number of orders that repeatedly appear/disappear:

- Indicates automated manipulation
- Higher count = more bot activity
- Common in low-liquidity pairs

## Implementation Details

### Data Sources

Reads CSV files from:
```
data/
├── whales/SYMBOL/SYMBOL_whales_YYYY-MM-DD.csv
├── spoofing/SYMBOL/SYMBOL_spoofing_YYYY-MM-DD.csv
└── snapshots/SYMBOL/SYMBOL_snapshots_YYYY-MM-DD.csv
```

### Key Functions

```python
analyze_symbol_data(symbol, date_str)
# Analyzes single symbol's data
# Returns: dict with whale_stats, spoof_stats, manipulation_score

compare_symbols(date_str)
# Compares all symbols for given date
# Outputs: ranking table and aggregate stats

print_analysis(results)
# Formats and displays analysis results
# Color-coded based on manipulation levels
```

### Dependencies

- Python 3.7+
- pandas
- pathlib (standard library)
- datetime (standard library)

## Interpretation Guide

### Low Manipulation (Score <20)
- Relatively clean market
- Whale orders likely genuine
- Safe for normal trading strategies

### Moderate Manipulation (Score 20-50)
- Some spoofing present
- Exercise caution
- Verify orders before trading

### High Manipulation (Score 50-80)
- Heavy spoofing activity
- Avoid momentum trades
- Consider fade strategies

### Extreme Manipulation (Score >80)
- Market dominated by fake orders
- Do not trade
- Wait for cleaner conditions

## Use Cases

### 1. Pre-Trading Analysis
Run before trading session to assess market conditions:
```bash
python analyze_data.py compare
```

### 2. Post-Event Investigation
Analyze specific events or anomalies:
```bash
python analyze_data.py ARBUSDT 2025-08-15
```

### 3. Strategy Backtesting
Use manipulation scores to filter trading signals:
```python
if manipulation_score < 30:
    execute_trade()
else:
    skip_trade()
```

### 4. Market Research
Track manipulation patterns over time:
```bash
for date in date_range:
    python analyze_data.py compare $date >> research.log
```

## Output Examples

### Single Symbol Output
```
============================================================
📊 Analysis for FETUSDT - 2025-08-15
============================================================

🐋 WHALE STATISTICS:
  Total Events: 867
  Unique Whales: 14
  Events per Whale: 61.9
  Average Value: $36,121
  Max Value: $65,537
  Avg Duration: 4.18 seconds

🚨 SPOOFING STATISTICS:
  Total Spoofs: 141
  Unique Spoofers: 7
  Avg Time Active: 6.88 seconds
  Flickering Events: 141
  Avg Disappearances: 4.5
  Max Disappearances: 15

🎯 MANIPULATION SCORE: 16.3/100
  ✅ LOW MANIPULATION - Relatively clean
```

### Comparative Output
```
🏆 MANIPULATION RANKING (Most to Least):

Symbol     Whale Events    Spoofs     Manipulation    Status
----------------------------------------------------------------------
INJUSDT    155             69         44.5            🟡 MODERATE
ARBUSDT    2,239           407        18.2            🟢 LOW
FETUSDT    867             141        16.3            🟢 LOW
```

## Future Enhancements

- Time-based analysis (hourly patterns)
- Correlation with price movements
- Export to JSON/Excel
- Automated alerts for manipulation spikes
- Historical trend analysis
- Machine learning integration