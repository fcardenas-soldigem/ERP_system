import { comprasAPI } from '../api';
import { api } from '../api';
import axios from 'axios';
import { queryClient } from '../lib/queryClient';

export const comprasService = {
  getCompras: async (page = 1, pageSize = 10) => {
    try {
      const empresaId = localStorage.getItem('empresa_id');
      
      console.log('Estado de localStorage:', {
        empresa_id: empresaId,
        access_token: localStorage.getItem('access_token') ? 'Existe' : 'No existe',
        refresh_token: localStorage.getItem('refresh_token') ? 'Existe' : 'No existe'
      });
      
      if (!empresaId) {
        console.error('No se encontró empresa_id en localStorage. Intentando obtener del perfil...');
        
        // Intentar obtener el perfil del usuario para conseguir el empresa_id
        try {
          const response = await api.get('/api/auth/profile/');
          if (response.data.empresa_info?.id) {
            const newEmpresaId = response.data.empresa_info.id.toString();
            localStorage.setItem('empresa_id', newEmpresaId);
            console.log('Empresa ID obtenido del perfil y guardado:', newEmpresaId);
            // Continuar con el nuevo empresa_id
            return await comprasService.getCompras(page, pageSize);
          } else {
            throw new Error('El usuario no tiene una empresa asignada. Por favor, contacte al administrador.');
          }
        } catch (profileError) {
          console.error('Error al obtener perfil:', profileError);
          throw new Error('No se pudo obtener la información de la empresa. Por favor, cierre sesión e inicie sesión nuevamente.');
        }
      }

      console.log('Solicitando compras:', { page, pageSize, empresaId });
      
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
      console.error('Error al obtener compras:', error);
      if (error.response?.status === 401) {
        localStorage.removeItem('empresa_id');
        throw new Error('Sesión expirada. Por favor, inicie sesión nuevamente.');
      }
      throw error;
    }
  },

  getCompra: async (id) => {
    try {
      console.log('Obteniendo compra:', id);
      const response = await api.get(`/api/compras/compras/${id}/`);
      console.log('Respuesta de compra:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error al obtener compra:', error);
      throw error;
    }
  },

  getProveedores: async () => {
    try {
      const response = await comprasAPI.getProveedores();
      console.log('Respuesta getProveedores:', response);
      return Array.isArray(response.data) ? response.data : 
             Array.isArray(response.data.results) ? response.data.results : [];
    } catch (error) {
      console.error('Error al obtener proveedores:', error);
      throw error;
    }
  },

  getProductos: async () => {
    try {
      const response = await api.get('/api/inventario/productos/');
      return Array.isArray(response.data) ? response.data : 
             Array.isArray(response.data.results) ? response.data.results : [];
    } catch (error) {
      console.error('Error al obtener productos:', error);
      throw error;
    }
  },

  createCompra: async (compraData) => {
    try {
      console.log('Datos recibidos en service:', compraData);

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
      console.error('Error en createCompra:', error);
      if (error.response?.data) {
        console.error('Error del servidor:', error.response.data);
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
      console.error('Error al cambiar estado:', error.response?.data);
      throw error;
    }
  },

  exportarExcel: async () => {
    try {
      console.log('Iniciando exportación...');
      const response = await comprasAPI.exportarExcel();

      console.log('Respuesta recibida:', response);

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
      console.error('Error detallado:', error);
      if (error.response) {
        console.error('Respuesta del servidor:', error.response);
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
      console.log('Obteniendo detalles de compra:', compraId);
      const response = await api.get(`/api/compras/compras/${compraId}/detalles/`);
      console.log('Respuesta de detalles:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error al obtener detalles de la compra:', error);
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
      console.log('Solicitando almacenes...');
      const response = await comprasAPI.getAlmacenes();
      console.log('Almacenes recibidos:', response.data);
      return Array.isArray(response.data) ? response.data : 
             Array.isArray(response.data.results) ? response.data.results : [];
    } catch (error) {
      console.error('Error al obtener almacenes:', error);
      throw error;
    }
  },

  cambiarMetodoPago: async (compraId, metodoPago) => {
    try {
      const response = await comprasAPI.cambiarMetodoPago(compraId, metodoPago);
      return response.data;
    } catch (error) {
      console.error('Error al cambiar método de pago:', error.response?.data);
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
      console.error('Error al descargar el template de compras:', error);
      throw new Error('Error al descargar el template de compras');
    }
  },

  updateCompraEstado: async (compraId, data) => {
    try {
      console.log('Actualizando estado de compra:', compraId, data);
      const response = await api.patch(`/api/compras/compras/${compraId}/`, data);
      console.log('Respuesta de actualización:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error al actualizar estado de la compra:', error);
      throw error;
    }
  },

  // Métodos para pagos
  getPagosCompra: async (compraId) => {
    try {
      console.log('Obteniendo pagos de compra:', compraId);
      const response = await api.get(`/api/compras/compras/${compraId}/pagos/`);
      console.log('Respuesta de pagos:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error al obtener pagos de la compra:', error);
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
      console.error('Error al crear pago:', error);
      throw new Error(error.response?.data?.error || error.message || 'Error al crear el pago');
    }
  },

  getSaldoPendiente: async (compraId) => {
    try {
      console.log('Obteniendo saldo pendiente de compra:', compraId);
      const response = await api.get(`/api/compras/compras/${compraId}/saldo-pendiente/`);
      console.log('Respuesta de saldo pendiente:', response.data);
      return response.data.saldo_pendiente;
    } catch (error) {
      console.error('Error al obtener saldo pendiente:', error);
      throw error;
    }
  },

  // Métodos para cuentas por pagar
  getComprasPendientes: async () => {
    try {
      const response = await comprasAPI.getComprasPendientes();
      return response.data;
    } catch (error) {
      console.error('Error al obtener compras pendientes:', error);
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
      console.error('Error al crear pago:', error);
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
      console.error('Error al actualizar pago:', error);
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
      console.error('Error al eliminar pago:', error);
      throw error;
    }
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