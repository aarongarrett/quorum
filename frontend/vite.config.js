import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // In production mode, require VITE_API_URL to be explicitly set
  // Empty string is allowed for same-origin deployments (e.g., Docker)
  if (mode === 'production' && process.env.VITE_API_URL === undefined) {
    throw new Error(
      'VITE_API_URL environment variable must be set for production builds. ' +
      'Example: VITE_API_URL=https://api.example.com npm run build (or VITE_API_URL="" for same-origin)'
    );
  }

  return {
    plugins: [react()],
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        }
      }
    }
  };
})
