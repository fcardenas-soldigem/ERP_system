import { authAPI } from '../lib/api';
import { useAuth } from '../components/context/AuthContext';

/**
 * Envuelve acciones críticas con una renovación proactiva del access token.
 * Si la acción retorna 401 el hook invoca refreshUser() para re-autenticar
 * desde la cookie httpOnly o redirigir al login si la sesión expiró.
 */
export const useSecureAction = () => {
  const { refreshUser } = useAuth();

  const executeSecure = async (action) => {
    // Renovar el token antes de la acción crítica para minimizar el riesgo
    // de que expire justo durante la operación (ventana de 15 min).
    try {
      await authAPI.refreshToken();
    } catch {
      // Si el refresh falla, la acción fallará con 401 y el bloque de abajo
      // o el interceptor global manejará la re-autenticación.
    }

    try {
      return await action();
    } catch (error) {
      if (error.response?.status === 401) {
        refreshUser();
      }
      throw error;
    }
  };

  return { executeSecure };
};
