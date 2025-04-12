#!/bin/bash

set -e  # Exit on any error

# Default test API URL
API_URL=${TEST_API_URL:-"http://localhost:5000"}
FRONTEND_URL=${TEST_FRONTEND_URL:-"http://localhost:3000"}
TEST_EMAIL="test-oauth@example.com"

echo "🧪 Running OAuth authentication tests..."
echo "API URL: $API_URL"
echo "Frontend URL: $FRONTEND_URL"

# Make sure test directories exist
mkdir -p test-results
mkdir -p screenshots

# Function to log test steps
log_step() {
  echo -e "\n🔍 $1"
}

# Function to handle errors
handle_error() {
  echo -e "\n❌ $1"
  exit 1
}

# Test OAuth endpoints existence
log_step "Testing OAuth endpoints existence"

# Test Google login endpoint
GOOGLE_LOGIN_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/auth/google/login")
if [ "$GOOGLE_LOGIN_RESPONSE" -ge 200 ] && [ "$GOOGLE_LOGIN_RESPONSE" -lt 400 ]; then
  echo "✅ Google login endpoint is available"
else
  handle_error "Google login endpoint returned status $GOOGLE_LOGIN_RESPONSE"
fi

# Test OAuth callback endpoint
CALLBACK_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/auth/callback")
if [ "$CALLBACK_RESPONSE" -ge 200 ] && [ "$CALLBACK_RESPONSE" -lt 400 ]; then
  echo "✅ OAuth callback endpoint is available"
else
  handle_error "OAuth callback endpoint returned status $CALLBACK_RESPONSE"
fi

# Test mock OAuth flow (only in dev/test environment)
log_step "Testing mock OAuth flow with test credentials"

# Generate a test token
TEST_TOKEN=$(openssl rand -hex 16)
TEST_USER_ID="test-oauth-user-123"

# Call the mock callback endpoint
MOCK_RESPONSE=$(curl -s -X POST "$API_URL/auth/mock/callback" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"name\":\"Test OAuth User\"}")

if [[ "$MOCK_RESPONSE" == *"token"* ]] && [[ "$MOCK_RESPONSE" == *"user_id"* ]]; then
  echo "✅ Mock OAuth callback returns token and user ID"
  
  # Extract token and user_id from response
  MOCK_TOKEN=$(echo $MOCK_RESPONSE | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
  MOCK_USER_ID=$(echo $MOCK_RESPONSE | grep -o '"user_id":"[^"]*"' | cut -d'"' -f4)
  
  # Test user profile endpoint with the token
  USER_RESPONSE=$(curl -s -H "Authorization: Bearer $MOCK_TOKEN" "$API_URL/auth/user")
  if [[ "$USER_RESPONSE" == *"user"* ]] && [[ "$USER_RESPONSE" == *"$TEST_EMAIL"* ]]; then
    echo "✅ Authentication token works for fetching user profile"
  else
    handle_error "Failed to fetch user profile with token"
  fi
else
  handle_error "Mock OAuth callback failed"
fi

# Run browser-based tests if Puppeteer is available
if command -v node &> /dev/null; then
  log_step "Running browser-based OAuth tests with Puppeteer"
  
  # Create a temporary test script
  cat << EOF > oauth-browser-test.js
const puppeteer = require('puppeteer');
const fs = require('fs');

(async () => {
  console.log('Starting browser-based OAuth test...');
  const browser = await puppeteer.launch({ 
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  
  try {
    // Set viewport and user agent
    await page.setViewport({ width: 1280, height: 800 });
    await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/96.0.4664.110 Safari/537.36');
    
    // Navigate to homepage
    console.log('Navigating to frontend URL...');
    await page.goto('${FRONTEND_URL}');
    await page.screenshot({ path: 'screenshots/01-homepage.png' });
    
    // Look for the login button
    console.log('Looking for login elements...');
    const loginButton = await page.waitForSelector('span:has-text("Login")', { timeout: 10000 });
    await loginButton.click();
    
    // Wait for login modal
    await page.waitForSelector('div[role="dialog"]', { timeout: 5000 });
    await page.screenshot({ path: 'screenshots/02-login-modal.png' });
    
    // Click Google login button
    const googleButton = await page.waitForSelector('button:has-text("Sign in with Google")');
    console.log('Clicking Google login button...');
    await googleButton.click();
    
    // We expect to be redirected to Google's auth page in a production environment
    // In a test environment, we might have a mock OAuth page
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'screenshots/03-redirect.png' });
    
    console.log('OAuth redirect flow initiated successfully');
  } catch (error) {
    console.error('Browser test error:', error);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
EOF

  # Check if Puppeteer is installed, install if needed
  if ! npm list -g puppeteer &> /dev/null; then
    echo "Installing Puppeteer for browser tests..."
    npm install -g puppeteer
  fi
  
  # Run the test
  node oauth-browser-test.js || handle_error "Browser-based test failed"
  echo "✅ Browser-based OAuth tests completed"
  
  # Clean up
  rm oauth-browser-test.js
else
  echo "⚠️ Node.js not found, skipping browser-based tests"
fi

echo -e "\n✅ OAuth tests completed successfully!"
exit 0 