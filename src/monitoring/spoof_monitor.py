#!/usr/bin/env python3
"""
Simple Spoofing Event Monitor
Watches CSV files for new spoofing events and prints to console
"""

import os
import csv
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Set
import sys

class SpoofMonitor:
    def __init__(self, data_dir: str = "data/spoofing"):
        self.data_dir = Path(data_dir)
        self.seen_events: Set[str] = set()  # Track already seen events
        self.file_positions: Dict[Path, int] = {}  # Track file read positions
        
    def get_event_id(self, row: Dict) -> str:
        """Create unique ID for event"""
        return f"{row['timestamp']}_{row['whale_id']}"
    
    def format_event(self, row: Dict) -> str:
        """Format spoofing event for console output"""
        timestamp = row['timestamp'].split('T')[1].split('.')[0]  # Extract time
        symbol = row['symbol']
        side = row['side'].upper()
        value = float(row['final_value_usd'])
        duration = float(row['time_active_seconds'])
        disappearances = int(row['disappearances'])
        pattern = row['spoof_pattern']
        
        # Color codes for console
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        RESET = '\033[0m'
        BOLD = '\033[1m'
        
        side_color = GREEN if side == 'BID' else RED
        
        return (
            f"{BOLD}[SPOOF DETECTED]{RESET} "
            f"{BLUE}{timestamp}{RESET} | "
            f"{YELLOW}{symbol}{RESET} | "
            f"{side_color}{side}{RESET} | "
            f"${value:,.0f} | "
            f"{duration:.1f}s | "
            f"{disappearances} flickers | "
            f"{pattern}"
        )
    
    def scan_files(self):
        """Scan all CSV files for new events"""
        if not self.data_dir.exists():
            return
            
        # Find all CSV files
        csv_files = list(self.data_dir.glob("**/*.csv"))
        
        for csv_file in csv_files:
            # Skip if file doesn't exist anymore
            if not csv_file.exists():
                continue
                
            # Get file size to check if it changed
            current_size = csv_file.stat().st_size
            
            # Initialize position if first time seeing file
            if csv_file not in self.file_positions:
                self.file_positions[csv_file] = 0
            
            # Only read if file has grown
            if current_size > self.file_positions[csv_file]:
                self.read_new_events(csv_file)
                self.file_positions[csv_file] = current_size
    
    def read_new_events(self, csv_file: Path):
        """Read new events from CSV file"""
        try:
            with open(csv_file, 'r') as f:
                # Skip to last position
                f.seek(self.file_positions.get(csv_file, 0))
                
                # Read remaining content
                remaining = f.read()
                if not remaining.strip():
                    return
                
                # Parse CSV from remaining content
                lines = remaining.strip().split('\n')
                
                # Check if we need headers (first read)
                if self.file_positions[csv_file] == 0 and lines:
                    # First line is header
                    header = lines[0].split(',')
                    data_lines = lines[1:]
                else:
                    # Read header from beginning of file for field names
                    f.seek(0)
                    header = f.readline().strip().split(',')
                    data_lines = lines
                
                # Process each new row
                for line in data_lines:
                    if not line.strip():
                        continue
                        
                    values = line.split(',')
                    if len(values) != len(header):
                        continue
                        
                    row = dict(zip(header, values))
                    event_id = self.get_event_id(row)
                    
                    # Only print if not seen before
                    if event_id not in self.seen_events:
                        self.seen_events.add(event_id)
                        print(self.format_event(row))
                        
        except Exception as e:
            # Silently handle errors (file might be writing)
            pass
    
    def monitor(self, interval: float = 1.0):
        """Main monitoring loop"""
        print(f"Starting Spoofing Monitor - Watching {self.data_dir}")
        print("Press Ctrl+C to stop")
        print("-" * 80)
        
        try:
            while True:
                self.scan_files()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nMonitor stopped")

def main():
    # Check if custom path provided
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data/spoofing"
    
    monitor = SpoofMonitor(data_dir)
    monitor.monitor()

if __name__ == "__main__":
    main()