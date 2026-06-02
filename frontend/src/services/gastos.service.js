import { api } from '../lib/api';

export const gastosService = {
  // Categorías
  getCategorias: () => api.get('/api/finanzas/categorias/').then(r => r.data?.results ?? r.data),

  // Gastos
  getGastos: (params) => api.get('/api/finanzas/gastos/', { params }).then(r => r.data),
  createGasto: (data) =>
    api.post('/api/finanzas/gastos/', data, {
      headers: data instanceof FormData ? { 'Content-Type': 'multipart/form-data' } : {},
    }).then(r => r.data),
  updateGasto: (id, data) => api.patch(`/api/finanzas/gastos/${id}/`, data).then(r => r.data),
  deleteGasto: (id) => api.delete(`/api/finanzas/gastos/${id}/`),
  getResumen: (fecha) =>
    api.get('/api/finanzas/gastos/resumen/', { params: { fecha } }).then(r => r.data),

  // Recurrentes
  getRecurrentes: () => api.get('/api/finanzas/recurrentes/').then(r => r.data?.results ?? r.data),
  createRecurrente: (data) => api.post('/api/finanzas/recurrentes/', data).then(r => r.data),
  generarMes: (id) =>
    api.post(`/api/finanzas/recurrentes/${id}/generar_mes/`).then(r => r.data),
};
