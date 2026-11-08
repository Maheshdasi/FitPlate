import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Requests to /api are forwarded to the FastAPI backend, so the browser only talks to one address.
const proxy = {
  '/api': {
    target: process.env.API_TARGET || 'http://127.0.0.1:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
  },
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    // Allow GitHub Codespaces' forwarded address (*.app.github.dev)
    allowedHosts: ['localhost', '127.0.0.1', '.app.github.dev'],
    proxy,
  },
  preview: { port: 5173, host: true, allowedHosts: ['localhost', '127.0.0.1', '.app.github.dev'], proxy },
  build: {
    rollupOptions: {
      output: {
        manualChunks: { charts: ['recharts'], vendor: ['react', 'react-dom', 'react-router-dom'] },
      },
    },
  },
})
