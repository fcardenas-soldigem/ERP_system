import { useState, useCallback, useEffect } from 'react';
import api from '../services/api.jsx';

const useTipoCambio = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tipoCambioActual, setTipoCambioActual] = useState(null);

  const consultarTipoCambio = useCallback(async (fecha = null) => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (fecha) {
        params.append('fecha', fecha);
      }

      const response = await api.get(`/api/core/tipo-cambio/?${params.toString()}`);
      
      if (response.data.success) {
        setLoading(false);
        return response.data.data;
      } else {
        setError(response.data.error);
        setLoading(false);
        return null;
      }
    } catch (error) {
      const errorMessage = error.response?.data?.error || 'Error al consultar tipo de cambio';
      setError(errorMessage);
      setLoading(false);
      return null;
    }
  }, []);

  const consultarTipoCambioMes = useCallback(async (mes, año) => {
    if (!mes || !año) {
      setError('Mes y año son requeridos');
      return null;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.get(`/api/core/tipo-cambio/mes/?mes=${mes}&año=${año}`);
      
      if (response.data.success) {
        setLoading(false);
        return response.data.data;
      } else {
        setError(response.data.error);
        setLoading(false);
        return null;
      }
    } catch (error) {
      const errorMessage = error.response?.data?.error || 'Error al consultar tipos de cambio del mes';
      setError(errorMessage);
      setLoading(false);
      return null;
    }
  }, []);

  const obtenerTipoCambioHoy = useCallback(async () => {
    const datos = await consultarTipoCambio();
    if (datos) {
      setTipoCambioActual(datos);
    }
    return datos;
  }, [consultarTipoCambio]);

  const limpiarError = useCallback(() => {
    setError(null);
  }, []);

  // Formatear moneda peruana
  const formatearMoneda = useCallback((valor) => {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN',
      minimumFractionDigits: 3,
      maximumFractionDigits: 3
    }).format(valor);
  }, []);

  // Validar formato de fecha
  const validarFecha = useCallback((fecha) => {
    const regex = /^\d{4}-\d{2}-\d{2}$/;
    if (!regex.test(fecha)) return false;
    
    const date = new Date(fecha);
    return date instanceof Date && !isNaN(date);
  }, []);

  // Cargar tipo de cambio actual al montar el componente
  useEffect(() => {
    obtenerTipoCambioHoy();
  }, [obtenerTipoCambioHoy]);

  return {
    consultarTipoCambio,
    consultarTipoCambioMes,
    obtenerTipoCambioHoy,
    validarFecha,
    formatearMoneda,
    limpiarError,
    loading,
    error,
    tipoCambioActual
  };
};

export default useTipoCambio; 