# Data Schema Documentation

## Overview

The Whale Analytics System collects and stores multiple types of data for comprehensive market analysis. Data is stored in both CSV files for portability and InfluxDB for time-series analysis.

## Data Flow Architecture

```
Binance WebSocket → Whale Monitor → Data Processing → Storage
                                                      ├── CSV Files
                                                      ├── InfluxDB
                                                      └── Redis (cache)
```

## CSV Data Formats

### 1. Whale Orders (`SYMBOL_whales_YYYY-MM-DD_HH.csv`)

Records every whale order detected in the order book.

| Column | Type | Description |
|--------|------|-------------|
| timestamp | datetime | When the whale order was detected |
| symbol | string | Trading pair (e.g., BTCUSDT) |
| side | string | Order side (bid/ask) |
| price | float | Order price |
| quantity | float | Order size in base currency |
| value_usd | float | USD value of the order |
| distance_from_mid_bps | float | Distance from mid price in basis points |
| is_mega_whale | boolean | True if order exceeds mega whale threshold |
| update_id | integer | Order book update ID |
| order_hash | string | Unique identifier for tracking |

### 2. Price Data (`SYMBOL_prices_YYYY-MM-DD_HH.csv`)

Market prices and liquidity metrics captured every second.

| Column | Type | Description |
|--------|------|-------------|
| timestamp | datetime | Data capture time |
| symbol | string | Trading pair |
| mid_price | float | Middle price between best bid/ask |
| best_bid | float | Best bid price |
| best_ask | float | Best ask price |
| spread_usd | float | Spread in USD |
| spread_bps | float | Spread in basis points |
| bid_liquidity_1pct | float | Bid liquidity within 1% of mid |
| ask_liquidity_1pct | float | Ask liquidity within 1% of mid |
| bid_whale_count | integer | Number of whale orders on bid side |
| ask_whale_count | integer | Number of whale orders on ask side |
| bid_whale_value | float | Total USD value of bid whales |
| ask_whale_value | float | Total USD value of ask whales |
| liquidity_imbalance | float | Bid/ask liquidity ratio (-1 to 1) |
| whale_imbalance | float | Bid/ask whale value ratio (-1 to 1) |
| market_pressure | string | Market pressure (bullish/bearish/neutral) |

### 3. Spoofing Events (`SYMBOL_spoofing_YYYY-MM-DD_HH.csv`)

Detected market manipulation attempts.

| Column | Type | Description |
|--------|------|-------------|
| timestamp | datetime | When spoofing was detected |
| symbol | string | Trading pair |
| side | string | Order side (bid/ask) |
| price | float | Spoofed order price |
| original_quantity | float | Original order size |
| value_usd | float | USD value of spoofed order |
| appeared_at | datetime | When order first appeared |
| disappeared_at | datetime | When order disappeared |
| lifetime_seconds | integer | How long order existed |
| distance_from_mid_bps | float | Distance from mid price |
| confidence_score | float | Confidence this was spoofing (0-1) |
| pattern_type | string | Type of manipulation pattern |

### 4. Order Book Snapshots (`SYMBOL_snapshots_YYYY-MM-DD_HH.csv`)

Periodic full order book state captures.

| Column | Type | Description |
|--------|------|-------------|
| timestamp | datetime | Snapshot time |
| symbol | string | Trading pair |
| update_id | integer | Order book update ID |
| best_bid | float | Best bid price |
| best_ask | float | Best ask price |
| mid_price | float | Middle price |
| spread_bps | float | Spread in basis points |
| bid_depth_5 | float | Total bid volume (top 5 levels) |
| ask_depth_5 | float | Total ask volume (top 5 levels) |
| bid_depth_20 | float | Total bid volume (top 20 levels) |
| ask_depth_20 | float | Total ask volume (top 20 levels) |
| bid_orders | json | Array of bid orders |
| ask_orders | json | Array of ask orders |

## InfluxDB Measurements

### Measurement: `whale_order`

**Purpose**: Track individual whale orders in real-time.

**Tags**:
- `symbol`: Trading pair
- `side`: bid/ask
- `order_id`: Unique identifier

**Fields**:
- `price`: Order price (float)
- `quantity`: Order size (float)
- `value_usd`: USD value (float)
- `distance_from_mid_bps`: Distance from mid (float)
- `is_mega_whale`: Mega whale flag (boolean)

**Retention**: 30 days

### Measurement: `price_data`

**Purpose**: Store market price and liquidity metrics.

**Tags**:
- `symbol`: Trading pair

**Fields**:
- All price metrics (floats)
- Liquidity metrics (floats)
- Whale counts (integers)
- Market pressure (string)

**Retention**: 30 days

### Measurement: `manipulation_event`

**Purpose**: Record detected manipulation events.

**Tags**:
- `symbol`: Trading pair
- `type`: Manipulation type
- `side`: Affected side

**Fields**:
- `confidence`: Detection confidence (float)
- `order_value_usd`: Manipulative order value (float)
- `duration_seconds`: Event duration (integer)
- `description`: Event description (string)

**Retention**: 30 days

## Redis Cache Schema

### Key Patterns

```
whale:SYMBOL:SIDE:PRICE     → Whale order data (TTL: 5 minutes)
price:SYMBOL                → Latest price data (TTL: 10 seconds)
spoof:SYMBOL:HASH           → Spoofing detection (TTL: 1 hour)
snapshot:SYMBOL             → Latest order book (TTL: 30 seconds)
```

### Data Structures

**Whale Order (Hash)**:
```redis
HSET whale:BTCUSDT:bid:98500 
  price 98500
  quantity 10.5
  value_usd 1034250
  timestamp 1642345678
  is_mega true
```

**Price Data (Hash)**:
```redis
HSET price:BTCUSDT
  mid_price 98750
  spread_bps 2.5
  bid_whales 3
  ask_whales 2
  pressure bullish
```

## Data Quality Metrics

### Completeness Checks
- Order book update gaps tracked
- Missing price data intervals logged
- Whale order lifecycle completion verified

### Accuracy Validation
- Price sanity checks (±50% from previous)
- Volume consistency validation
- Timestamp sequence verification

### Performance Metrics
- Data ingestion rate: ~1000 records/second
- Storage growth: ~100MB/day per pair
- Query response time: <100ms for recent data

## Data Access Patterns

### Real-time Queries
```python
# Get latest whale orders
SELECT * FROM whale_order 
WHERE symbol = 'BTCUSDT' 
AND time > now() - 1m
```

### Historical Analysis
```python
# Daily whale activity summary
SELECT 
  date_trunc('day', timestamp) as day,
  count(*) as whale_count,
  sum(value_usd) as total_volume
FROM whale_orders
WHERE symbol = 'BTCUSDT'
AND timestamp > now() - 7d
GROUP BY day
```

### Pattern Detection
```python
# Find potential spoofing
SELECT * FROM spoofing_events
WHERE confidence_score > 0.8
AND lifetime_seconds < 60
AND value_usd > 100000
```

## Data Lifecycle

### Collection Phase
1. WebSocket receives order book updates (100ms intervals)
2. Whale orders identified and tracked
3. Price data aggregated every second
4. Spoofing patterns detected in real-time

### Storage Phase
1. **Immediate**: Whale orders written to InfluxDB
2. **1 second**: Price data batched and written
3. **5 minutes**: Spoofing analysis completed
4. **1 hour**: CSV files rotated

### Retention Phase
- **CSV Files**: Kept indefinitely (manual cleanup)
- **InfluxDB**: 30-day retention (configurable)
- **Redis Cache**: 5 minutes to 1 hour (by data type)

## Performance Optimization

### Indexing Strategy
- InfluxDB: Automatic time-series indexing
- CSV: Hourly file rotation for manageable sizes
- Redis: Key expiration for automatic cleanup

### Query Optimization
1. Always include time ranges
2. Use symbol filters early
3. Aggregate before downloading
4. Cache frequently accessed data

### Storage Optimization
- CSV compression after 24 hours
- InfluxDB downsampling for old data
- Redis memory limits enforced

## Data Export Formats

### JSON Export
```json
{
  "timestamp": "2024-01-15T14:30:00Z",
  "symbol": "BTCUSDT",
  "whale_orders": [...],
  "price_data": {...},
  "spoofing_events": [...]
}
```

### Parquet Export
- Columnar format for analytics
- 10x compression vs CSV
- Faster query performance

### API Response Format
```json
{
  "success": true,
  "data": {
    "whales": [...],
    "metrics": {...}
  },
  "timestamp": "2024-01-15T14:30:00Z"
}
```

## Data Validation Rules

### Whale Orders
- `value_usd` must exceed whale threshold
- `price` within 50% of current market
- `quantity` > 0
- `distance_from_mid_bps` < 10000 (100%)

### Price Data
- `spread_bps` >= 0
- `mid_price` = (best_bid + best_ask) / 2
- Liquidity metrics >= 0
- Imbalance ratios between -1 and 1

### Spoofing Events
- `lifetime_seconds` > 0
- `confidence_score` between 0 and 1
- `disappeared_at` > `appeared_at`
- `value_usd` > whale threshold

## Error Handling

### Missing Data
- Gap detection in update IDs
- Automatic reconnection on disconnect
- Backfill from alternative sources

### Invalid Data
- Validation before storage
- Quarantine suspicious records
- Alert on repeated failures

### Recovery Procedures
1. Identify gap in data
2. Check backup sources
3. Attempt recovery from Redis
4. Mark as missing if unrecoverable

## Future Enhancements

### Planned Schema Updates
- Order flow toxicity metrics
- Cross-exchange arbitrage data
- Social sentiment correlation
- On-chain data integration

### Performance Improvements
- Implement data partitioning
- Add read replicas for queries
- Optimize aggregation queries
- Implement smart caching

### Additional Data Sources
- Multiple exchange integration
- DEX liquidity pools
- Options flow data
- Funding rates