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
        "whale": 50000,  # $50K - Layer 1 blockchain, moderate volume
        "mega_whale": 250000  # $250K
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