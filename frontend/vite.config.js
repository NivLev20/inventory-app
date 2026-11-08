// In development Vite proxies /api to the docker compose stack on port 8080; in production nginx does it.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Reachable from the Windows browser; WSL's network is not exposed to the LAN
    host: true,
    proxy: {
      "/api": "http://localhost:8080"
    }
  }
});
