import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(async ({ mode }) => {
  // Load env file based on mode, with special case for emulator
  const nodeEnv = process.env.VITE_USER_NODE_ENV || mode;
  const env = loadEnv(nodeEnv, process.cwd(), '');
  
  const plugins = [react()];

  // Determine host based on environment
  // Use 0.0.0.0 for wider network access when testing with emulators
  const host = nodeEnv === 'emulator' ? '0.0.0.0' : '::';

  console.log(`Starting in ${nodeEnv} mode with API URL: ${env.VITE_API_URL || 'default'}`);

  return {
    server: {
      host,
      port: 8080,
      strictPort: false,
    },
    plugins,
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});

