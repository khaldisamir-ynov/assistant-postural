import { fileURLToPath } from "node:url"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import { viteSingleFile } from "vite-plugin-singlefile"

const server = { target: "http://127.0.0.1:8765", changeOrigin: true }  // l'assistant lance : npm run dev s'y branche

// Une seule page, JS et CSS integres : posture/index.html, servi tel quel par server.py et embarque dans l'exe
export default defineConfig({
  plugins: [react(), tailwindcss(), viteSingleFile()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  publicDir: false,
  build: { outDir: "../posture", emptyOutDir: false },
  server: { proxy: { "/api": server, "/video": server } },
})
