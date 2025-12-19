from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q
from .models import Cotizacion, DetalleCotizacion
from .serializers import (
    CotizacionSerializer,
    CotizacionListSerializer,
    CotizacionCreateSerializer,
    DetalleCotizacionSerializer
)
from apps.core.permissions import HasEmpresaPermission
from .utils.pdf_generator import CotizacionPDFGenerator


class CotizacionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar cotizaciones
    """
    permission_classes = [IsAuthenticated, HasEmpresaPermission]
    
    def get_queryset(self):
        """
        Filtrar cotizaciones por empresa del usuario
        """
        queryset = Cotizacion.objects.filter(
            empresa=self.request.user.empresa
        ).select_related(
            'cliente', 'usuario_creador', 'empresa'
        ).prefetch_related('detalles', 'detalles__producto')
        
        # Filtros opcionales
        estado = self.request.query_params.get('estado', None)
        cliente_id = self.request.query_params.get('cliente', None)
        search = self.request.query_params.get('search', None)
        
        if estado:
            queryset = queryset.filter(estado=estado)
        
        if cliente_id:
            queryset = queryset.filter(cliente_id=cliente_id)
        
        if search:
            queryset = queryset.filter(
                Q(numero__icontains=search) |
                Q(asunto__icontains=search) |
                Q(cliente__nombre__icontains=search)
            )
        
        return queryset
    
    def get_serializer_class(self):
        """
        Usar diferentes serializers según la acción
        """
        if self.action == 'list':
            return CotizacionListSerializer
        elif self.action == 'create':
            return CotizacionCreateSerializer
        return CotizacionSerializer
    
    def perform_create(self, serializer):
        """
        Asignar empresa y usuario al crear
        """
        serializer.save(
            empresa=self.request.user.empresa,
            usuario_creador=self.request.user
        )
    
    @action(detail=True, methods=['get'], url_path='exportar-pdf')
    def exportar_pdf(self, request, pk=None):
        """
        Exportar cotización a PDF profesional
        """
        cotizacion = self.get_object()
        
        try:
            # Generar PDF
            pdf_generator = CotizacionPDFGenerator(cotizacion)
            pdf_buffer = pdf_generator.generar_pdf()
            
            # Preparar respuesta
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            filename = f'Cotizacion_{cotizacion.numero}.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
        
        except Exception as e:
            return Response(
                {'error': f'Error al generar PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='cambiar-estado')
    def cambiar_estado(self, request, pk=None):
        """
        Cambiar el estado de la cotización
        """
        cotizacion = self.get_object()
        nuevo_estado = request.data.get('estado')
        
        if nuevo_estado not in dict(Cotizacion.ESTADO_CHOICES):
            return Response(
                {'error': 'Estado inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cotizacion.estado = nuevo_estado
        
        # Si se acepta, registrar fecha
        if nuevo_estado == 'aceptada':
            cotizacion.fecha_aceptacion = timezone.now().date()
        
        cotizacion.save()
        
        serializer = self.get_serializer(cotizacion)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='duplicar')
    def duplicar(self, request, pk=None):
        """
        Duplicar una cotización existente
        """
        cotizacion_original = self.get_object()
        
        # Crear nueva cotización
        nueva_cotizacion = Cotizacion.objects.create(
            empresa=cotizacion_original.empresa,
            cliente=cotizacion_original.cliente,
            usuario_creador=request.user,
            asunto=f"{cotizacion_original.asunto} (Copia)",
            descripcion=cotizacion_original.descripcion,
            fecha_vencimiento=cotizacion_original.fecha_vencimiento,
            moneda=cotizacion_original.moneda,
            incluye_igv=cotizacion_original.incluye_igv,
            porcentaje_igv=cotizacion_original.porcentaje_igv,
            descuento=cotizacion_original.descuento,
            forma_pago=cotizacion_original.forma_pago,
            tiempo_entrega=cotizacion_original.tiempo_entrega,
            lugar_entrega=cotizacion_original.lugar_entrega,
            validez_oferta=cotizacion_original.validez_oferta,
            notas=cotizacion_original.notas,
            terminos_condiciones=cotizacion_original.terminos_condiciones,
        )
        
        # Copiar detalles
        for detalle in cotizacion_original.detalles.all():
            DetalleCotizacion.objects.create(
                cotizacion=nueva_cotizacion,
                producto=detalle.producto,
                codigo=detalle.codigo,
                descripcion=detalle.descripcion,
                cantidad=detalle.cantidad,
                precio_unitario=detalle.precio_unitario,
                descuento_item=detalle.descuento_item,
                orden=detalle.orden
            )
        
        # Calcular totales
        nueva_cotizacion.calcular_totales()
        
        serializer = self.get_serializer(nueva_cotizacion)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='convertir-venta')
    def convertir_venta(self, request, pk=None):
        """
        Convertir cotización a venta
        """
        cotizacion = self.get_object()
        
        if cotizacion.estado == 'convertida':
            return Response(
                {'error': 'Esta cotización ya fue convertida a venta'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.ventas.models import Venta, DetalleVenta
            
            # Crear venta
            venta = Venta.objects.create(
                empresa=cotizacion.empresa,
                cliente=cotizacion.cliente,
                tipo_venta='factura',
                moneda=cotizacion.moneda,
                forma_pago=cotizacion.forma_pago,
                notas=f"Generada desde cotización {cotizacion.numero}\n{cotizacion.notas or ''}",
                igv_incluido=cotizacion.incluye_igv,
            )
            
            # Crear detalles de venta
            for detalle in cotizacion.detalles.all():
                if detalle.producto:
                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=detalle.producto,
                        cantidad=detalle.cantidad,
                        precio_unitario=detalle.precio_unitario,
                        descuento=detalle.descuento_item
                    )
            
            # Actualizar cotización
            cotizacion.estado = 'convertida'
            cotizacion.venta = venta
            cotizacion.save()
            
            return Response({
                'success': True,
                'message': 'Cotización convertida a venta exitosamente',
                'venta_id': venta.id,
                'venta_numero': venta.numero
            })
        
        except Exception as e:
            return Response(
                {'error': f'Error al convertir a venta: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='estadisticas')
    def estadisticas(self, request):
        """
        Obtener estadísticas de cotizaciones
        """
        queryset = self.get_queryset()
        
        total = queryset.count()
        por_estado = {}
        
        for estado_key, estado_label in Cotizacion.ESTADO_CHOICES:
            count = queryset.filter(estado=estado_key).count()
            por_estado[estado_key] = {
                'label': estado_label,
                'count': count,
                'porcentaje': round((count / total * 100) if total > 0 else 0, 2)
            }
        
        # Valor total de cotizaciones
        from django.db.models import Sum
        valor_total = queryset.aggregate(total=Sum('total'))['total'] or 0
        valor_aceptadas = queryset.filter(estado='aceptada').aggregate(total=Sum('total'))['total'] or 0
        
        return Response({
            'total_cotizaciones': total,
            'por_estado': por_estado,
            'valor_total': float(valor_total),
            'valor_aceptadas': float(valor_aceptadas),
            'tasa_conversion': round((por_estado.get('aceptada', {}).get('count', 0) / total * 100) if total > 0 else 0, 2)
        })


