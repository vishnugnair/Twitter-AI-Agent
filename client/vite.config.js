import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  publicDir: "public",
  server: {
    // Remove the incorrect historyApiFallback option
    // Vite handles SPA routing automatically in dev mode
    open: true,
    port: 5173,
  },
  build: {
    copyPublicDir: true,
    outDir: "dist",
    // Ensure proper asset handling
    assetsDir: "assets",
  },
  // This is the correct way to handle SPA routing in Vite
  preview: {
    port: 4173,
    // For preview mode (vite preview)
    open: true,
  },
});

// Force deployment refresh
