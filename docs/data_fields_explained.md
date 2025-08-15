# CSV Data Fields Explanation

## 📊 Whales CSV (`data/whales/whales_YYYY-MM-DD.csv`)

This file logs **EVERY whale order** detected in real-time (hundreds per second).

### Fields:
| Field | Description | Example |
|-------|-------------|---------|
| **timestamp** | When detected | 2025-08-15T21:22:50.457289 |
| **symbol** | Trading pair | FETUSDT |
| **whale_id** | Unique tracking ID | FETUSDT_bid_0_1755278570457 |
| **side** | Buy or sell side | bid/ask |
| **price** | Order price | 0.6847 |
| **size** | Order size (in base asset) | 74142.0 |
| **value_usd** | Total USD value | 50765.67 |
| **percentage_of_book** | % of order book side | 15.67% |
| **level** | Position in book (0=best) | 3 |
| **mid_price** | Current market price | 0.68495 |
| **spread_bps** | Bid-ask spread | 2.5 |
| **total_bid_whales** | # of bid whales | 8 |
| **total_ask_whales** | # of ask whales | 6 |
| **volume_imbalance** | Bid/ask imbalance | 0.35 |
| **duration_seconds** | How long whale existed | 42.75 |
| **size_changes_count** | Times size changed | 3 |
| **disappearances** | Times disappeared/reappeared | 1 |
| **is_new** | First time seeing this whale | True/False |

### What This Tells Us:
- **Which whales persist** (real orders) vs disappear quickly (spoofs)
- **Size manipulation** - whales that change size to influence perception
- **Price levels** where whales concentrate
- **Market context** when whales appear

---

## 🚨 Spoofing CSV (`data/spoofing/spoofing_YYYY-MM-DD.csv`)

This file logs **suspected manipulation** - orders that disappeared suspiciously.

### Fields:
| Field | Description | Example |
|-------|-------------|---------|
| **timestamp** | When spoofing detected | 2025-08-15T21:22:51.545405 |
| **symbol** | Trading pair | ARBUSDT |
| **whale_id** | Unique tracking ID | ARBUSDT_bid_0_1755278571006 |
| **side** | Buy or sell side | bid |
| **price** | Order price | 0.4732 |
| **initial_size** | Size when first seen | 74142.0 |
| **final_size** | Size when disappeared | 98440.9 |
| **initial_value_usd** | Initial USD value | $35,083.99 |
| **final_value_usd** | Final USD value | $46,631.45 |
| **time_active_seconds** | How long it lasted | 0.428 seconds |
| **percentage_of_book** | % of order book | 4.89% |
| **size_changes_count** | Times size changed | 3 |
| **disappearances** | Times flickered on/off | 3 |
| **max_size_seen** | Largest size observed | 98440.9 |
| **min_size_seen** | Smallest size observed | 65700.8 |
| **size_variance_pct** | Size variation % | 44.16% |
| **spoof_pattern** | Type of manipulation | flickering/single/size_manipulation |

### Spoof Patterns Detected:
- **single**: Order appears once, disappears (classic spoof)
- **flickering**: Order appears/disappears multiple times (automated manipulation)
- **size_manipulation**: Order changes size dramatically (>50% variance)

### What This Tells Us:
- **Manipulation tactics** being used
- **Active times** for spoofing (often low liquidity periods)
- **Price levels** targeted for manipulation
- **Success rate** (did price move after spoof?)

---

## 📈 Snapshots CSV (`data/snapshots/SYMBOL_YYYY-MM-DD.csv`)

Periodic market state every ~1 minute for context.

### Fields:
- Market price, spread, volume
- Total whale counts per side
- Largest whales on each side
- Support/resistance levels
- Order book imbalance metrics

---

## 💡 Analysis Possibilities

With this data you can:

1. **Identify Persistent Actors**
   - Same whale_id appearing daily at similar prices
   - Likely institutional or smart money

2. **Detect Manipulation Patterns**
   - Spoofing before big moves
   - Coordinated spoofs across multiple pairs
   - Time-of-day patterns

3. **Build Trading Strategies**
   - Trade when real whales appear (duration > 30s)
   - Avoid trading during heavy spoofing
   - Follow whale accumulation/distribution

4. **Research Market Microstructure**
   - How often are large orders real vs fake?
   - What percentage of liquidity is spoofed?
   - Do spoofs successfully move price?

5. **Machine Learning Features**
   - Train models to predict which whales are real
   - Detect manipulation in real-time
   - Predict price moves based on whale behavior

---

## 📊 Current Data Volume

From just ARB, INJ, FET pairs:
- **Whales**: ~100,000+ events per hour
- **Spoofing**: ~1,000+ events per hour
- **File Size**: ~50-150MB per day (compressed to ~10-30MB)

The data shows heavy manipulation, especially in lower liquidity pairs like FET where:
- Orders flicker on/off in <1 second
- Size changes by 40-100% rapidly
- Same price levels repeatedly spoofed

This is valuable data for understanding crypto market manipulation!