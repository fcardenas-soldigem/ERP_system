import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import produccionService from '../../services/produccion.service';

const DashboardProduccion = () => {
  const navigate = useNavigate();
  const [metricas, setMetricas] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [periodo, setPeriodo] = useState('7'); // Solo vista semanal por defecto

  useEffect(() => {
    cargarMetricas();
    // Recargar cada 30 segundos
    const interval = setInterval(cargarMetricas, 30000);
    return () => clearInterval(interval);
  }, [periodo]);

  const cargarMetricas = async () => {
    try {
      setLoading(true);
      setError(null);

      const fechaHasta = new Date();
      const fechaDesde = new Date();
      fechaDesde.setDate(fechaDesde.getDate() - parseInt(periodo));

      const params = {
        fecha_desde: fechaDesde.toISOString().split('T')[0],
        fecha_hasta: fechaHasta.toISOString().split('T')[0]
      };

      const response = await produccionService.getDashboard(params);
      setMetricas(response.data);
    } catch (err) {
      console.error('Error al cargar métricas:', err);
      setError('Error al cargar las métricas');
    } finally {
      setLoading(false);
    }
  };

  if (loading && !metricas) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  if (error || !metricas) {
    return (
      <div className="container mx-auto p-6">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error || 'Error al cargar métricas'}
        </div>
      </div>
    );
  }

  const { metricas_operativas, ordenes_hoy } = metricas;

  // Calcular alertas
  const alertas = [];
  
  // Alerta de órdenes retrasadas
  if (metricas_operativas.ordenes_activas.retrasadas > 0) {
    alertas.push({
      tipo: 'error',
      icono: '⚠️',
      mensaje: `${metricas_operativas.ordenes_activas.retrasadas} órdenes retrasadas`,
      accion: () => navigate('/produccion/ordenes?retrasadas=true')
    });
  }

  // Alerta de merma elevada (>10%)
  if (metricas_operativas.mermas.porcentaje_merma > 10) {
    alertas.push({
      tipo: 'warning',
      icono: '📉',
      mensaje: `Merma elevada: ${metricas_operativas.mermas.porcentaje_merma.toFixed(1)}%`,
      accion: null
    });
  }

  // Alerta de cumplimiento bajo (<80%)
  if (metricas_operativas.cumplimiento.porcentaje_cumplimiento < 80 && metricas_operativas.cumplimiento.ordenes_finalizadas > 0) {
    alertas.push({
      tipo: 'warning',
      icono: '📊',
      mensaje: `Cumplimiento bajo: ${metricas_operativas.cumplimiento.porcentaje_cumplimiento.toFixed(0)}%`,
      accion: null
    });
  }

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      {/* Header Simplificado */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Control de Producción</h1>
          <p className="text-gray-600 mt-1">Vista en tiempo real de tu planta</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => navigate('/produccion/ordenes/nueva')}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium"
          >
            + Nueva Orden
          </button>
        </div>
      </div>

      {/* ALERTAS PROMINENTES */}
      {alertas.length > 0 && (
        <div className="mb-6 space-y-2">
          {alertas.map((alerta, idx) => (
            <div
              key={idx}
              className={`rounded-lg p-4 flex items-center justify-between cursor-pointer ${
                alerta.tipo === 'error' ? 'bg-red-50 border-2 border-red-500' :
                'bg-yellow-50 border-2 border-yellow-500'
              }`}
              onClick={alerta.accion}
            >
              <div className="flex items-center gap-3">
                <span className="text-3xl">{alerta.icono}</span>
                <span className={`text-lg font-semibold ${
                  alerta.tipo === 'error' ? 'text-red-800' : 'text-yellow-800'
                }`}>
                  {alerta.mensaje}
                </span>
              </div>
              {alerta.accion && (
                <span className="text-sm text-gray-600">Clic para ver →</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 6 KPIs PRINCIPALES - Vista Control de Planta */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {/* KPI 1: Producción Hoy */}
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-xl shadow-lg p-6">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-medium opacity-90">PRODUCCIÓN HOY</div>
            <svg className="w-8 h-8 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          <div className="text-5xl font-bold mb-2">{ordenes_hoy.length}</div>
          <div className="text-sm opacity-90">órdenes programadas</div>
        </div>

        {/* KPI 2: Órdenes Activas */}
        <div className="bg-gradient-to-br from-purple-500 to-purple-600 text-white rounded-xl shadow-lg p-6">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-medium opacity-90">EN PROCESO</div>
            <svg className="w-8 h-8 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div className="text-5xl font-bold mb-2">
            {metricas_operativas.ordenes_activas.en_proceso}
          </div>
          <div className="text-sm opacity-90">órdenes activas ahora</div>
        </div>

        {/* KPI 3: Cumplimiento */}
        <div className="bg-gradient-to-br from-green-500 to-green-600 text-white rounded-xl shadow-lg p-6">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-medium opacity-90">CUMPLIMIENTO</div>
            <svg className="w-8 h-8 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="text-5xl font-bold mb-2">
            {metricas_operativas.cumplimiento.porcentaje_cumplimiento.toFixed(0)}%
          </div>
          <div className="text-sm opacity-90">órdenes a tiempo (7 días)</div>
        </div>

        {/* KPI 4: Pendientes */}
        <div className="bg-gradient-to-br from-yellow-500 to-yellow-600 text-white rounded-xl shadow-lg p-6">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-medium opacity-90">PENDIENTES</div>
            <svg className="w-8 h-8 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="text-5xl font-bold mb-2">
            {metricas_operativas.ordenes_activas.pendientes}
          </div>
          <div className="text-sm opacity-90">por iniciar</div>
        </div>

        {/* KPI 5: Eficiencia */}
        <div className="bg-gradient-to-br from-indigo-500 to-indigo-600 text-white rounded-xl shadow-lg p-6">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-medium opacity-90">EFICIENCIA</div>
            <svg className="w-8 h-8 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          </div>
          <div className="text-5xl font-bold mb-2">
            {metricas.metricas_eficiencia.eficiencia_produccion_promedio.toFixed(0)}%
          </div>
          <div className="text-sm opacity-90">promedio semanal</div>
        </div>

        {/* KPI 6: Merma */}
        <div className={`bg-gradient-to-br ${
          metricas_operativas.mermas.porcentaje_merma > 10 ? 'from-red-500 to-red-600' : 'from-teal-500 to-teal-600'
        } text-white rounded-xl shadow-lg p-6`}>
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-medium opacity-90">MERMA</div>
            <svg className="w-8 h-8 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="text-5xl font-bold mb-2">
            {metricas_operativas.mermas.porcentaje_merma.toFixed(1)}%
          </div>
          <div className="text-sm opacity-90">
            S/ {metricas_operativas.mermas.costo_merma.toFixed(0)} en costos
          </div>
        </div>
      </div>

      {/* GRÁFICO SIMPLE: Producción Planificada vs Real */}
      <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Producción: Plan vs Real (Últimos 7 días)</h3>
        
        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-600">Planificado</span>
              <span className="font-bold text-gray-900">
                {metricas_operativas.produccion.total_planificado.toFixed(0)} unidades
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-8">
              <div
                className="bg-blue-400 h-8 rounded-full flex items-center justify-end pr-3 text-white text-sm font-medium"
                style={{ width: '100%' }}
              >
                100%
              </div>
            </div>
          </div>

          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-600">Producido</span>
              <span className="font-bold text-blue-600">
                {metricas_operativas.produccion.total_producido.toFixed(0)} unidades
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-8">
              <div
                className={`h-8 rounded-full flex items-center justify-end pr-3 text-white text-sm font-medium ${
                  metricas_operativas.produccion.diferencia >= 0 ? 'bg-green-500' : 'bg-red-500'
                }`}
                style={{
                  width: `${Math.min(
                    (metricas_operativas.produccion.total_producido / 
                     Math.max(metricas_operativas.produccion.total_planificado, 1)) * 100,
                    100
                  )}%`
                }}
              >
                {((metricas_operativas.produccion.total_producido / 
                   Math.max(metricas_operativas.produccion.total_planificado, 1)) * 100).toFixed(0)}%
              </div>
            </div>
          </div>

          <div className="pt-2 border-t">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Diferencia:</span>
              <span className={`text-xl font-bold ${
                metricas_operativas.produccion.diferencia >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {metricas_operativas.produccion.diferencia > 0 ? '+' : ''}
                {metricas_operativas.produccion.diferencia.toFixed(0)} unidades
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Órdenes de Hoy - Simple */}
      {ordenes_hoy.length > 0 && (
        <div className="bg-white rounded-xl shadow-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-800">Órdenes Programadas Hoy</h3>
            <Link to="/produccion/ordenes" className="text-blue-600 hover:text-blue-800 text-sm font-medium">
              Ver todas →
            </Link>
          </div>
          
          <div className="space-y-3">
            {ordenes_hoy.slice(0, 5).map((orden) => (
              <div
                key={orden.id}
                onClick={() => navigate(`/produccion/ordenes/${orden.id}`)}
                className="flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 rounded-lg cursor-pointer transition-colors"
              >
                <div className="flex items-center gap-4 flex-1">
                  <div className={`w-3 h-3 rounded-full ${
                    orden.estado === 'pendiente' ? 'bg-yellow-500' :
                    orden.estado === 'en_proceso' ? 'bg-blue-500 animate-pulse' :
                    orden.estado === 'finalizada' ? 'bg-green-500' : 'bg-gray-500'
                  }`}></div>
                  
                  <div className="flex-1">
                    <div className="font-medium text-gray-900">OP-{orden.numero}</div>
                    <div className="text-sm text-gray-500">{orden.receta__producto_terminado__nombre}</div>
                  </div>

                  <div className="text-right">
                    <div className="text-sm font-medium text-gray-900">
                      {orden.cantidad_producida || 0} / {orden.cantidad_planificada}
                    </div>
                    <div className="text-xs text-gray-500">
                      {orden.estado === 'pendiente' ? 'Por iniciar' :
                       orden.estado === 'en_proceso' ? 'En proceso' :
                       orden.estado === 'finalizada' ? 'Finalizada' : 'Cancelada'}
                    </div>
                  </div>

                  {orden.estado === 'en_proceso' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/produccion/ordenes/${orden.id}/ejecutar`);
                      }}
                      className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
                    >
                      Continuar →
                    </button>
                  )}
                  
                  {orden.estado === 'pendiente' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/produccion/ordenes/${orden.id}/ejecutar`);
                      }}
                      className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
                    >
                      Iniciar →
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {ordenes_hoy.length > 5 && (
            <div className="mt-4 text-center">
              <Link
                to="/produccion/ordenes"
                className="text-blue-600 hover:text-blue-800 text-sm font-medium"
              >
                Ver {ordenes_hoy.length - 5} órdenes más →
              </Link>
            </div>
          )}
        </div>
      )}

      {/* Sin órdenes hoy */}
      {ordenes_hoy.length === 0 && (
        <div className="bg-white rounded-xl shadow-lg p-12 text-center">
          <svg className="mx-auto h-16 w-16 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No hay órdenes para hoy</h3>
          <p className="text-gray-600 mb-4">Comienza creando una nueva orden de producción</p>
          <button
            onClick={() => navigate('/produccion/ordenes/nueva')}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium inline-flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Nueva Orden de Producción
          </button>
        </div>
      )}
    </div>
  );
};

export default DashboardProduccion;
