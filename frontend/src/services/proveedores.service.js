import { api } from '../lib/api';

export const proveedoresService = {
  async getProveedores() {
    try {
      const empresaId = localStorage.getItem('empresa_id');
      if (!empresaId) {
        throw new Error('No se encontró el ID de la empresa');
      }

      console.log('Obteniendo proveedores para empresa:', empresaId);
      const response = await api.get('/api/compras/proveedores/', {
        params: { empresa: empresaId }
      });
      
      console.log('URL de la petición:', response.config?.url);
      console.log('Parámetros:', response.config?.params);
      console.log('Respuesta completa:', response);
      console.log('Datos de proveedores:', response.data);
      
      const proveedores = Array.isArray(response.data) ? response.data : 
                         Array.isArray(response.data.results) ? response.data.results : [];
      
      return proveedores;
    } catch (error) {
      console.error('Error al obtener proveedores:', error);
      console.error('Detalles del error:', {
        mensaje: error.message,
        respuesta: error.response?.data,
        estado: error.response?.status
      });
      throw error;
    }
  },

  async getProveedor(id) {
    const response = await api.get(`/api/compras/proveedores/${id}/`);
    return response.data;
  },

  async crearProveedor(data) {
    const empresaId = localStorage.getItem('empresa_id');
    if (!empresaId) {
      throw new Error('No se encontró el ID de la empresa');
    }
    
    const dataConEmpresa = {
      ...data,
      empresa: empresaId
    };
    
    const response = await api.post('/api/compras/proveedores/', dataConEmpresa);
    return response.data;
  },

  async actualizarProveedor(id, data) {
    const response = await api.put(`/api/compras/proveedores/${id}/`, data);
    return response.data;
  },

  async eliminarProveedor(id) {
    const response = await api.delete(`/api/compras/proveedores/${id}/`);
    return response.data;
  },

  async consultarRuc(ruc) {
    try {
      console.log('Consultando RUC:', ruc);
      const response = await api.get('/api/compras/proveedores/consultar_ruc/', {
        params: { ruc }
      });
      
      console.log('Respuesta consulta RUC:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error al consultar RUC:', error);
      throw error;
    }
  },

  async exportarProveedores() {
    try {
      const response = await api.get('/api/compras/proveedores/exportar/', {
        responseType: 'blob',
        headers: {
          'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
      });

      // Verificar si la respuesta es un blob
      if (!(response.data instanceof Blob)) {
        throw new Error('La respuesta no es un archivo válido');
      }

      // Verificar el tipo de contenido
      if (!response.data.type.includes('spreadsheetml.sheet')) {
        throw new Error('El archivo no es un Excel válido');
      }

      return response.data;
    } catch (error) {
      console.error('Error al exportar proveedores:', error);
      
      // Si hay un mensaje de error en la respuesta, mostrarlo
      if (error.response?.data instanceof Blob) {
        try {
          const text = await error.response.data.text();
          const errorData = JSON.parse(text);
          throw new Error(errorData.error || 'Error al exportar proveedores');
        } catch (e) {
          // Si no podemos leer el error, mostrar un mensaje genérico
          throw new Error('Error al exportar proveedores');
        }
      }
      
      throw new Error('Error al exportar proveedores');
    }
  }
};

export default proveedoresService; 