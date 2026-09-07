import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // Keep the standalone dev UI on the same local-only API boundary as the
    // FastAPI app. This is development plumbing, not a research/runtime path.
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
      },
    },
  },
})
