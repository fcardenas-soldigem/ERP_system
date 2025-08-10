/**
 * Utilidades para debuggear problemas de autenticación
 */

export const checkAuthTokens = () => {
  const token = localStorage.getItem('access_token');
  const refreshToken = localStorage.getItem('refresh_token');
  
  console.log('🔐 Estado de autenticación:');
  console.log('  Token access:', token ? '✅ Presente' : '❌ Ausente');
  console.log('  Token refresh:', refreshToken ? '✅ Presente' : '❌ Ausente');
  
  if (token) {
    try {
      // Decodificar JWT para ver expiración
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
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  console.log('🧹 Tokens eliminados del localStorage');
};

export const testApiCall = async () => {
  try {
    const api = (await import('../services/api.jsx')).default;
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