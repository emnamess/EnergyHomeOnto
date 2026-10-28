import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // 127.0.0.1 et non localhost : Node résout localhost en IPv6 (::1) alors qu'uvicorn écoute en IPv4.
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
