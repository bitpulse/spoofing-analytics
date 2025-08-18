import numpy as np
from typing import List, Optional, Tuple
from collections import deque
from loguru import logger
import asyncio
import time

from src.models.order_book import OrderBookSnapshot, PriceLevel, WhaleOrder
from src.config import config
from src.tracking.whale_tracker import WhaleTracker
from src.storage.csv_logger import CSVLogger


class OrderBookAnalyzer:
    def __init__(self, whale_threshold_usd: float = None, mega_whale_threshold_usd: float = None, 
                 telegram_manager=None, enable_csv_logging: bool = True):
        # Store default thresholds (can be overridden per symbol)
        self.default_whale_threshold = whale_threshold_usd or config.whale_order_threshold
        self.default_mega_whale_threshold = mega_whale_threshold_usd or config.mega_whale_order_threshold
        self.telegram_manager = telegram_manager
        
        # Cache for per-symbol thresholds
        self.symbol_thresholds = {}
        
        # Rolling window for historical analysis
        self.snapshot_history = deque(maxlen=100)  # Last 10 seconds at 100ms updates
        self.whale_order_history = deque(maxlen=1000)
        
        # Initialize whale tracking
        self.whale_tracker = WhaleTracker()
        
        # Track which spoofs have already been logged to prevent duplicates
        # Use a deque with max size to automatically limit memory usage
        self.logged_spoofs = deque(maxlen=10000)  # Keep last 10k spoofs
        self.logged_spoofs_set = set()  # For O(1) lookups
        self.last_spoof_clear_time = None
        
        # Track last logged state for each whale to avoid redundant logging
        # Use LRU-like approach with deque
        self.last_logged_whale_state = {}  # whale_id -> (size, price, value_usd, timestamp)
        self.whale_state_order = deque(maxlen=5000)  # Track order for LRU cleanup
        self.min_log_interval = 1.0  # Minimum seconds between logs for same whale
        self.min_size_change_pct = 5.0  # Minimum % size change to log
        
        # Initialize CSV logging
        self.csv_logger = CSVLogger() if enable_csv_logging else None
        self.snapshot_counter = 0  # Log snapshots periodically
        
    def _get_thresholds(self, symbol: str) -> tuple:
        """Get whale thresholds for a specific symbol"""
        if symbol not in self.symbol_thresholds:
            thresholds = config.get_whale_thresholds(symbol)
            self.symbol_thresholds[symbol] = (
                thresholds["whale"],
                thresholds["mega_whale"]
            )
        return self.symbol_thresholds[symbol]
    
    def analyze_snapshot(self, snapshot: OrderBookSnapshot) -> OrderBookSnapshot:
        """Perform complete analysis on order book snapshot"""
        
        # Periodically clear old entries (every hour instead of daily)
        from datetime import datetime, timedelta
        now = datetime.now()
        if self.last_spoof_clear_time is None:
            self.last_spoof_clear_time = now
        elif (now - self.last_spoof_clear_time) > timedelta(hours=1):
            # Clean up logged_spoofs_set if it grows too large
            if len(self.logged_spoofs_set) > 10000:
                # Keep only the most recent spoofs
                self.logged_spoofs_set = set(list(self.logged_spoofs)[-5000:])
                logger.info(f"Cleaned logged_spoofs_set, kept 5000 most recent")
            
            # Clean up whale state if too large
            if len(self.last_logged_whale_state) > 5000:
                # Keep only the most recent whale states
                keep_ids = set(list(self.whale_state_order)[-2500:])
                self.last_logged_whale_state = {
                    k: v for k, v in self.last_logged_whale_state.items() 
                    if k in keep_ids
                }
                logger.info(f"Cleaned whale state cache, kept 2500 most recent")
            
            self.last_spoof_clear_time = now
        
        # Detect whale orders with tracking
        snapshot.whale_bids = self._detect_whale_orders(
            snapshot.bids, snapshot.bid_volume_total, 'bid', 
            snapshot.symbol, snapshot.mid_price, snapshot
        )
        snapshot.whale_asks = self._detect_whale_orders(
            snapshot.asks, snapshot.ask_volume_total, 'ask', 
            snapshot.symbol, snapshot.mid_price, snapshot
        )
        
        # Process whale tracking (detect disappeared whales)
        current_whale_ids = set()
        for whale in snapshot.whale_bids + snapshot.whale_asks:
            if hasattr(whale, 'whale_id'):
                current_whale_ids.add(whale.whale_id)
        
        # Check for disappeared whales (potential spoofing)
        self.whale_tracker.process_snapshot_whales(snapshot.symbol, current_whale_ids)
        
        # Check and log spoofing events (with deduplication)
        if self.csv_logger:
            for whale_id in list(self.whale_tracker.recent_whales.get(snapshot.symbol, [])):
                whale_summary = self.whale_tracker.get_whale_summary(whale_id.whale_id, snapshot.symbol)
                if whale_summary:
                    # Check for spoofing with enhanced scoring if available
                    is_spoof = False
                    confidence = None
                    
                    if 'spoof_confidence' in whale_summary:
                        # Enhanced detection available
                        confidence = whale_summary.get('spoof_confidence')
                        is_spoof = confidence in ['high', 'medium']
                    else:
                        # Fallback to basic detection
                        is_spoof = whale_summary.get('likely_spoof', False)
                    
                    if is_spoof:
                        # Create unique key for this spoof (symbol + whale_id)
                        spoof_key = f"{snapshot.symbol}_{whale_id.whale_id}"
                        
                        # Only log if we haven't logged this spoof before
                        if spoof_key not in self.logged_spoofs_set:
                            self.csv_logger.log_spoofing_from_dict(whale_summary)
                            self.logged_spoofs.append(spoof_key)  # Add to deque
                            self.logged_spoofs_set.add(spoof_key)  # Add to set for lookups
                            
                            if confidence:
                                logger.info(f"Logged {confidence} confidence spoof: {whale_id.whale_id[:50]}...")
                            else:
                                logger.info(f"Logged new spoof: {whale_id.whale_id[:50]}...")
        
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
        
        # Log market snapshot periodically (every 600 snapshots = ~1 minute at 100ms)
        self.snapshot_counter += 1
        if self.csv_logger and self.snapshot_counter % 600 == 0:
            self.csv_logger.log_snapshot_from_dict(snapshot)
        
        # Log significant events
        self._log_significant_events(snapshot)
        
        return snapshot
    
    def _detect_whale_orders(self, levels: List[PriceLevel], total_volume: float, 
                            side: str, symbol: str = "UNKNOWN", mid_price: float = 0,
                            snapshot: OrderBookSnapshot = None) -> List[WhaleOrder]:
        """Detect whale orders in the order book with tracking"""
        whale_orders = []
        current_whale_ids = set()
        
        # Get thresholds for this specific symbol
        whale_threshold, mega_whale_threshold = self._get_thresholds(symbol)
        
        for i, level in enumerate(levels):
            value_usd = level.value_usd
            
            if value_usd >= whale_threshold:
                percentage = (level.size / total_volume * 100) if total_volume > 0 else 0
                
                # Track this whale with unique ID
                whale_id = self.whale_tracker.identify_whale(
                    symbol=symbol,
                    side=side,
                    price=level.price,
                    size=level.size,
                    value_usd=value_usd,
                    percentage_of_book=percentage,
                    level=i,
                    mid_price=mid_price
                )
                
                current_whale_ids.add(whale_id)
                
                whale_order = WhaleOrder(
                    price=level.price,
                    size=level.size,
                    value_usd=value_usd,
                    level=i,
                    percentage_of_book=percentage,
                    side=side
                )
                
                # Add whale_id to the order (extend WhaleOrder if needed)
                whale_order.whale_id = whale_id
                
                whale_orders.append(whale_order)
                self.whale_order_history.append(whale_order)
                
                # Log whale to CSV only if there's a meaningful change
                if self.csv_logger:
                    # Check if we should log this update
                    should_log = False
                    now = time.time()
                    
                    if whale_id not in self.last_logged_whale_state:
                        # First time seeing this whale - always log
                        should_log = True
                    else:
                        last_size, last_price, last_value, last_time = self.last_logged_whale_state[whale_id]
                        time_since_last_log = now - last_time
                        
                        # Calculate changes
                        size_change_pct = abs((level.size - last_size) / last_size * 100) if last_size > 0 else 100
                        price_change_pct = abs((level.price - last_price) / last_price * 100) if last_price > 0 else 100
                        
                        # Log if: significant size change, price level change, or enough time passed
                        if (size_change_pct > self.min_size_change_pct or 
                            price_change_pct > 0.1 or 
                            time_since_last_log > 10.0):  # Also log every 10 seconds regardless
                            should_log = True
                    
                    if should_log:
                        whale_summary = self.whale_tracker.get_whale_summary(whale_id, symbol)
                        if whale_summary:
                            # Override with actual current values
                            whale_summary['price'] = level.price
                            whale_summary['size'] = level.size
                            whale_summary['value_usd'] = value_usd
                            whale_summary['percentage_of_book'] = percentage
                            whale_summary['level'] = i
                            whale_summary['symbol'] = symbol
                            whale_summary['side'] = side
                            whale_summary['whale_id'] = whale_id
                            
                            # Add snapshot context
                            snapshot_context = {
                                'mid_price': mid_price,
                                'spread_bps': snapshot.spread_bps if snapshot else 0,
                                'total_bid_whales': len(snapshot.whale_bids) if snapshot else 0,
                                'total_ask_whales': len(snapshot.whale_asks) if snapshot else 0,
                                'volume_imbalance': snapshot.volume_imbalance if snapshot else 0,
                                'bid_depth_1pct': snapshot.depth_1_percent if snapshot and hasattr(snapshot, 'depth_1_percent') else 0,
                                'ask_depth_1pct': 0
                            }
                            self.csv_logger.log_whale_from_dict(whale_summary, snapshot_context)
                            
                            # Update last logged state
                            self.last_logged_whale_state[whale_id] = (level.size, level.price, value_usd, now)
                
                # Use per-symbol mega whale threshold for alerts
                alert_threshold = mega_whale_threshold * 1.5  # Alert at 1.5x mega threshold
                
                # Only log truly significant mega whales
                if value_usd >= alert_threshold and percentage > 30:
                    logger.warning(
                        f"🐋 SIGNIFICANT WHALE {side.upper()} on {symbol}: "
                        f"${value_usd:,.0f} at ${level.price:,.2f} "
                        f"({percentage:.1f}% of book)"
                    )
                    
                    # Alert for mega whales based on per-symbol thresholds
                    if self.telegram_manager and value_usd >= alert_threshold and percentage > 30:
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
        except (np.linalg.LinAlgError, ValueError, TypeError) as e:
            # LinAlgError: Singular matrix, ValueError: empty arrays, TypeError: wrong types
            logger.debug(f"Failed to calculate slope: {e}")
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
            
        # Disable imbalance alerts - too frequent and not actionable
        # Only keep for internal tracking, no logging or alerts
        pass
            
        # Multiple whale orders on same side
        if len(snapshot.whale_bids) >= 3:
            total_whale_bid_value = sum(w.value_usd for w in snapshot.whale_bids)
            logger.warning(
                f"Multiple whale BIDS detected: {len(snapshot.whale_bids)} orders, "
                f"total ${total_whale_bid_value:,.0f}"
            )
            
            # Disabled - too frequent
            pass
            
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