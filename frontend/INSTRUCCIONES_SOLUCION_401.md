# Solución al Error 401 (Unauthorized)

## Problema
Los tokens JWT han expirado y necesitan ser renovados.

## Solución Rápida

### Opción 1: Desde la Consola del Navegador (Recomendado)
1. Abre la consola del navegador (F12 o Cmd+Option+I en Mac)
2. Ve a la pestaña "Console"
3. Ejecuta este comando:
```javascript
localStorage.clear();
window.location.reload();
```

### Opción 2: Desde el Navegador
1. Abre las DevTools (F12)
2. Ve a la pestaña "Application" (Chrome/Edge) o "Storage" (Firefox)
3. En el menú lateral, busca "Local Storage"
4. Haz clic en tu dominio (http://localhost:3000)
5. Haz clic derecho y selecciona "Clear"
6. Recarga la página (F5 o Cmd+R)

### Opción 3: Cerrar Sesión
1. Si puedes ver la interfaz, simplemente cierra sesión
2. Vuelve a iniciar sesión

## ¿Por qué ocurre esto?
Los tokens JWT tienen un tiempo de vida limitado por seguridad. Cuando expiran, el backend rechaza las peticiones con un error 401.

## Prevención
El sistema debería renovar automáticamente los tokens, pero si acabas de hacer cambios en la configuración de seguridad, es normal que los tokens antiguos ya no sean válidos.


