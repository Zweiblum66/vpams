# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # FFmpeg for media metadata extraction
    ffmpeg \
    # ExifTool for image metadata
    libimage-exiftool-perl \
    # Build dependencies
    gcc \
    python3-dev \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set Python path
ENV PYTHONPATH=/app/src

# Expose port
EXPOSE 8005

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8005/health').raise_for_status()"

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8005"]