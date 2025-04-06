#!/bin/bash

# Define colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print banner
echo -e "${GREEN}"
echo "===================================="
echo "   Tom's Gym - Development Setup"
echo "===================================="
echo -e "${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker is not installed. Please install Docker to continue.${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo -e "${YELLOW}Docker is not running. Please start Docker to continue.${NC}"
    exit 1
fi

# Function to check if a container is running
is_container_running() {
    docker ps --format '{{.Names}}' | grep -q "$1"
    return $?
}

# Stop any existing containers
echo -e "${BLUE}Stopping any existing containers...${NC}"
if is_container_running "toms-gym"; then
    docker-compose down
fi

# Check and stop individual containers
for container in "toms-gym-backend" "toms-gym-frontend" "toms-gym-test-server"; do
    if is_container_running "$container"; then
        echo "Stopping $container..."
        docker stop "$container" > /dev/null
        docker rm "$container" > /dev/null
    fi
done

# Check backend container running separately
if is_container_running "toms-gym-backend-local"; then
    echo "Stopping toms-gym-backend-local..."
    docker stop "toms-gym-backend-local" > /dev/null
    docker rm "toms-gym-backend-local" > /dev/null
fi

# Start the application using Docker Compose
echo -e "${BLUE}Starting the development environment...${NC}"
docker-compose up -d

# Wait a moment for containers to start
echo -e "${BLUE}Waiting for services to initialize...${NC}"
sleep 5

# Check if containers are running
echo -e "${BLUE}Checking service status...${NC}"
docker-compose ps

# Print success message with URLs
echo -e "${GREEN}"
echo "===================================="
echo "   Development Environment Ready"
echo "===================================="
echo -e "${NC}"
echo -e "Backend: ${GREEN}http://localhost:8888${NC}"
echo -e "Frontend: ${GREEN}http://localhost:8081${NC}" 
echo -e "Test server: ${GREEN}http://localhost:8000${NC}"
echo ""
echo -e "${YELLOW}To view logs:${NC} docker-compose logs -f"
echo -e "${YELLOW}To stop:${NC} docker-compose down"
echo "" 