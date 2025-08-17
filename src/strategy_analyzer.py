"""
Whale Trading Strategy Analyzer
Analyzes whale activity patterns to generate trading signals
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
from dataclasses import dataclass, asdict


@dataclass
class TradingSignal:
    """Trading signal based on whale activity"""
    timestamp: datetime
    symbol: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float  # 0-1
    reason: str
    whale_indicators: Dict
    price_at_signal: float
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    
    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'action': self.action,
            'confidence': self.confidence,
            'reason': self.reason,
            'whale_indicators': self.whale_indicators,
            'price_at_signal': self.price_at_signal,
            'target_price': self.target_price,
            'stop_loss': self.stop_loss
        }


class WhaleStrategyAnalyzer:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.strategies = {
            'wall_fade': self.wall_fade_strategy,
            'whale_accumulation': self.whale_accumulation_strategy,
            'spoofing_detection': self.spoofing_detection_strategy,
            'imbalance_momentum': self.imbalance_momentum_strategy,
            'mega_whale_reversal': self.mega_whale_reversal_strategy
        }
        
    def load_data(self, symbol: str, date: str, hour: Optional[int] = None) -> Dict[str, pd.DataFrame]:
        """Load all data types for a symbol"""
        data = {}
        
        # Load whale data
        whale_path = self.data_dir / "whales" / symbol
        if hour is not None:
            whale_file = whale_path / f"{symbol}_whales_{date}_{hour:02d}.csv"
        else:
            whale_files = list(whale_path.glob(f"{symbol}_whales_{date}_*.csv"))
            whale_file = whale_files[0] if whale_files else None
            
        if whale_file and whale_file.exists():
            data['whales'] = pd.read_csv(whale_file)
            data['whales']['timestamp'] = pd.to_datetime(data['whales']['timestamp'])
        
        # Load price data
        price_path = self.data_dir / "prices" / symbol
        if hour is not None:
            price_file = price_path / f"{symbol}_prices_{date}_{hour:02d}.csv"
        else:
            price_files = list(price_path.glob(f"{symbol}_prices_{date}_*.csv"))
            price_file = price_files[0] if price_files else None
            
        if price_file and price_file.exists():
            data['prices'] = pd.read_csv(price_file)
            data['prices']['timestamp'] = pd.to_datetime(data['prices']['timestamp'])
            
        # Load spoofing data
        spoof_path = self.data_dir / "spoofing" / symbol
        if hour is not None:
            spoof_file = spoof_path / f"{symbol}_spoofing_{date}_{hour:02d}.csv"
        else:
            spoof_files = list(spoof_path.glob(f"{symbol}_spoofing_{date}_*.csv"))
            spoof_file = spoof_files[0] if spoof_files else None
            
        if spoof_file and spoof_file.exists():
            data['spoofing'] = pd.read_csv(spoof_file)
            data['spoofing']['timestamp'] = pd.to_datetime(data['spoofing']['timestamp'])
            
        return data
    
    def wall_fade_strategy(self, data: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
        """
        Strategy: Fade large sell walls that appear as resistance
        Logic: When mega whale sell walls appear (>$500k, >50% of book), 
               price often tests them. If wall disappears quickly, it was likely spoofing.
               Trade opposite direction of persistent walls.
        """
        signals = []
        
        if 'whales' not in data or 'prices' not in data:
            return signals
            
        whales_df = data['whales']
        prices_df = data['prices']
        
        # Find mega whale sell walls
        mega_sells = whales_df[
            (whales_df['side'] == 'ask') & 
            (whales_df['value_usd'] > 500000) &
            (whales_df['percentage_of_book'] > 50)
        ]
        
        for _, whale in mega_sells.iterrows():
            # Check if wall persisted or disappeared quickly
            whale_duration = whale['duration_seconds'] if 'duration_seconds' in whale else 0
            
            # Get price at whale appearance
            price_at_time = prices_df[prices_df['timestamp'] >= whale['timestamp']].iloc[0] if len(prices_df[prices_df['timestamp'] >= whale['timestamp']]) > 0 else None
            
            if price_at_time is not None:
                current_price = price_at_time['last_price']
                
                if whale_duration < 60:  # Likely spoofing - trade in direction of wall
                    signal = TradingSignal(
                        timestamp=whale['timestamp'],
                        symbol=whale['symbol'],
                        action='BUY',
                        confidence=0.7,
                        reason=f"Spoofing sell wall detected at ${whale['price']:.4f}",
                        whale_indicators={
                            'wall_size_usd': whale['value_usd'],
                            'book_percentage': whale['percentage_of_book'],
                            'duration': whale_duration,
                            'wall_price': whale['price']
                        },
                        price_at_signal=current_price,
                        target_price=whale['price'] * 1.02,  # Target 2% above wall
                        stop_loss=current_price * 0.98  # 2% stop loss
                    )
                    signals.append(signal)
                    
                elif whale_duration > 300:  # Persistent wall - fade it
                    signal = TradingSignal(
                        timestamp=whale['timestamp'],
                        symbol=whale['symbol'],
                        action='SELL',
                        confidence=0.6,
                        reason=f"Persistent sell wall resistance at ${whale['price']:.4f}",
                        whale_indicators={
                            'wall_size_usd': whale['value_usd'],
                            'book_percentage': whale['percentage_of_book'],
                            'duration': whale_duration,
                            'wall_price': whale['price']
                        },
                        price_at_signal=current_price,
                        target_price=current_price * 0.98,  # Target 2% below
                        stop_loss=whale['price'] * 1.01  # Stop above wall
                    )
                    signals.append(signal)
                    
        return signals
    
    def whale_accumulation_strategy(self, data: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
        """
        Strategy: Follow whale accumulation patterns
        Logic: When multiple whale buy orders stack up (accumulation),
               it often precedes price movement up
        """
        signals = []
        
        if 'whales' not in data or 'prices' not in data:
            return signals
            
        whales_df = data['whales']
        prices_df = data['prices']
        
        # Group whales by 5-minute windows
        whales_df['time_window'] = pd.to_datetime(whales_df['timestamp']).dt.floor('5min')
        
        # Count whale buys per window
        whale_buys = whales_df[whales_df['side'] == 'bid'].groupby('time_window').agg({
            'value_usd': ['sum', 'count'],
            'percentage_of_book': 'mean',
            'price': 'mean'
        }).reset_index()
        
        whale_buys.columns = ['time_window', 'total_value', 'count', 'avg_book_pct', 'avg_price']
        
        # Find strong accumulation periods
        strong_accumulation = whale_buys[
            (whale_buys['total_value'] > 300000) &
            (whale_buys['count'] >= 3) &
            (whale_buys['avg_book_pct'] > 20)
        ]
        
        for _, acc in strong_accumulation.iterrows():
            # Get price at accumulation time
            price_at_time = prices_df[prices_df['timestamp'] >= acc['time_window']].iloc[0] if len(prices_df[prices_df['timestamp'] >= acc['time_window']]) > 0 else None
            
            if price_at_time is not None:
                signal = TradingSignal(
                    timestamp=acc['time_window'],
                    symbol=whales_df.iloc[0]['symbol'],
                    action='BUY',
                    confidence=0.75,
                    reason=f"Strong whale accumulation detected: {acc['count']} whales, ${acc['total_value']:.0f} total",
                    whale_indicators={
                        'total_whale_value': acc['total_value'],
                        'whale_count': acc['count'],
                        'avg_book_percentage': acc['avg_book_pct'],
                        'avg_whale_price': acc['avg_price']
                    },
                    price_at_signal=price_at_time['last_price'],
                    target_price=price_at_time['last_price'] * 1.025,  # 2.5% target
                    stop_loss=acc['avg_price'] * 0.99  # Stop below whale avg price
                )
                signals.append(signal)
                
        return signals
    
    def spoofing_detection_strategy(self, data: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
        """
        Strategy: Trade based on spoofing detection
        Logic: When spoofing is detected (large orders that disappear quickly),
               trade in the opposite direction as the spoof
        """
        signals = []
        
        if 'spoofing' not in data or 'prices' not in data:
            return signals
            
        spoofing_df = data['spoofing']
        prices_df = data['prices']
        
        if len(spoofing_df) == 0:
            return signals
            
        for _, spoof in spoofing_df.iterrows():
            # Get price at spoof time
            price_at_time = prices_df[prices_df['timestamp'] >= spoof['timestamp']].iloc[0] if len(prices_df[prices_df['timestamp'] >= spoof['timestamp']]) > 0 else None
            
            if price_at_time is not None:
                # Trade opposite of spoof direction
                action = 'BUY' if spoof['side'] == 'ask' else 'SELL'
                
                signal = TradingSignal(
                    timestamp=spoof['timestamp'],
                    symbol=spoof['symbol'],
                    action=action,
                    confidence=0.8,
                    reason=f"Spoofing detected on {spoof['side']} side, ${spoof['initial_value_usd']:.0f}",
                    whale_indicators={
                        'spoof_size': spoof['initial_value_usd'],
                        'spoof_duration': spoof['time_active_seconds'],
                        'spoof_side': spoof['side'],
                        'spoof_pattern': spoof.get('spoof_pattern', 'unknown')
                    },
                    price_at_signal=price_at_time['last_price'],
                    target_price=price_at_time['last_price'] * (1.02 if action == 'BUY' else 0.98),
                    stop_loss=price_at_time['last_price'] * (0.98 if action == 'BUY' else 1.02)
                )
                signals.append(signal)
                
        return signals
    
    def imbalance_momentum_strategy(self, data: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
        """
        Strategy: Trade based on order book imbalance with whale presence
        Logic: Strong imbalance + whale orders = momentum continuation
        """
        signals = []
        
        if 'prices' not in data or 'whales' not in data:
            return signals
            
        prices_df = data['prices']
        whales_df = data['whales']
        
        # Calculate rolling imbalance
        if 'volume_imbalance' in prices_df.columns:
            prices_df['imbalance_ma'] = prices_df['volume_imbalance'].rolling(window=10).mean()
            
            # Find extreme imbalances with whale presence
            for i, row in prices_df.iterrows():
                if pd.isna(row.get('imbalance_ma', None)):
                    continue
                    
                # Check for whale presence in same time window
                time_window_start = row['timestamp'] - timedelta(minutes=1)
                time_window_end = row['timestamp'] + timedelta(minutes=1)
                
                window_whales = whales_df[
                    (whales_df['timestamp'] >= time_window_start) &
                    (whales_df['timestamp'] <= time_window_end)
                ]
                
                if len(window_whales) > 0 and abs(row['imbalance_ma']) > 0.5:
                    # Strong imbalance with whale presence
                    action = 'BUY' if row['imbalance_ma'] > 0.5 else 'SELL'
                    
                    signal = TradingSignal(
                        timestamp=row['timestamp'],
                        symbol=prices_df.iloc[0]['symbol'],
                        action=action,
                        confidence=0.65,
                        reason=f"Strong {'buy' if action == 'BUY' else 'sell'} imbalance with whale activity",
                        whale_indicators={
                            'imbalance': row['imbalance_ma'],
                            'whale_count': len(window_whales),
                            'total_whale_value': window_whales['value_usd'].sum()
                        },
                        price_at_signal=row['last_price'],
                        target_price=row['last_price'] * (1.015 if action == 'BUY' else 0.985),
                        stop_loss=row['last_price'] * (0.99 if action == 'BUY' else 1.01)
                    )
                    signals.append(signal)
                    
        return signals
    
    def mega_whale_reversal_strategy(self, data: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
        """
        Strategy: Trade reversals when mega whales (>$1M) appear
        Logic: Mega whales often mark local tops/bottoms
        """
        signals = []
        
        if 'whales' not in data or 'prices' not in data:
            return signals
            
        whales_df = data['whales']
        prices_df = data['prices']
        
        # Find mega whales
        mega_whales = whales_df[whales_df['value_usd'] > 1000000]
        
        for _, whale in mega_whales.iterrows():
            # Get price context
            price_at_time = prices_df[prices_df['timestamp'] >= whale['timestamp']].iloc[0] if len(prices_df[prices_df['timestamp'] >= whale['timestamp']]) > 0 else None
            
            if price_at_time is not None:
                # Trade reversal - opposite of whale side
                action = 'SELL' if whale['side'] == 'bid' else 'BUY'
                
                signal = TradingSignal(
                    timestamp=whale['timestamp'],
                    symbol=whale['symbol'],
                    action=action,
                    confidence=0.85,
                    reason=f"Mega whale ${whale['value_usd']/1e6:.1f}M on {whale['side']} - potential reversal",
                    whale_indicators={
                        'whale_size': whale['value_usd'],
                        'whale_side': whale['side'],
                        'book_percentage': whale['percentage_of_book'],
                        'whale_price': whale['price']
                    },
                    price_at_signal=price_at_time['last_price'],
                    target_price=price_at_time['last_price'] * (1.03 if action == 'BUY' else 0.97),
                    stop_loss=whale['price'] * (0.995 if action == 'BUY' else 1.005)
                )
                signals.append(signal)
                
        return signals
    
    def analyze_symbol(self, symbol: str, date: str, strategies: Optional[List[str]] = None) -> Dict:
        """Analyze a symbol with specified strategies"""
        if strategies is None:
            strategies = list(self.strategies.keys())
            
        all_signals = []
        analysis_results = {
            'symbol': symbol,
            'date': date,
            'strategies_used': strategies,
            'signals': [],
            'summary': {}
        }
        
        # Load data for all hours
        for hour in range(24):
            data = self.load_data(symbol, date, hour)
            if not data:
                continue
                
            # Run each strategy
            for strategy_name in strategies:
                if strategy_name in self.strategies:
                    strategy_func = self.strategies[strategy_name]
                    signals = strategy_func(data)
                    
                    for signal in signals:
                        signal_dict = signal.to_dict()
                        signal_dict['strategy'] = strategy_name
                        all_signals.append(signal_dict)
        
        # Sort signals by timestamp
        all_signals.sort(key=lambda x: x['timestamp'])
        analysis_results['signals'] = all_signals
        
        # Generate summary statistics
        if all_signals:
            df_signals = pd.DataFrame(all_signals)
            analysis_results['summary'] = {
                'total_signals': len(all_signals),
                'buy_signals': len(df_signals[df_signals['action'] == 'BUY']),
                'sell_signals': len(df_signals[df_signals['action'] == 'SELL']),
                'avg_confidence': df_signals['confidence'].mean(),
                'signals_by_strategy': df_signals.groupby('strategy').size().to_dict(),
                'high_confidence_signals': len(df_signals[df_signals['confidence'] > 0.7])
            }
        else:
            analysis_results['summary'] = {
                'total_signals': 0,
                'message': 'No signals generated for this period'
            }
            
        return analysis_results
    
    def save_analysis(self, analysis: Dict, output_file: str):
        """Save analysis results to JSON"""
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
            
    def generate_report(self, analysis: Dict) -> str:
        """Generate a text report from analysis"""
        report = []
        report.append(f"=== Whale Trading Strategy Analysis ===")
        report.append(f"Symbol: {analysis['symbol']}")
        report.append(f"Date: {analysis['date']}")
        report.append(f"Strategies: {', '.join(analysis['strategies_used'])}")
        report.append("")
        
        summary = analysis['summary']
        if summary.get('total_signals', 0) > 0:
            report.append(f"📊 Summary Statistics:")
            report.append(f"  Total Signals: {summary['total_signals']}")
            report.append(f"  Buy Signals: {summary['buy_signals']}")
            report.append(f"  Sell Signals: {summary['sell_signals']}")
            report.append(f"  Avg Confidence: {summary['avg_confidence']:.2%}")
            report.append(f"  High Confidence (>70%): {summary['high_confidence_signals']}")
            report.append("")
            
            report.append("📈 Signals by Strategy:")
            for strategy, count in summary['signals_by_strategy'].items():
                report.append(f"  {strategy}: {count} signals")
            report.append("")
            
            # Top 10 high confidence signals
            signals_df = pd.DataFrame(analysis['signals'])
            top_signals = signals_df.nlargest(10, 'confidence')
            
            report.append("🎯 Top 10 High Confidence Signals:")
            for _, signal in top_signals.iterrows():
                report.append(f"  [{signal['timestamp']}] {signal['action']} @ ${signal['price_at_signal']:.4f}")
                report.append(f"    Strategy: {signal['strategy']}")
                report.append(f"    Confidence: {signal['confidence']:.1%}")
                report.append(f"    Reason: {signal['reason']}")
                if signal.get('target_price'):
                    report.append(f"    Target: ${signal['target_price']:.4f}")
                report.append("")
        else:
            report.append("No trading signals generated for this period.")
            
        return "\n".join(report)


if __name__ == "__main__":
    # Example usage
    analyzer = WhaleStrategyAnalyzer()
    
    # Analyze specific symbols
    symbols = ['WLDUSDT', '1000PEPEUSDT', 'SEIUSDT']
    date = '2025-08-17'
    
    for symbol in symbols:
        print(f"\nAnalyzing {symbol}...")
        analysis = analyzer.analyze_symbol(symbol, date)
        
        # Save results
        output_file = f"analysis_{symbol}_{date}.json"
        analyzer.save_analysis(analysis, output_file)
        
        # Print report
        report = analyzer.generate_report(analysis)
        print(report)
        print(f"Results saved to {output_file}")