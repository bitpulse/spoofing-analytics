"""
Redis Storage Manager for Spoofing Data
Provides high-performance storage and querying for web server access
"""

import redis
import json
import time
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from loguru import logger
import hashlib


@dataclass
class SpoofingData:
    """Spoofing event data structure"""
    timestamp: str
    symbol: str
    whale_id: str
    side: str  # bid/ask
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
    level: int = 0  # Order book depth level
    mid_price: float = 0  # Market price when detected
    spread_bps: float = 0  # Bid-ask spread
    volume_imbalance: float = 0  # Buy vs sell pressure
    severity_score: float = 0  # Calculated severity metric


class RedisSpoofStorage:
    """Redis-based storage for spoofing data with efficient querying"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 6379, db: int = 0,
                 ttl_days: int = 30, pool_size: int = 10):
        """
        Initialize Redis storage manager
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            ttl_days: Data retention period in days
            pool_size: Connection pool size
        """
        self.ttl_seconds = ttl_days * 86400
        
        # Create connection pool for better performance
        # Note: socket_keepalive_options can cause issues on some systems
        self.pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            max_connections=pool_size,
            decode_responses=True,
            socket_keepalive=True,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )
        self.redis_client = redis.Redis(connection_pool=self.pool)
        
        # Test connection
        try:
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {host}:{port}, DB={db}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
            
    def save_spoof(self, spoof_data: Dict[str, Any]) -> bool:
        """
        Save spoofing event to Redis with multiple indexes
        
        Args:
            spoof_data: Dictionary containing spoof data
            
        Returns:
            True if saved successfully
        """
        try:
            symbol = spoof_data.get('symbol', 'UNKNOWN')
            whale_id = spoof_data.get('whale_id', '')
            timestamp = spoof_data.get('timestamp', datetime.now().isoformat())
            
            # Generate unique spoof ID
            spoof_id = f"{symbol}:{whale_id}:{timestamp}"
            spoof_key = f"spoof:{spoof_id}"
            
            # Calculate severity score for ranking
            severity_score = self._calculate_severity(spoof_data)
            spoof_data['severity_score'] = severity_score
            
            # Use pipeline for atomic multi-command execution
            pipe = self.redis_client.pipeline()
            
            # 1. Store spoof data as hash
            pipe.hset(spoof_key, mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in spoof_data.items()
            })
            pipe.expire(spoof_key, self.ttl_seconds)
            
            # 2. Add to timeline (sorted by timestamp)
            timestamp_score = datetime.fromisoformat(timestamp).timestamp()
            pipe.zadd(f"spoofs:timeline:{symbol}", {spoof_id: timestamp_score})
            pipe.expire(f"spoofs:timeline:{symbol}", self.ttl_seconds)
            
            # 3. Add to pattern index
            pattern = spoof_data.get('spoof_pattern', 'unknown')
            pipe.sadd(f"spoofs:pattern:{pattern}:{symbol}", spoof_id)
            pipe.expire(f"spoofs:pattern:{pattern}:{symbol}", self.ttl_seconds)
            
            # 4. Add to daily index
            date_str = timestamp.split('T')[0]
            pipe.sadd(f"spoofs:date:{date_str}:{symbol}", spoof_id)
            pipe.expire(f"spoofs:date:{date_str}:{symbol}", self.ttl_seconds)
            
            # 5. Add to severity ranking
            pipe.zadd(f"spoofs:severity:{symbol}", {spoof_id: severity_score})
            pipe.expire(f"spoofs:severity:{symbol}", self.ttl_seconds)
            
            # 6. Add to size ranking
            value_usd = spoof_data.get('initial_value_usd', 0)
            pipe.zadd(f"spoofs:size:{symbol}", {spoof_id: value_usd})
            pipe.expire(f"spoofs:size:{symbol}", self.ttl_seconds)
            
            # 7. Update hourly statistics
            hour_str = timestamp[:13]  # YYYY-MM-DDTHH
            stats_key = f"spoofs:stats:{symbol}:{hour_str}"
            pipe.hincrby(stats_key, "count", 1)
            pipe.hincrbyfloat(stats_key, "total_value", value_usd)
            pipe.hincrby(stats_key, f"pattern:{pattern}", 1)
            pipe.expire(stats_key, self.ttl_seconds)
            
            # 8. Publish for real-time subscribers
            pipe.publish(f"spoofs:live:{symbol}", json.dumps({
                'spoof_id': spoof_id,
                'timestamp': timestamp,
                'pattern': pattern,
                'value_usd': value_usd,
                'severity': severity_score
            }))
            
            # Execute all commands atomically
            pipe.execute()
            
            logger.debug(f"Saved spoof to Redis: {spoof_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save spoof to Redis: {e}")
            return False
            
    def get_recent_spoofs(self, symbol: str, minutes: int = 5,
                         limit: int = 100) -> List[Dict]:
        """
        Get recent spoofing events within specified time window
        
        Args:
            symbol: Trading symbol
            minutes: Time window in minutes
            limit: Maximum number of results
            
        Returns:
            List of spoof data dictionaries
        """
        try:
            # Calculate time range
            end_time = time.time()
            start_time = end_time - (minutes * 60)
            
            # Get spoof IDs from timeline
            spoof_ids = self.redis_client.zrangebyscore(
                f"spoofs:timeline:{symbol}",
                start_time,
                end_time,
                start=0,
                num=limit
            )
            
            # Fetch spoof data
            spoofs = []
            for spoof_id in spoof_ids:
                spoof_data = self._get_spoof_by_id(spoof_id)
                if spoof_data:
                    spoofs.append(spoof_data)
                    
            return spoofs
            
        except Exception as e:
            logger.error(f"Failed to get recent spoofs: {e}")
            return []
            
    def get_spoofs_by_pattern(self, symbol: str, pattern: str,
                             limit: int = 100) -> List[Dict]:
        """
        Get spoofing events by pattern type
        
        Args:
            symbol: Trading symbol
            pattern: Spoof pattern (single/flickering/size_manipulation)
            limit: Maximum number of results
            
        Returns:
            List of spoof data dictionaries
        """
        try:
            # Get spoof IDs from pattern index
            spoof_ids = self.redis_client.srandmember(
                f"spoofs:pattern:{pattern}:{symbol}",
                limit
            )
            
            # Fetch spoof data
            spoofs = []
            for spoof_id in spoof_ids or []:
                spoof_data = self._get_spoof_by_id(spoof_id)
                if spoof_data:
                    spoofs.append(spoof_data)
                    
            # Sort by timestamp (newest first)
            spoofs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return spoofs[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get spoofs by pattern: {e}")
            return []
            
    def get_top_spoofs(self, symbol: str, limit: int = 10,
                      by: str = "severity") -> List[Dict]:
        """
        Get top spoofing events by severity or size
        
        Args:
            symbol: Trading symbol
            limit: Number of top spoofs to return
            by: Ranking criteria ('severity' or 'size')
            
        Returns:
            List of spoof data dictionaries
        """
        try:
            # Select appropriate ranking key
            if by == "size":
                ranking_key = f"spoofs:size:{symbol}"
            else:
                ranking_key = f"spoofs:severity:{symbol}"
                
            # Get top spoof IDs
            spoof_ids = self.redis_client.zrevrange(
                ranking_key,
                0,
                limit - 1,
                withscores=False
            )
            
            # Fetch spoof data
            spoofs = []
            for spoof_id in spoof_ids:
                spoof_data = self._get_spoof_by_id(spoof_id)
                if spoof_data:
                    spoofs.append(spoof_data)
                    
            return spoofs
            
        except Exception as e:
            logger.error(f"Failed to get top spoofs: {e}")
            return []
            
    def get_spoof_stats(self, symbol: str, hours: int = 24) -> Dict:
        """
        Get aggregated spoofing statistics
        
        Args:
            symbol: Trading symbol
            hours: Time period in hours
            
        Returns:
            Dictionary with statistics
        """
        try:
            stats = {
                'symbol': symbol,
                'period_hours': hours,
                'total_spoofs': 0,
                'total_value_usd': 0,
                'patterns': {},
                'hourly_distribution': [],
                'top_spoofs': []
            }
            
            # Get hourly stats for the period
            now = datetime.now()
            for i in range(hours):
                hour_time = now - timedelta(hours=i)
                hour_str = hour_time.strftime("%Y-%m-%dT%H")
                stats_key = f"spoofs:stats:{symbol}:{hour_str}"
                
                hour_stats = self.redis_client.hgetall(stats_key)
                if hour_stats:
                    count = int(hour_stats.get('count', 0))
                    value = float(hour_stats.get('total_value', 0))
                    
                    stats['total_spoofs'] += count
                    stats['total_value_usd'] += value
                    
                    # Pattern distribution
                    for key, val in hour_stats.items():
                        if key.startswith('pattern:'):
                            pattern = key.replace('pattern:', '')
                            stats['patterns'][pattern] = \
                                stats['patterns'].get(pattern, 0) + int(val)
                                
                    # Hourly distribution
                    stats['hourly_distribution'].append({
                        'hour': hour_str,
                        'count': count,
                        'value_usd': value
                    })
                    
            # Get top spoofs for the period
            stats['top_spoofs'] = self.get_top_spoofs(symbol, limit=5)
            
            # Calculate averages
            if stats['total_spoofs'] > 0:
                stats['avg_value_usd'] = stats['total_value_usd'] / stats['total_spoofs']
                stats['spoofs_per_hour'] = stats['total_spoofs'] / hours
            else:
                stats['avg_value_usd'] = 0
                stats['spoofs_per_hour'] = 0
                
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get spoof stats: {e}")
            return {}
            
    def search_spoofs(self, symbol: str, filters: Dict,
                     limit: int = 100) -> List[Dict]:
        """
        Search spoofs with multiple filter criteria
        
        Args:
            symbol: Trading symbol
            filters: Dictionary of filter criteria
                - min_value: Minimum USD value
                - max_value: Maximum USD value
                - min_duration: Minimum active seconds
                - max_duration: Maximum active seconds
                - pattern: Specific pattern
                - side: bid/ask
                - start_time: Start timestamp
                - end_time: End timestamp
            limit: Maximum results
            
        Returns:
            List of matching spoof data
        """
        try:
            # Start with all spoofs in time range
            start_time = filters.get('start_time', time.time() - 86400)
            end_time = filters.get('end_time', time.time())
            
            spoof_ids = self.redis_client.zrangebyscore(
                f"spoofs:timeline:{symbol}",
                start_time,
                end_time
            )
            
            # Apply filters
            results = []
            for spoof_id in spoof_ids:
                spoof_data = self._get_spoof_by_id(spoof_id)
                if not spoof_data:
                    continue
                    
                # Check value filters
                if 'min_value' in filters:
                    if spoof_data.get('initial_value_usd', 0) < filters['min_value']:
                        continue
                if 'max_value' in filters:
                    if spoof_data.get('initial_value_usd', 0) > filters['max_value']:
                        continue
                        
                # Check duration filters
                if 'min_duration' in filters:
                    if spoof_data.get('time_active_seconds', 0) < filters['min_duration']:
                        continue
                if 'max_duration' in filters:
                    if spoof_data.get('time_active_seconds', 0) > filters['max_duration']:
                        continue
                        
                # Check pattern filter
                if 'pattern' in filters:
                    if spoof_data.get('spoof_pattern') != filters['pattern']:
                        continue
                        
                # Check side filter
                if 'side' in filters:
                    if spoof_data.get('side') != filters['side']:
                        continue
                        
                results.append(spoof_data)
                
                if len(results) >= limit:
                    break
                    
            return results
            
        except Exception as e:
            logger.error(f"Failed to search spoofs: {e}")
            return []
            
    def subscribe_to_live_spoofs(self, symbol: str, callback):
        """
        Subscribe to real-time spoof notifications
        
        Args:
            symbol: Trading symbol to monitor
            callback: Function to call with spoof data
        """
        try:
            pubsub = self.redis_client.pubsub()
            pubsub.subscribe(f"spoofs:live:{symbol}")
            
            logger.info(f"Subscribed to live spoofs for {symbol}")
            
            for message in pubsub.listen():
                if message['type'] == 'message':
                    spoof_data = json.loads(message['data'])
                    callback(spoof_data)
                    
        except Exception as e:
            logger.error(f"Error in live spoof subscription: {e}")
            
    def export_to_csv(self, symbol: str, output_file: str,
                     start_time: float = None, end_time: float = None):
        """
        Export spoofs to CSV file for analysis
        
        Args:
            symbol: Trading symbol
            output_file: Output CSV file path
            start_time: Start timestamp (optional)
            end_time: End timestamp (optional)
        """
        import csv
        
        try:
            # Get spoofs in time range
            if not start_time:
                start_time = time.time() - 86400  # Last 24 hours
            if not end_time:
                end_time = time.time()
                
            spoof_ids = self.redis_client.zrangebyscore(
                f"spoofs:timeline:{symbol}",
                start_time,
                end_time
            )
            
            if not spoof_ids:
                logger.warning(f"No spoofs found for {symbol} in specified time range")
                return
                
            # Get first spoof to determine fields
            first_spoof = self._get_spoof_by_id(spoof_ids[0])
            if not first_spoof:
                return
                
            # Write to CSV
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=first_spoof.keys())
                writer.writeheader()
                
                for spoof_id in spoof_ids:
                    spoof_data = self._get_spoof_by_id(spoof_id)
                    if spoof_data:
                        writer.writerow(spoof_data)
                        
            logger.info(f"Exported {len(spoof_ids)} spoofs to {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to export spoofs to CSV: {e}")
            
    def cleanup_old_data(self, days: int = 30):
        """
        Clean up data older than specified days
        
        Args:
            days: Age threshold in days
        """
        try:
            cutoff_time = time.time() - (days * 86400)
            
            # Get all symbols
            symbols = set()
            for key in self.redis_client.scan_iter("spoofs:timeline:*"):
                symbol = key.split(':')[-1]
                symbols.add(symbol)
                
            # Clean up old data for each symbol
            for symbol in symbols:
                # Remove old entries from timeline
                removed = self.redis_client.zremrangebyscore(
                    f"spoofs:timeline:{symbol}",
                    0,
                    cutoff_time
                )
                
                if removed > 0:
                    logger.info(f"Cleaned up {removed} old spoofs for {symbol}")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            
    def _get_spoof_by_id(self, spoof_id: str) -> Optional[Dict]:
        """
        Retrieve spoof data by ID
        
        Args:
            spoof_id: Unique spoof identifier
            
        Returns:
            Spoof data dictionary or None
        """
        try:
            spoof_key = f"spoof:{spoof_id}"
            spoof_data = self.redis_client.hgetall(spoof_key)
            
            if not spoof_data:
                return None
                
            # Convert string values back to appropriate types
            for key, value in spoof_data.items():
                try:
                    # Try to parse as JSON first (for nested structures)
                    spoof_data[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # Try to convert to float if it looks numeric
                    try:
                        if '.' in value or 'e' in value.lower():
                            spoof_data[key] = float(value)
                        elif value.isdigit() or (value[0] == '-' and value[1:].isdigit()):
                            spoof_data[key] = int(value)
                    except (ValueError, AttributeError):
                        # Keep as string
                        pass
                        
            return spoof_data
            
        except Exception as e:
            logger.error(f"Failed to get spoof by ID {spoof_id}: {e}")
            return None
            
    def _calculate_severity(self, spoof_data: Dict) -> float:
        """
        Calculate severity score for ranking spoofs
        
        Args:
            spoof_data: Spoof data dictionary
            
        Returns:
            Severity score (0-100)
        """
        score = 0
        
        # Value component (0-40 points)
        value_usd = spoof_data.get('initial_value_usd', 0)
        if value_usd > 1000000:
            score += 40
        elif value_usd > 500000:
            score += 30
        elif value_usd > 100000:
            score += 20
        elif value_usd > 50000:
            score += 10
            
        # Pattern component (0-20 points)
        pattern = spoof_data.get('spoof_pattern', '')
        if pattern == 'flickering':
            score += 20
        elif pattern == 'size_manipulation':
            score += 15
        elif pattern == 'single':
            score += 10
            
        # Frequency component (0-20 points)
        disappearances = spoof_data.get('disappearances', 0)
        if disappearances > 10:
            score += 20
        elif disappearances > 5:
            score += 15
        elif disappearances > 2:
            score += 10
        elif disappearances > 0:
            score += 5
            
        # Market impact component (0-20 points)
        percentage_of_book = spoof_data.get('percentage_of_book', 0)
        if percentage_of_book > 20:
            score += 20
        elif percentage_of_book > 10:
            score += 15
        elif percentage_of_book > 5:
            score += 10
        elif percentage_of_book > 2:
            score += 5
            
        return min(score, 100)  # Cap at 100
        
    def get_connection_info(self) -> Dict:
        """Get Redis connection information and stats"""
        try:
            info = self.redis_client.info()
            return {
                'connected': True,
                'version': info.get('redis_version'),
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'total_keys': self.redis_client.dbsize()
            }
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }


# Example usage and testing
if __name__ == "__main__":
    # Initialize storage
    storage = RedisSpoofStorage()
    
    # Test data
    test_spoof = {
        'timestamp': datetime.now().isoformat(),
        'symbol': 'BTCUSDT',
        'whale_id': 'BTCUSDT_ask_65000_123456',
        'side': 'ask',
        'price': 65000.0,
        'initial_size': 100.0,
        'final_size': 0,
        'initial_value_usd': 6500000.0,
        'final_value_usd': 0,
        'time_active_seconds': 45.2,
        'percentage_of_book': 15.5,
        'size_changes_count': 3,
        'disappearances': 2,
        'max_size_seen': 120.0,
        'min_size_seen': 80.0,
        'size_variance_pct': 50.0,
        'spoof_pattern': 'flickering'
    }
    
    # Save spoof
    storage.save_spoof(test_spoof)
    
    # Query recent spoofs
    recent = storage.get_recent_spoofs('BTCUSDT', minutes=5)
    print(f"Recent spoofs: {len(recent)}")
    
    # Get stats
    stats = storage.get_spoof_stats('BTCUSDT', hours=24)
    print(f"Stats: {stats}")
    
    # Connection info
    info = storage.get_connection_info()
    print(f"Redis info: {info}")