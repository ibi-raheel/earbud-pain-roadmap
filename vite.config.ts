import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Hosted at ibiraheel.com/demos/earbud-pain-roadmap/. Override with VITE_BASE=/ for root hosting.
export default defineConfig({
  base: process.env.VITE_BASE ?? '/demos/earbud-pain-roadmap/',
  plugins: [react()],
})
