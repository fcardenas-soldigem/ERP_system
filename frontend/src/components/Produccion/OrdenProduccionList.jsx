import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import produccionService from '../../services/produccion.service';

const OrdenProduccionList = () => {
  const navigate = useNavigate();
  const [ordenes, setOrdenes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterEstado, setFilterEstado] = useState('all');

  useEffect(() => {
    cargarOrdenes();
  }, [filterEstado]);

  const cargarOrdenes = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = {};
      if (filterEstado !== 'all') {
        params.estado = filterEstado;
      }
      if (searchTerm) {
        params.search = searchTerm;
      }

      const response = await produccionService.getOrdenes(params);
      setOrdenes(response.data);
    } catch (err) {
      console.error('Error al cargar órdenes:', err);
      setError('Error al cargar las órdenes de producción');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    cargarOrdenes();
  };

  const getEstadoBadge = (estado, retrasada) => {
    const badges = {
      pendiente: 'bg-yellow-100 text-yellow-800',
      en_proceso: 'bg-blue-100 text-blue-800',
      finalizada: 'bg-green-100 text-green-800',
      cancelada: 'bg-gray-100 text-gray-800'
    };

    const textos = {
      pendiente: 'Pendiente',
      en_proceso: 'En Proceso',
      finalizada: 'Finalizada',
      cancelada: 'Cancelada'
    };

    return (
      <div className="flex items-center gap-2">
        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${badges[estado]}`}>
          {textos[estado]}
        </span>
        {retrasada && estado !== 'finalizada' && estado !== 'cancelada' && (
          <span className="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
            Retrasada
          </span>
        )}
      </div>
    );
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

  return (
    <div className="container mx-auto p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Órdenes de Producción</h1>
          <p className="text-gray-600 mt-1">Gestione las órdenes de producción</p>
        </div>
        <Link
          to="/produccion/ordenes/nueva"
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Nueva Orden
        </Link>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <form onSubmit={handleSearch} className="flex-1">
            <div className="relative">
              <input
                type="text"
                placeholder="Buscar por número, producto..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              <svg
                className="absolute left-3 top-2.5 h-5 w-5 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </form>

          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => setFilterEstado('all')}
              className={`px-4 py-2 rounded-lg ${filterEstado === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              Todas
            </button>
            <button
              onClick={() => setFilterEstado('pendiente')}
              className={`px-4 py-2 rounded-lg ${filterEstado === 'pendiente' ? 'bg-yellow-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              Pendientes
            </button>
            <button
              onClick={() => setFilterEstado('en_proceso')}
              className={`px-4 py-2 rounded-lg ${filterEstado === 'en_proceso' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              En Proceso
            </button>
            <button
              onClick={() => setFilterEstado('finalizada')}
              className={`px-4 py-2 rounded-lg ${filterEstado === 'finalizada' ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              Finalizadas
            </button>
            <button
              onClick={() => setFilterEstado('cancelada')}
              className={`px-4 py-2 rounded-lg ${filterEstado === 'cancelada' ? 'bg-gray-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              Canceladas
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {/* Lista */}
      {ordenes.length === 0 ? (
        <div className="bg-white rounded-lg shadow-sm p-12 text-center">
          <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No hay órdenes</h3>
          <p className="text-gray-600 mb-4">Cree su primera orden de producción</p>
          <Link
            to="/produccion/ordenes/nueva"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Crear Orden
          </Link>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Orden</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Producto</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Planificado</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Producido</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha Prog.</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Eficiencia</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Acciones</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {ordenes.map((orden) => (
                <tr key={orden.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">OP-{orden.numero}</div>
                    <div className="text-xs text-gray-500">{orden.receta_nombre}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{orden.producto_nombre}</div>
                    <div className="text-xs text-gray-500">{orden.producto_sku}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {orden.cantidad_planificada}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {orden.cantidad_producida || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {new Date(orden.fecha_programada).toLocaleDateString('es-PE')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {getEstadoBadge(orden.estado, orden.esta_retrasada)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {orden.estado === 'finalizada' ? (
                      <span className={`font-medium ${orden.eficiencia_produccion >= 95 ? 'text-green-600' : orden.eficiencia_produccion >= 80 ? 'text-yellow-600' : 'text-red-600'}`}>
                        {parseFloat(orden.eficiencia_produccion).toFixed(1)}%
                      </span>
                    ) : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex justify-end gap-2">
                      {orden.estado === 'pendiente' && (
                        <button
                          onClick={() => navigate(`/produccion/ordenes/${orden.id}/ejecutar`)}
                          className="text-blue-600 hover:text-blue-900"
                          title="Ejecutar"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </button>
                      )}
                      {orden.estado === 'en_proceso' && (
                        <button
                          onClick={() => navigate(`/produccion/ordenes/${orden.id}/ejecutar`)}
                          className="text-green-600 hover:text-green-900"
                          title="Continuar"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                      )}
                      <button
                        onClick={() => navigate(`/produccion/ordenes/${orden.id}`)}
                        className="text-blue-600 hover:text-blue-900"
                        title="Ver detalles"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {ordenes.length > 0 && (
        <div className="mt-4 text-sm text-gray-600">
          Mostrando {ordenes.length} orden{ordenes.length !== 1 ? 'es' : ''}
        </div>
      )}
    </div>
  );
};

export default OrdenProduccionList;
