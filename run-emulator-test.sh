#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Setting up for Android Emulator Testing ===${NC}"

# Check if adb is installed
if ! command -v adb &> /dev/null; then
    echo -e "${RED}Error: ADB (Android Debug Bridge) is not installed.${NC}"
    echo "Please install Android Studio or the Android SDK tools."
    exit 1
fi

# Check if emulator is running
DEVICE_COUNT=$(adb devices | grep -c "device$")
if [ $DEVICE_COUNT -eq 0 ]; then
    echo -e "${RED}Error: No Android devices/emulators found.${NC}"
    echo "Please start an Android emulator first and try again."
    exit 1
fi

echo -e "${YELLOW}Found ${DEVICE_COUNT} Android device(s)/emulator(s)${NC}"
adb devices

# Setup port forwarding to allow emulator to access localhost services
echo -e "\n${BLUE}Setting up port forwarding...${NC}"
adb reverse tcp:8888 tcp:8888
adb reverse tcp:8081 tcp:8081
echo -e "${GREEN}Port forwarding setup complete.${NC}"
echo "Backend will be accessible at: http://localhost:8888"
echo "Frontend will be accessible at: http://localhost:8081"

# Check if backend container is already running
BACKEND_RUNNING=$(docker ps | grep -c "toms-gym-backend-local")
if [ $BACKEND_RUNNING -eq 0 ]; then
    echo -e "\n${BLUE}Starting backend container...${NC}"
    ./run-local-backend.sh --keep &
    BACKEND_PID=$!
    # Wait for backend to start
    echo "Waiting for backend to start..."
    sleep 10
else
    echo -e "\n${GREEN}Backend already running.${NC}"
fi

# Start frontend with emulator configuration
echo -e "\n${BLUE}Starting frontend with emulator configuration...${NC}"
cd my-frontend && VITE_USER_NODE_ENV=emulator npm run dev

# Cleanup
echo -e "\n${BLUE}Cleaning up...${NC}"
adb reverse --remove-all
echo "Test completed." 