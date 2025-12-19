/**
 * Servicio para interactuar con las APIs de Machine Learning
 */
import api from '../config/axios';

const mlService = {
  // ============================================
  // ENTRENAMIENTO DE MODELOS
  // ============================================

  /**
   * Entrena el modelo de segmentación RFM
   * @param {number} nClusters - Número de segmentos a crear (default: 5)
   * @returns {Promise}
   */
  trainRFM: async (nClusters = 5) => {
    return api.post('/api/ml/models/train/rfm/', { n_clusters: nClusters });
  },

  /**
   * Entrena el modelo de predicción de churn
   * @returns {Promise}
   */
  trainChurn: async () => {
    return api.post('/api/ml/models/train/churn/');
  },

  /**
   * Entrena el modelo de recomendaciones de productos
   * @param {number} minSupport - Soporte mínimo (default: 0.01)
   * @param {number} minConfidence - Confianza mínima (default: 0.2)
   * @returns {Promise}
   */
  trainRecommendations: async (minSupport = 0.01, minConfidence = 0.2) => {
    return api.post('/api/ml/models/train/recommendations/', {
      min_support: minSupport,
      min_confidence: minConfidence
    });
  },

  /**
   * Entrena todos los modelos disponibles
   * @returns {Promise}
   */
  trainAllModels: async () => {
    return api.post('/api/ml/models/train/all/');
  },

  // ============================================
  // PREDICCIONES
  // ============================================

  /**
   * Obtiene la segmentación RFM de los clientes
   * @returns {Promise}
   */
  predictRFM: async () => {
    return api.post('/api/ml/models/predict/rfm/');
  },

  /**
   * Obtiene los clientes en riesgo de churn
   * @returns {Promise}
   */
  predictChurn: async () => {
    return api.post('/api/ml/models/predict/churn/');
  },

  /**
   * Obtiene recomendaciones de productos
   * @param {number|null} productoId - ID del producto (opcional)
   * @returns {Promise}
   */
  predictRecommendations: async (productoId = null) => {
    const data = productoId ? { producto_id: productoId } : {};
    return api.post('/api/ml/models/predict/recommendations/', data);
  },

  // ============================================
  // GESTIÓN DE MODELOS
  // ============================================

  /**
   * Lista todos los modelos de la empresa
   * @returns {Promise}
   */
  listModels: async () => {
    return api.get('/api/ml/models/list/');
  },

  /**
   * Verifica el estado de los modelos
   * @returns {Promise}
   */
  checkStatus: async () => {
    return api.get('/api/ml/models/status/');
  },

  /**
   * Obtiene el historial de entrenamientos
   * @returns {Promise}
   */
  getTrainingHistory: async () => {
    return api.get('/api/ml/models/training-history/');
  },
};

export default mlService;


