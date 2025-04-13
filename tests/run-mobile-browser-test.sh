#!/bin/bash

# Mobile Browser Test Runner
# This script runs the mobile browser test to emulate mobile devices and test the frontend and API URL handling

# Set up colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Create output directory
OUTPUT_DIR="./test-results"
mkdir -p $OUTPUT_DIR

echo -e "${BOLD}Starting mobile browser tests...${NC}"
echo "This test uses Puppeteer to emulate mobile browsers and test the frontend code"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
  echo -e "${RED}Error: Node.js is not installed. Please install Node.js to run these tests.${NC}"
  exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
  echo -e "${RED}Error: npm is not installed. Please install npm to run these tests.${NC}"
  exit 1
fi

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
npm install

# Make script executable
chmod +x mobile-browser-test.js

# Run the test with the appropriate flags
if [[ "$*" == *"--show-browser"* ]]; then
  echo -e "${YELLOW}Running tests with visible browser...${NC}"
  node mobile-browser-test.js --show-browser
elif [[ "$*" == *"--local"* ]]; then
  echo -e "${YELLOW}Running tests against local development server...${NC}"
  node mobile-browser-test.js --local
else
  echo -e "${YELLOW}Running tests against production URL...${NC}"
  node mobile-browser-test.js
fi

# Check if the test succeeded
if [ $? -eq 0 ]; then
  echo -e "${GREEN}Mobile browser tests completed successfully!${NC}"
else
  echo -e "${RED}Mobile browser tests failed!${NC}"
  exit 1
fi

# Try to find the latest report and open it
LATEST_REPORT=$(find ./test-results -maxdepth 2 -name 'browser-test-report.html' -type f | sort -r | head -n 1)

if [ -n "$LATEST_REPORT" ]; then
  echo -e "${GREEN}Opening test report: $LATEST_REPORT${NC}"
  
  # Try to open the report with the appropriate command for the OS
  if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open "$LATEST_REPORT"
  elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v xdg-open &> /dev/null; then
      xdg-open "$LATEST_REPORT"
    else
      echo -e "${YELLOW}Please open the report manually: $LATEST_REPORT${NC}"
    fi
  elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    start "$LATEST_REPORT"
  else
    echo -e "${YELLOW}Please open the report manually: $LATEST_REPORT${NC}"
  fi
else
  echo -e "${YELLOW}No test report found.${NC}"
fi

echo -e "${GREEN}Tests completed.${NC}" 