# Data Flow: How We Separate Whales from Spoofs

## The Real-Time Detection Pipeline

### 📊 What Happens Every 100ms

```
WebSocket Data Arrives (every 100ms)
         ↓
Order Book Analyzer Scans for Large Orders
         ↓
Found Large Order > Threshold?
         ↓ YES
Track with Unique ID (whale_tracker.py)
         ↓
Log to data/whales/SYMBOL/ IMMEDIATELY
         ↓
Monitor This Whale ID Every Update
         ↓
Whale Disappears?
         ↓ YES
Check: How long did it live?
         ↓
5-60 seconds? → Log to data/spoofing/SYMBOL/
>60 seconds? → Just a canceled order (stay in whales only)
```

## 🗂️ Data Directory Structure Explained

### `data/whales/SYMBOL/` - ALL Large Orders (Real-Time)
**When data goes here:** IMMEDIATELY when detected (every 100ms)
**What it contains:** EVERY large order that exceeds the whale threshold
**Includes both:** Real orders AND fake orders (we don't know yet!)

Example entry:
```csv
timestamp,symbol,whale_id,side,price,size,value_usd,duration_seconds
2025-08-15T21:22:50.457,FETUSDT,FETUSDT_bid_0.6847_1755278570457,bid,0.6847,74142,50765.67,0.0
```
- `duration_seconds: 0.0` means it just appeared
- This could be real or fake - we don't know yet!

### `data/spoofing/SYMBOL/` - CONFIRMED Fake Orders (Post-Detection)
**When data goes here:** AFTER the order disappears (5-60 seconds later)
**What it contains:** ONLY orders we've PROVEN are spoofs
**How we know:** The order disappeared without being filled

Example entry:
```csv
timestamp,symbol,whale_id,time_active_seconds,initial_value_usd,spoof_pattern
2025-08-15T21:22:56.542,FETUSDT,FETUSDT_bid_0.6847_1755278570457,6.085,50765.67,single
```
- Same `whale_id` as in whales directory
- `time_active_seconds: 6.085` - it lasted 6 seconds then vanished
- `spoof_pattern: single` - appeared once and disappeared

## 🔄 The Two-Stage Process

### Stage 1: Real-Time Logging (data/whales/)
```python
# In order_book_analyzer.py - happens IMMEDIATELY
if value_usd >= whale_threshold:
    whale_id = tracker.identify_whale(...)  # Create unique ID
    csv_logger.log_whale(...)               # Log to whales/ RIGHT NOW
    # We don't know if it's fake yet!
```

### Stage 2: Spoofing Detection (data/spoofing/)
```python
# In whale_tracker.py - happens when whale disappears
def process_snapshot_whales(current_whale_ids):
    for whale in active_whales:
        if whale not in current_whale_ids:
            # Whale disappeared!
            duration = time_now - whale.first_seen
            
            if 5 < duration < 60:
                # CONFIRMED SPOOF!
                csv_logger.log_spoofing(...)  # Log to spoofing/
                # This whale is now in BOTH directories
```

## 📈 Why This Two-Directory System?

### 1. **Complete History** (whales/)
- Shows ALL large orders as they happen
- Real-time view of market activity
- Includes timestamp when each whale first appears
- Can track how long orders stay active

### 2. **Manipulation Evidence** (spoofing/)
- Only CONFIRMED fake orders
- Each entry has proof: appeared → disappeared without fills
- Shows manipulation patterns (flickering, size changes)
- Used to calculate manipulation scores

## 🔍 How analyze_data.py Uses Both

```python
# The analysis combines both datasets:

# 1. Count total whales
df_whales = pd.read_csv("data/whales/SYMBOL/...")
total_whale_events = len(df_whales)  # e.g., 867

# 2. Count confirmed spoofs
df_spoofs = pd.read_csv("data/spoofing/SYMBOL/...")  
total_spoof_events = len(df_spoofs)  # e.g., 141

# 3. Calculate manipulation score
manipulation_score = (141 / 867) * 100 = 16.3%
```

## 🎯 Key Points

1. **Whales directory = RAW DATA**
   - Everything that LOOKS like a whale
   - Logged in real-time (within milliseconds)
   - Includes both real and fake orders

2. **Spoofing directory = CONFIRMED FAKES**
   - Only orders we've PROVEN are manipulative
   - Logged after they disappear (5-60 seconds later)
   - Each has evidence of manipulation

3. **The Same Order Appears in Both**
   - First in whales/ (when detected)
   - Then in spoofing/ (if proven fake)
   - Linked by unique whale_id

4. **Real Orders Only Appear in Whales**
   - If an order stays >60 seconds or gets filled
   - It only appears in whales/, never in spoofing/

## Example Timeline

```
21:22:50.457 - Large order detected
             → Logged to data/whales/FETUSDT/
             → whale_id: FETUSDT_bid_0.6847_1755278570457

21:22:50.557 - Still tracking (100ms update)
21:22:50.657 - Still tracking
21:22:50.757 - Still tracking
... (60 more updates)

21:22:56.542 - Order disappeared!
             → Duration: 6.085 seconds
             → Confirmed spoof (5-60 second window)
             → Logged to data/spoofing/FETUSDT/
             → Same whale_id links both records

Final Result:
- 1 entry in whales/ (logged at detection)
- 1 entry in spoofing/ (logged at disappearance)
- These are the SAME order at different stages
```

## Why Not Just One Directory?

**Real-time requirements:** We need to log whales immediately for:
- Market analysis
- Alert generation  
- Pattern detection

**Spoofing confirmation takes time:** We can't know an order is fake until:
- It disappears (5-60 seconds later)
- We confirm it wasn't filled
- We see the manipulation pattern

**Audit trail:** Two directories provide:
- Complete record of what we saw (whales/)
- Proven evidence of manipulation (spoofing/)
- Ability to verify our detection accuracy