import { api } from '../api';

export const almacenesService = {
  getAlmacenes: async () => {
    try {
      const response = await api.get('/api/inventario/almacenes/');
      console.log('Respuesta API almacenes:', response.data);

      const almacenes = response.data?.results || response.data || [];
      
      if (almacenes.length > 0) {
        console.log('Primer almacén:', almacenes[0]);
      } else {
        console.log('No hay almacenes disponibles');
      }

      return almacenes;
    } catch (error) {
      console.error('Error en getAlmacenes:', error);
      console.error('Detalles del error:', error.response?.data);
      throw new Error('No se pudieron cargar los almacenes');
    }
  },

  obtenerAlmacen: async (id) => {
    try {
      const response = await api.get(`/api/inventario/almacenes/${id}/`);
      return response.data;
    } catch (error) {
      console.error('Error al obtener almacén:', error);
      throw error;
    }
  },

  crearAlmacen: async (data) => {
    try {
      const response = await api.post('/api/inventario/almacenes/', data);
      return response.data;
    } catch (error) {
      console.error('Error al crear almacén:', error);
      throw error;
    }
  },

  actualizarAlmacen: async (id, data) => {
    try {
      const response = await api.put(`/api/inventario/almacenes/${id}/`, data);
      return response.data;
    } catch (error) {
      console.error('Error al actualizar almacén:', error);
      throw error;
    }
  },

  eliminarAlmacen: async (id) => {
    try {
      await api.delete(`/api/inventario/almacenes/${id}/`);
    } catch (error) {
      console.error('Error al eliminar almacén:', error);
      throw error;
    }
  }
}; 