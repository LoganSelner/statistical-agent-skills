import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";

// Dev-only: forward API calls to the backend so the browser sees one origin (no CORS).
// In production the API serves the built assets, so the client always uses relative URLs.
const apiTarget = "http://localhost:8000";

export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      "/runs": apiTarget,
      "/healthz": apiTarget,
    },
  },
});
