import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    strictPort: false,
    proxy: {
      '/api': {
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
