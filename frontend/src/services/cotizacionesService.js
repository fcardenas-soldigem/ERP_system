import api from '../config/axios';

const cotizacionesService = {
  // Obtener todas las cotizaciones
  getAll: async (params = {}) => {
    const response = await api.get('/api/cotizaciones/', { params });
    return response.data;
  },

  // Obtener una cotizacion por ID
  getById: async (id) => {
    const response = await api.get(`/api/cotizaciones/${id}/`);
    return response.data;
  },

  // Crear nueva cotización
  create: async (data) => {
    const response = await api.post('/api/cotizaciones/', data);
    return response.data;
  },

  // Actualizar cotización
  update: async (id, data) => {
    const response = await api.put(`/api/cotizaciones/${id}/`, data);
    return response.data;
  },

  // Eliminar cotización
  delete: async (id) => {
    const response = await api.delete(`/api/cotizaciones/${id}/`);
    return response.data;
  },

  // Cambiar estado de cotización
  cambiarEstado: async (id, estado) => {
    const response = await api.post(`/api/cotizaciones/${id}/cambiar-estado/`, { estado });
    return response.data;
  },

  // Duplicar cotización
  duplicar: async (id) => {
    const response = await api.post(`/api/cotizaciones/${id}/duplicar/`);
    return response.data;
  },

  // Convertir a venta
  convertirVenta: async (id) => {
    const response = await api.post(`/api/cotizaciones/${id}/convertir-venta/`);
    return response.data;
  },

  // Exportar a PDF
  exportarPDF: async (id) => {
    const response = await api.get(`/api/cotizaciones/${id}/exportar-pdf/`, {
      responseType: 'blob'
    });
    
    // Crear URL para descargar
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `Cotizacion_${id}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    
    return response.data;
  },

  // Obtener estadísticas
  getEstadisticas: async () => {
    const response = await api.get('/api/cotizaciones/estadisticas/');
    return response.data;
  }
};

export default cotizacionesService;


