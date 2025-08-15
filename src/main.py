import asyncio
import signal
import sys
import time
from loguru import logger
from typing import Dict, Any

from src.config import config
from src.collectors.websocket_manager import BinanceWebSocketManager
from src.models.order_book import OrderBookSnapshot
from src.analyzers.order_book_analyzer import OrderBookAnalyzer
from src.storage.memory_store import MemoryStore
from src.alerts.telegram_manager import TelegramAlertManager


class WhaleAnalyticsSystem:
    def __init__(self):
        # Initialize components
        self.ws_manager = BinanceWebSocketManager(config.binance_ws_base_url)
        self.telegram_manager = TelegramAlertManager() if config.telegram_alerts_enabled else None
        self.analyzer = OrderBookAnalyzer(telegram_manager=self.telegram_manager)
        self.storage = MemoryStore()
        
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
        
        # Log thresholds for each symbol
        logger.info("Configured whale thresholds:")
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