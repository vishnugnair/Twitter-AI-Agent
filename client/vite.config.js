import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  publicDir: "public", // This should be here
  server: {
    historyApiFallback: true, // This fixes the refresh issue
  },
  build: {
    copyPublicDir: true, // Add this line
  },
});
