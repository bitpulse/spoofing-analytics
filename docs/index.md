# Whale Analytics System Documentation

## Quick Start

1. [System Overview](system_architecture.md) - Architecture and components
2. [Data Collection Guide](data_collection_guide.md) - What data we collect and how
3. [Market Manipulation Guide](market_manipulation_guide.md) - Understanding whale tactics

## Configuration

- [Trading Pairs Configuration](trading_pairs_config.md) - Monitored pairs and thresholds
- [Alert Configuration](alert_configuration.md) - Telegram alerts and throttling

## Data Analysis

- [Data Fields Explained](data_fields_explained.md) - CSV field descriptions
- [Analysis Tool Guide](analyze_data_tool.md) - Using analyze_data.py
- [Data Volume Analysis](data_volume_analysis.md) - Storage and performance metrics

## Operations

- [Monitoring Summary](monitoring_summary.md) - Current monitoring status
- [Q&A](QA.md) - Common questions and answers

## File Structure

```
whale-analytics-system/
├── src/                    # Source code
│   ├── main.py            # Entry point
│   ├── collectors/        # WebSocket management
│   ├── analyzers/         # Order book analysis
│   ├── tracking/          # Whale tracking
│   ├── storage/           # CSV logging
│   ├── alerts/            # Telegram alerts
│   └── models/            # Data models
├── data/                  # CSV data storage
│   ├── whales/           # Per-symbol whale events
│   ├── spoofing/         # Spoofing detections
│   └── snapshots/        # Market snapshots
├── docs/                  # Documentation
├── logs/                  # System logs
├── analyze_data.py        # Analysis tool
├── requirements.txt       # Dependencies
├── .env                   # Configuration
└── README.md             # Project overview
```

## Key Concepts

### Whale Orders
Large orders that can influence market price, typically:
- BTCUSDT: >$1M
- ETHUSDT: >$500K
- Alt coins: >$30-200K

### Spoofing
Fake orders placed to manipulate price perception:
- Appear for 5-60 seconds
- Disappear before execution
- Create false support/resistance

### Manipulation Score
0-100 scale indicating market manipulation level:
- 0-20: Clean market
- 20-50: Moderate manipulation
- 50-80: High manipulation
- 80-100: Extreme manipulation

## Usage Examples

### Start Monitoring
```bash
python -m src.main
```

### Analyze Data
```bash
# Single symbol
python analyze_data.py BTCUSDT

# Compare all symbols
python analyze_data.py compare

# Specific date
python analyze_data.py BTCUSDT 2025-08-15
```

### Check Logs
```bash
tail -f logs/whale_analytics.log
```

### Data Locations
- Real-time data: `data/whales/SYMBOL/`
- Spoofing events: `data/spoofing/SYMBOL/`
- Market snapshots: `data/snapshots/SYMBOL/`

## Performance Metrics

- **Data Rate**: 500-1000 events/second
- **Storage**: 2-8GB/day (200-800MB compressed)
- **Latency**: <10ms processing time
- **Accuracy**: 95%+ spoof detection rate

## Support

For issues or questions:
1. Check the [Q&A](QA.md) section
2. Review error logs in `logs/`
3. Verify configuration in `.env`
4. Ensure Telegram bot is properly configured