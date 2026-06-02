import { useState, useCallback } from 'react';
import api from '../lib/api';

const useConsultaDocumentos = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const consultarDNI = useCallback(async (dni) => {
    if (!dni || dni.length !== 8) {
      setError('DNI debe tener 8 dígitos');
      return null;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.get(`/api/core/consultar-dni/?dni=${dni}`);
      
      if (response.data.success) {
        setLoading(false);
        return response.data.data;
      } else {
        setError(response.data.error);
        setLoading(false);
        return null;
      }
    } catch (error) {
      console.error('Error en consultarDNI:', error);
      
      // Manejar diferentes tipos de errores
      let errorMessage = 'Error al consultar DNI';
      
      if (error.response?.status === 401) {
        errorMessage = 'Error de autenticación. Por favor, inicia sesión nuevamente.';
      } else if (error.response?.status === 403) {
        errorMessage = 'No tienes permisos para realizar esta consulta.';
      } else if (error.response?.status === 500) {
        errorMessage = 'Error del servidor. Intenta nuevamente.';
      } else if (error.response?.data?.error) {
        errorMessage = error.response.data.error;
      } else if (!navigator.onLine) {
        errorMessage = 'Sin conexión a internet. Verifica tu conectividad.';
      }
      
      setError(errorMessage);
      setLoading(false);
      return null;
    }
  }, []);

  const consultarRUC = useCallback(async (ruc) => {
    if (!ruc || ruc.length !== 11) {
      setError('RUC debe tener 11 dígitos');
      return null;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.get(`/api/core/consultar-ruc/?ruc=${ruc}`);
      
      if (response.data.success) {
        setLoading(false);
        return response.data.data;
      } else {
        setError(response.data.error);
        setLoading(false);
        return null;
      }
    } catch (error) {
      console.error('Error en consultarRUC:', error);
      
      // Manejar diferentes tipos de errores
      let errorMessage = 'Error al consultar RUC';
      
      if (error.response?.status === 401) {
        errorMessage = 'Error de autenticación. Por favor, inicia sesión nuevamente.';
      } else if (error.response?.status === 403) {
        errorMessage = 'No tienes permisos para realizar esta consulta.';
      } else if (error.response?.status === 500) {
        errorMessage = 'Error del servidor. Intenta nuevamente.';
      } else if (error.response?.data?.error) {
        errorMessage = error.response.data.error;
      } else if (!navigator.onLine) {
        errorMessage = 'Sin conexión a internet. Verifica tu conectividad.';
      }
      
      setError(errorMessage);
      setLoading(false);
      return null;
    }
  }, []);

  const consultarDocumento = useCallback(async (numero, tipo) => {
    if (!numero || !tipo) {
      setError('Número y tipo de documento son requeridos');
      return null;
    }

    // Validaciones básicas
    if (tipo === 'dni' && numero.length !== 8) {
      setError('DNI debe tener 8 dígitos');
      return null;
    }

    if (tipo === 'ruc' && numero.length !== 11) {
      setError('RUC debe tener 11 dígitos');
      return null;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.get(`/api/core/consultar-documento/?numero=${numero}&tipo=${tipo}`);
      
      if (response.data.success) {
        setLoading(false);
        return response.data.data;
      } else {
        setError(response.data.error);
        setLoading(false);
        return null;
      }
    } catch (error) {
      console.error('Error en consultarDocumento:', error);
      
      // Manejar diferentes tipos de errores
      let errorMessage = 'Error al consultar documento';
      
      if (error.response?.status === 401) {
        errorMessage = 'Error de autenticación. Por favor, verifica tu sesión.';
      } else if (error.response?.status === 403) {
        errorMessage = 'No tienes permisos para realizar esta consulta.';
      } else if (error.response?.status === 500) {
        errorMessage = 'Error del servidor. Intenta nuevamente.';
      } else if (error.response?.data?.error) {
        errorMessage = error.response.data.error;
      } else if (!navigator.onLine) {
        errorMessage = 'Sin conexión a internet. Verifica tu conectividad.';
      }
      
      setError(errorMessage);
      setLoading(false);
      return null;
    }
  }, []);

  const limpiarError = useCallback(() => {
    setError(null);
  }, []);

  // Función para validar formato de documentos
  const validarDocumento = useCallback((numero, tipo) => {
    if (!numero || !tipo) return false;
    
    if (tipo === 'dni') {
      return /^\d{8}$/.test(numero);
    }
    
    if (tipo === 'ruc') {
      return /^\d{11}$/.test(numero);
    }
    
    return false;
  }, []);

  return {
    consultarDNI,
    consultarRUC,
    consultarDocumento,
    validarDocumento,
    limpiarError,
    loading,
    error
  };
};

export default useConsultaDocumentos; 