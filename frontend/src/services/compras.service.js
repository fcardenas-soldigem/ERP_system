import { comprasAPI } from '../lib/api';
import { api } from '../lib/api';
import axios from 'axios';
import { queryClient } from '../lib/queryClient';

export const comprasService = {
  getCompras: async (page = 1, pageSize = 10) => {
    try {
      const empresaId = localStorage.getItem('empresa_id');

      if (!empresaId) {
        // Intentar obtener el perfil del usuario para conseguir el empresa_id
        try {
          const response = await api.get('/api/auth/profile/');
          if (response.data.empresa_info?.id) {
            const newEmpresaId = response.data.empresa_info.id.toString();
            localStorage.setItem('empresa_id', newEmpresaId);
            // Continuar con el nuevo empresa_id
            return await comprasService.getCompras(page, pageSize);
          } else {
            throw new Error('El usuario no tiene una empresa asignada. Por favor, contacte al administrador.');
          }
        } catch (profileError) {
          throw new Error('No se pudo obtener la información de la empresa. Por favor, cierre sesión e inicie sesión nuevamente.');
        }
      }

      
      const response = await api.get('/api/compras/compras/', {
        params: {
          page,
          page_size: pageSize,
          empresa: empresaId
        }
      });
      
      if (!response.data) {
        throw new Error('No se recibieron datos del servidor');
      }

      return response.data;
    } catch (error) {
      if (error.response?.status === 401) {
        localStorage.removeItem('empresa_id');
        throw new Error('Sesión expirada. Por favor, inicie sesión nuevamente.');
      }
      throw error;
    }
  },

  getCompra: async (id) => {
    try {
      const response = await api.get(`/api/compras/compras/${id}/`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  getProveedores: async () => {
    try {
      const response = await comprasAPI.getProveedores();
      return Array.isArray(response.data) ? response.data : 
             Array.isArray(response.data.results) ? response.data.results : [];
    } catch (error) {
      throw error;
    }
  },

  getProductos: async () => {
    try {
      const response = await api.get('/api/inventario/productos/');
      return Array.isArray(response.data) ? response.data : 
             Array.isArray(response.data.results) ? response.data.results : [];
    } catch (error) {
      throw error;
    }
  },

  createCompra: async (compraData) => {
    try {

      // Validar datos requeridos
      if (!compraData.get('proveedor')) {
        throw new Error('El proveedor es requerido');
      }
      if (!compraData.get('almacen')) {
        throw new Error('El almacén es requerido');
      }

      // Obtener y validar detalles
      const detallesStr = compraData.get('detalles');
      if (!detallesStr) {
        throw new Error('Los detalles son requeridos');
      }

      const detalles = JSON.parse(detallesStr);
      if (!detalles.length) {
        throw new Error('Debe agregar al menos un producto');
      }

      // Validar que todos los detalles sean válidos
      const detallesInvalidos = detalles.some(
        detalle => !detalle.producto || !detalle.cantidad || detalle.cantidad <= 0 || !detalle.precio_unitario || detalle.precio_unitario <= 0
      );

      if (detallesInvalidos) {
        throw new Error('Todos los productos deben tener cantidad y precio mayor a 0');
      }

      // Calcular totales
      const subtotalBruto = detalles.reduce((acc, detalle) => 
        acc + (parseFloat(detalle.cantidad) * parseFloat(detalle.precio_unitario)), 0
      );

      const igvIncluido = compraData.get('igv_incluido') === 'true';
      let subtotal, igv, total;

      if (igvIncluido) {
        subtotal = subtotalBruto / 1.18;
        igv = subtotalBruto - subtotal;
        total = subtotalBruto;
      } else {
        subtotal = subtotalBruto;
        igv = subtotal * 0.18;
        total = subtotal + igv;
      }

      // Agregar los totales calculados al FormData
      compraData.append('subtotal', subtotal.toFixed(2));
      compraData.append('igv', igv.toFixed(2));
      compraData.append('total', total.toFixed(2));

      // Enviar la solicitud
      const response = await comprasAPI.createCompra(compraData);

      return response.data;
    } catch (error) {
      if (error.response?.data) {
      }
      throw error;
    }
  },

  updateCompra: async (id, data) => {
    const response = await comprasAPI.updateCompra(id, data);
    return response.data;
  },

  deleteCompra: async (id) => {
    const response = await comprasAPI.deleteCompra(id);
    return response.data;
  },

  cambiarEstado: async (compraId, nuevoEstado) => {
    try {
      const response = await api.post(`/api/compras/compras/${compraId}/cambiar-estado/`, {
        estado: nuevoEstado
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  bulkCambiarEstado: async (ids, estado) => {
    const response = await api.post('/api/compras/compras/bulk-estado/', { ids, estado });
    return response.data;
  },

  getCountByEstado: async () => {
    const empresaId = localStorage.getItem('empresa_id');
    const response = await api.get('/api/compras/compras/', {
      params: { empresa: empresaId, page_size: 1000 }
    });
    const counts = { todas: 0, borrador: 0, pendiente: 0, pagada: 0, anulada: 0 };
    const items = response.data?.results ?? [];
    counts.todas = response.data?.count ?? items.length;
    items.forEach(c => { if (counts[c.estado] !== undefined) counts[c.estado]++; });
    return counts;
  },

  exportarExcel: async () => {
    try {
      const response = await comprasAPI.exportarExcel();


      // Crear el blob
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });

      // Crear y hacer clic en el enlace de descarga
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Compras_${new Date().toISOString().slice(0,10)}.xlsx`;
      document.body.appendChild(link);
      link.click();
      
      // Limpieza
      setTimeout(() => {
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }, 100);

      return true;
    } catch (error) {
      if (error.response) {
      }
      throw new Error('No se pudo descargar el archivo Excel');
    }
  },

  getEstadisticas: async () => {
    const response = await comprasAPI.getEstadisticas();
    return response.data;
  },

  getDetallesCompra: async (compraId) => {
    try {
      const response = await api.get(`/api/compras/compras/${compraId}/detalles/`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  importarExcel: async (formData) => {
    try {
      const response = await comprasAPI.importarExcel(formData);
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Error al importar el archivo Excel');
    }
  },

  getAlmacenes: async () => {
    try {
      const response = await comprasAPI.getAlmacenes();
      return Array.isArray(response.data) ? response.data : 
             Array.isArray(response.data.results) ? response.data.results : [];
    } catch (error) {
      throw error;
    }
  },

  cambiarMetodoPago: async (compraId, metodoPago) => {
    try {
      const response = await comprasAPI.cambiarMetodoPago(compraId, metodoPago);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Descargar template para importación de compras
  descargarTemplateCompras: async () => {
    try {
      const response = await comprasAPI.descargarTemplateCompras();
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
      throw new Error('Error al descargar el template de compras');
    }
  },

  updateCompraEstado: async (compraId, data) => {
    try {
      const response = await api.patch(`/api/compras/compras/${compraId}/`, data);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Métodos para pagos
  getPagosCompra: async (compraId) => {
    try {
      const response = await api.get(`/api/compras/compras/${compraId}/pagos/`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  crearPagoCompra: async (compraId, pagoData) => {
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

      const response = await api.post(`/api/compras/compras/${compraId}/pagos/`, formData);
      return response.data;
    } catch (error) {
      throw new Error(error.response?.data?.error || error.message || 'Error al crear el pago');
    }
  },

  getSaldoPendiente: async (compraId) => {
    try {
      const response = await api.get(`/api/compras/compras/${compraId}/saldo-pendiente/`);
      return response.data.saldo_pendiente;
    } catch (error) {
      throw error;
    }
  },

  // Métodos para cuentas por pagar
  getComprasPendientes: async () => {
    try {
      const response = await comprasAPI.getComprasPendientes();
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  crearPago: async (compraId, pagoData) => {
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

      const response = await comprasAPI.crearPago(compraId, formData);

      // Invalidar consultas relevantes
      queryClient.invalidateQueries(['compras']);
      queryClient.invalidateQueries(['cuentas-por-pagar']);
      queryClient.invalidateQueries(['compra', compraId]);

      return response.data;
    } catch (error) {
      throw error;
    }
  },

  actualizarPago: async (compraId, pagoId, pagoData) => {
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

      const response = await comprasAPI.actualizarPago(compraId, pagoId, formData);

      // Invalidar consultas relevantes
      queryClient.invalidateQueries(['compras']);
      queryClient.invalidateQueries(['cuentas-por-pagar']);
      queryClient.invalidateQueries(['compra', compraId]);

      return response.data;
    } catch (error) {
      throw error;
    }
  },

  eliminarPago: async (compraId, pagoId) => {
    try {
      await comprasAPI.eliminarPago(compraId, pagoId);
      
      // Invalidar consultas relevantes
      queryClient.invalidateQueries(['compras']);
      queryClient.invalidateQueries(['cuentas-por-pagar']);
      queryClient.invalidateQueries(['compra', compraId]);
    } catch (error) {
      throw error;
    }
  },

  // ── Órdenes de Compra ──────────────────────────────────────────────────────
  getOrdenes: async (params = {}) => {
    const response = await api.get('/api/compras/ordenes/', { params });
    return response.data;
  },

  getOrden: async (id) => {
    const response = await api.get(`/api/compras/ordenes/${id}/`);
    return response.data;
  },

  createOrden: async (data) => {
    const response = await api.post('/api/compras/ordenes/', data);
    return response.data;
  },

  updateOrden: async (id, data) => {
    const response = await api.patch(`/api/compras/ordenes/${id}/`, data);
    return response.data;
  },

  deleteOrden: async (id) => {
    await api.delete(`/api/compras/ordenes/${id}/`);
  },

  cambiarEstadoOrden: async (id, estado) => {
    const response = await api.post(`/api/compras/ordenes/${id}/cambiar-estado/`, { estado });
    return response.data;
  },

  exportarPDFOrden: async (orden) => {
    const response = await api.get(`/api/compras/ordenes/${orden.id}/exportar-pdf/`, {
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    const prov = (orden.proveedor_nombre || 'OC').replace(/\s+/g, '_').slice(0, 30);
    link.setAttribute('download', `OC-${orden.numero || orden.id}_${prov}.pdf`);
    document.body.appendChild(link);
    link.click();
    setTimeout(() => { link.remove(); window.URL.revokeObjectURL(url); }, 100);
  },

  // ── Órdenes de Compra de Servicio (reparaciones / proveedor) ───────────────
  getOrdenesServicio: async (params = {}) => {
    const response = await api.get('/api/compras/ordenes-servicio/', { params });
    return response.data;
  },

  getOrdenServicio: async (id) => {
    const response = await api.get(`/api/compras/ordenes-servicio/${id}/`);
    return response.data;
  },

  createOrdenServicio: async (data) => {
    const response = await api.post('/api/compras/ordenes-servicio/', data);
    return response.data;
  },

  updateOrdenServicio: async (id, data) => {
    const response = await api.put(`/api/compras/ordenes-servicio/${id}/`, data);
    return response.data;
  },

  deleteOrdenServicio: async (id) => {
    await api.delete(`/api/compras/ordenes-servicio/${id}/`);
  },

  cambiarEstadoOrdenServicio: async (id, estado) => {
    const response = await api.post(`/api/compras/ordenes-servicio/${id}/cambiar-estado/`, { estado });
    return response.data;
  },

  exportarPDFOrdenServicio: async (orden) => {
    const response = await api.get(`/api/compras/ordenes-servicio/${orden.id}/exportar-pdf/`, {
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
    const link = document.createElement('a');
    link.href = url;
    const prov = (orden.proveedor_nombre || 'PROVEEDOR').replace(/\s+/g, '_').slice(0, 30);
    link.setAttribute('download', `OCS-${orden.numero || orden.id}_${prov}.pdf`);
    document.body.appendChild(link);
    link.click();
    setTimeout(() => { link.remove(); window.URL.revokeObjectURL(url); }, 100);
  },

  // Constantes
  TIPO_COMPRA: {
    CONTADO: 'contado',
    CREDITO_30: 'credito_30',
    CREDITO_60: 'credito_60'
  },

  METODO_PAGO: {
    EFECTIVO: 'efectivo',
    TRANSFERENCIA: 'transferencia',
    CHEQUE: 'cheque',
    TARJETA: 'tarjeta',
    PENDIENTE: 'pendiente'
  },

  ESTADO_COMPRA: {
    BORRADOR: 'borrador',
    PENDIENTE: 'pendiente',
    PAGADA: 'pagada',
    ANULADA: 'anulada'
  }
};

export default comprasService; 