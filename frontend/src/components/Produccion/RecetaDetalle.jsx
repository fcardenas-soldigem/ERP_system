import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import produccionService from '../../services/produccion.service';

const RecetaDetalle = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [receta, setReceta] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    cargarReceta();
  }, [id]);

  const cargarReceta = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await produccionService.getReceta(id);
      setReceta(response.data);
    } catch (err) {
      console.error('Error al cargar receta:', err);
      setError('Error al cargar la receta');
    } finally {
      setLoading(false);
    }
  };

  const handleDuplicar = async () => {
    if (!window.confirm('¿Desea duplicar esta receta?')) return;

    try {
      await produccionService.duplicarReceta(id);
      alert('Receta duplicada exitosamente');
      navigate('/produccion/recetas');
    } catch (err) {
      console.error('Error al duplicar receta:', err);
      alert('Error al duplicar la receta');
    }
  };

  const handleEliminar = async () => {
    if (!window.confirm('¿Está seguro de eliminar esta receta? Esta acción no se puede deshacer.')) return;

    try {
      await produccionService.deleteReceta(id);
      alert('Receta eliminada exitosamente');
      navigate('/produccion/recetas');
    } catch (err) {
      console.error('Error al eliminar receta:', err);
      alert('Error al eliminar la receta. Puede que esté siendo usada en órdenes de producción.');
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

  if (error || !receta) {
    return (
      <div className="container mx-auto p-6">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error || 'Receta no encontrada'}
        </div>
        <button
          onClick={() => navigate('/produccion/recetas')}
          className="mt-4 text-blue-600 hover:text-blue-800"
        >
          ← Volver a recetas
        </button>
      </div>
    );
  }

  const costos = receta.costos || {};

  return (
    <div className="container mx-auto p-6">
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <button
              onClick={() => navigate('/produccion/recetas')}
              className="text-gray-600 hover:text-gray-800"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
            <h1 className="text-3xl font-bold text-gray-800">{receta.nombre}</h1>
            <span
              className={`px-3 py-1 text-sm font-semibold rounded-full ${
                receta.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
              }`}
            >
              {receta.is_active ? 'Activa' : 'Inactiva'}
            </span>
          </div>
          <p className="text-gray-600">Versión {receta.version}</p>
        </div>

        <div className="flex gap-2">
          <Link
            to={`/produccion/recetas/${id}/editar`}
            className="bg-yellow-500 hover:bg-yellow-600 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            Editar
          </Link>
          <button
            onClick={handleDuplicar}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            Duplicar
          </button>
          <button
            onClick={handleEliminar}
            className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Eliminar
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Información Principal */}
        <div className="lg:col-span-2 space-y-6">
          {/* Producto Terminado */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Producto Terminado</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-600">Producto</div>
                <div className="text-base font-medium text-gray-900">{receta.producto_terminado_nombre}</div>
              </div>
              <div>
                <div className="text-sm text-gray-600">SKU</div>
                <div className="text-base font-medium text-gray-900">{receta.producto_terminado_sku}</div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Cantidad Producida</div>
                <div className="text-base font-medium text-gray-900">{receta.cantidad_producida}</div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Tiempo Estimado</div>
                <div className="text-base font-medium text-gray-900">{receta.tiempo_estimado} minutos</div>
              </div>
            </div>
          </div>

          {/* Insumos */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Insumos Necesarios</h2>
            
            {receta.detalles && receta.detalles.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Insumo
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        SKU
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                        Cantidad
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                        Costo Unit.
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                        Costo Total
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {receta.detalles.map((detalle) => (
                      <tr key={detalle.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">{detalle.insumo_nombre}</div>
                          {detalle.notas && (
                            <div className="text-xs text-gray-500">{detalle.notas}</div>
                          )}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                          {detalle.insumo_sku}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right">
                          {detalle.cantidad} {detalle.insumo_unidad_medida}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 text-right">
                          S/ {parseFloat(detalle.costo_unitario).toFixed(2)}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900 text-right">
                          S/ {parseFloat(detalle.costo_total).toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-gray-50">
                    <tr>
                      <td colSpan="4" className="px-4 py-3 text-sm font-medium text-gray-900 text-right">
                        Subtotal Insumos:
                      </td>
                      <td className="px-4 py-3 text-sm font-bold text-gray-900 text-right">
                        S/ {parseFloat(costos.costo_insumos || 0).toFixed(2)}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                No hay insumos definidos para esta receta
              </div>
            )}
          </div>

          {/* Notas */}
          {receta.notas && (
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">Notas / Instrucciones</h2>
              <p className="text-gray-700 whitespace-pre-wrap">{receta.notas}</p>
            </div>
          )}

          {/* Metadatos */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Información del Sistema</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-gray-600">Creada</div>
                <div className="font-medium text-gray-900">
                  {new Date(receta.created_at).toLocaleString('es-PE')}
                </div>
              </div>
              <div>
                <div className="text-gray-600">Última modificación</div>
                <div className="font-medium text-gray-900">
                  {new Date(receta.updated_at).toLocaleString('es-PE')}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar - Resumen de Costos */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow-sm p-6 sticky top-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Resumen de Costos</h3>
            
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">Insumos</span>
                  <span className="font-medium">S/ {parseFloat(costos.costo_insumos || 0).toFixed(2)}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{
                      width: `${((costos.costo_insumos || 0) / (costos.costo_total || 1)) * 100}%`
                    }}
                  ></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">Mano de Obra</span>
                  <span className="font-medium">S/ {parseFloat(receta.costo_mano_obra || 0).toFixed(2)}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-600 h-2 rounded-full"
                    style={{
                      width: `${((receta.costo_mano_obra || 0) / (costos.costo_total || 1)) * 100}%`
                    }}
                  ></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">Costos Indirectos</span>
                  <span className="font-medium">S/ {parseFloat(receta.costo_indirecto || 0).toFixed(2)}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-yellow-600 h-2 rounded-full"
                    style={{
                      width: `${((receta.costo_indirecto || 0) / (costos.costo_total || 1)) * 100}%`
                    }}
                  ></div>
                </div>
              </div>

              <div className="border-t pt-4">
                <div className="flex justify-between text-base font-semibold mb-2">
                  <span>Costo Total:</span>
                  <span className="text-blue-600">S/ {parseFloat(costos.costo_total || 0).toFixed(2)}</span>
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="text-xs text-gray-600 mb-1">Costo Unitario Teórico</div>
                <div className="text-3xl font-bold text-blue-600">
                  S/ {parseFloat(costos.costo_unitario || 0).toFixed(2)}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Por {receta.cantidad_producida} unidad(es)
                </div>
              </div>

              <div className="pt-4 space-y-2">
                <Link
                  to={`/produccion/ordenes/nueva?receta_id=${receta.id}`}
                  className="w-full bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg font-medium text-center block"
                >
                  Crear Orden de Producción
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RecetaDetalle;
