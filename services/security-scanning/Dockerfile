FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for security scanning tools
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    build-essential \
    nmap \
    nikto \
    dirb \
    sqlmap \
    git \
    dnsutils \
    netcat-traditional \
    masscan \
    zmap \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Install additional security tools
RUN curl -sSfL https://raw.githubusercontent.com/securecodewarrior/github-action-add-sarif/main/scripts/install-semgrep.sh | sh
RUN pip install bandit safety

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]