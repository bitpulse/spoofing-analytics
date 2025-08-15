from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()


class Config(BaseSettings):
    # Binance Configuration
    binance_ws_base_url: str = Field(
        default="wss://fstream.binance.com",
        env="BINANCE_WS_BASE_URL"
    )
    binance_rest_base_url: str = Field(
        default="https://fapi.binance.com",
        env="BINANCE_REST_BASE_URL"
    )
    
    # Trading Pairs
    symbols: str = Field(
        default="BTCUSDT",
        env="SYMBOLS"
    )
    
    # Order Book Settings
    order_book_depth: int = Field(default=20, env="ORDER_BOOK_DEPTH")
    order_book_update_speed: str = Field(default="100ms", env="ORDER_BOOK_UPDATE_SPEED")
    
    # Whale Detection Thresholds (USD)
    whale_order_threshold: float = Field(default=100000, env="WHALE_ORDER_THRESHOLD")
    mega_whale_order_threshold: float = Field(default=500000, env="MEGA_WHALE_ORDER_THRESHOLD")
    
    # Storage Configuration
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # Database URL for historical data
    database_url: str = Field(
        default="postgresql://user:password@localhost/whale_analytics",
        env="DATABASE_URL"
    )
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/whale_analytics.log", env="LOG_FILE")
    
    # Monitoring
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    # Telegram Alerts
    telegram_bot_token: str = Field(default="", env="TELEGRAM_BOT_TOKEN")
    telegram_channel_id: str = Field(default="", env="TELEGRAM_CHANNEL_ID")
    telegram_alerts_enabled: bool = Field(default=False, env="TELEGRAM_ALERTS_ENABLED")
    
    model_config = {
        "env_file": ".env"
    }
        
    @property
    def symbols_list(self) -> List[str]:
        if isinstance(self.symbols, str):
            return [s.strip() for s in self.symbols.split(",")]
        return self.symbols


config = Config()