# Data Collection Guide

## What Data We Collect

The Whale Analytics System captures comprehensive order book data from Binance Futures markets, focusing on large orders (whales) and market manipulation patterns.

## Data Structure

### 1. Whale Orders (`data/whales/SYMBOL/`)

**File Format**: `SYMBOL_whales_YYYY-MM-DD.csv`

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| timestamp | ISO 8601 | When order was detected | 2025-08-15T21:22:50.457289 |
| symbol | string | Trading pair | FETUSDT |
| whale_id | string | Unique tracking identifier | FETUSDT_bid_0_1755278570457 |
| side | string | Order side | bid/ask |
| price | float | Order price | 0.6847 |
| size | float | Order size in base asset | 74142.0 |
| value_usd | float | Total USD value | 50765.67 |
| percentage_of_book | float | % of total book side | 15.67 |
| level | int | Position in order book (0=best) | 3 |
| mid_price | float | Market price at detection | 0.68495 |
| spread_bps | float | Bid-ask spread in basis points | 2.5 |
| total_bid_whales | int | Count of bid whales | 8 |
| total_ask_whales | int | Count of ask whales | 6 |
| bid_depth_1pct | float | Bid liquidity within 1% | 245000.50 |
| ask_depth_1pct | float | Ask liquidity within 1% | 189000.25 |
| volume_imbalance | float | Bid/ask volume ratio | 0.35 |
| duration_seconds | float | How long whale existed | 42.75 |
| size_changes_count | int | Number of size modifications | 3 |
| disappearances | int | Times order vanished/reappeared | 1 |
| is_new | bool | First appearance flag | True |

### 2. Spoofing Events (`data/spoofing/SYMBOL/`)

**File Format**: `SYMBOL_spoofing_YYYY-MM-DD.csv`

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| timestamp | ISO 8601 | When spoofing detected | 2025-08-15T21:22:51.545405 |
| symbol | string | Trading pair | ARBUSDT |
| whale_id | string | Unique identifier | ARBUSDT_bid_0_1755278571006 |
| side | string | Order side | bid/ask |
| price | float | Order price | 0.4732 |
| initial_size | float | Size when first seen | 74142.0 |
| final_size | float | Size when disappeared | 98440.9 |
| initial_value_usd | float | Initial USD value | 35083.99 |
| final_value_usd | float | Final USD value | 46631.45 |
| time_active_seconds | float | Duration before disappearing | 0.428 |
| percentage_of_book | float | % of order book | 4.89 |
| size_changes_count | int | Number of size changes | 3 |
| disappearances | int | Flicker count | 3 |
| max_size_seen | float | Largest size observed | 98440.9 |
| min_size_seen | float | Smallest size observed | 65700.8 |
| size_variance_pct | float | Size variation percentage | 44.16 |
| spoof_pattern | string | Type of manipulation | flickering/single/size_manipulation |

### 3. Market Snapshots (`data/snapshots/SYMBOL/`)

**File Format**: `SYMBOL_snapshots_YYYY-MM-DD.csv`

Periodic market state captured every ~1 minute:

| Field | Type | Description |
|-------|------|-------------|
| timestamp | ISO 8601 | Snapshot time |
| symbol | string | Trading pair |
| mid_price | float | Current market price |
| spread_bps | float | Bid-ask spread |
| total_whale_count | int | Total whales detected |
| bid_whale_count | int | Bid side whales |
| ask_whale_count | int | Ask side whales |
| whale_imbalance | int | Bid whales - Ask whales |
| volume_imbalance | float | Bid/ask volume ratio |
| bid_volume_usd | float | Total bid volume in USD |
| ask_volume_usd | float | Total ask volume in USD |
| bid_depth_1pct | float | Bid depth within 1% |
| ask_depth_1pct | float | Ask depth within 1% |
| largest_bid_whale | float | Largest bid whale USD |
| largest_ask_whale | float | Largest ask whale USD |
| support_level | float | First major support |
| resistance_level | float | First major resistance |

## Data Volume

### Expected Data Rates (Per Symbol)

| Metric | Rate | Daily Volume |
|--------|------|--------------|
| Whale Events | ~100-300/second | 8-25 million |
| Spoofing Events | ~50-150/second | 4-13 million |
| Market Snapshots | 1/minute | 1,440 |
| Raw Size | - | 2-8 GB |
| Compressed Size | - | 200-800 MB |

### Storage Optimization

1. **Daily Rotation**: New files created each day
2. **Compression**: Previous day's files compressed with gzip
3. **Per-Symbol Organization**: Each pair in separate directory
4. **Archive Directory**: Compressed files moved to `data/archive/`

## Data Quality

### Whale Identification

Each whale order is assigned a unique ID using the pattern:
```
{SYMBOL}_{side}_{price_int}_{timestamp_ms}
```

This enables:
- Tracking individual whales over time
- Detecting order modifications
- Identifying spoofing patterns
- Correlating with price movements

### Spoofing Detection Criteria

Orders are flagged as spoofing when:

1. **Classic Spoof**: Large order disappears in 5-60 seconds
2. **Flickering**: Order appears/disappears 3+ times
3. **Size Manipulation**: Size varies by >50%

Additional filters:
- Minimum value: $5M for spoofing alerts
- Must represent >20% of order book side
- Time window: 5-60 seconds (excludes HFT and legitimate orders)

## Data Usage

### Analysis Capabilities

The collected data enables:

1. **Market Microstructure Analysis**
   - Order book dynamics
   - Liquidity patterns
   - Price discovery mechanics

2. **Manipulation Detection**
   - Spoofing patterns
   - Wash trading
   - Stop hunting
   - Pump & dump schemes

3. **Trading Strategy Development**
   - Whale following strategies
   - Fade-the-spoof tactics
   - Liquidity provision optimization

4. **Machine Learning Features**
   - Real vs fake order classification
   - Price movement prediction
   - Manipulation pattern recognition

### Data Access

Files are standard CSV format, compatible with:
- Python (pandas)
- R
- Excel
- PostgreSQL (COPY command)
- Any data analysis tool

## Privacy & Compliance

- No personal data collected
- Only public order book data
- No trader identification
- Compliant with exchange ToS
- Educational and research purposes