#!/usr/bin/env python3
"""
Simple spoofing monitor - watches CSV files and prints new rows
"""

import os
import time
import csv
from pathlib import Path
from datetime import datetime, timedelta

class SpoofMonitor:
    def __init__(self, symbol: str = None):
        # If symbol provided, watch that specific symbol
        if symbol and not symbol.startswith("data/"):
            self.data_dir = Path(f"data/spoofing/{symbol}")
            self.symbol = symbol
        else:
            # Backwards compatibility - if full path provided
            self.data_dir = Path(symbol) if symbol else Path("data/spoofing")
            self.symbol = self.data_dir.name if symbol else "ALL"
        
        self.file_positions = {}  # Track where we've read to
        
    def format_spoof_event(self, row):
        """Format a spoofing event for pretty display"""
        try:
            # Parse timestamp
            timestamp = row['timestamp']
            try:
                detected_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                detected_time = datetime.fromisoformat(timestamp)
            
            # Calculate start time
            duration = float(row['time_active_seconds'])
            start_time = detected_time - timedelta(seconds=duration)
            
            # Parse values
            side = row['side'].upper()
            price = float(row['price'])
            initial_value = float(row['initial_value_usd'])
            final_value = float(row['final_value_usd'])
            value_change_pct = ((final_value - initial_value) / initial_value) * 100
            disappearances = int(row['disappearances'])
            size_variance = float(row['size_variance_pct'])
            pattern = row['spoof_pattern']
            book_pct = float(row['percentage_of_book'])
            
            # Determine severity
            if final_value > 100000 and duration > 30:
                severity = "HIGH"
                severity_color = '\033[91m'  # Red
            elif final_value > 50000 and duration > 15:
                severity = "MED"
                severity_color = '\033[93m'  # Yellow
            else:
                severity = "LOW"
                severity_color = '\033[92m'  # Green
            
            # Colors
            RESET = '\033[0m'
            BOLD = '\033[1m'
            CYAN = '\033[96m'
            MAGENTA = '\033[95m'
            
            side_color = '\033[92m' if side == 'BID' else '\033[91m'
            
            # Format output
            output = []
            output.append(f"\n{BOLD}[SPOOF DETECTED]{RESET} {severity_color}{severity}{RESET} | {self.symbol} | Pattern: {MAGENTA}{pattern}{RESET}")
            output.append(f"├─ Time: {CYAN}{start_time.strftime('%H:%M:%S')}{RESET} → {CYAN}{detected_time.strftime('%H:%M:%S')}{RESET} ({duration:.1f}s)")
            output.append(f"├─ Side: {side_color}{side}{RESET} @ ${price:.4f}")
            output.append(f"├─ Value: ${initial_value:,.0f} → ${final_value:,.0f} ({value_change_pct:+.1f}%)")
            output.append(f"├─ Book Impact: {book_pct:.1f}% | Disappearances: {disappearances} | Variance: {size_variance:.1f}%")
            output.append(f"└─ Whale ID: {row['whale_id'].split('_')[-1][:8]}")
            
            return "\n".join(output)
            
        except Exception as e:
            # Fallback to simple format
            return f"[SPOOF] {row}"
    
    def monitor(self):
        """Monitor CSV files for new rows"""
        # Header
        print("=" * 80)
        print(f" SPOOFING MONITOR - {self.symbol} ".center(80))
        print("=" * 80)
        print(f"Watching: {self.data_dir}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 80)
        
        event_count = 0
        
        while True:
            # Find all CSV files
            csv_files = list(self.data_dir.glob("**/*.csv"))
            
            for csv_file in csv_files:
                try:
                    current_size = csv_file.stat().st_size
                    
                    # If first time seeing file, show last few events
                    if csv_file not in self.file_positions:
                        print(f"\n📁 Found file: {csv_file.name}")
                        
                        # Read and display last 3 events
                        with open(csv_file, 'r') as f:
                            reader = csv.DictReader(f)
                            rows = list(reader)
                            
                            if rows:
                                print(f"   Showing last {min(3, len(rows))} events from {len(rows)} total:\n")
                                for row in rows[-3:]:
                                    print(self.format_spoof_event(row))
                                    event_count += 1
                        
                        # Track from end
                        self.file_positions[csv_file] = current_size
                        continue
                    
                    # If file has grown, read new content
                    if current_size > self.file_positions[csv_file]:
                        with open(csv_file, 'r') as f:
                            # Go to last position
                            f.seek(self.file_positions[csv_file])
                            
                            # Read new lines
                            new_lines = f.readlines()
                            
                            # Parse as CSV
                            if new_lines:
                                # Get header from file
                                f.seek(0)
                                header = f.readline().strip().split(',')
                                
                                for line in new_lines:
                                    if line.strip():
                                        values = line.strip().split(',')
                                        if len(values) == len(header):
                                            row = dict(zip(header, values))
                                            event_count += 1
                                            print(f"\n{'🚨' * 3} NEW SPOOFING EVENT #{event_count} {'🚨' * 3}")
                                            print(self.format_spoof_event(row))
                                            print("-" * 80)
                        
                        # Update position
                        self.file_positions[csv_file] = current_size
                        
                except Exception as e:
                    # File might be writing, ignore errors
                    pass
            
            time.sleep(1)

if __name__ == "__main__":
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else None
    
    monitor = SpoofMonitor(symbol)
    try:
        monitor.monitor()
    except KeyboardInterrupt:
        print("\n\n" + "=" * 80)
        print(" MONITOR STOPPED ".center(80))
        print("=" * 80)