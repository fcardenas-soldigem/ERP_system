import React, { useState, useEffect } from 'react';
import { 
  Card, 
  CardHeader, 
  CardContent, 
  CardTitle 
} from '../common/Card';
import { Button } from '../common/Button';
import axios from 'axios';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

const Kardex = () => {
  const [movimientos, setMovimientos] = useState([]);
  const [productos, setProductos] = useState([]);
  const [almacenes, setAlmacenes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filtros, setFiltros] = useState({
    producto_id: '',
    almacen_id: '',
    fecha_inicio: '',
    fecha_fin: '',
    tipo_movimiento: '',
    tipo_documento: ''
  });
  const [resumen, setResumen] = useState(null);

  // Opciones para filtros
  const tiposMovimiento = [
    { value: '', label: 'Todos los movimientos' },
    { value: 'entrada', label: 'Entradas' },
    { value: 'salida', label: 'Salidas' },
    { value: 'ajuste_entrada', label: 'Ajuste - Entrada' },
    { value: 'ajuste_salida', label: 'Ajuste - Salida' },
    { value: 'devolucion_compra', label: 'Devolución Compra' },
    { value: 'devolucion_venta', label: 'Devolución Venta' },
    { value: 'transferencia_entrada', label: 'Transferencia - Entrada' },
    { value: 'transferencia_salida', label: 'Transferencia - Salida' }
  ];

  const tiposDocumento = [
    { value: '', label: 'Todos los documentos' },
    { value: 'compra', label: 'Compra' },
    { value: 'venta', label: 'Venta' },
    { value: 'ajuste', label: 'Ajuste de Inventario' },
    { value: 'devolucion_compra', label: 'Devolución de Compra' },
    { value: 'devolucion_venta', label: 'Devolución de Venta' },
    { value: 'transferencia', label: 'Transferencia' },
    { value: 'inventario_inicial', label: 'Inventario Inicial' }
  ];

  useEffect(() => {
    cargarDatosIniciales();
  }, []);

  const cargarDatosIniciales = async () => {
    try {
      const [productosRes, almacenesRes] = await Promise.all([
        axios.get('/api/inventario/productos/'),
        axios.get('/api/inventario/almacenes/')
      ]);
      
      setProductos(productosRes.data.results || productosRes.data);
      setAlmacenes(almacenesRes.data.results || almacenesRes.data);
    } catch (error) {
      console.error('Error cargando datos iniciales:', error);
    }
  };

  const cargarKardex = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      
      Object.keys(filtros).forEach(key => {
        if (filtros[key]) {
          params.append(key, filtros[key]);
        }
      });

      const response = await axios.get(`/api/inventario/kardex/?${params.toString()}`);
      setMovimientos(response.data.results || response.data);
    } catch (error) {
      console.error('Error cargando kardex:', error);
    } finally {
      setLoading(false);
    }
  };

  const cargarResumen = async () => {
    try {
      const response = await axios.get('/api/inventario/kardex/resumen_kardex/');
      setResumen(response.data);
    } catch (error) {
      console.error('Error cargando resumen:', error);
    }
  };

  const exportarExcel = async () => {
    try {
      const params = new URLSearchParams();
      
      Object.keys(filtros).forEach(key => {
        if (filtros[key]) {
          params.append(key, filtros[key]);
        }
      });

      const response = await axios.get(
        `/api/inventario/kardex/exportar_excel/?${params.toString()}`,
        { responseType: 'blob' }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `kardex_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Error exportando kardex:', error);
    }
  };

  const handleFiltroChange = (campo, valor) => {
    setFiltros(prev => ({
      ...prev,
      [campo]: valor
    }));
  };

  const limpiarFiltros = () => {
    setFiltros({
      producto_id: '',
      almacen_id: '',
      fecha_inicio: '',
      fecha_fin: '',
      tipo_movimiento: '',
      tipo_documento: ''
    });
    setMovimientos([]);
  };

  const formatearMoneda = (valor) => {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN'
    }).format(valor);
  };

  const formatearCantidad = (cantidad) => {
    return parseFloat(cantidad).toLocaleString('es-PE', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 4
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Kardex de Inventario</h1>
          <p className="text-gray-600">Registro cronológico de movimientos de inventario con método FIFO</p>
        </div>
        <div className="flex space-x-2">
          <Button
            onClick={cargarResumen}
            variant="outline"
            className="flex items-center space-x-2"
          >
            <span>📊</span>
            <span>Ver Resumen</span>
          </Button>
          <Button
            onClick={exportarExcel}
            disabled={movimientos.length === 0}
            className="flex items-center space-x-2"
          >
            <span>📥</span>
            <span>Exportar Excel</span>
          </Button>
        </div>
      </div>

      {/* Filtros */}
      <Card>
        <CardHeader>
          <CardTitle>Filtros de Búsqueda</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Producto
              </label>
              <select
                value={filtros.producto_id}
                onChange={(e) => handleFiltroChange('producto_id', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2"
              >
                <option value="">Todos los productos</option>
                {productos.map(producto => (
                  <option key={producto.id} value={producto.id}>
                    {producto.sku} - {producto.nombre}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Almacén
              </label>
              <select
                value={filtros.almacen_id}
                onChange={(e) => handleFiltroChange('almacen_id', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2"
              >
                <option value="">Todos los almacenes</option>
                {almacenes.map(almacen => (
                  <option key={almacen.id} value={almacen.id}>
                    {almacen.nombre}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tipo Movimiento
              </label>
              <select
                value={filtros.tipo_movimiento}
                onChange={(e) => handleFiltroChange('tipo_movimiento', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2"
              >
                {tiposMovimiento.map(tipo => (
                  <option key={tipo.value} value={tipo.value}>
                    {tipo.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tipo Documento
              </label>
              <select
                value={filtros.tipo_documento}
                onChange={(e) => handleFiltroChange('tipo_documento', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2"
              >
                {tiposDocumento.map(tipo => (
                  <option key={tipo.value} value={tipo.value}>
                    {tipo.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Fecha Inicio
              </label>
              <input
                type="date"
                value={filtros.fecha_inicio}
                onChange={(e) => handleFiltroChange('fecha_inicio', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Fecha Fin
              </label>
              <input
                type="date"
                value={filtros.fecha_fin}
                onChange={(e) => handleFiltroChange('fecha_fin', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2"
              />
            </div>
          </div>

          <div className="flex justify-end space-x-2 mt-4">
            <Button
              onClick={limpiarFiltros}
              variant="outline"
            >
              Limpiar Filtros
            </Button>
            <Button
              onClick={cargarKardex}
              disabled={loading}
            >
              {loading ? 'Buscando...' : 'Buscar'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Tabla de Movimientos */}
      {movimientos.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Movimientos de Inventario</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Fecha
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Producto
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Almacén
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Movimiento
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Documento
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Entrada
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Salida
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Saldo
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Costo Unit.
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Costo Total
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {movimientos.map((movimiento) => (
                    <tr key={movimiento.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {format(new Date(movimiento.fecha), 'dd/MM/yyyy HH:mm', { locale: es })}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {movimiento.producto_sku}
                        </div>
                        <div className="text-sm text-gray-500">
                          {movimiento.producto_nombre}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {movimiento.almacen_nombre}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          movimiento.tipo_movimiento.includes('entrada') 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {movimiento.tipo_movimiento_display}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {movimiento.tipo_documento_display}
                        </div>
                        <div className="text-sm text-gray-500">
                          {movimiento.numero_documento}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                        {movimiento.cantidad_entrada > 0 ? formatearCantidad(movimiento.cantidad_entrada) : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                        {movimiento.cantidad_salida > 0 ? formatearCantidad(movimiento.cantidad_salida) : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium text-gray-900">
                        {formatearCantidad(movimiento.cantidad_saldo)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                        {formatearMoneda(movimiento.costo_unitario)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                        {formatearMoneda(movimiento.costo_saldo)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Resumen */}
      {resumen && (
        <Card>
          <CardHeader>
            <CardTitle>Resumen por Producto y Almacén</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Producto
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Almacén
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Stock Actual
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Costo Promedio
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Valor Total
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Total Entradas
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Total Salidas
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {resumen.map((item, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {item.producto.sku}
                        </div>
                        <div className="text-sm text-gray-500">
                          {item.producto.nombre}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {item.almacen.nombre}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                        {formatearCantidad(item.stock_actual)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                        {formatearMoneda(item.costo_promedio)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium text-gray-900">
                        {formatearMoneda(item.costo_total)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                        {formatearCantidad(item.total_entradas)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                        {formatearCantidad(item.total_salidas)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Mensaje cuando no hay datos */}
      {!loading && movimientos.length === 0 && (
        <Card>
          <CardContent>
            <div className="text-center py-8">
              <div className="text-gray-400 text-6xl mb-4">📋</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No hay movimientos
              </h3>
              <p className="text-gray-500">
                Selecciona los filtros y presiona "Buscar" para ver los movimientos de inventario
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Kardex; 