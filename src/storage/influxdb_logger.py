"""
InfluxDB Logger for Whale Analytics System
==========================================

Stores whale order data, price data, and manipulation events in InfluxDB
for time-series analysis and visualization.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from loguru import logger
import time


class InfluxDBLogger:
    def __init__(
        self,
        url: str = "http://localhost:8086",
        token: str = None,
        org: str = "bitpulse",
        bucket: str = "whale_analytics",
        enable: bool = True
    ):
        """
        Initialize InfluxDB logger.
        
        Args:
            url: InfluxDB server URL
            token: Authentication token
            org: Organization name
            bucket: Bucket name for data storage
            enable: Whether to enable logging
        """
        self.enabled = enable and token is not None
        self.error_count = 0
        self.max_errors = 10  # Stop logging errors after 10 failures
        self.last_error_time = 0
        
        if not self.enabled:
            logger.warning("InfluxDB logging disabled or token not provided")
            return
            
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        
        try:
            # Initialize InfluxDB client
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org
            )
            
            # Get write API with synchronous mode for reliability
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            
            # Test connection
            health = self.client.health()
            if health.status == "pass":
                logger.info(f"InfluxDB connection established: {self.url}")
            else:
                logger.warning(f"InfluxDB health check failed: {health.message}")
                self.enabled = False
                
        except Exception as e:
            logger.warning(f"InfluxDB connection failed, will retry later: {e}")
            self.enabled = False
    
    def write_whale_order(self, whale_order: Dict[str, Any], symbol: str):
        """
        Write whale order data to InfluxDB.
        
        Args:
            whale_order: Whale order data
            symbol: Trading pair symbol
        """
        if not self.enabled:
            return
            
        try:
            point = Point("whale_order") \
                .tag("symbol", symbol) \
                .tag("side", whale_order.get("side", "unknown")) \
                .tag("order_id", str(whale_order.get("order_id", ""))) \
                .field("price", float(whale_order.get("price", 0))) \
                .field("quantity", float(whale_order.get("quantity", 0))) \
                .field("value_usd", float(whale_order.get("value_usd", 0))) \
                .field("distance_from_mid_bps", float(whale_order.get("distance_from_mid_bps", 0))) \
                .field("is_mega_whale", whale_order.get("is_mega_whale", False)) \
                .time(datetime.utcnow(), WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, record=point)
            
        except Exception as e:
            logger.error(f"Failed to write whale order to InfluxDB: {e}")
    
    def write_whale_event(self, whale_event: Dict[str, Any]):
        """
        Write whale event data to InfluxDB (matching CSV WhaleEvent dataclass).
        
        Args:
            whale_event: Whale event data matching CSV structure
        """
        if not self.enabled:
            return
            
        try:
            point = Point("whale_event") \
                .tag("symbol", whale_event.get("symbol", "UNKNOWN")) \
                .tag("whale_id", whale_event.get("whale_id", "")) \
                .tag("side", whale_event.get("side", "unknown")) \
                .field("price", float(whale_event.get("price", 0))) \
                .field("size", float(whale_event.get("size", 0))) \
                .field("value_usd", float(whale_event.get("value_usd", 0))) \
                .field("percentage_of_book", float(whale_event.get("percentage_of_book", 0))) \
                .field("level", int(whale_event.get("level", 0))) \
                .field("mid_price", float(whale_event.get("mid_price", 0))) \
                .field("spread_bps", float(whale_event.get("spread_bps", 0))) \
                .field("total_bid_whales", int(whale_event.get("total_bid_whales", 0))) \
                .field("total_ask_whales", int(whale_event.get("total_ask_whales", 0))) \
                .field("bid_depth_1pct", float(whale_event.get("bid_depth_1pct", 0))) \
                .field("ask_depth_1pct", float(whale_event.get("ask_depth_1pct", 0))) \
                .field("volume_imbalance", float(whale_event.get("volume_imbalance", 0))) \
                .field("duration_seconds", float(whale_event.get("duration_seconds", 0))) \
                .field("size_changes_count", int(whale_event.get("size_changes_count", 0))) \
                .field("disappearances", int(whale_event.get("disappearances", 0))) \
                .field("is_new", bool(whale_event.get("is_new", True))) \
                .time(datetime.utcnow(), WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, record=point)
            
        except Exception as e:
            logger.error(f"Failed to write whale event to InfluxDB: {e}")
    
    def write_price_data(self, price_data: Any):
        """
        Write price and market data to InfluxDB.
        
        Args:
            price_data: PriceData dataclass object
        """
        if not self.enabled:
            return
            
        try:
            # Direct access to PriceData dataclass attributes
            point = Point("price_data") \
                .tag("symbol", price_data.symbol) \
                .field("mid_price", float(price_data.mid_price)) \
                .field("best_bid", float(price_data.bid_price)) \
                .field("best_ask", float(price_data.ask_price)) \
                .field("last_price", float(price_data.last_price)) \
                .field("mark_price", float(price_data.mark_price)) \
                .field("index_price", float(price_data.index_price)) \
                .field("volume_24h", float(price_data.volume_24h)) \
                .field("volume_usd_24h", float(price_data.volume_usd_24h)) \
                .field("trade_count_24h", int(price_data.trade_count_24h)) \
                .field("buy_volume_5min", float(price_data.buy_volume_5min)) \
                .field("sell_volume_5min", float(price_data.sell_volume_5min)) \
                .field("trade_count_5min", int(price_data.trade_count_5min)) \
                .field("price_change_1min", float(price_data.price_change_1min)) \
                .field("price_change_5min", float(price_data.price_change_5min)) \
                .field("price_change_1h", float(price_data.price_change_1h)) \
                .field("high_5min", float(price_data.high_5min)) \
                .field("low_5min", float(price_data.low_5min)) \
                .field("active_whale_count", int(price_data.active_whale_count)) \
                .field("recent_spoof_count", int(price_data.recent_spoof_count)) \
                .field("whale_bid_value", float(price_data.whale_bid_value)) \
                .field("whale_ask_value", float(price_data.whale_ask_value)) \
                .field("funding_rate", float(price_data.funding_rate)) \
                .field("open_interest", float(price_data.open_interest)) \
                .field("liquidations_5min", float(price_data.liquidations_5min)) \
                .time(datetime.utcnow(), WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, record=point)
            
        except Exception as e:
            logger.error(f"Failed to write price data to InfluxDB: {e}")
    
    def write_manipulation_event(self, event: Dict[str, Any]):
        """
        Write manipulation detection event to InfluxDB.
        
        Args:
            event: Manipulation event data
        """
        if not self.enabled:
            return
            
        try:
            point = Point("manipulation_event") \
                .tag("symbol", event.get("symbol", "UNKNOWN")) \
                .tag("type", event.get("type", "unknown")) \
                .tag("side", event.get("side", "unknown")) \
                .field("confidence", float(event.get("confidence", 0))) \
                .field("order_value_usd", float(event.get("order_value_usd", 0))) \
                .field("price", float(event.get("price", 0))) \
                .field("distance_from_mid_bps", float(event.get("distance_from_mid_bps", 0))) \
                .field("duration_seconds", int(event.get("duration_seconds", 0))) \
                .field("description", event.get("description", "")) \
                .time(datetime.utcnow(), WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, record=point)
            
        except Exception as e:
            logger.error(f"Failed to write manipulation event to InfluxDB: {e}")
    
    def write_order_book_snapshot(self, snapshot: Any):
        """
        Write order book snapshot summary to InfluxDB.
        
        Args:
            snapshot: OrderBookSnapshot object
        """
        if not self.enabled:
            return
            
        try:
            # Calculate metrics
            total_bid_volume = sum(order.size for order in snapshot.bids[:20])
            total_ask_volume = sum(order.size for order in snapshot.asks[:20])
            
            point = Point("order_book_snapshot") \
                .tag("symbol", snapshot.symbol) \
                .field("mid_price", float(snapshot.mid_price)) \
                .field("spread_bps", float(snapshot.spread_bps)) \
                .field("bid_depth_20", float(total_bid_volume)) \
                .field("ask_depth_20", float(total_ask_volume)) \
                .field("volume_imbalance", float((total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume) if (total_bid_volume + total_ask_volume) > 0 else 0)) \
                .field("whale_bid_count", len(snapshot.whale_bids)) \
                .field("whale_ask_count", len(snapshot.whale_asks)) \
                .field("update_id", snapshot.update_id) \
                .time(datetime.utcnow(), WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, record=point)
            
            # Write individual whale orders
            for whale in snapshot.whale_bids:
                self.write_whale_order({
                    "side": "bid",
                    "price": whale.price,
                    "quantity": whale.size,
                    "value_usd": whale.value_usd,
                    "distance_from_mid_bps": whale.distance_from_mid_bps,
                    "is_mega_whale": whale.is_mega_whale,
                    "order_id": id(whale)  # Use object id as unique identifier
                }, snapshot.symbol)
            
            for whale in snapshot.whale_asks:
                self.write_whale_order({
                    "side": "ask",
                    "price": whale.price,
                    "quantity": whale.size,
                    "value_usd": whale.value_usd,
                    "distance_from_mid_bps": whale.distance_from_mid_bps,
                    "is_mega_whale": whale.is_mega_whale,
                    "order_id": id(whale)
                }, snapshot.symbol)
                
        except Exception as e:
            # Rate limit error logging
            current_time = time.time()
            if self.error_count < self.max_errors:
                if current_time - self.last_error_time > 60:  # Only log once per minute
                    logger.error(f"Failed to write order book snapshot to InfluxDB: {e}")
                    self.error_count += 1
                    self.last_error_time = current_time
                    if self.error_count == self.max_errors:
                        logger.warning("InfluxDB write errors exceeded limit, suppressing further errors")
    
    def write_spoofing_detection(self, symbol: str, spoofed_orders: List[Dict[str, Any]]):
        """
        Write spoofing detection results to InfluxDB.
        
        Args:
            symbol: Trading pair symbol
            spoofed_orders: List of detected spoofed orders
        """
        if not self.enabled:
            return
            
        try:
            for order in spoofed_orders:
                point = Point("spoofing_detection") \
                    .tag("symbol", symbol) \
                    .tag("side", order.get("side", "unknown")) \
                    .field("price", float(order.get("price", 0))) \
                    .field("original_quantity", float(order.get("original_quantity", 0))) \
                    .field("value_usd", float(order.get("value_usd", 0))) \
                    .field("lifetime_seconds", int(order.get("lifetime_seconds", 0))) \
                    .field("disappeared_at", order.get("disappeared_at", "")) \
                    .field("confidence_score", float(order.get("confidence_score", 0))) \
                    .time(datetime.utcnow(), WritePrecision.NS)
                
                self.write_api.write(bucket=self.bucket, record=point)
                
        except Exception as e:
            logger.error(f"Failed to write spoofing detection to InfluxDB: {e}")
    
    def write_spoofing_event(self, spoof_event: Dict[str, Any]):
        """
        Write spoofing event data to InfluxDB (matching CSV SpoofingEvent dataclass).
        
        Args:
            spoof_event: Spoofing event data matching CSV structure
        """
        if not self.enabled:
            return
            
        try:
            point = Point("spoofing_event") \
                .tag("symbol", spoof_event.get("symbol", "UNKNOWN")) \
                .tag("whale_id", spoof_event.get("whale_id", "")) \
                .tag("side", spoof_event.get("side", "unknown")) \
                .tag("spoof_pattern", spoof_event.get("spoof_pattern", "unknown")) \
                .field("price", float(spoof_event.get("price", 0))) \
                .field("initial_size", float(spoof_event.get("initial_size", 0))) \
                .field("final_size", float(spoof_event.get("final_size", 0))) \
                .field("initial_value_usd", float(spoof_event.get("initial_value_usd", 0))) \
                .field("final_value_usd", float(spoof_event.get("final_value_usd", 0))) \
                .field("time_active_seconds", float(spoof_event.get("time_active_seconds", 0))) \
                .field("percentage_of_book", float(spoof_event.get("percentage_of_book", 0))) \
                .field("size_changes_count", int(spoof_event.get("size_changes_count", 0))) \
                .field("disappearances", int(spoof_event.get("disappearances", 0))) \
                .field("max_size_seen", float(spoof_event.get("max_size_seen", 0))) \
                .field("min_size_seen", float(spoof_event.get("min_size_seen", 0))) \
                .field("size_variance_pct", float(spoof_event.get("size_variance_pct", 0))) \
                .time(datetime.utcnow(), WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, record=point)
            
        except Exception as e:
            logger.error(f"Failed to write spoofing event to InfluxDB: {e}")
    
    def write_market_metrics(self, symbol: str, metrics: Dict[str, Any]):
        """
        Write aggregated market metrics to InfluxDB.
        
        Args:
            symbol: Trading pair symbol
            metrics: Market metrics dictionary
        """
        if not self.enabled:
            return
            
        try:
            point = Point("market_metrics") \
                .tag("symbol", symbol) \
                .field("whale_activity_score", float(metrics.get("whale_activity_score", 0))) \
                .field("manipulation_score", float(metrics.get("manipulation_score", 0))) \
                .field("volatility", float(metrics.get("volatility", 0))) \
                .field("liquidity_depth", float(metrics.get("liquidity_depth", 0))) \
                .field("order_flow_imbalance", float(metrics.get("order_flow_imbalance", 0))) \
                .time(datetime.utcnow(), WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, record=point)
            
        except Exception as e:
            logger.error(f"Failed to write market metrics to InfluxDB: {e}")
    
    def write_market_snapshot(self, snapshot: Dict[str, Any]):
        """
        Write market snapshot data to InfluxDB (matching CSV MarketSnapshot dataclass).
        
        Args:
            snapshot: Market snapshot data matching CSV structure
        """
        if not self.enabled:
            return
            
        try:
            point = Point("market_snapshot") \
                .tag("symbol", snapshot.get("symbol", "UNKNOWN")) \
                .field("mid_price", float(snapshot.get("mid_price", 0))) \
                .field("spread_bps", float(snapshot.get("spread_bps", 0))) \
                .field("total_whale_count", int(snapshot.get("total_whale_count", 0))) \
                .field("bid_whale_count", int(snapshot.get("bid_whale_count", 0))) \
                .field("ask_whale_count", int(snapshot.get("ask_whale_count", 0))) \
                .field("whale_imbalance", int(snapshot.get("whale_imbalance", 0))) \
                .field("volume_imbalance", float(snapshot.get("volume_imbalance", 0))) \
                .field("bid_volume_usd", float(snapshot.get("bid_volume_usd", 0))) \
                .field("ask_volume_usd", float(snapshot.get("ask_volume_usd", 0))) \
                .field("bid_depth_1pct", float(snapshot.get("bid_depth_1pct", 0))) \
                .field("ask_depth_1pct", float(snapshot.get("ask_depth_1pct", 0))) \
                .field("largest_bid_whale", float(snapshot.get("largest_bid_whale", 0))) \
                .field("largest_ask_whale", float(snapshot.get("largest_ask_whale", 0))) \
                .field("support_level", float(snapshot.get("support_level", 0)) if snapshot.get("support_level") is not None else 0) \
                .field("resistance_level", float(snapshot.get("resistance_level", 0)) if snapshot.get("resistance_level") is not None else 0) \
                .time(datetime.utcnow(), WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, record=point)
            
        except Exception as e:
            logger.error(f"Failed to write market snapshot to InfluxDB: {e}")
    
    def write_alert_event(self, alert: Dict[str, Any]):
        """
        Write alert event data to InfluxDB (matching CSV AlertEvent dataclass).
        
        Args:
            alert: Alert event data matching CSV structure
        """
        if not self.enabled:
            return
            
        try:
            point = Point("alert_event") \
                .tag("symbol", alert.get("symbol", "UNKNOWN")) \
                .tag("alert_type", alert.get("alert_type", "unknown")) \
                .tag("alert_subtype", alert.get("alert_subtype", "unknown")) \
                .tag("severity", alert.get("severity", "info")) \
                .tag("side", alert.get("side", "n/a")) \
                .field("price", float(alert.get("price", 0))) \
                .field("value_usd", float(alert.get("value_usd", 0))) \
                .field("percentage_of_book", float(alert.get("percentage_of_book", 0))) \
                .field("message", str(alert.get("message", ""))) \
                .field("whale_id", str(alert.get("whale_id", "")) if alert.get("whale_id") else "") \
                .field("time_active_seconds", float(alert.get("time_active_seconds", 0)) if alert.get("time_active_seconds") is not None else 0) \
                .field("volume_imbalance", float(alert.get("volume_imbalance", 0)) if alert.get("volume_imbalance") is not None else 0) \
                .field("bid_volume_usd", float(alert.get("bid_volume_usd", 0)) if alert.get("bid_volume_usd") is not None else 0) \
                .field("ask_volume_usd", float(alert.get("ask_volume_usd", 0)) if alert.get("ask_volume_usd") is not None else 0) \
                .field("whale_count", int(alert.get("whale_count", 0)) if alert.get("whale_count") is not None else 0) \
                .field("bid_whale_count", int(alert.get("bid_whale_count", 0)) if alert.get("bid_whale_count") is not None else 0) \
                .field("ask_whale_count", int(alert.get("ask_whale_count", 0)) if alert.get("ask_whale_count") is not None else 0) \
                .field("trigger_threshold", float(alert.get("trigger_threshold", 0)) if alert.get("trigger_threshold") is not None else 0) \
                .field("was_throttled", bool(alert.get("was_throttled", False))) \
                .time(datetime.utcnow(), WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, record=point)
            
        except Exception as e:
            logger.error(f"Failed to write alert event to InfluxDB: {e}")
    
    def log_whale_from_dict(self, whale_data: Dict[str, Any], snapshot_data: Dict[str, Any] = None):
        """Convenience method to log whale from dictionary (matching CSV logger)."""
        if not self.enabled:
            return
            
        whale_event = {
            "timestamp": datetime.now().isoformat(),
            "symbol": whale_data.get('symbol', 'UNKNOWN'),
            "whale_id": whale_data.get('whale_id', ''),
            "side": whale_data.get('side', ''),
            "price": whale_data.get('price', 0),
            "size": whale_data.get('size', 0),
            "value_usd": whale_data.get('value_usd', 0),
            "percentage_of_book": whale_data.get('percentage_of_book', 0),
            "level": whale_data.get('level', 0),
            "mid_price": snapshot_data.get('mid_price', 0) if snapshot_data else 0,
            "spread_bps": snapshot_data.get('spread_bps', 0) if snapshot_data else 0,
            "total_bid_whales": snapshot_data.get('total_bid_whales', 0) if snapshot_data else 0,
            "total_ask_whales": snapshot_data.get('total_ask_whales', 0) if snapshot_data else 0,
            "bid_depth_1pct": snapshot_data.get('bid_depth_1pct', 0) if snapshot_data else 0,
            "ask_depth_1pct": snapshot_data.get('ask_depth_1pct', 0) if snapshot_data else 0,
            "volume_imbalance": snapshot_data.get('volume_imbalance', 0) if snapshot_data else 0,
            "duration_seconds": whale_data.get('duration_seconds', 0),
            "size_changes_count": whale_data.get('size_changes_count', 0),
            "disappearances": whale_data.get('disappearances', 0),
            "is_new": whale_data.get('is_new', True)
        }
        self.write_whale_event(whale_event)
    
    def log_spoofing_from_dict(self, spoof_data: Dict[str, Any]):
        """Convenience method to log spoofing from dictionary (matching CSV logger)."""
        if not self.enabled:
            return
            
        # Determine spoof pattern
        if spoof_data.get('disappearances', 0) >= 3:
            pattern = 'flickering'
        elif spoof_data.get('size_variance_pct', 0) > 50:
            pattern = 'size_manipulation'
        else:
            pattern = 'single'
            
        spoof_event = {
            "timestamp": datetime.now().isoformat(),
            "symbol": spoof_data.get('symbol', 'UNKNOWN'),
            "whale_id": spoof_data.get('whale_id', ''),
            "side": spoof_data.get('side', ''),
            "price": spoof_data.get('initial_price', 0),
            "initial_size": spoof_data.get('initial_size', 0),
            "final_size": spoof_data.get('current_size', 0),
            "initial_value_usd": spoof_data.get('initial_value_usd', 0),
            "final_value_usd": spoof_data.get('current_value_usd', 0),
            "time_active_seconds": spoof_data.get('duration_seconds', 0),
            "percentage_of_book": spoof_data.get('percentage_of_book', 0),
            "size_changes_count": spoof_data.get('size_changes_count', 0),
            "disappearances": spoof_data.get('disappearances', 0),
            "max_size_seen": spoof_data.get('max_size_seen', 0),
            "min_size_seen": spoof_data.get('min_size_seen', 0),
            "size_variance_pct": spoof_data.get('size_variance_pct', 0),
            "spoof_pattern": pattern
        }
        self.write_spoofing_event(spoof_event)
    
    def log_snapshot_from_dict(self, snapshot: Any):
        """Log market snapshot from OrderBookSnapshot object (matching CSV logger)."""
        if not self.enabled:
            return
            
        market_snapshot = {
            "timestamp": datetime.now().isoformat(),
            "symbol": snapshot.symbol,
            "mid_price": snapshot.mid_price,
            "spread_bps": snapshot.spread_bps,
            "total_whale_count": len(snapshot.whale_bids) + len(snapshot.whale_asks),
            "bid_whale_count": len(snapshot.whale_bids),
            "ask_whale_count": len(snapshot.whale_asks),
            "whale_imbalance": snapshot.whale_imbalance,
            "volume_imbalance": snapshot.volume_imbalance,
            "bid_volume_usd": snapshot.bid_volume_value,
            "ask_volume_usd": snapshot.ask_volume_value,
            "bid_depth_1pct": snapshot.depth_1_percent if hasattr(snapshot, 'depth_1_percent') else 0,
            "ask_depth_1pct": 0,  # Could calculate separately
            "largest_bid_whale": max([w.value_usd for w in snapshot.whale_bids], default=0),
            "largest_ask_whale": max([w.value_usd for w in snapshot.whale_asks], default=0),
            "support_level": snapshot.support_level,
            "resistance_level": snapshot.resistance_level
        }
        self.write_market_snapshot(market_snapshot)
    
    def log_alert(self, alert_event):
        """Log alert event (matching CSV logger)."""
        if not self.enabled:
            return
            
        # Convert dataclass to dict if needed
        if hasattr(alert_event, '__dict__'):
            alert_dict = vars(alert_event)
        else:
            alert_dict = alert_event
            
        self.write_alert_event(alert_dict)
    
    def close(self):
        """Close InfluxDB connection."""
        if self.enabled and hasattr(self, 'client'):
            try:
                self.client.close()
                logger.info("InfluxDB connection closed")
            except Exception as e:
                logger.error(f"Error closing InfluxDB connection: {e}")