# Multi-stage build for optimized image size
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 whale && \
    mkdir -p /app/data /app/logs && \
    chown -R whale:whale /app

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/whale/.local

# Copy application code
COPY --chown=whale:whale . .

# Ensure Python can find the installed packages
ENV PATH=/home/whale/.local/bin:$PATH
ENV PYTHONPATH=/app:$PYTHONPATH

# Switch to non-root user
USER whale

# Create necessary directories
RUN mkdir -p data logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default environment variables
ENV LOG_LEVEL=INFO \
    ORDER_BOOK_DEPTH=20 \
    ORDER_BOOK_UPDATE_SPEED=100ms \
    MONITORING_GROUP=0

# Volume for persistent data
VOLUME ["/app/data", "/app/logs"]

# Default command - can be overridden
ENTRYPOINT ["python", "-m", "src.whale_monitor"]
# CMD can be overridden to specify group number
CMD []