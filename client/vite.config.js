import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  publicDir: "public", // This should be here
  build: {
    copyPublicDir: true, // Add this line
  },
});
