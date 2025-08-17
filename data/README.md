1.  data/whales/ - Real-Time Whale Tracking 🐋

Purpose: Logs EVERY large order that exceeds whale thresholds in real-time

File Structure: data/whales/SYMBOL/SYMBOL_whales_YYYY-MM-DD.csv

Key Fields:
timestamp - When whale was detected (millisecond precision)
whale_id - Unique ID: SYMBOL_side_price_timestamp
side - bid (buy) or ask (sell)
price - Order price
size - Order size in base currency
value_usd - Total USD value
percentage_of_book - % of total order book this represents
duration_seconds - How long whale has been active
size_changes_count - Times the order size changed
disappearances - Times order vanished and reappeared
is_new - First time seeing this whale (True/False)

What It Tracks:

- ALL large orders as they appear
- Updates every 100ms per whale
- Both real and fake orders (we don't know yet)
- Complete lifecycle of each whale

Data Volume: ~50-100 MB per hour per symbol

---

2. data/spoofing/ - Confirmed Manipulation 🚨

Purpose: Logs orders confirmed as market manipulation

File Structure: data/spoofing/SYMBOL/SYMBOL_spoofing_YYYY-MM-DD.csv

Key Fields:
timestamp - When spoofing was detected
whale_id - Same ID from whales directory
initial_size - Size when first appeared
final_size - Size when disappeared
initial_value_usd - Starting value
final_value_usd - Ending value
time_active_seconds - Total time the spoof was active
disappearances - Number of flicker events
size_variance_pct - How much size varied (%)
spoof_pattern - Type: single/flickering/size_manipulation

What It Tracks:

- ONLY confirmed fake orders
- Orders that disappeared without being filled
- Manipulation patterns (flickering, size games)
- Evidence of market manipulation

Data Volume: Should be ~1-5 MB/hour (was 100+ MB with bug!)

---

3. data/snapshots/ - Market Overview 📸

Purpose: Periodic market state snapshots for context

File Structure: data/snapshots/SYMBOL/SYMBOL_snapshots_YYYY-MM-DD.csv

Key Fields:
timestamp - Snapshot time (every ~1 minute)
mid_price - Current market price
spread_bps - Bid-ask spread in basis points
total_whale_count - Number of active whales
whale_imbalance - Difference between bid/ask whales
volume_imbalance - Bid vs ask volume ratio
bid_volume_usd - Total bid side volume
ask_volume_usd - Total ask side volume
largest_bid_whale - Biggest buy whale value
largest_ask_whale - Biggest sell whale value
support_level - Detected support price
resistance_level - Detected resistance price

What It Tracks:

- Overall market conditions
- Whale distribution
- Volume imbalances
- Key price levels

Data Volume: ~5-10 MB per day per symbol

---

4. data/archive/ - Historical Compression 📦

Purpose: Compressed historical data for long-term storage

File Structure: data/archive/YYYY-MM-DD_compressed.tar.gz

Contains:

- All CSV files from previous days
- Compressed to save space (~10:1 ratio)
- Preserves complete historical record

What It Tracks:

- Everything from whales/, spoofing/, snapshots/
- Organized by date
- Ready for historical analysis

Data Volume: ~50-100 MB per day compressed (from ~1GB raw)

---

📊 Data Flow Summary

Real-Time (100ms)
↓

1. WHALES/ - Log every large order immediately
   ↓
2. SPOOFING/ - When whale disappears suspiciously (5-60s)
   ↓
3. SNAPSHOTS/ - Every minute, save market state
   ↓
4. ARCHIVE/ - Daily compression of all data

🎯 How Each Directory Helps Trading

| Directory  | Trading Use Case                                        |
| ---------- | ------------------------------------------------------- |
| whales/    | Track all large orders, identify patterns, see duration |
| spoofing/  | Identify manipulators, calculate manipulation score     |
| snapshots/ | Market context, trend analysis, support/resistance      |
| archive/   | Backtesting, historical patterns, long-term analysis    |

💡 Key Insights

1. whales/ is your primary data source - everything starts here
2. spoofing/ provides manipulation evidence - subset of whales that were fake
3. snapshots/ gives market context - helps understand conditions
4. archive/ enables historical analysis - compressed for efficiency
