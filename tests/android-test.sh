#!/bin/bash

# Android Phone Test Simulator
# This script tests the application as if it were accessed from an Android device

# Define colors for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Android device details
DEVICE="Pixel5"
ANDROID_VERSION="11"
CHROME_VERSION="90.0.4430.91"
USER_AGENT="Mozilla/5.0 (Linux; Android ${ANDROID_VERSION}; ${DEVICE}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${CHROME_VERSION} Mobile Safari/537.36"

# URLs - can be overridden by environment variables
API_URL=${TEST_API_URL:-"https://my-python-backend-quyiiugyoq-ue.a.run.app"}
FRONTEND_URL=${TEST_FRONTEND_URL:-"https://storage.googleapis.com/toms-gym.appspot.com/index.html"}

# Check if testing against localhost
IS_LOCAL_TEST=false
if [[ $API_URL == *"localhost"* ]] || [[ $API_URL == *"127.0.0.1"* ]]; then
  IS_LOCAL_TEST=true
  echo "🔍 Testing against local backend: $API_URL"
else
  echo "🔍 Testing against remote backend: $API_URL"
fi

# Create test results directory
TEST_RESULTS_DIR="./test-results/android-${DEVICE}"
mkdir -p "${TEST_RESULTS_DIR}"

# Print test info
echo "=== Android Phone Test (${DEVICE}) ==="
echo "Testing application with Android ${ANDROID_VERSION} / Chrome ${CHROME_VERSION}"
echo "API URL: ${API_URL}"
echo "Test results will be saved to: ${TEST_RESULTS_DIR}"
echo -e "\n"
echo "Starting Android tests..."

# Function to run a curl command with Android user agent and save output
run_curl_test() {
    local url=$1
    local output_file=$2
    local method=${3:-"GET"}
    local extra_headers=${4:-""}
    local extra_args=${5:-""}
    local timeout=${6:-"10"}
    
    echo -e "\nTesting ${method} ${url}"
    
    # Add extra options for local testing
    local curl_opts=""
    if [ "$IS_LOCAL_TEST" = true ]; then
        curl_opts="--insecure"  # Skip SSL verification for localhost
    fi
    
    # Save headers separately
    status_code=$(curl -s -o "${output_file}" -w "%{http_code}" \
        -X "${method}" \
        -H "User-Agent: ${USER_AGENT}" \
        ${extra_headers:+-H "${extra_headers}"} \
        -D "${output_file}.headers" \
        ${extra_args} \
        --max-time $timeout \
        $curl_opts \
        "${url}")
    
    if [[ $status_code -ge 200 && $status_code -lt 300 ]]; then
        echo -e "✓ ${method} request succeeded (${status_code})"
        
        # If successful response has content, show a preview
        if [ -s "${output_file}" ]; then
            echo "Response preview:"
            head -5 "${output_file}" | sed 's/^/  /'
            
            # Check content type
            content_type=$(grep -i "Content-Type:" "${output_file}.headers" | cut -d' ' -f2- | tr -d '\r')
            if [ -n "$content_type" ]; then
                echo "Content type: $content_type"
            fi
        fi
        
        return 0
    else
        echo -e "✗ ${method} request failed (${status_code})"
        
        # If the response contains error details, show them
        if [ -s "${output_file}" ]; then
            echo "Error response:"
            cat "${output_file}" | sed 's/^/  /'
        fi
        
        return 1
    fi
}

# Test API health endpoint
echo -e "\n=== Testing API Access ==="
run_curl_test "${API_URL}/health" "${TEST_RESULTS_DIR}/health.json"

# Test random video endpoint
echo -e "\n=== Testing Random Video Endpoint ==="
if run_curl_test "${API_URL}/random-video" "${TEST_RESULTS_DIR}/random-video.json"; then
    # Extract video URL from response
    VIDEO_URL=$(grep -o 'https://storage.googleapis.com[^\"]*' "${TEST_RESULTS_DIR}/random-video.json" | head -1)
    
    if [[ ! -z "${VIDEO_URL}" ]]; then
        echo "Video URL: ${VIDEO_URL}"
        
        # Extract video path from GCS URL
        VIDEO_PATH=$(echo "${VIDEO_URL}" | sed 's|https://storage.googleapis.com/jtr-lift-u-4ever-cool-bucket/||')
        
        # Test direct access to video
        echo -e "\n=== Testing Direct Video Access ==="
        run_curl_test "${VIDEO_URL}" "${TEST_RESULTS_DIR}/direct-video.bin" "GET" "" "-r 0-1024"
        
        # Test video proxy endpoint
        echo -e "\n=== Testing Video Proxy Endpoint ==="
        run_curl_test "${API_URL}/video/${VIDEO_PATH}?mobile=true" "${TEST_RESULTS_DIR}/proxy-video.bin"
        
        # Test video playback
        echo -e "\n=== Testing Video Playback Simulation ==="
        
        # Test range requests (common with mobile video players)
        echo -e "\n=== Simulating Range Requests ==="
        echo "Requesting first 100KB chunk"
        RANGE_HEADERS="Range: bytes=0-102399"
        curl -s -o "${TEST_RESULTS_DIR}/chunk1.bin" \
            -H "User-Agent: ${USER_AGENT}" \
            -H "${RANGE_HEADERS}" \
            -D "${TEST_RESULTS_DIR}/chunk1.headers" \
            "${VIDEO_URL}"
            
        # Check if range request was accepted
        if grep -q "206 Partial Content" "${TEST_RESULTS_DIR}/chunk1.headers" || grep -q "206" "${TEST_RESULTS_DIR}/chunk1.headers"; then
            echo -e "✓ Range request accepted"
            
            # Show the content range if available
            content_range=$(grep -i "Content-Range:" "${TEST_RESULTS_DIR}/chunk1.headers" | cut -d' ' -f2- | tr -d '\r')
            if [ -n "$content_range" ]; then
                echo "Content range: $content_range"
            fi
        else
            echo -e "✗ Range request not accepted"
            echo "Server response headers:"
            cat "${TEST_RESULTS_DIR}/chunk1.headers"
        fi
    else
        echo "No video URL found in response. Full response:"
        cat "${TEST_RESULTS_DIR}/random-video.json"
        
        # Check if the response contains any URL
        ANY_URL=$(grep -o 'http[s]*://[^\"]*' "${TEST_RESULTS_DIR}/random-video.json" | head -1)
        if [[ ! -z "${ANY_URL}" ]]; then
            echo "Found alternative URL in response: ${ANY_URL}"
            
            # Try using this URL
            echo -e "\n=== Testing Alternative Video URL ==="
            run_curl_test "${ANY_URL}" "${TEST_RESULTS_DIR}/alt-video.bin" "GET" "" "-r 0-1024"
        fi
    fi
else
    echo "Failed to retrieve random video. Trying a fallback approach."
    run_curl_test "${API_URL}/next-video" "${TEST_RESULTS_DIR}/next-video.json"
fi

# Generate test report
echo -e "\n=== Test Summary ==="
echo "Test results saved to: ${TEST_RESULTS_DIR}"
echo "To view the html test report, run:"
echo "  open ${TEST_RESULTS_DIR}/android-test-report.html"

# Create simple HTML report
cat > "${TEST_RESULTS_DIR}/android-test-report.html" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Android Test Report - ${DEVICE}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        .success { color: green; }
        .failure { color: red; }
        pre { background-color: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto; }
        .test-result { margin-bottom: 20px; border: 1px solid #ddd; border-radius: 5px; overflow: hidden; }
        .test-header { background-color: #f0f0f0; padding: 10px; border-bottom: 1px solid #ddd; }
        .test-content { padding: 10px; }
    </style>
</head>
<body>
    <h1>Android Test Report - ${DEVICE}</h1>
    <p>Test Date: $(date)</p>
    <p>Android Version: ${ANDROID_VERSION}</p>
    <p>Chrome Version: ${CHROME_VERSION}</p>
    <p>API URL: ${API_URL}</p>
    
    <h2>Test Results</h2>
    
    <div class="test-result">
        <div class="test-header">API Health</div>
        <div class="test-content">
            Status: $(if [ -f "${TEST_RESULTS_DIR}/health.json" ]; then echo "<span class='success'>Success</span>"; else echo "<span class='failure'>Failed</span>"; fi)
            <pre>$(cat "${TEST_RESULTS_DIR}/health.json" 2>/dev/null || echo "No data available")</pre>
        </div>
    </div>
    
    <div class="test-result">
        <div class="test-header">Random Video Endpoint</div>
        <div class="test-content">
            Status: $(if [ -f "${TEST_RESULTS_DIR}/random-video.json" ]; then echo "<span class='success'>Success</span>"; else echo "<span class='failure'>Failed</span>"; fi)
            <pre>$(cat "${TEST_RESULTS_DIR}/random-video.json" 2>/dev/null || echo "No data available")</pre>
        </div>
    </div>
    
    <div class="test-result">
        <div class="test-header">Direct Video Access</div>
        <div class="test-content">
            Status: $(if [ -f "${TEST_RESULTS_DIR}/direct-video.bin" ]; then echo "<span class='success'>Success</span>"; else echo "<span class='failure'>Failed</span>"; fi)
            <p>Size: $(du -h "${TEST_RESULTS_DIR}/direct-video.bin" 2>/dev/null | cut -f1 || echo "N/A")</p>
            <pre>$(cat "${TEST_RESULTS_DIR}/direct-video.bin.headers" 2>/dev/null || echo "No headers available")</pre>
        </div>
    </div>
    
    <div class="test-result">
        <div class="test-header">Video Proxy</div>
        <div class="test-content">
            Status: $(if [ -f "${TEST_RESULTS_DIR}/proxy-video.bin" ]; then echo "<span class='success'>Success</span>"; else echo "<span class='failure'>Failed</span>"; fi)
            <p>Size: $(du -h "${TEST_RESULTS_DIR}/proxy-video.bin" 2>/dev/null | cut -f1 || echo "N/A")</p>
            <pre>$(cat "${TEST_RESULTS_DIR}/proxy-video.bin.headers" 2>/dev/null || echo "No headers available")</pre>
        </div>
    </div>
    
    <div class="test-result">
        <div class="test-header">Range Request</div>
        <div class="test-content">
            Status: $(if grep -q "206" "${TEST_RESULTS_DIR}/chunk1.headers" 2>/dev/null; then echo "<span class='success'>Success</span>"; else echo "<span class='failure'>Failed</span>"; fi)
            <pre>$(cat "${TEST_RESULTS_DIR}/chunk1.headers" 2>/dev/null || echo "No headers available")</pre>
        </div>
    </div>
</body>
</html>
EOF

echo "Test completed!" 