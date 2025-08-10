import React, { useState } from 'react';
import ConsultaDocumento from './ConsultaDocumento';
import { Card, CardHeader, CardContent, CardTitle } from './Card';

const EjemploConsultaDocumento = () => {
  const [datosPersona, setDatosPersona] = useState(null);
  const [datosEmpresa, setDatosEmpresa] = useState(null);
  const [dniValor, setDniValor] = useState('');
  const [rucValor, setRucValor] = useState('');

  const handleDatosPersonaConsultados = (datos) => {
    setDatosPersona(datos);
    console.log('Datos de persona consultados:', datos);
  };

  const handleDatosEmpresaConsultados = (datos) => {
    setDatosEmpresa(datos);
    console.log('Datos de empresa consultados:', datos);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto p-6">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          🔍 Consulta de Documentos
        </h1>
        <p className="text-gray-600">
          Ejemplo de uso de la integración con APIs.net.pe para consultar DNI y RUC
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Consulta DNI */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <span>👤</span>
              <span>Consulta de DNI</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ConsultaDocumento
              tipo="dni"
              valor={dniValor}
              onChange={setDniValor}
              onDatosConsultados={handleDatosPersonaConsultados}
              placeholder="Ingrese DNI para consultar en RENIEC"
              required
            />
            
            {datosPersona && (
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
                <h4 className="font-medium text-blue-900 mb-2">📋 Datos Obtenidos:</h4>
                <div className="space-y-1 text-sm text-blue-800">
                  <p><strong>Documento:</strong> {datosPersona.numero_documento}</p>
                  <p><strong>Nombres:</strong> {datosPersona.nombres}</p>
                  <p><strong>Apellido Paterno:</strong> {datosPersona.apellido_paterno}</p>
                  <p><strong>Apellido Materno:</strong> {datosPersona.apellido_materno}</p>
                  <p><strong>Nombre Completo:</strong> {datosPersona.nombre_completo}</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Consulta RUC */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <span>🏢</span>
              <span>Consulta de RUC</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ConsultaDocumento
              tipo="ruc"
              valor={rucValor}
              onChange={setRucValor}
              onDatosConsultados={handleDatosEmpresaConsultados}
              placeholder="Ingrese RUC para consultar en SUNAT"
              required
            />
            
            {datosEmpresa && (
              <div className="mt-4 p-4 bg-purple-50 border border-purple-200 rounded-md">
                <h4 className="font-medium text-purple-900 mb-2">🏢 Datos Obtenidos:</h4>
                <div className="space-y-1 text-sm text-purple-800">
                  <p><strong>RUC:</strong> {datosEmpresa.ruc}</p>
                  <p><strong>Razón Social:</strong> {datosEmpresa.razon_social}</p>
                  {datosEmpresa.nombre_comercial && (
                    <p><strong>Nombre Comercial:</strong> {datosEmpresa.nombre_comercial}</p>
                  )}
                  <p><strong>Estado:</strong> {datosEmpresa.estado}</p>
                  <p><strong>Condición:</strong> {datosEmpresa.condicion}</p>
                  {datosEmpresa.direccion && (
                    <p><strong>Dirección:</strong> {datosEmpresa.direccion}</p>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

      </div>

      {/* Información del servicio */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <span>ℹ️</span>
            <span>Información del Servicio</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            <div className="space-y-3">
              <h4 className="font-medium text-gray-900">🔐 Características de Seguridad</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Token API protegido en el backend</li>
                <li>• Validación de formatos antes de consultar</li>
                <li>• Cache de resultados por 1 hora</li>
                <li>• Manejo de errores y límites de API</li>
                <li>• Timeout de 10 segundos por consulta</li>
              </ul>
            </div>

            <div className="space-y-3">
              <h4 className="font-medium text-gray-900">⚡ Funcionalidades</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Consulta en tiempo real</li>
                <li>• Autocompletado de formularios</li>
                <li>• Validación automática de documentos</li>
                <li>• Manejo de estados de carga</li>
                <li>• Mensajes informativos y de error</li>
              </ul>
            </div>

          </div>

          <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
            <div className="flex items-start space-x-2">
              <span className="text-yellow-600">⚠️</span>
              <div className="text-sm text-yellow-800">
                <p className="font-medium mb-1">Nota sobre el uso:</p>
                <p>
                  Este servicio consume la API de apis.net.pe y tiene limitaciones de uso según el plan contratado. 
                  Los datos se obtienen directamente de RENIEC (DNI) y SUNAT (RUC).
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

    </div>
  );
};

export default EjemploConsultaDocumento; 