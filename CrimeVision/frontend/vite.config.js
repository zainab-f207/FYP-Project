import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0', // Allow access from any IP (including mobile devices on same network)
    // Enhanced HMR with state preservation
    hmr: {
      overlay: true,
      clientPort: 5173
    },
    watch: {
      // Enhanced file watching
      usePolling: true,
      interval: 100,
      binaryInterval: 300
    },
    // Force full page reload only when necessary
    middlewareMode: false,
    // Proxy API requests to backend
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  },
  build: {
    // Better build optimization
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          auth: ['./src/contexts/AuthContext'],
          utils: ['./src/services/apiService']
        }
      }
    }
  },
  // Enhanced dependency optimization
  optimizeDeps: {
    include: [
      'react', 
      'react-dom', 
      'react-router-dom',
      'bootstrap',
      'bootstrap/dist/css/bootstrap.min.css'
    ],
    force: false
  },
  // Clear screen on restart
  clearScreen: false
})
