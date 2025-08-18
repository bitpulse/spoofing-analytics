"""
Whale tracking system with unique ID generation and behavior analysis
"""
import time
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

# Import enhanced spoof detector for better detection
try:
    from .enhanced_spoof_detector import EnhancedSpoofDetector, SpoofScore
    ENHANCED_DETECTION = True
except ImportError:
    ENHANCED_DETECTION = False
    logger.warning("Enhanced spoof detector not available, using basic detection")


@dataclass
class TrackedWhale:
    """Represents a tracked whale order with full history"""
    whale_id: str
    symbol: str
    side: str
    initial_price: float
    initial_size: float
    initial_value_usd: float
    
    # Tracking data
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    current_price: float = 0
    current_size: float = 0
    current_value_usd: float = 0
    
    # Behavior tracking
    size_changes: List[Tuple[float, float]] = field(default_factory=list)  # (timestamp, new_size)
    price_moves: List[Tuple[float, float]] = field(default_factory=list)  # (timestamp, new_price)
    disappearances: int = 0
    total_duration: float = 0
    max_size_seen: float = 0
    min_size_seen: float = float('inf')
    
    # Market context
    mid_price_on_appearance: float = 0
    percentage_of_book: float = 0
    level: int = 0
    
    def update(self, price: float, size: float, value_usd: float):
        """Update whale with new observation"""
        now = time.time()
        
        # Track SIGNIFICANT changes only (>5% size change or >0.1% price change)
        size_change_pct = abs((self.current_size - size) / self.current_size * 100) if self.current_size > 0 else 100
        price_change_pct = abs((self.current_price - price) / self.current_price * 100) if self.current_price > 0 else 100
        
        if size_change_pct > 5.0:  # Only track if size changes by more than 5%
            self.size_changes.append((now, size))
        if price_change_pct > 0.1:  # Only track if price changes by more than 0.1%
            self.price_moves.append((now, price))
            
        # Update current state
        self.current_price = price
        self.current_size = size
        self.current_value_usd = value_usd
        self.last_seen = now
        
        # Update extremes
        self.max_size_seen = max(self.max_size_seen, size)
        self.min_size_seen = min(self.min_size_seen, size)
        
    def mark_disappeared(self):
        """Mark whale as disappeared"""
        self.disappearances += 1
        self.total_duration += (self.last_seen - self.first_seen)
        

class WhaleTracker:
    """Tracks and identifies unique whales across time"""
    
    def __init__(self, 
                 price_tolerance: float = 0.001,  # 0.1% price tolerance
                 size_tolerance: float = 0.20,    # 20% size tolerance
                 memory_seconds: int = 300):      # Remember whales for 5 minutes
        
        self.price_tolerance = price_tolerance
        self.size_tolerance = size_tolerance
        self.memory_seconds = memory_seconds
        
        # Active whales by symbol
        self.active_whales: Dict[str, Dict[str, TrackedWhale]] = {}
        
        # Index for faster lookups: symbol -> side -> list of whale_ids
        self.whale_index: Dict[str, Dict[str, set]] = {}
        
        # Recently disappeared whales (might reappear)
        self.recent_whales: Dict[str, List[TrackedWhale]] = {}
        
        # Historical data for pattern analysis
        self.whale_history: List[TrackedWhale] = []
        
        # Statistics
        self.total_whales_tracked = 0
        self.total_spoofs_detected = 0
        
        # Initialize enhanced detector if available
        if ENHANCED_DETECTION:
            self.enhanced_detector = EnhancedSpoofDetector()
            logger.info("Enhanced spoofing detection enabled")
        else:
            self.enhanced_detector = None
        
    def identify_whale(self, 
                      symbol: str, 
                      side: str, 
                      price: float, 
                      size: float, 
                      value_usd: float,
                      percentage_of_book: float = 0,
                      level: int = 0,
                      mid_price: float = 0) -> str:
        """
        Identify if this is an existing whale or a new one.
        Returns whale_id.
        """
        
        # Initialize symbol dicts if needed
        if symbol not in self.active_whales:
            self.active_whales[symbol] = {}
            self.recent_whales[symbol] = []
            self.whale_index[symbol] = {'bid': set(), 'ask': set()}
        
        # First check active whales
        whale_id = self._match_active_whale(symbol, side, price, size)
        
        if whale_id:
            # Update existing whale
            whale = self.active_whales[symbol][whale_id]
            whale.update(price, size, value_usd)
            return whale_id
            
        # Check recently disappeared whales (might be flickering)
        whale_id = self._match_recent_whale(symbol, side, price, size)
        
        if whale_id:
            # Reactivate whale
            whale = self._reactivate_whale(symbol, whale_id)
            whale.update(price, size, value_usd)
            logger.debug(f"Reactivated whale {whale_id} after disappearance")
            return whale_id
            
        # Create new whale
        whale_id = self._create_new_whale(
            symbol, side, price, size, value_usd,
            percentage_of_book, level, mid_price
        )
        
        return whale_id
        
    def _match_active_whale(self, symbol: str, side: str, price: float, size: float) -> Optional[str]:
        """Check if matches any active whale"""
        
        # Use index for faster lookup (O(1) to get relevant whales)
        if symbol not in self.whale_index or side not in self.whale_index[symbol]:
            return None
            
        # Only check whales with matching side
        for whale_id in self.whale_index[symbol][side]:
            whale = self.active_whales[symbol].get(whale_id)
            if not whale:
                continue
                
            # Check price match (within tolerance)
            if whale.current_price > 0:
                price_diff = abs(price - whale.current_price) / whale.current_price
                if price_diff > self.price_tolerance:
                    continue
            else:
                # If current_price is 0, skip this whale
                continue
                
            # Check size match (within tolerance)
            if whale.current_size > 0:
                size_diff = abs(size - whale.current_size) / whale.current_size
                if size_diff > self.size_tolerance:
                    continue
            else:
                # If current_size is 0, skip this whale
                continue
                
            # Found a match
            return whale_id
            
        return None
        
    def _match_recent_whale(self, symbol: str, side: str, price: float, size: float) -> Optional[str]:
        """Check recently disappeared whales"""
        
        now = time.time()
        recent_whales = self.recent_whales[symbol]
        
        # Clean old whales
        recent_whales[:] = [w for w in recent_whales 
                           if now - w.last_seen < self.memory_seconds]
        
        for whale in recent_whales:
            if whale.side != side:
                continue
                
            # More lenient matching for reappearing whales
            if whale.current_price > 0 and whale.current_size > 0:
                price_diff = abs(price - whale.current_price) / whale.current_price
                size_diff = abs(size - whale.current_size) / whale.current_size
                
                if price_diff < self.price_tolerance * 2 and size_diff < self.size_tolerance * 2:
                    return whale.whale_id
            else:
                # Skip if price or size is 0
                continue
                
        return None
        
    def _reactivate_whale(self, symbol: str, whale_id: str) -> TrackedWhale:
        """Reactivate a recently disappeared whale"""
        
        # Find and remove from recent list
        whale = None
        for i, w in enumerate(self.recent_whales[symbol]):
            if w.whale_id == whale_id:
                whale = self.recent_whales[symbol].pop(i)
                break
                
        # Add back to active
        self.active_whales[symbol][whale_id] = whale
        whale.disappearances += 1  # Track that it disappeared and came back
        
        return whale
        
    def _create_new_whale(self, symbol: str, side: str, price: float, 
                         size: float, value_usd: float, percentage_of_book: float,
                         level: int, mid_price: float) -> str:
        """Create a new tracked whale"""
        
        # Generate unique ID
        timestamp = int(time.time() * 1000)  # Millisecond precision
        whale_id = f"{symbol}_{side}_{int(price)}_{timestamp}"
        
        # Create whale object
        whale = TrackedWhale(
            whale_id=whale_id,
            symbol=symbol,
            side=side,
            initial_price=price,
            initial_size=size,
            initial_value_usd=value_usd,
            current_price=price,
            current_size=size,
            current_value_usd=value_usd,
            max_size_seen=size,
            min_size_seen=size,
            mid_price_on_appearance=mid_price,
            percentage_of_book=percentage_of_book,
            level=level
        )
        
        # Add to active tracking
        self.active_whales[symbol][whale_id] = whale
        # Update index for faster lookups
        if side in self.whale_index[symbol]:
            self.whale_index[symbol][side].add(whale_id)
        self.total_whales_tracked += 1
        
        logger.debug(f"New whale tracked: {whale_id} - ${value_usd:,.0f} at ${price:,.2f}")
        
        return whale_id
        
    def process_snapshot_whales(self, symbol: str, current_whale_ids: set):
        """
        Process which whales are still present in the latest snapshot.
        Moves missing whales to recent_whales list.
        """
        
        if symbol not in self.active_whales:
            return
            
        now = time.time()
        disappeared = []
        
        # Check which active whales are missing
        for whale_id, whale in self.active_whales[symbol].items():
            if whale_id not in current_whale_ids:
                # Whale disappeared
                whale.mark_disappeared()
                disappeared.append(whale_id)
                
                # Check if it was a spoof
                duration = whale.last_seen - whale.first_seen
                
                # Use enhanced detector if available
                if self.enhanced_detector and hasattr(whale, 'mid_price_on_appearance'):
                    score = self.enhanced_detector.analyze_whale_lifecycle(
                        whale, symbol, whale.mid_price_on_appearance
                    )
                    if score and score.confidence_level in ['high', 'medium']:
                        self.total_spoofs_detected += 1
                        logger.info(
                            f"SPOOF [{score.confidence_level.upper()}] {whale.symbol} {whale.side} "
                            f"${whale.current_value_usd:,.0f} Score: {score.total_score:.0f} "
                            f"Pattern: {score.pattern_type} Duration: {duration:.1f}s"
                        )
                elif self._is_likely_spoof(whale, duration):
                    # Fallback to basic detection
                    self.total_spoofs_detected += 1
                    logger.info(
                        f"Likely spoof detected: {whale.symbol} {whale.side} "
                        f"${whale.current_value_usd:,.0f} lasted {duration:.1f}s"
                    )
                    
        # Move disappeared whales to recent list
        for whale_id in disappeared:
            whale = self.active_whales[symbol].pop(whale_id)
            self.recent_whales[symbol].append(whale)
            self.whale_history.append(whale)  # Save to history
            
    def _is_likely_spoof(self, whale: TrackedWhale, duration: float) -> bool:
        """Determine if whale behavior indicates spoofing"""
        
        # Classic spoof: large order that disappears quickly
        if 5 < duration < 60 and whale.current_value_usd >= 5000000:
            return True
            
        # Flickering spoof: appears and disappears multiple times
        if whale.disappearances >= 3 and duration < 120:
            return True
            
        # Size manipulation: significant size changes
        if whale.size_changes and len(whale.size_changes) >= 5:
            size_variance = (whale.max_size_seen - whale.min_size_seen) / whale.initial_size
            if size_variance > 0.5:  # Size varied by >50%
                return True
                
        return False
        
    def get_whale_summary(self, whale_id: str, symbol: str) -> Optional[Dict]:
        """Get comprehensive data about a specific whale"""
        
        whale = self.active_whales.get(symbol, {}).get(whale_id)
        if not whale:
            # Check recent whales
            for w in self.recent_whales.get(symbol, []):
                if w.whale_id == whale_id:
                    whale = w
                    break
                    
        if not whale:
            return None
            
        now = time.time()
        # Calculate total duration including previous appearances
        if whale_id in self.active_whales.get(symbol, {}):
            # Currently active: add current session to total
            current_session = now - whale.first_seen
            duration = whale.total_duration + current_session
        else:
            # Not active: use accumulated total
            duration = whale.total_duration
        
        # Calculate spoof probability with enhanced detector
        spoof_info = {}
        if self.enhanced_detector and hasattr(whale, 'mid_price_on_appearance'):
            score = self.enhanced_detector.analyze_whale_lifecycle(
                whale, symbol, whale.mid_price_on_appearance
            )
            if score:
                spoof_info = {
                    'spoof_score': score.total_score,
                    'spoof_confidence': score.confidence_level,
                    'spoof_pattern': score.pattern_type,
                    'spoof_reasons': score.reasons[:3]  # Top 3 reasons
                }
        
        result = {
            'whale_id': whale.whale_id,
            'symbol': whale.symbol,
            'side': whale.side,
            'initial_price': whale.initial_price,
            'current_price': whale.current_price,
            'initial_size': whale.initial_size,
            'current_size': whale.current_size,
            'initial_value_usd': whale.initial_value_usd,
            'current_value_usd': whale.current_value_usd,
            'duration_seconds': duration,
            'size_changes_count': len(whale.size_changes),
            'disappearances': whale.disappearances,
            'max_size_seen': whale.max_size_seen,
            'min_size_seen': whale.min_size_seen,
            'size_variance_pct': ((whale.max_size_seen - whale.min_size_seen) / whale.initial_size * 100) if whale.initial_size > 0 else 0,
            'is_active': whale_id in self.active_whales.get(symbol, {}),
            'likely_spoof': self._is_likely_spoof(whale, duration),
            'percentage_of_book': whale.percentage_of_book,
            'level': whale.level,
            'first_seen': datetime.fromtimestamp(whale.first_seen).isoformat(),
            'last_seen': datetime.fromtimestamp(whale.last_seen).isoformat()
        }
        
        # Add enhanced scoring if available
        result.update(spoof_info)
        
        return result
        
    def get_statistics(self) -> Dict:
        """Get tracking statistics"""
        
        total_active = sum(len(whales) for whales in self.active_whales.values())
        total_recent = sum(len(whales) for whales in self.recent_whales.values())
        
        return {
            'total_whales_tracked': self.total_whales_tracked,
            'currently_active': total_active,
            'recently_disappeared': total_recent,
            'total_spoofs_detected': self.total_spoofs_detected,
            'historical_whales': len(self.whale_history)
        }