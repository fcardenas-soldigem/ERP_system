import React, { useState, useEffect } from 'react';
import { Button } from './Button';
import useConsultaDocumentos from '../../hooks/useConsultaDocumentos';

const ConsultaDocumento = ({
  tipo, // 'dni' o 'ruc'
  valor,
  onChange,
  onDatosConsultados,
  placeholder,
  label,
  disabled = false,
  className = "",
  required = false
}) => {
  const [numeroDocumento, setNumeroDocumento] = useState(valor || '');
  const [consultado, setConsultado] = useState(false);
  const [datosConsulta, setDatosConsulta] = useState(null);
  
  const { 
    consultarDocumento, 
    validarDocumento, 
    loading, 
    error, 
    limpiarError 
  } = useConsultaDocumentos();

  useEffect(() => {
    setNumeroDocumento(valor || '');
    setConsultado(false);
    setDatosConsulta(null);
  }, [valor]);

  const handleInputChange = (e) => {
    const nuevoValor = e.target.value.replace(/\D/g, ''); // Solo números
    setNumeroDocumento(nuevoValor);
    setConsultado(false);
    setDatosConsulta(null);
    limpiarError();
    
    if (onChange) {
      onChange(nuevoValor);
    }
  };

  const handleConsultar = async () => {
    if (!validarDocumento(numeroDocumento, tipo)) {
      return;
    }

    const datos = await consultarDocumento(numeroDocumento, tipo);
    
    if (datos) {
      setDatosConsulta(datos);
      setConsultado(true);
      
      if (onDatosConsultados) {
        onDatosConsultados(datos);
      }
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleConsultar();
    }
  };

  const puedeConsultar = () => {
    return !loading && !disabled && validarDocumento(numeroDocumento, tipo);
  };

  const getMaxLength = () => {
    return tipo === 'dni' ? 8 : 11;
  };

  const getPlaceholder = () => {
    if (placeholder) return placeholder;
    return tipo === 'dni' ? 'Ingrese DNI (8 dígitos)' : 'Ingrese RUC (11 dígitos)';
  };

  const getLabel = () => {
    if (label) return label;
    return tipo === 'dni' ? 'DNI' : 'RUC';
  };

  return (
    <div className={`space-y-2 ${className}`}>
      {/* Campo de entrada con botón de consulta */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {getLabel()}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
        <div className="flex space-x-2">
          <input
            type="text"
            value={numeroDocumento}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            placeholder={getPlaceholder()}
            maxLength={getMaxLength()}
            disabled={disabled}
            className={`flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              error ? 'border-red-500' : ''
            } ${disabled ? 'bg-gray-100' : ''}`}
          />
          <Button
            onClick={handleConsultar}
            disabled={!puedeConsultar()}
            type="button"
            variant="outline"
            className="px-4 py-2 flex items-center space-x-1"
          >
            {loading ? (
              <>
                <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                <span>Consultando...</span>
              </>
            ) : (
              <>
                <span>🔍</span>
                <span>Consultar</span>
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Mensaje de error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-3">
          <div className="flex">
            <div className="flex-shrink-0">
              <span className="text-red-500">⚠️</span>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Datos consultados */}
      {consultado && datosConsulta && (
        <div className="bg-green-50 border border-green-200 rounded-md p-4">
          <div className="flex items-center mb-2">
            <span className="text-green-500 mr-2">✅</span>
            <h4 className="text-sm font-medium text-green-800">
              {tipo === 'dni' ? 'Datos RENIEC' : 'Datos SUNAT'}
            </h4>
          </div>
          
          {tipo === 'dni' ? (
            <div className="space-y-1">
              <p className="text-sm text-green-700">
                <strong>Nombres:</strong> {datosConsulta.nombres}
              </p>
              <p className="text-sm text-green-700">
                <strong>Apellidos:</strong> {datosConsulta.apellido_paterno} {datosConsulta.apellido_materno}
              </p>
              <p className="text-sm text-green-700">
                <strong>Nombre Completo:</strong> {datosConsulta.nombre_completo}
              </p>
            </div>
          ) : (
            <div className="space-y-1">
              <p className="text-sm text-green-700">
                <strong>Razón Social:</strong> {datosConsulta.razon_social}
              </p>
              {datosConsulta.nombre_comercial && (
                <p className="text-sm text-green-700">
                  <strong>Nombre Comercial:</strong> {datosConsulta.nombre_comercial}
                </p>
              )}
              <p className="text-sm text-green-700">
                <strong>Estado:</strong> {datosConsulta.estado}
              </p>
              <p className="text-sm text-green-700">
                <strong>Condición:</strong> {datosConsulta.condicion}
              </p>
              {datosConsulta.direccion && (
                <p className="text-sm text-green-700">
                  <strong>Dirección:</strong> {datosConsulta.direccion}
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Ayuda */}
      <div className="text-xs text-gray-500">
        {tipo === 'dni' ? (
          <p>💡 Ingrese el DNI y presione "Consultar" para obtener los datos de RENIEC</p>
        ) : (
          <p>💡 Ingrese el RUC y presione "Consultar" para obtener los datos de SUNAT</p>
        )}
      </div>
    </div>
  );
};

export default ConsultaDocumento; 