# Build stage
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only requirements first to leverage Docker cache
COPY requirements.txt setup.py ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt gunicorn && \
    pip install --no-cache-dir -e .

# Copy application code
COPY toms_gym/ toms_gym/
COPY main.py .

# Final stage
FROM python:3.11-slim

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy only the necessary files from builder
COPY --from=builder /app/toms_gym /app/toms_gym
COPY --from=builder /app/main.py .

# Set environment variables
ENV PORT=8080 \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

# Run as non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/ || exit 1

# Command to run the application with gunicorn
CMD exec gunicorn \
    --bind :${PORT} \
    --workers 2 \
    --threads 8 \
    --timeout 0 \
    --worker-class gthread \
    --worker-tmp-dir /dev/shm \
    --access-logfile - \
    --error-logfile - \
    "toms_gym.app:app"

