# AI/ML Service Dockerfile - Multi-stage build for optimal image size
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies for ML libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    libjpeg-dev \
    libpng-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies for ML operations
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy wheels from builder and install
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

# Create models directory
RUN mkdir -p /app/models && chown -R appuser:appuser /app/models

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    SERVICE_NAME=ai-ml-service \
    SERVICE_PORT=8006 \
    MODEL_STORAGE_PATH=/app/models

# Expose port
EXPOSE 8006

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8006/health || exit 1

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8006"]
