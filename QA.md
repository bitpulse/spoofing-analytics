# Whale Analytics Q&A

## What Are Whale Alerts?

Whale alerts detect large limit orders sitting in the order book - these are **NOT executed trades**, but rather:

- **Bids (Buy Orders)**: Whales willing to buy at specific prices below current market
- **Asks (Sell Orders)**: Whales willing to sell at specific prices above current market

### Key Points

1. **Not Executed Trades**: These are pending orders waiting to be filled
2. **Market Manipulation Potential**: Large orders can create psychological support/resistance levels
3. **Often Fake (Spoofing)**: Whales may place huge orders to influence price, then cancel before execution
4. **Real Intent Unknown**: Could be genuine accumulation/distribution OR market manipulation

### Example Scenarios

- **Bid Wall at $95,000**: $2M buy order might be real support OR fake wall to pump price
- **Ask Wall at $100,000**: $3M sell order might be real resistance OR fake to suppress price

## What Are Order Book Imbalances?

Imbalances measure the difference in liquidity between buy and sell sides of the order book.

### The Calculation

```
Imbalance = (Bid Volume - Ask Volume) / Total Volume
```

- **Positive imbalance**: More buy orders (bids) than sell orders
- **Negative imbalance**: More sell orders (asks) than buy orders

### Visual Examples

#### Balanced Order Book (0% imbalance)
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ASKS (Sellers) | $500,000 total
$100,010 ████████████ |
$100,009 ██████████   |
$100,008 ████████     |
------------------------|
Current Price: $100,007 |
------------------------|
$100,006 ████████     |
$100,005 ██████████   |
$100,004 ████████████ |
BIDS (Buyers)  | $500,000 total
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### Imbalanced Order Book (80% positive)
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ASKS (Sellers) | $100,000 total
$100,010 ██           |
$100,009 █            |
$100,008 ██           |
------------------------|
Current Price: $100,007 |
------------------------|
$100,006 ████████████████████         |
$100,005 ██████████████████████       |
$100,004 ████████████████████████████ |
BIDS (Buyers)  | $900,000 total
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### What Imbalances Mean

#### 1. High Positive Imbalance (>70%)
- Heavy buying pressure
- More people want to buy than sell
- Price likely to go **UP** ↗️
- Can indicate accumulation

#### 2. High Negative Imbalance (<-70%)
- Heavy selling pressure
- More people want to sell than buy
- Price likely to go **DOWN** ↘️
- Can indicate distribution

#### 3. Balanced (-20% to +20%)
- Normal market conditions
- No clear directional pressure
- Price relatively stable

### Real-World Interpretation

#### Example 1: 85% Positive Imbalance
- $850,000 in buy orders vs $150,000 in sell orders
- **Meaning**: Strong support below, buyers are aggressive
- **BUT**: Could be fake walls to pump price

#### Example 2: -90% Negative Imbalance
- $100,000 in buy orders vs $900,000 in sell orders
- **Meaning**: Heavy resistance above, sellers dominating
- **BUT**: Could be spoofing to suppress price

### Why Imbalances Matter for Whale Detection

1. **Whale Impact**: A single $3M order can create massive imbalance
2. **Market Manipulation**: Whales place large orders to create artificial imbalances
3. **Directional Bias**: Shows where the market "wants" to go
4. **Support/Resistance**: Imbalances create temporary price barriers

### Important Caveats

- Imbalances change rapidly (every 100ms in our system)
- Can be manipulated (fake orders create fake imbalances)
- Not always predictive (orders can be pulled anytime)
- Context matters (news, time of day, overall trend)

> **Note**: The system now only alerts on extreme imbalances (>85%) after a warmup period - these are more likely to be significant rather than normal market noise.
