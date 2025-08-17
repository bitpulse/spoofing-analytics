"""
📈 Price Data Collector
Collects and saves price, volume, and trade data for correlation analysis
"""

import asyncio
import json
import queue
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
from loguru import logger
from dataclasses import dataclass, asdict
import time

@dataclass
class PriceData:
    """Price and volume data point"""
    timestamp: datetime
    symbol: str
    
    # Price data
    last_price: float  # Last trade price
    mark_price: float  # Mark price (for futures)
    index_price: float  # Index price
    bid_price: float  # Best bid
    ask_price: float  # Best ask
    mid_price: float  # (bid + ask) / 2
    
    # Volume data
    volume_24h: float  # 24h volume in base currency
    volume_usd_24h: float  # 24h volume in USD
    trade_count_24h: int  # Number of trades in 24h
    
    # Recent activity
    buy_volume_5min: float  # Buy volume last 5 minutes
    sell_volume_5min: float  # Sell volume last 5 minutes
    trade_count_5min: int  # Trades in last 5 minutes
    
    # Volatility metrics
    price_change_1min: float  # % change from 1 minute ago
    price_change_5min: float  # % change from 5 minutes ago
    price_change_1h: float  # % change from 1 hour ago
    high_5min: float  # Highest price in 5 minutes
    low_5min: float  # Lowest price in 5 minutes
    
    # Whale correlation fields
    active_whale_count: int  # Current active whales
    recent_spoof_count: int  # Spoofs in last 5 minutes
    whale_bid_value: float  # Total value of bid whales
    whale_ask_value: float  # Total value of ask whales
    
    # Market metrics
    funding_rate: float  # Perpetual funding rate
    open_interest: float  # Open interest
    liquidations_5min: float  # Liquidation volume last 5 min

class PriceCollector:
    """Collects comprehensive price data for analysis"""
    
    def __init__(self, symbol: str = "SEIUSDT"):
        self.symbol = symbol
        self.data_dir = Path(f"data/prices/{symbol}")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Rolling windows for calculations (using deque for automatic size management)
        from collections import deque
        self.price_history = deque(maxlen=3600)  # Last 3600 prices (1 hour at 1s intervals)
        self.trade_history = deque(maxlen=300)  # Last 300 trades
        self.last_save_time = time.time()
        
        # CSV file management with async queue
        import threading
        import queue
        self.save_queue = queue.Queue(maxsize=1000)
        self.writer_thread = None
        self.running = False
        self.current_csv_path = None
        self._start_async_writer()
        
    def get_current_csv_path(self) -> Path:
        """Get path for current hour's CSV file"""
        now = datetime.now()
        date_hour = now.strftime("%Y-%m-%d_%H")
        return self.data_dir / f"{self.symbol}_prices_{date_hour}.csv"
    
    def collect_price_data(self, order_book_snapshot, whale_tracker=None) -> PriceData:
        """Collect comprehensive price data from various sources"""
        
        # Basic price data from order book
        bid_price = order_book_snapshot.bids[0].price if order_book_snapshot.bids else 0
        ask_price = order_book_snapshot.asks[0].price if order_book_snapshot.asks else 0
        mid_price = order_book_snapshot.mid_price
        
        # Calculate price changes
        price_change_1min = 0
        price_change_5min = 0
        price_change_1h = 0
        
        if len(self.price_history) > 0:
            current_price = mid_price
            if len(self.price_history) >= 60:  # 1 minute of data
                # Convert deque to list for indexing
                price_list = list(self.price_history)
                price_1min_ago = price_list[-60]
                price_change_1min = ((current_price - price_1min_ago) / price_1min_ago) * 100
            
            if len(self.price_history) >= 300:  # 5 minutes
                price_list = list(self.price_history)
                price_5min_ago = price_list[-300]
                price_change_5min = ((current_price - price_5min_ago) / price_5min_ago) * 100
                
                # Calculate 5-minute high/low
                recent_5min = list(self.price_history)[-300:]
                high_5min = max(recent_5min)
                low_5min = min(recent_5min)
            else:
                high_5min = max(self.price_history) if self.price_history else mid_price
                low_5min = min(self.price_history) if self.price_history else mid_price
        else:
            high_5min = mid_price
            low_5min = mid_price
        
        # Whale data integration
        active_whale_count = 0
        whale_bid_value = 0
        whale_ask_value = 0
        
        if whale_tracker:
            # Get active whale statistics
            stats = whale_tracker.get_statistics()
            active_whale_count = stats.get('currently_active', 0)
            
            # Calculate whale values
            if hasattr(order_book_snapshot, 'whale_bids'):
                whale_bid_value = sum(w.value_usd for w in order_book_snapshot.whale_bids)
            if hasattr(order_book_snapshot, 'whale_asks'):
                whale_ask_value = sum(w.value_usd for w in order_book_snapshot.whale_asks)
        
        # Create price data object
        price_data = PriceData(
            timestamp=datetime.now(),
            symbol=self.symbol,
            last_price=mid_price,  # Using mid_price as proxy for last trade
            mark_price=mid_price,  # Would come from futures WebSocket
            index_price=mid_price,  # Would come from index calculation
            bid_price=bid_price,
            ask_price=ask_price,
            mid_price=mid_price,
            volume_24h=0,  # Would come from API
            volume_usd_24h=0,  # Would come from API
            trade_count_24h=0,  # Would come from API
            buy_volume_5min=0,  # Would calculate from trades
            sell_volume_5min=0,  # Would calculate from trades
            trade_count_5min=len(self.trade_history),
            price_change_1min=price_change_1min,
            price_change_5min=price_change_5min,
            price_change_1h=price_change_1h,
            high_5min=high_5min,
            low_5min=low_5min,
            active_whale_count=active_whale_count,
            recent_spoof_count=0,  # Would track from spoofing data
            whale_bid_value=whale_bid_value,
            whale_ask_value=whale_ask_value,
            funding_rate=0,  # Would come from futures API
            open_interest=0,  # Would come from futures API
            liquidations_5min=0  # Would come from liquidation stream
        )
        
        # Update history (deque handles size limit automatically)
        self.price_history.append(mid_price)
        
        return price_data
    
    def _start_async_writer(self):
        """Start background thread for async CSV writing"""
        import threading
        self.running = True
        self.writer_thread = threading.Thread(target=self._async_writer_loop, daemon=True)
        self.writer_thread.start()
    
    def _async_writer_loop(self):
        """Background loop for writing CSV data"""
        import csv
        file_handle = None
        csv_writer = None
        current_path = None
        
        while self.running:
            try:
                # Get next item from queue (timeout to check running flag)
                data_dict = self.save_queue.get(timeout=1.0)
                
                csv_path = self.get_current_csv_path()
                
                # Check if we need a new file (hourly rotation)
                if csv_path != current_path:
                    # Close old file if exists
                    if file_handle:
                        file_handle.close()
                    
                    # Open new file
                    current_path = csv_path
                    file_exists = csv_path.exists()
                    file_handle = open(csv_path, 'a', newline='')
                    
                    if not file_exists:
                        # Write headers for new file
                        fieldnames = list(data_dict.keys())
                        csv_writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
                        csv_writer.writeheader()
                        logger.info(f"Created new price CSV: {csv_path}")
                    else:
                        fieldnames = list(data_dict.keys())
                        csv_writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
                
                # Write data
                if csv_writer:
                    csv_writer.writerow(data_dict)
                    file_handle.flush()  # Ensure data is written
                    
            except queue.Empty:
                # Normal timeout - no data to write, continue loop
                continue
            except Exception as e:
                logger.error(f"Error in async CSV writer: {e}")
        
        # Cleanup on exit
        if file_handle:
            file_handle.close()
    
    def save_price_data(self, price_data: PriceData):
        """Queue price data for async CSV writing"""
        # Convert to dict for CSV
        data_dict = asdict(price_data)
        data_dict['timestamp'] = price_data.timestamp.isoformat()
        
        # Add to queue (non-blocking)
        try:
            self.save_queue.put_nowait(data_dict)
            self.last_save_time = time.time()
        except:
            # Queue full, skip this data point
            logger.warning(f"Price save queue full for {self.symbol}, skipping data point")
    
    def should_save(self) -> bool:
        """Determine if we should save (every second)"""
        return time.time() - self.last_save_time >= 1.0
    
    def analyze_price_impact(self, before_snapshot, after_snapshot, event_type: str) -> Dict:
        """
        Analyze price impact of events (whale appearance/disappearance, spoofing)
        """
        if not before_snapshot or not after_snapshot:
            return {}
        
        before_price = before_snapshot.mid_price
        after_price = after_snapshot.mid_price
        
        price_change = after_price - before_price
        price_change_pct = (price_change / before_price) * 100 if before_price > 0 else 0
        
        # Calculate spread change
        before_spread = before_snapshot.spread_bps
        after_spread = after_snapshot.spread_bps
        spread_change = after_spread - before_spread
        
        return {
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            'symbol': self.symbol,
            'price_before': before_price,
            'price_after': after_price,
            'price_change': price_change,
            'price_change_pct': price_change_pct,
            'spread_before': before_spread,
            'spread_after': after_spread,
            'spread_change': spread_change,
            'impact_direction': 'up' if price_change > 0 else 'down' if price_change < 0 else 'neutral'
        }
    
    def save_price_impact(self, impact_data: Dict):
        """Save price impact analysis"""
        impact_dir = Path(f"data/price_impacts/{self.symbol}")
        impact_dir.mkdir(parents=True, exist_ok=True)
        
        date = datetime.now().strftime("%Y-%m-%d")
        impact_file = impact_dir / f"{self.symbol}_impacts_{date}.csv"
        
        df = pd.DataFrame([impact_data])
        
        if impact_file.exists():
            df.to_csv(impact_file, mode='a', header=False, index=False)
        else:
            df.to_csv(impact_file, index=False)
            logger.info(f"Created price impact file: {impact_file}")


# Note: Integration is now done directly in src/main.py
# The PriceCollector is instantiated per symbol and called synchronously