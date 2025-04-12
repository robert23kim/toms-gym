#!/bin/bash

# Script to run the database migrations against the GCP project toms-gym
# Usage: ./run_gcp_migration.sh [--drop-tables]

set -e

# Default values
GCP_PROJECT="toms-gym"
GCP_REGION="us-east1"
DB_NAME="postgres"
DB_USER="postgres"
DROP_TABLES="false"

# Check for command line arguments
if [[ "$1" == "--drop-tables" ]]; then
  DROP_TABLES="true"
  echo "⚠️ Tables will be dropped and recreated"
fi

# Check if credentials file exists
CREDENTIALS_FILE="../credentials.json"
if [[ -f "$CREDENTIALS_FILE" ]]; then
  export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/$CREDENTIALS_FILE"
  echo "✅ Using credentials from $CREDENTIALS_FILE"
else
  echo "ℹ️ No credentials file found at $CREDENTIALS_FILE"
  echo "ℹ️ Using application default credentials (make sure you're logged in with 'gcloud auth application-default login')"
fi

# Prompt for DB password (never hardcode passwords)
read -sp "Enter database password: " DB_PASS
echo

# Export all required environment variables
export GCP_PROJECT="$GCP_PROJECT"
export GCP_REGION="$GCP_REGION"
export DB_TYPE="postgres"
export DB_USER="$DB_USER"
export DB_PASS="$DB_PASS"
export DB_NAME="$DB_NAME"
export USE_GCP="true"
export DROP_TABLES="$DROP_TABLES"

# Set the correct DB_INSTANCE connection string
export DB_INSTANCE="toms-gym:us-east1:my-db"

echo "🚀 Running schema migration against GCP project: $GCP_PROJECT"
echo "📊 Database: $DB_NAME"
echo "👤 User: $DB_USER"
echo "🌎 Region: $GCP_REGION"
echo "🔌 Instance: $DB_INSTANCE"

# Run the migration script
python toms_gym/migrations/apply_schema.py

echo "✅ Migration completed" 