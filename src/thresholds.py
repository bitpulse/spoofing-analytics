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
    "1000PEPEUSDT": {
        "whale": 25000,  # $25K - Ultra high manipulation, low liquidity
        "mega_whale": 125000  # $125K
    },
    "PEPEUSDT": {  # Keep for compatibility
        "whale": 25000,  # $25K - Ultra high manipulation, low liquidity
        "mega_whale": 125000  # $125K
    },
    "1000BONKUSDT": {
        "whale": 20000,  # $20K - Most volatile per 2025 data
        "mega_whale": 100000  # $100K
    },
    "BONKUSDT": {  # Keep for compatibility
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
    "DYDXUSDT": {  # Fixed: Added USDT suffix for consistency
        "whale": 25000,  # $25K - dYdX
        "mega_whale": 125000  # $125K
    },
    
    # === ADDITIONAL HIGH-MANIPULATION PAIRS ===
    # New meme coins and volatile alts for 50-pair monitoring
    "ACTUSDT": {  # AI Prophecy meme
        "whale": 15000,  # $15K - Recent 1000% pump
        "mega_whale": 75000  # $75K
    },
    "PNUTUSDT": {  # Peanut the Squirrel
        "whale": 20000,  # $20K - Extreme volatility
        "mega_whale": 100000  # $100K
    },
    "NEIROUSDT": {  # NEIRO meme
        "whale": 10000,  # $10K - New listing
        "mega_whale": 50000  # $50K
    },
    "MEMEUSDT": {  # MEME coin
        "whale": 25000,  # $25K
        "mega_whale": 125000  # $125K
    },
    "DOGSUSDT": {  # Dogs community
        "whale": 15000,  # $15K
        "mega_whale": 75000  # $75K
    },
    "ENJUSDT": {  # Enjin gaming
        "whale": 20000,  # $20K
        "mega_whale": 100000  # $100K
    },
    "MANAUSDT": {  # Decentraland full symbol
        "whale": 25000,  # $25K
        "mega_whale": 125000  # $125K
    },
    "BLURUSDT": {  # Blur NFT marketplace
        "whale": 30000,  # $30K
        "mega_whale": 150000  # $150K
    },
    "HOOKUSDT": {  # Hooked Protocol
        "whale": 15000,  # $15K
        "mega_whale": 75000  # $75K
    },
    "MAGICUSDT": {  # Magic gaming
        "whale": 20000,  # $20K
        "mega_whale": 100000  # $100K
    },
    "DOTUSDT": {  # Polkadot
        "whale": 100000,  # $100K
        "mega_whale": 500000  # $500K
    },
    "NEARUSDT": {  # NEAR Protocol
        "whale": 80000,  # $80K
        "mega_whale": 400000  # $400K
    },
    "ATOMUSDT": {  # Cosmos
        "whale": 70000,  # $70K
        "mega_whale": 350000  # $350K
    },
    "FTMUSDT": {  # Fantom
        "whale": 40000,  # $40K
        "mega_whale": 200000  # $200K
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

# Strategy-specific configuration
STRATEGY_CONFIG = {
    "spoofing_detection": {
        "duration_threshold": 60,  # Orders that disappear within 60 seconds
        "confidence": 0.8
    },
    "wall_fade": {
        "book_percentage": 50,  # Walls that dominate >50% of book
        "quick_disappear": 60,  # Spoofing if disappears in 60s
        "persistent_time": 300,  # Persistent if lasts >5 minutes
        "confidence_spoof": 0.7,
        "confidence_persistent": 0.6
    },
    "whale_accumulation": {
        "min_whale_count": 3,  # Need at least 3 whales
        "time_window": 5,  # Within 5 minute window
        "avg_book_percentage": 20,  # Average >20% of book
        "confidence": 0.75
    },
    "imbalance_momentum": {
        "imbalance_threshold": 0.5,  # >50% imbalance
        "time_window": 1,  # Check whale presence within 1 minute
        "confidence": 0.65
    },
    "mega_whale_reversal": {
        "confidence": 0.85
    },
    # Trading parameters
    "position_sizing": {
        "target_gain": 0.02,  # 2% default target
        "stop_loss": 0.02,    # 2% default stop
        "max_hold_time": 3600  # 1 hour max hold
    }
}

def get_strategy_config(strategy_name: str) -> dict:
    """
    Get configuration for a specific trading strategy.
    
    Args:
        strategy_name: Name of the strategy
    
    Returns:
        Strategy configuration dictionary
    """
    return STRATEGY_CONFIG.get(strategy_name, {}).copy()

# === MONITORING GROUPS FOR PARALLEL EXECUTION ===
# Each group contains 10 pairs optimized for manipulation detection
# Run with: python -m src.whale_monitor --group 1 (or 2,3,4,5)
MONITORING_GROUPS = {
    # Group 1: Ultra High Risk - Meme Coins & New Listings
    # Most prone to pump & dump, requires lowest thresholds
    1: [
        "1000PEPEUSDT",  # Meme king, 97% manipulation rate
        "1000BONKUSDT",  # Most volatile meme
        "WIFUSDT",       # DogWifHat, whale playground  
        "FLOKIUSDT",     # Small cap, extreme swings
        "SHIBUSDT",      # Retail magnet, easy to spoof
        "ACTUSDT",       # AI Prophecy, recent pump
        "PNUTUSDT",      # Peanut Squirrel, 1000% surge history
        "NEIROUSDT",     # New meme, high volatility
        "MEMEUSDT",      # Meta meme coin
        "DOGSUSDT"       # Dogs community token
    ],
    
    # Group 2: AI & Gaming Narrative - Heavy Speculation
    # 50-70% daily swings, narrative-driven manipulation
    2: [
        "WLDUSDT",       # Worldcoin, Sam Altman hype
        "FETUSDT",       # Fetch.ai, AI leader
        "AGIXUSDT",      # SingularityNET
        "RNDR",          # Render, GPU/AI narrative
        "SANDUSDT",      # Sandbox, metaverse
        "AXSUSDT",       # Axie, gaming comeback
        "IMXUSDT",       # Immutable X, gaming L2
        "GALAUSDT",      # Gala Games
        "ENJUSDT",       # Enjin, gaming infrastructure
        "MANAUSDT"       # Decentraland, virtual land
    ],
    
    # Group 3: Low Cap DeFi & L2s - Liquidity Games
    # Thin order books, perfect for spoofing
    3: [
        "SPELLUSDT",     # Spell Token, ultra low cap
        "ANKRUSDT",      # Ankr, thin liquidity
        "CELRUSDT",      # Celer, easy to move
        "LRCUSDT",       # Loopring, DeFi L2
        "CTSIUSDT",      # Cartesi, low volume
        "PERPUSDT",      # Perpetual Protocol
        "DYDXUSDT",      # dYdX, DEX token
        "GMXUSDT",       # GMX, perp DEX
        "ARBUSDT",       # Arbitrum L2
        "OPUSDT"         # Optimism L2
    ],
    
    # Group 4: Volatile Alts - Manipulation Favorites  
    # Regular 30-50% moves, whale hunting grounds
    4: [
        "SEIUSDT",       # SEI, 97.8% manipulation observed
        "INJUSDT",       # Injective, DeFi volatile
        "APTUSDT",       # Aptos, VC games
        "SUIUSDT",       # Sui, Move-based L1
        "STRKUSDT",      # StarkNet, new L2
        "CFXUSDT",       # Conflux, China pump
        "IDUSDT",        # Space ID, domain names
        "BLURUSDT",      # Blur, NFT marketplace
        "HOOKUSDT",      # Hooked Protocol
        "MAGICUSDT"      # Magic, gaming ecosystem
    ],
    
    # Group 5: Mid-Cap Majors & Established Alts
    # Higher liquidity but still manipulated
    5: [
        "SOLUSDT",       # Solana, meme chain
        "ADAUSDT",       # Cardano, retail heavy
        "DOGEUSDT",      # Original meme
        "AVAXUSDT",      # Avalanche
        "MATICUSDT",     # Polygon, easily moved
        "LINKUSDT",      # Chainlink oracle
        "DOTUSDT",       # Polkadot
        "NEARUSDT",      # NEAR Protocol
        "ATOMUSDT",      # Cosmos
        "FTMUSDT"        # Fantom
    ]
}

def get_monitoring_group(group_number: int) -> list:
    """
    Get the list of trading pairs for a specific monitoring group.
    
    Args:
        group_number: Group number (1-5)
    
    Returns:
        List of trading pair symbols for the group
    
    Raises:
        ValueError: If group_number is not between 1 and 5
    """
    if group_number not in MONITORING_GROUPS:
        raise ValueError(f"Invalid group number {group_number}. Must be between 1 and 5.")
    return MONITORING_GROUPS[group_number].copy()

def get_all_monitoring_pairs() -> list:
    """
    Get all monitoring pairs across all groups.
    
    Returns:
        List of all 50 trading pairs
    """
    all_pairs = []
    for group_pairs in MONITORING_GROUPS.values():
        all_pairs.extend(group_pairs)
    return all_pairs