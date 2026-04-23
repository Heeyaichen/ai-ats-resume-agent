import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target:
          "https://ats-agent-dev-api.salmonsmoke-fa24b266.swedencentral.azurecontainerapps.io",
        changeOrigin: true,
        secure: true,
      },
    },
  },
});
