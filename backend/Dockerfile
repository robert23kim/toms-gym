# Build stage
FROM python:3.10-slim AS build

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM python:3.10-slim AS development

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy from build stage
COPY --from=build /usr/local/lib/python3.10/site-packages/ /usr/local/lib/python3.10/site-packages/
COPY --from=build /usr/local/bin/ /usr/local/bin/

# Install additional development dependencies
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Set Python path
ENV PYTHONPATH=/app

# Copy the entrypoint script and make it executable
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]

# Copy application code
COPY . .

# Production stage
FROM python:3.10-slim AS production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy from build stage
COPY --from=build /usr/local/lib/python3.10/site-packages/ /usr/local/lib/python3.10/site-packages/
COPY --from=build /usr/local/bin/ /usr/local/bin/

# Set Python path
ENV PYTHONPATH=/app

# Copy the entrypoint script and make it executable
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]

# Copy application code
COPY . .

# Run the application
# Worker timeout must exceed the Cloud Tasks analysis-job hold: the /jobs
# handlers wait up to 620s for bowling-service, and dispatch_deadline is 900s.
# At 300s gunicorn killed workers mid-analysis (503) on large raw videos.
# gthread with 2x8 threads: the default single sync worker serialized ALL
# requests behind an in-flight analysis hold, stalling the whole API for the
# duration of the job.
CMD ["gunicorn", "-b", "0.0.0.0:8080", "--workers", "2", "--threads", "8", "--worker-class", "gthread", "--timeout", "900", "--graceful-timeout", "900", "toms_gym.wsgi:app"]
