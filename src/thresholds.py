"""
Whale detection thresholds configuration for different trading pairs.
Each pair can have custom thresholds based on its typical volume and price.
"""

# Default thresholds for pairs not explicitly configured
DEFAULT_THRESHOLDS = {
    "whale": 500000,  # $500K
    "mega_whale": 2000000  # $2M
}

# Per-pair threshold configuration
PAIR_THRESHOLDS = {
    "BTCUSDT": {
        "whale": 1000000,  # $1M - Higher for BTC due to high volume
        "mega_whale": 5000000  # $5M
    },
    "ETHUSDT": {
        "whale": 500000,  # $500K - Medium threshold
        "mega_whale": 2000000  # $2M
    },
    "BNBUSDT": {
        "whale": 300000,  # $300K
        "mega_whale": 1500000  # $1.5M
    },
    "SOLUSDT": {
        "whale": 200000,  # $200K - Lower for smaller cap
        "mega_whale": 1000000  # $1M
    },
    "ADAUSDT": {
        "whale": 200000,  # $200K
        "mega_whale": 1000000  # $1M
    },
    "DOGEUSDT": {
        "whale": 300000,  # $300K
        "mega_whale": 1500000  # $1.5M
    },
    "XRPUSDT": {
        "whale": 300000,  # $300K
        "mega_whale": 1500000  # $1.5M
    },
    "AVAXUSDT": {
        "whale": 200000,  # $200K
        "mega_whale": 1000000  # $1M
    },
    "LINKUSDT": {
        "whale": 200000,  # $200K
        "mega_whale": 1000000  # $1M
    },
    "MATICUSDT": {
        "whale": 200000,  # $200K - Lower cap, easily manipulated
        "mega_whale": 1000000  # $1M
    },
    "ARBUSDT": {
        "whale": 30000,  # $300K - Layer 2 token, medium manipulation risk
        "mega_whale": 150000  # $1.5M
    },
    "INJUSDT": {
        "whale": 25000,  # $250K - DeFi token, volatile
        "mega_whale": 120000  # $1.2M
    },
    "FETUSDT": {
        "whale": 20000,  # $200K - AI token, highly speculative
        "mega_whale": 100000  # $1M
    },
    "SEIUSDT": {
        "whale": 50000,  # $50K - Layer 1 blockchain, moderate volume, 97.8% manipulation rate observed
        "mega_whale": 250000  # $250K
    },
    
    # === CATEGORY 1: EXTREME MANIPULATION - MEME COINS ===
    # Research shows meme coins are most susceptible to pump & dump schemes
    "PEPEUSDT": {
        "whale": 25000,  # $25K - Ultra high manipulation, low liquidity
        "mega_whale": 125000  # $125K
    },
    "BONKUSDT": {
        "whale": 20000,  # $20K - Most volatile per 2025 data
        "mega_whale": 100000  # $100K
    },
    "WIFUSDT": {  # DogWifHat
        "whale": 30000,  # $30K - High volatility, whale target
        "mega_whale": 150000  # $150K
    },
    "SHIBUSDT": {
        "whale": 40000,  # $40K - High retail interest, easy to spoof
        "mega_whale": 200000  # $200K
    },
    "FLOKIUSDT": {
        "whale": 15000,  # $15K - Small cap, extreme manipulation
        "mega_whale": 75000  # $75K
    },
    
    # === CATEGORY 2: AI NARRATIVE - HIGH VOLATILITY ===
    # AI tokens show 50-70% daily swings, perfect for spoofing
    "WLDUSDT": {
        "whale": 50000,  # $50K - Worldcoin, narrative driven
        "mega_whale": 250000  # $250K
    },
    "RNDR": {
        "whale": 40000,  # $40K - Render Token, GPU/AI
        "mega_whale": 200000  # $200K
    },
    "FETUSDT": {
        "whale": 20000,  # $20K - Fetch.ai, highly speculative
        "mega_whale": 100000  # $100K
    },
    "AGIXUSDT": {
        "whale": 25000,  # $25K - SingularityNET
        "mega_whale": 125000  # $125K
    },
    "OCEANUSDT": {
        "whale": 15000,  # $15K - Ocean Protocol
        "mega_whale": 75000  # $75K
    },
    
    # === CATEGORY 3: GAMING/METAVERSE - PUMP PRONE ===
    # Stop hunting common, 30-40% daily moves
    "SANDUSDT": {
        "whale": 30000,  # $30K - Sandbox, retail heavy
        "mega_whale": 150000  # $150K
    },
    "AXSUSDT": {
        "whale": 35000,  # $35K - Axie, comeback narrative
        "mega_whale": 175000  # $175K
    },
    "MANA": {
        "whale": 25000,  # $25K - Decentraland
        "mega_whale": 125000  # $125K
    },
    "IMXUSDT": {
        "whale": 20000,  # $20K - Immutable X
        "mega_whale": 100000  # $100K
    },
    "GALAUSDT": {
        "whale": 15000,  # $15K - Gala Games
        "mega_whale": 75000  # $75K
    },
    
    # === CATEGORY 4: LAYER 2s - MODERATE MANIPULATION ===
    # 20-30% moves, wash trading common
    "ARBUSDT": {
        "whale": 30000,  # $30K - Arbitrum, high speculation
        "mega_whale": 150000  # $150K
    },
    "OPUSDT": {
        "whale": 35000,  # $35K - Optimism
        "mega_whale": 175000  # $175K
    },
    "STRKUSDT": {
        "whale": 25000,  # $25K - StarkNet, new listing
        "mega_whale": 125000  # $125K
    },
    
    # === CATEGORY 5: LOW CAP ALTS - EASIEST TARGETS ===
    # Under $100M cap, 50%+ daily moves possible
    "CELRUSDT": {
        "whale": 10000,  # $10K - Celer, thin books
        "mega_whale": 50000  # $50K
    },
    "ANKRUSDT": {
        "whale": 8000,  # $8K - Ankr, low liquidity
        "mega_whale": 40000  # $40K
    },
    "SPELLUSDT": {
        "whale": 5000,  # $5K - Spell Token, extreme low cap
        "mega_whale": 25000  # $25K
    },
    "LRCUSDT": {
        "whale": 15000,  # $15K - Loopring
        "mega_whale": 75000  # $75K
    },
    "CTSIUSDT": {
        "whale": 12000,  # $12K - Cartesi
        "mega_whale": 60000  # $60K
    },
    
    # === CATEGORY 6: NEW LISTINGS - EXTREME VOLATILITY ===
    # First 30 days = manipulation heaven
    "SUIUSDT": {
        "whale": 60000,  # $60K - Move-based L1
        "mega_whale": 300000  # $300K
    },
    "APTUSDT": {
        "whale": 70000,  # $70K - Aptos, VC backed
        "mega_whale": 350000  # $350K
    },
    "CFXUSDT": {
        "whale": 20000,  # $20K - Conflux, China narrative
        "mega_whale": 100000  # $100K
    },
    "IDUSDT": {
        "whale": 15000,  # $15K - Space ID
        "mega_whale": 75000  # $75K
    },
    
    # === CATEGORY 7: DEFI LOW CAPS - LIQUIDITY GAMES ===
    # Perfect for wash trading and spoofing
    "PERPUSDT": {
        "whale": 10000,  # $10K - Perpetual Protocol
        "mega_whale": 50000  # $50K
    },
    "GMXUSDT": {
        "whale": 30000,  # $30K - GMX
        "mega_whale": 150000  # $150K
    },
    "DYDX": {
        "whale": 25000,  # $25K - dYdX
        "mega_whale": 125000  # $125K
    }
}

def get_thresholds(symbol: str) -> dict:
    """
    Get whale thresholds for a specific trading pair.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT')
    
    Returns:
        Dictionary with 'whale' and 'mega_whale' thresholds
    """
    return PAIR_THRESHOLDS.get(symbol, DEFAULT_THRESHOLDS).copy()

def get_alert_threshold(symbol: str) -> float:
    """
    Get the alert threshold for Telegram notifications.
    This is typically 1.5x the mega whale threshold.
    
    Args:
        symbol: Trading pair symbol
    
    Returns:
        Alert threshold in USD
    """
    thresholds = get_thresholds(symbol)
    return thresholds["mega_whale"] * 1.5