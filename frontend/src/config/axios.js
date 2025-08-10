import axios from 'axios';

const instance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para agregar el token a todas las peticiones
instance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor para manejar errores
instance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Si el error es 401 y no hemos intentado renovar el token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          try {
            const response = await instance.post('/api/token/refresh/', {
              refresh: refreshToken
            });
            
            if (response.data.access) {
              localStorage.setItem('access_token', response.data.access);
              instance.defaults.headers.common['Authorization'] = `Bearer ${response.data.access}`;
              originalRequest.headers['Authorization'] = `Bearer ${response.data.access}`;
              return instance(originalRequest);
            }
          } catch (refreshError) {
            console.error('Error al renovar el token:', refreshError);
          }
        }
      } catch (refreshError) {
        console.error('Error al renovar el token:', refreshError);
      }

      // Solo redirigir al login si no estamos ya en la página de login
      if (window.location.pathname !== '/login') {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('empresa_id');
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

export default instance; 