// Script de debug para CompraForm - Prueba de productos y almacenes
console.log('=== DEBUG COMPRAS ===');

// Función para probar las APIs
async function debugCompras() {
  try {
    // Obtener token de localStorage (simular frontend)
    const accessToken = localStorage.getItem('access_token');
    if (!accessToken) {
      console.error('❌ No hay token de acceso');
      return;
    }
    
    console.log('✅ Token encontrado:', accessToken.substring(0, 20) + '...');
    
    // Configurar headers
    const headers = {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    };
    
    console.log('\n--- Probando API de Productos ---');
    
    // Probar productos
    const productosResponse = await fetch('/api/inventario/productos/', {
      method: 'GET',
      headers: headers
    });
    
    console.log('Status productos:', productosResponse.status);
    
    if (productosResponse.ok) {
      const productosData = await productosResponse.json();
      console.log('✅ Productos obtenidos:', productosData);
      console.log('✅ Es array:', Array.isArray(productosData));
      
      if (Array.isArray(productosData)) {
        console.log('✅ Cantidad de productos:', productosData.length);
      } else if (productosData.results && Array.isArray(productosData.results)) {
        console.log('✅ Cantidad de productos (paginado):', productosData.results.length);
      }
    } else {
      const errorData = await productosResponse.text();
      console.error('❌ Error productos:', errorData);
    }
    
    console.log('\n--- Probando API de Almacenes ---');
    
    // Probar almacenes
    const almacenesResponse = await fetch('/api/compras/almacenes/', {
      method: 'GET',
      headers: headers
    });
    
    console.log('Status almacenes:', almacenesResponse.status);
    
    if (almacenesResponse.ok) {
      const almacenesData = await almacenesResponse.json();
      console.log('✅ Almacenes obtenidos:', almacenesData);
      console.log('✅ Es array:', Array.isArray(almacenesData));
      
      if (Array.isArray(almacenesData)) {
        console.log('✅ Cantidad de almacenes:', almacenesData.length);
      } else if (almacenesData.results && Array.isArray(almacenesData.results)) {
        console.log('✅ Cantidad de almacenes (paginado):', almacenesData.results.length);
      }
    } else {
      const errorData = await almacenesResponse.text();
      console.error('❌ Error almacenes:', errorData);
    }
    
  } catch (error) {
    console.error('❌ Error general:', error);
  }
}

// Ejecutar debug
debugCompras();

console.log('=== FIN DEBUG ==='); 