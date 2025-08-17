"""
🐋 Whale Monitor - Real-time Cryptocurrency Whale Activity Tracker
================================================================

This module continuously monitors Binance order books to detect and track whale orders
(large trades that can move the market). It performs the following tasks:

1. Connects to Binance WebSocket streams for real-time order book data
2. Identifies whale orders based on configurable thresholds (e.g., >$50K)
3. Tracks whale order lifecycle (appear, persist, disappear)
4. Detects market manipulation patterns (spoofing, fake walls)
5. Saves all data to CSV files for analysis
6. Sends Telegram alerts for significant whale activity

Usage:
    # Monitor default symbols from .env or SYMBOLS environment variable
    python -m src.whale_monitor
    
    # Monitor specific group (1-5, each group has 10 pre-configured pairs)
    python -m src.whale_monitor 1      # Group 1: Ultra high risk meme coins
    python -m src.whale_monitor 2      # Group 2: AI & Gaming narrative
    python -m src.whale_monitor 3      # Group 3: Low cap DeFi & L2s
    python -m src.whale_monitor 4      # Group 4: Volatile alts
    python -m src.whale_monitor 5      # Group 5: Mid-cap majors
    
    # Alternative syntax
    python -m src.whale_monitor --group 1
    python -m src.whale_monitor --group=2
    
    # Run multiple instances in parallel (different terminals)
    python -m src.whale_monitor 1 &    # Terminal 1
    python -m src.whale_monitor 2 &    # Terminal 2
    python -m src.whale_monitor 3 &    # Terminal 3
    python -m src.whale_monitor 4 &    # Terminal 4
    python -m src.whale_monitor 5 &    # Terminal 5

The system will run continuously until stopped with Ctrl+C.
All collected data is saved to the data/ directory.

Groups are optimized for detecting manipulation:
- Group 1: Meme coins with 97%+ manipulation rates
- Group 2: Narrative-driven tokens with 50-70% daily swings  
- Group 3: Thin order books perfect for spoofing
- Group 4: Regular 30-50% moves, whale hunting grounds
- Group 5: Higher liquidity but still manipulated
"""

import asyncio
import signal
import sys
import time
from loguru import logger
from typing import Dict, Any

from src.config import config
from src.collectors.websocket_manager import BinanceWebSocketManager
from src.collectors.price_collector import PriceCollector
from src.models.order_book import OrderBookSnapshot
from src.analyzers.order_book_analyzer import OrderBookAnalyzer
from src.storage.memory_store import MemoryStore
from src.storage.csv_logger import CSVLogger
from src.alerts.telegram_manager import TelegramAlertManager


class WhaleAnalyticsSystem:
    def __init__(self):
        # Initialize components
        self.ws_manager = BinanceWebSocketManager(config.binance_ws_base_url)
        
        # Create a shared CSV logger instance
        self.csv_logger = CSVLogger()
        
        # Pass CSV logger to both Telegram manager and analyzer
        self.telegram_manager = TelegramAlertManager(csv_logger=self.csv_logger) if config.telegram_alerts_enabled else None
        self.analyzer = OrderBookAnalyzer(telegram_manager=self.telegram_manager, enable_csv_logging=False)  # Disable analyzer's own CSV logger
        self.analyzer.csv_logger = self.csv_logger  # Use shared CSV logger instead
        
        self.storage = MemoryStore()
        
        # Initialize price collectors for each symbol with thread safety
        import threading
        self.price_collectors: Dict[str, PriceCollector] = {}
        self.price_collectors_lock = threading.Lock()
        
        # Track previous update IDs for gap detection
        self.previous_update_ids: Dict[str, int] = {}
        
        # Setup logging
        self._setup_logging()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = False
        
    def _setup_logging(self):
        """Configure logging"""
        logger.remove()  # Remove default handler
        
        # Console logging
        logger.add(
            sys.stdout,
            level=config.log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
        )
        
        # File logging
        logger.add(
            config.log_file,
            level=config.log_level,
            rotation="100 MB",
            retention="7 days",
            compression="zip"
        )
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        
    def process_order_book(self, data: Dict[str, Any]):
        """Process incoming order book data"""
        try:
            symbol = data.get('s', 'UNKNOWN')
            
            # Get previous update ID
            previous_update_id = self.previous_update_ids.get(symbol, 0)
            
            # Parse snapshot
            snapshot = OrderBookSnapshot.from_raw_data(data, symbol, previous_update_id)
            
            # Update previous ID
            self.previous_update_ids[symbol] = snapshot.update_id
            
            # Check for gaps
            if previous_update_id > 0 and snapshot.update_id_gap > 1:
                logger.warning(
                    f"Update gap detected for {symbol}: {snapshot.update_id_gap} "
                    f"(previous: {previous_update_id}, current: {snapshot.update_id})"
                )
                
            # Analyze snapshot
            analyzed_snapshot = self.analyzer.analyze_snapshot(snapshot)
            
            # Store in memory
            self.storage.store_snapshot(analyzed_snapshot)
            
            # Collect and save price data every second (with thread safety)
            with self.price_collectors_lock:
                if symbol not in self.price_collectors:
                    self.price_collectors[symbol] = PriceCollector(symbol)
                price_collector = self.price_collectors[symbol]
            
            # Collect price data (now synchronous)
            price_data = price_collector.collect_price_data(
                analyzed_snapshot, 
                self.analyzer.whale_tracker
            )
            
            # Save price data if it's been at least 1 second
            if price_collector.should_save():
                price_collector.save_price_data(price_data)
                logger.debug(f"Saved price data for {symbol}")
            
            # Check for whale changes (spoofing detection)
            if self.telegram_manager:
                self.telegram_manager.check_whale_changes(analyzed_snapshot)
            
            # Only log when significant whale orders detected (reduce spam)
            if (analyzed_snapshot.whale_bids and any(w.value_usd > 3000000 for w in analyzed_snapshot.whale_bids)) or \
               (analyzed_snapshot.whale_asks and any(w.value_usd > 3000000 for w in analyzed_snapshot.whale_asks)):
                logger.info(
                    f"{symbol} | Price: ${analyzed_snapshot.mid_price:,.2f} | "
                    f"Whales: {len(analyzed_snapshot.whale_bids)}B/{len(analyzed_snapshot.whale_asks)}A | "
                    f"Largest: ${max([w.value_usd for w in analyzed_snapshot.whale_bids + analyzed_snapshot.whale_asks]):,.0f}"
                )
                
        except Exception as e:
            logger.error(f"Error processing order book: {e}")
            
    def start(self):
        """Start the whale analytics system"""
        logger.info("Starting Whale Analytics System...")
        self.running = True
        
        # Log which group or symbols we're monitoring
        if len(sys.argv) > 1 and sys.argv[-1].isdigit():
            group_num = int(sys.argv[-1])
            if 1 <= group_num <= 5:
                group_descriptions = {
                    1: "Ultra High Risk - Meme Coins & New Listings",
                    2: "AI & Gaming Narrative - Heavy Speculation",
                    3: "Low Cap DeFi & L2s - Liquidity Games",
                    4: "Volatile Alts - Manipulation Favorites",
                    5: "Mid-Cap Majors & Established Alts"
                }
                logger.info(f"Monitoring Group {group_num}: {group_descriptions[group_num]}")
        
        # Log thresholds for each symbol
        logger.info(f"Monitoring {len(config.symbols_list)} trading pairs:")
        for symbol in config.symbols_list:
            thresholds = config.get_whale_thresholds(symbol)
            logger.info(f"  {symbol}: Whale=${thresholds['whale']:,.0f}, Mega=${thresholds['mega_whale']:,.0f}")
        
        # Send startup message to Telegram if enabled
        if self.telegram_manager:
            self.telegram_manager.send_startup_message()
        
        # Subscribe to order book streams for configured symbols
        for symbol in config.symbols_list:
            logger.info(f"Subscribing to {symbol} order book...")
            
            self.ws_manager.subscribe_order_book(
                symbol=symbol,
                depth=config.order_book_depth,
                speed=config.order_book_update_speed,
                callback=self.process_order_book
            )
            
        # Start WebSocket connections
        self.ws_manager.start()
        
        logger.info("System started successfully!")
        
        # Main loop for periodic tasks
        loop_count = 0
        while self.running:
            try:
                time.sleep(10)  # Main loop interval
                loop_count += 1
                
                # Periodic tasks
                if loop_count % 6 == 0:  # Every minute
                    self._print_stats()
                    
                    # Send summary to Telegram
                    if self.telegram_manager and loop_count % 180 == 0:  # Every 30 minutes
                        stats = self.storage.get_stats()
                        self.telegram_manager.send_summary(stats)
                    
                if loop_count % 30 == 0:  # Every 5 minutes
                    # Check for spoofing
                    spoofed_orders = self.analyzer.detect_spoofing()
                    if spoofed_orders:
                        logger.warning(f"Detected {len(spoofed_orders)} potential spoofing attempts")
                        
                if loop_count % 360 == 0:  # Every hour
                    self.storage.cleanup_old_data(hours=24)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                
    def _print_stats(self):
        """Print system statistics"""
        stats = self.storage.get_stats()
        market_pressure = self.analyzer.get_market_pressure()
        
        logger.info(
            f"System Stats | Snapshots: {stats['total_snapshots']} | "
            f"Whale Orders: {stats['total_whale_orders']} | "
            f"Rate: {stats['snapshots_per_second']:.1f}/s | "
            f"Market: {market_pressure}"
        )
        
        # Print per-symbol stats
        for symbol, snapshot in self.storage.latest_snapshots.items():
            recent_whales = len([
                w for w in self.storage.get_recent_whale_orders(60)
                if symbol in str(w)
            ])
            
            logger.info(
                f"{symbol} | Price: ${snapshot.mid_price:,.2f} | "
                f"Spread: {snapshot.spread_bps:.2f}bps | "
                f"Recent Whales (1m): {recent_whales}"
            )
            
    def stop(self):
        """Stop the system gracefully"""
        logger.info("Stopping Whale Analytics System...")
        self.running = False
        
        # Stop WebSocket connections
        self.ws_manager.stop()
        
        # Stop Telegram manager
        if self.telegram_manager:
            self.telegram_manager.stop()
        
        # Final stats
        self._print_stats()
        
        logger.info("System stopped successfully")
        

def main():
    """Main entry point"""
    # Parse command line arguments for group selection
    import argparse
    parser = argparse.ArgumentParser(
        description="Whale Analytics System - Monitor crypto whale activity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.whale_monitor          # Use symbols from .env
  python -m src.whale_monitor 1        # Monitor group 1 (meme coins)
  python -m src.whale_monitor --group 2  # Monitor group 2 (AI/Gaming)
  
Groups (10 pairs each):
  1: Ultra high risk meme coins (PEPE, BONK, WIF, etc.)
  2: AI & Gaming tokens (WLD, FET, SAND, AXS, etc.)
  3: Low cap DeFi & L2s (SPELL, ANKR, ARB, OP, etc.)
  4: Volatile alts (SEI, INJ, APT, SUI, etc.)
  5: Mid-cap majors (SOL, ADA, DOGE, AVAX, etc.)
        """
    )
    
    # Support both positional and named argument for group
    parser.add_argument(
        'group_num',
        nargs='?',
        type=int,
        choices=[1, 2, 3, 4, 5],
        help='Monitoring group number (1-5)'
    )
    parser.add_argument(
        '--group',
        type=int,
        choices=[1, 2, 3, 4, 5],
        help='Monitoring group number (1-5)'
    )
    
    args = parser.parse_args()
    
    # Determine which group to use (positional takes precedence)
    group_to_use = args.group_num or args.group
    
    if group_to_use:
        logger.info(f"Starting Whale Analytics System for Group {group_to_use}")
        # The config will automatically detect the group from sys.argv
    
    system = WhaleAnalyticsSystem()
    
    try:
        system.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        system.stop()
        

if __name__ == "__main__":
    main()