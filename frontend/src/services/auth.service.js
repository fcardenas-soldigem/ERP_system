import { authAPI } from '../lib/api';

export const MENSAJE_SIN_EMPRESA =
  'Tu usuario no tiene una empresa asignada. Pide al administrador que te asigne una.';

// El backend responde 403 {detail: 'Usuario no tiene empresa asignada'} (HasEmpresaPermission)
// en /api/auth/profile/ cuando el usuario existe pero no tiene empresa. Mensaje claro en vez del
// genérico. Cualquier otro error conserva el detalle del backend o el texto por defecto.
export const mensajeErrorLogin = (error, porDefecto = 'Credenciales inválidas') =>
  error?.response?.status === 403
    ? MENSAJE_SIN_EMPRESA
    : error?.response?.data?.detail || porDefecto;

export const authService = {
  login: authAPI.login,
  logout: authAPI.logout,
  getProfile: authAPI.getProfile,
  refreshToken: authAPI.refreshToken
}; 