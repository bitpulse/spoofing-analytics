from collections import deque, defaultdict
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import time
import json
from loguru import logger

from src.models.order_book import OrderBookSnapshot, WhaleOrder


class MemoryStore:
    """In-memory storage for real-time data with automatic cleanup"""
    
    def __init__(self, max_snapshots: int = 1000, max_whale_orders: int = 10000):
        # Order book snapshots by symbol
        self.order_book_snapshots: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_snapshots)
        )
        
        # Whale orders history
        self.whale_orders = deque(maxlen=max_whale_orders)
        
        # Aggregated metrics (1-minute candles)
        self.minute_metrics: Dict[str, List[Dict]] = defaultdict(list)
        
        # Latest snapshot for each symbol
        self.latest_snapshots: Dict[str, OrderBookSnapshot] = {}
        
        # Performance metrics
        self.stats = {
            'total_snapshots': 0,
            'total_whale_orders': 0,
            'start_time': time.time()
        }
        
    def store_snapshot(self, snapshot: OrderBookSnapshot):
        """Store order book snapshot"""
        symbol = snapshot.symbol
        
        # Store in history
        self.order_book_snapshots[symbol].append(snapshot)
        
        # Update latest
        self.latest_snapshots[symbol] = snapshot
        
        # Store whale orders
        for whale_order in snapshot.whale_bids + snapshot.whale_asks:
            self.whale_orders.append(whale_order)
            self.stats['total_whale_orders'] += 1
            
        # Update stats
        self.stats['total_snapshots'] += 1
        
        # Aggregate minute metrics if needed
        self._update_minute_metrics(snapshot)
        
    def _update_minute_metrics(self, snapshot: OrderBookSnapshot):
        """Update minute-level aggregated metrics"""
        current_minute = int(snapshot.timestamp_local / 60) * 60
        symbol = snapshot.symbol
        
        # Find or create minute record
        minute_data = None
        if self.minute_metrics[symbol]:
            last_minute = self.minute_metrics[symbol][-1]
            if last_minute['timestamp'] == current_minute:
                minute_data = last_minute
                
        if minute_data is None:
            minute_data = {
                'timestamp': current_minute,
                'symbol': symbol,
                'snapshots': 0,
                'avg_spread_bps': 0,
                'avg_volume_imbalance': 0,
                'whale_orders_count': 0,
                'max_bid_volume': 0,
                'max_ask_volume': 0,
                'price_high': snapshot.mid_price,
                'price_low': snapshot.mid_price
            }
            self.minute_metrics[symbol].append(minute_data)
            
        # Update minute data
        n = minute_data['snapshots']
        minute_data['snapshots'] = n + 1
        
        # Running averages
        minute_data['avg_spread_bps'] = (
            (minute_data['avg_spread_bps'] * n + snapshot.spread_bps) / (n + 1)
        )
        minute_data['avg_volume_imbalance'] = (
            (minute_data['avg_volume_imbalance'] * n + snapshot.volume_imbalance) / (n + 1)
        )
        
        # Counts and extremes
        minute_data['whale_orders_count'] += len(snapshot.whale_bids) + len(snapshot.whale_asks)
        minute_data['max_bid_volume'] = max(minute_data['max_bid_volume'], snapshot.bid_volume_total)
        minute_data['max_ask_volume'] = max(minute_data['max_ask_volume'], snapshot.ask_volume_total)
        minute_data['price_high'] = max(minute_data['price_high'], snapshot.mid_price)
        minute_data['price_low'] = min(minute_data['price_low'], snapshot.mid_price)
        
    def get_recent_snapshots(self, symbol: str, seconds: int = 60) -> List[OrderBookSnapshot]:
        """Get snapshots from the last N seconds"""
        if symbol not in self.order_book_snapshots:
            return []
            
        cutoff_time = time.time() - seconds
        return [
            s for s in self.order_book_snapshots[symbol]
            if s.timestamp_local >= cutoff_time
        ]
        
    def get_recent_whale_orders(self, seconds: int = 300) -> List[WhaleOrder]:
        """Get whale orders from the last N seconds"""
        cutoff_time = time.time() - seconds
        return [
            w for w in self.whale_orders
            if w.timestamp >= cutoff_time
        ]
        
    def get_minute_metrics(self, symbol: str, minutes: int = 60) -> List[Dict]:
        """Get minute-level metrics for the last N minutes"""
        if symbol not in self.minute_metrics:
            return []
            
        cutoff_time = (time.time() - minutes * 60)
        return [
            m for m in self.minute_metrics[symbol]
            if m['timestamp'] >= cutoff_time
        ]
        
    def get_stats(self) -> Dict:
        """Get storage statistics"""
        uptime = time.time() - self.stats['start_time']
        
        return {
            **self.stats,
            'uptime_seconds': uptime,
            'snapshots_per_second': self.stats['total_snapshots'] / uptime if uptime > 0 else 0,
            'symbols_tracked': len(self.latest_snapshots),
            'current_whale_orders': len(self.whale_orders),
            'memory_snapshots': sum(len(d) for d in self.order_book_snapshots.values())
        }
        
    def cleanup_old_data(self, hours: int = 24):
        """Remove data older than N hours"""
        cutoff_time = time.time() - (hours * 3600)
        
        # Clean minute metrics
        for symbol in self.minute_metrics:
            self.minute_metrics[symbol] = [
                m for m in self.minute_metrics[symbol]
                if m['timestamp'] >= cutoff_time
            ]
            
        logger.info(f"Cleaned up data older than {hours} hours")