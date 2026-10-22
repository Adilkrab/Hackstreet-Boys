import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Every request to /api is forwarded to the FastAPI backend.
// The browser only ever talks to one address, so no CORS setup is needed.
const backend = process.env.BACKEND_URL || "http://localhost:8000";

const shared = {
  host: "0.0.0.0",
  port: 5173,
  allowedHosts: true, // Replit gives the app a random domain name
  proxy: { "/api": backend },
};

export default defineConfig({
  plugins: [react()],
  server: shared,
  preview: shared,
});
