import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import produccionService from '../../services/produccion.service';
import { getAlmacenes } from '../../services/almacenes.service';

const OrdenProduccionForm = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const recetaIdParam = searchParams.get('receta_id');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [recetas, setRecetas] = useState([]);
  const [almacenes, setAlmacenes] = useState([]);
  const [validacionStock, setValidacionStock] = useState(null);
  const [recetaSeleccionada, setRecetaSeleccionada] = useState(null);

  const [formData, setFormData] = useState({
    receta_id: recetaIdParam || '',
    cantidad: 1,
    fecha_programada: new Date().toISOString().split('T')[0],
    almacen_insumos_id: '',
    almacen_destino_id: '',
    observaciones: ''
  });

  useEffect(() => {
    cargarDatos();
  }, []);

  useEffect(() => {
    if (formData.receta_id && recetaIdParam) {
      cargarReceta(formData.receta_id);
    }
  }, [formData.receta_id, recetaIdParam]);

  const cargarDatos = async () => {
    try {
      setLoading(true);
      const [recetasRes, almacenesRes] = await Promise.all([
        produccionService.getRecetas({ is_active: true }),
        getAlmacenes()
      ]);
      
      setRecetas(recetasRes.data);
      setAlmacenes(almacenesRes.data);
    } catch (err) {
      console.error('Error al cargar datos:', err);
      setError('Error al cargar datos iniciales');
    } finally {
      setLoading(false);
    }
  };

  const cargarReceta = async (id) => {
    try {
      const response = await produccionService.getReceta(id);
      setRecetaSeleccionada(response.data);
    } catch (err) {
      console.error('Error al cargar receta:', err);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    if (name === 'receta_id') {
      cargarReceta(value);
      setValidacionStock(null);
    }

    if (['receta_id', 'cantidad', 'almacen_insumos_id'].includes(name)) {
      setValidacionStock(null);
    }
  };

  const validarStock = async () => {
    if (!formData.receta_id || !formData.cantidad || !formData.almacen_insumos_id) {
      alert('Complete receta, cantidad y almacén de insumos para validar');
      return;
    }

    try {
      setLoading(true);
      const response = await produccionService.validarStock({
        receta_id: parseInt(formData.receta_id),
        cantidad: parseFloat(formData.cantidad),
        almacen_insumos_id: parseInt(formData.almacen_insumos_id)
      });
      setValidacionStock(response.data);
    } catch (err) {
      console.error('Error al validar stock:', err);
      alert('Error al validar stock');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.receta_id || !formData.cantidad || !formData.almacen_insumos_id || !formData.almacen_destino_id) {
      alert('Complete todos los campos requeridos');
      return;
    }

    if (parseFloat(formData.cantidad) <= 0) {
      alert('La cantidad debe ser mayor a 0');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const dataToSend = {
        receta_id: parseInt(formData.receta_id),
        cantidad: parseFloat(formData.cantidad),
        fecha_programada: formData.fecha_programada,
        almacen_insumos_id: parseInt(formData.almacen_insumos_id),
        almacen_destino_id: parseInt(formData.almacen_destino_id),
        observaciones: formData.observaciones || ''
      };

      const response = await produccionService.createOrden(dataToSend);
      alert('Orden de producción creada exitosamente');
      navigate(`/produccion/ordenes/${response.data.id}`);
    } catch (err) {
      console.error('Error al crear orden:', err);
      const errorMsg = err.response?.data?.error || 'Error al crear la orden de producción';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  if (loading && recetas.length === 0) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800">Nueva Orden de Producción</h1>
        <p className="text-gray-600 mt-1">Complete los datos para crear una orden de producción</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 whitespace-pre-wrap">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {/* Información Básica */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">Información de la Orden</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Receta a Producir *
                  </label>
                  <select
                    name="receta_id"
                    value={formData.receta_id}
                    onChange={handleChange}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Seleccione una receta</option>
                    {recetas.map(receta => (
                      <option key={receta.id} value={receta.id}>
                        {receta.nombre} - {receta.producto_terminado_nombre} (v{receta.version})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Cantidad a Producir *
                  </label>
                  <input
                    type="number"
                    name="cantidad"
                    value={formData.cantidad}
                    onChange={handleChange}
                    min="0.01"
                    step="0.01"
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Fecha Programada *
                  </label>
                  <input
                    type="date"
                    name="fecha_programada"
                    value={formData.fecha_programada}
                    onChange={handleChange}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Almacén de Insumos *
                  </label>
                  <select
                    name="almacen_insumos_id"
                    value={formData.almacen_insumos_id}
                    onChange={handleChange}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Seleccione almacén</option>
                    {almacenes.map(almacen => (
                      <option key={almacen.id} value={almacen.id}>
                        {almacen.nombre}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Almacén de Destino *
                  </label>
                  <select
                    name="almacen_destino_id"
                    value={formData.almacen_destino_id}
                    onChange={handleChange}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Seleccione almacén</option>
                    {almacenes.map(almacen => (
                      <option key={almacen.id} value={almacen.id}>
                        {almacen.nombre}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Observaciones
                  </label>
                  <textarea
                    name="observaciones"
                    value={formData.observaciones}
                    onChange={handleChange}
                    rows="3"
                    placeholder="Notas adicionales..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* Validación de Stock */}
            {formData.receta_id && formData.cantidad && formData.almacen_insumos_id && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-lg font-semibold text-gray-800">Validación de Stock</h2>
                  <button
                    type="button"
                    onClick={validarStock}
                    disabled={loading}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm"
                  >
                    {loading ? 'Validando...' : 'Validar Stock'}
                  </button>
                </div>

                {validacionStock && (
                  <div className="space-y-2">
                    {validacionStock.valido ? (
                      <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
                        ✓ Stock suficiente para todos los insumos
                      </div>
                    ) : (
                      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                        ✗ Stock insuficiente para algunos insumos
                      </div>
                    )}

                    <div className="overflow-x-auto">
                      <table className="min-w-full text-sm">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Insumo</th>
                            <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Necesario</th>
                            <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Disponible</th>
                            <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Estado</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200">
                          {validacionStock.insumos.map((insumo, idx) => (
                            <tr key={idx}>
                              <td className="px-3 py-2 text-gray-900">
                                {insumo.insumo_nombre}
                                <span className="text-gray-500 text-xs ml-1">({insumo.insumo_sku})</span>
                              </td>
                              <td className="px-3 py-2 text-right text-gray-900">{insumo.cantidad_necesaria}</td>
                              <td className="px-3 py-2 text-right text-gray-900">{insumo.stock_disponible}</td>
                              <td className="px-3 py-2 text-center">
                                {insumo.suficiente ? (
                                  <span className="text-green-600 font-semibold">✓</span>
                                ) : (
                                  <span className="text-red-600 font-semibold">✗ Falta: {insumo.faltante}</span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Sidebar - Resumen */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-sm p-6 sticky top-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Resumen</h3>
              
              {recetaSeleccionada ? (
                <div className="space-y-4">
                  <div>
                    <div className="text-sm text-gray-600 mb-1">Producto</div>
                    <div className="text-base font-medium text-gray-900">{recetaSeleccionada.producto_terminado_nombre}</div>
                  </div>

                  <div>
                    <div className="text-sm text-gray-600 mb-1">Cantidad a Producir</div>
                    <div className="text-2xl font-bold text-blue-600">{formData.cantidad}</div>
                  </div>

                  <div>
                    <div className="text-sm text-gray-600 mb-1">Tiempo Estimado</div>
                    <div className="text-base font-medium text-gray-900">
                      {Math.round((recetaSeleccionada.tiempo_estimado / recetaSeleccionada.cantidad_producida) * parseFloat(formData.cantidad || 0))} min
                    </div>
                  </div>

                  {recetaSeleccionada.costos && (
                    <div>
                      <div className="text-sm text-gray-600 mb-1">Costo Estimado Total</div>
                      <div className="text-xl font-bold text-gray-900">
                        S/ {(recetaSeleccionada.costos.costo_unitario * parseFloat(formData.cantidad || 0)).toFixed(2)}
                      </div>
                    </div>
                  )}

                  <div className="border-t pt-4">
                    <div className="text-sm text-gray-600 mb-2">Insumos Requeridos</div>
                    <div className="text-base font-medium text-gray-900">{recetaSeleccionada.detalles?.length || 0} insumos</div>
                  </div>
                </div>
              ) : (
                <div className="text-center text-gray-500 py-8">
                  Seleccione una receta para ver el resumen
                </div>
              )}

              <div className="pt-6 space-y-2">
                <button
                  type="submit"
                  disabled={loading || (validacionStock && !validacionStock.valido)}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Creando...' : 'Crear Orden'}
                </button>

                <button
                  type="button"
                  onClick={() => navigate('/produccion/ordenes')}
                  className="w-full bg-gray-200 hover:bg-gray-300 text-gray-700 py-3 rounded-lg font-medium"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};

export default OrdenProduccionForm;
