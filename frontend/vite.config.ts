import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  // Loads .env / .env.local plus process.env (no prefix filter) so dev-only
  // overrides like FORLAS_API_PROXY work regardless of how vite is launched.
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react()],
    // Docker bundle serves the SPA under `/app/`; Tauri serves it via a custom
    // protocol where relative paths work. Default to `/` for the dev server.
    base: env.VITE_BASE_PATH || "/",
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        "/api": {
          // Overridable so a dev/test backend can run on a different port
          // without disturbing an installed app already bound to 8765.
          target: env.FORLAS_API_PROXY || "http://127.0.0.1:8765",
          changeOrigin: true,
        },
      },
    },
    build: {
      target: "es2022",
      sourcemap: true,
    },
  };
});
