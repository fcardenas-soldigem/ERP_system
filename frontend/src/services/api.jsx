import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Interceptor para agregar el token a las peticiones
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        console.error('Error en la petición:', error);
        return Promise.reject(error);
    }
);

// Interceptor para manejar las respuestas
api.interceptors.response.use(
    (response) => {
        return response;
    },
    async (error) => {
        const originalRequest = error.config;

        // Si el error es 401 y no es un reintento
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
                // Verificar si hay refresh token antes de intentar renovar
                const refreshToken = localStorage.getItem('refresh_token');
                if (!refreshToken) {
                    console.warn('No hay refresh token disponible');
                    // En lugar de redirigir inmediatamente, solo removemos tokens inválidos
                    localStorage.removeItem('access_token');
                    return Promise.reject(error);
                }

                console.log('Intentando renovar token...');
                const response = await axios.post(
                    `${api.defaults.baseURL}/api/token/refresh/`,
                    { refresh: refreshToken }
                );

                const { access } = response.data;
                localStorage.setItem('access_token', access);
                console.log('Token renovado exitosamente');

                // Actualizar el token en la petición original y reintentarla
                originalRequest.headers.Authorization = `Bearer ${access}`;
                return api(originalRequest);
            } catch (refreshError) {
                console.error('Error al renovar token:', refreshError);
                
                // Solo limpiar tokens y redirigir si realmente es un problema de autenticación
                // No redirigir si es un problema de red o servidor
                if (refreshError.response?.status === 401 || refreshError.response?.status === 403) {
                    console.warn('Refresh token inválido, limpiando sesión...');
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                    
                    // Usar setTimeout para evitar redirección inmediata durante pruebas
                    setTimeout(() => {
                        if (window.location.pathname !== '/login') {
                            window.location.href = '/login';
                        }
                    }, 100);
                }
                
                return Promise.reject(refreshError);
            }
        }

        // Si el error es 403, mostrar mensaje de error de permisos
        if (error.response?.status === 403) {
            console.error('Error de permisos:', error.response.data);
        }

        // Si el error es 500, mostrar mensaje de error del servidor
        if (error.response?.status === 500) {
            console.error('Error del servidor:', error.response.data);
        }

        return Promise.reject(error);
    }
);

export default api; 