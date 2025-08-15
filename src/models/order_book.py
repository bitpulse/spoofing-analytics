from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from datetime import datetime
import time


@dataclass
class PriceLevel:
    price: float
    size: float
    
    @property
    def value_usd(self) -> float:
        return self.price * self.size


@dataclass
class WhaleOrder:
    price: float
    size: float
    value_usd: float
    level: int
    percentage_of_book: float
    side: str  # 'bid' or 'ask'
    timestamp: float = field(default_factory=time.time)


@dataclass
class OrderBookSnapshot:
    symbol: str
    timestamp_server: int
    timestamp_local: float
    update_id: int
    update_id_gap: int
    
    # Raw order book data
    bids: List[PriceLevel]
    asks: List[PriceLevel]
    
    # Price levels
    best_bid: float
    best_bid_size: float
    best_ask: float
    best_ask_size: float
    
    # Spreads
    spread: float
    spread_bps: float
    mid_price: float
    
    # Volume Analysis
    bid_volume_total: float
    ask_volume_total: float
    bid_volume_value: float
    ask_volume_value: float
    
    # Whale Detection
    whale_bids: List[WhaleOrder]
    whale_asks: List[WhaleOrder]
    
    # Imbalance Metrics
    volume_imbalance: float
    value_imbalance: float
    whale_imbalance: int
    
    # Order Book Shape
    bid_slope: float
    ask_slope: float
    book_skew: float
    
    # Depth Metrics
    depth_1_percent: float
    depth_10bps: float
    resistance_level: Optional[float]
    support_level: Optional[float]
    
    @classmethod
    def from_raw_data(cls, raw_data: Dict, symbol: str, previous_update_id: int = 0) -> 'OrderBookSnapshot':
        """Create OrderBookSnapshot from Binance WebSocket data"""
        timestamp_server = raw_data['E']
        timestamp_local = time.time()
        update_id = raw_data['u']
        update_id_gap = update_id - previous_update_id
        
        # Parse bids and asks
        bids = [PriceLevel(float(price), float(size)) for price, size in raw_data['b']]
        asks = [PriceLevel(float(price), float(size)) for price, size in raw_data['a']]
        
        # Best bid/ask
        best_bid = bids[0].price if bids else 0
        best_bid_size = bids[0].size if bids else 0
        best_ask = asks[0].price if asks else 0
        best_ask_size = asks[0].size if asks else 0
        
        # Calculate metrics
        spread = best_ask - best_bid
        spread_bps = (spread / best_bid * 10000) if best_bid > 0 else 0
        mid_price = (best_bid + best_ask) / 2 if best_bid > 0 and best_ask > 0 else 0
        
        # Volume calculations
        bid_volume_total = sum(level.size for level in bids)
        ask_volume_total = sum(level.size for level in asks)
        bid_volume_value = sum(level.value_usd for level in bids)
        ask_volume_value = sum(level.value_usd for level in asks)
        
        # Calculate imbalances
        total_volume = bid_volume_total + ask_volume_total
        volume_imbalance = ((bid_volume_total - ask_volume_total) / total_volume) if total_volume > 0 else 0
        
        total_value = bid_volume_value + ask_volume_value
        value_imbalance = ((bid_volume_value - ask_volume_value) / total_value) if total_value > 0 else 0
        
        # These will be calculated by separate methods
        whale_bids = []
        whale_asks = []
        whale_imbalance = 0
        bid_slope = 0
        ask_slope = 0
        book_skew = 0
        depth_1_percent = 0
        depth_10bps = 0
        resistance_level = None
        support_level = None
        
        return cls(
            symbol=symbol,
            timestamp_server=timestamp_server,
            timestamp_local=timestamp_local,
            update_id=update_id,
            update_id_gap=update_id_gap,
            bids=bids,
            asks=asks,
            best_bid=best_bid,
            best_bid_size=best_bid_size,
            best_ask=best_ask,
            best_ask_size=best_ask_size,
            spread=spread,
            spread_bps=spread_bps,
            mid_price=mid_price,
            bid_volume_total=bid_volume_total,
            ask_volume_total=ask_volume_total,
            bid_volume_value=bid_volume_value,
            ask_volume_value=ask_volume_value,
            whale_bids=whale_bids,
            whale_asks=whale_asks,
            volume_imbalance=volume_imbalance,
            value_imbalance=value_imbalance,
            whale_imbalance=whale_imbalance,
            bid_slope=bid_slope,
            ask_slope=ask_slope,
            book_skew=book_skew,
            depth_1_percent=depth_1_percent,
            depth_10bps=depth_10bps,
            resistance_level=resistance_level,
            support_level=support_level
        )