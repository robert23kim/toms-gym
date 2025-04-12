#!/bin/bash

set -e  # Exit on any error

echo "🧪 Running Hybrid Authentication Tests..."

# Function to log test steps
log_step() {
    echo -e "\n🔍 $1"
}

# Function to handle errors
handle_error() {
    echo -e "\n❌ $1"
    exit 1
}

# Check if Python and required packages are installed
log_step "Checking dependencies"
python3 -c "import pytest, requests" 2>/dev/null || {
    echo "Installing required Python packages..."
    pip3 install pytest requests
}

# Start Docker containers if not running
log_step "Checking Docker containers"
if ! docker-compose ps | grep -q "backend"; then
    echo "Starting Docker containers..."
    docker-compose up -d
    # Wait for services to be ready
    sleep 10
fi

# Run the tests
log_step "Running authentication tests"
python3 -m pytest auth_test_suite.py -v

# Check test results
if [ $? -eq 0 ]; then
    echo -e "\n✅ All authentication tests passed!"
else
    handle_error "Some authentication tests failed"
fi

# Cleanup (optional)
# docker-compose down 