/// <reference types="vite/client" />

// In development we want to use localhost, overriding the .env.production file
// This will handle both local development and container environments
const defaultApiUrl = import.meta.env.DEV ? 'http://localhost:5001' : import.meta.env.VITE_API_URL;
export const API_URL = import.meta.env.VITE_API_URL || defaultApiUrl;

// Log the API URL for debugging
console.log('API_URL configured as:', API_URL);
console.log('Environment mode:', import.meta.env.MODE);
console.log('Is development?', import.meta.env.DEV);

// Use the local backend for competitions now since it connects to the GCP database
export const COMPETITIONS_API_URL = API_URL; 