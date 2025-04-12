#!/bin/bash
set -e

# Script to run tests in the Docker environment

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up test environment...${NC}"

# Check if network exists, create if not
if ! docker network inspect toms-gym-test-network >/dev/null 2>&1; then
  echo -e "${YELLOW}Creating Docker network: toms-gym-test-network${NC}"
  docker network create toms-gym-test-network
fi

# Clean up existing containers if they exist
echo -e "${YELLOW}Cleaning up any existing test containers...${NC}"
docker-compose -f ../docker-compose.test.yml down -v 2>/dev/null || true

# Start the test environment
echo -e "${BLUE}Starting test environment...${NC}"
docker-compose -f ../docker-compose.test.yml up -d db-test redis-test

# Wait for database to be ready
echo -e "${BLUE}Waiting for database to be ready...${NC}"
for i in {1..30}; do
  if docker exec toms-gym-db-test pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}Database is ready!${NC}"
    break
  fi
  echo -e "${YELLOW}Waiting for database... ($i/30)${NC}"
  sleep 2
  if [ $i -eq 30 ]; then
    echo -e "${RED}Database failed to start in 60 seconds. Exiting.${NC}"
    docker-compose -f ../docker-compose.test.yml down -v
    exit 1
  fi
done

# Build the backend test image
echo -e "${BLUE}Building backend test image...${NC}"
docker-compose -f ../docker-compose.test.yml build backend-test

# Run the tests
echo -e "${BLUE}Running tests...${NC}"
docker-compose -f ../docker-compose.test.yml run --rm \
  -e POSTGRES_HOST=db-test \
  -e POSTGRES_PORT=5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=toms_gym_test \
  -e TEST_MODE=true \
  -e DEBUG=true \
  -e FLASK_ENV=testing \
  backend-test bash -c "cd /app && python -m pytest -v"

# Capture the exit code
TEST_EXIT_CODE=$?

# Clean up
echo -e "${BLUE}Cleaning up test environment...${NC}"
docker-compose -f ../docker-compose.test.yml down -v

# Report results
if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo -e "${GREEN}✅ All tests passed!${NC}"
else
  echo -e "${RED}❌ Tests failed with exit code $TEST_EXIT_CODE${NC}"
fi

exit $TEST_EXIT_CODE 