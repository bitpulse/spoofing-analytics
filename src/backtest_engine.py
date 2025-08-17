"""
Backtesting Engine for Whale Trading Strategies
Simulates trading based on generated signals and calculates performance metrics
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
from dataclasses import dataclass, asdict


@dataclass
class Trade:
    """Represents a completed trade"""
    entry_time: datetime
    exit_time: datetime
    symbol: str
    side: str  # 'LONG' or 'SHORT'
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_percent: float
    exit_reason: str  # 'TARGET', 'STOP_LOSS', 'TIME_EXIT', 'SIGNAL'
    strategy: str
    confidence: float
    
    def to_dict(self):
        return {
            'entry_time': self.entry_time.isoformat(),
            'exit_time': self.exit_time.isoformat(),
            'symbol': self.symbol,
            'side': self.side,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'quantity': self.quantity,
            'pnl': self.pnl,
            'pnl_percent': self.pnl_percent,
            'exit_reason': self.exit_reason,
            'strategy': self.strategy,
            'confidence': self.confidence
        }


@dataclass
class BacktestResults:
    """Backtesting results and metrics"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    trades: List[Trade]
    equity_curve: List[float]
    
    def to_dict(self):
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'total_pnl': self.total_pnl,
            'total_return': self.total_return,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'profit_factor': self.profit_factor,
            'trades': [t.to_dict() for t in self.trades],
            'equity_curve': self.equity_curve
        }


class BacktestEngine:
    def __init__(self, initial_capital: float = 10000, position_size: float = 0.1):
        """
        Initialize backtesting engine
        
        Args:
            initial_capital: Starting capital for backtest
            position_size: Fraction of capital to use per trade (0.1 = 10%)
        """
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.capital = initial_capital
        self.trades = []
        self.open_positions = {}
        self.equity_curve = [initial_capital]
        
    def load_price_data(self, symbol: str, date: str, data_dir: str = "data") -> pd.DataFrame:
        """Load and combine price data for backtesting"""
        price_path = Path(data_dir) / "prices" / symbol
        price_files = list(price_path.glob(f"{symbol}_prices_{date}_*.csv"))
        
        if not price_files:
            return pd.DataFrame()
            
        # Combine all price files
        dfs = []
        for file in sorted(price_files):
            df = pd.read_csv(file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            dfs.append(df)
            
        combined_df = pd.concat(dfs, ignore_index=True)
        combined_df = combined_df.sort_values('timestamp')
        combined_df = combined_df.set_index('timestamp')
        
        # Forward fill price data for continuous series
        combined_df['last_price'] = combined_df['last_price'].ffill()
        
        return combined_df
    
    def execute_signal(self, signal: Dict, price_data: pd.DataFrame) -> Optional[Trade]:
        """Execute a trading signal"""
        signal_time = pd.to_datetime(signal['timestamp'])
        
        # Check if we already have an open position for this symbol
        if signal['symbol'] in self.open_positions:
            # Close existing position if opposite signal
            existing = self.open_positions[signal['symbol']]
            if (existing['side'] == 'LONG' and signal['action'] == 'SELL') or \
               (existing['side'] == 'SHORT' and signal['action'] == 'BUY'):
                # Close position
                exit_price = signal['price_at_signal']
                trade = self._close_position(
                    symbol=signal['symbol'],
                    exit_time=signal_time,
                    exit_price=exit_price,
                    exit_reason='SIGNAL'
                )
                if trade:
                    self.trades.append(trade)
            return None
            
        # Open new position
        if signal['action'] in ['BUY', 'SELL']:
            # Calculate position size
            position_value = self.capital * self.position_size
            entry_price = signal['price_at_signal']
            quantity = position_value / entry_price
            
            # Store open position
            self.open_positions[signal['symbol']] = {
                'entry_time': signal_time,
                'entry_price': entry_price,
                'quantity': quantity,
                'side': 'LONG' if signal['action'] == 'BUY' else 'SHORT',
                'target_price': signal.get('target_price'),
                'stop_loss': signal.get('stop_loss'),
                'strategy': signal.get('strategy', 'unknown'),
                'confidence': signal.get('confidence', 0.5)
            }
            
        return None
    
    def _close_position(self, symbol: str, exit_time: datetime, 
                       exit_price: float, exit_reason: str) -> Optional[Trade]:
        """Close an open position"""
        if symbol not in self.open_positions:
            return None
            
        position = self.open_positions[symbol]
        
        # Calculate PnL
        if position['side'] == 'LONG':
            pnl = (exit_price - position['entry_price']) * position['quantity']
            pnl_percent = (exit_price - position['entry_price']) / position['entry_price']
        else:  # SHORT
            pnl = (position['entry_price'] - exit_price) * position['quantity']
            pnl_percent = (position['entry_price'] - exit_price) / position['entry_price']
            
        # Update capital
        self.capital += pnl
        self.equity_curve.append(self.capital)
        
        # Create trade record
        trade = Trade(
            entry_time=position['entry_time'],
            exit_time=exit_time,
            symbol=symbol,
            side=position['side'],
            entry_price=position['entry_price'],
            exit_price=exit_price,
            quantity=position['quantity'],
            pnl=pnl,
            pnl_percent=pnl_percent,
            exit_reason=exit_reason,
            strategy=position['strategy'],
            confidence=position['confidence']
        )
        
        # Remove from open positions
        del self.open_positions[symbol]
        
        return trade
    
    def check_exits(self, timestamp: datetime, price_data: pd.DataFrame):
        """Check if any positions should be closed"""
        positions_to_close = []
        
        for symbol, position in self.open_positions.items():
            # Get current price
            if timestamp in price_data.index:
                current_price = price_data.loc[timestamp, 'last_price']
            else:
                # Find nearest price
                nearest_idx = price_data.index.get_indexer([timestamp], method='nearest')[0]
                if nearest_idx >= 0 and nearest_idx < len(price_data):
                    current_price = price_data.iloc[nearest_idx]['last_price']
                else:
                    continue
                    
            # Check target price
            if position.get('target_price'):
                if position['side'] == 'LONG' and current_price >= position['target_price']:
                    positions_to_close.append((symbol, current_price, 'TARGET'))
                elif position['side'] == 'SHORT' and current_price <= position['target_price']:
                    positions_to_close.append((symbol, current_price, 'TARGET'))
                    
            # Check stop loss
            if position.get('stop_loss'):
                if position['side'] == 'LONG' and current_price <= position['stop_loss']:
                    positions_to_close.append((symbol, current_price, 'STOP_LOSS'))
                elif position['side'] == 'SHORT' and current_price >= position['stop_loss']:
                    positions_to_close.append((symbol, current_price, 'STOP_LOSS'))
                    
            # Time-based exit (hold max 1 hour)
            if (timestamp - position['entry_time']).total_seconds() > 3600:
                positions_to_close.append((symbol, current_price, 'TIME_EXIT'))
                
        # Close positions
        for symbol, exit_price, exit_reason in positions_to_close:
            trade = self._close_position(symbol, timestamp, exit_price, exit_reason)
            if trade:
                self.trades.append(trade)
    
    def run_backtest(self, signals: List[Dict], symbol: str, date: str, 
                    data_dir: str = "data") -> BacktestResults:
        """Run backtest on signals"""
        # Reset state
        self.capital = self.initial_capital
        self.trades = []
        self.open_positions = {}
        self.equity_curve = [self.initial_capital]
        
        # Load price data
        price_data = self.load_price_data(symbol, date, data_dir)
        
        if price_data.empty:
            return self._calculate_results()
            
        # Sort signals by timestamp
        signals = sorted(signals, key=lambda x: x['timestamp'])
        
        # Process each timestamp in price data
        for timestamp in price_data.index:
            # Check for exits first
            self.check_exits(timestamp, price_data)
            
            # Check for new signals at this timestamp
            for signal in signals:
                signal_time = pd.to_datetime(signal['timestamp'])
                
                # Process signal if timestamp matches (within 1 minute)
                if abs((signal_time - timestamp).total_seconds()) < 60:
                    self.execute_signal(signal, price_data)
                    
        # Close any remaining positions at end of day
        for symbol in list(self.open_positions.keys()):
            last_price = price_data.iloc[-1]['last_price']
            trade = self._close_position(
                symbol, 
                price_data.index[-1], 
                last_price, 
                'TIME_EXIT'
            )
            if trade:
                self.trades.append(trade)
                
        return self._calculate_results()
    
    def _calculate_results(self) -> BacktestResults:
        """Calculate backtesting metrics"""
        if not self.trades:
            return BacktestResults(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0,
                total_pnl=0,
                total_return=0,
                sharpe_ratio=0,
                max_drawdown=0,
                avg_win=0,
                avg_loss=0,
                profit_factor=0,
                trades=[],
                equity_curve=self.equity_curve
            )
            
        # Calculate metrics
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]
        
        total_pnl = sum(t.pnl for t in self.trades)
        total_return = (self.capital - self.initial_capital) / self.initial_capital
        
        # Win rate
        win_rate = len(winning_trades) / len(self.trades) if self.trades else 0
        
        # Average win/loss
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        
        # Profit factor
        gross_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0
        gross_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Sharpe ratio (simplified - daily)
        if len(self.trades) > 1:
            returns = [t.pnl_percent for t in self.trades]
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0
            
        # Max drawdown
        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max
        max_drawdown = abs(np.min(drawdown)) if len(drawdown) > 0 else 0
        
        return BacktestResults(
            total_trades=len(self.trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            trades=self.trades,
            equity_curve=self.equity_curve
        )
    
    def generate_report(self, results: BacktestResults) -> str:
        """Generate backtest report"""
        report = []
        report.append("=== Backtest Results ===")
        report.append(f"Initial Capital: ${self.initial_capital:,.2f}")
        report.append(f"Final Capital: ${self.capital:,.2f}")
        report.append("")
        
        report.append("📊 Performance Metrics:")
        report.append(f"  Total Trades: {results.total_trades}")
        report.append(f"  Winning Trades: {results.winning_trades}")
        report.append(f"  Losing Trades: {results.losing_trades}")
        report.append(f"  Win Rate: {results.win_rate:.1%}")
        report.append("")
        
        report.append("💰 Profit/Loss:")
        report.append(f"  Total PnL: ${results.total_pnl:,.2f}")
        report.append(f"  Total Return: {results.total_return:.1%}")
        report.append(f"  Average Win: ${results.avg_win:,.2f}")
        report.append(f"  Average Loss: ${results.avg_loss:,.2f}")
        report.append(f"  Profit Factor: {results.profit_factor:.2f}")
        report.append("")
        
        report.append("📈 Risk Metrics:")
        report.append(f"  Sharpe Ratio: {results.sharpe_ratio:.2f}")
        report.append(f"  Max Drawdown: {results.max_drawdown:.1%}")
        report.append("")
        
        if results.trades:
            report.append("🏆 Best Trades:")
            best_trades = sorted(results.trades, key=lambda x: x.pnl, reverse=True)[:3]
            for i, trade in enumerate(best_trades, 1):
                report.append(f"  {i}. {trade.strategy} - ${trade.pnl:.2f} ({trade.pnl_percent:.1%})")
                
            report.append("")
            report.append("📉 Worst Trades:")
            worst_trades = sorted(results.trades, key=lambda x: x.pnl)[:3]
            for i, trade in enumerate(worst_trades, 1):
                report.append(f"  {i}. {trade.strategy} - ${trade.pnl:.2f} ({trade.pnl_percent:.1%})")
                
            report.append("")
            report.append("📊 Exit Reasons:")
            exit_reasons = {}
            for trade in results.trades:
                exit_reasons[trade.exit_reason] = exit_reasons.get(trade.exit_reason, 0) + 1
            for reason, count in exit_reasons.items():
                report.append(f"  {reason}: {count} trades")
                
        return "\n".join(report)


if __name__ == "__main__":
    # Example usage
    from src.strategy_analyzer import WhaleStrategyAnalyzer
    
    # Generate signals
    analyzer = WhaleStrategyAnalyzer()
    symbol = 'WLDUSDT'
    date = '2025-08-17'
    
    print(f"Analyzing {symbol} for {date}...")
    analysis = analyzer.analyze_symbol(symbol, date)
    
    # Run backtest
    engine = BacktestEngine(initial_capital=10000, position_size=0.1)
    
    # Filter signals for the symbol
    signals = [s for s in analysis['signals'] if s['symbol'] == symbol]
    
    print(f"\nRunning backtest with {len(signals)} signals...")
    results = engine.run_backtest(signals, symbol, date)
    
    # Print report
    report = engine.generate_report(results)
    print(report)
    
    # Save results
    with open(f"backtest_{symbol}_{date}.json", 'w') as f:
        json.dump(results.to_dict(), f, indent=2, default=str)