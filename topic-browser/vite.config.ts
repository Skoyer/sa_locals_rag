import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  /** Load `VITE_*` from repo root `.env` when developing from `topic-browser/`. */
  envDir: '..',
  /** Listen on all interfaces so other devices on the LAN can open http://<your-ip>:5173 */
  server: {
    host: true,
    /** Proxy local MP4 streams from ``python -m local_media serve`` (default :8010). */
    proxy: {
      '/media': {
        target: 'http://127.0.0.1:8010',
        changeOrigin: true,
      },
    },
  },
})
