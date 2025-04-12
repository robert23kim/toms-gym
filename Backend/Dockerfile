# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM builder as development

# Install development dependencies
RUN pip install --no-cache-dir \
    flask-debugtoolbar \
    pytest \
    pytest-cov \
    black \
    flake8

# Set development environment variables
ENV FLASK_APP=toms_gym/app.py \
    FLASK_ENV=development \
    FLASK_DEBUG=1

# Production stage
FROM python:3.11-slim as production

# Install system dependencies required for bcrypt
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN useradd -m -u 1000 appuser
USER appuser

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Set production environment variables
ENV FLASK_APP=toms_gym/app.py \
    FLASK_ENV=production \
    FLASK_DEBUG=0 \
    PORT=8080

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "toms_gym.app:app"]

