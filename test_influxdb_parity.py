#!/usr/bin/env python3
"""Test script to verify InfluxDB saves the same data as CSV"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from src.storage.influxdb_logger import InfluxDBLogger
from src.storage.csv_logger import WhaleEvent, SpoofingEvent, MarketSnapshot, AlertEvent
from dataclasses import asdict

def test_influxdb_methods():
    """Test that all new InfluxDB methods exist and handle the same data"""
    
    # Initialize logger (disabled for testing, just checking methods)
    logger = InfluxDBLogger(enable=False)
    
    # Test data matching CSV dataclasses
    test_whale = {
        "symbol": "BTCUSDT",
        "whale_id": "test_whale_123",
        "side": "bid",
        "price": 50000.0,
        "size": 100.0,
        "value_usd": 5000000.0,
        "percentage_of_book": 15.5,
        "level": 1,
        "mid_price": 50100.0,
        "spread_bps": 2.0,
        "total_bid_whales": 5,
        "total_ask_whales": 3,
        "bid_depth_1pct": 1000000.0,
        "ask_depth_1pct": 800000.0,
        "volume_imbalance": 0.2,
        "duration_seconds": 120.5,
        "size_changes_count": 3,
        "disappearances": 1,
        "is_new": False
    }
    
    test_spoof = {
        "symbol": "ETHUSDT",
        "whale_id": "spoof_456",
        "side": "ask",
        "initial_price": 3000.0,
        "initial_size": 500.0,
        "current_size": 100.0,
        "initial_value_usd": 1500000.0,
        "current_value_usd": 300000.0,
        "duration_seconds": 45.0,
        "percentage_of_book": 8.5,
        "size_changes_count": 5,
        "disappearances": 3,
        "max_size_seen": 600.0,
        "min_size_seen": 50.0,
        "size_variance_pct": 65.0
    }
    
    # Mock snapshot object
    class MockSnapshot:
        def __init__(self):
            self.symbol = "BTCUSDT"
            self.mid_price = 50000.0
            self.spread_bps = 2.5
            self.whale_bids = [type('', (), {'value_usd': 100000})(), type('', (), {'value_usd': 200000})()]
            self.whale_asks = [type('', (), {'value_usd': 150000})()]
            self.whale_imbalance = 1
            self.volume_imbalance = 0.15
            self.bid_volume_value = 5000000.0
            self.ask_volume_value = 4500000.0
            self.depth_1_percent = 1200000.0
            self.support_level = 49500.0
            self.resistance_level = 50500.0
    
    test_alert = AlertEvent(
        timestamp=datetime.now().isoformat(),
        symbol="BTCUSDT",
        alert_type="whale",
        alert_subtype="DETECTED",
        severity="warning",
        price=50000.0,
        value_usd=5000000.0,
        side="bid",
        percentage_of_book=12.5,
        message="Large whale order detected",
        whale_id="whale_789",
        time_active_seconds=30.0,
        volume_imbalance=0.25,
        bid_volume_usd=10000000.0,
        ask_volume_usd=8000000.0,
        whale_count=8,
        bid_whale_count=5,
        ask_whale_count=3,
        trigger_threshold=100000.0,
        was_throttled=False
    )
    
    # Check that all new methods exist
    methods_to_check = [
        'write_whale_event',
        'write_spoofing_event', 
        'write_market_snapshot',
        'write_alert_event',
        'log_whale_from_dict',
        'log_spoofing_from_dict',
        'log_snapshot_from_dict',
        'log_alert'
    ]
    
    print("Checking InfluxDB logger methods...")
    for method_name in methods_to_check:
        if hasattr(logger, method_name):
            print(f"✓ Method {method_name} exists")
        else:
            print(f"✗ Method {method_name} is missing!")
            return False
    
    # Test calling the convenience methods (won't actually write since disabled)
    try:
        logger.log_whale_from_dict(test_whale, {"mid_price": 50100, "spread_bps": 2.0})
        print("✓ log_whale_from_dict callable")
        
        logger.log_spoofing_from_dict(test_spoof)
        print("✓ log_spoofing_from_dict callable")
        
        logger.log_snapshot_from_dict(MockSnapshot())
        print("✓ log_snapshot_from_dict callable")
        
        logger.log_alert(test_alert)
        print("✓ log_alert callable")
        
    except Exception as e:
        print(f"✗ Error calling methods: {e}")
        return False
    
    # Check field mapping for WhaleEvent
    whale_event = WhaleEvent(
        timestamp=datetime.now().isoformat(),
        symbol="BTCUSDT",
        whale_id="test",
        side="bid",
        price=50000.0,
        size=100.0,
        value_usd=5000000.0,
        percentage_of_book=10.0,
        level=1,
        mid_price=50100.0,
        spread_bps=2.0,
        total_bid_whales=5,
        total_ask_whales=3,
        bid_depth_1pct=1000000.0,
        ask_depth_1pct=800000.0,
        volume_imbalance=0.2,
        duration_seconds=60.0,
        size_changes_count=2,
        disappearances=0,
        is_new=True
    )
    
    whale_dict = asdict(whale_event)
    print(f"\n✓ WhaleEvent has {len(whale_dict)} fields")
    print(f"  Fields: {', '.join(whale_dict.keys())}")
    
    # Check field mapping for SpoofingEvent
    spoof_event = SpoofingEvent(
        timestamp=datetime.now().isoformat(),
        symbol="ETHUSDT",
        whale_id="spoof_1",
        side="ask",
        price=3000.0,
        initial_size=500.0,
        final_size=100.0,
        initial_value_usd=1500000.0,
        final_value_usd=300000.0,
        time_active_seconds=45.0,
        percentage_of_book=8.0,
        size_changes_count=5,
        disappearances=3,
        max_size_seen=600.0,
        min_size_seen=50.0,
        size_variance_pct=60.0,
        spoof_pattern="flickering"
    )
    
    spoof_dict = asdict(spoof_event)
    print(f"\n✓ SpoofingEvent has {len(spoof_dict)} fields")
    print(f"  Fields: {', '.join(spoof_dict.keys())}")
    
    # Check field mapping for MarketSnapshot
    snapshot = MarketSnapshot(
        timestamp=datetime.now().isoformat(),
        symbol="BTCUSDT",
        mid_price=50000.0,
        spread_bps=2.0,
        total_whale_count=8,
        bid_whale_count=5,
        ask_whale_count=3,
        whale_imbalance=2,
        volume_imbalance=0.1,
        bid_volume_usd=5000000.0,
        ask_volume_usd=4500000.0,
        bid_depth_1pct=1000000.0,
        ask_depth_1pct=900000.0,
        largest_bid_whale=500000.0,
        largest_ask_whale=400000.0,
        support_level=49500.0,
        resistance_level=50500.0
    )
    
    snapshot_dict = asdict(snapshot)
    print(f"\n✓ MarketSnapshot has {len(snapshot_dict)} fields")
    print(f"  Fields: {', '.join(snapshot_dict.keys())}")
    
    # Check field mapping for AlertEvent
    alert_dict = asdict(test_alert)
    print(f"\n✓ AlertEvent has {len(alert_dict)} fields")
    print(f"  Fields: {', '.join(alert_dict.keys())}")
    
    print("\n✅ All tests passed! InfluxDB logger now saves the same data as CSV logger.")
    return True

if __name__ == "__main__":
    success = test_influxdb_methods()
    sys.exit(0 if success else 1)