import { api } from '../api';
import { queryClient } from '../lib/queryClient';

export const cuentasService = {
    // Resumen general
    getResumen: async () => {
        try {
            const [comprasResponse, ventasResponse] = await Promise.all([
                api.get('/api/compras/compras/', {
                    params: {
                        tipo_compra__in: 'credito_30,credito_60',
                        estado__in: 'pendiente,borrador'
                    }
                }),
                api.get('/api/ventas/')
            ]);

            const compras = comprasResponse.data.results || [];
            const todasLasVentas = ventasResponse.data.results || [];
            
            // Filtrar SOLO ventas a crédito con plazo de 30 o 60 días
            const ventas = todasLasVentas.filter(venta => 
                venta.tipo_venta === 'credito_30' || venta.tipo_venta === 'credito_60'
            );

            // Obtener los pagos de todas las ventas
            const ventasIds = ventas.map(venta => venta.id);
            const ventasPagosPromises = ventasIds.map(id => 
                api.get(`/api/ventas/${id}/pagos/`)
                .catch(error => {
                    console.error(`Error al obtener pagos para venta ${id}:`, error);
                    return { data: [] };
                })
            );

            // Obtener los pagos de todas las compras
            const comprasIds = compras.map(compra => compra.id);
            const comprasPagosPromises = comprasIds.map(id => 
                api.get(`/api/compras/${id}/pagos/`)
                .catch(error => {
                    console.error(`Error al obtener pagos para compra ${id}:`, error);
                    return { data: [] };
                })
            );

            const [ventasPagosResponses, comprasPagosResponses] = await Promise.all([
                Promise.all(ventasPagosPromises),
                Promise.all(comprasPagosPromises)
            ]);

            // Calcular total por cobrar
            const ventasConSaldos = ventas.map((venta, index) => {
                const pagos = Array.isArray(ventasPagosResponses[index]?.data) 
                    ? ventasPagosResponses[index].data 
                    : Array.isArray(ventasPagosResponses[index]) 
                        ? ventasPagosResponses[index] 
                        : [];
                
                const totalPagado = pagos.reduce((sum, pago) => {
                    const monto = parseFloat(pago?.monto || 0);
                    return sum + (isNaN(monto) ? 0 : monto);
                }, 0);
                
                return {
                    ...venta,
                    saldo_pendiente: parseFloat(venta.total || 0) - totalPagado
                };
            }).filter(venta => venta.saldo_pendiente > 0);

            // Calcular total por pagar
            const comprasConSaldos = compras.map((compra, index) => {
                const pagos = Array.isArray(comprasPagosResponses[index]?.data) 
                    ? comprasPagosResponses[index].data 
                    : Array.isArray(comprasPagosResponses[index]) 
                        ? comprasPagosResponses[index] 
                        : [];
                
                const totalPagado = pagos.reduce((sum, pago) => {
                    const monto = parseFloat(pago?.monto || 0);
                    return sum + (isNaN(monto) ? 0 : monto);
                }, 0);
                
                return {
                    ...compra,
                    saldo_pendiente: parseFloat(compra.total || 0) - totalPagado
                };
            }).filter(compra => compra.saldo_pendiente > 0);

            const totalPorCobrar = ventasConSaldos.reduce((sum, venta) => sum + venta.saldo_pendiente, 0);
            const totalPorPagar = comprasConSaldos.reduce((sum, compra) => sum + compra.saldo_pendiente, 0);

            return {
                total_por_cobrar: totalPorCobrar,
                total_por_pagar: totalPorPagar,
                ventas_pendientes: ventasConSaldos.length,
                compras_pendientes: comprasConSaldos.length
            };
        } catch (error) {
            console.error('Error al obtener resumen:', error);
            throw error;
        }
    },

    getResumenPorPagar: async () => {
        try {
            const response = await api.get('/api/compras/compras/', {
                params: {
                    tipo_compra__in: 'credito_30,credito_60',
                    estado__in: 'pendiente,borrador'
                }
            });

            const compras = response.data.results || [];
            const totalPorPagar = compras.reduce((sum, compra) => 
                sum + (parseFloat(compra.total) - parseFloat(compra.pagos_total || 0)), 0);

            return {
                total_por_pagar: totalPorPagar,
                compras_pendientes: compras.length
            };
        } catch (error) {
            console.error('Error al obtener resumen de cuentas por pagar:', error);
            throw error;
        }
    },

    // Cuentas por Cobrar - SOLO ventas a crédito con saldo pendiente
    getCuentasPorCobrar: async (page = 1, pageSize = 10) => {
        try {
            // Obtener SOLO las ventas a crédito pendientes
            const response = await api.get('/api/ventas/', {
                params: {
                    page,
                    page_size: pageSize,
                    tipo_venta__in: 'credito_30,credito_60',
                    estado: 'pendiente'
                }
            });

            const ventas = response.data.results || [];
            
            // Obtener los pagos de todas las ventas
            const pagosPromises = ventas.map(venta => 
                api.get(`/api/ventas/${venta.id}/pagos/`)
                .catch(error => {
                    console.error(`Error al obtener pagos para venta ${venta.id}:`, error);
                    return { data: [] };
                })
            );
            
            const pagosResponses = await Promise.all(pagosPromises);
            
            // Procesar las ventas con sus pagos
            const ventasConPagos = ventas.map((venta, index) => {
                const pagos = Array.isArray(pagosResponses[index]?.data) 
                    ? pagosResponses[index].data 
                    : [];
                
                const totalPagado = pagos.reduce((sum, pago) => {
                    const monto = parseFloat(pago?.monto || 0);
                    return sum + (isNaN(monto) ? 0 : monto);
                }, 0);
                
                const saldoPendiente = parseFloat(venta.total || 0) - totalPagado;
                
                // Calcular fecha de vencimiento y días restantes
                const fechaVencimiento = new Date(venta.fecha_vencimiento);
                const diasRestantes = Math.ceil(
                    (fechaVencimiento - new Date()) / (1000 * 60 * 60 * 24)
                );
                
                return {
                    ...venta,
                    pagos,
                    saldo_pendiente: saldoPendiente,
                    total_pagado: totalPagado,
                    dias_restantes: diasRestantes,
                    estado_vencimiento: diasRestantes < 0 
                        ? 'VENCIDO'
                        : diasRestantes === 0 
                            ? 'VENCE HOY'
                            : `${diasRestantes} DÍAS RESTANTES`
                };
            });

            // Calcular el total por cobrar
            const totalPorCobrar = ventasConPagos.reduce((sum, venta) => sum + venta.saldo_pendiente, 0);

            return {
                results: ventasConPagos,
                count: response.data.count,
                total_pages: Math.ceil(response.data.count / pageSize),
                current_page: page,
                total_por_cobrar: totalPorCobrar,
                ventas_pendientes: ventasConPagos.length
            };
        } catch (error) {
            console.error('Error al obtener cuentas por cobrar:', error);
            throw error;
        }
    },

    getCuentaPorCobrarDetalle: async (id) => {
        try {
            console.log('🔍 Buscando cuenta por cobrar con ID:', id);
            
            console.log('Obteniendo venta y pagos para ID:', id);
            
            const [ventaResponse, pagosResponse] = await Promise.all([
                api.get(`/api/ventas/${id}/`),
                api.get(`/api/ventas/${id}/pagos/`)
            ]);

            console.log('Respuesta de venta:', ventaResponse);
            console.log('Respuesta de pagos:', pagosResponse);

            const venta = ventaResponse.data;
            // Asegurarnos que pagos sea siempre un array
            const pagos = Array.isArray(pagosResponse.data) ? pagosResponse.data : 
                         Array.isArray(pagosResponse.data?.results) ? pagosResponse.data.results : [];

            console.log('📊 Venta obtenida:', venta);
            console.log('💰 Pagos obtenidos:', pagos);
            console.log('🏷️ Tipo de venta:', venta.tipo_venta);

            // Verificar si la venta es a crédito
            if (!['credito_30', 'credito_60'].includes(venta.tipo_venta)) {
                const errorMsg = `Esta venta no es a crédito. Tipo actual: ${venta.tipo_venta}`;
                console.error('❌', errorMsg);
                throw new Error(errorMsg);
            }

            // Filtrar pagos reales (excluir "pendiente")
            const pagosReales = pagos.filter(pago => pago.metodo_pago !== 'pendiente');
            const totalPagado = pagosReales.reduce((sum, pago) => {
                const monto = parseFloat(pago?.monto || 0);
                return sum + (isNaN(monto) ? 0 : monto);
            }, 0);

            const saldoPendiente = parseFloat(venta.total || 0) - totalPagado;
            
            console.log('📈 Total venta:', venta.total);
            console.log('💸 Total pagado:', totalPagado);
            console.log('💳 Saldo pendiente:', saldoPendiente);
            
            // Calcular fecha de vencimiento y días restantes
            const fechaVencimiento = venta.fecha_vencimiento ? 
                new Date(venta.fecha_vencimiento) : 
                (() => {
                    const fecha = new Date(venta.fecha_emision);
                    let plazo = 30; // Default
                    if (venta.tipo_venta === 'credito_30') plazo = 30;
                    else if (venta.tipo_venta === 'credito_60') plazo = 60;
                    fecha.setDate(fecha.getDate() + plazo);
                    return fecha;
                })();

            const diasRestantes = Math.ceil(
                (fechaVencimiento - new Date()) / (1000 * 60 * 60 * 24)
            );

            const resultado = {
                ...venta,
                pagos: pagosReales, // Solo mostrar pagos reales
                saldo_pendiente: saldoPendiente,
                total_pagado: totalPagado,
                fecha_vencimiento: fechaVencimiento.toISOString().split('T')[0],
                dias_restantes: diasRestantes,
                plazo_credito: venta.tipo_venta === 'credito_30' ? 30 : 
                              venta.tipo_venta === 'credito_60' ? 60 : 30,
                estado_vencimiento: diasRestantes < 0 
                    ? 'VENCIDO'
                    : diasRestantes === 0 
                        ? 'VENCE HOY'
                        : `${diasRestantes} DÍAS RESTANTES`
            };

            console.log('✅ Resultado final:', resultado);
            return resultado;
        } catch (error) {
            console.error('💥 Error al obtener detalle de cuenta por cobrar:', error);
            throw error;
        }
    },

    registrarPagoCuentaPorCobrar: async (ventaId, pagoData) => {
        try {
            console.log('🔍 Registrando pago para venta ID:', ventaId);
            console.log('📝 Datos del pago:', pagoData);
            
            // Validar y convertir el monto
            const montoNumerico = parseFloat(pagoData.monto);
            if (isNaN(montoNumerico) || montoNumerico <= 0) {
                throw new Error('El monto debe ser un número válido mayor a 0');
            }
            
            // Validar fecha
            if (!pagoData.fecha) {
                throw new Error('La fecha es requerida');
            }

            // Validar método de pago
            if (!pagoData.metodo_pago) {
                throw new Error('El método de pago es requerido');
            }

            // Primero obtener la venta para verificar el saldo
            const ventaResponse = await api.get(`/api/ventas/${ventaId}/`);
            const venta = ventaResponse.data;

            // Obtener pagos existentes
            const pagosResponse = await api.get(`/api/ventas/${ventaId}/pagos/`);
            const pagosExistentes = Array.isArray(pagosResponse.data) ? pagosResponse.data : 
                                  Array.isArray(pagosResponse.data?.results) ? pagosResponse.data.results : [];
            
            console.log('Pagos existentes:', pagosExistentes);
            
            // Filtrar pagos reales (excluir "pendiente")
            const pagosReales = pagosExistentes.filter(pago => pago.metodo_pago !== 'pendiente');
            const totalPagado = pagosReales.reduce((sum, pago) => {
                const monto = parseFloat(pago?.monto || 0);
                return sum + (isNaN(monto) ? 0 : monto);
            }, 0);

            console.log('Total pagado:', totalPagado);
            console.log('Venta total:', venta.total);
            
            const saldoPendiente = parseFloat(venta.total) - totalPagado;
            const nuevoTotalPagado = totalPagado + montoNumerico;
            const quedaSaldo = nuevoTotalPagado < parseFloat(venta.total);

            // Preparar los datos del pago
            const datosPago = {
                venta: ventaId,
                fecha: pagoData.fecha,
                monto: montoNumerico.toFixed(2), // Asegurar 2 decimales
                metodo_pago: pagoData.metodo_pago,
                referencia: pagoData.referencia || '',
                notas: pagoData.notas || ''
            };

            console.log('📦 Datos del pago preparados:', datosPago);

            let data;
            let headers = {};

            // Si hay un comprobante, usar FormData
            if (pagoData.comprobante) {
                const formData = new FormData();
                // Agregar cada campo al FormData
                Object.entries(datosPago).forEach(([key, value]) => {
                    formData.append(key, value);
                });
                formData.append('comprobante', pagoData.comprobante);
                data = formData;
            } else {
                data = datosPago;
                headers['Content-Type'] = 'application/json';
            }

            // Registrar el pago
            const pagoResponse = await api.post(`/api/ventas/${ventaId}/pagos/`, data, { headers });

            // El estado se actualiza automáticamente en el backend si es necesario
            if (!quedaSaldo) {
                console.log('Venta marcada como pagada');
            }

            // Invalidar consultas para actualizar los datos
            queryClient.invalidateQueries(['cuentas-por-cobrar']);
            queryClient.invalidateQueries(['venta', ventaId]);
            queryClient.invalidateQueries(['pagos-venta', ventaId]);
            queryClient.invalidateQueries(['ventas']);

            return {
                ...pagoResponse.data,
                venta_completamente_pagada: !quedaSaldo,
                saldo_restante: quedaSaldo ? parseFloat(venta.total) - nuevoTotalPagado : 0
            };
        } catch (error) {
            console.error('❌ Error al registrar pago:', error);
            console.error('📄 Detalles del error:', error.response?.data);
            
            // Intentar obtener un mensaje de error más específico
            const mensajeError = error.response?.data?.error || 
                               error.response?.data?.detail ||
                               error.response?.data?.message ||
                               error.message ||
                               'Error al registrar el pago';
            
            throw new Error(mensajeError);
        }
    },

    actualizarEstado: async (ventaId, nuevoEstado) => {
        try {
            const response = await api.patch(`/api/cuentas/por-cobrar/${ventaId}/estado/`, {
                estado: nuevoEstado
            });

            // Invalidar consultas para actualizar los datos en ambos módulos
            queryClient.invalidateQueries(['cuentas-por-cobrar']);
            queryClient.invalidateQueries(['cuenta-por-cobrar', ventaId]);
            queryClient.invalidateQueries(['ventas']);
            queryClient.invalidateQueries(['venta', ventaId]);

            return response.data;
        } catch (error) {
            console.error('Error al actualizar estado:', error);
            throw error;
        }
    },

    getPagosCuenta: async (ventaId) => {
        try {
            const response = await api.get(`/api/ventas/${ventaId}/pagos/`);
            return response.data;
        } catch (error) {
            console.error('Error al obtener pagos:', error);
            throw error;
        }
    },

    getPagosCompra: async (compraId) => {
        try {
            const response = await api.get(`/api/compras/compras/${compraId}/pagos/`);
            return response.data;
        } catch (error) {
            console.error('Error al obtener pagos de compra:', error);
            throw error;
        }
    },

    getSaldoPendiente: async (ventaId) => {
        try {
            const response = await api.get(`/api/ventas/${ventaId}/`);
            const venta = response.data;
            const pagosResponse = await api.get(`/api/ventas/${ventaId}/pagos/`);
            const pagos = Array.isArray(pagosResponse.data) ? pagosResponse.data : [];
            const totalPagado = pagos.reduce((sum, pago) => sum + parseFloat(pago.monto || 0), 0);
            return venta.total - totalPagado;
        } catch (error) {
            console.error('Error al obtener saldo pendiente:', error);
            throw error;
        }
    },

    // Cuentas por Pagar
    getCuentasPorPagar: async (params = {}) => {
        const { page = 1, pageSize = 10 } = params;
        try {
            const response = await api.get('/api/compras/compras/compras_pendientes/');
            
            const comprasData = response.data;
            const compras = comprasData.compras || [];
            
            // Paginación manual del lado del cliente por ahora
            const startIndex = (page - 1) * pageSize;
            const endIndex = startIndex + pageSize;
            const comprasPaginadas = compras.slice(startIndex, endIndex);

            return {
                results: comprasPaginadas,
                count: compras.length,
                total_pages: Math.ceil(compras.length / pageSize),
                current_page: page,
                total_general_pen: comprasData.total_general_pen || 0,
                tipo_cambio: comprasData.tipo_cambio || 3.8
            };
        } catch (error) {
            console.error('Error al obtener cuentas por pagar:', error);
            throw error;
        }
    },

    getCuentaPorPagarDetalle: async (id) => {
        try {
            const response = await api.get(`/api/compras/compras/${id}/`);
            return response.data;
        } catch (error) {
            console.error('Error al obtener detalle de cuenta por pagar:', error);
            throw error;
        }
    },

    registrarPagoCuentaPorPagar: async (compraId, pagoData) => {
        const response = await api.post(`/api/compras/compras/${compraId}/pagos/`, pagoData);
        return response.data;
    },

    // Estadísticas y reportes
    getEstadisticasCuentas: async () => {
        const response = await api.get('/api/cuentas/estadisticas/');
        return response.data;
    },

    getReporteCuentasPorCobrar: async (params = {}) => {
        const response = await api.get('/api/cuentas/reporte/por-cobrar/', { params });
        return response.data;
    },

    getReporteCuentasPorPagar: async (params = {}) => {
        const response = await api.get('/api/cuentas/reporte/por-pagar/', { params });
        return response.data;
    },

    // Utilidades
    getEstadoVencimiento: (fechaVencimiento) => {
        if (!fechaVencimiento) return { label: 'Sin vencimiento', color: 'gray' };
        
        const hoy = new Date();
        const vencimiento = new Date(fechaVencimiento);
        
        if (hoy > vencimiento) {
            return { label: 'Vencida', color: 'red' };
        }
        return { label: 'Pendiente', color: 'yellow' };
    },

    formatCurrency: (amount, currency = 'PEN') => {
        const symbol = currency === 'USD' ? '$' : 'S/';
        return `${symbol} ${parseFloat(amount || 0).toFixed(2)}`;
    },

    getVencimientosPorCobrar: async () => {
        const response = await api.get('/api/ventas/vencimientos/');
        return response.data;
    },

    getVencimientosPorPagar: async () => {
        const response = await api.get('/api/compras/vencimientos/');
        return response.data;
    }
};

export default cuentasService; 