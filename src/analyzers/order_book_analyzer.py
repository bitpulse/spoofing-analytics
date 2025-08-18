import numpy as np
from typing import List, Optional, Tuple
from collections import deque
from loguru import logger
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
        
        # Cache for per-symbol thresholds
        self.symbol_thresholds = {}
        
        # Rolling window for historical analysis
        self.snapshot_history = deque(maxlen=100)  # Last 10 seconds at 100ms updates
        self.whale_order_history = deque(maxlen=1000)
        
        # Initialize whale tracking
        self.whale_tracker = WhaleTracker()
        
        # Track last logged state for each whale to avoid redundant logging
        self.last_logged_whale_state = {}
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
        
        # Clean up whale state if too large (every hour)
        from datetime import datetime, timedelta
        if len(self.last_logged_whale_state) > 5000:
            # Keep only the most recent whale states
            keep_ids = set(list(self.whale_state_order)[-2500:])
            self.last_logged_whale_state = {
                k: v for k, v in self.last_logged_whale_state.items() 
                if k in keep_ids
            }
            logger.debug(f"Cleaned whale state cache, kept 2500 most recent")
        
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
        
        # Process disappeared whales
        disappeared_whales = self.whale_tracker.process_snapshot(
            snapshot.symbol, 
            current_whale_ids, 
            snapshot.whale_bids + snapshot.whale_asks
        )
        
        # Calculate whale metrics
        snapshot.whale_imbalance = len(snapshot.whale_bids) - len(snapshot.whale_asks)
        snapshot.whale_pressure = self._calculate_whale_pressure(snapshot)
        
        # Analyze support/resistance levels
        snapshot.support_level = self._find_support_level(snapshot)
        snapshot.resistance_level = self._find_resistance_level(snapshot)
        
        # Store in history
        self.snapshot_history.append(snapshot)
        self.whale_order_history.extend(snapshot.whale_bids)
        self.whale_order_history.extend(snapshot.whale_asks)
        
        # Log snapshot periodically (every 60 seconds = 600 updates at 100ms)
        self.snapshot_counter += 1
        if self.snapshot_counter % 600 == 0 and self.csv_logger:
            # Removed snapshot logging - not needed anymore
            pass
        
        return snapshot
    
    def _detect_whale_orders(self, levels: List[PriceLevel], total_volume: float, 
                            side: str, symbol: str, mid_price: float, 
                            snapshot: OrderBookSnapshot) -> List[WhaleOrder]:
        """Detect and track whale orders in order book levels"""
        whales = []
        
        # Get thresholds for this symbol
        whale_threshold, mega_whale_threshold = self._get_thresholds(symbol)
        
        for i, level in enumerate(levels):
            if level.value_usd >= whale_threshold:
                # Track this whale
                whale_data = self.whale_tracker.track_whale(
                    symbol=symbol,
                    side=side,
                    price=level.price,
                    size=level.size,
                    value_usd=level.value_usd,
                    percentage_of_book=(level.value_usd / snapshot.total_volume_usd * 100) if snapshot.total_volume_usd > 0 else 0,
                    level=i,
                    mid_price=mid_price,
                    spread_bps=snapshot.spread_bps
                )
                
                # Check if we should log this whale
                if whale_data and self._should_log_whale(whale_data):
                    # Log to CSV if enabled
                    if self.csv_logger:
                        snapshot_data = {
                            'mid_price': mid_price,
                            'spread_bps': snapshot.spread_bps,
                            'total_bid_whales': len(snapshot.whale_bids) if hasattr(snapshot, 'whale_bids') else 0,
                            'total_ask_whales': len(snapshot.whale_asks) if hasattr(snapshot, 'whale_asks') else 0,
                            'volume_imbalance': snapshot.volume_imbalance
                        }
                        self.csv_logger.log_whale_from_dict(whale_data, snapshot_data)
                    
                    # Update logged state
                    self._update_logged_state(whale_data)
                
                # Create WhaleOrder object
                whale = WhaleOrder(
                    price=level.price,
                    size=level.size,
                    value_usd=level.value_usd,
                    percentage=(level.value_usd / snapshot.total_volume_usd * 100) if snapshot.total_volume_usd > 0 else 0,
                    level=i,
                    is_mega=(level.value_usd >= mega_whale_threshold),
                    side=side,
                    whale_id=whale_data.get('whale_id') if whale_data else None,
                    duration_seconds=whale_data.get('duration_seconds', 0) if whale_data else 0,
                    size_changes=whale_data.get('size_changes_count', 0) if whale_data else 0
                )
                whales.append(whale)
        
        return whales
    
    def _should_log_whale(self, whale_data: dict) -> bool:
        """Determine if whale should be logged based on significance"""
        whale_id = whale_data.get('whale_id')
        if not whale_id:
            return False
        
        # Always log new whales
        if whale_data.get('is_new', False):
            return True
        
        # Check if we've logged this whale recently
        if whale_id in self.last_logged_whale_state:
            last_state = self.last_logged_whale_state[whale_id]
            last_size, last_price, last_value, last_time = last_state
            
            current_time = time.time()
            time_since_last = current_time - last_time
            
            # Log if enough time has passed (10 seconds heartbeat)
            if time_since_last >= 10.0:
                return True
            
            # Log if significant size change
            size_change_pct = abs((whale_data['size'] - last_size) / last_size * 100) if last_size > 0 else 0
            if size_change_pct >= self.min_size_change_pct:
                return True
            
            # Log if price changed significantly (moved to different level)
            price_change_pct = abs((whale_data['price'] - last_price) / last_price * 100) if last_price > 0 else 0
            if price_change_pct >= 0.1:  # 0.1% price change = likely different level
                return True
            
            return False
        
        # If we haven't seen this whale before, log it
        return True
    
    def _update_logged_state(self, whale_data: dict):
        """Update the last logged state for a whale"""
        whale_id = whale_data.get('whale_id')
        if whale_id:
            self.last_logged_whale_state[whale_id] = (
                whale_data['size'],
                whale_data['price'],
                whale_data['value_usd'],
                time.time()
            )
            # Track order for LRU cleanup
            if whale_id not in self.whale_state_order:
                self.whale_state_order.append(whale_id)
    
    def _calculate_whale_pressure(self, snapshot: OrderBookSnapshot) -> str:
        """Calculate overall whale pressure on the market"""
        bid_whale_value = sum(w.value_usd for w in snapshot.whale_bids)
        ask_whale_value = sum(w.value_usd for w in snapshot.whale_asks)
        
        if bid_whale_value + ask_whale_value == 0:
            return "neutral"
        
        whale_ratio = bid_whale_value / (bid_whale_value + ask_whale_value)
        
        if whale_ratio > 0.7:
            return "strong_buy"
        elif whale_ratio > 0.55:
            return "buy"
        elif whale_ratio < 0.3:
            return "strong_sell"
        elif whale_ratio < 0.45:
            return "sell"
        else:
            return "neutral"
    
    def _find_support_level(self, snapshot: OrderBookSnapshot) -> Optional[float]:
        """Find the strongest support level based on whale orders"""
        if not snapshot.whale_bids:
            return None
        
        # Find the largest whale bid as support
        largest_whale = max(snapshot.whale_bids, key=lambda w: w.value_usd)
        return largest_whale.price
    
    def _find_resistance_level(self, snapshot: OrderBookSnapshot) -> Optional[float]:
        """Find the strongest resistance level based on whale orders"""
        if not snapshot.whale_asks:
            return None
        
        # Find the largest whale ask as resistance
        largest_whale = max(snapshot.whale_asks, key=lambda w: w.value_usd)
        return largest_whale.price
    
    def get_market_pressure(self) -> str:
        """Get current market pressure based on recent snapshots"""
        if not self.snapshot_history:
            return "unknown"
        
        recent_snapshots = list(self.snapshot_history)[-20:]  # Last 2 seconds
        if not recent_snapshots:
            return "unknown"
        
        pressures = [s.whale_pressure for s in recent_snapshots if hasattr(s, 'whale_pressure')]
        if not pressures:
            return "unknown"
        
        # Get most common pressure
        from collections import Counter
        pressure_counts = Counter(pressures)
        return pressure_counts.most_common(1)[0][0]
    
    def detect_spoofing(self) -> List:
        """Placeholder - spoofing detection removed"""
        return []