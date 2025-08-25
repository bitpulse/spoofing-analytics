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
    
    def write_price_data(self, price_data: Dict[str, Any]):
        """
        Write price and market data to InfluxDB.
        
        Args:
            price_data: Price and market data
        """
        if not self.enabled:
            return
            
        try:
            symbol = price_data.get("symbol", "UNKNOWN")
            
            point = Point("price_data") \
                .tag("symbol", symbol) \
                .field("mid_price", float(price_data.get("mid_price", 0))) \
                .field("best_bid", float(price_data.get("best_bid", 0))) \
                .field("best_ask", float(price_data.get("best_ask", 0))) \
                .field("spread_usd", float(price_data.get("spread_usd", 0))) \
                .field("spread_bps", float(price_data.get("spread_bps", 0))) \
                .field("bid_liquidity_1pct", float(price_data.get("bid_liquidity_1pct", 0))) \
                .field("ask_liquidity_1pct", float(price_data.get("ask_liquidity_1pct", 0))) \
                .field("bid_whale_count", int(price_data.get("bid_whale_count", 0))) \
                .field("ask_whale_count", int(price_data.get("ask_whale_count", 0))) \
                .field("bid_whale_value", float(price_data.get("bid_whale_value", 0))) \
                .field("ask_whale_value", float(price_data.get("ask_whale_value", 0))) \
                .field("liquidity_imbalance", float(price_data.get("liquidity_imbalance", 0))) \
                .field("whale_imbalance", float(price_data.get("whale_imbalance", 0))) \
                .field("market_pressure", price_data.get("market_pressure", "neutral")) \
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
    
    def close(self):
        """Close InfluxDB connection."""
        if self.enabled and hasattr(self, 'client'):
            try:
                self.client.close()
                logger.info("InfluxDB connection closed")
            except Exception as e:
                logger.error(f"Error closing InfluxDB connection: {e}")