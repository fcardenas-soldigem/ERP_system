/**
 * 0.3 — mismo origen: JSON por ruta relativa (rewrite de Vercel con cookie
 * same-site); subidas multipart directo a Cloud Run (límite de body del
 * rewrite no documentado). Se inspecciona la config final de cada request
 * con un adapter falso: nada sale a la red.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

const RUN_APP = 'https://erp-backend-25656632090.southamerica-west1.run.app';

async function cargarApi(env) {
  vi.resetModules();
  vi.stubEnv('VITE_API_URL', env.VITE_API_URL ?? '');
  vi.stubEnv('VITE_API_UPLOAD_URL', env.VITE_API_UPLOAD_URL ?? '');
  const { api } = await import('./api.js');
  const vistas = [];
  api.defaults.adapter = async (config) => {
    vistas.push(config);
    return { data: {}, status: 200, statusText: 'OK', headers: {}, config };
  };
  return { api, vistas };
}

afterEach(() => vi.unstubAllEnvs());

describe('cliente api — mismo origen', () => {
  it('JSON va relativo (/api/…) y con credenciales', async () => {
    const { api, vistas } = await cargarApi({ VITE_API_UPLOAD_URL: RUN_APP });
    await api.get('/api/ventas/');
    expect(vistas[0].baseURL).toBe('');
    expect(vistas[0].withCredentials).toBe(true);
  });

  it('una subida FormData va directo a Cloud Run, sin cookie', async () => {
    const { api, vistas } = await cargarApi({ VITE_API_UPLOAD_URL: RUN_APP });
    const fd = new FormData();
    fd.append('archivo', new Blob(['x']), 'comprobante.jpg');
    await api.post('/api/ventas/1/pagos/', fd);
    expect(vistas[0].baseURL).toBe(RUN_APP);
    expect(vistas[0].withCredentials).toBe(false);
  });

  it('una descarga blob (PDF/Excel) también va directo', async () => {
    const { api, vistas } = await cargarApi({ VITE_API_UPLOAD_URL: RUN_APP });
    await api.get('/api/cotizaciones/1/exportar-pdf/', { responseType: 'blob' });
    expect(vistas[0].baseURL).toBe(RUN_APP);
  });

  it('sin VITE_API_UPLOAD_URL (local) la subida sigue el destino normal', async () => {
    const { api, vistas } = await cargarApi({ VITE_API_URL: 'http://127.0.0.1:8000' });
    await api.post('/api/importador/upload/', new FormData());
    expect(vistas[0].baseURL).toBe('http://127.0.0.1:8000');
  });
});
