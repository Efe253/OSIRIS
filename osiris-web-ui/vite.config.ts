import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  // Alt-yolda (/ui/) sunulduğu için göreli asset yolları şart
  base: "./",
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
    },
  },
});
