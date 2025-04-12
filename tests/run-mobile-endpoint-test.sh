#!/bin/bash

# Mobile Endpoint Test Runner
# This script installs required dependencies and runs the mobile endpoint test

echo "=== Mobile Endpoint Tests ==="
echo "Testing production endpoints with simulated mobile devices"
echo

# Create output directory
OUTPUT_DIR="./test-results"
mkdir -p $OUTPUT_DIR

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed. Please install Node.js to run the tests.${NC}"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is not installed. Please install npm to run the tests.${NC}"
    exit 1
fi

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
npm install

# Make the script executable
chmod +x mobile-endpoint-test.js

echo -e "${GREEN}Running mobile endpoint tests...${NC}"
node mobile-endpoint-test.js

# Check exit code
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Tests completed successfully!${NC}"
    
    # Find the latest test report
    LATEST_REPORT=$(find ./test-results -name 'mobile-test-report.html' -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -f2- -d" ")
    
    if [ -n "$LATEST_REPORT" ]; then
        echo -e "${GREEN}Opening test report: $LATEST_REPORT${NC}"
        if command -v open &> /dev/null; then
            open "$LATEST_REPORT"
        elif command -v xdg-open &> /dev/null; then
            xdg-open "$LATEST_REPORT"
        else
            echo -e "${YELLOW}Please open the report manually: $LATEST_REPORT${NC}"
        fi
    else
        echo -e "${YELLOW}Test report not found${NC}"
    fi
else
    echo -e "${RED}Tests failed!${NC}"
fi 