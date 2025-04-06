#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BACKEND_CONTAINER="toms-gym-backend-local"
BACKEND_PORT=8888

echo -e "${BLUE}=== Setting up local backend for Android testing ===${NC}"

# Cleanup function
cleanup() {
  echo -e "\n${YELLOW}Cleaning up existing containers...${NC}"
  docker rm -f $BACKEND_CONTAINER 2>/dev/null || true
}

# Clean up on script exit
trap cleanup EXIT

# Initial cleanup
cleanup

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
  echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
  exit 1
fi

# Find Google Cloud credentials
CREDENTIALS_FILE=""
if [ -f "$HOME/.config/gcloud/application_default_credentials.json" ]; then
  CREDENTIALS_FILE="$HOME/.config/gcloud/application_default_credentials.json"
  echo -e "${GREEN}Found Google Cloud credentials at $CREDENTIALS_FILE${NC}"
elif [ -f "$HOME/.config/gcloud/legacy_credentials/$(whoami)/adc.json" ]; then
  CREDENTIALS_FILE="$HOME/.config/gcloud/legacy_credentials/$(whoami)/adc.json"
  echo -e "${GREEN}Found Google Cloud credentials at $CREDENTIALS_FILE${NC}"
elif [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
  CREDENTIALS_FILE="$GOOGLE_APPLICATION_CREDENTIALS"
  echo -e "${GREEN}Using Google Cloud credentials from GOOGLE_APPLICATION_CREDENTIALS: $CREDENTIALS_FILE${NC}"
else
  echo -e "${YELLOW}⚠️  No Google Cloud credentials found. Creating mock credentials...${NC}"
  mkdir -p /tmp/mock-credentials
  echo '{
    "type": "service_account",
    "project_id": "toms-gym",
    "private_key_id": "mock",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7VJTUt9Us8cKj\nMzEfYyjiWA4R4/M2bS1GB4t7NXp98C3SC6dVMvDuictGeurT8jNbvJZHtCSuYEvu\nNMoSfm76oqFvAp8Gy0iz5sxjZmSnXyCdPEovGhLa0VzMaQ8s+CLOyS56YyCFGeJZ\n-----END PRIVATE KEY-----\n",
    "client_email": "mock@toms-gym.iam.gserviceaccount.com",
    "client_id": "000000000000000000000",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/mock%40toms-gym.iam.gserviceaccount.com"
  }' > /tmp/mock-credentials/mock-credentials.json
  CREDENTIALS_FILE="/tmp/mock-credentials/mock-credentials.json"
fi

# Build the backend container
echo -e "\n${BLUE}Building backend Docker container...${NC}"
docker build -t toms-gym-backend-local -f Backend/Dockerfile ./Backend

if [ $? -ne 0 ]; then
  echo -e "${RED}❌ Backend build failed. Check the Docker build logs above.${NC}"
  exit 1
fi

# Run the backend container
echo -e "\n${BLUE}Starting backend container on port ${BACKEND_PORT}...${NC}"
docker run -d --name $BACKEND_CONTAINER \
  -p ${BACKEND_PORT}:8080 \
  -e "DATABASE_URL=sqlite:///test.db" \
  -e "GCS_BUCKET=jtr-lift-u-4ever-cool-bucket" \
  -e "GOOGLE_APPLICATION_CREDENTIALS=/credentials/credentials.json" \
  -v "${CREDENTIALS_FILE}:/credentials/credentials.json:ro" \
  -e "GOOGLE_CLOUD_PROJECT=toms-gym" \
  -e "FLASK_ENV=development" \
  -e "FLASK_DEBUG=1" \
  -e "USE_MOCK_DB=true" \
  toms-gym-backend-local

if [ $? -ne 0 ]; then
  echo -e "${RED}❌ Failed to start backend container.${NC}"
  exit 1
fi

# Wait for backend to start
echo -e "\n${YELLOW}Waiting for backend to start...${NC}"
sleep 10  # Give more time to start

# Test backend health
echo -e "\n${BLUE}Testing backend health...${NC}"
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${BACKEND_PORT}/health)

if [ $HEALTH_STATUS -eq 200 ]; then
  echo -e "${GREEN}✅ Backend is running and healthy${NC}"
else
  echo -e "${RED}❌ Backend health check failed with status ${HEALTH_STATUS}${NC}"
  echo -e "${YELLOW}Showing backend logs:${NC}"
  docker logs $BACKEND_CONTAINER
  echo -e "\n${YELLOW}Trying a different endpoint...${NC}"
  
  # Try the random-video endpoint as fallback
  RANDOM_VIDEO_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${BACKEND_PORT}/random-video)
  if [ $RANDOM_VIDEO_STATUS -ge 200 ] && [ $RANDOM_VIDEO_STATUS -lt 300 ]; then
    echo -e "${GREEN}✅ Backend is running (random-video endpoint works)${NC}"
  else
    echo -e "${RED}❌ Backend is not responding correctly. Exiting tests.${NC}"
    exit 1
  fi
fi

# Run Android tests against local backend
echo -e "\n${BLUE}Running Android tests against local backend...${NC}"
cd tests && TEST_API_URL="http://localhost:${BACKEND_PORT}" ./android-test.sh

# If --keep flag is used, keep the container running
if [ "$1" == "--keep" ]; then
  echo -e "\n${GREEN}Local backend container is running at http://localhost:${BACKEND_PORT}${NC}"
  echo -e "${YELLOW}Container will remain running for manual testing.${NC}"
  echo -e "${BLUE}Try these test endpoints:${NC}"
  echo -e "  - http://localhost:${BACKEND_PORT}/health"
  echo -e "  - http://localhost:${BACKEND_PORT}/random-video"
  echo -e "To stop the container later, run: ${BLUE}docker rm -f $BACKEND_CONTAINER${NC}"
  
  # Remove the cleanup trap so container stays running
  trap - EXIT
  exit 0
fi

echo -e "\n${GREEN}Tests completed. Local backend container will be removed.${NC}" 