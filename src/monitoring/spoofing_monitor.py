#!/usr/bin/env python3
"""
Real-time Spoofing Detection Monitor
====================================
Watches for new spoofing events and displays them as they're detected.

Usage:
    python -m src.spoofing_monitor              # Monitor all symbols
    python -m src.spoofing_monitor BTCUSDT      # Monitor specific symbol
    python -m src.spoofing_monitor --stats      # Show statistics
"""

import os
import sys
import time
import csv
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional
from collections import defaultdict
import argparse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich import box
import requests
import json

console = Console()


class PriceTracker:
    """Tracks current prices for symbols"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.prices: Dict[str, float] = {}
        self.last_update: Dict[str, datetime] = {}
        self.price_source: Dict[str, str] = {}  # Track source of price
        
    def get_both_prices(self, symbol: str) -> tuple[Optional[float], Optional[float]]:
        """Get prices from both local CSV and Binance API for comparison
        Returns: (local_price, api_price)
        """
        # Get from both sources
        local_price = self._get_price_from_csv(symbol)
        api_price = self._get_price_from_api(symbol)
        
        return local_price, api_price
        
    def _get_price_from_csv(self, symbol: str) -> Optional[float]:
        """Get most recent price from CSV files (only if very recent)"""
        try:
            prices_dir = self.data_dir / "prices" / symbol
            if not prices_dir.exists():
                return None
                
            # Find most recent CSV file
            csv_files = list(prices_dir.glob("*.csv"))
            if not csv_files:
                return None
                
            latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
            
            # Check if file is recent (within last 30 seconds)
            file_age = time.time() - latest_file.stat().st_mtime
            if file_age > 30:  # More than 30 seconds old
                return None
            
            # Read last line of CSV
            with open(latest_file, 'r') as f:
                lines = f.readlines()
                if len(lines) > 1:  # Skip header
                    last_line = lines[-1].strip()
                    if last_line:
                        parts = last_line.split(',')
                        # CSV columns: timestamp,symbol,last_price,mark_price,index_price,bid_price,ask_price,mid_price...
                        if len(parts) > 7:
                            # Use mid_price directly (column 7, index 7)
                            mid_price = float(parts[7])
                            return mid_price
                        elif len(parts) > 6:
                            # Fallback: calculate from bid and ask
                            bid_price = float(parts[5])  # bid_price column
                            ask_price = float(parts[6])  # ask_price column
                            return (bid_price + ask_price) / 2
        except Exception as e:
            logger.debug(f"Could not get price from CSV for {symbol}: {e}")
        return None
        
    def _get_price_from_api(self, symbol: str) -> Optional[float]:
        """Get current price from Binance API"""
        try:
            # Check cache first
            if symbol in self.prices:
                last_update = self.last_update.get(symbol)
                if last_update and (datetime.now() - last_update).seconds < 10:
                    return self.prices[symbol]
            
            # Fetch from API
            url = f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}"
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                data = response.json()
                price = float(data['price'])
                self.prices[symbol] = price
                self.last_update[symbol] = datetime.now()
                return price
        except Exception as e:
            logger.debug(f"Could not get price from API for {symbol}: {e}")
        return None


class SpoofingEventHandler(FileSystemEventHandler):
    """Handles file system events for spoofing CSV files"""
    
    def __init__(self, symbol_filter: str = None, show_stats: bool = False, price_tracker: PriceTracker = None):
        self.symbol_filter = symbol_filter
        self.show_stats = show_stats
        self.price_tracker = price_tracker
        self.processed_events: Set[str] = set()
        self.stats = defaultdict(lambda: {"count": 0, "total_value": 0})
        self.last_events: List[Dict] = []
        self.max_events = 20  # Keep last 20 events for display
        
    def on_modified(self, event):
        """Called when a CSV file is modified"""
        if event.is_directory or not event.src_path.endswith('.csv'):
            return
            
        # Extract symbol from path
        path_parts = Path(event.src_path).parts
        if 'spoofing' not in path_parts:
            return
            
        try:
            symbol_idx = path_parts.index('spoofing') + 1
            if symbol_idx < len(path_parts):
                symbol = path_parts[symbol_idx]
                
                # Apply symbol filter if specified
                if self.symbol_filter and symbol != self.symbol_filter:
                    return
                    
                self.process_new_spoofing_events(event.src_path, symbol)
        except (ValueError, IndexError):
            pass
            
    def process_new_spoofing_events(self, filepath: str, symbol: str):
        """Process new spoofing events from CSV file"""
        try:
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                events = list(reader)
                
            # Process only new events
            for event in events:
                event_id = f"{event['timestamp']}_{event['symbol']}_{event.get('whale_id', event.get('order_id', ''))}"
                
                if event_id not in self.processed_events:
                    self.processed_events.add(event_id)
                    self.display_spoofing_event(event, is_historical=False)  # Real-time event
                    self.update_stats(event)
                    
                    # Keep for display
                    self.last_events.append(event)
                    if len(self.last_events) > self.max_events:
                        self.last_events.pop(0)
                        
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
    
    def process_historical_spoofing_events(self, filepath: str, symbol: str):
        """Process historical spoofing events from CSV file (for initial scan)"""
        try:
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                events = list(reader)
                
            # Process only new events
            for event in events:
                event_id = f"{event['timestamp']}_{event['symbol']}_{event.get('whale_id', event.get('order_id', ''))}"
                
                if event_id not in self.processed_events:
                    self.processed_events.add(event_id)
                    self.display_spoofing_event(event, is_historical=True)  # Historical event
                    self.update_stats(event)
                    
                    # Keep for display
                    self.last_events.append(event)
                    if len(self.last_events) > self.max_events:
                        self.last_events.pop(0)
                        
        except Exception as e:
            logger.error(f"Error processing historical {filepath}: {e}")
            
    def display_spoofing_event(self, event: Dict, is_historical: bool = False):
        """Display a single spoofing event with rich context"""
        timestamp = event['timestamp'].split('T')[1].split('.')[0]  # Get time only
        symbol = event['symbol']
        side = event['side']
        spoof_price = float(event['price'])
        
        # Extract all available fields for context
        initial_value = float(event.get('initial_value_usd', event.get('value_usd', 0)))
        final_value = float(event.get('final_value_usd', initial_value))
        duration = float(event.get('time_active_seconds', event.get('duration_seconds', 0)))
        pattern = event.get('spoof_pattern', 'unknown')
        
        # Additional context fields
        size_changes = int(event.get('size_changes_count', 0))
        disappearances = int(event.get('disappearances', 0))
        book_percentage = float(event.get('percentage_of_book', 0))
        size_variance = float(event.get('size_variance_pct', 0))
        
        # Get market price - for historical events, don't show market price
        # For real-time events, get fresh price
        local_price = None
        if not is_historical and self.price_tracker:
            local_price = self.price_tracker._get_price_from_csv(symbol)
        
        # Color code based on side
        side_color = "red" if side == "ask" else "green"
        side_emoji = "🔴" if side == "ask" else "🟢"
        
        # Format values
        def format_value(val):
            if val >= 1000000:
                return f"${val/1000000:.2f}M"
            elif val >= 1000:
                return f"${val/1000:.0f}K"
            else:
                return f"${val:.0f}"
        
        initial_str = format_value(initial_value)
        final_str = format_value(final_value) if final_value != initial_value else ""
        
        # Build message
        message = Text()
        message.append(f"[{timestamp}] ", style="dim")
        message.append(f"{side_emoji} ", style=f"bold {side_color}")
        
        # Symbol and current price
        message.append(f"{symbol} ", style="bold cyan")
        
        # Show local price and distance
        if local_price:
            price_diff = ((spoof_price - local_price) / local_price) * 100
            diff_color = "bright_red" if abs(price_diff) > 1 else "yellow" if abs(price_diff) > 0.5 else "green"
            message.append(f"[Mkt: ${local_price:.4f}] ", style="white")
            message.append(f"Spoof @ ${spoof_price:.4f} ", style="bold yellow")
            message.append(f"({price_diff:+.2f}%) ", style=diff_color)
        else:
            # For historical events or when no current price available
            message.append(f"Spoof @ ${spoof_price:.4f} ", style="bold yellow")
            if is_historical:
                message.append("[HIST] ", style="dim")
        
        # Size and changes
        message.append("| ", style="dim")
        if final_value != initial_value:
            message.append(f"{initial_str}→{final_str} ", style="bold white")
        else:
            message.append(f"{initial_str} ", style="bold white")
        
        # Book dominance if significant
        if book_percentage > 10:
            message.append(f"({book_percentage:.1f}% book) ", style="bright_yellow")
        
        # Duration with color coding
        duration_color = "red" if duration < 10 else "yellow" if duration < 30 else "green"
        message.append(f"| {duration:.1f}s ", style=duration_color)
        
        # Pattern and manipulation indicators
        if disappearances > 0:
            message.append(f"| Flicker×{disappearances} ", style="bright_red")
        if size_changes > 5:
            message.append(f"| Changes×{size_changes} ", style="orange")
        if size_variance > 50:
            message.append(f"| Var:{size_variance:.0f}% ", style="red")
        
        message.append(f"| {pattern}", style="dim")
        
        console.print(message)
        
    def update_stats(self, event: Dict):
        """Update statistics for the symbol"""
        symbol = event['symbol']
        value_usd = float(event.get('initial_value_usd', event.get('value_usd', 0)))
        
        self.stats[symbol]['count'] += 1
        self.stats[symbol]['total_value'] += value_usd
        
    def get_stats_table(self) -> Table:
        """Generate statistics table"""
        table = Table(title="Spoofing Statistics", box=box.ROUNDED)
        table.add_column("Symbol", style="cyan", justify="left")
        table.add_column("Count", style="yellow", justify="right")
        table.add_column("Total Value", style="green", justify="right")
        table.add_column("Avg Size", style="magenta", justify="right")
        
        for symbol, stats in sorted(self.stats.items()):
            count = stats['count']
            total = stats['total_value']
            avg = total / count if count > 0 else 0
            
            # Format values
            if total >= 1000000:
                total_str = f"${total/1000000:.2f}M"
            else:
                total_str = f"${total/1000:.0f}K"
                
            if avg >= 1000000:
                avg_str = f"${avg/1000000:.2f}M"
            else:
                avg_str = f"${avg/1000:.0f}K"
                
            table.add_row(symbol, str(count), total_str, avg_str)
            
        return table


class SpoofingMonitor:
    """Main spoofing monitor class"""
    
    def __init__(self, data_dir: str = "data", symbol: str = None, show_stats: bool = False):
        self.data_dir = Path(data_dir)
        self.spoofing_dir = self.data_dir / "spoofing"
        self.symbol = symbol
        self.show_stats = show_stats
        
        # Verify directory exists
        if not self.spoofing_dir.exists():
            console.print(f"[red]Spoofing directory not found: {self.spoofing_dir}[/red]")
            console.print("[yellow]Run whale_monitor.py first to collect data[/yellow]")
            sys.exit(1)
            
    def scan_existing_events(self, handler: SpoofingEventHandler):
        """Scan existing files for recent events"""
        console.print("[dim]Scanning existing spoofing events from last hour (historical - no market price)...[/dim]")
        
        # Look for events from last hour
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        # Scan all symbol directories
        if self.symbol:
            symbol_dirs = [self.spoofing_dir / self.symbol]
        else:
            symbol_dirs = [d for d in self.spoofing_dir.iterdir() if d.is_dir()]
            
        for symbol_dir in symbol_dirs:
            if not symbol_dir.exists():
                continue
                
            # Find CSV files from current hour
            for csv_file in symbol_dir.glob("*.csv"):
                # Check if file is recent
                if csv_file.stat().st_mtime > cutoff_time.timestamp():
                    symbol = symbol_dir.name
                    handler.process_historical_spoofing_events(str(csv_file), symbol)
                    
    def run(self):
        """Start monitoring for spoofing events"""
        # Print header
        console.print(Panel.fit(
            "[bold cyan]🔍 Real-time Spoofing Detection Monitor[/bold cyan]\n" +
            f"[dim]Watching: {self.spoofing_dir}[/dim]\n\n" +
            "[dim]Context: Market price from local data | Size changes | Flickering | Book dominance[/dim]",
            border_style="cyan"
        ))
        
        if self.symbol:
            console.print(f"[yellow]Filtering for symbol: {self.symbol}[/yellow]")
            
        # Create price tracker
        price_tracker = PriceTracker(self.data_dir)
            
        # Create event handler
        handler = SpoofingEventHandler(
            symbol_filter=self.symbol,
            show_stats=self.show_stats,
            price_tracker=price_tracker
        )
        
        # Scan existing recent events
        self.scan_existing_events(handler)
        
        # Set up file system observer
        observer = Observer()
        observer.schedule(handler, str(self.spoofing_dir), recursive=True)
        observer.start()
        
        console.print("[green]✓ Monitoring started. Press Ctrl+C to stop.[/green]")
        
        # Print legend
        console.print("\n[dim]Legend:[/dim]")
        console.print("[dim]  • Duration colors: [red]<10s[/red] [yellow]10-30s[/yellow] [green]>30s[/green] (longer = more real)[/dim]")
        console.print("[dim]  • Price distance: [green]<0.5%[/green] [yellow]0.5-1%[/yellow] [bright_red]>1%[/bright_red] from market[/dim]")
        console.print("[dim]  • Flicker×N = Disappeared N times | Changes×N = Size changed N times[/dim]")
        console.print("[dim]  • Book % = Order dominated X% of order book[/dim]\n")
        
        try:
            while True:
                time.sleep(1)
                
                # Periodically show stats if requested
                if self.show_stats and handler.stats:
                    console.print("\n")
                    console.print(handler.get_stats_table())
                    console.print("\n")
                    time.sleep(9)  # Show stats every 10 seconds
                    
        except KeyboardInterrupt:
            observer.stop()
            console.print("\n[yellow]Monitoring stopped.[/yellow]")
            
            # Show final stats
            if handler.stats:
                console.print("\n")
                console.print(handler.get_stats_table())
                
        observer.join()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Monitor spoofing detection in real-time",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.spoofing_monitor              # Monitor all symbols
  python -m src.spoofing_monitor BTCUSDT      # Monitor specific symbol
  python -m src.spoofing_monitor --stats      # Show statistics
  python -m src.spoofing_monitor WIFUSDT --stats  # Both symbol filter and stats
        """
    )
    
    parser.add_argument(
        'symbol',
        nargs='?',
        help='Optional symbol to filter (e.g., BTCUSDT)'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show statistics periodically'
    )
    
    parser.add_argument(
        '--data-dir',
        default='data',
        help='Data directory path (default: data)'
    )
    
    args = parser.parse_args()
    
    # Convert symbol to uppercase if provided
    symbol = args.symbol.upper() if args.symbol else None
    
    # Create and run monitor
    monitor = SpoofingMonitor(
        data_dir=args.data_dir,
        symbol=symbol,
        show_stats=args.stats
    )
    
    monitor.run()


if __name__ == "__main__":
    main()