import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Dev: /api được proxy sang FastAPI (uvicorn, cổng 8000) để không cần CORS.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
  test: { environment: "node" },
});
