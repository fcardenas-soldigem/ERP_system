import api from '../lib/api';

const serviciosService = {
  listar: async (params = {}) => {
    const response = await api.get('/api/servicios/ordenes/', { params });
    return response.data;
  },

  obtener: async (id) => {
    const response = await api.get(`/api/servicios/ordenes/${id}/`);
    return response.data;
  },

  crear: async (data) => {
    const response = await api.post('/api/servicios/ordenes/', data);
    return response.data;
  },

  actualizar: async (id, data) => {
    const response = await api.put(`/api/servicios/ordenes/${id}/`, data);
    return response.data;
  },

  cambiarEstado: async (id, data) => {
    const response = await api.post(`/api/servicios/ordenes/${id}/cambiar_estado/`, data);
    return response.data;
  },

  agregarSeguimiento: async (id, data) => {
    const response = await api.post(`/api/servicios/ordenes/${id}/agregar_seguimiento/`, data);
    return response.data;
  },

  resumen: async () => {
    const response = await api.get('/api/servicios/ordenes/resumen/');
    return response.data;
  },

  exportarExcel: async () => {
    const response = await api.get('/api/servicios/ordenes/exportar_excel/', {
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(
      new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
    );
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `ordenes_servicio_${new Date().toISOString().split('T')[0]}.xlsx`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
};

export default serviciosService;
