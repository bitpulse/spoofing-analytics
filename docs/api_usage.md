# Spoofing Analytics API Documentation

## Overview

The Spoofing Analytics API provides real-time and historical access to cryptocurrency market manipulation (spoofing) data stored in Redis. It offers RESTful endpoints for querying, filtering, and analyzing spoofing events, plus WebSocket support for live updates.

## Features

- **Real-time Access**: Query spoofing data with <1ms response times
- **Multiple Query Patterns**: Recent, by pattern, top spoofs, statistics
- **Advanced Search**: Multi-criteria filtering
- **Live Updates**: WebSocket subscriptions for real-time notifications
- **Data Export**: CSV export functionality for analysis
- **CORS Enabled**: Ready for web frontend integration

## Quick Start

### 1. Start Redis
```bash
redis-server
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the API Server
```bash
python run_api.py
```

The API will be available at `http://localhost:8000`

### 4. View Interactive Documentation
Open `http://localhost:8000/docs` in your browser for Swagger UI

## API Endpoints

### Core Endpoints

#### Get Recent Spoofs
```http
GET /api/spoofs/recent?symbol=BTCUSDT&minutes=5&limit=100
```
Returns spoofing events from the last N minutes.

**Parameters:**
- `symbol` (required): Trading pair (e.g., BTCUSDT)
- `minutes`: Time window (1-1440, default: 5)
- `limit`: Max results (1-1000, default: 100)

**Example Response:**
```json
{
  "symbol": "BTCUSDT",
  "minutes": 5,
  "count": 23,
  "spoofs": [
    {
      "timestamp": "2025-08-18T10:30:45",
      "whale_id": "BTCUSDT_ask_65000_123456",
      "side": "ask",
      "price": 65000.0,
      "initial_value_usd": 6500000.0,
      "time_active_seconds": 45.2,
      "spoof_pattern": "flickering",
      "severity_score": 85
    }
  ]
}
```

#### Get Spoofs by Pattern
```http
GET /api/spoofs/patterns?symbol=BTCUSDT&pattern=flickering&limit=50
```
Filter spoofs by manipulation pattern type.

**Pattern Types:**
- `single`: One-time fake orders
- `flickering`: Rapidly appearing/disappearing orders
- `size_manipulation`: Orders with dramatic size changes

#### Get Top Spoofs
```http
GET /api/spoofs/top?symbol=BTCUSDT&limit=10&by=severity
```
Returns the most significant spoofing events.

**Ranking Options:**
- `severity`: Composite score based on impact
- `size`: By USD value

#### Get Statistics
```http
GET /api/spoofs/stats?symbol=BTCUSDT&hours=24
```
Aggregated statistics for analysis.

**Response Includes:**
- Total spoofs count
- Total/average USD values
- Pattern distribution
- Hourly breakdown
- Top 5 spoofs

#### Advanced Search
```http
POST /api/spoofs/search?symbol=BTCUSDT&limit=100
Content-Type: application/json

{
  "min_value": 100000,
  "max_value": 10000000,
  "min_duration": 5,
  "max_duration": 60,
  "pattern": "flickering",
  "side": "bid"
}
```
Multi-criteria search for specific spoof characteristics.

### Utility Endpoints

#### Export to CSV
```http
GET /api/spoofs/export?symbol=BTCUSDT&hours=24
```
Downloads spoofing data as CSV file.

#### Get Available Symbols
```http
GET /api/symbols
```
Lists all symbols with available spoofing data.

#### Redis Info
```http
GET /api/redis/info
```
Redis connection status and statistics.

#### Health Check
```http
GET /health
```
Service health status for monitoring.

## WebSocket Support

### Live Spoof Notifications
```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/spoofs/BTCUSDT');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'spoof') {
    console.log('New spoof detected:', data.data);
    // Update UI with new spoof
  }
};
```

## Integration Examples

### Python Client
```python
import requests

# Get recent spoofs
response = requests.get(
    'http://localhost:8000/api/spoofs/recent',
    params={'symbol': 'BTCUSDT', 'minutes': 5}
)
spoofs = response.json()['spoofs']

for spoof in spoofs:
    print(f"Spoof: ${spoof['initial_value_usd']:,.0f} "
          f"lasted {spoof['time_active_seconds']:.1f}s")
```

### JavaScript/React
```javascript
// Fetch top spoofs
fetch('http://localhost:8000/api/spoofs/top?symbol=BTCUSDT&limit=5')
  .then(res => res.json())
  .then(data => {
    data.spoofs.forEach(spoof => {
      console.log(`Pattern: ${spoof.spoof_pattern}, 
                   Value: $${spoof.initial_value_usd.toLocaleString()}`);
    });
  });
```

### cURL Examples
```bash
# Get recent spoofs
curl "http://localhost:8000/api/spoofs/recent?symbol=BTCUSDT&minutes=10"

# Get statistics
curl "http://localhost:8000/api/spoofs/stats?symbol=BTCUSDT&hours=24"

# Search with filters
curl -X POST "http://localhost:8000/api/spoofs/search?symbol=BTCUSDT" \
  -H "Content-Type: application/json" \
  -d '{"min_value": 500000, "pattern": "flickering"}'
```

## Performance Considerations

### Response Times
- Recent spoofs: <5ms
- Pattern queries: <10ms
- Statistics: <20ms
- Search: <50ms (depends on criteria)

### Rate Limits
- Default: No rate limiting
- Production: Configure nginx/cloudflare rate limiting

### Caching
- Redis provides inherent caching
- Statistics cached for 1 minute
- Consider CDN for static exports

## Data Retention

- **Default TTL**: 30 days
- **Hourly Stats**: Aggregated and retained longer
- **CSV Exports**: Generated on-demand
- **Cleanup**: Automatic via Redis expiration

## Error Handling

All endpoints return standard HTTP status codes:
- `200`: Success
- `400`: Bad request (invalid parameters)
- `404`: Resource not found
- `500`: Server error

Error response format:
```json
{
  "detail": "Error description"
}
```

## Security Considerations

### CORS Configuration
Currently allows all origins (`*`). For production:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### Authentication
Not implemented. For production, consider:
- API keys
- JWT tokens
- OAuth2
- Rate limiting by API key

### Data Sanitization
All inputs are validated using Pydantic models.

## Monitoring

### Metrics to Track
- Request rate per endpoint
- Response times (p50, p95, p99)
- Redis memory usage
- WebSocket connections
- Error rates

### Health Checks
```bash
# Simple health check
curl http://localhost:8000/health

# Detailed Redis info
curl http://localhost:8000/api/redis/info
```

## Deployment

### Production Setup
```bash
# Use gunicorn with uvicorn workers
gunicorn src.api.spoofing_api:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "src.api.spoofing_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables
```bash
# Redis connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# API server
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false  # Set to true for development
```

## Troubleshooting

### Redis Connection Issues
```python
# Test Redis connection
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
r.ping()  # Should return True
```

### No Data Returned
1. Check if whale monitor is running and detecting spoofs
2. Verify Redis has data: `redis-cli keys "spoof:*"`
3. Check symbol spelling (case-sensitive)

### WebSocket Disconnections
- Implement reconnection logic in client
- Check nginx/proxy WebSocket settings
- Monitor for memory leaks in long connections

## Support

For issues or questions:
1. Check API docs at `/docs`
2. Review Redis data structure in `src/storage/redis_storage.py`
3. Check logs for errors
4. Monitor Redis memory usage