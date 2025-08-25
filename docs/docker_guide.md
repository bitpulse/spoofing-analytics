# Docker Deployment Guide

## Overview

This guide covers Docker deployment for the BitPulse Spoofing Analytics system components, with a focus on the Whale Monitor service that tracks large cryptocurrency orders and market manipulation patterns.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Building Images](#building-images)
- [Running Containers](#running-containers)
- [Configuration](#configuration)
- [Data Persistence](#data-persistence)
- [Monitoring & Logs](#monitoring--logs)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production-deployment)

## Prerequisites

- Docker Engine 20.10+ installed
- Docker Compose 2.0+ (optional, for multi-container setups)
- `.env` file configured with required API keys and settings
- Sufficient disk space for logs and data storage (minimum 10GB recommended)

## Building Images

### Whale Monitor Image

Build the whale monitor image using the provided Dockerfile:

```bash
# Basic build
docker build -f Dockerfile.whale-monitor -t whale-monitor:latest .

# Build with specific tag
docker build -f Dockerfile.whale-monitor -t whale-monitor:v1.0 .

# Build with no cache (fresh build)
docker build -f Dockerfile.whale-monitor --no-cache -t whale-monitor:latest .

# Multi-platform build (for ARM/AMD64)
docker buildx build -f Dockerfile.whale-monitor --platform linux/amd64,linux/arm64 -t whale-monitor:latest .
```

## Running Containers

### Basic Run Commands

```bash
# Run with default configuration (monitors group 1)
docker run -d --name whale-monitor whale-monitor:latest

# Run interactively for debugging
docker run -it --rm whale-monitor:latest

# Run with automatic restart
docker run -d --restart unless-stopped --name whale-monitor whale-monitor:latest
```

### Monitoring Different Symbol Groups

The whale monitor supports 5 predefined symbol groups optimized for detecting manipulation:

```bash
# Group 1: Ultra high risk meme coins (97%+ manipulation rate)
docker run -d --name whale-group1 whale-monitor:latest python -m src.whale_monitor 1

# Group 2: AI & Gaming narrative tokens (50-70% daily swings)
docker run -d --name whale-group2 whale-monitor:latest python -m src.whale_monitor 2

# Group 3: Low cap DeFi & L2s (thin order books)
docker run -d --name whale-group3 whale-monitor:latest python -m src.whale_monitor 3

# Group 4: Volatile alts (30-50% regular moves)
docker run -d --name whale-group4 whale-monitor:latest python -m src.whale_monitor 4

# Group 5: Mid-cap majors (higher liquidity)
docker run -d --name whale-group5 whale-monitor:latest python -m src.whale_monitor 5
```

### Monitoring Specific Trading Pairs

```bash
# Monitor Bitcoin
docker run -d --name whale-btc whale-monitor:latest python -m src.whale_monitor BTCUSDT

# Monitor Ethereum
docker run -d --name whale-eth whale-monitor:latest python -m src.whale_monitor ETHUSDT

# Monitor multiple pairs in parallel
docker run -d --name whale-btc whale-monitor:latest python -m src.whale_monitor BTCUSDT
docker run -d --name whale-eth whale-monitor:latest python -m src.whale_monitor ETHUSDT
docker run -d --name whale-sol whale-monitor:latest python -m src.whale_monitor SOLUSDT
```

## Configuration

### Environment Variables

Pass environment variables using `--env-file` or `-e` flags:

```bash
# Using .env file (recommended)
docker run -d --env-file .env --name whale-monitor whale-monitor:latest

# Individual environment variables
docker run -d \
  -e TELEGRAM_BOT_TOKEN=your_token \
  -e TELEGRAM_CHAT_ID=your_chat_id \
  -e REDIS_HOST=redis \
  -e REDIS_PORT=6379 \
  -e LOG_LEVEL=INFO \
  --name whale-monitor whale-monitor:latest
```

### Required Environment Variables

Create a `.env` file with the following variables:

```env
# Telegram Alerts
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=optional_password

# Monitoring Settings
WHALE_THRESHOLD_USD=50000
ORDER_BOOK_DEPTH=100
UPDATE_INTERVAL=1

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Data Persistence

### Volume Mounts

Persist data and logs outside the container:

```bash
# Mount data and logs directories
docker run -d \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  --name whale-monitor \
  whale-monitor:latest

# Using named volumes
docker volume create whale-data
docker volume create whale-logs

docker run -d \
  -v whale-data:/app/data \
  -v whale-logs:/app/logs \
  --env-file .env \
  --name whale-monitor \
  whale-monitor:latest
```

### Backup Data

```bash
# Backup data from container
docker cp whale-monitor:/app/data ./backup/data-$(date +%Y%m%d)
docker cp whale-monitor:/app/logs ./backup/logs-$(date +%Y%m%d)

# Backup named volumes
docker run --rm \
  -v whale-data:/source \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/whale-data-$(date +%Y%m%d).tar.gz -C /source .
```

## Monitoring & Logs

### View Container Logs

```bash
# View real-time logs
docker logs -f whale-monitor

# View last 100 lines
docker logs --tail 100 whale-monitor

# View logs with timestamps
docker logs -t whale-monitor

# Filter logs by time
docker logs --since 2h whale-monitor
docker logs --since 2024-01-01T00:00:00 whale-monitor
```

### Container Statistics

```bash
# View resource usage
docker stats whale-monitor

# View detailed container info
docker inspect whale-monitor

# Check container health
docker ps --filter name=whale-monitor
```

### Log Rotation

Configure Docker log rotation in `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "10",
    "compress": "true"
  }
}
```

## Troubleshooting

### Common Issues and Solutions

#### Container Exits Immediately

```bash
# Check exit code and logs
docker ps -a --filter name=whale-monitor
docker logs whale-monitor

# Run interactively to debug
docker run -it --rm --env-file .env whale-monitor:latest /bin/bash
```

#### Permission Errors

```bash
# Fix data directory permissions
docker exec whale-monitor chown -R 1000:1000 /app/data /app/logs

# Run with specific user
docker run -d --user 1000:1000 --name whale-monitor whale-monitor:latest
```

#### Network Connectivity Issues

```bash
# Test network from container
docker run --rm whale-monitor:latest curl -I https://api.binance.com

# Run with host network (development only)
docker run -d --network host --name whale-monitor whale-monitor:latest
```

#### Memory Issues

```bash
# Limit memory usage
docker run -d \
  --memory="2g" \
  --memory-swap="4g" \
  --name whale-monitor \
  whale-monitor:latest

# Check memory usage
docker stats --no-stream whale-monitor
```

### Debug Commands

```bash
# Execute commands in running container
docker exec -it whale-monitor /bin/bash
docker exec whale-monitor ps aux
docker exec whale-monitor ls -la /app/data

# Copy files for inspection
docker cp whale-monitor:/app/logs/whale_analytics.log ./debug/

# Check container filesystem
docker diff whale-monitor
```

## Production Deployment

### Docker Compose Setup

Create `docker-compose.yml` for production:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis-data:/data
    ports:
      - "127.0.0.1:6379:6379"
    command: redis-server --appendonly yes

  whale-monitor-group1:
    image: whale-monitor:latest
    restart: unless-stopped
    env_file: .env
    environment:
      - REDIS_HOST=redis
    volumes:
      - ./data:/app/data
      - ./logs/group1:/app/logs
    depends_on:
      - redis
    command: python -m src.whale_monitor 1

  whale-monitor-group2:
    image: whale-monitor:latest
    restart: unless-stopped
    env_file: .env
    environment:
      - REDIS_HOST=redis
    volumes:
      - ./data:/app/data
      - ./logs/group2:/app/logs
    depends_on:
      - redis
    command: python -m src.whale_monitor 2

volumes:
  redis-data:
```

### Health Checks

Add health checks to Dockerfile:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)" || exit 1
```

### Resource Limits

Set appropriate resource limits:

```bash
docker run -d \
  --cpus="2" \
  --memory="4g" \
  --memory-reservation="2g" \
  --restart unless-stopped \
  --name whale-monitor \
  whale-monitor:latest
```

### Security Best Practices

1. **Run as non-root user** (already configured in Dockerfile)
2. **Use read-only filesystem where possible**:
   ```bash
   docker run -d --read-only \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/logs:/app/logs \
     --tmpfs /tmp \
     --name whale-monitor \
     whale-monitor:latest
   ```

3. **Limit capabilities**:
   ```bash
   docker run -d \
     --cap-drop=ALL \
     --cap-add=NET_BIND_SERVICE \
     --name whale-monitor \
     whale-monitor:latest
   ```

4. **Use secrets for sensitive data**:
   ```bash
   # Create secrets
   echo "your_token" | docker secret create telegram_token -
   
   # Use in Docker Swarm
   docker service create \
     --secret telegram_token \
     --name whale-monitor \
     whale-monitor:latest
   ```

### Monitoring Stack Integration

Integrate with Prometheus/Grafana:

```yaml
# Add to docker-compose.yml
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
    - prometheus-data:/prometheus
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana:latest
  volumes:
    - grafana-data:/var/lib/grafana
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
```

## Maintenance

### Update Container

```bash
# Pull latest image
docker pull whale-monitor:latest

# Stop and remove old container
docker stop whale-monitor
docker rm whale-monitor

# Start new container with same configuration
docker run -d \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  --restart unless-stopped \
  --name whale-monitor \
  whale-monitor:latest
```

### Cleanup

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Full cleanup (careful!)
docker system prune -a --volumes
```

## Quick Reference

```bash
# Build
docker build -f Dockerfile.whale-monitor -t whale-monitor .

# Run basic
docker run -d --name whale-monitor whale-monitor

# Run with everything
docker run -d \
  --name whale-monitor \
  --restart unless-stopped \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  --memory="2g" \
  --cpus="1" \
  whale-monitor:latest python -m src.whale_monitor 1

# Stop
docker stop whale-monitor

# Remove
docker rm whale-monitor

# Logs
docker logs -f whale-monitor

# Shell access
docker exec -it whale-monitor /bin/bash

# Stats
docker stats whale-monitor
```

## Support

For issues or questions:
1. Check container logs: `docker logs whale-monitor`
2. Review the troubleshooting section above
3. Ensure all environment variables are set correctly
4. Verify network connectivity to Binance API
5. Check disk space for data/logs directories