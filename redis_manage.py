#!/usr/bin/env python3
"""
Redis Data Management Script
Utilities for managing spoofing data in Redis
"""

import argparse
from datetime import datetime, timedelta
from src.storage.redis_storage import RedisSpoofStorage
from loguru import logger
import sys


def show_stats(storage: RedisSpoofStorage, symbol: str = None):
    """Show statistics for stored spoofing data"""
    
    # Get all symbols if not specified
    symbols = []
    if symbol:
        symbols = [symbol]
    else:
        for key in storage.redis_client.scan_iter("spoofs:timeline:*"):
            sym = key.split(':')[-1]
            symbols.append(sym)
    
    if not symbols:
        logger.info("No spoofing data found in Redis")
        return
    
    logger.info("=" * 60)
    logger.info("REDIS SPOOFING DATA STATISTICS")
    logger.info("=" * 60)
    
    total_spoofs = 0
    for sym in sorted(symbols):
        count = storage.redis_client.zcard(f"spoofs:timeline:{sym}")
        total_spoofs += count
        
        # Get time range
        spoofs = storage.redis_client.zrange(
            f"spoofs:timeline:{sym}", 0, 0, withscores=True
        )
        oldest = datetime.fromtimestamp(spoofs[0][1]) if spoofs else None
        
        spoofs = storage.redis_client.zrange(
            f"spoofs:timeline:{sym}", -1, -1, withscores=True
        )
        newest = datetime.fromtimestamp(spoofs[0][1]) if spoofs else None
        
        logger.info(f"\n{sym}:")
        logger.info(f"  Total spoofs: {count}")
        if oldest and newest:
            logger.info(f"  Time range: {oldest.strftime('%Y-%m-%d %H:%M')} to {newest.strftime('%Y-%m-%d %H:%M')}")
        
        # Get pattern distribution
        patterns = {}
        for pattern in ['single', 'flickering', 'size_manipulation']:
            pattern_count = storage.redis_client.scard(f"spoofs:pattern:{pattern}:{sym}")
            if pattern_count > 0:
                patterns[pattern] = pattern_count
        
        if patterns:
            logger.info(f"  Patterns: {patterns}")
        
        # Get top spoof by severity
        top_spoofs = storage.get_top_spoofs(sym, limit=1, by='severity')
        if top_spoofs:
            top = top_spoofs[0]
            logger.info(f"  Top spoof: ${top.get('initial_value_usd', 0):,.0f} "
                       f"({top.get('spoof_pattern', 'unknown')} pattern, "
                       f"severity: {top.get('severity_score', 0):.0f})")
    
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Total spoofs across all symbols: {total_spoofs}")
    
    # Memory usage
    info = storage.get_connection_info()
    logger.info(f"Redis memory usage: {info['used_memory']}")
    logger.info(f"Total keys in database: {info['total_keys']}")


def cleanup_old_data(storage: RedisSpoofStorage, days: int):
    """Clean up data older than specified days"""
    
    logger.info(f"Cleaning up data older than {days} days...")
    storage.cleanup_old_data(days)
    logger.success("Cleanup completed")


def export_data(storage: RedisSpoofStorage, symbol: str, hours: int, output_file: str):
    """Export spoofing data to CSV"""
    
    logger.info(f"Exporting {symbol} data from last {hours} hours to {output_file}...")
    
    end_time = datetime.now().timestamp()
    start_time = end_time - (hours * 3600)
    
    storage.export_to_csv(symbol, output_file, start_time, end_time)
    logger.success(f"Data exported to {output_file}")


def clear_symbol(storage: RedisSpoofStorage, symbol: str):
    """Clear all data for a specific symbol"""
    
    logger.warning(f"This will delete ALL spoofing data for {symbol}")
    confirm = input("Are you sure? (yes/no): ")
    
    if confirm.lower() != 'yes':
        logger.info("Cancelled")
        return
    
    # Delete all keys for this symbol
    patterns = [
        f"spoof:*{symbol}*",
        f"spoofs:timeline:{symbol}",
        f"spoofs:pattern:*:{symbol}",
        f"spoofs:date:*:{symbol}",
        f"spoofs:severity:{symbol}",
        f"spoofs:size:{symbol}",
        f"spoofs:stats:{symbol}:*"
    ]
    
    deleted = 0
    for pattern in patterns:
        for key in storage.redis_client.scan_iter(pattern):
            storage.redis_client.delete(key)
            deleted += 1
    
    logger.success(f"Deleted {deleted} keys for {symbol}")


def main():
    parser = argparse.ArgumentParser(description="Manage Redis spoofing data")
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    stats_parser.add_argument('--symbol', help='Specific symbol (optional)')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old data')
    cleanup_parser.add_argument('--days', type=int, default=30, 
                                help='Delete data older than N days (default: 30)')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export data to CSV')
    export_parser.add_argument('symbol', help='Symbol to export')
    export_parser.add_argument('--hours', type=int, default=24,
                              help='Export last N hours (default: 24)')
    export_parser.add_argument('--output', default='spoofing_export.csv',
                              help='Output file (default: spoofing_export.csv)')
    
    # Clear command
    clear_parser = subparsers.add_parser('clear', help='Clear data for a symbol')
    clear_parser.add_argument('symbol', help='Symbol to clear')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize storage
    storage = RedisSpoofStorage()
    
    # Execute command
    if args.command == 'stats':
        show_stats(storage, args.symbol)
    elif args.command == 'cleanup':
        cleanup_old_data(storage, args.days)
    elif args.command == 'export':
        export_data(storage, args.symbol, args.hours, args.output)
    elif args.command == 'clear':
        clear_symbol(storage, args.symbol)


if __name__ == "__main__":
    main()