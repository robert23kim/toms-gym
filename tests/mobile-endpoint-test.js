#!/usr/bin/env node

/**
 * Mobile Endpoint Test Script
 * 
 * This script emulates various mobile devices to test the production endpoints,
 * focusing primarily on the random-video endpoint and video playback.
 * 
 * Run with: node mobile-endpoint-test.js
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');

// Configuration - Production endpoints
const API_URL = 'https://my-python-backend-quyiiugyoq-ue.a.run.app';
const FRONTEND_URL = 'https://my-frontend-quyiiugyoq-ue.a.run.app';
const OUTPUT_DIR = path.join(__dirname, 'test-results', 'mobile-tests-' + new Date().toISOString().replace(/:/g, '-'));

// Create output directory if it doesn't exist
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// Mobile User Agents
const MOBILE_DEVICES = {
  iPhone: {
    name: 'iPhone 13',
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
    viewportWidth: 390,
    viewportHeight: 844,
    pixelRatio: 3
  },
  androidPhone: {
    name: 'Google Pixel 6',
    userAgent: 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Mobile Safari/537.36',
    viewportWidth: 412,
    viewportHeight: 915,
    pixelRatio: 2.625
  },
  iPad: {
    name: 'iPad Pro',
    userAgent: 'Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
    viewportWidth: 1024,
    viewportHeight: 1366,
    pixelRatio: 2
  },
  android10Chrome: {
    name: 'Android 10 Chrome',
    userAgent: 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36',
    viewportWidth: 412,
    viewportHeight: 915,
    pixelRatio: 2.625
  },
  linuxChrome: {
    name: 'Linux Chrome',
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    viewportWidth: 1920,
    viewportHeight: 1080,
    pixelRatio: 1
  }
};

// Log function with timestamps
function log(message, type = 'info') {
  const timestamp = new Date().toISOString();
  const colored = type === 'error' 
    ? `\x1b[31m${message}\x1b[0m` // Red for errors
    : type === 'success' 
      ? `\x1b[32m${message}\x1b[0m` // Green for success
      : type === 'warning'
        ? `\x1b[33m${message}\x1b[0m` // Yellow for warnings
        : message;
  
  console.log(`[${timestamp}] ${colored}`);
  
  // Also write to log file
  fs.appendFileSync(
    path.join(OUTPUT_DIR, 'test-log.txt'), 
    `[${timestamp}] [${type.toUpperCase()}] ${message}\n`
  );
}

// Helper to make requests with mobile device emulation
async function makeRequestAsMobileDevice(url, device, method = 'GET', headers = {}, data = null) {
  try {
    log(`Making ${method} request to ${url} as ${device.name}`);
    
    const requestHeaders = {
      'User-Agent': device.userAgent,
      'Accept': 'application/json, text/plain, */*',
      'Accept-Language': 'en-US,en;q=0.9',
      'Viewport-Width': device.viewportWidth.toString(),
      'Referer': FRONTEND_URL,
      'Origin': FRONTEND_URL,
      ...headers
    };
    
    const response = await axios({
      method,
      url,
      headers: requestHeaders,
      data: data,
      validateStatus: () => true, // Don't throw on error status codes
      timeout: 10000 // 10 second timeout
    });
    
    const result = {
      status: response.status,
      headers: response.headers,
      data: response.data,
      success: response.status >= 200 && response.status < 300
    };
    
    if (result.success) {
      log(`Request successful: ${response.status}`, 'success');
    } else {
      log(`Request failed: ${response.status}`, 'error');
    }
    
    // Save response for analysis
    const filename = `${device.name.replace(/\s+/g, '-')}-${new URL(url).pathname.replace(/\//g, '-')}-${method}`;
    fs.writeFileSync(
      path.join(OUTPUT_DIR, `${filename}.json`),
      JSON.stringify({
        url,
        method,
        headers: requestHeaders,
        status: response.status,
        responseHeaders: response.headers,
        data: response.data
      }, null, 2)
    );
    
    return result;
  } catch (error) {
    log(`Request failed: ${error.message}`, 'error');
    return {
      success: false,
      error: error.message
    };
  }
}

// Test the random-video endpoint
async function testRandomVideo(device) {
  log(`\n=== Testing Random Video Endpoint as ${device.name} ===`);
  
  const result = await makeRequestAsMobileDevice(`${API_URL}/random-video`, device);
  
  if (result.success && result.data && result.data.video_url) {
    log(`Retrieved video URL: ${result.data.video_url}`, 'success');
    return result.data.video_url;
  }
  
  log('Failed to retrieve video URL', 'error');
  return null;
}

// Test direct video access
async function testDirectVideoAccess(videoUrl, device) {
  if (!videoUrl) {
    log('No video URL provided', 'error');
    return false;
  }
  
  log(`\n=== Testing Direct Video Access as ${device.name} ===`);
  
  // First check with HEAD request to get content info without downloading the whole video
  const headResult = await makeRequestAsMobileDevice(videoUrl, device, 'HEAD');
  
  if (headResult.success) {
    const contentType = headResult.headers['content-type'] || '';
    const contentLength = headResult.headers['content-length'] || 'unknown';
    
    log(`Content type: ${contentType}`, 'success');
    log(`Content length: ${contentLength} bytes`, 'success');
    
    if (contentType.startsWith('video/')) {
      // Now test a range request to simulate video streaming
      log('Testing range request for video streaming');
      
      const rangeResult = await makeRequestAsMobileDevice(videoUrl, device, 'GET', {
        'Range': 'bytes=0-1023', // Request just the first 1KB
      });
      
      if (rangeResult.success && rangeResult.headers['content-range']) {
        log(`Range request successful: ${rangeResult.headers['content-range']}`, 'success');
        return true;
      } else {
        log('Range request failed or not supported', 'warning');
      }
      
      return true;
    } else {
      log(`Unexpected content type: ${contentType}`, 'warning');
    }
  }
  
  log('Failed to access video directly', 'error');
  return false;
}

// Test video proxy endpoint
async function testVideoProxy(videoUrl, device) {
  if (!videoUrl) {
    log('No video URL provided', 'error');
    return false;
  }
  
  log(`\n=== Testing Video Proxy Endpoint as ${device.name} ===`);
  
  // Extract the video path from the URL
  let videoPath;
  try {
    const url = new URL(videoUrl);
    // Handle Google Cloud Storage URLs
    if (url.hostname.includes('storage.googleapis.com')) {
      const bucketPath = url.pathname.split('/');
      // Remove the first empty element and the bucket name
      bucketPath.shift(); // Remove empty string before first slash
      bucketPath.shift(); // Remove bucket name
      videoPath = bucketPath.join('/');
    } else {
      videoPath = url.pathname.substring(1); // Remove leading slash
    }
  } catch (error) {
    log(`Failed to parse video URL: ${error.message}`, 'error');
    return false;
  }
  
  // Test the proxy endpoint
  const proxyUrl = `${API_URL}/video/${encodeURIComponent(videoPath)}?mobile=true`;
  log(`Testing proxy URL: ${proxyUrl}`);
  
  const result = await makeRequestAsMobileDevice(proxyUrl, device);
  
  // Check if we got a direct response or a redirect
  if (result.success) {
    log('Video proxy access successful', 'success');
    
    // Check content type
    const contentType = result.headers['content-type'] || '';
    log(`Content type: ${contentType}`);
    
    if (contentType.startsWith('video/')) {
      return true;
    } else if (result.headers.location) {
      log(`Proxy redirected to: ${result.headers.location}`, 'success');
      return true;
    } else {
      log('Unexpected content type from proxy', 'warning');
    }
  }
  
  log('Failed to access video through proxy', 'error');
  return false;
}

// Test frontend with mobile user agent
async function testFrontend(device) {
  log(`\n=== Testing Frontend as ${device.name} ===`);
  
  const result = await makeRequestAsMobileDevice(FRONTEND_URL, device);
  
  if (result.success) {
    log('Successfully accessed frontend homepage', 'success');
    
    // Check if we received HTML
    const contentType = result.headers['content-type'] || '';
    if (contentType.includes('text/html')) {
      log('Received valid HTML from frontend', 'success');
      return true;
    } else {
      log(`Unexpected content type: ${contentType}`, 'warning');
    }
  }
  
  return false;
}

// Test challenge page access
async function testChallengePage(device) {
  log(`\n=== Testing Challenge Page as ${device.name} ===`);
  
  const result = await makeRequestAsMobileDevice(`${API_URL}/competitions`, device);
  
  if (result.success) {
    log('Successfully accessed challenges endpoint', 'success');
    
    if (result.data && result.data.competitions) {
      log(`Retrieved ${result.data.competitions.length} challenges`, 'success');
      return result.data.competitions;
    } else {
      log('No challenges found in response', 'warning');
    }
  }
  
  return null;
}

// Test create challenge
async function testCreateChallenge(device) {
  log(`\n=== Testing Create Challenge as ${device.name} ===`);
  
  // Create challenge data
  const challengeData = {
    name: `Mobile Test Challenge ${new Date().toISOString()}`,
    location: "Test Location",
    lifttypes: ["snatch", "clean_and_jerk"],
    weightclasses: ["56kg", "62kg", "69kg"],
    gender: "M",
    start_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 7 days from now
    end_date: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString().split('T')[0] // 14 days from now
  };
  
  // Make the POST request
  const result = await makeRequestAsMobileDevice(
    `${API_URL}/create_competition`, 
    device,
    'POST',
    { 'Content-Type': 'application/json' },
    challengeData
  );
  
  if (result.success) {
    log('Successfully created challenge', 'success');
    log(`Challenge ID: ${result.data.competition_id}`, 'success');
    
    // Verify the challenge was created by fetching it
    if (result.data && result.data.competition_id) {
      const verifyResult = await makeRequestAsMobileDevice(
        `${API_URL}/competitions/${result.data.competition_id}`, 
        device
      );
      
      if (verifyResult.success && verifyResult.data && verifyResult.data.competition) {
        log('Successfully verified created challenge', 'success');
        return {
          created: true,
          challengeId: result.data.competition_id,
          challenge: verifyResult.data.competition
        };
      } else {
        log('Failed to verify created challenge', 'error');
      }
    }
    
    return {
      created: true,
      challengeId: result.data.competition_id
    };
  }
  
  log('Failed to create challenge', 'error');
  if (result.data && result.data.error) {
    log(`Error: ${result.data.error}`, 'error');
  }
  
  return { created: false };
}

// Create HTML report
function generateReport(results) {
  const reportPath = path.join(OUTPUT_DIR, 'mobile-test-report.html');
  log(`\nGenerating test report at ${reportPath}`);
  
  const reportContent = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mobile Endpoint Test Results</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.6;
      color: #333;
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
    }
    h1, h2, h3 {
      color: #2c3e50;
    }
    .success { color: #27ae60; }
    .warning { color: #f39c12; }
    .error { color: #e74c3c; }
    .test-section {
      margin-bottom: 30px;
      padding: 20px;
      border-radius: 8px;
      background: #f9f9f9;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 20px 0;
    }
    th, td {
      text-align: left;
      padding: 12px;
      border-bottom: 1px solid #ddd;
    }
    th {
      background-color: #f2f2f2;
    }
    tr:hover {
      background-color: #f5f5f5;
    }
    .timestamp {
      color: #7f8c8d;
      font-size: 14px;
    }
  </style>
</head>
<body>
  <h1>Mobile Endpoint Test Results</h1>
  <p class="timestamp">Tests run at ${new Date().toLocaleString()}</p>
  
  <div class="test-section">
    <h2>Test Environment</h2>
    <p><strong>API URL:</strong> ${API_URL}</p>
    <p><strong>Frontend URL:</strong> ${FRONTEND_URL}</p>
  </div>
  
  <div class="test-section">
    <h2>Test Results Summary</h2>
    <table>
      <thead>
        <tr>
          <th>Device</th>
          <th>Random Video</th>
          <th>Direct Video</th>
          <th>Video Proxy</th>
          <th>Frontend</th>
          <th>Challenge Page</th>
          <th>Create Challenge</th>
        </tr>
      </thead>
      <tbody>
        ${Object.keys(results).map(deviceKey => {
          const deviceResult = results[deviceKey];
          return `
            <tr>
              <td>${MOBILE_DEVICES[deviceKey].name}</td>
              <td class="${deviceResult.randomVideo ? 'success' : 'error'}">${deviceResult.randomVideo ? '✓ Pass' : '✗ Fail'}</td>
              <td class="${deviceResult.directVideo ? 'success' : 'error'}">${deviceResult.directVideo ? '✓ Pass' : '✗ Fail'}</td>
              <td class="${deviceResult.videoProxy ? 'success' : 'error'}">${deviceResult.videoProxy ? '✓ Pass' : '✗ Fail'}</td>
              <td class="${deviceResult.frontend ? 'success' : 'error'}">${deviceResult.frontend ? '✓ Pass' : '✗ Fail'}</td>
              <td class="${deviceResult.challengePage ? 'success' : 'error'}">${deviceResult.challengePage ? '✓ Pass' : '✗ Fail'}</td>
              <td class="${deviceResult.createChallenge ? 'success' : 'error'}">${deviceResult.createChallenge ? '✓ Pass' : '✗ Fail'}</td>
            </tr>
          `;
        }).join('')}
      </tbody>
    </table>
  </div>
  
  <div class="test-section">
    <h2>Test Log</h2>
    <pre>${fs.existsSync(path.join(OUTPUT_DIR, 'test-log.txt')) ? 
      fs.readFileSync(path.join(OUTPUT_DIR, 'test-log.txt'), 'utf8') : 
      'Log file not found'}</pre>
  </div>
</body>
</html>
  `;
  
  fs.writeFileSync(reportPath, reportContent);
  log(`Report generated at ${reportPath}`, 'success');
  
  return reportPath;
}

// Main test function
async function runTests() {
  log('Starting mobile endpoint tests', 'info');
  log('Output directory: ' + OUTPUT_DIR);
  
  const results = {};
  
  // Test with each device
  for (const [deviceKey, device] of Object.entries(MOBILE_DEVICES)) {
    results[deviceKey] = {
      randomVideo: false,
      directVideo: false,
      videoProxy: false,
      frontend: false,
      challengePage: false,
      createChallenge: false
    };
    
    log(`\n=== Testing with ${device.name} ===`);
    
    // Test frontend
    results[deviceKey].frontend = await testFrontend(device);
    
    // Test random video
    const videoUrl = await testRandomVideo(device);
    results[deviceKey].randomVideo = !!videoUrl;
    
    if (videoUrl) {
      // Test direct video access
      results[deviceKey].directVideo = await testDirectVideoAccess(videoUrl, device);
      
      // Test video proxy
      results[deviceKey].videoProxy = await testVideoProxy(videoUrl, device);
    }
    
    // Test challenge page
    const challenges = await testChallengePage(device);
    results[deviceKey].challengePage = !!challenges;
    
    // Test create challenge - only on one device to avoid creating too many test challenges
    if (deviceKey === 'iPhone') {
      const createResult = await testCreateChallenge(device);
      results[deviceKey].createChallenge = createResult.created;
    } else {
      // Skip challenge creation for other devices
      log('Skipping challenge creation test for this device', 'info');
      results[deviceKey].createChallenge = 'skipped';
    }
  }
  
  // Generate report
  const reportPath = generateReport(results);
  
  log('\n=== Test Summary ===');
  for (const [deviceKey, deviceResults] of Object.entries(results)) {
    log(`${MOBILE_DEVICES[deviceKey].name}:`);
    for (const [test, passed] of Object.entries(deviceResults)) {
      log(`  ${test}: ${passed === 'skipped' ? '⚪ Skipped' : passed ? '✓ Pass' : '✗ Fail'}`, passed === 'skipped' ? 'info' : passed ? 'success' : 'error');
    }
  }
  
  log(`\nAll tests completed. Report available at: ${reportPath}`, 'success');
}

// Run the tests
runTests().catch(error => {
  log(`Error running tests: ${error.message}`, 'error');
  process.exit(1);
});