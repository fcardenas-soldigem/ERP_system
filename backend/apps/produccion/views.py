from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Q, Sum, Count, Avg, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import RecetaProducto, RecetaDetalle, OrdenProduccion, ConsumoReal
from .serializers import (
    RecetaProductoSerializer,
    RecetaProductoListSerializer,
    RecetaProductoCreateSerializer,
    OrdenProduccionSerializer,
    OrdenProduccionListSerializer,
    OrdenProduccionCreateSerializer,
    FinalizarOrdenSerializer,
    ActualizarConsumoSerializer,
    ConsumoRealSerializer
)
from .services.produccion_service import ProduccionService
from django.core.exceptions import ValidationError as DjangoValidationError


class RecetaProductoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar recetas de producción (BOM).
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrar recetas por empresa del usuario"""
        empresa = self.request.user.perfil.empresa
        queryset = RecetaProducto.objects.filter(empresa=empresa).select_related(
            'producto_terminado'
        ).prefetch_related('detalles__insumo')
        
        # Filtros opcionales
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        producto_id = self.request.query_params.get('producto_id', None)
        if producto_id:
            queryset = queryset.filter(producto_terminado_id=producto_id)
        
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(producto_terminado__nombre__icontains=search) |
                Q(producto_terminado__sku__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        """Seleccionar serializer según la acción"""
        if self.action == 'list':
            return RecetaProductoListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return RecetaProductoCreateSerializer
        return RecetaProductoSerializer
    
    @action(detail=True, methods=['post'])
    def duplicar_receta(self, request, pk=None):
        """Duplica una receta con una nueva versión"""
        receta_original = self.get_object()
        
        # Crear nueva receta
        nueva_receta = RecetaProducto.objects.create(
            empresa=receta_original.empresa,
            producto_terminado=receta_original.producto_terminado,
            nombre=f"{receta_original.nombre} (Copia)",
            cantidad_producida=receta_original.cantidad_producida,
            tiempo_estimado=receta_original.tiempo_estimado,
            costo_mano_obra=receta_original.costo_mano_obra,
            costo_indirecto=receta_original.costo_indirecto,
            version=receta_original.version + 1,
            notas=receta_original.notas
        )
        
        # Copiar detalles
        for detalle in receta_original.detalles.all():
            RecetaDetalle.objects.create(
                receta=nueva_receta,
                insumo=detalle.insumo,
                cantidad=detalle.cantidad,
                unidad_medida=detalle.unidad_medida,
                costo_unitario=detalle.costo_unitario,
                notas=detalle.notas
            )
        
        serializer = RecetaProductoSerializer(nueva_receta)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def calcular_costo_teorico(self, request, pk=None):
        """Calcula el costo teórico de la receta"""
        receta = self.get_object()
        costos = receta.calcular_costo_teorico()
        return Response(costos)
    
    @action(detail=False, methods=['post'])
    def validar_stock(self, request):
        """Valida si hay stock suficiente para producir una cantidad"""
        receta_id = request.data.get('receta_id')
        cantidad = request.data.get('cantidad')
        almacen_insumos_id = request.data.get('almacen_insumos_id')
        
        if not all([receta_id, cantidad, almacen_insumos_id]):
            return Response(
                {'error': 'Se requieren receta_id, cantidad y almacen_insumos_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            empresa = request.user.perfil.empresa
            resultado = ProduccionService.validar_stock_receta(
                empresa, receta_id, Decimal(str(cantidad)), almacen_insumos_id
            )
            return Response(resultado)
        except DjangoValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OrdenProduccionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar órdenes de producción.
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrar órdenes por empresa del usuario"""
        empresa = self.request.user.perfil.empresa
        queryset = OrdenProduccion.objects.filter(empresa=empresa).select_related(
            'receta__producto_terminado',
            'almacen_insumos',
            'almacen_destino',
            'responsable',
            'created_by'
        ).prefetch_related('consumos__insumo')
        
        # Filtros opcionales
        estado = self.request.query_params.get('estado', None)
        if estado:
            queryset = queryset.filter(estado=estado)
        
        fecha_desde = self.request.query_params.get('fecha_desde', None)
        if fecha_desde:
            queryset = queryset.filter(fecha_programada__gte=fecha_desde)
        
        fecha_hasta = self.request.query_params.get('fecha_hasta', None)
        if fecha_hasta:
            queryset = queryset.filter(fecha_programada__lte=fecha_hasta)
        
        producto_id = self.request.query_params.get('producto_id', None)
        if producto_id:
            queryset = queryset.filter(receta__producto_terminado_id=producto_id)
        
        almacen_id = self.request.query_params.get('almacen_id', None)
        if almacen_id:
            queryset = queryset.filter(
                Q(almacen_insumos_id=almacen_id) |
                Q(almacen_destino_id=almacen_id)
            )
        
        retrasadas = self.request.query_params.get('retrasadas', None)
        if retrasadas and retrasadas.lower() == 'true':
            queryset = queryset.filter(
                fecha_programada__lt=timezone.now().date()
            ).exclude(estado__in=['finalizada', 'cancelada'])
        
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(numero__icontains=search) |
                Q(receta__nombre__icontains=search) |
                Q(receta__producto_terminado__nombre__icontains=search) |
                Q(receta__producto_terminado__sku__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        """Seleccionar serializer según la acción"""
        if self.action == 'list':
            return OrdenProduccionListSerializer
        elif self.action == 'create':
            return OrdenProduccionCreateSerializer
        return OrdenProduccionSerializer
    
    @action(detail=True, methods=['post'])
    def iniciar(self, request, pk=None):
        """Inicia una orden de producción"""
        orden = self.get_object()
        
        try:
            orden_actualizada = ProduccionService.iniciar_orden(
                orden.id,
                usuario=request.user
            )
            serializer = OrdenProduccionSerializer(orden_actualizada)
            return Response(serializer.data)
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def finalizar(self, request, pk=None):
        """Finaliza una orden de producción"""
        orden = self.get_object()
        serializer = FinalizarOrdenSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                orden_finalizada = ProduccionService.finalizar_orden(
                    orden.id,
                    cantidad_producida=serializer.validated_data['cantidad_producida'],
                    costo_mano_obra_real=serializer.validated_data.get('costo_mano_obra_real', 0),
                    costo_indirecto_real=serializer.validated_data.get('costo_indirecto_real', 0),
                    observaciones=serializer.validated_data.get('observaciones', '')
                )
                response_serializer = OrdenProduccionSerializer(orden_finalizada)
                return Response(response_serializer.data)
            except DjangoValidationError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """Cancela una orden de producción"""
        orden = self.get_object()
        motivo = request.data.get('motivo', '')
        
        try:
            orden_cancelada = ProduccionService.cancelar_orden(orden.id, motivo)
            serializer = OrdenProduccionSerializer(orden_cancelada)
            return Response(serializer.data)
        except DjangoValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def actualizar_consumo(self, request, pk=None):
        """Actualiza el consumo real de un insumo"""
        orden = self.get_object()
        serializer = ActualizarConsumoSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                consumo = ProduccionService.registrar_consumo_real(
                    orden.id,
                    insumo_id=serializer.validated_data['insumo_id'],
                    cantidad_real=serializer.validated_data['cantidad_real'],
                    merma=serializer.validated_data.get('merma', 0),
                    notas=serializer.validated_data.get('notas', '')
                )
                response_serializer = ConsumoRealSerializer(consumo)
                return Response(response_serializer.data)
            except DjangoValidationError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DashboardProduccionView(APIView):
    """
    Vista para el dashboard de producción con métricas operativas y de eficiencia.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        empresa = request.user.perfil.empresa
        
        # Parámetros de fecha (por defecto último mes)
        fecha_hasta = timezone.now().date()
        fecha_desde = fecha_hasta - timedelta(days=30)
        
        fecha_desde_param = request.query_params.get('fecha_desde')
        fecha_hasta_param = request.query_params.get('fecha_hasta')
        
        if fecha_desde_param:
            from datetime import datetime
            fecha_desde = datetime.strptime(fecha_desde_param, '%Y-%m-%d').date()
        
        if fecha_hasta_param:
            from datetime import datetime
            fecha_hasta = datetime.strptime(fecha_hasta_param, '%Y-%m-%d').date()
        
        # 1. MÉTRICAS OPERATIVAS
        
        # Órdenes activas
        ordenes_pendientes = OrdenProduccion.objects.filter(
            empresa=empresa,
            estado='pendiente'
        ).count()
        
        ordenes_en_proceso = OrdenProduccion.objects.filter(
            empresa=empresa,
            estado='en_proceso'
        ).count()
        
        ordenes_retrasadas = OrdenProduccion.objects.filter(
            empresa=empresa,
            fecha_programada__lt=fecha_hasta
        ).exclude(estado__in=['finalizada', 'cancelada']).count()
        
        # Órdenes del período
        ordenes_periodo = OrdenProduccion.objects.filter(
            empresa=empresa,
            created_at__date__gte=fecha_desde,
            created_at__date__lte=fecha_hasta
        )
        
        ordenes_finalizadas = ordenes_periodo.filter(estado='finalizada').count()
        ordenes_totales = ordenes_periodo.count()
        
        # Cumplimiento
        ordenes_a_tiempo = ordenes_periodo.filter(
            estado='finalizada',
            fecha_fin__date__lte=F('fecha_programada')
        ).count()
        
        porcentaje_cumplimiento = (
            (ordenes_a_tiempo / ordenes_finalizadas * 100)
            if ordenes_finalizadas > 0 else 0
        )
        
        # Producción planificada vs real
        stats_produccion = ordenes_periodo.filter(estado='finalizada').aggregate(
            total_planificado=Sum('cantidad_planificada'),
            total_producido=Sum('cantidad_producida')
        )
        
        # Mermas del período
        consumos_periodo = ConsumoReal.objects.filter(
            orden_produccion__empresa=empresa,
            orden_produccion__estado='finalizada',
            orden_produccion__fecha_fin__date__gte=fecha_desde,
            orden_produccion__fecha_fin__date__lte=fecha_hasta
        )
        
        stats_mermas = consumos_periodo.aggregate(
            total_merma=Sum('merma'),
            costo_merma=Sum(F('merma') * F('costo_unitario')),
            total_consumido=Sum('cantidad_real')
        )
        
        porcentaje_merma = (
            (stats_mermas['total_merma'] / stats_mermas['total_consumido'] * 100)
            if stats_mermas['total_consumido'] and stats_mermas['total_consumido'] > 0 else 0
        )
        
        # Top 5 productos producidos
        top_productos = ordenes_periodo.filter(estado='finalizada').values(
            'receta__producto_terminado__id',
            'receta__producto_terminado__nombre',
            'receta__producto_terminado__sku'
        ).annotate(
            total_producido=Sum('cantidad_producida'),
            cantidad_ordenes=Count('id')
        ).order_by('-total_producido')[:5]
        
        # 2. MÉTRICAS DE EFICIENCIA
        
        ordenes_finalizadas_qs = ordenes_periodo.filter(estado='finalizada')
        
        # Eficiencia de producción promedio
        eficiencia_produccion = ordenes_finalizadas_qs.aggregate(
            promedio=Avg(
                F('cantidad_producida') * 100.0 / F('cantidad_planificada')
            )
        )['promedio'] or 0
        
        # Variación de consumo por insumo (Top 10 con mayor variación)
        variaciones_consumo = consumos_periodo.values(
            'insumo__id',
            'insumo__nombre',
            'insumo__sku'
        ).annotate(
            total_teorico=Sum('cantidad_teorica'),
            total_real=Sum('cantidad_real')
        ).annotate(
            variacion=((F('total_real') - F('total_teorico')) / F('total_teorico') * 100)
        ).order_by('-variacion')[:10]
        
        # Costos: Promedio de desviación
        costos_ordenes = []
        for orden in ordenes_finalizadas_qs:
            costos = orden.calcular_costo_real()
            costos_teoricos = orden.receta.calcular_costo_teorico()
            
            costos_ordenes.append({
                'orden_numero': orden.numero,
                'producto': orden.receta.producto_terminado.nombre,
                'costo_unitario_real': float(costos['costo_unitario']),
                'costo_unitario_teorico': float(costos_teoricos['costo_unitario']),
                'variacion': float(costos['costo_unitario'] - costos_teoricos['costo_unitario']),
                'porcentaje_variacion': (
                    float((costos['costo_unitario'] - costos_teoricos['costo_unitario']) / 
                          costos_teoricos['costo_unitario'] * 100)
                    if costos_teoricos['costo_unitario'] > 0 else 0
                )
            })
        
        # Eficiencia de tiempo promedio
        eficiencia_tiempo = ordenes_finalizadas_qs.filter(
            tiempo_real__gt=0,
            receta__tiempo_estimado__gt=0
        ).aggregate(
            promedio=Avg(
                F('receta__tiempo_estimado') * 100.0 / F('tiempo_real')
            )
        )['promedio'] or 0
        
        # Órdenes del día
        hoy = timezone.now().date()
        ordenes_hoy = OrdenProduccion.objects.filter(
            empresa=empresa,
            fecha_programada=hoy
        ).select_related('receta__producto_terminado').values(
            'id', 'numero', 'estado',
            'receta__producto_terminado__nombre',
            'cantidad_planificada', 'cantidad_producida'
        )
        
        # Órdenes de la semana
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        fin_semana = inicio_semana + timedelta(days=6)
        
        ordenes_semana_stats = OrdenProduccion.objects.filter(
            empresa=empresa,
            fecha_programada__gte=inicio_semana,
            fecha_programada__lte=fin_semana
        ).aggregate(
            total=Count('id'),
            finalizadas=Count('id', filter=Q(estado='finalizada')),
            en_proceso=Count('id', filter=Q(estado='en_proceso')),
            pendientes=Count('id', filter=Q(estado='pendiente'))
        )
        
        # Construir respuesta
        data = {
            'periodo': {
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta
            },
            'metricas_operativas': {
                'ordenes_activas': {
                    'pendientes': ordenes_pendientes,
                    'en_proceso': ordenes_en_proceso,
                    'retrasadas': ordenes_retrasadas
                },
                'cumplimiento': {
                    'ordenes_totales': ordenes_totales,
                    'ordenes_finalizadas': ordenes_finalizadas,
                    'ordenes_a_tiempo': ordenes_a_tiempo,
                    'porcentaje_cumplimiento': round(porcentaje_cumplimiento, 2)
                },
                'produccion': {
                    'total_planificado': float(stats_produccion['total_planificado'] or 0),
                    'total_producido': float(stats_produccion['total_producido'] or 0),
                    'diferencia': float(
                        (stats_produccion['total_producido'] or 0) - 
                        (stats_produccion['total_planificado'] or 0)
                    )
                },
                'mermas': {
                    'total_merma': float(stats_mermas['total_merma'] or 0),
                    'costo_merma': float(stats_mermas['costo_merma'] or 0),
                    'porcentaje_merma': round(porcentaje_merma, 2)
                },
                'top_productos': list(top_productos)
            },
            'metricas_eficiencia': {
                'eficiencia_produccion_promedio': round(eficiencia_produccion, 2),
                'eficiencia_tiempo_promedio': round(eficiencia_tiempo, 2),
                'variaciones_consumo': list(variaciones_consumo),
                'costos_ordenes': costos_ordenes[:10]  # Top 10
            },
            'ordenes_hoy': list(ordenes_hoy),
            'ordenes_semana': ordenes_semana_stats
        }
        
        return Response(data)
