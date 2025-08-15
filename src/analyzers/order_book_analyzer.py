import numpy as np
from typing import List, Optional, Tuple
from collections import deque
from loguru import logger
import asyncio

from src.models.order_book import OrderBookSnapshot, PriceLevel, WhaleOrder
from src.config import config


class OrderBookAnalyzer:
    def __init__(self, whale_threshold_usd: float = None, mega_whale_threshold_usd: float = None, 
                 telegram_manager=None):
        self.whale_threshold = whale_threshold_usd or config.whale_order_threshold
        self.mega_whale_threshold = mega_whale_threshold_usd or config.mega_whale_order_threshold
        self.telegram_manager = telegram_manager
        
        # Rolling window for historical analysis
        self.snapshot_history = deque(maxlen=100)  # Last 10 seconds at 100ms updates
        self.whale_order_history = deque(maxlen=1000)
        
    def analyze_snapshot(self, snapshot: OrderBookSnapshot) -> OrderBookSnapshot:
        """Perform complete analysis on order book snapshot"""
        
        # Detect whale orders
        snapshot.whale_bids = self._detect_whale_orders(
            snapshot.bids, snapshot.bid_volume_total, 'bid', snapshot.symbol
        )
        snapshot.whale_asks = self._detect_whale_orders(
            snapshot.asks, snapshot.ask_volume_total, 'ask', snapshot.symbol
        )
        
        # Calculate whale imbalance
        snapshot.whale_imbalance = len(snapshot.whale_bids) - len(snapshot.whale_asks)
        
        # Calculate order book slopes
        snapshot.bid_slope = self._calculate_slope(snapshot.bids)
        snapshot.ask_slope = self._calculate_slope(snapshot.asks)
        snapshot.book_skew = snapshot.bid_slope - snapshot.ask_slope
        
        # Calculate depth metrics
        snapshot.depth_1_percent = self._calculate_depth_at_percentage(
            snapshot.bids, snapshot.asks, snapshot.mid_price, 1.0
        )
        snapshot.depth_10bps = self._calculate_depth_at_bps(
            snapshot.bids, snapshot.asks, snapshot.mid_price, 10
        )
        
        # Find support and resistance levels
        snapshot.support_level = self._find_support_level(snapshot.bids)
        snapshot.resistance_level = self._find_resistance_level(snapshot.asks)
        
        # Store in history
        self.snapshot_history.append(snapshot)
        
        # Log significant events
        self._log_significant_events(snapshot)
        
        return snapshot
    
    def _detect_whale_orders(self, levels: List[PriceLevel], total_volume: float, 
                            side: str, symbol: str = "UNKNOWN") -> List[WhaleOrder]:
        """Detect whale orders in the order book"""
        whale_orders = []
        
        for i, level in enumerate(levels):
            value_usd = level.value_usd
            
            if value_usd >= self.whale_threshold:
                percentage = (level.size / total_volume * 100) if total_volume > 0 else 0
                
                whale_order = WhaleOrder(
                    price=level.price,
                    size=level.size,
                    value_usd=value_usd,
                    level=i,
                    percentage_of_book=percentage,
                    side=side
                )
                
                whale_orders.append(whale_order)
                self.whale_order_history.append(whale_order)
                
                # Log mega whales
                if value_usd >= self.mega_whale_threshold:
                    logger.warning(
                        f"MEGA WHALE {side.upper()} detected: "
                        f"${value_usd:,.0f} at {level.price} "
                        f"({percentage:.1f}% of book)"
                    )
                    
                    # Only alert for truly significant mega whales (>$3M and >30% of book)
                    if self.telegram_manager and value_usd >= 3000000 and percentage > 30:
                        self.telegram_manager.queue_whale_alert(
                            whale_order, 
                            symbol,
                            "MEGA WHALE DETECTED"
                        )
                    
        return whale_orders
    
    def _calculate_slope(self, levels: List[PriceLevel]) -> float:
        """Calculate the slope of order book side (steepness)"""
        if len(levels) < 2:
            return 0
            
        prices = [level.price for level in levels[:10]]  # Use top 10 levels
        sizes = [level.size for level in levels[:10]]
        
        if not prices or not sizes:
            return 0
            
        # Normalize prices to percentage from best price
        best_price = prices[0]
        price_distances = [(abs(p - best_price) / best_price * 100) for p in prices]
        
        # Calculate weighted average slope
        try:
            # Using numpy for linear regression
            coefficients = np.polyfit(price_distances, sizes, 1)
            slope = coefficients[0]
        except:
            slope = 0
            
        return slope
    
    def _calculate_depth_at_percentage(self, bids: List[PriceLevel], asks: List[PriceLevel],
                                      mid_price: float, percentage: float) -> float:
        """Calculate total volume within X% of mid price"""
        if mid_price <= 0:
            return 0
            
        threshold_up = mid_price * (1 + percentage / 100)
        threshold_down = mid_price * (1 - percentage / 100)
        
        bid_volume = sum(
            level.size for level in bids 
            if level.price >= threshold_down
        )
        
        ask_volume = sum(
            level.size for level in asks 
            if level.price <= threshold_up
        )
        
        return bid_volume + ask_volume
    
    def _calculate_depth_at_bps(self, bids: List[PriceLevel], asks: List[PriceLevel],
                               mid_price: float, bps: int) -> float:
        """Calculate total volume within X basis points of mid price"""
        return self._calculate_depth_at_percentage(bids, asks, mid_price, bps / 100)
    
    def _find_support_level(self, bids: List[PriceLevel]) -> Optional[float]:
        """Find first significant support level (bid wall > $1M)"""
        for level in bids:
            if level.value_usd >= 1000000:
                return level.price
        return None
    
    def _find_resistance_level(self, asks: List[PriceLevel]) -> Optional[float]:
        """Find first significant resistance level (ask wall > $1M)"""
        for level in asks:
            if level.value_usd >= 1000000:
                return level.price
        return None
    
    def _log_significant_events(self, snapshot: OrderBookSnapshot):
        """Log significant market events"""
        
        # Extreme spread
        if snapshot.spread_bps > 10:
            logger.warning(f"Wide spread detected: {snapshot.spread_bps:.2f} bps")
            
        # Extreme imbalance (only after warmup and truly extreme)
        if len(self.snapshot_history) > 50 and abs(snapshot.volume_imbalance) > 0.85:
            side = "BID" if snapshot.volume_imbalance > 0 else "ASK"
            logger.warning(
                f"Extreme {side} imbalance: {abs(snapshot.volume_imbalance):.1%}"
            )
            
            # Queue Telegram alert for extreme imbalance
            if self.telegram_manager:
                self.telegram_manager.queue_market_alert(snapshot, "EXTREME_IMBALANCE")
            
        # Multiple whale orders on same side
        if len(snapshot.whale_bids) >= 3:
            total_whale_bid_value = sum(w.value_usd for w in snapshot.whale_bids)
            logger.warning(
                f"Multiple whale BIDS detected: {len(snapshot.whale_bids)} orders, "
                f"total ${total_whale_bid_value:,.0f}"
            )
            
            # Queue alert for whale cluster
            if self.telegram_manager and (len(snapshot.whale_bids) + len(snapshot.whale_asks)) >= 5:
                self.telegram_manager.queue_market_alert(snapshot, "MULTIPLE_WHALES")
            
        if len(snapshot.whale_asks) >= 3:
            total_whale_ask_value = sum(w.value_usd for w in snapshot.whale_asks)
            logger.warning(
                f"Multiple whale ASKS detected: {len(snapshot.whale_asks)} orders, "
                f"total ${total_whale_ask_value:,.0f}"
            )
    
    def detect_spoofing(self, lookback_seconds: int = 5) -> List[WhaleOrder]:
        """Detect potential spoofing (orders placed and quickly canceled)"""
        if len(self.snapshot_history) < lookback_seconds * 10:
            return []
            
        recent_snapshots = list(self.snapshot_history)[-lookback_seconds * 10:]
        
        # Track whale orders that appeared and disappeared
        seen_orders = {}
        disappeared_orders = []
        
        for snapshot in recent_snapshots:
            current_whale_orders = snapshot.whale_bids + snapshot.whale_asks
            current_order_keys = {(o.price, o.side) for o in current_whale_orders}
            
            # Check for disappeared orders
            for key, order in seen_orders.items():
                if key not in current_order_keys:
                    lifespan = snapshot.timestamp_local - order.timestamp
                    if lifespan < 2:  # Lived less than 2 seconds
                        disappeared_orders.append(order)
                        logger.warning(
                            f"Potential SPOOFING detected: {order.side} order "
                            f"${order.value_usd:,.0f} at {order.price} "
                            f"(lived {lifespan:.1f}s)"
                        )
                        
            # Update seen orders
            for order in current_whale_orders:
                key = (order.price, order.side)
                if key not in seen_orders:
                    seen_orders[key] = order
                    
        return disappeared_orders
    
    def get_market_pressure(self) -> str:
        """Determine overall market pressure based on recent snapshots"""
        if not self.snapshot_history:
            return "neutral"
            
        recent = list(self.snapshot_history)[-20:]  # Last 2 seconds
        
        avg_volume_imbalance = np.mean([s.volume_imbalance for s in recent])
        avg_whale_imbalance = np.mean([s.whale_imbalance for s in recent])
        
        if avg_volume_imbalance > 0.3 and avg_whale_imbalance > 1:
            return "strong_buy_pressure"
        elif avg_volume_imbalance > 0.1:
            return "buy_pressure"
        elif avg_volume_imbalance < -0.3 and avg_whale_imbalance < -1:
            return "strong_sell_pressure"
        elif avg_volume_imbalance < -0.1:
            return "sell_pressure"
        else:
            return "neutral"