import { api } from '../api';

export const dashboardService = {
    getResumen: async () => {
        try {
            console.log('Obteniendo resumen del dashboard...');
            const response = await api.get('/api/dashboard/resumen/');
            console.log('Respuesta del resumen:', response.data);
            return response.data;
        } catch (error) {
            console.error('Error al obtener resumen del dashboard:', error);
            console.error('Detalles del error:', error.response?.data);
            
            // Si hay un error específico del servidor, lo propagamos
            if (error.response?.data?.error) {
                throw new Error(error.response.data.error);
            }
            
            // Si no hay un error específico, lanzamos un error genérico
            throw new Error('Error al cargar el resumen del dashboard');
        }
    },

    getUtilityData: async (year, month) => {
        try {
            console.log(`Obteniendo datos de utilidad para ${month}/${year}`);
            const response = await api.get('/api/dashboard/utility/', {
                params: { year, month }
            });
            console.log('Respuesta de utilidad:', response.data);
            return response.data;
        } catch (error) {
            console.error('Error al obtener datos de utilidad:', error);
            throw error;
        }
    },

    getVentasData: async (month = null, year = null) => {
        try {
            if (month && year) {
                console.log(`Obteniendo datos de ventas para ${month}/${year}`);
                const response = await api.get('/api/dashboard/ventas/mensual/', {
                    params: { year, month }
                });
                console.log('Respuesta de ventas mensuales:', response.data);
                return response.data;
            } else {
                console.log('Obteniendo datos de ventas últimos 30 días...');
                const response = await api.get('/api/dashboard/stats/30/');
                console.log('Respuesta de ventas:', response.data);
                return response.data.ventas; // Ya viene con formato {labels: [], data: []}
            }
        } catch (error) {
            console.error('Error al obtener datos de ventas:', error);
            return { labels: [], data: [] };
        }
    },

    getComprasData: async () => {
        try {
            console.log('Obteniendo datos de compras...');
            const response = await api.get('/api/dashboard/stats/30/');
            console.log('Respuesta de compras:', response.data);
            return response.data.compras; // Ya viene con formato {labels: [], data: []}
        } catch (error) {
            console.error('Error al obtener datos de compras:', error);
            return { labels: [], data: [] };
        }
    },

    getInventarioData: async () => {
        try {
            console.log('Obteniendo datos de inventario...');
            const response = await api.get('/api/dashboard/resumen/');
            console.log('Respuesta de inventario:', response.data);
            return response.data.inventario;
        } catch (error) {
            console.error('Error al obtener datos de inventario:', error);
            return {
                total_productos: 0,
                total_cantidad: 0,
                productos_bajo_stock: 0
            };
        }
    },

    getIGVData: async () => {
        try {
            console.log('Obteniendo datos de IGV...');
            const response = await api.get('/api/dashboard/igv/');
            console.log('Respuesta de IGV:', response.data);
            return response.data;
        } catch (error) {
            console.error('Error al obtener datos de IGV:', error);
            return {
                igv_ventas: 0,
                igv_compras: 0,
                igv_por_pagar: 0
            };
        }
    },

    // Nuevos métodos para datos anuales
    getVentasAnual: async (year = new Date().getFullYear()) => {
        try {
            console.log(`Obteniendo datos de ventas anuales para ${year}`);
            const response = await api.get('/api/dashboard/ventas/anual/', {
                params: { year }
            });
            console.log('Respuesta de ventas anuales:', response.data);
            return response.data;
        } catch (error) {
            console.error('Error al obtener datos de ventas anuales:', error);
            return { labels: [], data: [] };
        }
    },

    getComprasAnual: async (year = new Date().getFullYear()) => {
        try {
            console.log(`Obteniendo datos de compras anuales para ${year}`);
            const response = await api.get('/api/dashboard/compras/anual/', {
                params: { year }
            });
            console.log('Respuesta de compras anuales:', response.data);
            return response.data;
        } catch (error) {
            console.error('Error al obtener datos de compras anuales:', error);
            return { labels: [], data: [] };
        }
    },

    getUtilidadAnual: async (year = new Date().getFullYear()) => {
        try {
            console.log(`Obteniendo datos de utilidad anual para ${year}`);
            const response = await api.get('/api/dashboard/utilidad/anual/', {
                params: { year }
            });
            console.log('Respuesta de utilidad anual:', response.data);
            return response.data;
        } catch (error) {
            console.error('Error al obtener datos de utilidad anual:', error);
            return { labels: [], utilidades: [], ventas: [], compras: [] };
        }
    }
};

