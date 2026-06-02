import { getAccessToken, clearAccessToken } from '../lib/api';

export const checkAuthTokens = () => {
  const token = getAccessToken();

  console.log('🔐 Estado de autenticación:');
  console.log('  Token access:', token ? '✅ Presente (en memoria)' : '❌ Ausente');
  console.log('  Refresh token: httpOnly cookie (inaccesible desde JS)');

  if (token) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const exp = new Date(payload.exp * 1000);
      const now = new Date();

      console.log('  Expira:', exp.toLocaleString());
      console.log('  Estado:', now > exp ? '❌ Expirado' : '✅ Válido');
      console.log('  Usuario:', payload.username || payload.user_id);

      return {
        hasToken: true,
        isExpired: now > exp,
        expiresAt: exp,
        user: payload.username || payload.user_id
      };
    } catch (error) {
      console.log('  ❌ Token inválido/corrupto');
      return { hasToken: true, isExpired: true, error: 'Token corrupto' };
    }
  }

  return { hasToken: false };
};

export const clearAuthTokens = () => {
  clearAccessToken();
  console.log('🧹 Access token eliminado de memoria. Refresh token en cookie httpOnly — usa logout() para eliminarlo.');
};

export const testApiCall = async () => {
  try {
    const api = (await import('../lib/api')).default;
    console.log('🧪 Probando llamada API...');

    const response = await api.get('/api/core/consultar-dni/?dni=70774842');
    console.log('✅ API funciona correctamente:', response.data);
    return true;
  } catch (error) {
    console.log('❌ Error en API:', error.response?.status, error.message);
    return false;
  }
};

// Función global para usar en consola del navegador
window.debugAuth = {
  check: checkAuthTokens,
  clear: clearAuthTokens,
  test: testApiCall
};
