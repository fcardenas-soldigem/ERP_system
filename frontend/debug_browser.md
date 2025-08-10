# 🔧 Guía de Debug para Problemas de Autenticación

## Para ejecutar en la consola del navegador (F12):

### 1. Verificar estado actual de tokens:
```javascript
console.log('=== ESTADO DE TOKENS ===');
console.log('access_token:', localStorage.getItem('access_token') ? '✅ Presente' : '❌ Ausente');
console.log('refresh_token:', localStorage.getItem('refresh_token') ? '✅ Presente' : '❌ Ausente');

// Verificar si el token está expirado
const token = localStorage.getItem('access_token');
if (token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = new Date(payload.exp * 1000);
    const now = new Date();
    console.log('Token expira:', exp.toLocaleString());
    console.log('Estado:', now > exp ? '❌ Expirado' : '✅ Válido');
  } catch(e) {
    console.log('❌ Token corrupto');
  }
}
```

### 2. Limpiar tokens corruptos:
```javascript
localStorage.removeItem('access_token');
localStorage.removeItem('refresh_token');
console.log('🧹 Tokens eliminados');
```

### 3. Copiar tokens válidos del login actual:
Después de hacer login exitoso con las credenciales del sistema, ejecutar:
```javascript
// Obtener tokens del login actual (después de hacer login exitoso)
const access_token = localStorage.getItem('access_token');
const refresh_token = localStorage.getItem('refresh_token');

console.log('=== TOKENS DESPUÉS DEL LOGIN ===');
console.log('access_token:', access_token ? access_token.substring(0, 50) + '...' : 'No encontrado');
console.log('refresh_token:', refresh_token ? refresh_token.substring(0, 50) + '...' : 'No encontrado');
```

### 4. Probar consulta de documento:
```javascript
// Probar llamada API directamente
fetch('/api/core/consultar-documento/?numero=70774842&tipo=dni', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
    'Content-Type': 'application/json'
  }
})
.then(response => {
  console.log('Status:', response.status);
  return response.json();
})
.then(data => console.log('Respuesta:', data))
.catch(error => console.error('Error:', error));
```

## Problema común:
Si ves "No hay refresh token disponible", significa que el usuario está logueado pero los tokens no están sincronizados.

**Solución:** 
1. Cerrar sesión completamente
2. Iniciar sesión nuevamente 
3. Los tokens se guardarán correctamente 