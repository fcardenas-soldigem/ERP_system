import logging

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
from .services.conversion_service import (
    convertir_cotizacion_a_venta,
    CotizacionNoConvertibleError,
    ProductosFaltantesError,
)

logger = logging.getLogger(__name__)


from rest_framework.pagination import PageNumberPagination


class CotizacionPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 200


class CotizacionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar cotizaciones
    """
    permission_classes = [IsAuthenticated, HasEmpresaPermission]
    pagination_class = CotizacionPagination
    
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
        if self.action == 'list':
            return CotizacionListSerializer
        elif self.action in ('create', 'update', 'partial_update'):
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
        import traceback
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
            error_traceback = traceback.format_exc()
            return Response(
                {'error': f'Error al generar PDF: {str(e)}', 'detail': error_traceback},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='cambiar-estado')
    def cambiar_estado(self, request, pk=None):
        """
        Cambiar el estado de la cotización.

        Si el nuevo estado es 'aceptada', la cotización se convierte automáticamente
        a venta y termina en estado 'convertida' con la venta enlazada.
        """
        cotizacion = self.get_object()
        nuevo_estado = request.data.get('estado')

        if nuevo_estado not in dict(Cotizacion.ESTADO_CHOICES):
            return Response(
                {'error': 'Estado inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if nuevo_estado == 'aceptada':
            if cotizacion.estado == 'convertida':
                return Response(
                    {'error': 'Esta cotización ya fue aceptada y convertida a venta.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                cotizacion.fecha_aceptacion = timezone.now().date()
                cotizacion.save(update_fields=['fecha_aceptacion', 'fecha_modificacion'])

                venta = convertir_cotizacion_a_venta(cotizacion)
            except ProductosFaltantesError as e:
                return Response({
                    'error': 'productos_faltantes',
                    'message': str(e),
                    'productos_faltantes': e.productos_faltantes,
                    'cotizacion_id': cotizacion.id,
                    'moneda': cotizacion.moneda,
                }, status=status.HTTP_400_BAD_REQUEST)
            except CotizacionNoConvertibleError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except Exception as e:
                logger.exception('Error al convertir cotización %s al aceptar', cotizacion.numero)
                return Response(
                    {'error': f'Error al crear la venta: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            cotizacion.refresh_from_db()
            data = self.get_serializer(cotizacion).data
            data.update({
                'venta_creada': True,
                'venta_id': venta.id,
                'venta_numero': venta.numero,
                'message': f'Cotización aceptada y convertida a venta {venta.numero}',
            })
            return Response(data)

        cotizacion.estado = nuevo_estado
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
        Convertir cotización a venta de forma manual.

        Usa el mismo servicio que la auto-conversión al aceptar.
        """
        cotizacion = self.get_object()

        try:
            venta = convertir_cotizacion_a_venta(cotizacion)
        except ProductosFaltantesError as e:
            return Response({
                'error': 'productos_faltantes',
                'message': str(e),
                'productos_faltantes': e.productos_faltantes,
                'cotizacion_id': cotizacion.id,
                'moneda': cotizacion.moneda,
            }, status=status.HTTP_400_BAD_REQUEST)
        except CotizacionNoConvertibleError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception('Error al convertir cotización %s a venta', cotizacion.numero)
            return Response(
                {'error': f'Error al convertir a venta: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'success': True,
            'message': f'Cotización convertida a venta {venta.numero}',
            'venta_id': venta.id,
            'venta_numero': venta.numero,
        })
    
    @action(detail=True, methods=['post'], url_path='vincular-producto')
    def vincular_producto(self, request, pk=None):
        """
        Vincula un producto del inventario con una línea de detalle de la cotización.
        Body: { detalle_id: int, producto_id: int }
        """
        cotizacion = self.get_object()
        detalle_id = request.data.get('detalle_id')
        producto_id = request.data.get('producto_id')

        if not detalle_id or not producto_id:
            return Response(
                {'error': 'Se requiere detalle_id y producto_id'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            detalle = cotizacion.detalles.get(id=detalle_id)
        except DetalleCotizacion.DoesNotExist:
            return Response(
                {'error': f'Detalle {detalle_id} no pertenece a esta cotización'},
                status=status.HTTP_404_NOT_FOUND,
            )

        from apps.inventario.models import Producto
        try:
            producto = Producto.objects.get(id=producto_id, empresa=cotizacion.empresa)
        except Producto.DoesNotExist:
            return Response(
                {'error': f'Producto {producto_id} no encontrado'},
                status=status.HTTP_404_NOT_FOUND,
            )

        detalle.producto = producto
        detalle.save(update_fields=['producto'])

        return Response({'success': True, 'detalle_id': detalle.id, 'producto_id': producto.id})

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


