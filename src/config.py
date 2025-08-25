from typing import List, Dict, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator
from dotenv import load_dotenv
import os
import sys
from src.thresholds import get_thresholds, get_monitoring_group

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
    
    # Monitoring Group (1-5 for grouped monitoring, 0 for custom symbols)
    monitoring_group: int = Field(
        default=0,
        env="MONITORING_GROUP"
    )
    
    # Order Book Settings
    order_book_depth: int = Field(default=20, env="ORDER_BOOK_DEPTH")
    order_book_update_speed: str = Field(default="100ms", env="ORDER_BOOK_UPDATE_SPEED")
    
    # Whale Detection Thresholds (USD)
    whale_order_threshold: float = Field(default=100000, env="WHALE_ORDER_THRESHOLD")
    mega_whale_order_threshold: float = Field(default=500000, env="MEGA_WHALE_ORDER_THRESHOLD")
    
    # Storage Configuration
    csv_logging_enabled: bool = Field(default=False, env="CSV_LOGGING_ENABLED")  # Disabled by default - using InfluxDB
    
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
    
    # InfluxDB Configuration (Primary storage)
    influxdb_url: str = Field(default="http://localhost:8086", env="INFLUXDB_URL")
    influxdb_token: str = Field(default="", env="INFLUXDB_TOKEN")
    influxdb_org: str = Field(default="bitpulse", env="INFLUXDB_ORG")
    influxdb_bucket: str = Field(default="whale_analytics", env="INFLUXDB_BUCKET")
    influxdb_enabled: bool = Field(default=True, env="INFLUXDB_ENABLED")
    
    
    model_config = {
        "env_file": ".env",
        "extra": "ignore"  # Ignore extra fields from env
    }
        
    
    @property
    def symbols_list(self) -> List[str]:
        # Check if running with --group argument
        if len(sys.argv) > 1:
            try:
                # Support both --group N and just N formats
                arg = sys.argv[-1]  # Get last argument
                if arg.startswith('--group'):
                    # Extract number after --group
                    if '=' in arg:
                        group_num = int(arg.split('=')[1])
                    else:
                        # Next argument should be the number
                        idx = sys.argv.index(arg)
                        if idx + 1 < len(sys.argv):
                            group_num = int(sys.argv[idx + 1])
                        else:
                            raise ValueError("--group requires a number")
                else:
                    # Try to parse as direct number
                    group_num = int(arg)
                
                # Validate group number and return pairs
                if 1 <= group_num <= 5:
                    return get_monitoring_group(group_num)
            except (ValueError, IndexError):
                pass  # Fall through to normal symbol handling
        
        # Check environment variable for monitoring group
        if self.monitoring_group > 0:
            try:
                return get_monitoring_group(self.monitoring_group)
            except ValueError:
                pass  # Fall through to normal symbol handling
        
        # Default: use symbols from config/env
        if isinstance(self.symbols, str):
            return [s.strip() for s in self.symbols.split(",")]
        return self.symbols
    
    def get_whale_thresholds(self, symbol: str) -> Dict[str, float]:
        """Get whale thresholds for a specific symbol from thresholds.py"""
        return get_thresholds(symbol)


config = Config()