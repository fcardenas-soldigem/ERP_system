import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import produccionService from '../../services/produccion.service';
import productosService from '../../services/productos.service';

const RecetaForm = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEditing = Boolean(id);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [productos, setProductos] = useState([]);
  const [insumos, setInsumos] = useState([]);

  const [formData, setFormData] = useState({
    producto_terminado: '',
    nombre: '',
    cantidad_producida: 1,
    tiempo_estimado: 0,
    costo_mano_obra: 0,
    costo_indirecto: 0,
    is_active: true,
    version: 1,
    notas: '',
    detalles: []
  });

  useEffect(() => {
    cargarProductos();
    if (isEditing) {
      cargarReceta();
    }
  }, [id]);

  const cargarProductos = async () => {
    try {
      const response = await productosService.getProductos();
      setProductos(response.data);
      setInsumos(response.data); // Los insumos son productos también
    } catch (err) {
      console.error('Error al cargar productos:', err);
      setError('Error al cargar productos');
    }
  };

  const cargarReceta = async () => {
    try {
      setLoading(true);
      const response = await produccionService.getReceta(id);
      const receta = response.data;
      
      setFormData({
        producto_terminado: receta.producto_terminado,
        nombre: receta.nombre,
        cantidad_producida: receta.cantidad_producida,
        tiempo_estimado: receta.tiempo_estimado,
        costo_mano_obra: receta.costo_mano_obra,
        costo_indirecto: receta.costo_indirecto,
        is_active: receta.is_active,
        version: receta.version,
        notas: receta.notas || '',
        detalles: receta.detalles || []
      });
    } catch (err) {
      console.error('Error al cargar receta:', err);
      setError('Error al cargar la receta');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const agregarInsumo = () => {
    setFormData(prev => ({
      ...prev,
      detalles: [
        ...prev.detalles,
        {
          insumo: '',
          cantidad: 0,
          unidad_medida: 'unidad',
          costo_unitario: 0,
          notas: ''
        }
      ]
    }));
  };

  const eliminarInsumo = (index) => {
    setFormData(prev => ({
      ...prev,
      detalles: prev.detalles.filter((_, i) => i !== index)
    }));
  };

  const handleInsumoChange = (index, field, value) => {
    setFormData(prev => {
      const nuevosDetalles = [...prev.detalles];
      nuevosDetalles[index] = {
        ...nuevosDetalles[index],
        [field]: value
      };

      // Si cambia el insumo, actualizar unidad_medida y costo_unitario
      if (field === 'insumo') {
        const insumoSeleccionado = insumos.find(p => p.id === parseInt(value));
        if (insumoSeleccionado) {
          nuevosDetalles[index].unidad_medida = insumoSeleccionado.unidad_medida;
          nuevosDetalles[index].costo_unitario = insumoSeleccionado.precio_compra;
        }
      }

      return {
        ...prev,
        detalles: nuevosDetalles
      };
    });
  };

  const calcularCostoTotal = () => {
    const costoInsumos = formData.detalles.reduce((sum, detalle) => {
      return sum + (parseFloat(detalle.cantidad || 0) * parseFloat(detalle.costo_unitario || 0));
    }, 0);
    
    const costoTotal = costoInsumos + 
                      parseFloat(formData.costo_mano_obra || 0) + 
                      parseFloat(formData.costo_indirecto || 0);
    
    const costoUnitario = formData.cantidad_producida > 0 
                         ? costoTotal / parseFloat(formData.cantidad_producida) 
                         : 0;

    return {
      costoInsumos,
      costoTotal,
      costoUnitario
    };
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validaciones
    if (!formData.producto_terminado) {
      alert('Debe seleccionar un producto terminado');
      return;
    }

    if (!formData.nombre.trim()) {
      alert('Debe ingresar un nombre para la receta');
      return;
    }

    if (formData.cantidad_producida <= 0) {
      alert('La cantidad producida debe ser mayor a 0');
      return;
    }

    if (formData.detalles.length === 0) {
      alert('Debe agregar al menos un insumo a la receta');
      return;
    }

    // Validar que todos los insumos estén completos
    const insumosIncompletos = formData.detalles.some(
      detalle => !detalle.insumo || detalle.cantidad <= 0
    );

    if (insumosIncompletos) {
      alert('Todos los insumos deben tener producto y cantidad mayor a 0');
      return;
    }

    // Validar que el producto terminado no esté en los insumos
    const productoEnInsumos = formData.detalles.some(
      detalle => parseInt(detalle.insumo) === parseInt(formData.producto_terminado)
    );

    if (productoEnInsumos) {
      alert('El producto terminado no puede ser usado como insumo en su propia receta');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const dataToSend = {
        ...formData,
        detalles: formData.detalles.map(detalle => ({
          insumo: parseInt(detalle.insumo),
          cantidad: parseFloat(detalle.cantidad),
          unidad_medida: detalle.unidad_medida,
          costo_unitario: parseFloat(detalle.costo_unitario),
          notas: detalle.notas || ''
        }))
      };

      if (isEditing) {
        await produccionService.updateReceta(id, dataToSend);
        alert('Receta actualizada exitosamente');
      } else {
        await produccionService.createReceta(dataToSend);
        alert('Receta creada exitosamente');
      }

      navigate('/produccion/recetas');
    } catch (err) {
      console.error('Error al guardar receta:', err);
      setError(err.response?.data?.error || 'Error al guardar la receta');
    } finally {
      setLoading(false);
    }
  };

  const costos = calcularCostoTotal();

  if (loading && isEditing) {
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
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800">
          {isEditing ? 'Editar Receta' : 'Nueva Receta de Producción'}
        </h1>
        <p className="text-gray-600 mt-1">
          {isEditing ? 'Modifique los datos de la receta' : 'Complete los datos para crear una nueva receta (BOM)'}
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Columna Principal */}
          <div className="lg:col-span-2 space-y-6">
            {/* Información Básica */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">Información Básica</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Producto Terminado *
                  </label>
                  <select
                    name="producto_terminado"
                    value={formData.producto_terminado}
                    onChange={handleChange}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">Seleccione un producto</option>
                    {productos.map(producto => (
                      <option key={producto.id} value={producto.id}>
                        {producto.nombre} ({producto.sku})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Nombre de la Receta *
                  </label>
                  <input
                    type="text"
                    name="nombre"
                    value={formData.nombre}
                    onChange={handleChange}
                    required
                    placeholder="Ej: Receta estándar de..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Cantidad Producida *
                  </label>
                  <input
                    type="number"
                    name="cantidad_producida"
                    value={formData.cantidad_producida}
                    onChange={handleChange}
                    min="0.01"
                    step="0.01"
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Tiempo Estimado (minutos)
                  </label>
                  <input
                    type="number"
                    name="tiempo_estimado"
                    value={formData.tiempo_estimado}
                    onChange={handleChange}
                    min="0"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Costo Mano de Obra (S/)
                  </label>
                  <input
                    type="number"
                    name="costo_mano_obra"
                    value={formData.costo_mano_obra}
                    onChange={handleChange}
                    min="0"
                    step="0.01"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Costos Indirectos / CIF (S/)
                  </label>
                  <input
                    type="number"
                    name="costo_indirecto"
                    value={formData.costo_indirecto}
                    onChange={handleChange}
                    min="0"
                    step="0.01"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                {isEditing && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Versión
                    </label>
                    <input
                      type="number"
                      name="version"
                      value={formData.version}
                      onChange={handleChange}
                      min="1"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                )}

                <div className="flex items-center">
                  <label className="flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      name="is_active"
                      checked={formData.is_active}
                      onChange={handleChange}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">Receta activa</span>
                  </label>
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Notas / Instrucciones
                  </label>
                  <textarea
                    name="notas"
                    value={formData.notas}
                    onChange={handleChange}
                    rows="3"
                    placeholder="Instrucciones adicionales para la producción..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>
            </div>

            {/* Insumos */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold text-gray-800">Insumos de la Receta</h2>
                <button
                  type="button"
                  onClick={agregarInsumo}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Agregar Insumo
                </button>
              </div>

              {formData.detalles.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  No hay insumos agregados. Haga clic en "Agregar Insumo" para comenzar.
                </div>
              ) : (
                <div className="space-y-4">
                  {formData.detalles.map((detalle, index) => (
                    <div key={index} className="border border-gray-200 rounded-lg p-4">
                      <div className="grid grid-cols-12 gap-4">
                        <div className="col-span-12 md:col-span-5">
                          <label className="block text-xs font-medium text-gray-700 mb-1">
                            Insumo *
                          </label>
                          <select
                            value={detalle.insumo}
                            onChange={(e) => handleInsumoChange(index, 'insumo', e.target.value)}
                            required
                            className="w-full px-2 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                          >
                            <option value="">Seleccionar...</option>
                            {insumos.map(insumo => (
                              <option key={insumo.id} value={insumo.id}>
                                {insumo.nombre} ({insumo.sku})
                              </option>
                            ))}
                          </select>
                        </div>

                        <div className="col-span-6 md:col-span-2">
                          <label className="block text-xs font-medium text-gray-700 mb-1">
                            Cantidad *
                          </label>
                          <input
                            type="number"
                            value={detalle.cantidad}
                            onChange={(e) => handleInsumoChange(index, 'cantidad', e.target.value)}
                            min="0.01"
                            step="0.01"
                            required
                            className="w-full px-2 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                          />
                        </div>

                        <div className="col-span-6 md:col-span-2">
                          <label className="block text-xs font-medium text-gray-700 mb-1">
                            Costo Unit.
                          </label>
                          <input
                            type="number"
                            value={detalle.costo_unitario}
                            onChange={(e) => handleInsumoChange(index, 'costo_unitario', e.target.value)}
                            min="0"
                            step="0.01"
                            className="w-full px-2 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                          />
                        </div>

                        <div className="col-span-10 md:col-span-2">
                          <label className="block text-xs font-medium text-gray-700 mb-1">
                            Costo Total
                          </label>
                          <div className="px-2 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg">
                            S/ {(parseFloat(detalle.cantidad || 0) * parseFloat(detalle.costo_unitario || 0)).toFixed(2)}
                          </div>
                        </div>

                        <div className="col-span-2 md:col-span-1 flex items-end">
                          <button
                            type="button"
                            onClick={() => eliminarInsumo(index)}
                            className="w-full px-2 py-2 text-red-600 hover:bg-red-50 border border-red-300 rounded-lg"
                            title="Eliminar"
                          >
                            <svg className="w-5 h-5 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>

                        <div className="col-span-12">
                          <input
                            type="text"
                            value={detalle.notas}
                            onChange={(e) => handleInsumoChange(index, 'notas', e.target.value)}
                            placeholder="Notas sobre este insumo..."
                            className="w-full px-2 py-1 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Sidebar - Resumen */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-sm p-6 sticky top-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Resumen de Costos</h3>
              
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Costo Insumos:</span>
                  <span className="font-medium">S/ {costos.costoInsumos.toFixed(2)}</span>
                </div>

                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Mano de Obra:</span>
                  <span className="font-medium">S/ {parseFloat(formData.costo_mano_obra || 0).toFixed(2)}</span>
                </div>

                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Costos Indirectos:</span>
                  <span className="font-medium">S/ {parseFloat(formData.costo_indirecto || 0).toFixed(2)}</span>
                </div>

                <div className="border-t pt-3">
                  <div className="flex justify-between text-base font-semibold">
                    <span>Costo Total:</span>
                    <span className="text-blue-600">S/ {costos.costoTotal.toFixed(2)}</span>
                  </div>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <div className="text-xs text-gray-600 mb-1">Costo Unitario</div>
                  <div className="text-2xl font-bold text-blue-600">
                    S/ {costos.costoUnitario.toFixed(2)}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Por {formData.cantidad_producida} unidad(es)
                  </div>
                </div>

                <div className="pt-3 space-y-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Guardando...' : (isEditing ? 'Actualizar Receta' : 'Crear Receta')}
                  </button>

                  <button
                    type="button"
                    onClick={() => navigate('/produccion/recetas')}
                    className="w-full bg-gray-200 hover:bg-gray-300 text-gray-700 py-3 rounded-lg font-medium"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};

export default RecetaForm;
