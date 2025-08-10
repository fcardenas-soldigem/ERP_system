import { api } from '../api';

export const categoriasService = {
    getCategorias: async () => {
        try {
            const response = await api.get('/api/inventario/categorias/');
            console.log('Respuesta getCategorias:', response.data);
            return Array.isArray(response.data) ? response.data : 
                   Array.isArray(response.data.results) ? response.data.results : [];
        } catch (error) {
            console.error('Error en getCategorias:', error);
            throw error;
        }
    },

    createCategoria: async (data) => {
        const response = await api.post('/api/inventario/categorias/', data);
        return response.data;
    },

    updateCategoria: async (id, data) => {
        const response = await api.put(`/api/inventario/categorias/${id}/`, data);
        return response.data;
    },

    deleteCategoria: async (id) => {
        const response = await api.delete(`/api/inventario/categorias/${id}/`);
        return response.data;
    }
};

export default categoriasService; 