# whale-analytics-system

PLAN

## **🎯 COMPLETE BINANCE DATA COLLECTION GUIDE FOR WHALE TRACKING**

Based on Binance API research, here's EXACTLY what data you need to collect and why each piece matters for whale detection.

---

## **📊 1. ORDER BOOK DATA (Most Critical)**

### **WebSocket Stream: `depth20@100ms` or `depth@100ms`**

**What to Collect:**

```javascript
{
  "e": "depthUpdate",      // Event type
  "E": 1672515782136,      // Event time (server timestamp)
  "s": "BTCUSDT",          // Symbol
  "U": 157,                // First update ID in event
  "u": 160,                // Final update ID in event
  "b": [                   // Bids to be updated
    ["43250.00", "125.5"], // [price, quantity]
    ["43249.50", "89.2"],
    // ... collect ALL levels (20-50 levels ideal)
  ],
  "a": [                   // Asks to be updated
    ["43251.00", "98.3"],
    ["43251.50", "156.7"],
    // ... collect ALL levels
  ]
}
```

**What to Calculate & Store:**

```python
For EACH snapshot (every 100ms):
- timestamp (both local and server E)
- update_id (u) - CRITICAL for sequence validation
- best_bid_price, best_bid_size
- best_ask_price, best_ask_size
- spread (ask - bid)
- mid_price ((ask + bid) / 2)

For EACH price level:
- price
- size
- order_count (if available from depth5@100ms stream)
- value_usd (price × size)
- is_whale (value > $100k)
- distance_from_mid (percentage from mid price)

Aggregated Metrics:
- total_bid_volume (sum of all bid sizes)
- total_ask_volume (sum of all ask sizes)
- bid_ask_ratio (bid_vol / ask_vol)
- weighted_bid_price (volume-weighted average)
- weighted_ask_price
- imbalance ((bid_vol - ask_vol) / (bid_vol + ask_vol))

Whale-Specific:
- whale_bid_count (orders > $100k)
- whale_ask_count
- largest_bid_size, largest_bid_price
- largest_ask_size, largest_ask_price
- whale_volume_percentage (whale_vol / total_vol)
```

**Why This Matters:**

- **100ms updates**: Whales can place/cancel orders in 200ms
- **Update IDs**: Detect if you missed data (critical for accuracy)
- **Deep book (20+ levels)**: Whales often hide orders away from best bid/ask
- **Order count**: Multiple orders at same price = real interest vs single whale

---

## **📈 2. TRADE DATA**

### **WebSocket Stream: `aggTrade`**

**What to Collect:**

```javascript
{
  "e": "aggTrade",         // Event type
  "E": 1672515782136,      // Event time
  "s": "BTCUSDT",          // Symbol
  "a": 12345,              // Aggregate trade ID
  "p": "43250.50",         // Price
  "q": "15.5",             // Quantity
  "f": 100,                // First trade ID
  "l": 105,                // Last trade ID
  "T": 1672515782136,      // Trade time
  "m": true,               // Is buyer the maker?
  "M": true                // Best price match?
}
```

**What to Store:**

```python
For EACH trade:
- timestamp (T)
- price
- quantity
- value_usd (price × quantity)
- is_buyer_maker (m) - CRITICAL for determining aggression
- trade_count (l - f + 1) - how many orders filled

Calculated Fields:
- is_whale_trade (value > $50k)
- price_impact (% change from previous trade)
- side ('buy' if m=false, 'sell' if m=true)
- unusual_size (size > 3× recent average)

Aggregated (every minute):
- total_buy_volume
- total_sell_volume
- buy_sell_ratio
- average_trade_size
- whale_trade_count
- vwap (volume-weighted average price)
```

**Why This Matters:**

- **Buyer maker (m)**: Shows aggression - market buying/selling
- **Trade clustering**: Many trades at same price = accumulation/distribution
- **Trade size**: Whales often split orders but aggregate trades reveal them

---

## **💥 3. LIQUIDATION DATA (Futures Specific)**

### **WebSocket Stream: `forceOrder` or `allForceOrder`**

**What to Collect:**

```javascript
{
  "e": "forceOrder",       // Event Type
  "E": 1672515782136,      // Event Time
  "o": {
    "s": "BTCUSDT",        // Symbol
    "S": "SELL",           // Side (SELL = long liquidation)
    "o": "LIMIT",          // Order Type
    "f": "IOC",            // Time in Force
    "q": "125.5",          // Quantity
    "p": "43000.00",       // Price
    "ap": "42999.50",      // Average Price
    "X": "FILLED",         // Order Status
    "l": "125.5",          // Last Filled Quantity
    "z": "125.5",          // Cumulative Filled Quantity
    "T": 1672515782136     // Transaction Time
  }
}
```

**What to Store:**

```python
For EACH liquidation:
- timestamp
- symbol
- side (SELL = long liquidation, BUY = short liquidation)
- quantity
- price
- value_usd
- average_price (ap)

Calculated:
- size_category ('small', 'medium', 'large', 'mega')
- is_cascade_participant (if multiple liquidations within 10 seconds)
- price_distance_from_mark (how far from mark price)

Aggregated (rolling windows):
- liquidations_1m (count in last minute)
- liquidation_volume_1m
- long_liquidation_ratio
- cascade_detected (>5 liquidations in 10 seconds)
```

**Why This Matters:**

- **Cascade prediction**: Large liquidations trigger more liquidations
- **Direction bias**: More long liquidations = potential bottom
- **Whale hunting**: Whales often trigger liquidations intentionally

---

## **📊 4. OPEN INTEREST & FUNDING (Critical for Futures)**

### **REST API: `/fapi/v1/openInterest` (Every 30 seconds)**

**What to Collect:**

```javascript
{
  "openInterest": "125000.000",  // Total open interest in contracts
  "symbol": "BTCUSDT",
  "time": 1672515782136
}
```

### **REST API: `/fapi/v1/fundingRate` (Every 5 minutes)**

**What to Collect:**

```javascript
{
  "symbol": "BTCUSDT",
  "fundingRate": "0.0001000",    // Current funding rate
  "fundingTime": 1672516800000,   // Next funding time
  "time": 1672515782136
}
```

**What to Store:**

```python
Open Interest:
- timestamp
- open_interest_contracts
- open_interest_usd (contracts × price)
- change_1m, change_5m, change_1h
- percent_change_5m
- rapid_increase (change > 5% in 5 minutes)

Funding Rate:
- timestamp
- funding_rate
- funding_rate_annual (rate × 3 × 365)
- time_until_funding
- is_extreme (|rate| > 0.1%)
- sentiment ('bullish' if > 0.05%, 'bearish' if < -0.05%)
```

**Why This Matters:**

- **OI spikes**: New money entering = big move coming
- **OI drops**: Positions closing = volatility decreasing
- **Extreme funding**: Squeeze setups (high funding = short squeeze potential)

---

## **📉 5. KLINE/CANDLESTICK DATA**

### **WebSocket Stream: `kline_1m`, `kline_5m`**

**What to Collect:**

```javascript
{
  "e": "kline",
  "E": 1672515782136,
  "s": "BTCUSDT",
  "k": {
    "t": 1672515720000,    // Kline start time
    "T": 1672515779999,    // Kline close time
    "s": "BTCUSDT",
    "i": "1m",              // Interval
    "f": 100,               // First trade ID
    "L": 200,               // Last trade ID
    "o": "43250.00",        // Open
    "c": "43255.00",        // Close
    "h": "43260.00",        // High
    "l": "43245.00",        // Low
    "v": "1250.5",          // Volume
    "n": 100,               // Number of trades
    "x": false,             // Is this kline closed?
    "q": "54062500.00",     // Quote asset volume (in USDT)
    "V": "750.5",           // Taker buy base asset volume
    "Q": "32437500.00"      // Taker buy quote asset volume
  }
}
```

**What to Store:**

```python
- All OHLCV data
- volume (v)
- quote_volume (q) - USDT volume
- trade_count (n)
- taker_buy_ratio (V / v) - buying pressure
- average_trade_size (v / n)
- is_high_volume (volume > 2× average)
- price_range (high - low)
- body_size (|close - open|)
- wick_ratio (upper wick vs lower wick)
```

**Why This Matters:**

- **Volume spikes**: Whale activity
- **Taker buy ratio**: Shows aggression direction
- **Trade count**: High count = retail, Low count with high volume = whales

---

## **🔄 6. 24HR TICKER STATISTICS**

### **WebSocket Stream: `ticker` (Every second)**

**What to Collect:**

```javascript
{
  "e": "24hrTicker",
  "E": 1672515782136,
  "s": "BTCUSDT",
  "p": "250.00",           // Price change
  "P": "0.58",             // Price change percent
  "w": "43251.25",         // Weighted average price
  "c": "43255.00",         // Last price
  "Q": "10.5",             // Last quantity
  "o": "43005.00",         // Open price
  "h": "43500.00",         // High price
  "l": "42900.00",         // Low price
  "v": "250000.00",        // Total traded base asset volume
  "q": "10806250000.00",   // Total traded quote asset volume
  "O": 1672429382136,      // Statistics open time
  "C": 1672515782136,      // Statistics close time
  "F": 28385858,           // First trade ID
  "L": 28395858,           // Last trade Id
  "n": 10000               // Total number of trades
}
```

**What to Store:**

```python
- price_change_24h (p)
- percent_change_24h (P)
- volume_24h (v)
- quote_volume_24h (q)
- high_24h, low_24h
- trade_count_24h (n)
- average_trade_size_24h
- current_price_position ((current - low) / (high - low))
```

**Why This Matters:**

- **Volume comparison**: Current vs 24h average shows unusual activity
- **Price position**: Near highs/lows indicates potential reversals
- **Trade frequency**: Sudden changes indicate institutional activity

---

## **⚡ 7. REAL-TIME BOOK TICKER**

### **WebSocket Stream: `bookTicker`**

**What to Collect:**

```javascript
{
  "e": "bookTicker",
  "u": 400900217,          // order book updateId
  "E": 1672515782136,      // Event time
  "T": 1672515782136,      // Transaction time
  "s": "BTCUSDT",
  "b": "43250.00",         // Best bid price
  "B": "125.5",            // Best bid qty
  "a": "43250.50",         // Best ask price
  "A": "98.3"              // Best ask qty
}
```

**What to Store:**

```python
- All fields as-is
- spread (a - b)
- spread_percentage
- bid_ask_size_ratio (B / A)
- micro_imbalance
```

**Why This Matters:**

- **Fastest updates**: First signal of whale orders
- **Spread changes**: Indicates changing volatility
- **Size imbalance**: Shows immediate pressure

---

## **🎯 8. MARK PRICE (Futures Specific)**

### **WebSocket Stream: `markPrice@1s`**

**What to Collect:**

```javascript
{
  "e": "markPriceUpdate",
  "E": 1672515782136,
  "s": "BTCUSDT",
  "p": "43250.500",        // Mark price
  "i": "43250.250",        // Index price
  "P": "43260.750",        // Estimated Settle Price
  "r": "0.0001",           // Funding rate
  "T": 1672516800000       // Next funding time
}
```

**What to Store:**

```python
- mark_price (p)
- index_price (i)
- mark_index_spread (p - i)
- funding_rate (r)
- time_to_funding
- premium/discount percentage
```

**Why This Matters:**

- **Premium/Discount**: Shows futures sentiment vs spot
- **Liquidation calculations**: Mark price determines liquidations
- **Arbitrage opportunities**: Large spreads = whale games

---

## **📊 DATA COLLECTION PRIORITIES**

### **Tier 1 (MUST HAVE):**

1. **Order Book Depth** (`depth20@100ms`) - See whale orders
2. **Aggregated Trades** (`aggTrade`) - Detect accumulation
3. **Liquidations** (`forceOrder`) - Profit from cascades

### **Tier 2 (IMPORTANT):**

4. **Open Interest** (REST API every 30s) - Gauge participation
5. **Funding Rate** (REST API every 5m) - Sentiment indicator
6. **Klines 1m/5m** - Context and volume analysis

### **Tier 3 (NICE TO HAVE):**

7. **Book Ticker** - Micro structure
8. **24hr Ticker** - Relative metrics
9. **Mark Price** - Futures specific dynamics

---

## **⚠️ CRITICAL COLLECTION RULES**

### **Data Integrity:**

```python
ALWAYS track:
- Update IDs (ensure no gaps)
- Server timestamps (E) AND local timestamps
- Message sequence numbers
- Connection drops and reconnections
```

### **Storage Frequency:**

```python
Order Book:
- Store EVERY update if whale present
- Store every 10th update if no whale (for context)

Trades:
- Store ALL trades > $10,000
- Aggregate small trades per minute

Liquidations:
- Store EVERY liquidation (they're rare and valuable)
```

### **Cross-Validation:**

```python
Always compare:
- Order book best bid/ask vs trade prices
- Mark price vs index price vs last price
- Your local timestamp vs server timestamp (detect lag)
```

---

## **💡 WHY EACH DATA TYPE MATTERS**

**Order Book** → Shows INTENTION (whales placing orders)
**Trades** → Shows EXECUTION (whales actually buying/selling)
**Liquidations** → Shows PAIN (forced selling/buying)
**Open Interest** → Shows PARTICIPATION (money flowing in/out)
**Funding** → Shows SENTIMENT (bullish/bearish bias)
**Volume** → Shows INTENSITY (how serious the move is)

---

## **🎯 THE MINIMUM VIABLE DATA SET**

If you can only collect 3 things:

1. **Order book depth** (see the whales)
2. **Aggregated trades** (confirm whale action)
3. **Liquidations** (ride the cascades)

This gives you 80% of the alpha with 20% of the complexity.

The key is collecting data at the RIGHT frequency and storing the RIGHT calculations, not just raw data. Every millisecond and every byte should have a purpose in your whale detection strategy.
