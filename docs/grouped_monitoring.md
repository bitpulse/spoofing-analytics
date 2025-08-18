# Grouped Monitoring System

## Overview
The whale analytics system now supports monitoring 50 highly manipulated futures pairs organized into 5 groups of 10 pairs each. This allows running multiple instances in parallel to monitor all pairs effectively.

## Groups Configuration

### Group 1: Ultra High Risk - Meme Coins & New Listings
**Manipulation Rate: 90-97%**
- 1000PEPEUSDT - Meme king with 97% manipulation rate
- 1000BONKUSDT - Most volatile meme coin
- WIFUSDT - DogWifHat, whale playground
- FLOKIUSDT - Small cap, extreme swings
- SHIBUSDT - Retail magnet, easy to spoof
- ACTUSDT - AI Prophecy, recent 1000% pump
- PNUTUSDT - Peanut Squirrel, extreme volatility
- NEIROUSDT - New meme, high volatility
- MEMEUSDT - Meta meme coin
- DOGSUSDT - Dogs community token

### Group 2: AI & Gaming Narrative
**Daily Swings: 50-70%**
- WLDUSDT - Worldcoin (Sam Altman)
- FETUSDT - Fetch.ai
- AGIXUSDT - SingularityNET
- RNDR - Render Token
- SANDUSDT - Sandbox metaverse
- AXSUSDT - Axie Infinity
- IMXUSDT - Immutable X
- GALAUSDT - Gala Games
- ENJUSDT - Enjin
- MANAUSDT - Decentraland

### Group 3: Low Cap DeFi & L2s
**Thin Order Books - Perfect for Spoofing**
- SPELLUSDT - Ultra low cap
- ANKRUSDT - Thin liquidity
- CELRUSDT - Easy to move
- LRCUSDT - Loopring
- CTSIUSDT - Cartesi
- PERPUSDT - Perpetual Protocol
- DYDXUSDT - dYdX
- GMXUSDT - GMX
- ARBUSDT - Arbitrum
- OPUSDT - Optimism

### Group 4: Volatile Alts
**Regular 30-50% Moves**
- SEIUSDT - 97.8% manipulation observed
- INJUSDT - Injective Protocol
- APTUSDT - Aptos
- SUIUSDT - Sui
- STRKUSDT - StarkNet
- CFXUSDT - Conflux
- IDUSDT - Space ID
- BLURUSDT - Blur NFT
- HOOKUSDT - Hooked Protocol
- MAGICUSDT - Magic

### Group 5: Mid-Cap Majors
**Higher Liquidity but Still Manipulated**
- SOLUSDT - Solana
- ADAUSDT - Cardano
- DOGEUSDT - Dogecoin
- AVAXUSDT - Avalanche
- MATICUSDT - Polygon
- LINKUSDT - Chainlink
- DOTUSDT - Polkadot
- NEARUSDT - NEAR Protocol
- ATOMUSDT - Cosmos
- FTMUSDT - Fantom

## Usage

### Single Pair Monitoring
```bash
# Monitor a specific trading pair
python -m src.whale_monitor BTCUSDT        # Monitor Bitcoin
python -m src.whale_monitor ETHUSDT        # Monitor Ethereum
python -m src.whale_monitor --pair SOLUSDT # Alternative syntax
```

### Single Group Monitoring
```bash
# Monitor group 1 (meme coins)
python -m src.whale_monitor 1

# Monitor group 2 (AI/Gaming)
python -m src.whale_monitor 2

# Alternative syntax
python -m src.whale_monitor --group 3
python -m src.whale_monitor --group=4
```

### Parallel Monitoring (All 50 Pairs)
Run each command in a separate terminal or use a process manager:

```bash
# Terminal 1
python -m src.whale_monitor 1

# Terminal 2
python -m src.whale_monitor 2

# Terminal 3
python -m src.whale_monitor 3

# Terminal 4
python -m src.whale_monitor 4

# Terminal 5
python -m src.whale_monitor 5
```

### Using tmux for Parallel Monitoring
```bash
# Create tmux session
tmux new-session -d -s whale-monitor

# Create 5 panes for 5 groups
tmux split-window -h
tmux split-window -v
tmux select-pane -t 0
tmux split-window -v
tmux select-pane -t 2
tmux split-window -v

# Run each group in its pane
tmux send-keys -t 0 'python -m src.whale_monitor 1' C-m
tmux send-keys -t 1 'python -m src.whale_monitor 2' C-m
tmux send-keys -t 2 'python -m src.whale_monitor 3' C-m
tmux send-keys -t 3 'python -m src.whale_monitor 4' C-m
tmux send-keys -t 4 'python -m src.whale_monitor 5' C-m

# Attach to session
tmux attach-session -t whale-monitor
```

### Using systemd for Production
Create service files for each group:

```ini
# /etc/systemd/system/whale-monitor-1.service
[Unit]
Description=Whale Monitor Group 1 - Meme Coins
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/whale-analytics-system
ExecStart=/usr/bin/python -m src.whale_monitor 1
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then start all services:
```bash
sudo systemctl enable whale-monitor-{1..5}.service
sudo systemctl start whale-monitor-{1..5}.service
```

## Resource Requirements

### Per Instance (10 pairs)
- **Memory**: ~250MB
- **CPU**: 5-10% of single core
- **Network**: ~10 Mbps
- **Disk I/O**: Minimal (CSV logging)

### All 5 Instances (50 pairs)
- **Memory**: ~1.25GB
- **CPU**: 25-50% total
- **Network**: ~50 Mbps
- **Disk Space**: ~100MB/day

## Monitoring & Logs

Each group creates separate log files:
- Console output shows real-time whale detection
- CSV files saved to `data/` directory
- Telegram alerts sent for mega whales (if configured)

View logs:
```bash
# View specific group output
tail -f logs/whale_analytics.log | grep "Group 1"

# Monitor all CSV outputs
watch -n 1 'ls -la data/*.csv | tail -10'

# Check system resource usage
htop -p $(pgrep -f "whale_monitor")
```

## Custom Symbol Selection

If you prefer custom symbols instead of groups:
```bash
# Set in .env file
SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT

# Or set via environment
SYMBOLS=BTCUSDT,ETHUSDT python -m src.whale_monitor
```

## Threshold Customization

Each pair has optimized thresholds in `src/thresholds.py`:
- **Whale threshold**: Minimum USD value to classify as whale order
- **Mega whale threshold**: Extreme whale orders triggering alerts
- Thresholds are adjusted based on liquidity and manipulation risk

## Best Practices

1. **Start with one group** to test your setup
2. **Monitor system resources** before running all 5 groups
3. **Use a process manager** (systemd, supervisor, PM2) for production
4. **Set up log rotation** to prevent disk space issues
5. **Configure Telegram alerts** for critical whale activity
6. **Regularly review CSV data** for manipulation patterns

## Troubleshooting

### High Memory Usage
- Reduce `ORDER_BOOK_DEPTH` in .env (default: 20)
- Increase cleanup frequency in main loop

### Connection Issues
- Check Binance API status
- Verify network connectivity
- Review WebSocket reconnection logs

### Missing Data
- Check for update gaps in logs
- Verify all symbols are valid futures pairs
- Ensure sufficient API weight limits