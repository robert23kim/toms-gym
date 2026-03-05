#!/bin/bash
set -e

# Log startup information
echo "Starting docker-entrypoint.sh"
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"

# Ensure all dependencies are installed
if ! pip show bcrypt >/dev/null 2>&1; then
  echo "Installing bcrypt package..."
  pip install bcrypt==4.1.2
fi

# Wait for PostgreSQL to be ready
wait_for_postgres() {
  local host=${POSTGRES_HOST:-db-test}
  local port=${POSTGRES_PORT:-5432}
  local user=${POSTGRES_USER:-postgres}
  local password=${POSTGRES_PASSWORD:-test}
  local dbname=${POSTGRES_DB:-toms_gym_test}
  local max_attempts=${MAX_DB_WAIT_ATTEMPTS:-30}
  local attempt=0

  echo "Waiting for PostgreSQL at $host:$port to become available..."
  while [ $attempt -lt $max_attempts ]; do
    attempt=$((attempt+1))
    PGPASSWORD=$password pg_isready -h "$host" -p "$port" -U "$user" -d "$dbname" -t 1 > /dev/null 2>&1
    if [ $? -eq 0 ]; then
      echo "PostgreSQL is available!"
      return 0
    fi
    echo "Waiting for PostgreSQL... ($attempt/$max_attempts)"
    sleep 2
  done

  echo "Failed to connect to PostgreSQL after $max_attempts attempts"
  return 1
}

# Check if we're in test mode
if [ "$FLASK_ENV" = "testing" ] || [ "$TEST_MODE" = "true" ]; then
  echo "Running in test mode, initializing test database..."
  
  # Wait for the database
  wait_for_postgres
  
  # Initialize the test database
  echo "Initializing test database schema..."
  python -m tests.init_db
  
  # Log success
  if [ $? -eq 0 ]; then
    echo "✅ Test database initialized successfully"
  else
    echo "❌ Failed to initialize test database"
    exit 1
  fi
elif [ -n "$APPLY_MIGRATIONS" ] && [ "$APPLY_MIGRATIONS" = "true" ]; then
  echo "Applying database migrations..."
  
  # Wait for the database
  wait_for_postgres
  
  # Apply schema
  echo "Applying database schema..."
  if [ -f toms_gym/migrations/schema.sql ]; then
    python apply_migration.py toms_gym/migrations/schema.sql
  elif [ -f toms_gym/migrations/apply_schema.py ]; then
    python toms_gym/migrations/apply_schema.py
  else
    echo "Warning: No schema migration found"
  fi
fi

# Display dependency information for troubleshooting
if [ "$DEBUG" = "true" ]; then
  echo "Installed Python packages:"
  pip list
fi

# Execute command
echo "Running command: $@"
exec "$@" 