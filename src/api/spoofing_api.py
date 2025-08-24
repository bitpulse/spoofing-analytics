"""
Web API for querying spoofing data from Redis
FastAPI-based REST endpoints for real-time and historical spoof data
"""

from fastapi import FastAPI, Query, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import asyncio
from loguru import logger
from pydantic import BaseModel, Field
import time
import tempfile
import os

from src.storage.redis_storage import RedisSpoofStorage
from src.config import Config


# Initialize FastAPI app
app = FastAPI(
    title="Spoofing Analytics API",
    description="Real-time API for cryptocurrency market spoofing detection data",
    version="1.0.0"
)

# Add CORS middleware for web frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis storage
config = Config()
redis_storage = RedisSpoofStorage(
    host=config.redis_host,
    port=config.redis_port,
    db=config.redis_db
)


# Pydantic models for request/response
class SpoofResponse(BaseModel):
    """Spoofing event response model"""
    timestamp: str
    symbol: str
    whale_id: str
    side: str
    price: float
    initial_value_usd: float
    final_value_usd: float
    time_active_seconds: float
    percentage_of_book: float
    spoof_pattern: str
    severity_score: float = 0
    
    
class SpoofStats(BaseModel):
    """Spoofing statistics response"""
    symbol: str
    period_hours: int
    total_spoofs: int
    total_value_usd: float
    avg_value_usd: float
    spoofs_per_hour: float
    patterns: Dict[str, int]
    top_spoofs: List[Dict]
    hourly_distribution: List[Dict]
    

class SearchFilters(BaseModel):
    """Search filter parameters"""
    min_value: Optional[float] = Field(None, description="Minimum USD value")
    max_value: Optional[float] = Field(None, description="Maximum USD value")
    min_duration: Optional[float] = Field(None, description="Minimum active seconds")
    max_duration: Optional[float] = Field(None, description="Maximum active seconds")
    pattern: Optional[str] = Field(None, description="Spoof pattern type")
    side: Optional[str] = Field(None, description="Order side (bid/ask)")
    start_time: Optional[float] = Field(None, description="Start timestamp")
    end_time: Optional[float] = Field(None, description="End timestamp")


# API Endpoints

@app.get("/")
async def root():
    """API root endpoint with basic info"""
    return {
        "service": "Spoofing Analytics API",
        "version": "1.0.0",
        "status": "operational",
        "redis_connected": redis_storage.get_connection_info()['connected'],
        "endpoints": {
            "recent_spoofs": "/api/spoofs/recent",
            "spoof_patterns": "/api/spoofs/patterns",
            "top_spoofs": "/api/spoofs/top",
            "spoof_stats": "/api/spoofs/stats",
            "search_spoofs": "/api/spoofs/search",
            "live_websocket": "/ws/spoofs/{symbol}"
        }
    }


@app.get("/api/spoofs/recent")
async def get_recent_spoofs(
    symbol: str = Query(..., description="Trading symbol (e.g., BTCUSDT)"),
    minutes: int = Query(5, ge=1, le=1440, description="Time window in minutes"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results")
) -> List[Dict]:
    """
    Get recent spoofing events within specified time window
    
    - **symbol**: Trading pair symbol (required)
    - **minutes**: Look back period in minutes (default: 5)
    - **limit**: Maximum number of results (default: 100)
    """
    try:
        spoofs = redis_storage.get_recent_spoofs(symbol, minutes, limit)
        
        if not spoofs:
            return JSONResponse(
                content={
                    "symbol": symbol,
                    "minutes": minutes,
                    "count": 0,
                    "spoofs": [],
                    "message": "No spoofs found in the specified time window"
                }
            )
            
        return JSONResponse(
            content={
                "symbol": symbol,
                "minutes": minutes,
                "count": len(spoofs),
                "spoofs": spoofs
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting recent spoofs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/spoofs/patterns")
async def get_spoofs_by_pattern(
    symbol: str = Query(..., description="Trading symbol"),
    pattern: str = Query(..., description="Pattern type: single, flickering, or size_manipulation"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results")
) -> List[Dict]:
    """
    Get spoofing events filtered by pattern type
    
    - **symbol**: Trading pair symbol (required)
    - **pattern**: Spoof pattern type (required)
    - **limit**: Maximum number of results (default: 100)
    """
    valid_patterns = ['single', 'flickering', 'size_manipulation']
    if pattern not in valid_patterns:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid pattern. Must be one of: {', '.join(valid_patterns)}"
        )
        
    try:
        spoofs = redis_storage.get_spoofs_by_pattern(symbol, pattern, limit)
        
        return JSONResponse(
            content={
                "symbol": symbol,
                "pattern": pattern,
                "count": len(spoofs),
                "spoofs": spoofs
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting spoofs by pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/spoofs/top")
async def get_top_spoofs(
    symbol: str = Query(..., description="Trading symbol"),
    limit: int = Query(10, ge=1, le=100, description="Number of top spoofs"),
    by: str = Query("severity", description="Ranking criteria: severity or size")
) -> List[Dict]:
    """
    Get top spoofing events ranked by severity or size
    
    - **symbol**: Trading pair symbol (required)
    - **limit**: Number of results (default: 10)
    - **by**: Ranking criteria - 'severity' or 'size' (default: severity)
    """
    if by not in ['severity', 'size']:
        raise HTTPException(
            status_code=400,
            detail="Ranking criteria must be 'severity' or 'size'"
        )
        
    try:
        spoofs = redis_storage.get_top_spoofs(symbol, limit, by)
        
        return JSONResponse(
            content={
                "symbol": symbol,
                "ranking_by": by,
                "count": len(spoofs),
                "spoofs": spoofs
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting top spoofs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/spoofs/stats", response_model=SpoofStats)
async def get_spoof_statistics(
    symbol: str = Query(..., description="Trading symbol"),
    hours: int = Query(24, ge=1, le=168, description="Time period in hours")
):
    """
    Get aggregated spoofing statistics
    
    - **symbol**: Trading pair symbol (required)
    - **hours**: Analysis period in hours (default: 24, max: 168)
    """
    try:
        stats = redis_storage.get_spoof_stats(symbol, hours)
        
        if not stats:
            return JSONResponse(
                content={
                    "symbol": symbol,
                    "period_hours": hours,
                    "total_spoofs": 0,
                    "message": "No data available for the specified period"
                }
            )
            
        return stats
        
    except Exception as e:
        logger.error(f"Error getting spoof stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/spoofs/search")
async def search_spoofs(
    symbol: str = Query(..., description="Trading symbol"),
    filters: SearchFilters = None,
    limit: int = Query(100, ge=1, le=1000, description="Maximum results")
) -> List[Dict]:
    """
    Search spoofs with multiple filter criteria
    
    - **symbol**: Trading pair symbol (required)
    - **filters**: Search filter criteria (JSON body)
    - **limit**: Maximum number of results (default: 100)
    """
    try:
        # Convert filters to dict if provided
        filter_dict = {}
        if filters:
            filter_dict = {
                k: v for k, v in filters.dict().items() 
                if v is not None
            }
            
        spoofs = redis_storage.search_spoofs(symbol, filter_dict, limit)
        
        return JSONResponse(
            content={
                "symbol": symbol,
                "filters": filter_dict,
                "count": len(spoofs),
                "spoofs": spoofs
            }
        )
        
    except Exception as e:
        logger.error(f"Error searching spoofs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/spoofs/export")
async def export_spoofs_to_csv(
    symbol: str = Query(..., description="Trading symbol"),
    hours: int = Query(24, ge=1, le=168, description="Export period in hours")
):
    """
    Export spoofing data to CSV file for download
    
    - **symbol**: Trading pair symbol (required)
    - **hours**: Export period in hours (default: 24)
    """
    try:
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix=f'_{symbol}_spoofs.csv',
            delete=False
        )
        temp_path = temp_file.name
        temp_file.close()
        
        # Calculate time range
        end_time = time.time()
        start_time = end_time - (hours * 3600)
        
        # Export data
        redis_storage.export_to_csv(symbol, temp_path, start_time, end_time)
        
        # Return file for download
        return FileResponse(
            path=temp_path,
            filename=f"{symbol}_spoofs_{hours}h.csv",
            media_type="text/csv",
            background=lambda: os.unlink(temp_path)  # Delete after download
        )
        
    except Exception as e:
        logger.error(f"Error exporting spoofs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/redis/info")
async def get_redis_info():
    """Get Redis connection information and statistics"""
    try:
        info = redis_storage.get_connection_info()
        return JSONResponse(content=info)
    except Exception as e:
        logger.error(f"Error getting Redis info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/symbols")
async def get_available_symbols():
    """Get list of symbols with available spoofing data"""
    try:
        # Get all timeline keys to find symbols
        symbols = set()
        for key in redis_storage.redis_client.scan_iter("spoofs:timeline:*"):
            symbol = key.split(':')[-1]
            symbols.add(symbol)
            
        # Get count for each symbol
        symbol_stats = []
        for symbol in symbols:
            count = redis_storage.redis_client.zcard(f"spoofs:timeline:{symbol}")
            symbol_stats.append({
                "symbol": symbol,
                "spoof_count": count
            })
            
        # Sort by count
        symbol_stats.sort(key=lambda x: x['spoof_count'], reverse=True)
        
        return JSONResponse(
            content={
                "total_symbols": len(symbols),
                "symbols": symbol_stats
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pairs")
async def get_monitored_pairs():
    """
    Get list of all monitored trading pairs with detailed information
    
    Returns configuration, monitoring status, and data availability for each pair
    """
    try:
        # Import config to get monitoring groups
        from src.thresholds import MONITORING_GROUPS, PAIR_THRESHOLDS
        
        # Collect all monitored pairs
        monitored_pairs = {}
        
        # Get configured pairs from monitoring groups
        for group_num, pairs in MONITORING_GROUPS.items():
            for pair in pairs:
                if pair not in monitored_pairs:
                    monitored_pairs[pair] = {
                        "symbol": pair,
                        "monitoring_group": group_num,
                        "group_name": {
                            1: "Ultra High Risk - Meme Coins",
                            2: "AI & Gaming Narrative",
                            3: "Low Cap DeFi & L2s",
                            4: "Volatile Alts",
                            5: "Mid-Cap Majors"
                        }.get(group_num, "Custom"),
                        "thresholds": PAIR_THRESHOLDS.get(pair, {
                            "whale": 100000,
                            "mega_whale": 500000
                        }),
                        "has_data": False,
                        "data_stats": {}
                    }
        
        # Check Redis for actual data availability
        for pair in list(monitored_pairs.keys()):
            # Check spoofing data
            spoof_count = redis_storage.redis_client.zcard(f"spoofs:timeline:{pair}")
            
            # Get time range if data exists
            if spoof_count > 0:
                monitored_pairs[pair]["has_data"] = True
                
                # Get first and last spoof timestamps
                first_spoof = redis_storage.redis_client.zrange(
                    f"spoofs:timeline:{pair}", 0, 0, withscores=True
                )
                last_spoof = redis_storage.redis_client.zrange(
                    f"spoofs:timeline:{pair}", -1, -1, withscores=True
                )
                
                if first_spoof and last_spoof:
                    monitored_pairs[pair]["data_stats"] = {
                        "total_spoofs": spoof_count,
                        "first_seen": datetime.fromtimestamp(first_spoof[0][1]).isoformat(),
                        "last_seen": datetime.fromtimestamp(last_spoof[0][1]).isoformat(),
                        "patterns": {}
                    }
                    
                    # Get pattern distribution
                    for pattern in ['single', 'flickering', 'size_manipulation']:
                        pattern_count = redis_storage.redis_client.scard(
                            f"spoofs:pattern:{pattern}:{pair}"
                        )
                        if pattern_count > 0:
                            monitored_pairs[pair]["data_stats"]["patterns"][pattern] = pattern_count
        
        # Also check for pairs with data but not in config
        for key in redis_storage.redis_client.scan_iter("spoofs:timeline:*"):
            symbol = key.split(':')[-1]
            if symbol not in monitored_pairs:
                spoof_count = redis_storage.redis_client.zcard(key)
                monitored_pairs[symbol] = {
                    "symbol": symbol,
                    "monitoring_group": 0,
                    "group_name": "Unconfigured (Historical Data Only)",
                    "thresholds": {
                        "whale": 100000,
                        "mega_whale": 500000
                    },
                    "has_data": True,
                    "data_stats": {
                        "total_spoofs": spoof_count
                    }
                }
        
        # Sort by monitoring group and then by symbol
        sorted_pairs = sorted(
            monitored_pairs.values(),
            key=lambda x: (x["monitoring_group"], x["symbol"])
        )
        
        # Group by monitoring status
        active_monitoring = [p for p in sorted_pairs if p["monitoring_group"] > 0]
        data_only = [p for p in sorted_pairs if p["monitoring_group"] == 0]
        
        return JSONResponse(
            content={
                "total_pairs": len(monitored_pairs),
                "actively_monitored": len(active_monitoring),
                "data_only": len(data_only),
                "monitoring_groups": {
                    1: "Ultra High Risk - Meme Coins & New Listings",
                    2: "AI & Gaming Narrative - Heavy Speculation",
                    3: "Low Cap DeFi & L2s - Liquidity Games",
                    4: "Volatile Alts - Manipulation Favorites",
                    5: "Mid-Cap Majors & Established Alts"
                },
                "pairs": sorted_pairs,
                "summary": {
                    "with_data": len([p for p in sorted_pairs if p["has_data"]]),
                    "without_data": len([p for p in sorted_pairs if not p["has_data"]]),
                    "by_group": {
                        group: len([p for p in sorted_pairs if p["monitoring_group"] == group])
                        for group in range(6)
                    }
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting monitored pairs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket for real-time updates
@app.websocket("/ws/spoofs/{symbol}")
async def websocket_live_spoofs(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint for real-time spoof notifications
    
    Connect to receive live updates when new spoofs are detected
    """
    pubsub = None
    try:
        await websocket.accept()
        logger.info(f"WebSocket client connected for {symbol}")
        
        # Create pubsub subscription
        pubsub = redis_storage.redis_client.pubsub()
        pubsub.subscribe(f"spoofs:live:{symbol}")
        
        # Send initial connection message
        await websocket.send_json({
            "type": "connection",
            "symbol": symbol,
            "message": f"Connected to live spoofs for {symbol}"
        })
        
        # Listen for messages
        while True:
            # Check for new messages (non-blocking)
            message = pubsub.get_message(timeout=1.0)
            
            if message and message['type'] == 'message':
                # Parse and send spoof data
                try:
                    spoof_data = json.loads(message['data'])
                    await websocket.send_json({
                        "type": "spoof",
                        "data": spoof_data
                    })
                except Exception as send_error:
                    logger.debug(f"Error sending WebSocket message: {send_error}")
                    break  # Exit loop if we can't send messages
                    
            # Check if client is still connected (ping-pong)
            try:
                await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=0.1
                )
            except asyncio.TimeoutError:
                pass  # Expected timeout, connection still alive
            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected normally for {symbol}")
                break
            except Exception:
                # Client disconnected unexpectedly
                logger.debug(f"WebSocket client disconnected unexpectedly for {symbol}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for {symbol}")
    except Exception as e:
        if "no close frame received or sent" not in str(e):
            logger.error(f"WebSocket error for {symbol}: {e}")
    finally:
        # Clean up resources
        if pubsub:
            try:
                pubsub.unsubscribe()
                pubsub.close()
            except Exception:
                pass  # Ignore cleanup errors
        
        # Try to close WebSocket if still open
        try:
            await websocket.close()
        except Exception:
            pass  # WebSocket already closed


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    redis_connected = redis_storage.get_connection_info()['connected']
    
    return {
        "status": "healthy" if redis_connected else "degraded",
        "timestamp": datetime.now().isoformat(),
        "redis_connected": redis_connected
    }


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Spoofing API started")
    
    # Test Redis connection
    info = redis_storage.get_connection_info()
    if info['connected']:
        logger.info(f"Redis connected: {info['total_keys']} keys in database")
    else:
        logger.error("Failed to connect to Redis")
        

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Spoofing API shutting down")


# Run the API server
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True
    )