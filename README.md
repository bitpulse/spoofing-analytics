# whale-analytics-system

PLAN

## **🎯 COMPLETE FUTURES-ONLY DATA COLLECTION PLAN**

Here's EXACTLY what futures data to collect from Binance for whale tracking.

---

## **📊 FUTURES DATA HIERARCHY**

```
CRITICAL (Must Have):
├── Order Book Depth (100ms updates)
├── Aggregated Trades (real-time)
└── Liquidations (real-time)

IMPORTANT (Need Within Week 1):
├── Open Interest (30-second updates)
├── Funding Rate (5-minute updates)
└── Mark Price (1-second updates)

VALUABLE (Add Week 2):
├── Long/Short Ratio (15-minute updates)
├── Top Trader Positions (5-minute updates)
└── Klines 1m/5m (completed candles)

OPTIONAL (Nice to Have):
├── Book Ticker (fastest spread)
├── 24hr Ticker Stats
└── Composite Index Price
```

---

## **🔴 TIER 1: CRITICAL DATA (Start Immediately)**

### **1. FUTURES ORDER BOOK DEPTH**

**WebSocket:** `wss://fstream.binance.com/ws/btcusdt@depth20@100ms`

**Raw Data Structure:**

```javascript
{
  "e": "depthUpdate",
  "E": 1681877152136,      // Event time (server timestamp)
  "T": 1681877152123,      // Transaction time
  "s": "BTCUSDT",
  "U": 3251658789,         // First update ID in event
  "u": 3251658852,         // Final update ID in event
  "pu": 3251658788,        // Previous final update ID
  "b": [                   // Bids
    ["43250.00", "125.532"],  // [price, contracts]
    ["43249.90", "89.221"],
    ["43249.80", "45.500"],
    // ... up to 20 levels
  ],
  "a": [                   // Asks
    ["43250.10", "98.332"],
    ["43250.20", "156.773"],
    ["43250.30", "67.100"],
    // ... up to 20 levels
  ]
}
```

**What to Calculate & Store:**

```python
EVERY 100ms snapshot:
{
    # Metadata
    'timestamp_server': E,
    'timestamp_local': time.time(),
    'symbol': 'BTCUSDT',
    'update_id': u,
    'update_id_gap': u - pu,  # Should be small, detect missed data

    # Price Levels
    'best_bid': b[0][0],
    'best_bid_size': b[0][1],
    'best_ask': a[0][0],
    'best_ask_size': a[0][1],

    # Spreads
    'spread': best_ask - best_bid,
    'spread_bps': (spread / best_bid) * 10000,  # Basis points
    'mid_price': (best_bid + best_ask) / 2,

    # Volume Analysis (Top 20 levels)
    'bid_volume_total': sum(all_bid_sizes),
    'ask_volume_total': sum(all_ask_sizes),
    'bid_volume_value': sum(price * size for bids),  # USD value
    'ask_volume_value': sum(price * size for asks),

    # Whale Detection
    'whale_bids': [
        {
            'price': price,
            'size': size,
            'value_usd': price * size,
            'level': i,  # Distance from best bid
            'percentage_of_book': (size / total_bid_volume) * 100
        }
        for price, size in bids if price * size > 100000
    ],
    'whale_asks': [...],  # Same structure

    # Imbalance Metrics
    'volume_imbalance': (bid_vol - ask_vol) / (bid_vol + ask_vol),
    'value_imbalance': (bid_value - ask_value) / (bid_value + ask_value),
    'whale_imbalance': (whale_bid_count - whale_ask_count),

    # Order Book Shape
    'bid_slope': calculate_slope(bid_prices, bid_sizes),  # Steepness
    'ask_slope': calculate_slope(ask_prices, ask_sizes),
    'book_skew': bid_slope - ask_slope,  # Asymmetry

    # Depth Metrics
    'depth_1_percent': volume_within_1_percent_of_mid,
    'depth_10bps': volume_within_10_basis_points,
    'resistance_level': first_ask_over_1M_usd,
    'support_level': first_bid_over_1M_usd
}
```

**Storage Strategy:**

```python
if whale_detected or significant_change:
    store_full_snapshot()  # All 20 levels
else:
    store_compressed()  # Just metrics, not raw data

# Keep rolling window in memory
last_100_snapshots = deque(maxlen=100)  # Last 10 seconds
```

---

### **2. FUTURES AGGREGATED TRADES**

**WebSocket:** `wss://fstream.binance.com/ws/btcusdt@aggTrade`

**Raw Data Structure:**

```javascript
{
  "e": "aggTrade",
  "E": 1681877152136,    // Event time
  "a": 812361844,        // Aggregate trade ID
  "s": "BTCUSDT",
  "p": "43250.50",       // Price
  "q": "15.532",         // Quantity (contracts)
  "f": 921645788,        // First trade ID
  "l": 921645791,        // Last trade ID
  "T": 1681877152123,    // Trade time
  "m": false             // Is buyer the maker? false = aggressive buy
}
```

**What to Calculate & Store:**

```python
EVERY trade:
{
    'timestamp': T,
    'price': p,
    'size': q,
    'value_usd': p * q,
    'trade_count': l - f + 1,  # How many individual trades

    # Direction Analysis
    'side': 'buy' if not m else 'sell',  # Aggressor side
    'is_aggressive': not m,

    # Size Classification
    'size_category': classify_size(value_usd),
    # 'micro': < $1k
    # 'small': $1k - $10k
    # 'medium': $10k - $50k
    # 'large': $50k - $100k
    # 'whale': > $100k
    # 'mega_whale': > $500k

    # Price Impact
    'price_change': price - previous_price,
    'price_change_bps': (price_change / previous_price) * 10000,

    # Clustering Detection
    'time_since_last': T - previous_trade_time,
    'is_cluster': time_since_last < 100,  # Within 100ms

    # Unusual Activity
    'is_unusual_size': size > recent_avg_size * 3,
    'is_block_trade': trade_count == 1 and value_usd > 100000
}

# Aggregated Metrics (Every Minute)
{
    'buy_volume': sum(buy_trades),
    'sell_volume': sum(sell_trades),
    'buy_count': count(buy_trades),
    'sell_count': count(sell_trades),
    'avg_trade_size': total_volume / trade_count,
    'whale_trade_count': count(trades > $100k),
    'buy_sell_ratio': buy_volume / sell_volume,
    'vwap': sum(price * volume) / sum(volume),
    'trade_intensity': trades_per_second
}
```

---

### **3. LIQUIDATIONS**

**WebSocket:** `wss://fstream.binance.com/ws/btcusdt@forceOrder`

**Raw Data Structure:**

```javascript
{
  "e": "forceOrder",
  "E": 1681877152136,
  "o": {
    "s": "BTCUSDT",      // Symbol
    "S": "BUY",          // BUY = short liquidation, SELL = long liquidation
    "o": "LIMIT",
    "f": "IOC",
    "q": "125.532",      // Quantity liquidated
    "p": "43000.00",     // Price
    "ap": "42999.50",    // Average price
    "X": "FILLED",
    "l": "125.532",      // Last filled quantity
    "z": "125.532",      // Cumulative filled
    "T": 1681877152123   // Trade time
  }
}
```

**What to Calculate & Store:**

```python
EVERY liquidation:
{
    'timestamp': T,
    'side': S,  # BUY = shorts liquidated, SELL = longs liquidated
    'size': q,
    'price': p,
    'avg_price': ap,
    'value_usd': ap * q,

    # Classification
    'liquidation_type': 'long' if S == 'SELL' else 'short',
    'size_category': get_liq_category(value_usd),
    # 'small': < $10k
    # 'medium': $10k - $100k
    # 'large': $100k - $1M
    # 'mega': > $1M

    # Cascade Detection
    'time_since_last_liq': T - previous_liq_time,
    'is_cascade_participant': time_since_last_liq < 10000,  # 10 seconds

    # Market Context
    'price_distance_from_last': abs(p - last_trade_price),
    'caused_by': 'wick' if price_distance > threshold else 'trend'
}

# Cascade Metrics (Rolling Window)
{
    'liquidations_1m': count_in_last_minute,
    'liquidation_volume_1m': sum_in_last_minute,
    'long_short_ratio': long_liqs / short_liqs,
    'cascade_intensity': liqs_per_second if > 0.5,
    'largest_liquidation': max_in_window
}
```

---

## **🟡 TIER 2: IMPORTANT DATA (Add Within Days)**

### **4. OPEN INTEREST**

**REST API:** `GET /fapi/v1/openInterest`
**Frequency:** Every 30 seconds

**Response:**

```javascript
{
  "symbol": "BTCUSDT",
  "openInterest": "125678.532",  // Total contracts
  "time": 1681877152136
}
```

**What to Calculate & Store:**

```python
{
    'timestamp': time,
    'open_interest': openInterest,
    'open_interest_usd': openInterest * current_price,

    # Changes
    'oi_change_1m': current - oi_1m_ago,
    'oi_change_5m': current - oi_5m_ago,
    'oi_change_1h': current - oi_1h_ago,

    # Percentage Changes
    'oi_pct_change_1m': (change_1m / oi_1m_ago) * 100,
    'oi_pct_change_5m': (change_5m / oi_5m_ago) * 100,

    # Signals
    'rapid_increase': oi_pct_change_5m > 5,
    'rapid_decrease': oi_pct_change_5m < -5,
    'new_high': oi > max_24h,
    'capitulation': oi < min_24h
}
```

---

### **5. FUNDING RATE**

**REST API:** `GET /fapi/v1/fundingRate`
**Frequency:** Every 5 minutes (or at funding time)

**Response:**

```javascript
{
  "symbol": "BTCUSDT",
  "fundingRate": "0.0001",      // 0.01%
  "fundingTime": 1681920000000,  // Next funding time
  "time": 1681877152136
}
```

**What to Calculate & Store:**

```python
{
    'timestamp': time,
    'funding_rate': fundingRate,
    'funding_rate_pct': fundingRate * 100,
    'funding_rate_annual': fundingRate * 3 * 365 * 100,  # APR
    'next_funding_time': fundingTime,
    'minutes_until_funding': (fundingTime - time) / 60000,

    # Market Sentiment
    'sentiment': get_sentiment(fundingRate),
    # 'extremely_bullish': > 0.1%
    # 'bullish': 0.05% to 0.1%
    # 'neutral': -0.05% to 0.05%
    # 'bearish': -0.1% to -0.05%
    # 'extremely_bearish': < -0.1%

    # Squeeze Potential
    'long_squeeze_risk': fundingRate > 0.1,
    'short_squeeze_risk': fundingRate < -0.1,

    # Historical Context
    'percentile_7d': get_percentile(fundingRate, last_7_days),
    'is_extreme': percentile_7d > 95 or percentile_7d < 5
}
```

---

### **6. MARK PRICE**

**WebSocket:** `wss://fstream.binance.com/ws/btcusdt@markPrice@1s`

**Raw Data:**

```javascript
{
  "e": "markPriceUpdate",
  "E": 1681877152136,
  "s": "BTCUSDT",
  "p": "43250.52341234",    // Mark price
  "i": "43249.87654321",    // Index price
  "P": "43251.12345678",    // Estimated settle price
  "r": "0.0001",            // Funding rate
  "T": 1681920000000        // Next funding time
}
```

**What to Calculate & Store:**

```python
{
    'timestamp': E,
    'mark_price': p,
    'index_price': i,
    'settle_price': P,

    # Spreads
    'mark_index_spread': p - i,
    'mark_index_spread_bps': ((p - i) / i) * 10000,
    'mark_last_spread': p - last_trade_price,

    # Premium/Discount
    'futures_premium': p > i,
    'premium_amount': abs(p - i),
    'premium_pct': ((p - i) / i) * 100,

    # Liquidation Levels (Common Leverages)
    'liq_price_long_10x': p * 0.91,   # 10x leverage
    'liq_price_long_25x': p * 0.96,   # 25x leverage
    'liq_price_long_50x': p * 0.98,   # 50x leverage
    'liq_price_long_100x': p * 0.99,  # 100x leverage
    'liq_price_short_10x': p * 1.09,
    'liq_price_short_25x': p * 1.04,
    'liq_price_short_50x': p * 1.02,
    'liq_price_short_100x': p * 1.01
}
```

---

## **🟢 TIER 3: VALUABLE DATA (Week 2)**

### **7. LONG/SHORT RATIO**

**REST API:** `GET /futures/data/globalLongShortAccountRatio`
**Frequency:** Every 15 minutes

```python
{
    'long_short_ratio': longShortRatio,
    'long_percentage': (longShortRatio / (1 + longShortRatio)) * 100,
    'short_percentage': (1 / (1 + longShortRatio)) * 100,
    'sentiment': 'bullish' if longShortRatio > 1.2 else 'bearish' if < 0.8
}
```

### **8. TOP TRADER POSITIONS**

**REST API:** `GET /futures/data/topLongShortPositionRatio`
**Frequency:** Every 5 minutes

```python
{
    'top_trader_long_ratio': topLongRatio,
    'top_trader_sentiment': 'bullish' if > 1.5 else 'bearish',
    'divergence': top_trader_ratio - retail_ratio,
    'smart_money_signal': 'follow' if divergence > threshold
}
```

### **9. KLINES (1m and 5m)**

**WebSocket:** `wss://fstream.binance.com/ws/btcusdt@kline_1m`

```python
{
    'volume': v,
    'quote_volume': q,  # USD volume
    'trade_count': n,
    'taker_buy_ratio': V / v,
    'avg_trade_size': v / n,
    'is_high_volume': v > average_volume * 2,
    'body_size': abs(close - open),
    'upper_wick': high - max(open, close),
    'lower_wick': min(open, close) - low
}
```

---

## **⚡ DATA COLLECTION PRIORITIES BY DAY**

### **Day 1: Core Setup**

```python
Connect to:
1. btcusdt@depth20@100ms  # Order book
2. btcusdt@aggTrade        # Trades
3. btcusdt@forceOrder      # Liquidations

Store: Everything for now (optimize later)
```

### **Day 2-3: Add Context**

```python
Add REST calls:
4. Open Interest (every 30s)
5. Funding Rate (every 5m)

Add WebSocket:
6. btcusdt@markPrice@1s
```

### **Day 4-7: Expand Coverage**

```python
Add more symbols:
- ethusdt@depth20@100ms
- bnbusdt@depth20@100ms
- solusdt@depth20@100ms

Same 6 data types for each
```

### **Week 2: Advanced Metrics**

```python
Add:
- Long/Short ratios
- Top trader positions
- Klines for volume analysis
- Multiple timeframes
```

---

## **💾 STORAGE OPTIMIZATION**

### **What to Store Forever:**

- All liquidations (rare and valuable)
- Whale orders > $500k
- Unusual events (cascade, flash crash)
- Daily aggregates

### **What to Store Temporarily:**

- Order book snapshots: 24 hours
- Small trades: 1 hour aggregated
- Mark prices: 1 hour
- Failed whale signals: 7 days

### **What to Keep in Memory Only:**

- Last 100 order book updates
- Last 1000 trades
- Current whale positions
- Active signals

---

## **🎯 SUCCESS METRICS**

### **Week 1 Targets:**

- Zero gaps in order book updates
- Capture 100% of liquidations
- Detect 50+ whale orders daily
- Identify 3-5 whale patterns

### **Data Quality Checks:**

```python
Every hour verify:
- Update IDs sequential (no gaps)
- Timestamps increasing
- Best bid < Best ask
- Mark price ≈ Last price (within 0.5%)
- No duplicate trades
```

---

## **⚠️ CRITICAL FUTURES-SPECIFIC RULES**

1. **Contract Size**: BTCUSDT = 1 contract = 1 BTC worth
2. **Funding Times**: Every 8 hours (00:00, 08:00, 16:00 UTC)
3. **Liquidation Priority**: These are GOLD - never miss one
4. **OI Changes**: Sudden drops = mass liquidations incoming
5. **Mark vs Last**: Divergence > 0.5% = manipulation active

---

## **🚀 THE MINIMUM VIABLE FUTURES DATA**

If you can only handle 3 things to start:

```python
MUST HAVE:
1. Order Book (depth20@100ms) - See whales
2. Liquidations (forceOrder) - Ride cascades
3. Open Interest (REST/30s) - Gauge momentum

This gives you 80% of alpha with 20% complexity
```

Everything else adds precision but these three are the CORE of futures whale tracking.

Ready to start collecting futures data? Begin with these three streams and expand as your system proves profitable!
