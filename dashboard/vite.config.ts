import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  // For GitHub Pages deployments, set BASE_PATH in CI to `/${repo}/`
  base: process.env.BASE_PATH || '/',
  plugins: [react()],
})
