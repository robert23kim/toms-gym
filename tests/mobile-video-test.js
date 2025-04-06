/**
 * Mobile Video Playback Test Script
 * 
 * This script simulates mobile devices by using different user agents
 * and tests the video playback functionality across endpoints.
 * 
 * Run with: node mobile-video-test.js
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');

// Configuration
const API_URL = 'https://my-python-backend-quyiiugyoq-ue.a.run.app';
const FRONTEND_URL = 'https://my-frontend-quyiiugyoq-ue.a.run.app';
const OUTPUT_DIR = path.join(__dirname, 'test-results');

// Create output directory if it doesn't exist
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// Mobile User Agents
const USER_AGENTS = {
  iphone: 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
  android: 'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36',
  ipad: 'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
  desktop: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
};

// Log function with timestamps
function log(message, type = 'info') {
  const timestamp = new Date().toISOString();
  const colored = type === 'error' 
    ? `\x1b[31m${message}\x1b[0m` // Red for errors
    : type === 'success' 
      ? `\x1b[32m${message}\x1b[0m` // Green for success
      : message;
  
  console.log(`[${timestamp}] ${colored}`);
  
  // Also write to log file
  fs.appendFileSync(
    path.join(OUTPUT_DIR, 'test-log.txt'), 
    `[${timestamp}] [${type.toUpperCase()}] ${message}\n`
  );
}

// Helper to make requests with different user agents
async function makeRequest(url, userAgentKey, method = 'GET', extraHeaders = {}) {
  try {
    log(`Making ${method} request to ${url} with ${userAgentKey} user agent`);
    
    const response = await axios({
      method,
      url,
      headers: {
        'User-Agent': USER_AGENTS[userAgentKey],
        ...extraHeaders
      },
      validateStatus: () => true, // Don't throw on error status codes
    });
    
    return {
      status: response.status,
      headers: response.headers,
      data: response.data,
      success: response.status >= 200 && response.status < 300
    };
  } catch (error) {
    log(`Request failed: ${error.message}`, 'error');
    return {
      success: false,
      error: error.message
    };
  }
}

// Test the random-video endpoint
async function testRandomVideo(userAgentKey) {
  const result = await makeRequest(`${API_URL}/random-video`, userAgentKey);
  
  if (result.success) {
    log(`Random video request successful with ${userAgentKey}`, 'success');
    
    // Save response for analysis
    fs.writeFileSync(
      path.join(OUTPUT_DIR, `random-video-${userAgentKey}.json`),
      JSON.stringify(result.data, null, 2)
    );
    
    // Test if the video URL is properly formed
    if (result.data && result.data.video_url) {
      log(`Video URL: ${result.data.video_url}`);
      return result.data.video_url;
    } else {
      log('No video URL in response', 'error');
    }
  } else {
    log(`Random video request failed with ${userAgentKey}: ${result.status}`, 'error');
  }
  
  return null;
}

// Test the video proxy endpoint
async function testVideoProxy(userAgentKey, videoPath) {
  if (!videoPath) {
    log('No video path provided for proxy test', 'error');
    return false;
  }
  
  // Extract path from full URL if needed
  let path = videoPath;
  if (path.includes('jtr-lift-u-4ever-cool-bucket/')) {
    path = path.split('jtr-lift-u-4ever-cool-bucket/')[1];
  }
  
  const proxyUrl = `${API_URL}/video/${encodeURIComponent(path)}?mobile=true`;
  const result = await makeRequest(proxyUrl, userAgentKey);
  
  // Check if we got a redirect
  if (result.status === 302 && result.headers.location) {
    log(`Video proxy redirected to: ${result.headers.location}`, 'success');
    
    // Test the redirected URL
    const signedUrlResult = await makeRequest(result.headers.location, userAgentKey);
    
    if (signedUrlResult.success) {
      log(`Signed URL request successful with ${userAgentKey}`, 'success');
      log(`Content-Type: ${signedUrlResult.headers['content-type']}`);
      log(`Content-Length: ${signedUrlResult.headers['content-length']}`);
      
      // Check crucial headers for video streaming
      const hasRangeHeader = 'accept-ranges' in signedUrlResult.headers;
      log(`Has Accept-Ranges header: ${hasRangeHeader}`, hasRangeHeader ? 'success' : 'error');
      
      return true;
    } else {
      log(`Signed URL request failed: ${signedUrlResult.status}`, 'error');
    }
  } else {
    log(`Video proxy request failed or didn't redirect: ${result.status}`, 'error');
    
    // If we got a response, log it for debugging
    if (result.data) {
      fs.writeFileSync(
        path.join(OUTPUT_DIR, `video-proxy-error-${userAgentKey}.json`),
        JSON.stringify(result.data, null, 2)
      );
    }
  }
  
  return false;
}

// Test CORS headers
async function testCorsHeaders(userAgentKey, url) {
  if (!url) {
    log('No URL provided for CORS test', 'error');
    return false;
  }
  
  // Make an OPTIONS request to check CORS headers
  const result = await makeRequest(url, userAgentKey, 'OPTIONS', {
    'Origin': FRONTEND_URL,
    'Access-Control-Request-Method': 'GET',
    'Access-Control-Request-Headers': 'Content-Type'
  });
  
  const corsHeaders = [
    'access-control-allow-origin',
    'access-control-allow-methods',
    'access-control-allow-headers'
  ];
  
  const missingHeaders = corsHeaders.filter(header => !(header.toLowerCase() in result.headers));
  
  if (missingHeaders.length === 0) {
    log(`CORS headers present for ${userAgentKey}`, 'success');
    
    // Log the CORS headers
    corsHeaders.forEach(header => {
      log(`${header}: ${result.headers[header.toLowerCase()]}`);
    });
    
    return true;
  } else {
    log(`Missing CORS headers for ${userAgentKey}: ${missingHeaders.join(', ')}`, 'error');
    return false;
  }
}

// Main test function
async function runTests() {
  log('Starting mobile video playback tests', 'info');
  log('----------------------------------------');
  
  const results = {
    randomVideo: {},
    videoProxy: {},
    cors: {}
  };
  
  // Test with different user agents
  for (const [device, _] of Object.entries(USER_AGENTS)) {
    log(`\nTesting with ${device} user agent`);
    log('----------------------------------------');
    
    // Test random video endpoint
    const videoUrl = await testRandomVideo(device);
    results.randomVideo[device] = !!videoUrl;
    
    // Test video proxy endpoint if we got a video URL
    if (videoUrl) {
      results.videoProxy[device] = await testVideoProxy(device, videoUrl);
      
      // Test CORS headers
      results.cors[device] = await testCorsHeaders(device, videoUrl);
    } else {
      results.videoProxy[device] = false;
      results.cors[device] = false;
    }
    
    log('----------------------------------------');
  }
  
  // Summary
  log('\nTest Summary', 'info');
  log('----------------------------------------');
  
  let allPassed = true;
  
  ['randomVideo', 'videoProxy', 'cors'].forEach(testType => {
    log(`\n${testType} Tests:`);
    Object.entries(results[testType]).forEach(([device, passed]) => {
      log(`  ${device}: ${passed ? 'PASSED' : 'FAILED'}`, passed ? 'success' : 'error');
      if (!passed) allPassed = false;
    });
  });
  
  log('\n----------------------------------------');
  log(`Overall Test Result: ${allPassed ? 'PASSED' : 'FAILED'}`, allPassed ? 'success' : 'error');
  
  // Save results
  fs.writeFileSync(
    path.join(OUTPUT_DIR, 'test-results.json'),
    JSON.stringify(results, null, 2)
  );
  
  log(`\nResults saved to ${OUTPUT_DIR}`);
}

// Run the tests
runTests().catch(error => {
  log(`Test execution failed: ${error.message}`, 'error');
  console.error(error);
}); 