# System Architecture

## Overview

The Whale Analytics System is a real-time order book monitoring and analysis platform for Binance Futures markets, designed to detect large orders (whales) and identify market manipulation patterns.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Binance Futures API                       │
│                  WebSocket Streams (100ms)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  WebSocket Manager                           │
│         (Concurrent connections per symbol)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 Order Book Parser                            │
│           (Validates and structures data)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 Order Book Analyzer                          │
│    ┌──────────────┬──────────────┬──────────────┐          │
│    │Whale Tracker │Spoof Detector│Market Metrics│          │
│    └──────────────┴──────────────┴──────────────┘          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ├──────────────┐
                       ▼              ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│     CSV Data Logger      │  │   Telegram Alert Manager │
│  (Per-symbol CSV files)  │  │    (Async queue-based)   │
└──────────────────────────┘  └──────────────────────────┘
```

## Core Components

### 1. WebSocket Manager (`src/collectors/websocket_manager.py`)

**Purpose**: Manages persistent WebSocket connections to Binance

**Key Features**:
- Concurrent connections for multiple symbols
- Automatic reconnection on failure
- Message validation and routing
- Thread-based isolation per symbol

**Configuration**:
- Update speed: 100ms
- Depth: 20 levels
- Symbols: Configurable via .env

### 2. Order Book Parser (`src/models/order_book.py`)

**Purpose**: Structures raw WebSocket data into analyzable format

**Data Models**:
- `PriceLevel`: Individual order book level
- `WhaleOrder`: Large order with metadata
- `OrderBookSnapshot`: Complete book state

**Key Calculations**:
- USD value conversion
- Spread calculations
- Volume aggregation
- Update gap detection

### 3. Order Book Analyzer (`src/analyzers/order_book_analyzer.py`)

**Purpose**: Performs real-time analysis on order book data

**Analysis Functions**:
- Whale detection (per-symbol thresholds)
- Spoofing identification
- Market pressure calculation
- Support/resistance detection
- Order book imbalance metrics

**Thresholds** (via `src/thresholds.py`):
- Per-symbol whale thresholds
- Mega whale thresholds
- Alert trigger levels

### 4. Whale Tracker (`src/tracking/whale_tracker.py`)

**Purpose**: Tracks individual whales across time

**Key Features**:
- Unique ID generation
- Fuzzy matching for order tracking
- Behavior pattern analysis
- Disappearance detection

**Tracking Metrics**:
- Duration active
- Size changes
- Disappearance count
- Pattern classification

### 5. CSV Data Logger (`src/storage/csv_logger.py`)

**Purpose**: Persists all data to CSV files

**Features**:
- Per-symbol file organization
- Daily file rotation
- Automatic compression
- Queue-based async writing

**Data Types**:
- Whale events
- Spoofing events
- Market snapshots

### 6. Telegram Alert Manager (`src/alerts/telegram_manager.py`)

**Purpose**: Sends real-time alerts to Telegram

**Alert Types**:
- Mega whale detection
- Spoofing alerts
- Market imbalance warnings

**Features**:
- Async queue processing
- Smart throttling
- Color-coded messages
- Markdown formatting

## Data Flow

### 1. Real-Time Processing Pipeline

```python
WebSocket Data (100ms)
    ↓
Parse to OrderBookSnapshot
    ↓
Detect Whales (threshold check)
    ↓
Track with Unique IDs
    ↓
Analyze for Spoofing
    ↓
Log to CSV + Send Alerts
```

### 2. Whale Detection Flow

```python
For each price level:
    if value_usd > whale_threshold:
        whale_id = generate_unique_id()
        track_whale(whale_id)
        log_to_csv()
        if value_usd > mega_threshold * 1.5:
            send_telegram_alert()
```

### 3. Spoofing Detection Flow

```python
For each disappeared whale:
    duration = time_disappeared - time_appeared
    if 5 < duration < 60 and value > $5M:
        flag_as_spoof()
        log_spoofing_event()
        send_alert()
```

## Configuration

### Environment Variables (`.env`)

```bash
# API Configuration
BINANCE_WS_BASE_URL=wss://fstream.binance.com

# Trading Pairs
SYMBOLS=BTCUSDT,ETHUSDT,ARBUSDT,INJUSDT,FETUSDT

# Order Book Settings
ORDER_BOOK_DEPTH=20
ORDER_BOOK_UPDATE_SPEED=100ms

# Telegram Alerts
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHANNEL_ID=your_channel
TELEGRAM_ALERTS_ENABLED=true
```

### Per-Symbol Thresholds (`src/thresholds.py`)

```python
PAIR_THRESHOLDS = {
    "BTCUSDT": {
        "whale": 1000000,      # $1M
        "mega_whale": 5000000  # $5M
    },
    "ARBUSDT": {
        "whale": 30000,        # $30K
        "mega_whale": 150000   # $150K
    }
}
```

## Performance Characteristics

### Processing Capacity

- **Events per second**: 500-1000
- **Latency**: <10ms per snapshot
- **Memory usage**: ~200MB for 8 symbols
- **Network bandwidth**: ~10 Mbps

### Data Generation

- **Whale events**: ~300/second per symbol
- **Spoofing events**: ~200/second per symbol
- **Daily data volume**: 2-8GB uncompressed
- **Compressed size**: 200-800MB

## Deployment

### Requirements

- Python 3.12+
- 2GB RAM minimum
- 50GB disk space (for data)
- Stable internet connection

### Installation

```bash
# Clone repository
git clone <repo>

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run system
python -m src.whale_monitor
```

### Monitoring

- Logs: `logs/whale_analytics.log`
- Data: `data/` directory
- Analysis: `python analyze_data.py compare`

## Security Considerations

- No private keys stored
- Read-only API access
- No trading capabilities
- Telegram bot token secured
- Data privacy maintained

## Scalability

### Current Limits

- 8-10 symbols comfortably
- 100ms update frequency
- 20 order book levels

### Scaling Options

1. **Horizontal**: Multiple instances for different symbols
2. **Vertical**: Increase server resources
3. **Database**: PostgreSQL for historical data
4. **Cloud**: Deploy on AWS/GCP for better connectivity

## Future Enhancements

- Redis for real-time data sharing
- PostgreSQL for historical analysis
- Web dashboard for visualization
- Machine learning integration
- Cross-exchange arbitrage detection
- REST API for data access