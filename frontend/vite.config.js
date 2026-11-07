// Vite settings: the React plugin + a dev-mode proxy.
// In development (npm run dev) the browser talks to Vite on port 5173,
// and Vite forwards every /api request to the backend running in docker compose (port 5000).
// In production nginx does the same job (see nginx.conf.template).
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Listen on all interfaces inside WSL so the Windows browser can reach it.
    // WSL's network is private to this computer, so this is not exposed to the LAN.
    host: true,
    proxy: {
      "/api": "http://localhost:5000"
    }
  }
});
