import axios from 'axios';

// Access token lives only in memory — never in localStorage or sessionStorage.
// This prevents XSS attacks from stealing the token via script injection.
let _accessToken = null;

export const setAccessToken = (token) => { _accessToken = token; };
export const getAccessToken = () => _accessToken;
export const clearAccessToken = () => { _accessToken = null; };

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Required so the httpOnly refresh cookie is sent automatically
});

// Prevents concurrent 401s from triggering multiple simultaneous refresh attempts.
let _isRefreshing = false;

const _redirectToLogin = () => {
  // replace() avoids adding /login to history (prevents back-button loop).
  // Guard prevents reload loop when already on /login.
  if (window.location.pathname !== '/login') {
    window.location.replace('/login');
  }
};

api.interceptors.request.use(
  (config) => {
    if (_accessToken) {
      config.headers.Authorization = `Bearer ${_accessToken}`;
    }

    if (config.data instanceof FormData) {
      delete config.headers['Content-Type'];
    } else if (!config.headers['Content-Type']) {
      config.headers['Content-Type'] = 'application/json';
    }

    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Any /token endpoint failure means the session is dead — bail immediately.
    if (originalRequest.url?.includes('/token')) {
      _isRefreshing = false;
      clearAccessToken();
      _redirectToLogin();
      return Promise.reject(error);
    }

    if (error.response?.status === 401 && !originalRequest._retry && !_isRefreshing) {
      originalRequest._retry = true;
      _isRefreshing = true;

      try {
        // Cookie is sent automatically via withCredentials — no token in request body
        await authAPI.refreshToken();
        _isRefreshing = false;
        return api(originalRequest);
      } catch {
        _isRefreshing = false;
        clearAccessToken();
        _redirectToLogin();
        return Promise.reject(error);
      }
    }

    return Promise.reject(error);
  }
);

export { api };
export default api;

export const comprasAPI = {
  getCompras: (params) => api.get('/api/compras/compras/', { params }),
  getCompra: (id) => api.get(`/api/compras/compras/${id}/`),
  createCompra: (data) => api.post('/api/compras/compras/', data),
  updateCompra: (id, data) => api.put(`/api/compras/compras/${id}/`, data),
  deleteCompra: (id) => api.delete(`/api/compras/compras/${id}/`),
  cambiarEstado: (id, estado) =>
    api.patch(`/api/compras/compras/${id}/`, { estado }),
  cambiarMetodoPago: (id, metodoPago) =>
    api.patch(`/api/compras/compras/${id}/`, { metodo_pago: metodoPago }),
  exportarExcel: () =>
    api.get('/api/compras/compras/exportar_excel/', {
      responseType: 'blob',
      headers: { Accept: '*/*', 'Content-Type': 'application/json' },
    }),
  importarExcel: (data) =>
    api.post('/api/compras/compras/importar_excel/', data),
  getEstadisticas: () => api.get('/api/compras/compras/estadisticas/'),
  getDetallesCompra: (id) =>
    api.get(`/api/compras/compras/${id}/detalles/`),
  getPagosCompra: (id) => api.get(`/api/compras/compras/${id}/pagos/`),
  crearPagoCompra: (id, data) =>
    api.post(`/api/compras/compras/${id}/pagos/`, data),
  getSaldoPendiente: (id) =>
    api.get(`/api/compras/compras/${id}/saldo-pendiente/`),
  getComprasPendientes: () =>
    api.get('/api/compras/compras/compras_pendientes/'),

  getProveedores: () => api.get('/api/compras/proveedores/'),
  getProveedor: (id) => api.get(`/api/compras/proveedores/${id}/`),
  createProveedor: (data) => api.post('/api/compras/proveedores/', data),
  updateProveedor: (id, data) =>
    api.put(`/api/compras/proveedores/${id}/`, data),
  deleteProveedor: (id) => api.delete(`/api/compras/proveedores/${id}/`),

  getProductos: () => api.get('/api/inventario/productos/'),

  getAlmacenes: () => api.get('/api/inventario/almacenes/'),
  createAlmacen: (data) => api.post('/api/inventario/almacenes/', data),
  updateAlmacen: (id, data) =>
    api.put(`/api/inventario/almacenes/${id}/`, data),
  deleteAlmacen: (id) => api.delete(`/api/inventario/almacenes/${id}/`),

  descargarTemplateCompras: () =>
    api.get('/api/compras/template/descargar/', {
      responseType: 'arraybuffer',
      headers: { Accept: '*/*', 'Content-Type': 'application/json' },
    }),
};

export const authAPI = {
  login: async (credentials) => {
    try {
      const response = await api.post('/api/token/', credentials);
      if (response.data.access) {
        // Store access token in memory only — refresh token is in httpOnly cookie
        setAccessToken(response.data.access);

        const userResponse = await api.get('/api/auth/profile/');

        if (userResponse.data.empresa_info?.id) {
          localStorage.setItem(
            'empresa_id',
            userResponse.data.empresa_info.id.toString()
          );
        }

        return {
          data: {
            token: response.data.access,
            user: userResponse.data,
          },
        };
      }
      throw new Error('No se recibió el token de acceso');
    } catch (error) {
      console.error('Error de login:', error.response?.data);
      throw error;
    }
  },

  logout: () => {
    clearAccessToken();
    localStorage.removeItem('empresa_id');
    delete api.defaults.headers.common['Authorization'];
    // Fire-and-forget: ask backend to blacklist the token and clear the httpOnly cookie
    api.post('/api/auth/logout/', {}).catch(() => {});
  },

  getProfile: async () => {
    try {
      const response = await api.get('/api/auth/profile/');

      if (response.data.empresa_info?.id) {
        localStorage.setItem(
          'empresa_id',
          response.data.empresa_info.id.toString()
        );
      }

      return response.data;
    } catch (error) {
      console.error('Error al obtener perfil:', error);
      throw error;
    }
  },

  refreshToken: async () => {
    try {
      // Cookie is sent automatically — no token needed in body
      const response = await api.post('/api/token/refresh/', {});

      if (response.data.access) {
        setAccessToken(response.data.access);
        return response.data.access;
      }
      throw new Error('No se recibió el token de acceso en el refresh');
    } catch (error) {
      console.error('Error al refrescar el token:', error);
      throw error;
    }
  },
};

export const inventarioAPI = {
  getProductos: () => api.get('/api/inventario/productos/'),
  getProducto: (id) => api.get(`/api/inventario/productos/${id}/`),
  createProducto: (data) => api.post('/api/inventario/productos/', data),
  updateProducto: (id, data) =>
    api.put(`/api/inventario/productos/${id}/`, data),
  deleteProducto: (id) => api.delete(`/api/inventario/productos/${id}/`),

  getStock: () => api.get('/api/inventario/productos/estadisticas/'),
  updateStock: (id, data) =>
    api.put(`/api/inventario/productos/${id}/stock/`, data),

  getCategorias: () => api.get('/api/inventario/categorias/'),
  createCategoria: (data) => api.post('/api/inventario/categorias/', data),
  updateCategoria: (id, data) =>
    api.put(`/api/inventario/categorias/${id}/`, data),
  deleteCategoria: (id) => api.delete(`/api/inventario/categorias/${id}/`),

  getAlmacenes: () => api.get('/api/inventario/almacenes/'),
  createAlmacen: (data) => api.post('/api/inventario/almacenes/', data),
  updateAlmacen: (id, data) =>
    api.put(`/api/inventario/almacenes/${id}/`, data),
  deleteAlmacen: (id) => api.delete(`/api/inventario/almacenes/${id}/`),
};
