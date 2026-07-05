import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { initTelemetry } from './lib/telemetry'

// Before render: reports upload journeys that died with the previous page
// (crash/OOM/reload), sends the once-per-session boot ping, and installs
// global error reporters.
initTelemetry();

createRoot(document.getElementById("root")!).render(<App />);

