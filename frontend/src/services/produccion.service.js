import api from '../config/axios';

const API_URL = '/api/produccion';

export const produccionService = {
  // ========== RECETAS ==========
  
  /**
   * Obtiene lista de recetas
   * @param {Object} params - Parámetros de filtro (is_active, producto_id, search)
   */
  getRecetas: (params = {}) => {
    return api.get(`${API_URL}/recetas/`, { params });
  },

  /**
   * Obtiene una receta por ID
   * @param {number} id - ID de la receta
   */
  getReceta: (id) => {
    return api.get(`${API_URL}/recetas/${id}/`);
  },

  /**
   * Crea una nueva receta
   * @param {Object} data - Datos de la receta
   */
  createReceta: (data) => {
    return api.post(`${API_URL}/recetas/`, data);
  },

  /**
   * Actualiza una receta existente
   * @param {number} id - ID de la receta
   * @param {Object} data - Datos actualizados
   */
  updateReceta: (id, data) => {
    return api.put(`${API_URL}/recetas/${id}/`, data);
  },

  /**
   * Actualización parcial de una receta
   * @param {number} id - ID de la receta
   * @param {Object} data - Datos a actualizar
   */
  patchReceta: (id, data) => {
    return api.patch(`${API_URL}/recetas/${id}/`, data);
  },

  /**
   * Elimina una receta
   * @param {number} id - ID de la receta
   */
  deleteReceta: (id) => {
    return api.delete(`${API_URL}/recetas/${id}/`);
  },

  /**
   * Duplica una receta creando una nueva versión
   * @param {number} id - ID de la receta a duplicar
   */
  duplicarReceta: (id) => {
    return api.post(`${API_URL}/recetas/${id}/duplicar_receta/`);
  },

  /**
   * Calcula el costo teórico de una receta
   * @param {number} id - ID de la receta
   */
  calcularCostoTeorico: (id) => {
    return api.get(`${API_URL}/recetas/${id}/calcular_costo_teorico/`);
  },

  /**
   * Valida si hay stock suficiente para producir
   * @param {Object} data - { receta_id, cantidad, almacen_insumos_id }
   */
  validarStock: (data) => {
    return api.post(`${API_URL}/recetas/validar_stock/`, data);
  },

  // ========== ÓRDENES DE PRODUCCIÓN ==========

  /**
   * Obtiene lista de órdenes de producción
   * @param {Object} params - Parámetros de filtro (estado, fecha_desde, fecha_hasta, etc.)
   */
  getOrdenes: (params = {}) => {
    return api.get(`${API_URL}/ordenes/`, { params });
  },

  /**
   * Obtiene una orden de producción por ID
   * @param {number} id - ID de la orden
   */
  getOrden: (id) => {
    return api.get(`${API_URL}/ordenes/${id}/`);
  },

  /**
   * Crea una nueva orden de producción
   * @param {Object} data - Datos de la orden
   */
  createOrden: (data) => {
    return api.post(`${API_URL}/ordenes/`, data);
  },

  /**
   * Actualiza una orden de producción
   * @param {number} id - ID de la orden
   * @param {Object} data - Datos actualizados
   */
  updateOrden: (id, data) => {
    return api.put(`${API_URL}/ordenes/${id}/`, data);
  },

  /**
   * Actualización parcial de una orden
   * @param {number} id - ID de la orden
   * @param {Object} data - Datos a actualizar
   */
  patchOrden: (id, data) => {
    return api.patch(`${API_URL}/ordenes/${id}/`, data);
  },

  /**
   * Elimina una orden de producción
   * @param {number} id - ID de la orden
   */
  deleteOrden: (id) => {
    return api.delete(`${API_URL}/ordenes/${id}/`);
  },

  /**
   * Inicia una orden de producción (cambia estado a En Proceso)
   * @param {number} id - ID de la orden
   */
  iniciarOrden: (id) => {
    return api.post(`${API_URL}/ordenes/${id}/iniciar/`);
  },

  /**
   * Finaliza una orden de producción
   * @param {number} id - ID de la orden
   * @param {Object} data - { cantidad_producida, costo_mano_obra_real, costo_indirecto_real, observaciones }
   */
  finalizarOrden: (id, data) => {
    return api.post(`${API_URL}/ordenes/${id}/finalizar/`, data);
  },

  /**
   * Cancela una orden de producción
   * @param {number} id - ID de la orden
   * @param {string} motivo - Motivo de cancelación
   */
  cancelarOrden: (id, motivo = '') => {
    return api.post(`${API_URL}/ordenes/${id}/cancelar/`, { motivo });
  },

  /**
   * Actualiza el consumo real de un insumo
   * @param {number} ordenId - ID de la orden
   * @param {Object} data - { insumo_id, cantidad_real, merma, notas }
   */
  actualizarConsumo: (ordenId, data) => {
    return api.post(`${API_URL}/ordenes/${ordenId}/actualizar_consumo/`, data);
  },

  // ========== DASHBOARD ==========

  /**
   * Obtiene métricas del dashboard de producción
   * @param {Object} params - Parámetros (fecha_desde, fecha_hasta)
   */
  getDashboard: (params = {}) => {
    return api.get(`${API_URL}/dashboard/`, { params });
  },
};

export default produccionService;
