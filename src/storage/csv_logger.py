"""
CSV data logger for whale analytics system
Saves whale orders, spoofing events, and market snapshots to CSV files
"""
import csv
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import gzip
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
    

@dataclass
class SpoofingEvent:
    """Spoofing detection event"""
    timestamp: str
    symbol: str
    whale_id: str
    side: str
    price: float
    initial_size: float
    final_size: float
    initial_value_usd: float
    final_value_usd: float
    time_active_seconds: float
    percentage_of_book: float
    size_changes_count: int
    disappearances: int
    max_size_seen: float
    min_size_seen: float
    size_variance_pct: float
    spoof_pattern: str  # single/flickering/size_manipulation
    

@dataclass
class MarketSnapshot:
    """Periodic market snapshot"""
    timestamp: str
    symbol: str
    mid_price: float
    spread_bps: float
    total_whale_count: int
    bid_whale_count: int
    ask_whale_count: int
    whale_imbalance: int
    volume_imbalance: float
    bid_volume_usd: float
    ask_volume_usd: float
    bid_depth_1pct: float
    ask_depth_1pct: float
    largest_bid_whale: float
    largest_ask_whale: float
    support_level: Optional[float]
    resistance_level: Optional[float]
    

@dataclass
class AlertEvent:
    """Alert event data for Telegram notifications"""
    timestamp: str
    symbol: str
    alert_type: str  # whale, market, spoofing, message
    alert_subtype: str  # DETECTED, EXTREME_IMBALANCE, MULTIPLE_WHALES, etc.
    severity: str  # info, warning, critical
    price: float
    value_usd: float
    side: str  # bid, ask, both, n/a
    percentage_of_book: float
    message: str  # The formatted alert message
    
    # Additional context
    whale_id: Optional[str] = None
    time_active_seconds: Optional[float] = None
    volume_imbalance: Optional[float] = None
    bid_volume_usd: Optional[float] = None
    ask_volume_usd: Optional[float] = None
    whale_count: Optional[int] = None
    bid_whale_count: Optional[int] = None
    ask_whale_count: Optional[int] = None
    trigger_threshold: Optional[float] = None
    was_throttled: bool = False
    

class CSVLogger:
    """Manages CSV logging with daily rotation and compression"""
    
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
            self.base_dir / "spoofing",
            self.base_dir / "snapshots",
            self.base_dir / "alerts",
            self.base_dir / "archive"
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            
    def get_filename(self, data_type: str, symbol: str = None) -> Path:
        """Generate filename with hourly rotation - organized by symbol"""
        # Use hourly rotation for better data management
        now = datetime.now()
        date_hour = now.strftime("%Y-%m-%d_%H")  # Format: 2025-08-17_18
        
        if data_type == "whales" and symbol:
            # Create per-symbol subdirectory
            symbol_dir = self.base_dir / "whales" / symbol
            symbol_dir.mkdir(parents=True, exist_ok=True)
            return symbol_dir / f"{symbol}_whales_{date_hour}.csv"
        elif data_type == "spoofing" and symbol:
            # Create per-symbol subdirectory
            symbol_dir = self.base_dir / "spoofing" / symbol
            symbol_dir.mkdir(parents=True, exist_ok=True)
            return symbol_dir / f"{symbol}_spoofing_{date_hour}.csv"
        elif data_type == "snapshots" and symbol:
            # Create per-symbol subdirectory
            symbol_dir = self.base_dir / "snapshots" / symbol
            symbol_dir.mkdir(parents=True, exist_ok=True)
            return symbol_dir / f"{symbol}_snapshots_{date_hour}.csv"
        elif data_type == "alerts" and symbol:
            # Create per-symbol subdirectory for alerts
            symbol_dir = self.base_dir / "alerts" / symbol
            symbol_dir.mkdir(parents=True, exist_ok=True)
            return symbol_dir / f"{symbol}_alerts_{date_hour}.csv"
        else:
            # Fallback for any other type
            return self.base_dir / f"{data_type}_{date_hour}.csv"
            
    def log_whale(self, event: WhaleEvent):
        """Log a whale order event"""
        self.write_queue.put(("whale", event))
        
    def log_spoofing(self, event: SpoofingEvent):
        """Log a spoofing event"""
        self.write_queue.put(("spoofing", event))
        
    def log_snapshot(self, snapshot: MarketSnapshot):
        """Log a market snapshot"""
        self.write_queue.put(("snapshot", snapshot))
        
    def log_alert(self, event: AlertEvent):
        """Log an alert event"""
        self.write_queue.put(("alert", event))
        
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
        
    def log_spoofing_from_dict(self, spoof_data: Dict):
        """Convenience method to log spoofing from dictionary"""
        
        # Determine spoof pattern
        if spoof_data.get('disappearances', 0) >= 3:
            pattern = 'flickering'
        elif spoof_data.get('size_variance_pct', 0) > 50:
            pattern = 'size_manipulation'
        else:
            pattern = 'single'
            
        event = SpoofingEvent(
            timestamp=datetime.now().isoformat(),
            symbol=spoof_data.get('symbol', 'UNKNOWN'),
            whale_id=spoof_data.get('whale_id', ''),
            side=spoof_data.get('side', ''),
            price=spoof_data.get('initial_price', 0),
            initial_size=spoof_data.get('initial_size', 0),
            final_size=spoof_data.get('current_size', 0),
            initial_value_usd=spoof_data.get('initial_value_usd', 0),
            final_value_usd=spoof_data.get('current_value_usd', 0),
            time_active_seconds=spoof_data.get('duration_seconds', 0),
            percentage_of_book=spoof_data.get('percentage_of_book', 0),
            size_changes_count=spoof_data.get('size_changes_count', 0),
            disappearances=spoof_data.get('disappearances', 0),
            max_size_seen=spoof_data.get('max_size_seen', 0),
            min_size_seen=spoof_data.get('min_size_seen', 0),
            size_variance_pct=spoof_data.get('size_variance_pct', 0),
            spoof_pattern=pattern
        )
        self.log_spoofing(event)
        
    def log_snapshot_from_dict(self, snapshot: Any):
        """Log market snapshot from OrderBookSnapshot object"""
        event = MarketSnapshot(
            timestamp=datetime.now().isoformat(),
            symbol=snapshot.symbol,
            mid_price=snapshot.mid_price,
            spread_bps=snapshot.spread_bps,
            total_whale_count=len(snapshot.whale_bids) + len(snapshot.whale_asks),
            bid_whale_count=len(snapshot.whale_bids),
            ask_whale_count=len(snapshot.whale_asks),
            whale_imbalance=snapshot.whale_imbalance,
            volume_imbalance=snapshot.volume_imbalance,
            bid_volume_usd=snapshot.bid_volume_value,
            ask_volume_usd=snapshot.ask_volume_value,
            bid_depth_1pct=snapshot.depth_1_percent if hasattr(snapshot, 'depth_1_percent') else 0,
            ask_depth_1pct=0,  # Could calculate separately
            largest_bid_whale=max([w.value_usd for w in snapshot.whale_bids], default=0),
            largest_ask_whale=max([w.value_usd for w in snapshot.whale_asks], default=0),
            support_level=snapshot.support_level,
            resistance_level=snapshot.resistance_level
        )
        self.log_snapshot(event)
        
    def _process_write_queue(self):
        """Process write queue in background thread"""
        while self.running:
            try:
                if not self.write_queue.empty():
                    data_type, event = self.write_queue.get(timeout=0.1)
                    
                    if data_type == "whale":
                        self._write_whale(event)
                    elif data_type == "spoofing":
                        self._write_spoofing(event)
                    elif data_type == "snapshot":
                        self._write_snapshot(event)
                    elif data_type == "alert":
                        self._write_alert(event)
                        
            except Exception as e:
                logger.error(f"Error processing write queue: {e}")
                
    def _write_whale(self, event: WhaleEvent):
        """Write whale event to CSV - per symbol file"""
        filename = self.get_filename("whales", event.symbol)
        self._write_csv_row(filename, asdict(event), WhaleEvent)
        
    def _write_spoofing(self, event: SpoofingEvent):
        """Write spoofing event to CSV - per symbol file"""
        filename = self.get_filename("spoofing", event.symbol)
        self._write_csv_row(filename, asdict(event), SpoofingEvent)
        
    def _write_snapshot(self, event: MarketSnapshot):
        """Write market snapshot to CSV - per symbol file"""
        filename = self.get_filename("snapshots", event.symbol)
        self._write_csv_row(filename, asdict(event), MarketSnapshot)
        
    def _write_alert(self, event: AlertEvent):
        """Write alert event to CSV - per symbol file"""
        filename = self.get_filename("alerts", event.symbol)
        self._write_csv_row(filename, asdict(event), AlertEvent)
        
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
        
    def rotate_files(self):
        """Rotate daily files and compress old ones"""
        yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Close all file handles
        for handle in self.file_handles.values():
            handle.close()
        self.file_handles.clear()
        self.csv_writers.clear()
        
        # Compress yesterday's files
        for subdir in ["whales", "spoofing", "snapshots", "alerts"]:
            dir_path = self.base_dir / subdir
            for csv_file in dir_path.glob(f"*_{yesterday}.csv"):
                self._compress_file(csv_file)
                
    def _compress_file(self, filepath: Path):
        """Compress a CSV file with gzip"""
        compressed_path = self.base_dir / "archive" / f"{filepath.name}.gz"
        
        try:
            with open(filepath, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    f_out.writelines(f_in)
                    
            # Remove original file after compression
            filepath.unlink()
            logger.info(f"Compressed and archived {filepath.name}")
            
        except Exception as e:
            logger.error(f"Failed to compress {filepath}: {e}")
            
    def get_today_stats(self) -> Dict:
        """Get statistics for today's logging - per symbol"""
        today = date.today().strftime("%Y-%m-%d")
        
        stats = {
            'total': {
                'whales_logged': 0,
                'spoofs_logged': 0,
                'snapshots_logged': 0,
                'alerts_logged': 0,
                'total_size_mb': 0
            },
            'per_symbol': {}
        }
        
        # Get stats for each symbol
        for data_type in ["whales", "spoofing", "snapshots", "alerts"]:
            type_dir = self.base_dir / data_type
            if type_dir.exists():
                for symbol_dir in type_dir.iterdir():
                    if symbol_dir.is_dir():
                        symbol = symbol_dir.name
                        if symbol not in stats['per_symbol']:
                            stats['per_symbol'][symbol] = {
                                'whales': 0,
                                'spoofs': 0,
                                'snapshots': 0,
                                'alerts': 0,
                                'size_mb': 0
                            }
                        
                        # Count rows in symbol's files
                        for csv_file in symbol_dir.glob(f"*_{today}.csv"):
                            if csv_file.exists():
                                with open(csv_file, 'r') as f:
                                    row_count = sum(1 for line in f) - 1  # Minus header
                                    
                                file_size_mb = csv_file.stat().st_size / (1024 * 1024)
                                
                                if 'whales' in csv_file.name:
                                    stats['per_symbol'][symbol]['whales'] = row_count
                                    stats['total']['whales_logged'] += row_count
                                elif 'spoofing' in csv_file.name:
                                    stats['per_symbol'][symbol]['spoofs'] = row_count
                                    stats['total']['spoofs_logged'] += row_count
                                elif 'snapshots' in csv_file.name:
                                    stats['per_symbol'][symbol]['snapshots'] = row_count
                                    stats['total']['snapshots_logged'] += row_count
                                elif 'alerts' in csv_file.name:
                                    stats['per_symbol'][symbol]['alerts'] = row_count
                                    stats['total']['alerts_logged'] += row_count
                                    
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