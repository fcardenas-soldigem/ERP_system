// Script de prueba para la descarga de kardex
console.log('=== TEST DESCARGA KARDEX ===');

async function testDescargaKardex() {
  try {
    // Obtener token de acceso
    const accessToken = localStorage.getItem('access_token');
    if (!accessToken) {
      console.error('❌ No hay token de acceso');
      return;
    }
    
    console.log('✅ Token encontrado');
    
    // Probar endpoint de kardex
    console.log('\n--- Probando endpoint de kardex ---');
    
    const headers = {
      'Authorization': `Bearer ${accessToken}`,
      'Accept': '*/*'
    };
    
    const response = await fetch('/api/inventario/kardex/exportar_excel/', {
      method: 'GET',
      headers: headers
    });
    
    console.log('Status de respuesta:', response.status);
    console.log('Headers de respuesta:', response.headers);
    
    if (response.ok) {
      console.log('✅ Endpoint de kardex responde correctamente');
      
      // Obtener el blob
      const blob = await response.blob();
      console.log('✅ Tamaño del archivo:', blob.size, 'bytes');
      console.log('✅ Tipo de archivo:', blob.type);
      
      // Simular descarga
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `test_kardex_${new Date().toISOString().split('T')[0]}.xlsx`;
      
      console.log('✅ Archivo listo para descarga');
      console.log('📥 Para descargar, ejecute: link.click()');
      
      // Limpiar después de un tiempo
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        console.log('🧹 Recursos limpiados');
      }, 5000);
      
    } else {
      const errorText = await response.text();
      console.error('❌ Error en endpoint:', response.status, errorText);
    }
    
  } catch (error) {
    console.error('❌ Error general:', error);
  }
}

// Función para probar también los movimientos de kardex
async function testMovimientosKardex() {
  try {
    const accessToken = localStorage.getItem('access_token');
    if (!accessToken) {
      console.error('❌ No hay token de acceso');
      return;
    }
    
    console.log('\n--- Probando movimientos de kardex ---');
    
    const headers = {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    };
    
    const response = await fetch('/api/inventario/kardex/', {
      method: 'GET',
      headers: headers
    });
    
    console.log('Status movimientos:', response.status);
    
    if (response.ok) {
      const data = await response.json();
      console.log('✅ Movimientos obtenidos:', data);
      console.log('📊 Cantidad de movimientos:', data.results?.length || data.length || 0);
    } else {
      const errorText = await response.text();
      console.error('❌ Error en movimientos:', response.status, errorText);
    }
    
  } catch (error) {
    console.error('❌ Error al obtener movimientos:', error);
  }
}

// Ejecutar pruebas
console.log('🚀 Iniciando pruebas...');
testDescargaKardex();
testMovimientosKardex();

console.log('\n=== FIN TEST ==='); 