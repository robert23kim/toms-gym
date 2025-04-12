#!/bin/bash

# Mobile Video Playback Test Runner for Android Only
# This script runs the Android tests against a local backend container

echo "=== Mobile Video Playback Tests (Android Only) ==="
echo "Testing backend video serving for mobile devices"
echo

# Create test output directory
OUTPUT_DIR="./test-results"
mkdir -p $OUTPUT_DIR

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Test configurations - use environment variable if set, otherwise use default
API_URL="${TEST_API_URL:-http://localhost:8085}"
FRONTEND_URL="http://localhost:3000"

# Mobile User Agents
ANDROID_UA="Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36"

# Function to run curl with specific user agent
run_curl() {
    local url=$1
    local user_agent=$2
    local device_name=$3
    local output_file="$OUTPUT_DIR/${device_name}-$(echo $url | md5sum | cut -d' ' -f1).json"
    
    echo -e "${YELLOW}Testing $url as $device_name${NC}"
    
    # Run curl with the user agent and write output
    STATUS=$(curl -s -o $output_file -w "%{http_code}" \
        -H "User-Agent: $user_agent" \
        -H "Accept: application/json" \
        "$url")
    
    if [[ $STATUS -ge 200 && $STATUS -lt 300 ]]; then
        echo -e "${GREEN}✓ Test passed with status $STATUS${NC}"
        return 0
    else
        echo -e "${RED}✗ Test failed with status $STATUS${NC}"
        return 1
    fi
}

# Function to test random video endpoint
test_random_video() {
    local device_name=$1
    local user_agent=$2
    
    echo
    echo "=== Testing Random Video for $device_name ==="
    
    # Get random video
    output_file="$OUTPUT_DIR/$device_name-random-video.json"
    STATUS=$(curl -s -o $output_file -w "%{http_code}" \
        -H "User-Agent: $user_agent" \
        -H "Accept: application/json" \
        "$API_URL/random-video")
    
    if [[ $STATUS -ge 200 && $STATUS -lt 300 ]]; then
        echo -e "${GREEN}✓ Random video request successful with status $STATUS${NC}"
        
        # Extract video URL using jq (install with: apt-get install jq or brew install jq)
        if command -v jq &> /dev/null; then
            VIDEO_URL=$(jq -r '.video_url' "$output_file")
        else
            # Fallback to grep if jq is not available
            VIDEO_URL=$(grep -o '"video_url":"[^"]*"' "$output_file" | cut -d'"' -f4)
        fi
        
        echo "Video URL: $VIDEO_URL"
        
        if [[ ! -z "$VIDEO_URL" ]]; then
            # Test video URL directly
            echo
            echo "Testing direct video URL access..."
            run_curl "$VIDEO_URL" "$user_agent" "$device_name-direct"
            
            # Extract path for proxy test
            if [[ $VIDEO_URL == *"jtr-lift-u-4ever-cool-bucket"* ]]; then
                VIDEO_PATH=$(echo $VIDEO_URL | grep -o 'jtr-lift-u-4ever-cool-bucket/[^"]*' | cut -d'/' -f2-)
                
                if [[ ! -z "$VIDEO_PATH" ]]; then
                    echo
                    echo "Testing video proxy endpoint..."
                    PROXY_URL="$API_URL/video/$(echo -n $VIDEO_PATH | jq -sRr @uri)?mobile=true"
                    run_curl "$PROXY_URL" "$user_agent" "$device_name-proxy"
                fi
            fi
        else
            echo -e "${RED}✗ No video URL found in response${NC}"
        fi
    else
        echo -e "${RED}✗ Random video request failed with status $STATUS${NC}"
    fi
}

# Generate HTML test report
generate_report() {
    local report_file="$OUTPUT_DIR/test-report.html"
    
    echo "Generating test report at $report_file"
    
    cat > $report_file << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Mobile Video Playback Test Results</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        .pass { color: green; }
        .fail { color: red; }
        pre { background: #f5f5f5; padding: 10px; border-radius: 5px; overflow: auto; }
        .test-section { margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>Mobile Video Playback Test Results</h1>
    <p>Tests run at $(date)</p>
    
    <div class="test-section">
        <h2>Test Environment</h2>
        <p><strong>API URL:</strong> $API_URL</p>
        <p><strong>Frontend URL:</strong> $FRONTEND_URL</p>
    </div>
    
    <div class="test-section">
        <h2>Test Results</h2>
        <pre>$(cat $OUTPUT_DIR/test-log.txt || echo "No log file found")</pre>
    </div>
    
    <div class="test-section">
        <h2>Response Samples</h2>
EOF
    
    # Add all JSON files as samples
    for file in $OUTPUT_DIR/*.json; do
        if [ -f "$file" ]; then
            filename=$(basename $file)
            cat >> $report_file << EOF
        <h3>$filename</h3>
        <pre>$(cat $file)</pre>
EOF
        fi
    done
    
    # Close HTML
    cat >> $report_file << EOF
    </div>
</body>
</html>
EOF
    
    echo "Report generated at $report_file"
}

# Run tests
echo "Starting mobile video playback tests (Android only)..."

# Create test log
TEST_LOG="$OUTPUT_DIR/test-log.txt"
echo "Mobile Video Playback Tests (Android only) started at $(date)" > $TEST_LOG

# Test with Android
echo
echo "=== Android Tests ==="
test_random_video "android" "$ANDROID_UA" | tee -a $TEST_LOG

# Generate HTML test report
generate_report

echo
echo "=== Tests completed ==="
echo "Results saved to $OUTPUT_DIR"
echo "Run 'open $OUTPUT_DIR/test-report.html' to view the test report" 