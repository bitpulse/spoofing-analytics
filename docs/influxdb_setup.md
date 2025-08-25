# InfluxDB Setup and Usage Guide

## Overview

The Whale Analytics System now includes InfluxDB integration for powerful time-series data storage and analysis. This allows for real-time querying, visualization with Grafana, and long-term data retention.

## Quick Start

### 1. Start InfluxDB with Docker

```bash
# Start InfluxDB container
docker-compose up -d influxdb

# Verify it's running
docker ps | grep influxdb

# Check health status
curl http://localhost:8086/health
```

### 2. Configure Environment Variables

Add to your `.env` file:

```env
# InfluxDB Configuration
INFLUXDB_TOKEN=your_token_here
INFLUXDB_URL=http://localhost:8086
INFLUXDB_ORG=bitpulse
INFLUXDB_BUCKET=whale_analytics
INFLUXDB_ENABLED=true
```

### 3. Test Connection

```bash
# Run the test script
python test_influxdb.py

# Expected output:
# ✓ InfluxDB is pass: ready for queries and writes
# ✓ Successfully wrote whale order data
# ✓ Successfully wrote price data
# ✓ All tests passed!
```

## Data Schema

### 1. whale_order
Individual whale orders detected in the order book.

**Tags:**
- `symbol`: Trading pair (e.g., BTCUSDT)
- `side`: Order side (bid/ask)
- `order_id`: Unique identifier

**Fields:**
- `price`: Order price
- `quantity`: Order size
- `value_usd`: USD value of order
- `distance_from_mid_bps`: Distance from mid price in basis points
- `is_mega_whale`: Boolean flag for mega whale orders

### 2. price_data
Market price and liquidity metrics captured every second.

**Tags:**
- `symbol`: Trading pair

**Fields:**
- `mid_price`: Middle price between best bid/ask
- `best_bid`: Best bid price
- `best_ask`: Best ask price
- `spread_usd`: Spread in USD
- `spread_bps`: Spread in basis points
- `bid_liquidity_1pct`: Bid liquidity within 1% of mid price
- `ask_liquidity_1pct`: Ask liquidity within 1% of mid price
- `bid_whale_count`: Number of whale orders on bid side
- `ask_whale_count`: Number of whale orders on ask side
- `bid_whale_value`: Total USD value of bid whales
- `ask_whale_value`: Total USD value of ask whales
- `liquidity_imbalance`: Ratio of bid vs ask liquidity
- `whale_imbalance`: Ratio of bid vs ask whale value
- `market_pressure`: Market pressure indicator (bullish/bearish/neutral)

### 3. manipulation_event
Detected market manipulation events.

**Tags:**
- `symbol`: Trading pair
- `type`: Type of manipulation (spoofing/layering/wash_trading)
- `side`: Affected side (bid/ask)

**Fields:**
- `confidence`: Confidence score (0-1)
- `order_value_usd`: Value of manipulative order
- `price`: Order price
- `distance_from_mid_bps`: Distance from mid price
- `duration_seconds`: How long the order existed
- `description`: Human-readable description

### 4. order_book_snapshot
Periodic snapshots of order book state.

**Tags:**
- `symbol`: Trading pair

**Fields:**
- `mid_price`: Current mid price
- `spread_bps`: Current spread in basis points
- `bid_depth_20`: Total bid volume (top 20 levels)
- `ask_depth_20`: Total ask volume (top 20 levels)
- `volume_imbalance`: Bid/ask volume imbalance ratio
- `whale_bid_count`: Number of whale orders on bid side
- `whale_ask_count`: Number of whale orders on ask side
- `update_id`: Order book update ID for tracking gaps

### 5. spoofing_detection
Specific instances of detected spoofing.

**Tags:**
- `symbol`: Trading pair
- `side`: Order side (bid/ask)

**Fields:**
- `price`: Spoofed order price
- `original_quantity`: Original order size
- `value_usd`: USD value of spoofed order
- `lifetime_seconds`: How long order existed before disappearing
- `disappeared_at`: Timestamp when order disappeared
- `confidence_score`: Confidence that this was spoofing (0-1)

### 6. market_metrics
Aggregated market health indicators.

**Tags:**
- `symbol`: Trading pair

**Fields:**
- `whale_activity_score`: Overall whale activity level (0-100)
- `manipulation_score`: Market manipulation index (0-100)
- `volatility`: Price volatility metric
- `liquidity_depth`: Overall liquidity depth score
- `order_flow_imbalance`: Order flow imbalance indicator

## Query Examples

### Using InfluxDB CLI

```bash
# Connect to InfluxDB
docker exec -it influxdb influx

# Switch to the bucket
use whale_analytics

# Query recent whale orders
from(bucket: "whale_analytics")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "whale_order")
  |> filter(fn: (r) => r["symbol"] == "BTCUSDT")
  |> filter(fn: (r) => r["_field"] == "value_usd")
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 10)
```

### Using Python

```python
from influxdb_client import InfluxDBClient

client = InfluxDBClient(
    url="http://localhost:8086",
    token="your_token_here",
    org="bitpulse"
)

query_api = client.query_api()

# Get average spread over last hour
query = '''
from(bucket: "whale_analytics")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "price_data")
  |> filter(fn: (r) => r["_field"] == "spread_bps")
  |> mean()
'''

result = query_api.query(query)
for table in result:
    for record in table.records:
        print(f"{record['symbol']}: {record.get_value():.2f} bps")
```

## Grafana Dashboard Setup

### 1. Add InfluxDB Data Source

1. Open Grafana (http://localhost:3000)
2. Go to Configuration → Data Sources
3. Add new InfluxDB data source:
   - Query Language: Flux
   - URL: http://influxdb:8086
   - Organization: bitpulse
   - Token: your_token_here
   - Default Bucket: whale_analytics

### 2. Import Dashboard

Use the provided dashboard template:

```bash
# Import whale analytics dashboard
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_GRAFANA_API_KEY" \
  -d @grafana_dashboard.json
```

### 3. Key Visualizations

- **Whale Activity Heatmap**: Shows whale order concentration by price level
- **Market Manipulation Score**: Real-time manipulation detection gauge
- **Order Book Imbalance**: Bid/ask pressure visualization
- **Spoofing Detection Timeline**: Timeline of detected spoofing events
- **Price & Spread Chart**: Price movement with spread overlay
- **Whale Value Distribution**: Breakdown of whale orders by size

## Data Retention Policy

Default retention: 30 days

To modify retention:

```bash
# Update bucket retention (example: 7 days)
curl -X PATCH http://localhost:8086/api/v2/buckets/BUCKET_ID \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"retentionRules": [{"everySeconds": 604800}]}'
```

## Performance Optimization

### Write Performance
- Data is written synchronously for reliability
- Batch writes occur every second for price data
- Individual whale orders written immediately for real-time tracking

### Query Performance Tips
1. Always use time ranges in queries
2. Use specific field filters when possible
3. Aggregate data for long time ranges
4. Create continuous queries for frequently accessed metrics

### Resource Usage
- Typical memory usage: 200-500MB
- Disk usage: ~100MB per day per trading pair
- CPU usage: <5% on modern systems

## Troubleshooting

### Connection Issues

```bash
# Check InfluxDB is running
docker ps | grep influxdb

# Check logs
docker logs influxdb

# Test connection
curl -I http://localhost:8086/ping
```

### Data Not Appearing

1. Check token permissions:
```bash
curl http://localhost:8086/api/v2/authorizations \
  -H "Authorization: Token YOUR_TOKEN"
```

2. Verify bucket exists:
```bash
curl http://localhost:8086/api/v2/buckets \
  -H "Authorization: Token YOUR_TOKEN" | jq '.buckets[].name'
```

3. Check write errors in application logs:
```bash
grep "Failed to write" logs/whale_analytics.log
```

### Query Issues

- Ensure time range is specified
- Check measurement and field names match exactly
- Verify organization and bucket are correct

## Advanced Usage

### Custom Aggregations

Create task for hourly aggregations:

```flux
option task = {
  name: "hourly_whale_summary",
  every: 1h
}

from(bucket: "whale_analytics")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "whale_order")
  |> group(columns: ["symbol", "side"])
  |> count()
  |> to(bucket: "whale_analytics_hourly")
```

### Alerting

Set up alerts for significant events:

```flux
from(bucket: "whale_analytics")
  |> range(start: -5m)
  |> filter(fn: (r) => r["_measurement"] == "manipulation_event")
  |> filter(fn: (r) => r["_field"] == "confidence")
  |> filter(fn: (r) => r._value > 0.9)
  |> alert(
      check: {_value: true},
      message: "High confidence manipulation detected!"
    )
```

## Backup and Recovery

### Backup

```bash
# Backup entire bucket
docker exec influxdb influx backup /var/lib/influxdb2/backup

# Copy backup to host
docker cp influxdb:/var/lib/influxdb2/backup ./influxdb_backup
```

### Restore

```bash
# Copy backup to container
docker cp ./influxdb_backup influxdb:/var/lib/influxdb2/backup

# Restore
docker exec influxdb influx restore /var/lib/influxdb2/backup
```

## Security Best Practices

1. **Use environment variables** for tokens (never hardcode)
2. **Create read-only tokens** for visualization tools
3. **Enable HTTPS** in production environments
4. **Implement rate limiting** for write operations
5. **Regular backups** of critical data
6. **Monitor disk usage** to prevent data loss

## Integration with Analysis Tools

### Export to Pandas

```python
import pandas as pd
from influxdb_client import InfluxDBClient

def get_whale_data(symbol, hours=24):
    client = InfluxDBClient(
        url="http://localhost:8086",
        token="your_token",
        org="bitpulse"
    )
    
    query = f'''
    from(bucket: "whale_analytics")
      |> range(start: -{hours}h)
      |> filter(fn: (r) => r["_measurement"] == "whale_order")
      |> filter(fn: (r) => r["symbol"] == "{symbol}")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    
    df = client.query_api().query_data_frame(query)
    return df

# Example usage
whale_df = get_whale_data("BTCUSDT", hours=24)
print(whale_df.describe())
```

### Real-time Streaming

```python
from influxdb_client import InfluxDBClient

def stream_whale_alerts():
    client = InfluxDBClient(
        url="http://localhost:8086",
        token="your_token",
        org="bitpulse"
    )
    
    query = '''
    from(bucket: "whale_analytics")
      |> range(start: -1s)
      |> filter(fn: (r) => r["_measurement"] == "whale_order")
      |> filter(fn: (r) => r["_field"] == "value_usd")
      |> filter(fn: (r) => r._value > 1000000)
    '''
    
    # Poll every second for new mega whales
    while True:
        result = client.query_api().query(query)
        for table in result:
            for record in table.records:
                print(f"MEGA WHALE: {record['symbol']} ${record.get_value():,.0f}")
        time.sleep(1)
```

## Next Steps

1. **Set up Grafana** for visualization
2. **Create custom alerts** for trading signals
3. **Implement continuous queries** for performance
4. **Export historical data** for backtesting
5. **Integrate with trading bots** for automated execution

For more information, see the [InfluxDB documentation](https://docs.influxdata.com/influxdb/v2.7/).