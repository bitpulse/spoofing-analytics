#!/bin/bash
# Fix Docker permission issues for whale analytics

echo "Fixing permissions for Docker volumes..."

# Create directories if they don't exist
mkdir -p data logs

# Fix permissions (make them writable)
chmod -R 777 data logs

# Alternative: Set ownership to the container user (UID 1000 typically)
# chown -R 1000:1000 data logs

echo "Permissions fixed!"
echo ""
echo "Now you can run the container:"
echo "docker run -d \\"
echo "  -v \$(pwd)/data:/app/data \\"
echo "  -v \$(pwd)/logs:/app/logs \\"
echo "  --env-file .env \\"
echo "  --network host \\"
echo "  --name whale-group1 \\"
echo "  whale-monitor:latest python -m src.whale_monitor 1"
echo ""
echo "Note: Added --network host to allow connection to InfluxDB on localhost"