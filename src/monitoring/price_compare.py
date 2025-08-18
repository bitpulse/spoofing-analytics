#!/usr/bin/env python3
"""
Price Comparison Monitor
========================
Compares local CSV prices with Binance API prices to verify data accuracy.

Usage:
    python -m src.monitoring.price_compare              # Compare all symbols once
    python -m src.monitoring.price_compare WIFUSDT      # Compare specific symbol once
    python -m src.monitoring.price_compare -c           # Continuous monitoring (live update)
    python -m src.monitoring.price_compare -c -s        # Stream mode (new line per update)
    python -m src.monitoring.price_compare -c -i 100    # 100ms updates
    python -m src.monitoring.price_compare -c -s -i 100 # 100ms stream mode
"""

import os
import sys
import time
import csv
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import requests
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich import box
from rich.layout import Layout
from rich.align import Align
from loguru import logger

console = Console()


class PriceComparator:
    """Compares prices from different sources"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.prices_dir = self.data_dir / "prices"
        self.api_cache: Dict[str, Tuple[float, datetime]] = {}
        self.cache_duration = 2  # seconds
        
    def get_symbols_with_data(self) -> List[str]:
        """Get all symbols that have price data"""
        if not self.prices_dir.exists():
            return []
        
        symbols = []
        for symbol_dir in self.prices_dir.iterdir():
            if symbol_dir.is_dir():
                # Check if there are CSV files
                csv_files = list(symbol_dir.glob("*.csv"))
                if csv_files:
                    symbols.append(symbol_dir.name)
        
        return sorted(symbols)
    
    def get_local_price(self, symbol: str) -> Optional[Dict]:
        """Get the most recent price from local CSV"""
        try:
            prices_dir = self.prices_dir / symbol
            if not prices_dir.exists():
                return None
            
            # Find most recent CSV file
            csv_files = list(prices_dir.glob("*.csv"))
            if not csv_files:
                return None
            
            latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
            file_age = time.time() - latest_file.stat().st_mtime
            
            # Read last line
            with open(latest_file, 'r') as f:
                lines = f.readlines()
                if len(lines) > 1:
                    last_line = lines[-1].strip()
                    if last_line:
                        parts = last_line.split(',')
                        if len(parts) > 7:
                            return {
                                'timestamp': parts[0],
                                'last_price': float(parts[2]),
                                'mark_price': float(parts[3]),
                                'index_price': float(parts[4]),
                                'bid_price': float(parts[5]),
                                'ask_price': float(parts[6]),
                                'mid_price': float(parts[7]),
                                'file_age_seconds': file_age,
                                'source_file': latest_file.name
                            }
        except Exception as e:
            logger.error(f"Error reading local price for {symbol}: {e}")
        return None
    
    def get_api_price(self, symbol: str) -> Optional[Dict]:
        """Get current price from Binance API"""
        try:
            # Check cache first
            if symbol in self.api_cache:
                cached_price, cached_time = self.api_cache[symbol]
                if (datetime.now() - cached_time).seconds < self.cache_duration:
                    return cached_price
            
            # Fetch ticker data
            ticker_url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}"
            ticker_resp = requests.get(ticker_url, timeout=2)
            
            # Fetch order book for bid/ask
            depth_url = f"https://fapi.binance.com/fapi/v1/depth?symbol={symbol}&limit=5"
            depth_resp = requests.get(depth_url, timeout=2)
            
            if ticker_resp.status_code == 200 and depth_resp.status_code == 200:
                ticker = ticker_resp.json()
                depth = depth_resp.json()
                
                bid_price = float(depth['bids'][0][0]) if depth['bids'] else 0
                ask_price = float(depth['asks'][0][0]) if depth['asks'] else 0
                
                result = {
                    'last_price': float(ticker['lastPrice']),
                    'mark_price': float(ticker.get('markPrice', ticker['lastPrice'])),
                    'bid_price': bid_price,
                    'ask_price': ask_price,
                    'mid_price': (bid_price + ask_price) / 2,
                    'volume_24h': float(ticker['volume']),
                    'price_change_24h': float(ticker['priceChangePercent'])
                }
                
                # Cache the result
                self.api_cache[symbol] = (result, datetime.now())
                return result
                
        except Exception as e:
            logger.error(f"Error fetching API price for {symbol}: {e}")
        return None
    
    def compare_prices(self, symbol: str) -> Optional[Dict]:
        """Compare local and API prices for a symbol"""
        local = self.get_local_price(symbol)
        api = self.get_api_price(symbol)
        
        if not local or not api:
            return None
        
        # Calculate differences
        comparison = {
            'symbol': symbol,
            'local': local,
            'api': api,
            'differences': {
                'last_price': {
                    'local': local['last_price'],
                    'api': api['last_price'],
                    'diff': api['last_price'] - local['last_price'],
                    'diff_pct': ((api['last_price'] - local['last_price']) / local['last_price']) * 100
                },
                'bid_price': {
                    'local': local['bid_price'],
                    'api': api['bid_price'],
                    'diff': api['bid_price'] - local['bid_price'],
                    'diff_pct': ((api['bid_price'] - local['bid_price']) / local['bid_price']) * 100 if local['bid_price'] > 0 else 0
                },
                'ask_price': {
                    'local': local['ask_price'],
                    'api': api['ask_price'],
                    'diff': api['ask_price'] - local['ask_price'],
                    'diff_pct': ((api['ask_price'] - local['ask_price']) / local['ask_price']) * 100 if local['ask_price'] > 0 else 0
                },
                'mid_price': {
                    'local': local['mid_price'],
                    'api': api['mid_price'],
                    'diff': api['mid_price'] - local['mid_price'],
                    'diff_pct': ((api['mid_price'] - local['mid_price']) / local['mid_price']) * 100
                },
                'spread': {
                    'local': local['ask_price'] - local['bid_price'],
                    'api': api['ask_price'] - api['bid_price']
                }
            },
            'data_age_seconds': local['file_age_seconds']
        }
        
        return comparison
    
    def format_compact_view(self, comparisons: List[Dict]) -> Table:
        """Create a compact view for high-frequency monitoring"""
        table = Table(title=f"Live Price Monitor - {datetime.now().strftime('%H:%M:%S.%f')[:-3]}", box=box.SIMPLE)
        
        # Add columns
        table.add_column("Symbol", style="cyan", justify="left")
        table.add_column("Local Price", style="green", justify="right")
        table.add_column("API Price", style="blue", justify="right")
        table.add_column("Diff", justify="right")
        table.add_column("Spread", style="dim", justify="right")
        table.add_column("Age", justify="right")
        
        for comp in comparisons:
            if not comp:
                continue
                
            symbol = comp['symbol']
            local_mid = comp['differences']['mid_price']['local']
            api_mid = comp['differences']['mid_price']['api']
            diff_pct = comp['differences']['mid_price']['diff_pct']
            spread_local = comp['differences']['spread']['local']
            age = comp['data_age_seconds']
            
            # Color code difference
            if abs(diff_pct) < 0.01:
                diff_style = "green"
            elif abs(diff_pct) < 0.05:
                diff_style = "yellow"
            else:
                diff_style = "red"
            
            # Color code age
            if age < 1:
                age_style = "bright_green"
                age_str = f"{age*1000:.0f}ms"
            elif age < 5:
                age_style = "green"
                age_str = f"{age:.1f}s"
            else:
                age_style = "yellow"
                age_str = f"{age:.1f}s"
            
            table.add_row(
                symbol,
                f"${local_mid:.4f}",
                f"${api_mid:.4f}",
                f"[{diff_style}]{diff_pct:+.3f}%[/{diff_style}]",
                f"${spread_local:.4f}",
                f"[{age_style}]{age_str}[/{age_style}]"
            )
        
        return table
    
    def format_comparison_table(self, comparisons: List[Dict]) -> Table:
        """Create a formatted table of price comparisons"""
        table = Table(title="Price Comparison: Local CSV vs Binance API", box=box.ROUNDED)
        
        # Add columns
        table.add_column("Symbol", style="cyan", justify="left")
        table.add_column("Type", style="white", justify="left")
        table.add_column("Local 📁", style="green", justify="right")
        table.add_column("API 🌐", style="blue", justify="right")
        table.add_column("Diff", style="yellow", justify="right")
        table.add_column("Diff %", justify="right")
        table.add_column("Age", style="dim", justify="right")
        
        for comp in comparisons:
            if not comp:
                continue
                
            symbol = comp['symbol']
            age = comp['data_age_seconds']
            
            # Format age
            if age < 60:
                age_str = f"{age:.0f}s"
            elif age < 3600:
                age_str = f"{age/60:.1f}m"
            else:
                age_str = f"{age/3600:.1f}h"
            
            # Color code age
            if age < 5:
                age_style = "green"
            elif age < 30:
                age_style = "yellow"
            else:
                age_style = "red"
            
            # Add rows for each price type
            for price_type in ['last_price', 'bid_price', 'ask_price', 'mid_price']:
                diff_data = comp['differences'][price_type]
                
                # Color code difference percentage
                diff_pct = diff_data['diff_pct']
                if abs(diff_pct) < 0.01:
                    pct_style = "green"
                elif abs(diff_pct) < 0.05:
                    pct_style = "yellow"
                elif abs(diff_pct) < 0.1:
                    pct_style = "bright_yellow"
                else:
                    pct_style = "red"
                
                # Format price type display
                type_display = price_type.replace('_', ' ').title()
                
                table.add_row(
                    symbol if price_type == 'last_price' else "",
                    type_display,
                    f"${diff_data['local']:.4f}",
                    f"${diff_data['api']:.4f}",
                    f"${diff_data['diff']:+.4f}",
                    f"[{pct_style}]{diff_pct:+.3f}%[/{pct_style}]",
                    f"[{age_style}]{age_str}[/{age_style}]" if price_type == 'last_price' else ""
                )
            
            # Add spread row
            spread_local = comp['differences']['spread']['local']
            spread_api = comp['differences']['spread']['api']
            spread_diff = spread_api - spread_local
            
            table.add_row(
                "",
                "Spread",
                f"${spread_local:.4f}",
                f"${spread_api:.4f}",
                f"${spread_diff:+.4f}",
                "",
                "",
                style="dim"
            )
            
            # Add separator
            table.add_row("", "", "", "", "", "", "")
        
        return table
    
    def create_summary_panel(self, comparisons: List[Dict]) -> Panel:
        """Create a summary panel with statistics"""
        if not comparisons:
            return Panel("No data available", title="Summary")
        
        # Calculate statistics
        all_diffs = []
        max_diff = 0
        max_diff_symbol = ""
        
        for comp in comparisons:
            if comp:
                for price_type in ['last_price', 'mid_price']:
                    diff_pct = abs(comp['differences'][price_type]['diff_pct'])
                    all_diffs.append(diff_pct)
                    if diff_pct > max_diff:
                        max_diff = diff_pct
                        max_diff_symbol = comp['symbol']
        
        if all_diffs:
            avg_diff = sum(all_diffs) / len(all_diffs)
            
            # Determine overall status
            if avg_diff < 0.01:
                status = "[green]✅ EXCELLENT[/green] - Prices match closely"
                status_color = "green"
            elif avg_diff < 0.05:
                status = "[yellow]⚠️ GOOD[/yellow] - Minor differences"
                status_color = "yellow"
            elif avg_diff < 0.1:
                status = "[bright_yellow]⚠️ CAUTION[/bright_yellow] - Notable differences"
                status_color = "bright_yellow"
            else:
                status = "[red]❌ WARNING[/red] - Significant differences"
                status_color = "red"
            
            content = Text()
            content.append(f"Status: {status}\n\n")
            content.append(f"Symbols Monitored: {len(comparisons)}\n")
            content.append(f"Average Difference: {avg_diff:.3f}%\n")
            content.append(f"Maximum Difference: {max_diff:.3f}% ({max_diff_symbol})\n")
            
            # Add data freshness
            fresh_count = sum(1 for c in comparisons if c and c['data_age_seconds'] < 5)
            content.append(f"\nData Freshness:\n")
            content.append(f"  Fresh (<5s): {fresh_count}\n", style="green")
            content.append(f"  Recent (<30s): {sum(1 for c in comparisons if c and 5 <= c['data_age_seconds'] < 30)}\n", style="yellow")
            content.append(f"  Stale (>30s): {sum(1 for c in comparisons if c and c['data_age_seconds'] >= 30)}\n", style="red")
            
            return Panel(content, title="Summary", border_style=status_color)
        
        return Panel("No valid comparisons", title="Summary")


def monitor_prices(comparator: PriceComparator, symbols: List[str], continuous: bool = False, interval_ms: int = 2000, stream_mode: bool = False):
    """Monitor price comparisons"""
    
    console.print(Panel.fit(
        "[bold cyan]📊 Price Comparison Monitor[/bold cyan]\n" +
        "[dim]Comparing Local CSV prices with Binance API[/dim]",
        border_style="cyan"
    ))
    
    if continuous:
        interval_sec = interval_ms / 1000.0
        if interval_ms >= 1000:
            interval_str = f"{interval_sec:.1f} seconds"
        else:
            interval_str = f"{interval_ms}ms"
            
        console.print(f"[yellow]Continuous monitoring mode - updates every {interval_str}[/yellow]")
        
        if stream_mode:
            console.print("[cyan]Stream mode: Each update on new line[/cyan]")
        else:
            console.print("[cyan]Live mode: Updates in place[/cyan]")
            
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        
        if stream_mode:
            # Stream mode - print each update on a new line
            while True:
                try:
                    # Get comparisons
                    comparisons = []
                    for symbol in symbols:
                        comp = comparator.compare_prices(symbol)
                        if comp:
                            comparisons.append(comp)
                    
                    # Print compact line for each comparison
                    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    for comp in comparisons:
                        if comp:
                            symbol = comp['symbol']
                            local_mid = comp['differences']['mid_price']['local']
                            api_mid = comp['differences']['mid_price']['api']
                            diff_pct = comp['differences']['mid_price']['diff_pct']
                            age = comp['data_age_seconds']
                            
                            # Color code difference
                            if abs(diff_pct) < 0.01:
                                diff_color = "green"
                            elif abs(diff_pct) < 0.05:
                                diff_color = "yellow"
                            else:
                                diff_color = "red"
                            
                            # Format age
                            if age < 1:
                                age_str = f"{age*1000:.0f}ms"
                                age_color = "bright_green"
                            elif age < 5:
                                age_str = f"{age:.1f}s"
                                age_color = "green"
                            else:
                                age_str = f"{age:.1f}s"
                                age_color = "yellow"
                            
                            # Print line
                            console.print(
                                f"[dim]{timestamp}[/dim] | "
                                f"[cyan]{symbol:8}[/cyan] | "
                                f"[green]📁 ${local_mid:.4f}[/green] | "
                                f"[blue]🌐 ${api_mid:.4f}[/blue] | "
                                f"[{diff_color}]{diff_pct:+.3f}%[/{diff_color}] | "
                                f"[{age_color}]{age_str:>6}[/{age_color}]"
                            )
                    
                    time.sleep(interval_sec)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(interval_sec)
        else:
            # Live mode - update in place
            # Higher refresh rate for fast updates
            refresh_rate = max(10, 1000 / interval_ms)
            
            with Live(console=console, refresh_per_second=refresh_rate) as live:
                while True:
                    try:
                        # Get comparisons
                        comparisons = []
                        for symbol in symbols:
                            comp = comparator.compare_prices(symbol)
                            if comp:
                                comparisons.append(comp)
                        
                        # Create layout - use compact view for fast updates
                        if interval_ms <= 500:
                            # Ultra-fast mode - just the compact table
                            live.update(comparator.format_compact_view(comparisons))
                        elif interval_ms <= 1000:
                            # Fast mode - compact view with summary
                            layout = Layout()
                            layout.split_column(
                                Layout(comparator.create_summary_panel(comparisons), size=10),
                                Layout(comparator.format_compact_view(comparisons))
                            )
                            live.update(layout)
                        else:
                            # Normal mode - full view
                            layout = Layout()
                            layout.split_column(
                                Layout(comparator.create_summary_panel(comparisons), size=10),
                                Layout(comparator.format_comparison_table(comparisons))
                            )
                            live.update(layout)
                        time.sleep(interval_sec)
                        
                    except KeyboardInterrupt:
                        break
                    except Exception as e:
                        logger.error(f"Error in monitoring loop: {e}")
                        time.sleep(2)
    else:
        # Single run
        comparisons = []
        for symbol in symbols:
            comp = comparator.compare_prices(symbol)
            if comp:
                comparisons.append(comp)
        
        console.print(comparator.create_summary_panel(comparisons))
        console.print()
        console.print(comparator.format_comparison_table(comparisons))


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Compare local CSV prices with Binance API prices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single comparison
  python -m src.monitoring.price_compare WIFUSDT
  
  # Continuous monitoring (updates in place)
  python -m src.monitoring.price_compare WIFUSDT -c
  python -m src.monitoring.price_compare WIFUSDT -c -i 100   # 100ms updates
  
  # Stream mode (new line per update - good for logging)
  python -m src.monitoring.price_compare WIFUSDT -c -s        # 2s stream
  python -m src.monitoring.price_compare WIFUSDT -c -s -i 100 # 100ms stream
  python -m src.monitoring.price_compare WIFUSDT -c -s -i 500 # 500ms stream
  
  # Multiple symbols
  python -m src.monitoring.price_compare WIFUSDT BTCUSDT -c -s -i 100
        """
    )
    
    parser.add_argument(
        'symbols',
        nargs='*',
        help='Symbols to monitor (if none, monitors all with data)'
    )
    
    parser.add_argument(
        '--continuous',
        '-c',
        action='store_true',
        help='Continuous monitoring mode'
    )
    
    parser.add_argument(
        '--interval',
        '-i',
        type=int,
        default=2000,
        help='Update interval in milliseconds (default: 2000ms, minimum: 100ms)'
    )
    
    parser.add_argument(
        '--stream',
        '-s',
        action='store_true',
        help='Stream mode: print each update on a new line (good for logging)'
    )
    
    parser.add_argument(
        '--data-dir',
        default='data',
        help='Data directory path (default: data)'
    )
    
    args = parser.parse_args()
    
    # Validate interval
    if args.interval < 100:
        console.print("[red]Interval must be at least 100ms[/red]")
        sys.exit(1)
    
    # Create comparator
    comparator = PriceComparator(data_dir=args.data_dir)
    
    # Determine symbols to monitor
    if args.symbols:
        symbols = [s.upper() for s in args.symbols]
    else:
        symbols = comparator.get_symbols_with_data()
        if not symbols:
            console.print("[red]No symbols found with price data[/red]")
            console.print("[yellow]Run whale_monitor.py first to collect data[/yellow]")
            sys.exit(1)
    
    # Start monitoring
    try:
        monitor_prices(comparator, symbols, continuous=args.continuous, interval_ms=args.interval, stream_mode=args.stream)
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped[/yellow]")


if __name__ == "__main__":
    main()