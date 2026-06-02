import { api } from '../lib/api';
import { queryClient } from '../lib/queryClient';

export const ventasService = {
  getVentas: async (page = 1, pageSize = 10) => {
    try {
      const response = await api.get(`/api/ventas/?page=${page}&page_size=${pageSize}`);
      return response.data;
    } catch (error) {
      console.error('Error al obtener ventas:', error);
      throw error;
    }
  },

  getVenta: async (id) => {
    try {
      const response = await api.get(`/api/ventas/${id}/`);
      return response.data;
    } catch (error) {
      console.error('Error al obtener venta:', error);
      throw error;
    }
  },

  async getClientes() {
    try {
      const response = await api.get('/api/ventas/clientes/');
      return response.data;
    } catch (error) {
      console.error('Error al obtener clientes:', error);
      throw error;
    }
  },

  async getProductos() {
    try {
      const response = await api.get('/api/inventario/productos/');
      // Asegurarnos de que los datos se procesen igual que en inventarioService
      const productos = Array.isArray(response.data) ? response.data : 
                       Array.isArray(response.data.results) ? response.data.results : [];

      const productosProcessed = productos.map(producto => {
        const stockTotal = parseFloat(producto.stock_total);
        const stockMinimo = parseFloat(producto.stock_minimo);

        return {
          ...producto,
          stock_total: isNaN(stockTotal) ? 0 : stockTotal,
          stock_minimo: isNaN(stockMinimo) ? 0 : stockMinimo,
          stock_maximo: parseFloat(producto.stock_maximo) || 0,
          precio_venta: parseFloat(producto.precio_venta) || 0,
          precio_compra: parseFloat(producto.precio_compra) || 0
        };
      });

      return productosProcessed;
    } catch (error) {
      console.error('Error detallado al obtener productos en ventas:', error);
      if (error.response) {
        console.error('Datos de la respuesta de error:', error.response.data);
        console.error('Estado de la respuesta:', error.response.status);
      }
      throw new Error('Error al obtener los productos');
    }
  },

  crearVenta: async (ventaData) => {
    try {
      // Determinar si ventaData es FormData u objeto
      const isFormData = ventaData instanceof FormData;
      
      // Si no es FormData, crear uno nuevo
      const formData = isFormData ? ventaData : new FormData();
      
      // Si no es FormData, agregar los campos
      if (!isFormData) {
        // Asegurar que el cliente sea un entero
        const clienteId = parseInt(ventaData.cliente);
        if (isNaN(clienteId)) {
          throw new Error('Cliente no válido');
        }
        
        formData.append('cliente', clienteId.toString());
        formData.append('fecha_emision', ventaData.fecha_emision);
        formData.append('tipo_venta', ventaData.tipo_venta);
        formData.append('metodo_pago', ventaData.metodo_pago);
        formData.append('igv_incluido', String(ventaData.igv_incluido));
        formData.append('moneda', ventaData.moneda || 'PEN');
        formData.append('referencia', ventaData.referencia || '');
        formData.append('estado', ventaData.estado || 'borrador');
        
        // Validar y procesar detalles
        if (!ventaData.detalles || !Array.isArray(ventaData.detalles) || ventaData.detalles.length === 0) {
          throw new Error('Debe incluir al menos un detalle de producto');
        }
        
        // Procesar detalles para asegurar tipos correctos
        const detallesProcesados = ventaData.detalles.map((detalle, index) => {
          const productoId = parseInt(detalle.producto);
          const cantidad = parseFloat(detalle.cantidad);
          const precio_unitario = parseFloat(detalle.precio_unitario);
          
          if (isNaN(productoId)) {
            throw new Error(`Producto no válido en detalle ${index + 1}`);
          }
          if (isNaN(cantidad) || cantidad <= 0) {
            throw new Error(`Cantidad no válida en detalle ${index + 1}`);
          }
          if (isNaN(precio_unitario) || precio_unitario <= 0) {
            throw new Error(`Precio no válido en detalle ${index + 1}`);
          }
          
          return {
            producto: productoId,
            cantidad: cantidad,
            precio_unitario: precio_unitario
          };
        });
        
        formData.append('detalles', JSON.stringify(detallesProcesados));

        // Si es venta a crédito, establecer fecha de vencimiento
        if (ventaData.tipo_venta !== 'contado' && ventaData.fecha_vencimiento) {
          formData.append('fecha_vencimiento', ventaData.fecha_vencimiento);
        }

        // Agregar comprobante si existe
        if (ventaData.comprobante) {
          formData.append('comprobante', ventaData.comprobante);
        }
      }

      // Log para debugging
      console.log('Datos enviados al servidor:', {
        cliente: formData.get('cliente'),
        fecha_emision: formData.get('fecha_emision'),
        tipo_venta: formData.get('tipo_venta'),
        metodo_pago: formData.get('metodo_pago'),
        igv_incluido: formData.get('igv_incluido'),
        moneda: formData.get('moneda'),
        estado: formData.get('estado'),
        detalles: formData.get('detalles')
      });

      const response = await api.post('/api/ventas/', formData);

      return {
        ...response.data,
        esCredito: formData.get('tipo_venta') === 'credito_30' || formData.get('tipo_venta') === 'credito_60'
      };
    } catch (error) {
      console.error('Error en crearVenta:', error);
      if (error.response?.data) {
        console.error('Error del servidor:', error.response.data);
      }
      throw new Error(error.response?.data?.error || error.message || 'Error al crear la venta');
    }
  },

  async actualizarVenta(id, ventaData) {
    try {
      const response = await api.put(`/api/ventas/${id}/`, ventaData);
      return response.data;
    } catch (error) {
      console.error('Error al actualizar venta:', error);
      throw error;
    }
  },

  async eliminarVenta(id) {
    try {
      const response = await api.delete(`/api/ventas/${id}/`);
      return response.data;
    } catch (error) {
      console.error('Error al eliminar venta:', error);
      throw error;
    }
  },

  async cambiarEstado(id, estado) {
    try {
      const response = await api.post(`/api/ventas/${id}/cambiar_estado/`, {
        estado: estado
      });
      return response.data;
    } catch (error) {
      console.error('Error al cambiar estado:', error);
      if (error.response?.data) {
        throw new Error(error.response.data.error || 'Error al cambiar el estado');
      }
      throw error;
    }
  },

  async exportarExcel() {
    try {
      const response = await api.get('/api/ventas/exportar_excel/', {
        responseType: 'blob'
      });
      let filename = 'Venta_' + new Date().toISOString().slice(0, 16).replace('T', '_').replace(':', '-') + '.xlsx';
      const disposition = response.headers['content-disposition'];
      if (disposition && disposition.indexOf('filename=') !== -1) {
        filename = disposition.split('filename=')[1].replace(/['"]/g, '');
      }
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error al exportar ventas:', error);
      throw error;
    }
  },

  // Nuevos endpoints para estadísticas
  async getVentasUltimos30Dias() {
    try {
      const response = await api.get('/api/ventas/estadisticas_ultimos_30_dias/');
      return response.data;
    } catch (error) {
      throw new Error('Error al obtener las estadísticas de ventas');
    }
  },

  async getTotalVentasUltimos30Dias() {
    try {
      const response = await api.get('/api/ventas/total_ultimos_30_dias/');
      return response.data;
    } catch (error) {
      throw new Error('Error al obtener el total de ventas');
    }
  },

  async getIGVRecaudado() {
    try {
      const response = await api.get('/api/ventas/igv_recaudado/');
      return response.data;
    } catch (error) {
      throw new Error('Error al obtener el IGV recaudado');
    }
  },

  updateVentaEstado: async (id, data) => {
    const response = await api.patch(`/api/ventas/${id}/`, data);
    return response.data;
  },

  getProductosMasVendidos: async (periodo = 'historico') => {
    const response = await api.get('/api/ventas/productos_mas_vendidos/', { params: { periodo } });
    return response.data;
  },

  getMejoresClientes: async () => {
    const response = await api.get('/api/ventas/mejores_clientes/');
    return response.data;
  },

  async descargarTemplate() {
    try {
      const response = await api.get('/api/ventas/descargar_template/', {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'template_ventas.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error al descargar el template de ventas:', error);
      throw error;
    }
  },

  async importarExcel(file) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/api/ventas/importar_excel/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  // Constantes para tipos de venta y métodos de pago
  TIPO_VENTA: {
    CONTADO: 'contado',
    CREDITO_30: 'credito_30',
    CREDITO_60: 'credito_60'
  },

  METODO_PAGO: {
    EFECTIVO: 'efectivo',
    TRANSFERENCIA: 'transferencia',
    TARJETA: 'tarjeta',
    CHEQUE: 'cheque'
  },

  ESTADO_VENTA: {
    BORRADOR: 'borrador',
    PENDIENTE: 'pendiente',
    PAGADO: 'pagado',
    ANULADO: 'anulado'
  },

  // Nuevos métodos para pagos
  getPagosVenta: async (ventaId) => {
    try {
      const response = await api.get(`/api/ventas/${ventaId}/pagos/`);
      return response.data;
    } catch (error) {
      console.error('Error al obtener pagos:', error);
      throw error;
    }
  },

  crearPago: async (ventaId, pagoData) => {
    try {
      const formData = new FormData();
      formData.append('fecha', pagoData.fecha);
      formData.append('monto', pagoData.monto);
      formData.append('metodo_pago', pagoData.metodo_pago);
      formData.append('referencia', pagoData.referencia || '');
      
      if (pagoData.comprobante) {
        formData.append('comprobante', pagoData.comprobante);
      }
      
      if (pagoData.notas) {
        formData.append('notas', pagoData.notas);
      }

      const response = await api.post(`/api/ventas/${ventaId}/pagos/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      return response.data;
    } catch (error) {
      console.error('Error al crear pago:', error);
      throw error;
    }
  },

  actualizarPago: async (ventaId, pagoId, pagoData) => {
    try {
      const formData = new FormData();
      formData.append('fecha', pagoData.fecha);
      formData.append('monto', pagoData.monto);
      formData.append('metodo_pago', pagoData.metodo_pago);
      formData.append('referencia', pagoData.referencia || '');
      
      if (pagoData.comprobante) {
        formData.append('comprobante', pagoData.comprobante);
      }
      
      if (pagoData.notas) {
        formData.append('notas', pagoData.notas);
      }

      const response = await api.put(`/api/ventas/${ventaId}/pagos/${pagoId}/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      return response.data;
    } catch (error) {
      console.error('Error al actualizar pago:', error);
      throw error;
    }
  },

  eliminarPago: async (ventaId, pagoId) => {
    try {
      await api.delete(`/api/ventas/${ventaId}/pagos/${pagoId}/`);
    } catch (error) {
      console.error('Error al eliminar pago:', error);
      throw error;
    }
  },

  getVentasPendientes: async () => {
    try {
      const response = await api.get('/api/ventas/ventas_pendientes/');
      return response.data;
    } catch (error) {
      console.error('Error al obtener ventas pendientes:', error);
      throw error;
    }
  },

  actualizarEstadoVenta: async (ventaId, data) => {
    try {
      const response = await api.patch(`/api/ventas/${ventaId}/`, data);
      
      // Invalidar las consultas relevantes para mantener la sincronización
      queryClient.invalidateQueries(['venta', ventaId]);
      queryClient.invalidateQueries(['ventas']);
      queryClient.invalidateQueries(['cuentas-por-cobrar']);
      
      return response.data;
    } catch (error) {
      console.error('Error al actualizar estado de venta:', error);
      throw error;
    }
  },

  getSaldoPendiente: async (ventaId) => {
    try {
      const response = await api.get(`/api/ventas/${ventaId}/saldo_pendiente/`);
      return response.data.saldo_pendiente;
    } catch (error) {
      console.error('Error al obtener saldo pendiente:', error);
      throw error;
    }
  },
};
