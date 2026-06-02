import { api } from '../lib/api';

export const productosService = {
    getProductos: async (filtros = {}) => {
        try {
            console.log('Iniciando petición a productos...', filtros);
            const response = await api.get('/api/inventario/productos/', { params: filtros });
            console.log('Respuesta completa:', response);
            return response.data;
        } catch (error) {
            console.error('Error en getProductos:', error);
            throw error;
        }
    },

    // Obtener solo productos terminados (para ventas y cotizaciones)
    getProductosParaVenta: async () => {
        try {
            console.log('Obteniendo productos terminados para venta...');
            const response = await api.get('/api/inventario/productos/', {
                params: { tipo_producto: 'FINISHED' }
            });
            console.log('Productos para venta:', response.data);
            return response.data;
        } catch (error) {
            console.error('Error en getProductosParaVenta:', error);
            throw error;
        }
    },

    getStocks: async () => {
        try {
            console.log('Solicitando stocks...');
            const response = await api.get('/api/inventario/stocks/');
            console.log('Stocks recibidos:', response.data);
            return response.data;
        } catch (error) {
            console.error('Error en getStocks:', error);
            throw error;
        }
    },

    getAlmacenes: async () => {
        try {
            console.log('Solicitando almacenes...');
            const response = await api.get('/api/inventario/almacenes/');
            console.log('Almacenes recibidos:', response.data);
            return response.data;
        } catch (error) {
            console.error('Error en getAlmacenes:', error);
            throw error;
        }
    },

    getProducto: async (id) => {
        try {
            const response = await api.get(`/api/inventario/productos/${id}/`);
            return response.data;
        } catch (error) {
            console.error('Error en getProducto:', error);
            throw error;
        }
    },

    createProducto: async (data) => {
        try {
            console.log('Datos a enviar:', data);
            const response = await api.post('/api/inventario/productos/', data);
            console.log('Producto creado:', response.data);
            return response.data;
        } catch (error) {
            console.error('Error en createProducto:', error);
            throw error;
        }
    },

    updateProducto: async (id, data) => {
        try {
            const response = await api.put(`/api/inventario/productos/${id}/`, data);
            return response.data;
        } catch (error) {
            console.error('Error en updateProducto:', error);
            throw error;
        }
    },

    deleteProducto: async (id) => {
        try {
            const response = await api.delete(`/api/inventario/productos/${id}/`);
            return response.data;
        } catch (error) {
            console.error('Error en deleteProducto:', error);
            throw error;
        }
    },

    getEstadisticas: async () => {
        try {
            const response = await api.get('/api/inventario/productos/estadisticas/');
            return response.data;
        } catch (error) {
            console.error('Error en getEstadisticas:', error);
            throw error;
        }
    },

    checkSku: async (sku) => {
        try {
            const response = await api.get(`/api/inventario/productos/check_sku/?sku=${sku}`);
            return response.data;
        } catch (error) {
            console.error('Error en checkSku:', error);
            throw error;
        }
    },

    actualizarStock: async (id, data) => {
        try {
            const response = await api.post(`/api/inventario/productos/${id}/actualizar_stock/`, data);
            return response.data;
        } catch (error) {
            console.error('Error en actualizarStock:', error);
            throw error;
        }
    },

    getMateriasPrimas: async () => {
        try {
            console.log('Solicitando materias primas...');
            const response = await api.get('/api/inventario/productos/materias_primas/');
            console.log('Materias primas recibidas:', response.data);
            return response.data;
        } catch (error) {
            console.error('Error en getMateriasPrimas:', error);
            throw error;
        }
    },

    // Método de utilidad para cargar datos iniciales
    getInitialData: async () => {
        try {
            const [almacenes, stocks] = await Promise.all([
                productosService.getAlmacenes(),
                productosService.getStocks()
            ]);
            console.log('Datos iniciales cargados:', { almacenes, stocks });
            return { almacenes, stocks };
        } catch (error) {
            console.error('Error al cargar datos iniciales:', error);
            throw error;
        }
    }
};

export default productosService; 