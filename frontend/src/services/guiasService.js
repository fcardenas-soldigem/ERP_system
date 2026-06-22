import api from '../lib/api';

const guiasService = {
  getAll: async (params = {}) => {
    const response = await api.get('/api/guias/guias/', { params });
    return response.data;
  },

  getById: async (id) => {
    const response = await api.get(`/api/guias/guias/${id}/`);
    return response.data;
  },

  create: async (data) => {
    const response = await api.post('/api/guias/guias/', data);
    return response.data;
  },

  update: async (id, data) => {
    const response = await api.put(`/api/guias/guias/${id}/`, data);
    return response.data;
  },

  delete: async (id) => {
    const response = await api.delete(`/api/guias/guias/${id}/`);
    return response.data;
  },

  cambiarEstado: async (id, estado) => {
    const response = await api.post(`/api/guias/guias/${id}/cambiar-estado/`, { estado });
    return response.data;
  },

  generarDesdeVenta: async (ventaId) => {
    const response = await api.post(`/api/ventas/ventas/${ventaId}/generar-guia/`);
    return response.data;
  },

  exportarPDF: async (id, numero = '') => {
    const response = await api.get(`/api/guias/guias/${id}/pdf/`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${numero || `GR-${id}`}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    return response.data;
  },
};

export default guiasService;
