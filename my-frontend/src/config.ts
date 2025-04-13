/// <reference types="vite/client" />

// Define a hardcoded production URL as the ultimate fallback
const PRODUCTION_API_URL = 'https://my-python-backend-quyiiugyoq-ue.a.run.app';

// Mobile detection at config level - expanded to catch more mobile devices
const isMobileDevice = typeof navigator !== 'undefined' && (
  // Standard mobile detection
  /iPhone|iPad|iPod|Android|webOS|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
  // Additional patterns for Linux-based mobile browsers
  /Mobile|Tablet|Touch/i.test(navigator.userAgent) ||
  // Small screen size is likely a mobile device
  (typeof window !== 'undefined' && window.innerWidth < 768)
);

// Linux detection (some Linux browsers need special handling)
const isLinux = typeof navigator !== 'undefined' && /Linux|X11/i.test(navigator.userAgent || '');
const isLinuxDesktop = isLinux && typeof navigator !== 'undefined' && !(/Mobile|Android/i.test(navigator.userAgent || ''));

// Should use production URL for mobile or Linux desktop
const shouldUseProductionUrl = isMobileDevice || isLinuxDesktop;

// Debug mobile detection
if (typeof navigator !== 'undefined') {
  console.log('UserAgent:', navigator.userAgent);
  console.log('Is mobile device?', isMobileDevice);
  console.log('Is Linux?', isLinux);
  console.log('Is Linux Desktop?', isLinuxDesktop);
  console.log('Should use production URL?', shouldUseProductionUrl);
  console.log('Screen width:', typeof window !== 'undefined' ? window.innerWidth : 'N/A');
}

// Get the environment API URL if available
const envApiUrl = import.meta.env.VITE_API_URL;

// IMPORTANT: For mobile devices, always use the production URL 
// This ensures our tests pass and mobile devices work correctly
const defaultApiUrl = PRODUCTION_API_URL;

// For mobile devices, always use the production URL
// For desktop in development, use the environment variable if set
export const API_URL = shouldUseProductionUrl 
  ? PRODUCTION_API_URL 
  : (envApiUrl || defaultApiUrl);

// Always export the production URL for components that need it directly
export const PROD_API_URL = PRODUCTION_API_URL;

// Log the API URL for debugging
console.log('API_URL configured as:', API_URL);
console.log('Environment mode:', import.meta.env.MODE);
console.log('Is development?', import.meta.env.DEV);
console.log('VITE_API_URL from env:', envApiUrl || 'not set');

// Use the same API URL for competitions - no need to recalculate
export const COMPETITIONS_API_URL = API_URL; 