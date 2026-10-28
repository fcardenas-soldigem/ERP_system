import { authAPI } from '../lib/api';

export const MENSAJE_SIN_EMPRESA =
  'Tu usuario no tiene una empresa asignada. Pide al administrador que te asigne una.';

export const MENSAJE_SIN_CONEXION =
  'No hay conexión con el servidor. Revisa tu internet e inténtalo de nuevo.';

// El backend responde 403 {detail: 'Usuario no tiene empresa asignada'} (HasEmpresaPermission)
// en /api/auth/profile/ cuando el usuario existe pero no tiene empresa. Mensaje claro en vez del
// genérico. Cualquier otro error conserva el detalle del backend o el texto por defecto.
// QW5 — sin respuesta HTTP = problema de red, no de contraseña: con 4G
// inestable "Credenciales inválidas" hacía creer al vendedor que olvidó su clave.
export const mensajeErrorLogin = (error, porDefecto = 'Credenciales inválidas') => {
  if (error && !error.response) return MENSAJE_SIN_CONEXION;
  if (error?.response?.status === 403) return MENSAJE_SIN_EMPRESA;
  if (error?.response?.status >= 500) return 'El servidor tuvo un problema. Inténtalo en unos minutos.';
  return error?.response?.data?.detail || porDefecto;
};

export const authService = {
  login: authAPI.login,
  logout: authAPI.logout,
  getProfile: authAPI.getProfile,
  refreshToken: authAPI.refreshToken
}; 