import React, { useState } from 'react';
import { Card, CardHeader, CardContent, CardTitle } from './Card';
import { Button } from './Button';
import useTipoCambio from '../../hooks/useTipoCambio';

const TipoCambioWidget = ({ mostrarHistorial = true, tamaño = 'normal' }) => {
  const [fechaConsulta, setFechaConsulta] = useState('');
  const [historialMes, setHistorialMes] = useState([]);
  const [mesConsulta, setMesConsulta] = useState('');
  const [añoConsulta, setAñoConsulta] = useState(new Date().getFullYear());

  const { 
    consultarTipoCambio,
    consultarTipoCambioMes,
    obtenerTipoCambioHoy,
    validarFecha,
    formatearMoneda,
    loading,
    error,
    tipoCambioActual,
    limpiarError
  } = useTipoCambio();

  const handleConsultarFecha = async () => {
    if (!validarFecha(fechaConsulta)) {
      return;
    }

    await consultarTipoCambio(fechaConsulta);
  };

  const handleConsultarMes = async () => {
    if (!mesConsulta || !añoConsulta) {
      return;
    }

    const datos = await consultarTipoCambioMes(parseInt(mesConsulta), parseInt(añoConsulta));
    if (datos) {
      setHistorialMes(datos);
    }
  };

  const formatearFecha = (fecha) => {
    if (!fecha) return '';
    return new Date(fecha).toLocaleDateString('es-PE', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const getVariacionColor = (compra, venta) => {
    // Lógica simple para mostrar tendencia (puedes mejorarla)
    const promedio = (compra + venta) / 2;
    if (promedio > 3.8) return 'text-red-600';
    if (promedio < 3.7) return 'text-green-600';
    return 'text-gray-600';
  };

  if (tamaño === 'mini') {
    // Versión mini para dashboard
    return (
      <div className="bg-white rounded-lg shadow-sm border p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-lg">💱</span>
            <span className="text-sm font-medium text-gray-700">Tipo de Cambio</span>
          </div>
          {tipoCambioActual && (
            <div className="text-right">
              <div className="text-xs text-gray-500">
                {formatearFecha(tipoCambioActual.fecha)}
              </div>
              <div className="text-sm font-bold text-blue-600">
                S/ {tipoCambioActual.venta}
              </div>
            </div>
          )}
        </div>
        {loading && (
          <div className="mt-2 text-xs text-gray-500">Actualizando...</div>
        )}
      </div>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <span>💱</span>
          <span>Tipo de Cambio SUNAT</span>
          <Button
            onClick={obtenerTipoCambioHoy}
            disabled={loading}
            variant="outline"
            className="ml-auto px-2 py-1 text-xs"
          >
            {loading ? '🔄' : '🔄 Actualizar'}
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        
        {/* Tipo de cambio actual */}
        {tipoCambioActual && (
          <div className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-green-50 rounded-lg border">
            <div className="text-center mb-2">
              <h3 className="text-lg font-semibold text-gray-800">
                {formatearFecha(tipoCambioActual.fecha)}
              </h3>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-3 bg-white rounded-md shadow-sm">
                <div className="text-sm text-gray-600 mb-1">💸 Compra</div>
                <div className="text-xl font-bold text-green-600">
                  {formatearMoneda(tipoCambioActual.compra)}
                </div>
              </div>
              <div className="text-center p-3 bg-white rounded-md shadow-sm">
                <div className="text-sm text-gray-600 mb-1">💰 Venta</div>
                <div className="text-xl font-bold text-blue-600">
                  {formatearMoneda(tipoCambioActual.venta)}
                </div>
              </div>
            </div>
            <div className="text-center mt-2">
              <span className="text-xs text-gray-500">
                Fuente: {tipoCambioActual.origen}
              </span>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <div className="flex items-center space-x-2">
              <span className="text-red-500">⚠️</span>
              <span className="text-sm text-red-700">{error}</span>
              <Button
                onClick={limpiarError}
                variant="outline"
                className="ml-auto px-2 py-1 text-xs"
              >
                ✕
              </Button>
            </div>
          </div>
        )}

        {/* Consultar por fecha específica */}
        {mostrarHistorial && (
          <div className="space-y-4">
            <div className="border-t pt-4">
              <h4 className="text-sm font-medium text-gray-700 mb-3">
                📅 Consultar fecha específica
              </h4>
              <div className="flex space-x-2">
                <input
                  type="date"
                  value={fechaConsulta}
                  onChange={(e) => setFechaConsulta(e.target.value)}
                  className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm"
                  max={new Date().toISOString().split('T')[0]}
                />
                <Button
                  onClick={handleConsultarFecha}
                  disabled={loading || !fechaConsulta}
                  className="px-4 py-2 text-sm"
                >
                  Consultar
                </Button>
              </div>
            </div>

            {/* Consultar historial mensual */}
            <div className="border-t pt-4">
              <h4 className="text-sm font-medium text-gray-700 mb-3">
                📊 Historial mensual
              </h4>
              <div className="flex space-x-2 mb-3">
                <select
                  value={mesConsulta}
                  onChange={(e) => setMesConsulta(e.target.value)}
                  className="border border-gray-300 rounded-md px-3 py-2 text-sm"
                >
                  <option value="">Seleccionar mes</option>
                  {Array.from({ length: 12 }, (_, i) => (
                    <option key={i + 1} value={i + 1}>
                      {new Date(2024, i, 1).toLocaleDateString('es-PE', { month: 'long' })}
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  value={añoConsulta}
                  onChange={(e) => setAñoConsulta(e.target.value)}
                  min="2020"
                  max={new Date().getFullYear()}
                  className="border border-gray-300 rounded-md px-3 py-2 text-sm w-24"
                />
                <Button
                  onClick={handleConsultarMes}
                  disabled={loading || !mesConsulta || !añoConsulta}
                  className="px-4 py-2 text-sm"
                >
                  Ver Historial
                </Button>
              </div>

              {/* Mostrar historial mensual */}
              {historialMes.length > 0 && (
                <div className="max-h-64 overflow-y-auto border rounded-md">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>
                        <th className="px-3 py-2 text-left">Fecha</th>
                        <th className="px-3 py-2 text-right">Compra</th>
                        <th className="px-3 py-2 text-right">Venta</th>
                      </tr>
                    </thead>
                    <tbody>
                      {historialMes.map((item, index) => (
                        <tr key={index} className="border-t hover:bg-gray-50">
                          <td className="px-3 py-2">
                            {new Date(item.fecha).toLocaleDateString('es-PE')}
                          </td>
                          <td className="px-3 py-2 text-right text-green-600 font-medium">
                            {item.compra}
                          </td>
                          <td className="px-3 py-2 text-right text-blue-600 font-medium">
                            {item.venta}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Información adicional */}
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
          <div className="flex items-start space-x-2">
            <span className="text-yellow-600">💡</span>
            <div className="text-xs text-yellow-800">
              <p className="font-medium mb-1">Información importante:</p>
              <ul className="space-y-1">
                <li>• Datos oficiales de SUNAT</li>
                <li>• Actualización automática diaria</li>
                <li>• Cache de 30 minutos para optimizar consultas</li>
                <li>• Usado para conversiones USD ↔ PEN</li>
              </ul>
            </div>
          </div>
        </div>

      </CardContent>
    </Card>
  );
};

export default TipoCambioWidget; 