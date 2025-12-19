import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import produccionService from '../../services/produccion.service';

const OrdenDetalle = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [orden, setOrden] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    cargarOrden();
  }, [id]);

  const cargarOrden = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await produccionService.getOrden(id);
      setOrden(response.data);
    } catch (err) {
      console.error('Error al cargar orden:', err);
      setError('Error al cargar la orden de producción');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  if (error || !orden) {
    return (
      <div className="container mx-auto p-6">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error || 'Orden no encontrada'}
        </div>
        <button onClick={() => navigate('/produccion/ordenes')} className="mt-4 text-blue-600 hover:text-blue-800">
          ← Volver a órdenes
        </button>
      </div>
    );
  }

  const getEstadoBadge = (estado) => {
    const badges = {
      pendiente: 'bg-yellow-100 text-yellow-800',
      en_proceso: 'bg-blue-100 text-blue-800',
      finalizada: 'bg-green-100 text-green-800',
      cancelada: 'bg-gray-100 text-gray-800'
    };
    return badges[estado] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="container mx-auto p-6">
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <button onClick={() => navigate('/produccion/ordenes')} className="text-gray-600 hover:text-gray-800">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
            <h1 className="text-3xl font-bold text-gray-800">OP-{orden.numero}</h1>
            <span className={`px-3 py-1 text-sm font-semibold rounded-full ${getEstadoBadge(orden.estado)}`}>
              {orden.estado_display}
            </span>
            {orden.esta_retrasada && orden.estado !== 'finalizada' && (
              <span className="px-3 py-1 text-sm font-semibold rounded-full bg-red-100 text-red-800">
                Retrasada
              </span>
            )}
          </div>
          <p className="text-gray-600">{orden.receta_info.nombre}</p>
        </div>

        <div className="flex gap-2">
          {orden.estado === 'pendiente' && (
            <button
              onClick={() => navigate(`/produccion/ordenes/${id}/ejecutar`)}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
            >
              Ejecutar
            </button>
          )}
          {orden.estado === 'en_proceso' && (
            <button
              onClick={() => navigate(`/produccion/ordenes/${id}/ejecutar`)}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg"
            >
              Continuar
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Columna Principal */}
        <div className="lg:col-span-2 space-y-6">
          {/* Información General */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Información General</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-600">Producto Terminado</div>
                <div className="text-base font-medium text-gray-900">{orden.receta_info.producto_terminado_nombre}</div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Receta</div>
                <div className="text-base font-medium text-gray-900">{orden.receta_info.nombre} (v{orden.receta_info.version})</div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Cantidad Planificada</div>
                <div className="text-base font-medium text-gray-900">{orden.cantidad_planificada}</div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Cantidad Producida</div>
                <div className="text-base font-medium text-gray-900">
                  {orden.cantidad_producida || '-'}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Fecha Programada</div>
                <div className="text-base font-medium text-gray-900">
                  {new Date(orden.fecha_programada).toLocaleDateString('es-PE')}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Fecha Inicio</div>
                <div className="text-base font-medium text-gray-900">
                  {orden.fecha_inicio ? new Date(orden.fecha_inicio).toLocaleString('es-PE') : '-'}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Fecha Finalización</div>
                <div className="text-base font-medium text-gray-900">
                  {orden.fecha_fin ? new Date(orden.fecha_fin).toLocaleString('es-PE') : '-'}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Tiempo Real</div>
                <div className="text-base font-medium text-gray-900">
                  {orden.tiempo_real > 0 ? `${orden.tiempo_real} min` : '-'}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Almacén Insumos</div>
                <div className="text-base font-medium text-gray-900">{orden.almacen_insumos_nombre}</div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Almacén Destino</div>
                <div className="text-base font-medium text-gray-900">{orden.almacen_destino_nombre}</div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Responsable</div>
                <div className="text-base font-medium text-gray-900">{orden.responsable_nombre || '-'}</div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Creado por</div>
                <div className="text-base font-medium text-gray-900">{orden.created_by_nombre || '-'}</div>
              </div>
            </div>
          </div>

          {/* Consumo de Insumos */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Consumo de Insumos</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Insumo</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Teórico</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Real</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Diferencia</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">% Var.</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Merma</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Costo</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {orden.consumos.map((consumo) => (
                    <tr key={consumo.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="text-sm font-medium text-gray-900">{consumo.insumo_nombre}</div>
                        <div className="text-xs text-gray-500">{consumo.insumo_sku}</div>
                      </td>
                      <td className="px-4 py-3 text-right text-sm text-gray-900">
                        {parseFloat(consumo.cantidad_teorica).toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-right text-sm font-medium text-gray-900">
                        {parseFloat(consumo.cantidad_real).toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-right text-sm">
                        <span className={`font-medium ${
                          consumo.diferencia > 0 ? 'text-red-600' :
                          consumo.diferencia < 0 ? 'text-green-600' : 'text-gray-600'
                        }`}>
                          {consumo.diferencia > 0 ? '+' : ''}{parseFloat(consumo.diferencia).toFixed(2)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-sm">
                        <span className={`${
                          Math.abs(consumo.porcentaje_diferencia) > 10 ? 'text-red-600 font-semibold' : 'text-gray-600'
                        }`}>
                          {consumo.porcentaje_diferencia > 0 ? '+' : ''}{parseFloat(consumo.porcentaje_diferencia).toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-sm">
                        {consumo.merma > 0 ? (
                          <span className="text-red-600">
                            {parseFloat(consumo.merma).toFixed(2)} ({parseFloat(consumo.porcentaje_merma).toFixed(1)}%)
                          </span>
                        ) : '-'}
                      </td>
                      <td className="px-4 py-3 text-right text-sm font-medium text-gray-900">
                        S/ {parseFloat(consumo.costo_total).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Observaciones */}
          {orden.observaciones && (
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">Observaciones</h2>
              <p className="text-gray-700 whitespace-pre-wrap">{orden.observaciones}</p>
            </div>
          )}
        </div>

        {/* Sidebar - Métricas */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow-sm p-6 sticky top-6 space-y-6">
            {/* Eficiencia */}
            {orden.estado === 'finalizada' && (
              <>
                <div>
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">Eficiencia</h3>
                  
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-600">Producción</span>
                        <span className={`font-semibold ${
                          orden.eficiencia_produccion >= 95 ? 'text-green-600' :
                          orden.eficiencia_produccion >= 80 ? 'text-yellow-600' : 'text-red-600'
                        }`}>
                          {parseFloat(orden.eficiencia_produccion).toFixed(1)}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            orden.eficiencia_produccion >= 95 ? 'bg-green-600' :
                            orden.eficiencia_produccion >= 80 ? 'bg-yellow-600' : 'bg-red-600'
                          }`}
                          style={{ width: `${Math.min(orden.eficiencia_produccion, 100)}%` }}
                        ></div>
                      </div>
                    </div>

                    {orden.eficiencia_tiempo > 0 && (
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-600">Tiempo</span>
                          <span className={`font-semibold ${
                            orden.eficiencia_tiempo >= 90 ? 'text-green-600' :
                            orden.eficiencia_tiempo >= 70 ? 'text-yellow-600' : 'text-red-600'
                          }`}>
                            {parseFloat(orden.eficiencia_tiempo).toFixed(1)}%
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${
                              orden.eficiencia_tiempo >= 90 ? 'bg-green-600' :
                              orden.eficiencia_tiempo >= 70 ? 'bg-yellow-600' : 'bg-red-600'
                            }`}
                            style={{ width: `${Math.min(orden.eficiencia_tiempo, 100)}%` }}
                          ></div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Costos Reales */}
                {orden.costos_reales && (
                  <div>
                    <h3 className="text-lg font-semibold text-gray-800 mb-4">Costos Reales</h3>
                    
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Insumos:</span>
                        <span className="font-medium">S/ {parseFloat(orden.costos_reales.costo_insumos).toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Mano de Obra:</span>
                        <span className="font-medium">S/ {parseFloat(orden.costos_reales.costo_mano_obra).toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Costos Indirectos:</span>
                        <span className="font-medium">S/ {parseFloat(orden.costos_reales.costo_indirecto).toFixed(2)}</span>
                      </div>
                      
                      <div className="border-t pt-2">
                        <div className="flex justify-between text-base font-semibold">
                          <span>Costo Total:</span>
                          <span className="text-blue-600">S/ {parseFloat(orden.costos_reales.costo_total).toFixed(2)}</span>
                        </div>
                      </div>

                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mt-3">
                        <div className="text-xs text-gray-600 mb-1">Costo Unitario Real</div>
                        <div className="text-2xl font-bold text-blue-600">
                          S/ {parseFloat(orden.costos_reales.costo_unitario).toFixed(2)}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Información del Sistema */}
            <div>
              <h3 className="text-sm font-semibold text-gray-800 mb-2">Información del Sistema</h3>
              <div className="space-y-2 text-xs text-gray-600">
                <div>
                  <span className="font-medium">Creada:</span> {new Date(orden.created_at).toLocaleString('es-PE')}
                </div>
                <div>
                  <span className="font-medium">Actualizada:</span> {new Date(orden.updated_at).toLocaleString('es-PE')}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OrdenDetalle;
