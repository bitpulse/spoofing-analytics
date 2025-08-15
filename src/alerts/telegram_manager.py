import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import time
import threading
from queue import Queue
from telegram import Bot
from telegram.error import TelegramError
from loguru import logger
from collections import defaultdict

from src.config import config
from src.models.order_book import WhaleOrder, OrderBookSnapshot


class TelegramAlertManager:
    """Manages Telegram notifications for whale alerts"""
    
    def __init__(self):
        self.enabled = config.telegram_alerts_enabled
        self.bot = None
        self.channel_id = config.telegram_channel_id
        
        # Alert throttling - prevent spam
        self.last_alert_time: Dict[str, float] = defaultdict(float)
        self.alert_cooldown = 120  # seconds between similar alerts (increased to avoid flood)
        
        # Track active whale orders to detect changes
        self.active_whales: Dict[str, Dict] = {}
        
        # Alert statistics
        self.stats = {
            'alerts_sent': 0,
            'alerts_throttled': 0,
            'alerts_failed': 0
        }
        
        # Queue for alerts to be sent
        self.alert_queue = Queue()
        self.running = False
        self.alert_thread = None
        
        if self.enabled and config.telegram_bot_token:
            try:
                self.bot = Bot(token=config.telegram_bot_token)
                logger.info("Telegram bot initialized successfully")
                self.start_alert_thread()
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
                self.enabled = False
    
    def queue_whale_alert(self, whale: WhaleOrder, symbol: str, action: str = "DETECTED"):
        """Queue alert for whale order detection"""
        if not self.enabled or not self.bot:
            return
        
        self.alert_queue.put({
            'type': 'whale',
            'whale': whale,
            'symbol': symbol,
            'action': action
        })
    
    def queue_market_alert(self, snapshot: OrderBookSnapshot, alert_type: str):
        """Queue alert for significant market conditions"""
        if not self.enabled or not self.bot:
            return
        
        self.alert_queue.put({
            'type': 'market',
            'snapshot': snapshot,
            'alert_type': alert_type
        })
    
    def check_whale_changes(self, snapshot: OrderBookSnapshot):
        """Check for new whales or removed whales (potential spoofing)"""
        symbol = snapshot.symbol
        current_whales = {}
        current_time = time.time()
        
        # Track current whale orders with timestamps
        for whale in snapshot.whale_bids + snapshot.whale_asks:
            key = f"{whale.side}_{whale.price}_{whale.size}"
            current_whales[key] = {
                'whale': whale,
                'first_seen': current_time  # Will be updated below if already tracked
            }
        
        # Initialize if first time seeing this symbol
        if symbol not in self.active_whales:
            self.active_whales[symbol] = {}
        
        # Check for removed whales (potential spoofing)
        for key, whale_data in list(self.active_whales[symbol].items()):
            if key not in current_whales:
                # Whale order disappeared - potential spoof
                time_active = current_time - whale_data['first_seen']
                whale_obj = whale_data['whale']
                
                # Only alert for MEGA spoofs:
                # - $5M+ orders (truly significant)
                # - Lasted 5-60 seconds (not HFT, not legitimate)
                # - Represents >20% of their side of the book
                if (5 < time_active < 60 and 
                    whale_obj.value_usd >= 5000000 and 
                    whale_obj.percentage_of_book > 20):
                    self.queue_spoofing_alert(whale_obj, symbol, time_active)
        
        # Update active whales, preserving first_seen timestamps
        new_active = {}
        for key, whale_info in current_whales.items():
            if key in self.active_whales[symbol]:
                # Preserve original first_seen time
                new_active[key] = self.active_whales[symbol][key]
            else:
                # New whale, use current time
                new_active[key] = whale_info
        
        self.active_whales[symbol] = new_active
    
    def queue_spoofing_alert(self, whale: WhaleOrder, symbol: str, time_active: float):
        """Queue alert for potential spoofing activity"""
        if not self.enabled or not self.bot:
            return
        
        self.alert_queue.put({
            'type': 'spoofing',
            'whale': whale,
            'symbol': symbol,
            'time_active': time_active
        })
    
    def _format_whale_alert(self, whale: WhaleOrder, symbol: str, action: str) -> str:
        """Format whale alert message"""
        emoji = "🐋" if whale.value_usd < config.mega_whale_order_threshold else "🔥🐋"
        direction = "BUY" if whale.side == "bid" else "SELL"
        
        message = (
            f"{emoji} **WHALE {action}** {emoji}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"**{symbol}**\n"
            f"Type: **{direction} WALL**\n"
            f"Price: **${whale.price:,.2f}**\n"
            f"Size: **${whale.value_usd:,.0f}**\n"
            f"Book %: **{whale.percentage_of_book:.1f}%**\n"
            f"Level: **{whale.level}**\n"
            f"━━━━━━━━━━━━━━━━\n"
        )
        
        # Add context
        if whale.value_usd >= config.mega_whale_order_threshold:
            message += "⚡ MEGA WHALE ORDER ⚡\n"
        
        if whale.percentage_of_book > 50:
            message += "⚠️ Dominates order book!\n"
        
        if whale.side == "bid":
            message += "📈 Potential support level\n"
        else:
            message += "📉 Potential resistance level\n"
        
        return message
    
    def _format_market_alert(self, snapshot: OrderBookSnapshot, alert_type: str) -> str:
        """Format market condition alert"""
        if alert_type == "EXTREME_IMBALANCE":
            emoji = "⚖️" if snapshot.volume_imbalance > 0 else "⚖️"
            direction = "BUY" if snapshot.volume_imbalance > 0 else "SELL"
            
            return (
                f"{emoji} **EXTREME ORDER IMBALANCE** {emoji}\n"
                f"Symbol: {snapshot.symbol}\n"
                f"Imbalance: {abs(snapshot.volume_imbalance*100):.1f}% {direction} side\n"
                f"Bid Volume: ${snapshot.bid_volume_value:,.0f}\n"
                f"Ask Volume: ${snapshot.ask_volume_value:,.0f}\n"
                f"Price: ${snapshot.mid_price:,.2f}\n"
                f"⚠️ Strong {direction} pressure detected"
            )
        
        elif alert_type == "MULTIPLE_WHALES":
            total_whales = len(snapshot.whale_bids) + len(snapshot.whale_asks)
            
            return (
                f"🐋🐋 **WHALE CLUSTER DETECTED** 🐋🐋\n"
                f"Symbol: {snapshot.symbol}\n"
                f"Total Whales: {total_whales}\n"
                f"Bid Whales: {len(snapshot.whale_bids)}\n"
                f"Ask Whales: {len(snapshot.whale_asks)}\n"
                f"Price: ${snapshot.mid_price:,.2f}\n"
                f"⚠️ Unusual concentration of large orders"
            )
        
        return f"Alert: {alert_type} on {snapshot.symbol}"
    
    def _is_throttled(self, alert_key: str, cooldown: Optional[int] = None) -> bool:
        """Check if alert should be throttled"""
        cooldown = cooldown or self.alert_cooldown
        last_time = self.last_alert_time.get(alert_key, 0)
        return (time.time() - last_time) < cooldown
    
    async def _send_message(self, message: str, parse_mode: str = 'Markdown'):
        """Send message to Telegram channel"""
        if not self.bot or not self.channel_id:
            return
        
        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode=parse_mode
            )
            self.stats['alerts_sent'] += 1
            logger.debug(f"Telegram alert sent successfully")
        except TelegramError as e:
            self.stats['alerts_failed'] += 1
            logger.error(f"Failed to send Telegram alert: {e}")
        except Exception as e:
            self.stats['alerts_failed'] += 1
            logger.error(f"Unexpected error sending alert: {e}")
    
    def send_startup_message(self):
        """Send a message when the system starts"""
        if not self.enabled or not self.bot:
            return
        
        message = (
            "🚀 **Whale Analytics System Started** 🚀\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"Symbols: {', '.join(config.symbols_list)}\n"
            f"Whale Threshold: ${config.whale_order_threshold:,.0f}\n"
            f"Mega Whale: ${config.mega_whale_order_threshold:,.0f}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"Monitoring active..."
        )
        
        self.alert_queue.put({
            'type': 'message',
            'message': message
        })
    
    def send_summary(self, stats: Dict[str, Any]):
        """Send periodic summary statistics"""
        if not self.enabled or not self.bot:
            return
        
        message = (
            "📊 **System Summary** 📊\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"Uptime: {stats['uptime_seconds']/3600:.1f} hours\n"
            f"Total Snapshots: {stats['total_snapshots']:,}\n"
            f"Total Whales: {stats['total_whale_orders']:,}\n"
            f"Alerts Sent: {self.stats['alerts_sent']:,}\n"
            f"Alerts Throttled: {self.stats['alerts_throttled']:,}\n"
            f"━━━━━━━━━━━━━━━━"
        )
        
        self.alert_queue.put({
            'type': 'message',
            'message': message
        })
    
    def start_alert_thread(self):
        """Start the background thread for processing alerts"""
        if not self.enabled:
            return
        
        self.running = True
        self.alert_thread = threading.Thread(target=self._process_alert_queue, daemon=True)
        self.alert_thread.start()
        logger.info("Telegram alert thread started")
    
    def stop(self):
        """Stop the alert thread"""
        self.running = False
        if self.alert_thread:
            self.alert_thread.join(timeout=2)
    
    def _process_alert_queue(self):
        """Process alerts from the queue in a separate thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self.running:
            try:
                if not self.alert_queue.empty():
                    alert = self.alert_queue.get(timeout=0.1)
                    
                    if alert['type'] == 'whale':
                        loop.run_until_complete(
                            self._process_whale_alert(
                                alert['whale'],
                                alert['symbol'],
                                alert['action']
                            )
                        )
                    elif alert['type'] == 'market':
                        loop.run_until_complete(
                            self._process_market_alert(
                                alert['snapshot'],
                                alert['alert_type']
                            )
                        )
                    elif alert['type'] == 'spoofing':
                        loop.run_until_complete(
                            self._process_spoofing_alert(
                                alert['whale'],
                                alert['symbol'],
                                alert['time_active']
                            )
                        )
                    elif alert['type'] == 'message':
                        loop.run_until_complete(
                            self._send_message(alert['message'])
                        )
                else:
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error processing alert queue: {e}")
                time.sleep(0.5)
    
    async def _process_whale_alert(self, whale: WhaleOrder, symbol: str, action: str):
        """Process a whale alert"""
        # Create unique key for throttling
        alert_key = f"{symbol}_{whale.side}_{int(whale.price/100)*100}"  # Group by price range
        
        # Check throttling
        if self._is_throttled(alert_key):
            self.stats['alerts_throttled'] += 1
            return
        
        # Format the alert message
        message = self._format_whale_alert(whale, symbol, action)
        
        # Send the alert
        await self._send_message(message)
        
        # Update throttling
        self.last_alert_time[alert_key] = time.time()
    
    async def _process_market_alert(self, snapshot: OrderBookSnapshot, alert_type: str):
        """Process a market alert"""
        alert_key = f"{snapshot.symbol}_{alert_type}"
        
        if self._is_throttled(alert_key, cooldown=300):  # 5 min cooldown for market alerts
            self.stats['alerts_throttled'] += 1
            return
        
        message = self._format_market_alert(snapshot, alert_type)
        
        await self._send_message(message)
        self.last_alert_time[alert_key] = time.time()
    
    async def _process_spoofing_alert(self, whale: WhaleOrder, symbol: str, time_active: float):
        """Process a spoofing alert"""
        # Additional check for significance (redundant but safe)
        if whale.value_usd < 5000000:
            return
        
        # Throttle spoofing alerts more aggressively
        alert_key = f"spoofing_{symbol}_{whale.side}"
        if self._is_throttled(alert_key, cooldown=600):  # 10 minute cooldown
            self.stats['alerts_throttled'] += 1
            return
            
        message = (
            f"🚨 **MEGA SPOOFING DETECTED** 🚨\n"
            f"Symbol: {symbol}\n"
            f"Side: {'BUY' if whale.side == 'bid' else 'SELL'}\n"
            f"Price: ${whale.price:,.2f}\n"
            f"Size: ${whale.value_usd:,.0f}\n"
            f"Book %: {whale.percentage_of_book:.1f}%\n"
            f"Time Active: {time_active:.1f} seconds\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"⚠️ Massive order placed and removed\n"
            f"💡 Likely price manipulation attempt"
        )
        
        await self._send_message(message, parse_mode='Markdown')
        self.last_alert_time[alert_key] = time.time()