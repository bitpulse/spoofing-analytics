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
from typing import Dict, List, Set
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

console = Console()


class SpoofingEventHandler(FileSystemEventHandler):
    """Handles file system events for spoofing CSV files"""
    
    def __init__(self, symbol_filter: str = None, show_stats: bool = False):
        self.symbol_filter = symbol_filter
        self.show_stats = show_stats
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
                    self.display_spoofing_event(event)
                    self.update_stats(event)
                    
                    # Keep for display
                    self.last_events.append(event)
                    if len(self.last_events) > self.max_events:
                        self.last_events.pop(0)
                        
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
            
    def display_spoofing_event(self, event: Dict):
        """Display a single spoofing event"""
        timestamp = event['timestamp'].split('T')[1].split('.')[0]  # Get time only
        symbol = event['symbol']
        side = event['side']
        price = float(event['price'])
        
        # Handle different field names for value and duration
        value_usd = float(event.get('initial_value_usd', event.get('value_usd', 0)))
        duration = float(event.get('time_active_seconds', event.get('duration_seconds', 0)))
        pattern = event.get('spoof_pattern', 'unknown')
        
        # Color code based on side
        side_color = "red" if side == "ask" else "green"
        side_emoji = "🔴" if side == "ask" else "🟢"
        
        # Format value
        if value_usd >= 1000000:
            value_str = f"${value_usd/1000000:.2f}M"
        elif value_usd >= 1000:
            value_str = f"${value_usd/1000:.0f}K"
        else:
            value_str = f"${value_usd:.0f}"
            
        # Build message
        message = Text()
        message.append(f"[{timestamp}] ", style="dim")
        message.append(f"{side_emoji} SPOOF DETECTED ", style=f"bold {side_color}")
        message.append(f"{symbol} ", style="bold cyan")
        message.append(f"@ ${price:.4f} ", style="yellow")
        message.append(f"| {value_str} ", style="bold white")
        message.append(f"| {duration:.1f}s ", style="magenta")
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
        console.print("[dim]Scanning existing spoofing events...[/dim]")
        
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
                    handler.process_new_spoofing_events(str(csv_file), symbol)
                    
    def run(self):
        """Start monitoring for spoofing events"""
        # Print header
        console.print(Panel.fit(
            "[bold cyan]🔍 Real-time Spoofing Detection Monitor[/bold cyan]\n" +
            f"[dim]Watching: {self.spoofing_dir}[/dim]",
            border_style="cyan"
        ))
        
        if self.symbol:
            console.print(f"[yellow]Filtering for symbol: {self.symbol}[/yellow]")
            
        # Create event handler
        handler = SpoofingEventHandler(
            symbol_filter=self.symbol,
            show_stats=self.show_stats
        )
        
        # Scan existing recent events
        self.scan_existing_events(handler)
        
        # Set up file system observer
        observer = Observer()
        observer.schedule(handler, str(self.spoofing_dir), recursive=True)
        observer.start()
        
        console.print("[green]✓ Monitoring started. Press Ctrl+C to stop.[/green]\n")
        
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