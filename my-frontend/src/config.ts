/// <reference types="vite/client" />

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:9888';

// Use the local backend for competitions now since it connects to the GCP database
export const COMPETITIONS_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:9888'; 