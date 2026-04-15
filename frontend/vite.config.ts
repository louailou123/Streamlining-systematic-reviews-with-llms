import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // WebSocket endpoint — must be listed BEFORE the generic /api catch-all
      '/api/v1/events/ws': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
      // REST API
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
