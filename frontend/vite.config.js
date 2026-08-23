import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Sostituisce craco.config.js: build.outDir resta "build" (non il default
// "dist" di Vite) per non dover cambiare la cartella di pubblicazione su
// Netlify, che vive solo nella dashboard, non nel repo — e per non dover
// toccare scripts/prerender.js, che legge/scrive già in build/.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  build: {
    outDir: "build",
  },
  // Stessa porta di CRA (3000, non il 5173 di default di Vite): evita di
  // dover toccare .claude/launch.json e qualunque altro riferimento fisso
  // alla porta usato finora.
  server: {
    port: 3000,
  },
});
