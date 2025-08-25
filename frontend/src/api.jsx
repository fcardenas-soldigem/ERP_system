import axios from 'axios';
import { toast } from 'react-toastify';

// Crear instancia de axios con configuración base
export const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '',
});

// Interceptor para agregar el token a las peticiones
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
            console.log('Token agregado a la petición:', token.substring(0, 10) + '...');
        } else {
            console.warn('No hay token disponible');
        }

        // Si los datos son FormData, asegurarse de que el Content-Type sea multipart/form-data
        if (config.data instanceof FormData) {
            config.headers['Content-Type'] = 'multipart/form-data';
        } else {
            config.headers['Content-Type'] = 'application/json';
        }

        return config;
    },
    (error) => {
        console.error('Error en el interceptor de request:', error);
        return Promise.reject(error);
    }
);

// Interceptor para manejar errores de respuesta
api.interceptors.response.use(
    (response) => {
        return response;
    },
    async (error) => {
        console.error('Error en la respuesta:', error);
        
        if (error.response) {
            console.error('Datos del error:', error.response.data);
            console.error('Estado:', error.response.status);
            
            // Si el error es 401 (No autorizado)
            if (error.response.status === 401) {
                // Intentar refrescar el token
                const refresh_token = localStorage.getItem('refresh_token');
                if (refresh_token) {
                    try {
                        const response = await api.post('/api/token/refresh/', {
                            refresh: refresh_token
                        });
                        
                        if (response.data.access) {
                            localStorage.setItem('access_token', response.data.access);
                            error.config.headers.Authorization = `Bearer ${response.data.access}`;
                            return axios(error.config);
                        }
                    } catch (refreshError) {
                        console.error('Error al refrescar el token:', refreshError);
                        localStorage.removeItem('access_token');
                        localStorage.removeItem('refresh_token');
                        window.location.href = '/login';
                    }
                } else {
                    window.location.href = '/login';
                }
            }
        }
        
        return Promise.reject(error);
    }
);

// Exportar las configuraciones de API
export const comprasAPI = {
    // Compras
    getCompras: (params) => api.get('/api/compras/compras/', { params }),
    getCompra: (id) => api.get(`/api/compras/compras/${id}/`),
    createCompra: (data) => api.post('/api/compras/compras/', data),
    updateCompra: (id, data) => api.put(`/api/compras/compras/${id}/`, data),
    deleteCompra: (id) => api.delete(`/api/compras/compras/${id}/`),
    cambiarEstado: (id, estado) => api.patch(`/api/compras/compras/${id}/`, { estado }),
    cambiarMetodoPago: (id, metodoPago) => api.patch(`/api/compras/compras/${id}/`, { metodo_pago: metodoPago }),
    exportarExcel: () => api.get('/api/compras/compras/exportar_excel/', {
        responseType: 'blob',
        headers: {
            'Accept': '*/*',
            'Content-Type': 'application/json',
        }
    }),
    importarExcel: (data) => api.post('/api/compras/compras/importar_excel/', data),
    getEstadisticas: () => api.get('/api/compras/compras/estadisticas/'),
    getDetallesCompra: (id) => api.get(`/api/compras/compras/${id}/detalles/`),
    getPagosCompra: (id) => api.get(`/api/compras/compras/${id}/pagos/`),
    crearPagoCompra: (id, data) => api.post(`/api/compras/compras/${id}/pagos/`, data),
    getSaldoPendiente: (id) => api.get(`/api/compras/compras/${id}/saldo-pendiente/`),
    getComprasPendientes: () => api.get('/api/compras/compras/compras_pendientes/'),
    
    // Proveedores
    getProveedores: () => api.get('/api/compras/proveedores/'),
    getProveedor: (id) => api.get(`/api/compras/proveedores/${id}/`),
    createProveedor: (data) => api.post('/api/compras/proveedores/', data),
    updateProveedor: (id, data) => api.put(`/api/compras/proveedores/${id}/`, data),
    deleteProveedor: (id) => api.delete(`/api/compras/proveedores/${id}/`),
    
    // Productos
    getProductos: () => api.get('/api/inventario/productos/'),
    
    // Almacenes
    getAlmacenes: () => api.get('/api/inventario/almacenes/'),
    createAlmacen: (data) => api.post('/api/inventario/almacenes/', data),
    updateAlmacen: (id, data) => api.put(`/api/inventario/almacenes/${id}/`, data),
    deleteAlmacen: (id) => api.delete(`/api/inventario/almacenes/${id}/`),
    
    // Templates
    descargarTemplateCompras: () => api.get('/api/compras/template/descargar/', {
        responseType: 'arraybuffer',
        headers: {
            'Accept': '*/*',
            'Content-Type': 'application/json'
        }
    }),
};

export const authAPI = {
    login: async (credentials) => {
        try {
            const response = await api.post('/api/token/', credentials);
            if (response.data.access) {
                localStorage.setItem('access_token', response.data.access);
                localStorage.setItem('refresh_token', response.data.refresh);
                api.defaults.headers.common['Authorization'] = `Bearer ${response.data.access}`;
                
                const userResponse = await api.get('/api/auth/profile/');
                
                // Guardar empresa_id si existe
                if (userResponse.data.empresa_info?.id) {
                    localStorage.setItem('empresa_id', userResponse.data.empresa_info.id.toString());
                    console.log('Empresa ID guardado:', userResponse.data.empresa_info.id);
                } else {
                    console.warn('No se encontró empresa_info en el perfil del usuario');
                }
                
                return {
                    data: {
                        token: response.data.access,
                        user: userResponse.data
                    }
                };
            }
            throw new Error('No se recibió el token de acceso');
        } catch (error) {
            console.error('Error de login:', error.response?.data);
            throw error;
        }
    },
    
    logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('empresa_id'); // Limpiar también el empresa_id
        delete api.defaults.headers.common['Authorization'];
    },
    
    getProfile: async () => {
        try {
            const response = await api.get('/api/auth/profile/');
            
            // Actualizar empresa_id en localStorage si existe
            if (response.data.empresa_info?.id) {
                localStorage.setItem('empresa_id', response.data.empresa_info.id.toString());
            }
            
            return response.data;
        } catch (error) {
            console.error('Error al obtener perfil:', error);
            throw error;
        }
    },

    refreshToken: async () => {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
            throw new Error('No hay refresh token disponible');
        }
        
        try {
            const response = await api.post('/api/token/refresh/', {
                refresh: refreshToken
            });
            
            if (response.data.access) {
                localStorage.setItem('access_token', response.data.access);
                api.defaults.headers.common['Authorization'] = `Bearer ${response.data.access}`;
                return response.data.access;
            }
            throw new Error('No se recibió el token de acceso en el refresh');
        } catch (error) {
            console.error('Error al refrescar el token:', error);
            throw error;
        }
    }
};

// API para inventario
export const inventarioAPI = {
    // Productos
    getProductos: () => api.get('/api/inventario/productos/'),
    getProducto: (id) => api.get(`/api/inventario/productos/${id}/`),
    createProducto: (data) => api.post('/api/inventario/productos/', data),
    updateProducto: (id, data) => api.put(`/api/inventario/productos/${id}/`, data),
    deleteProducto: (id) => api.delete(`/api/inventario/productos/${id}/`),
    
    // Stock
    getStock: () => api.get('/api/inventario/productos/estadisticas/'),
    updateStock: (id, data) => api.put(`/api/inventario/productos/${id}/stock/`, data),
    
    // Categorías
    getCategorias: () => api.get('/api/inventario/categorias/'),
    createCategoria: (data) => api.post('/api/inventario/categorias/', data),
    updateCategoria: (id, data) => api.put(`/api/inventario/categorias/${id}/`, data),
    deleteCategoria: (id) => api.delete(`/api/inventario/categorias/${id}/`),
    
    // Almacenes
    getAlmacenes: () => api.get('/api/inventario/almacenes/'),
    createAlmacen: (data) => api.post('/api/inventario/almacenes/', data),
    updateAlmacen: (id, data) => api.put(`/api/inventario/almacenes/${id}/`, data),
    deleteAlmacen: (id) => api.delete(`/api/inventario/almacenes/${id}/`)
};