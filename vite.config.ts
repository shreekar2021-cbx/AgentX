import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icons/icon-192.png', 'icons/icon-512.png', 'knowledge/essential-crops.json'],
      manifest: {
        id: '/', name: 'AgriVision AI', short_name: 'AgriVision', description: 'Farm observations and field intelligence',
        start_url: '/', scope: '/', display: 'standalone', background_color: '#0b1413', theme_color: '#0b1413',
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any maskable' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ],
      },
      workbox: {
        navigateFallback: '/index.html',
        globPatterns: ['**/*.{js,css,html,svg,png,json}'],
        globIgnores: ['**/demo/**'],
        maximumFileSizeToCacheInBytes: 2 * 1024 * 1024,
        runtimeCaching: [],
      },
    }),
  ],
  server: { proxy: { '/api': process.env.VITE_DEV_PROXY_TARGET || 'http://127.0.0.1:8000' } },
  build: { rollupOptions: { output: { manualChunks: { charts: ['recharts'], maps: ['leaflet', 'react-leaflet'] } } } },
})
