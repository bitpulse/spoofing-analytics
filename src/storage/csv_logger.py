"""
CSV data logger for whale analytics system
Saves whale orders to CSV files
"""
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict
from dataclasses import dataclass, asdict
import threading
from queue import Queue
from loguru import logger


@dataclass
class WhaleEvent:
    """Whale order event data"""
    timestamp: str
    symbol: str
    whale_id: str
    side: str
    price: float
    size: float
    value_usd: float
    percentage_of_book: float
    level: int
    mid_price: float
    spread_bps: float
    
    # Context
    total_bid_whales: int = 0
    total_ask_whales: int = 0
    bid_depth_1pct: float = 0
    ask_depth_1pct: float = 0
    volume_imbalance: float = 0
    
    # Tracking
    duration_seconds: float = 0
    size_changes_count: int = 0
    disappearances: int = 0
    is_new: bool = True


class CSVLogger:
    """Manages CSV logging with hourly rotation for whales data"""
    
    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.ensure_directories()
        
        # File handles cache
        self.file_handles = {}
        self.csv_writers = {}
        
        # Async write queue
        self.write_queue = Queue()
        self.running = True
        
        # Start writer thread
        self.writer_thread = threading.Thread(target=self._process_write_queue, daemon=True)
        self.writer_thread.start()
        
        logger.info(f"CSV Logger initialized, saving to {self.base_dir}")
        
    def ensure_directories(self):
        """Create necessary directories"""
        dirs = [
            self.base_dir,
            self.base_dir / "whales",
            self.base_dir / "prices",  # Already handled by PriceCollector
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            
    def get_filename(self, data_type: str, symbol: str = None) -> Path:
        """Generate filename with hourly rotation - organized by symbol"""
        now = datetime.now()
        date_hour = now.strftime("%Y-%m-%d_%H")  # Format: 2025-08-17_18
        
        if data_type == "whales" and symbol:
            # Create per-symbol subdirectory
            symbol_dir = self.base_dir / "whales" / symbol
            symbol_dir.mkdir(parents=True, exist_ok=True)
            return symbol_dir / f"{symbol}_whales_{date_hour}.csv"
        else:
            # Fallback for any other type
            return self.base_dir / f"{data_type}_{date_hour}.csv"
            
    def log_whale(self, event: WhaleEvent):
        """Log a whale order event"""
        self.write_queue.put(("whale", event))
        
    def log_whale_from_dict(self, whale_data: Dict, snapshot_data: Dict = None):
        """Convenience method to log whale from dictionary"""
        event = WhaleEvent(
            timestamp=datetime.now().isoformat(),
            symbol=whale_data.get('symbol', 'UNKNOWN'),
            whale_id=whale_data.get('whale_id', ''),
            side=whale_data.get('side', ''),
            price=whale_data.get('price', 0),
            size=whale_data.get('size', 0),
            value_usd=whale_data.get('value_usd', 0),
            percentage_of_book=whale_data.get('percentage_of_book', 0),
            level=whale_data.get('level', 0),
            mid_price=snapshot_data.get('mid_price', 0) if snapshot_data else 0,
            spread_bps=snapshot_data.get('spread_bps', 0) if snapshot_data else 0,
            total_bid_whales=snapshot_data.get('total_bid_whales', 0) if snapshot_data else 0,
            total_ask_whales=snapshot_data.get('total_ask_whales', 0) if snapshot_data else 0,
            volume_imbalance=snapshot_data.get('volume_imbalance', 0) if snapshot_data else 0,
            duration_seconds=whale_data.get('duration_seconds', 0),
            size_changes_count=whale_data.get('size_changes_count', 0),
            disappearances=whale_data.get('disappearances', 0),
            is_new=whale_data.get('is_new', True)
        )
        self.log_whale(event)
        
    def _process_write_queue(self):
        """Process write queue in background thread"""
        while self.running:
            try:
                if not self.write_queue.empty():
                    data_type, event = self.write_queue.get(timeout=0.1)
                    
                    if data_type == "whale":
                        self._write_whale(event)
                        
            except Exception as e:
                logger.error(f"Error processing write queue: {e}")
                
    def _write_whale(self, event: WhaleEvent):
        """Write whale event to CSV - per symbol file"""
        filename = self.get_filename("whales", event.symbol)
        self._write_csv_row(filename, asdict(event), WhaleEvent)
        
    def _write_csv_row(self, filename: Path, row_dict: Dict, dataclass_type):
        """Write a row to CSV file"""
        
        # Check if file exists
        file_exists = filename.exists()
        
        # Open file and get writer
        if filename not in self.csv_writers:
            mode = 'a' if file_exists else 'w'
            file_handle = open(filename, mode, newline='')
            self.file_handles[filename] = file_handle
            
            # Get field names from dataclass
            fieldnames = list(row_dict.keys())
            writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
            
            # Write header if new file
            if not file_exists:
                writer.writeheader()
                
            self.csv_writers[filename] = writer
            
        # Write row
        self.csv_writers[filename].writerow(row_dict)
        self.file_handles[filename].flush()  # Ensure data is written
            
    def get_today_stats(self) -> Dict:
        """Get statistics for today's logging - per symbol"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        stats = {
            'total': {
                'whales_logged': 0,
                'total_size_mb': 0
            },
            'per_symbol': {}
        }
        
        # Get stats for whales
        type_dir = self.base_dir / "whales"
        if type_dir.exists():
            for symbol_dir in type_dir.iterdir():
                if symbol_dir.is_dir():
                    symbol = symbol_dir.name
                    if symbol not in stats['per_symbol']:
                        stats['per_symbol'][symbol] = {
                            'whales': 0,
                            'size_mb': 0
                        }
                    
                    # Count rows in symbol's files
                    for csv_file in symbol_dir.glob(f"*_{today}*.csv"):
                        if csv_file.exists():
                            with open(csv_file, 'r') as f:
                                row_count = sum(1 for line in f) - 1  # Minus header
                                
                            file_size_mb = csv_file.stat().st_size / (1024 * 1024)
                            
                            stats['per_symbol'][symbol]['whales'] = row_count
                            stats['total']['whales_logged'] += row_count
                            stats['per_symbol'][symbol]['size_mb'] += file_size_mb
                            stats['total']['total_size_mb'] += file_size_mb
                
        return stats
        
    def stop(self):
        """Stop the logger and close all files"""
        self.running = False
        
        # Wait for queue to empty
        self.write_queue.join()
        
        # Close all file handles
        for handle in self.file_handles.values():
            handle.close()
            
        logger.info("CSV Logger stopped")