import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: ['malika-abrupt-goniometrically.ngrok-free.dev'], // 👈 your ngrok domain
    host: true,
    port: 5173,
    strictPort: false,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/admin': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/profile_photos': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
    hmr: {
      overlay: true,
    },
    watch: {
      usePolling: true,
      interval: 300,
    },
    historyApiFallback: true,
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'antd', 'chart.js', 'react-chartjs-2'],
  },
})
