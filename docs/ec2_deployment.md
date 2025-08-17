# EC2 Deployment Guide for Whale Monitoring System

## Prerequisites

- AWS Account with EC2 access
- EC2 instance (recommended: t3.xlarge or larger)
- Docker and Docker Compose installed
- Git installed
- Telegram Bot Token (optional, for alerts)

## Recommended EC2 Instance Types

### Development/Testing
- **t3.large** (2 vCPU, 8 GB RAM) - Can run 2-3 groups
- **t3.xlarge** (4 vCPU, 16 GB RAM) - Can run all 5 groups

### Production
- **c5.2xlarge** (8 vCPU, 16 GB RAM) - Optimal for all 5 groups
- **m5.2xlarge** (8 vCPU, 32 GB RAM) - Extra memory for data processing

## Step 1: Launch EC2 Instance

1. Launch Ubuntu 22.04 LTS AMI
2. Configure Security Group:
   ```
   - SSH (port 22) from your IP
   - Custom TCP (port 9090) for metrics (optional)
   ```
3. Allocate at least 50 GB EBS storage

## Step 2: Connect and Setup

```bash
# Connect to EC2
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
# Log out and back in for group changes to take effect

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installations
docker --version
docker-compose --version
```

## Step 3: Clone and Configure

```bash
# Clone repository
git clone https://github.com/yourusername/whale-analytics-system.git
cd whale-analytics-system

# Create .env file
cat > .env << 'EOF'
# Binance WebSocket Configuration
BINANCE_WS_BASE_URL=wss://fstream.binance.com
BINANCE_REST_BASE_URL=https://fapi.binance.com

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/whale_analytics.log

# Order Book Settings
ORDER_BOOK_DEPTH=20
ORDER_BOOK_UPDATE_SPEED=100ms

# Telegram Alerts (optional)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHANNEL_ID=@your_channel_here
TELEGRAM_ALERTS_ENABLED=false

# Database (optional, for future use)
DATABASE_URL=postgresql://user:password@localhost/whale_analytics

# Redis (optional, for future use)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
EOF

# Create data and logs directories
mkdir -p data logs
mkdir -p data/group{1..5} logs/group{1..5}

# Set permissions
chmod 600 .env
```

## Step 4: Build and Run with Docker

### Option A: Run All 5 Groups
```bash
# Build image
docker-compose build

# Start all groups
docker-compose up -d

# Check status
docker-compose ps

# View logs for specific group
docker-compose logs -f whale-group-1
```

### Option B: Run Specific Groups
```bash
# Start only groups 1 and 2
docker-compose up -d whale-group-1 whale-group-2

# Scale specific service
docker-compose up -d --scale whale-group-1=2
```

### Option C: Run Single Group with Docker
```bash
# Build image
docker build -t whale-monitor .

# Run group 1
docker run -d \
  --name whale-group-1 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/.env:/app/.env:ro \
  --restart unless-stopped \
  whale-monitor 1

# Run group 2
docker run -d \
  --name whale-group-2 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/.env:/app/.env:ro \
  --restart unless-stopped \
  whale-monitor 2
```

## Step 5: Monitoring and Management

### View Container Status
```bash
# All containers
docker ps

# Resource usage
docker stats

# System resources
htop
```

### View Logs
```bash
# All groups
docker-compose logs -f

# Specific group
docker-compose logs -f whale-group-1

# Last 100 lines
docker-compose logs --tail 100 whale-group-2
```

### Data Collection
```bash
# Check CSV files
ls -la data/group1/*.csv

# Monitor file growth
watch -n 5 'du -sh data/*'

# Tail whale orders
tail -f data/group1/whale_orders_*.csv
```

### Stop and Restart
```bash
# Stop all groups
docker-compose stop

# Stop specific group
docker-compose stop whale-group-1

# Restart all
docker-compose restart

# Remove containers (preserves data)
docker-compose down
```

## Step 6: Automated Startup

### Using systemd
```bash
# Create service file
sudo cat > /etc/systemd/system/whale-monitor.service << 'EOF'
[Unit]
Description=Whale Monitoring System
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/whale-analytics-system
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl enable whale-monitor
sudo systemctl start whale-monitor
```

## Step 7: Backup and Maintenance

### Automated Backups to S3
```bash
# Install AWS CLI
sudo apt install awscli -y
aws configure

# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
tar -czf whale_data_$TIMESTAMP.tar.gz data/
aws s3 cp whale_data_$TIMESTAMP.tar.gz s3://your-bucket/backups/
rm whale_data_$TIMESTAMP.tar.gz
find data/ -name "*.csv" -mtime +7 -delete  # Remove CSV files older than 7 days
EOF

chmod +x backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/ubuntu/whale-analytics-system/backup.sh") | crontab -
```

### Log Rotation
```bash
# Create logrotate config
sudo cat > /etc/logrotate.d/whale-monitor << 'EOF'
/home/ubuntu/whale-analytics-system/logs/**/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 ubuntu ubuntu
}
EOF
```

## Performance Tuning

### Docker Resource Limits
Edit `docker-compose.yml` to adjust:
```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'    # Increase for better performance
      memory: 1024M  # Increase if seeing OOM errors
```

### System Tuning
```bash
# Increase file descriptors
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Optimize network settings
sudo sysctl -w net.core.rmem_max=134217728
sudo sysctl -w net.core.wmem_max=134217728
sudo sysctl -w net.ipv4.tcp_rmem="4096 87380 134217728"
sudo sysctl -w net.ipv4.tcp_wmem="4096 65536 134217728"

# Make permanent
echo "net.core.rmem_max=134217728" | sudo tee -a /etc/sysctl.conf
echo "net.core.wmem_max=134217728" | sudo tee -a /etc/sysctl.conf
```

## Monitoring with CloudWatch

```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb

# Configure for Docker metrics
sudo cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
  "metrics": {
    "namespace": "WhaleMonitor",
    "metrics_collected": {
      "cpu": {
        "measurement": [
          {"name": "cpu_usage_idle", "rename": "CPU_IDLE", "unit": "Percent"}
        ],
        "totalcpu": false
      },
      "mem": {
        "measurement": [
          {"name": "mem_used_percent", "rename": "MEM_USED", "unit": "Percent"}
        ]
      },
      "disk": {
        "measurement": [
          {"name": "used_percent", "rename": "DISK_USED", "unit": "Percent"}
        ],
        "resources": ["/"]
      }
    }
  }
}
EOF

# Start agent
sudo systemctl start amazon-cloudwatch-agent
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose logs whale-group-1

# Check configuration
docker-compose config

# Rebuild image
docker-compose build --no-cache
```

### High Memory Usage
```bash
# Check memory per container
docker stats --no-stream

# Limit memory in docker-compose.yml
# Reduce ORDER_BOOK_DEPTH in .env
```

### Connection Issues
```bash
# Test WebSocket connection
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==" \
  https://fstream.binance.com/ws/btcusdt@depth20@100ms

# Check DNS
nslookup fstream.binance.com

# Check network
docker network ls
docker network inspect whale-analytics-system_whale-network
```

### Data Not Being Saved
```bash
# Check permissions
ls -la data/
ls -la logs/

# Check disk space
df -h

# Check volume mounts
docker inspect whale-group-1 | grep -A 10 Mounts
```

## Security Best Practices

1. **Never commit .env file** to git
2. **Use AWS Secrets Manager** for sensitive data
3. **Enable EC2 Instance Connect** instead of SSH keys
4. **Set up VPC** with private subnets
5. **Use IAM roles** for S3 access
6. **Enable CloudWatch alarms** for anomaly detection
7. **Regular security updates**: `sudo unattended-upgrades`

## Cost Optimization

1. **Use Spot Instances** for non-critical monitoring
2. **Schedule start/stop** during low-activity hours
3. **Use S3 Intelligent-Tiering** for backups
4. **Monitor with AWS Cost Explorer**
5. **Consider Reserved Instances** for long-term use

## Support

For issues or questions:
- Check logs: `docker-compose logs`
- System status: `docker ps` and `htop`
- Review documentation in `/docs` directory
- Monitor Telegram alerts if configured