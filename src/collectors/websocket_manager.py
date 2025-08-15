import asyncio
import json
import time
from typing import Dict, Callable, Optional, Any
from loguru import logger
import websocket
import threading
from collections import defaultdict


class BinanceWebSocketManager:
    def __init__(self, base_url: str = "wss://fstream.binance.com"):
        self.base_url = base_url
        self.connections: Dict[str, websocket.WebSocketApp] = {}
        self.callbacks: Dict[str, Callable] = {}
        self.reconnect_attempts = defaultdict(int)
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5
        self.running = False
        self.threads: Dict[str, threading.Thread] = {}
        
    def subscribe_order_book(self, symbol: str, depth: int = 20, speed: str = "100ms", 
                            callback: Optional[Callable] = None):
        """Subscribe to order book depth stream"""
        stream_name = f"{symbol.lower()}@depth{depth}@{speed}"
        url = f"{self.base_url}/ws/{stream_name}"
        
        if callback:
            self.callbacks[stream_name] = callback
            
        self._create_connection(stream_name, url)
        logger.info(f"Subscribed to order book for {symbol} (depth={depth}, speed={speed})")
        
    def subscribe_agg_trades(self, symbol: str, callback: Optional[Callable] = None):
        """Subscribe to aggregated trades stream"""
        stream_name = f"{symbol.lower()}@aggTrade"
        url = f"{self.base_url}/ws/{stream_name}"
        
        if callback:
            self.callbacks[stream_name] = callback
            
        self._create_connection(stream_name, url)
        logger.info(f"Subscribed to aggregated trades for {symbol}")
        
    def subscribe_liquidations(self, symbol: str, callback: Optional[Callable] = None):
        """Subscribe to liquidation orders stream"""
        stream_name = f"{symbol.lower()}@forceOrder"
        url = f"{self.base_url}/ws/{stream_name}"
        
        if callback:
            self.callbacks[stream_name] = callback
            
        self._create_connection(stream_name, url)
        logger.info(f"Subscribed to liquidations for {symbol}")
        
    def subscribe_mark_price(self, symbol: str, speed: str = "1s", 
                           callback: Optional[Callable] = None):
        """Subscribe to mark price stream"""
        stream_name = f"{symbol.lower()}@markPrice@{speed}"
        url = f"{self.base_url}/ws/{stream_name}"
        
        if callback:
            self.callbacks[stream_name] = callback
            
        self._create_connection(stream_name, url)
        logger.info(f"Subscribed to mark price for {symbol} (speed={speed})")
        
    def _create_connection(self, stream_name: str, url: str):
        """Create and manage WebSocket connection"""
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                
                # Call the callback if registered
                if stream_name in self.callbacks:
                    self.callbacks[stream_name](data)
                    
                # Log high-level metrics
                if 'e' in data:
                    event_type = data['e']
                    if event_type == 'depthUpdate':
                        logger.debug(f"Order book update for {data.get('s', 'Unknown')}")
                    elif event_type == 'aggTrade':
                        logger.debug(f"Trade: {data.get('p', 0)} x {data.get('q', 0)}")
                    elif event_type == 'forceOrder':
                        logger.warning(f"LIQUIDATION detected: {json.dumps(data)}")
                        
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse message: {e}")
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                
        def on_error(ws, error):
            logger.error(f"WebSocket error for {stream_name}: {error}")
            
        def on_close(ws, close_status_code, close_msg):
            logger.warning(f"WebSocket closed for {stream_name}: {close_status_code} - {close_msg}")
            
            # Attempt reconnection
            if self.running and self.reconnect_attempts[stream_name] < self.max_reconnect_attempts:
                self.reconnect_attempts[stream_name] += 1
                logger.info(f"Attempting reconnection {self.reconnect_attempts[stream_name]}/{self.max_reconnect_attempts}")
                time.sleep(self.reconnect_delay)
                self._create_connection(stream_name, url)
            else:
                logger.error(f"Max reconnection attempts reached for {stream_name}")
                
        def on_open(ws):
            logger.info(f"WebSocket connection established for {stream_name}")
            self.reconnect_attempts[stream_name] = 0
            
        # Create WebSocket connection
        ws = websocket.WebSocketApp(
            url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        self.connections[stream_name] = ws
        
        # Run in separate thread
        thread = threading.Thread(target=ws.run_forever)
        thread.daemon = True
        self.threads[stream_name] = thread
        
    def start(self):
        """Start all WebSocket connections"""
        self.running = True
        for stream_name, thread in self.threads.items():
            thread.start()
            logger.info(f"Started thread for {stream_name}")
            
    def stop(self):
        """Stop all WebSocket connections"""
        self.running = False
        for stream_name, ws in self.connections.items():
            ws.close()
            logger.info(f"Closed connection for {stream_name}")
            
    def is_connected(self, stream_name: str) -> bool:
        """Check if a specific stream is connected"""
        return stream_name in self.connections