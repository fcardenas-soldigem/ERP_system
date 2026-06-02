import { api } from '../lib/api';

export const inventarioService = {
  // Productos
  getProductos: async () => {
    try {
      const response = await api.get('/api/inventario/productos/');
      console.log('Respuesta raw de productos:', response);
      console.log('Datos de productos:', response.data);

      // Asegurarnos de que los datos numéricos se procesen correctamente
      const productos = Array.isArray(response.data) ? response.data : 
                       Array.isArray(response.data.results) ? response.data.results : [];

      const productosProcessed = productos.map(producto => {
        const stockTotal = parseFloat(producto.stock_total);
        const stockMinimo = parseFloat(producto.stock_minimo);
        console.log(`Procesando producto ${producto.nombre}:`, {
          stock_original: producto.stock_total,
          stock_procesado: stockTotal,
          stock_minimo_original: producto.stock_minimo,
          stock_minimo_procesado: stockMinimo
        });

        return {
          ...producto,
          stock_total: isNaN(stockTotal) ? 0 : stockTotal,
          stock_minimo: isNaN(stockMinimo) ? 0 : stockMinimo,
          stock_maximo: parseFloat(producto.stock_maximo) || 0,
          precio_venta: parseFloat(producto.precio_venta) || 0,
          precio_compra: parseFloat(producto.precio_compra) || 0
        };
      });

      console.log('Productos procesados:', productosProcessed);
      return productosProcessed;
    } catch (error) {
      console.error('Error detallado al obtener productos:', error);
      if (error.response) {
        console.error('Datos de la respuesta de error:', error.response.data);
        console.error('Estado de la respuesta:', error.response.status);
      }
      throw new Error('Error al obtener los productos');
    }
  },

  getProducto: async (id) => {
    try {
      const response = await api.get(`/api/inventario/productos/${id}/`);
      const producto = response.data;
      // Asegurarnos de que los datos numéricos se procesen correctamente
      return {
        ...producto,
        stock_total: parseFloat(producto.stock_total) || 0,
        stock_minimo: parseFloat(producto.stock_minimo) || 0,
        stock_maximo: parseFloat(producto.stock_maximo) || 0,
        precio_venta: parseFloat(producto.precio_venta) || 0,
        precio_compra: parseFloat(producto.precio_compra) || 0
      };
    } catch (error) {
      console.error('Error al obtener el producto:', error);
      throw new Error('Error al obtener el producto');
    }
  },

  crearProducto: async (productoData) => {
    try {
      // Determinar si es materia prima
      const esMateriaPrima = productoData.tipo_producto === 'RAW' || productoData.tipo_producto === 'SEMIFINISHED';
      
      // Asegurarnos de que los datos numéricos se envíen correctamente
      // NOTA: precio_venta debe ser 0 (no null) para materias primas porque el modelo no permite null
      const dataToSend = {
        ...productoData,
        stock: parseFloat(productoData.stock_total) || 0,
        stock_total: parseFloat(productoData.stock_total) || 0,
        stock_minimo: parseFloat(productoData.stock_minimo) || 0,
        stock_maximo: parseFloat(productoData.stock_maximo) || 0,
        // Para materias primas, precio_venta = 0 (el modelo no permite null)
        precio_venta: esMateriaPrima ? 0 : (parseFloat(productoData.precio_venta) || 0),
        precio_compra: parseFloat(productoData.precio_compra) || 0,
        tipo_producto: productoData.tipo_producto || 'FINISHED',
        // Margen = 0 para materias primas
        margen_ganancia: esMateriaPrima ? 0 : (parseFloat(productoData.margen_ganancia) || 0)
      };

      console.log('Datos a enviar al crear producto:', dataToSend);
      console.log('Es materia prima:', esMateriaPrima);
      const response = await api.post('/api/inventario/productos/', dataToSend);
      console.log('Respuesta al crear producto:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error detallado al crear el producto:', error);
      if (error.response) {
        console.error('Datos de la respuesta de error:', error.response.data);
        console.error('Estado de la respuesta:', error.response.status);
        // Mostrar errores específicos
        const errorData = error.response.data;
        if (errorData?.non_field_errors) {
          console.error('NON_FIELD_ERRORS:', errorData.non_field_errors);
        }
        // Construir mensaje de error legible
        let errorMsg = 'Error al crear el producto';
        if (typeof errorData === 'object') {
          const errores = Object.entries(errorData)
            .map(([campo, msgs]) => `${campo}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
            .join('; ');
          if (errores) errorMsg = errores;
        }
        throw new Error(errorMsg);
      }
      throw new Error('Error al crear el producto');
    }
  },

  actualizarProducto: async (id, productoData) => {
    try {
      // Asegurarnos de que los datos numéricos se envíen correctamente
      const dataToSend = {
        ...productoData,
        stock_total: parseFloat(productoData.stock_total) || 0,
        stock_minimo: parseFloat(productoData.stock_minimo) || 0,
        stock_maximo: parseFloat(productoData.stock_maximo) || 0,
        precio_venta: parseFloat(productoData.precio_venta) || 0,
        precio_compra: parseFloat(productoData.precio_compra) || 0
      };

      console.log('Datos a enviar al actualizar producto:', dataToSend);
      const response = await api.put(`/api/inventario/productos/${id}/`, dataToSend);
      console.log('Respuesta al actualizar producto:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error al actualizar el producto:', error);
      throw new Error('Error al actualizar el producto');
    }
  },

  eliminarProducto: async (id) => {
    try {
      await api.delete(`/api/inventario/productos/${id}/`);
    } catch (error) {
      throw new Error('Error al eliminar el producto');
    }
  },

  // Categorías
  getCategorias: async () => {
    try {
      const response = await api.get('/api/inventario/categorias/');
      console.log('Respuesta raw de categorías:', response);
      
      // Asegurarnos de que devolvemos un array
      if (Array.isArray(response.data)) {
      return response.data;
      } else if (response.data && Array.isArray(response.data.results)) {
        return response.data.results;
      }
      
      console.warn('La respuesta de categorías no tiene el formato esperado:', response.data);
      return [];
    } catch (error) {
      console.error('Error detallado al obtener categorías:', error);
      throw new Error('Error al obtener las categorías');
    }
  },

  getCategoria: async (id) => {
    try {
      const response = await api.get(`/api/inventario/categorias/${id}/`);
      return response.data;
    } catch (error) {
      throw new Error('Error al obtener la categoría');
    }
  },

  crearCategoria: async (categoriaData) => {
    try {
      const response = await api.post('/api/inventario/categorias/', categoriaData);
      return response.data;
    } catch (error) {
      if (error.response?.data?.nombre) {
        throw new Error(error.response.data.nombre);
      }
      throw new Error('Error al crear la categoría');
    }
  },

  actualizarCategoria: async (id, categoriaData) => {
    try {
      const response = await api.put(`/api/inventario/categorias/${id}/`, categoriaData);
      return response.data;
    } catch (error) {
      throw new Error('Error al actualizar la categoría');
    }
  },

  eliminarCategoria: async (id) => {
    try {
      await api.delete(`/api/inventario/categorias/${id}/`);
    } catch (error) {
      throw new Error('Error al eliminar la categoría');
    }
  },

  // Almacenes
  getAlmacenes: async () => {
    try {
      const response = await api.get('/api/inventario/almacenes/');
      console.log('Respuesta getAlmacenes:', response.data);
      // Manejar respuesta paginada o array directo
      const data = response.data;
      if (Array.isArray(data)) {
        return data;
      } else if (data && Array.isArray(data.results)) {
        return data.results;
      }
      return [];
    } catch (error) {
      console.error('Error en getAlmacenes:', error);
      return []; // Retornar array vacío en caso de error
    }
  },

  getAlmacen: async (id) => {
    try {
      const response = await api.get(`/api/inventario/almacenes/${id}/`);
      return response.data;
    } catch (error) {
      throw new Error('Error al obtener el almacén');
    }
  },

  crearAlmacen: async (almacenData) => {
    try {
      const empresaId = localStorage.getItem('empresa_id');
      if (!empresaId) {
        throw new Error('No se encontró el ID de la empresa');
      }

      const dataConEmpresa = {
        ...almacenData,
        empresa: parseInt(empresaId)
      };

      console.log('Intentando crear almacén con datos:', dataConEmpresa);
      const response = await api.post('/api/inventario/almacenes/', dataConEmpresa);
      console.log('Respuesta del servidor:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error completo al crear almacén:', error.response || error);
      throw error;
    }
  },

  actualizarAlmacen: async (id, almacenData) => {
    try {
      const response = await api.put(`/api/inventario/almacenes/${id}/`, almacenData);
      return response.data;
    } catch (error) {
      throw new Error('Error al actualizar el almacén');
    }
  },

  eliminarAlmacen: async (id) => {
    try {
      await api.delete(`/api/inventario/almacenes/${id}/`);
    } catch (error) {
      throw new Error('Error al eliminar el almacén');
    }
  },

  // Valor total del inventario
  getValorTotalInventario: async () => {
    try {
      // Obtener todos los productos
      const productos = await inventarioService.getProductos();
      console.log('Productos para cálculo de valor total:', productos);

      // Calcular el valor total sumando (precio_compra * stock_total) de cada producto
      const valorTotal = productos.reduce((total, producto) => {
        const valorProducto = (parseFloat(producto.precio_compra) || 0) * (parseFloat(producto.stock_total) || 0);
        console.log(`Valor del producto ${producto.nombre}:`, {
          precio_compra: producto.precio_compra,
          stock_total: producto.stock_total,
          valor: valorProducto
        });
        return total + valorProducto;
      }, 0);

      console.log('Valor total calculado:', valorTotal);
      return { valor_total: valorTotal };
    } catch (error) {
      console.error('Error al calcular valor total:', error);
      return { valor_total: 0 };
    }
  },

  // Movimientos de inventario
  getMovimientos: async () => {
    try {
      const response = await api.get('/api/movimientos/');
      return response.data;
    } catch (error) {
      throw new Error('Error al obtener los movimientos');
    }
  },

  crearMovimiento: async (movimientoData) => {
    try {
      const response = await api.post('/api/movimientos/', movimientoData);
      return response.data;
    } catch (error) {
      throw new Error('Error al crear el movimiento');
    }
  },

  // Exportar inventario
  exportarInventario: async () => {
    try {
      const response = await api.get('/api/inventario/productos/exportar/', {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'inventario.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      throw new Error('Error al exportar el inventario');
    }
  },

  // Descargar template para importación
  descargarTemplate: async () => {
    try {
      console.log('Iniciando descarga del template...');
      const response = await api.get('/api/inventario/productos/template/descargar/', {
        responseType: 'arraybuffer',
        headers: {
          'Accept': '*/*',
          'Content-Type': 'application/json'
        }
      });
      
      console.log('Respuesta recibida:', response);
      
      // Crear blob y URL
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      const url = window.URL.createObjectURL(blob);
      
      // Crear link y forzar descarga
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'template_productos.xlsx');
      document.body.appendChild(link);
      link.click();
      
      // Limpieza
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        link.remove();
      }, 100);
      
      return true;
    } catch (error) {
      console.error('Error detallado al descargar template:', error);
      if (error.response) {
        console.error('Datos de la respuesta:', error.response);
        console.error('Mensaje de error:', error.response.data);
      }
      throw new Error('Error al descargar el template');
    }
  },

  // Importar productos desde Excel
  importarProductos: async (file) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await api.post('/api/inventario/productos/importar/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        }
      });
      
      console.log('Respuesta de importación:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error al importar productos:', error);
      throw error;
    }
  },

  // Descargar template para importación de compras
  descargarTemplateCompras: async () => {
    try {
      const response = await api.get('/api/compras/template/descargar/', {
        responseType: 'arraybuffer',
        headers: {
          'Accept': '*/*',
          'Content-Type': 'application/json'
        }
      });
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'template_compras.xlsx');
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        link.remove();
      }, 100);
      return true;
    } catch (error) {
      console.error('Error al descargar el template de compras:', error);
      throw new Error('Error al descargar el template de compras');
    }
  },

  async getValorTotalAdquisicion() {
    try {
      const response = await api.get('/api/inventario/productos/valor_total_adquisicion/');
      return response.data.valor_total_adquisicion;
    } catch (error) {
      console.error('Error al obtener el valor total de adquisición:', error);
      throw new Error('Error al obtener el valor total de adquisición');
    }
  },

  // Descargar kardex en Excel
  descargarKardex: async (params = {}) => {
    try {
      console.log('Solicitando descarga de kardex con parámetros:', params);
      
      // Construir query string con los parámetros
      const queryParams = new URLSearchParams();
      if (params.producto_id) queryParams.append('producto_id', params.producto_id);
      if (params.almacen_id) queryParams.append('almacen_id', params.almacen_id);
      if (params.fecha_inicio) queryParams.append('fecha_inicio', params.fecha_inicio);
      if (params.fecha_fin) queryParams.append('fecha_fin', params.fecha_fin);
      
      const queryString = queryParams.toString();
      const url = `/api/inventario/kardex/exportar_excel/${queryString ? '?' + queryString : ''}`;
      
      const response = await api.get(url, {
        responseType: 'arraybuffer',
        headers: {
          'Accept': '*/*',
          'Content-Type': 'application/json'
        }
      });
      
      console.log('Respuesta de kardex recibida:', response);
      return response.data;
    } catch (error) {
      console.error('Error detallado al descargar kardex:', error);
      if (error.response) {
        console.error('Datos de la respuesta:', error.response);
        console.error('Estado:', error.response.status);
      }
      throw new Error('Error al descargar el kardex');
    }
  },

  // Valor del inventario para el reporte detallado
  getValorInventario: async (filtros = {}) => {
    try {
      const response = await api.get('/api/inventario/valor-inventario/reporte_detallado/');
      return response.data;
    } catch (error) {
      console.error('Error al obtener valor del inventario:', error);
      throw new Error('Error al obtener valor del inventario');
    }
  },
  
  // Obtener bodegas (alias para almacenes)
  getBodegas: async () => {
    return await inventarioService.getAlmacenes();
  },

  // ========================================
  // INVENTARIOS SEPARADOS - MATERIAS PRIMAS
  // ========================================
  
  getMateriasPrimas: async () => {
    try {
      const response = await api.get('/api/inventario/materias-primas/');
      const data = Array.isArray(response.data) ? response.data : 
                   Array.isArray(response.data.results) ? response.data.results : [];
      return data.map(item => ({
        ...item,
        cantidad_disponible: parseFloat(item.cantidad_disponible) || 0,
        cantidad_reservada: parseFloat(item.cantidad_reservada) || 0,
        costo_unitario_promedio: parseFloat(item.costo_unitario_promedio) || 0,
        stock_minimo: parseFloat(item.stock_minimo) || 0,
        stock_maximo: parseFloat(item.stock_maximo) || 0,
      }));
    } catch (error) {
      console.error('Error al obtener materias primas:', error);
      throw new Error('Error al obtener materias primas');
    }
  },

  getMateriaPrima: async (id) => {
    try {
      const response = await api.get(`/api/inventario/materias-primas/${id}/`);
      return response.data;
    } catch (error) {
      console.error('Error al obtener materia prima:', error);
      throw new Error('Error al obtener materia prima');
    }
  },

  crearMateriaPrima: async (data) => {
    try {
      const response = await api.post('/api/inventario/materias-primas/', data);
      return response.data;
    } catch (error) {
      console.error('Error al crear materia prima:', error);
      throw error;
    }
  },

  actualizarMateriaPrima: async (id, data) => {
    try {
      const response = await api.put(`/api/inventario/materias-primas/${id}/`, data);
      return response.data;
    } catch (error) {
      console.error('Error al actualizar materia prima:', error);
      throw error;
    }
  },

  eliminarMateriaPrima: async (id) => {
    try {
      await api.delete(`/api/inventario/materias-primas/${id}/`);
    } catch (error) {
      console.error('Error al eliminar materia prima:', error);
      throw error;
    }
  },

  getMateriasPrimasStockBajo: async () => {
    try {
      const response = await api.get('/api/inventario/materias-primas/stock_bajo/');
      return response.data;
    } catch (error) {
      console.error('Error al obtener materias primas con stock bajo:', error);
      throw error;
    }
  },

  getMateriasPrimasPorVencer: async (dias = 30) => {
    try {
      const response = await api.get(`/api/inventario/materias-primas/por_vencer/?dias=${dias}`);
      return response.data;
    } catch (error) {
      console.error('Error al obtener materias primas por vencer:', error);
      throw error;
    }
  },

  getMateriasPrimasAlertas: async () => {
    try {
      const response = await api.get('/api/inventario/materias-primas/alertas/');
      return response.data;
    } catch (error) {
      console.error('Error al obtener alertas de materias primas:', error);
      throw error;
    }
  },

  registrarEntradaCompra: async (data) => {
    try {
      const response = await api.post('/api/inventario/materias-primas/entrada_compra/', data);
      return response.data;
    } catch (error) {
      console.error('Error al registrar entrada compra:', error);
      throw error;
    }
  },

  reservarMateriaParaProduccion: async (data) => {
    try {
      const response = await api.post('/api/inventario/materias-primas/reservar/', data);
      return response.data;
    } catch (error) {
      console.error('Error al reservar materia prima:', error);
      throw error;
    }
  },

  ajustarInventarioMateriaPrima: async (data) => {
    try {
      const response = await api.post('/api/inventario/materias-primas/ajustar/', data);
      return response.data;
    } catch (error) {
      console.error('Error al ajustar inventario:', error);
      throw error;
    }
  },

  getValorTotalMateriasPrimas: async () => {
    try {
      const response = await api.get('/api/inventario/materias-primas/valor_total/');
      return response.data;
    } catch (error) {
      console.error('Error al obtener valor total de materias primas:', error);
      throw error;
    }
  },

  // =============================================
  // INVENTARIOS SEPARADOS - PRODUCTOS TERMINADOS
  // =============================================
  
  getProductosTerminados: async () => {
    try {
      const response = await api.get('/api/inventario/productos-terminados/');
      const data = Array.isArray(response.data) ? response.data : 
                   Array.isArray(response.data.results) ? response.data.results : [];
      return data.map(item => ({
        ...item,
        cantidad_disponible: parseFloat(item.cantidad_disponible) || 0,
        cantidad_reservada: parseFloat(item.cantidad_reservada) || 0,
        costo_produccion_unitario: parseFloat(item.costo_produccion_unitario) || 0,
        precio_venta_sugerido: parseFloat(item.precio_venta_sugerido) || 0,
        stock_minimo: parseFloat(item.stock_minimo) || 0,
        stock_maximo: parseFloat(item.stock_maximo) || 0,
      }));
    } catch (error) {
      console.error('Error al obtener productos terminados:', error);
      throw new Error('Error al obtener productos terminados');
    }
  },

  getProductoTerminado: async (id) => {
    try {
      const response = await api.get(`/api/inventario/productos-terminados/${id}/`);
      return response.data;
    } catch (error) {
      console.error('Error al obtener producto terminado:', error);
      throw new Error('Error al obtener producto terminado');
    }
  },

  crearProductoTerminado: async (data) => {
    try {
      const response = await api.post('/api/inventario/productos-terminados/', data);
      return response.data;
    } catch (error) {
      console.error('Error al crear producto terminado:', error);
      throw error;
    }
  },

  actualizarProductoTerminado: async (id, data) => {
    try {
      const response = await api.put(`/api/inventario/productos-terminados/${id}/`, data);
      return response.data;
    } catch (error) {
      console.error('Error al actualizar producto terminado:', error);
      throw error;
    }
  },

  eliminarProductoTerminado: async (id) => {
    try {
      await api.delete(`/api/inventario/productos-terminados/${id}/`);
    } catch (error) {
      console.error('Error al eliminar producto terminado:', error);
      throw error;
    }
  },

  getProductosTerminadosStockBajo: async () => {
    try {
      const response = await api.get('/api/inventario/productos-terminados/stock_bajo/');
      return response.data;
    } catch (error) {
      console.error('Error al obtener productos terminados con stock bajo:', error);
      throw error;
    }
  },

  getProductosTerminadosAlertas: async () => {
    try {
      const response = await api.get('/api/inventario/productos-terminados/alertas/');
      return response.data;
    } catch (error) {
      console.error('Error al obtener alertas de productos terminados:', error);
      throw error;
    }
  },

  registrarEntradaProduccion: async (data) => {
    try {
      const response = await api.post('/api/inventario/productos-terminados/entrada_produccion/', data);
      return response.data;
    } catch (error) {
      console.error('Error al registrar entrada producción:', error);
      throw error;
    }
  },

  registrarSalidaVenta: async (data) => {
    try {
      const response = await api.post('/api/inventario/productos-terminados/salida_venta/', data);
      return response.data;
    } catch (error) {
      console.error('Error al registrar salida venta:', error);
      throw error;
    }
  },

  reservarProductoParaVenta: async (data) => {
    try {
      const response = await api.post('/api/inventario/productos-terminados/reservar/', data);
      return response.data;
    } catch (error) {
      console.error('Error al reservar producto:', error);
      throw error;
    }
  },

  ajustarInventarioProductoTerminado: async (data) => {
    try {
      const response = await api.post('/api/inventario/productos-terminados/ajustar/', data);
      return response.data;
    } catch (error) {
      console.error('Error al ajustar inventario:', error);
      throw error;
    }
  },

  getValorTotalProductosTerminados: async () => {
    try {
      const response = await api.get('/api/inventario/productos-terminados/valor_total/');
      return response.data;
    } catch (error) {
      console.error('Error al obtener valor total de productos terminados:', error);
      throw error;
    }
  },

  // ================================
  // RESUMEN INVENTARIOS SEPARADOS
  // ================================
  
  getResumenInventariosSeparados: async () => {
    try {
      const response = await api.get('/api/inventario/resumen-separado/');
      return response.data;
    } catch (error) {
      console.error('Error al obtener resumen de inventarios:', error);
      throw error;
    }
  },

  validarStockParaProduccion: async (materiales) => {
    try {
      const response = await api.post('/api/inventario/validar-stock-produccion/', { materiales });
      return response.data;
    } catch (error) {
      console.error('Error al validar stock para producción:', error);
      throw error;
    }
  },
};

