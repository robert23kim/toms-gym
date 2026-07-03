/// <reference types="vite/client" />

// Hardcoded production URL as the fallback when VITE_API_URL is unset
// (e.g. a local build without env). Deploys set VITE_API_URL explicitly.
const PRODUCTION_API_URL = "https://my-python-backend-quyiiugyoq-ue.a.run.app";

export const API_URL = import.meta.env.VITE_API_URL || PRODUCTION_API_URL;
export const PROD_API_URL = PRODUCTION_API_URL;
export const COMPETITIONS_API_URL = API_URL;

// App build/version stamp — set at deploy time by deploy.py via
// VITE_BUILD_TIMESTAMP (unix seconds). Surfaced in the footer so you can
// confirm at a glance which frontend build is actually live.
const buildTimestamp = Number(import.meta.env.VITE_BUILD_TIMESTAMP) || 0;
export const APP_VERSION = buildTimestamp
  ? `${new Date(buildTimestamp * 1000).toISOString().slice(0, 16).replace("T", " ")} UTC`
  : "dev";
export const APP_BUILD = buildTimestamp;
