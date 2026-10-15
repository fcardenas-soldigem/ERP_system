import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// assetsDir 'l-assets' evita colisión con /assets del ERP cuando ambos
// proyectos conviven bajo el mismo dominio vía los rewrites de Vercel.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  build: {
    assetsDir: 'l-assets',
  },
  // Dev: proxy /api -> backend local, replicando el mismo-origen que en
  // producción dan los rewrites de Vercel (sin CORS). El form usa ruta
  // relativa /api/leads/ en ambos entornos.
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
});
