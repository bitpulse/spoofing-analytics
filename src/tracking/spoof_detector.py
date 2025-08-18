"""
Enhanced Spoofing Detection System
==================================

This module provides improved spoofing detection with:
- Dynamic thresholds based on market conditions
- Symbol-specific calibration
- Context-aware scoring
- Confidence-based classification

Key improvements over basic detection:
1. Excludes HFT noise (<10 seconds)
2. Dynamic value thresholds based on average order size
3. Distance from mid-price analysis
4. Market volatility consideration
5. Probabilistic scoring instead of binary classification
"""

import time
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import statistics
from loguru import logger


@dataclass
class MarketContext:
    """Market conditions for context-aware detection"""
    avg_order_size: float
    avg_trade_size: float
    recent_volatility: float
    bid_ask_spread_bps: float
    order_book_depth: float
    volume_24h: float
    recent_trade_frequency: float  # trades per minute
    liquidity_score: float  # 0-1, higher = more liquid


@dataclass
class SpoofScore:
    """Detailed spoofing probability score"""
    total_score: float  # 0-100
    duration_score: float
    size_pattern_score: float
    distance_score: float
    behavior_score: float
    context_score: float
    confidence_level: str  # 'high', 'medium', 'low', 'unlikely'
    reasons: List[str]
    pattern_type: str  # 'classic', 'layering', 'flickering', 'size_manipulation'


class EnhancedSpoofDetector:
    """
    Advanced spoofing detection with market-adaptive thresholds
    and confidence scoring
    """
    
    def __init__(self):
        # Market data tracking (per symbol)
        self.market_contexts: Dict[str, MarketContext] = {}
        self.order_history: Dict[str, deque] = {}  # Recent orders for statistics
        self.trade_history: Dict[str, deque] = {}  # Recent trades
        self.volatility_cache: Dict[str, float] = {}
        
        # Calibration parameters (can be tuned per symbol)
        self.calibrations = {
            # Meme coins / High volatility
            'HIGH_VOL': {
                'min_duration': 5,      # Lower threshold for meme coins
                'max_duration': 90,
                'size_multiplier': 10,  # 10x average order (more sensitive)
                'distance_threshold': 0.015,  # 1.5% from mid
                'flickering_threshold': 3,    # Need 3+ disappearances
                'size_variance_threshold': 0.35  # 35% size change
            },
            # Major coins / Low volatility  
            'LOW_VOL': {
                'min_duration': 15,
                'max_duration': 120,
                'size_multiplier': 100,  
                'distance_threshold': 0.005,  # 0.5% from mid
                'flickering_threshold': 3,
                'size_variance_threshold': 0.3
            },
            # Default / Medium volatility
            'DEFAULT': {
                'min_duration': 10,
                'max_duration': 90,
                'size_multiplier': 50,
                'distance_threshold': 0.01,  # 1% from mid
                'flickering_threshold': 4,
                'size_variance_threshold': 0.35
            }
        }
        
        # Detection statistics
        self.stats = {
            'total_analyzed': 0,
            'high_confidence_spoofs': 0,
            'medium_confidence_spoofs': 0,
            'low_confidence_spoofs': 0
        }
        
    def get_calibration(self, symbol: str) -> Dict:
        """Get calibration parameters based on symbol characteristics"""
        # Determine volatility category
        if symbol in ['PEPEUSDT', 'BONKUSDT', 'WIFUSDT', 'SHIBUSDT', 'FLOKIUSDT']:
            return self.calibrations['HIGH_VOL']
        elif symbol in ['BTCUSDT', 'ETHUSDT', 'USDTUSDT']:
            return self.calibrations['LOW_VOL']
        else:
            return self.calibrations['DEFAULT']
    
    def update_market_context(self, symbol: str, snapshot: any):
        """Update market context from order book snapshot"""
        if symbol not in self.order_history:
            self.order_history[symbol] = deque(maxlen=1000)
            self.trade_history[symbol] = deque(maxlen=500)
        
        # Calculate average order sizes
        if symbol in self.order_history and len(self.order_history[symbol]) > 10:
            recent_orders = list(self.order_history[symbol])
            avg_order = statistics.mean([o['value_usd'] for o in recent_orders])
            avg_trade = statistics.mean([t['value_usd'] for t in self.trade_history[symbol]]) if self.trade_history[symbol] else avg_order * 0.1
        else:
            # Bootstrap with snapshot data
            all_orders = snapshot.bids[:20] + snapshot.asks[:20]
            avg_order = statistics.mean([o.value_usd for o in all_orders]) if all_orders else 10000
            avg_trade = avg_order * 0.1  # Estimate
        
        # Calculate volatility (price range over recent period)
        if symbol in self.order_history and len(self.order_history[symbol]) > 50:
            recent_prices = [o['price'] for o in list(self.order_history[symbol])[-100:]]
            price_std = statistics.stdev(recent_prices) if len(recent_prices) > 1 else 0
            volatility = (price_std / statistics.mean(recent_prices)) * 100 if recent_prices else 1.0
        else:
            volatility = 2.0  # Default 2% volatility
        
        # Calculate liquidity score (0-1)
        depth_score = min(snapshot.bid_volume_total + snapshot.ask_volume_total, 1000000) / 1000000
        spread_score = max(0, 1 - (snapshot.spread_bps / 100))  # Lower spread = better liquidity
        liquidity_score = (depth_score + spread_score) / 2
        
        # Update context
        self.market_contexts[symbol] = MarketContext(
            avg_order_size=avg_order,
            avg_trade_size=avg_trade,
            recent_volatility=volatility,
            bid_ask_spread_bps=snapshot.spread_bps,
            order_book_depth=snapshot.bid_volume_total + snapshot.ask_volume_total,
            volume_24h=getattr(snapshot, 'volume_24h', 0),
            recent_trade_frequency=len(self.trade_history[symbol]) / 5 if self.trade_history[symbol] else 1,
            liquidity_score=liquidity_score
        )
        
        self.volatility_cache[symbol] = volatility
        
    def calculate_spoof_score(self, 
                             whale: any,
                             symbol: str,
                             duration: float,
                             mid_price: float) -> SpoofScore:
        """
        Calculate comprehensive spoofing probability score
        
        Returns score 0-100 with detailed breakdown
        """
        self.stats['total_analyzed'] += 1
        
        # Get calibration and context
        calib = self.get_calibration(symbol)
        context = self.market_contexts.get(symbol)
        
        if not context:
            # No context yet, use defaults
            context = MarketContext(
                avg_order_size=50000,
                avg_trade_size=5000,
                recent_volatility=2.0,
                bid_ask_spread_bps=10,
                order_book_depth=1000000,
                volume_24h=10000000,
                recent_trade_frequency=10,
                liquidity_score=0.5
            )
        
        reasons = []
        scores = {
            'duration': 0,
            'size_pattern': 0,
            'distance': 0,
            'behavior': 0,
            'context': 0
        }
        
        # 1. Duration Analysis (0-25 points)
        if calib['min_duration'] <= duration <= calib['max_duration']:
            # Perfect spoofing window
            if 15 <= duration <= 45:
                scores['duration'] = 25
                reasons.append(f"Perfect spoof duration: {duration:.1f}s")
            else:
                scores['duration'] = 20
                reasons.append(f"Suspicious duration: {duration:.1f}s")
        elif duration < calib['min_duration']:
            if duration < 5:
                scores['duration'] = 0  # Too fast, likely HFT
                reasons.append(f"Too fast for spoofing: {duration:.1f}s (HFT)")
            else:
                scores['duration'] = 10
                reasons.append(f"Quick order: {duration:.1f}s")
        else:
            scores['duration'] = 5  # Too long, might be legitimate
            reasons.append(f"Long duration: {duration:.1f}s (possibly legitimate)")
        
        # 2. Size Pattern Analysis (0-25 points)
        size_multiplier = whale.current_value_usd / context.avg_order_size if context.avg_order_size > 0 else 1
        
        if size_multiplier > calib['size_multiplier']:
            scores['size_pattern'] = 20
            reasons.append(f"Huge order: {size_multiplier:.1f}x average")
        elif size_multiplier > calib['size_multiplier'] * 0.5:
            scores['size_pattern'] = 15
            reasons.append(f"Large order: {size_multiplier:.1f}x average")
        else:
            scores['size_pattern'] = 5
        
        # Check for size manipulation
        if hasattr(whale, 'max_size_seen') and hasattr(whale, 'min_size_seen'):
            size_variance = (whale.max_size_seen - whale.min_size_seen) / whale.initial_size if whale.initial_size > 0 else 0
            if size_variance > calib['size_variance_threshold']:
                scores['size_pattern'] += 5
                reasons.append(f"Size manipulation: {size_variance:.1%} variance")
        
        # 3. Distance from Mid-Price (0-20 points)
        if mid_price > 0 and whale.current_price > 0:
            price_distance = abs(whale.current_price - mid_price) / mid_price
            
            if 0.005 < price_distance < 0.03:  # Sweet spot for spoofing
                if price_distance < calib['distance_threshold']:
                    scores['distance'] = 15
                    reasons.append(f"Suspicious distance: {price_distance:.2%} from mid")
                else:
                    scores['distance'] = 20
                    reasons.append(f"Perfect spoof distance: {price_distance:.2%} from mid")
            elif price_distance <= 0.005:
                scores['distance'] = 5  # Too close, might execute
                reasons.append("Very close to mid-price (might trade)")
            else:
                scores['distance'] = 10  # Far but could still be spoofing
        else:
            # No price data, can't assess distance
            scores['distance'] = 5
        
        # 4. Behavioral Analysis (0-20 points)
        if hasattr(whale, 'disappearances'):
            if whale.disappearances >= calib['flickering_threshold']:
                scores['behavior'] = 20
                reasons.append(f"Flickering pattern: {whale.disappearances} disappearances")
            elif whale.disappearances >= 2:
                scores['behavior'] = 10
                reasons.append(f"Multiple appearances: {whale.disappearances}")
        
        # Check if never traded
        if hasattr(whale, 'trades_executed') and whale.trades_executed == 0 and duration > 20:
            scores['behavior'] += 5
            reasons.append("Never executed despite duration")
        
        # 5. Market Context (0-10 points)
        # Low liquidity = more likely spoofing
        if context.liquidity_score < 0.3:
            scores['context'] = 10
            reasons.append("Low liquidity environment")
        elif context.liquidity_score < 0.5:
            scores['context'] = 5
            reasons.append("Medium liquidity")
        
        # High volatility = more manipulation
        if context.recent_volatility > 5:
            scores['context'] += 5
            reasons.append(f"High volatility: {context.recent_volatility:.1f}%")
        
        # Calculate total score
        total_score = sum(scores.values())
        
        # Determine confidence level (adjusted for better sensitivity)
        if total_score >= 60:
            confidence = 'high'
            self.stats['high_confidence_spoofs'] += 1
        elif total_score >= 40:
            confidence = 'medium'
            self.stats['medium_confidence_spoofs'] += 1
        elif total_score >= 25:
            confidence = 'low'
            self.stats['low_confidence_spoofs'] += 1
        else:
            confidence = 'unlikely'
        
        # Determine pattern type
        if whale.disappearances >= calib['flickering_threshold']:
            pattern = 'flickering'
        elif size_variance > calib['size_variance_threshold'] if 'size_variance' in locals() else False:
            pattern = 'size_manipulation'
        elif scores['distance'] >= 15 and scores['duration'] >= 20:
            pattern = 'classic'
        else:
            pattern = 'unknown'
        
        return SpoofScore(
            total_score=total_score,
            duration_score=scores['duration'],
            size_pattern_score=scores['size_pattern'],
            distance_score=scores['distance'],
            behavior_score=scores['behavior'],
            context_score=scores['context'],
            confidence_level=confidence,
            reasons=reasons,
            pattern_type=pattern
        )
    
    def should_alert(self, score: SpoofScore, min_confidence: str = 'medium') -> bool:
        """Determine if spoof score warrants an alert"""
        confidence_levels = {'unlikely': 0, 'low': 1, 'medium': 2, 'high': 3}
        min_level = confidence_levels.get(min_confidence, 2)
        current_level = confidence_levels.get(score.confidence_level, 0)
        return current_level >= min_level
    
    def get_statistics(self) -> Dict:
        """Get detection statistics"""
        total = self.stats['total_analyzed']
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            'high_confidence_rate': self.stats['high_confidence_spoofs'] / total * 100,
            'medium_confidence_rate': self.stats['medium_confidence_spoofs'] / total * 100,
            'low_confidence_rate': self.stats['low_confidence_spoofs'] / total * 100,
            'detection_rate': (self.stats['high_confidence_spoofs'] + 
                             self.stats['medium_confidence_spoofs']) / total * 100
        }
    
    def analyze_whale_lifecycle(self, whale: any, symbol: str, mid_price: float) -> Optional[SpoofScore]:
        """
        Analyze a whale's complete lifecycle for spoofing behavior
        """
        # Calculate duration
        if hasattr(whale, 'first_seen') and hasattr(whale, 'last_seen'):
            duration = whale.last_seen - whale.first_seen
        elif hasattr(whale, 'total_duration'):
            duration = whale.total_duration
        else:
            return None
        
        # Update market context if we have snapshot data
        if hasattr(whale, 'snapshot'):
            self.update_market_context(symbol, whale.snapshot)
        
        # Calculate comprehensive spoof score
        score = self.calculate_spoof_score(whale, symbol, duration, mid_price)
        
        # Log high-confidence spoofs
        if score.confidence_level == 'high':
            logger.warning(
                f"HIGH CONFIDENCE SPOOF DETECTED: {symbol} "
                f"Score: {score.total_score:.1f} "
                f"Pattern: {score.pattern_type} "
                f"Reasons: {', '.join(score.reasons[:3])}"
            )
        
        return score