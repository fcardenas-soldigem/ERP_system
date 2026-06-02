import { api } from '../lib/api';

export const clientesService = {
  // Obtener todos los clientes
  getClientes: async (params = {}) => {
    try {
      const response = await api.get('/api/ventas/clientes/', { params });
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Obtener un cliente por ID
  getClienteById: async (id) => {
    try {
      const response = await api.get(`/api/ventas/clientes/${id}/`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Crear un nuevo cliente
  createCliente: async (clienteData) => {
    try {
      const response = await api.post('/api/ventas/clientes/', clienteData);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Actualizar un cliente existente
  updateCliente: async (id, clienteData) => {
    try {
      const response = await api.put(`/api/ventas/clientes/${id}/`, clienteData);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Eliminar un cliente
  deleteCliente: async (id) => {
    try {
      const response = await api.delete(`/api/ventas/clientes/${id}/`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Buscar clientes
  searchClientes: async (searchTerm) => {
    try {
      const response = await api.get('/api/ventas/clientes/', {
        params: { search: searchTerm }
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Importar clientes masivamente
  importarClientes: async (archivo) => {
    try {
      const formData = new FormData();
      formData.append('archivo', archivo);

      const response = await api.post('/api/ventas/clientes/importar_clientes/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Descargar plantilla Excel para importación
  descargarPlantillaExcel: async () => {
    try {
      const response = await api.get('/api/ventas/clientes/descargar_plantilla_excel/', {
        responseType: 'blob',
      });
      
      // Crear URL del blob y disparar descarga
      const blob = new Blob([response.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'plantilla_clientes.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      return { success: true };
    } catch (error) {
      throw error;
    }
  }
}; 