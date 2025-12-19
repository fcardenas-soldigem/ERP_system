import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { produccionService } from '../../services/produccion.service';

const OrdenProduccionEjecucion = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [orden, setOrden] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [guardando, setGuardando] = useState(false);

  const [datosFinalizacion, setDatosFinalizacion] = useState({
    cantidad_producida: '',
    costo_mano_obra_real: 0,
    costo_indirecto_real: 0,
    observaciones: ''
  });

  useEffect(() => {
    cargarOrden();
  }, [id]);

  const cargarOrden = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await produccionService.getOrden(id);
      const ordenData = response.data;
      setOrden(ordenData);

      // Pre-llenar cantidad producida con la planificada
      if (!datosFinalizacion.cantidad_producida) {
        setDatosFinalizacion(prev => ({
          ...prev,
          cantidad_producida: ordenData.cantidad_planificada,
          costo_mano_obra_real: ordenData.receta_info.costo_mano_obra || 0,
          costo_indirecto_real: ordenData.receta_info.costo_indirecto || 0
        }));
      }
    } catch (err) {
      console.error('Error al cargar orden:', err);
      setError('Error al cargar la orden de producción');
    } finally {
      setLoading(false);
    }
  };

  const handleIniciar = async () => {
    if (!window.confirm('¿Desea iniciar esta orden de producción?')) return;

    try {
      setGuardando(true);
      await produccionService.iniciarOrden(id);
      alert('Orden iniciada exitosamente');
      cargarOrden();
    } catch (err) {
      console.error('Error al iniciar orden:', err);
      const errorMsg = err.response?.data?.error || 'Error al iniciar la orden';
      alert(errorMsg);
    } finally {
      setGuardando(false);
    }
  };

  const handleActualizarConsumo = async (consumo) => {
    const cantidadReal = prompt(
      `Ingrese la cantidad real consumida de ${consumo.insumo_nombre}:`,
      consumo.cantidad_real || consumo.cantidad_teorica
    );

    if (cantidadReal === null) return;

    const cantidad = parseFloat(cantidadReal);
    if (isNaN(cantidad) || cantidad < 0) {
      alert('Cantidad inválida');
      return;
    }

    const merma = prompt('Ingrese la cantidad de merma/desperdicio:', '0');
    if (merma === null) return;

    const cantidadMerma = parseFloat(merma);
    if (isNaN(cantidadMerma) || cantidadMerma < 0) {
      alert('Merma inválida');
      return;
    }

    try {
      setGuardando(true);
      await produccionService.actualizarConsumo(id, {
        insumo_id: consumo.insumo,
        cantidad_real: cantidad,
        merma: cantidadMerma,
        notas: ''
      });
      alert('Consumo actualizado exitosamente');
      cargarOrden();
    } catch (err) {
      console.error('Error al actualizar consumo:', err);
      alert(err.response?.data?.error || 'Error al actualizar consumo');
    } finally {
      setGuardando(false);
    }
  };

  const handleFinalizar = async () => {
    if (!datosFinalizacion.cantidad_producida || parseFloat(datosFinalizacion.cantidad_producida) <= 0) {
      alert('Debe ingresar la cantidad producida');
      return;
    }

    // Validar que todos los consumos estén registrados
    const consumosSinRegistrar = orden.consumos.filter(c => !c.cantidad_real || c.cantidad_real === 0);
    if (consumosSinRegistrar.length > 0) {
      if (!window.confirm(
        `Hay ${consumosSinRegistrar.length} insumos sin consumo registrado. ¿Desea continuar de todas formas? Esto puede causar un error.`
      )) {
        return;
      }
    }

    if (!window.confirm('¿Está seguro de finalizar esta orden? Esta acción no se puede deshacer.')) return;

    try {
      setGuardando(true);
      await produccionService.finalizarOrden(id, {
        cantidad_producida: parseFloat(datosFinalizacion.cantidad_producida),
        costo_mano_obra_real: parseFloat(datosFinalizacion.costo_mano_obra_real),
        costo_indirecto_real: parseFloat(datosFinalizacion.costo_indirecto_real),
        observaciones: datosFinalizacion.observaciones
      });
      alert('Orden finalizada exitosamente');
      navigate(`/produccion/ordenes/${id}`);
    } catch (err) {
      console.error('Error al finalizar orden:', err);
      const errorMsg = err.response?.data?.error || 'Error al finalizar la orden';
      alert(errorMsg);
    } finally {
      setGuardando(false);
    }
  };

  const handleCancelar = async () => {
    const motivo = prompt('Ingrese el motivo de cancelación:');
    if (!motivo) return;

    if (!window.confirm('¿Está seguro de cancelar esta orden?')) return;

    try {
      setGuardando(true);
      await produccionService.cancelarOrden(id, motivo);
      alert('Orden cancelada exitosamente');
      navigate('/app/produccion/ordenes');
    } catch (err) {
      console.error('Error al cancelar orden:', err);
      alert(err.response?.data?.error || 'Error al cancelar la orden');
    } finally {
      setGuardando(false);
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
      </div>
    );
  }

  const consumosRegistrados = orden.consumos.filter(c => c.cantidad_real > 0).length;
  const porcentajeAvance = (consumosRegistrados / orden.consumos.length) * 100;

  return (
    <div className="container mx-auto p-6">
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-bold text-gray-800">OP-{orden.numero}</h1>
            <span className={`px-3 py-1 text-sm font-semibold rounded-full ${
              orden.estado === 'pendiente' ? 'bg-yellow-100 text-yellow-800' :
              orden.estado === 'en_proceso' ? 'bg-blue-100 text-blue-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {orden.estado_display}
            </span>
          </div>
          <p className="text-gray-600">{orden.receta_info.producto_terminado_nombre}</p>
        </div>

        <div className="flex gap-2">
          {orden.estado === 'pendiente' && (
            <button
              onClick={handleIniciar}
              disabled={guardando}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg flex items-center gap-2 disabled:opacity-50"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Iniciar Producción
            </button>
          )}
          
          {orden.estado !== 'finalizada' && orden.estado !== 'cancelada' && (
            <button
              onClick={handleCancelar}
              disabled={guardando}
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-3 rounded-lg disabled:opacity-50"
            >
              Cancelar Orden
            </button>
          )}

          <button
            onClick={() => navigate('/app/produccion/ordenes')}
            className="bg-gray-200 hover:bg-gray-300 text-gray-700 px-4 py-3 rounded-lg"
          >
            Volver
          </button>
        </div>
      </div>

      {/* Información */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="text-sm text-gray-600">Cantidad Planificada</div>
          <div className="text-2xl font-bold text-gray-900">{orden.cantidad_planificada}</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="text-sm text-gray-600">Fecha Programada</div>
          <div className="text-2xl font-bold text-gray-900">
            {new Date(orden.fecha_programada).toLocaleDateString('es-PE')}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="text-sm text-gray-600">Tiempo Estimado</div>
          <div className="text-2xl font-bold text-gray-900">{orden.receta_info.tiempo_estimado} min</div>
        </div>
        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="text-sm text-gray-600">Consumos Registrados</div>
          <div className="text-2xl font-bold text-blue-600">
            {consumosRegistrados}/{orden.consumos.length}
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
            <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${porcentajeAvance}%` }}></div>
          </div>
        </div>
      </div>

      {/* Consumo de Insumos */}
      <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Consumo de Insumos</h2>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Insumo</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Teórico</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Real</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Diferencia</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Merma</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Costo Total</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Acción</th>
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
                  <td className="px-4 py-3 text-right text-sm">
                    <span className={`font-medium ${consumo.cantidad_real > 0 ? 'text-blue-600' : 'text-gray-400'}`}>
                      {consumo.cantidad_real > 0 ? parseFloat(consumo.cantidad_real).toFixed(2) : '-'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-sm">
                    {consumo.cantidad_real > 0 ? (
                      <span className={`font-medium ${
                        consumo.diferencia > 0 ? 'text-red-600' : 
                        consumo.diferencia < 0 ? 'text-green-600' : 'text-gray-600'
                      }`}>
                        {consumo.diferencia > 0 ? '+' : ''}{parseFloat(consumo.diferencia).toFixed(2)}
                      </span>
                    ) : '-'}
                  </td>
                  <td className="px-4 py-3 text-right text-sm">
                    {consumo.merma > 0 ? (
                      <span className="text-red-600 font-medium">
                        {parseFloat(consumo.merma).toFixed(2)}
                      </span>
                    ) : '-'}
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-medium text-gray-900">
                    S/ {parseFloat(consumo.costo_total).toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {orden.estado === 'en_proceso' && (
                      <button
                        onClick={() => handleActualizarConsumo(consumo)}
                        disabled={guardando}
                        className="text-blue-600 hover:text-blue-900 text-sm font-medium disabled:opacity-50"
                      >
                        {consumo.cantidad_real > 0 ? 'Editar' : 'Registrar'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Finalización */}
      {orden.estado === 'en_proceso' && (
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Finalizar Producción</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Cantidad Producida *
              </label>
              <input
                type="number"
                value={datosFinalizacion.cantidad_producida}
                onChange={(e) => setDatosFinalizacion(prev => ({ ...prev, cantidad_producida: e.target.value }))}
                min="0.01"
                step="0.01"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Costo Mano de Obra (S/)
              </label>
              <input
                type="number"
                value={datosFinalizacion.costo_mano_obra_real}
                onChange={(e) => setDatosFinalizacion(prev => ({ ...prev, costo_mano_obra_real: e.target.value }))}
                min="0"
                step="0.01"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Costos Indirectos (S/)
              </label>
              <input
                type="number"
                value={datosFinalizacion.costo_indirecto_real}
                onChange={(e) => setDatosFinalizacion(prev => ({ ...prev, costo_indirecto_real: e.target.value }))}
                min="0"
                step="0.01"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex items-end">
              <button
                onClick={handleFinalizar}
                disabled={guardando}
                className="w-full bg-green-600 hover:bg-green-700 text-white py-2 rounded-lg font-medium disabled:opacity-50"
              >
                {guardando ? 'Finalizando...' : 'Finalizar Orden'}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Observaciones Finales
            </label>
            <textarea
              value={datosFinalizacion.observaciones}
              onChange={(e) => setDatosFinalizacion(prev => ({ ...prev, observaciones: e.target.value }))}
              rows="2"
              placeholder="Observaciones sobre la producción..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default OrdenProduccionEjecucion;
