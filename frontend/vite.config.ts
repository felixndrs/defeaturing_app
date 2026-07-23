import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies API calls to the backend so the browser talks to a
// single origin (no CORS in dev) and the same build works behind a reverse
// proxy in production.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Bind IPv4 explicitly. Left at the default, Vite/Node can bind only the
    // IPv6 loopback ([::1]) on some Windows setups, which then refuses plain
    // 127.0.0.1 connections (curl, some browsers/extensions, some proxies).
    host: "127.0.0.1",
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
