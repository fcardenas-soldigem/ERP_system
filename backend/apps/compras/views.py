from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Sum, Count, Q, F, ExpressionWrapper, IntegerField
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from apps.core.permissions import HasEmpresaPermission
from .models import Compra, CompraDetalle, Proveedor, OrdenCompra, RecepcionCompra, PagoCompra
from apps.inventario.models import Producto, Almacen
from .serializers import (
    CompraSerializer,
    CompraDetalleSerializer,
    ProveedorSerializer,
    OrdenCompraSerializer,
    RecepcionCompraSerializer,
    PagoCompraSerializer
)
from rest_framework.views import APIView
import os
from io import BytesIO
from rest_framework.renderers import BaseRenderer
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
import json

class ExcelRenderer(BaseRenderer):
    media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    format = 'xlsx'
    charset = None
    render_style = 'binary'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data

class CompraPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class CompraViewSet(viewsets.ModelViewSet):
    queryset = Compra.objects.all()
    serializer_class = CompraSerializer
    permission_classes = [IsAuthenticated, HasEmpresaPermission]
    pagination_class = CompraPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        try:
            if not hasattr(self.request.user, 'empresa'):
                print(f'Usuario {self.request.user.username} no tiene empresa asignada')
                raise PermissionDenied('Usuario no tiene empresa asignada')

            empresa = self.request.user.empresa
            print(f'Filtrando compras para empresa: {empresa.nombre} (ID: {empresa.id})')

            queryset = self.queryset.filter(empresa=empresa)
            
            # Filtros adicionales por parámetros de URL
            # Filtro por tipo de compra
            tipo_compra_in = self.request.query_params.get('tipo_compra__in')
            if tipo_compra_in:
                tipos = tipo_compra_in.split(',')
                queryset = queryset.filter(tipo_compra__in=tipos)
                print(f'Filtrando por tipo_compra__in: {tipos}')
            
            # Filtro por estado
            estado_in = self.request.query_params.get('estado__in')
            if estado_in:
                estados = estado_in.split(',')
                queryset = queryset.filter(estado__in=estados)
                print(f'Filtrando por estado__in: {estados}')
            
            queryset = queryset.select_related(
                'empresa',
                'proveedor',
                'almacen'
            ).prefetch_related(
                'detalles',
                'detalles__producto',
                'pagos'
            ).order_by('-fecha_emision', '-id')

            print(f'Queryset final: {queryset.count()} compras encontradas')
            return queryset
        except Exception as e:
            print(f'Error en get_queryset: {str(e)}')
            raise

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Exception as e:
            print(f'Error en retrieve: {str(e)}')
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def perform_create(self, serializer):
        if not hasattr(self.request.user, 'empresa'):
            raise PermissionDenied('Usuario no tiene empresa asignada')
        serializer.save(empresa=self.request.user.empresa)

    def list(self, request, *args, **kwargs):
        try:
            print(f'Usuario {request.user.username} solicitando lista de compras')
            queryset = self.get_queryset()
            
            # Aplicar paginación
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'count': queryset.count(),
                'next': None,
                'previous': None,
                'results': serializer.data
            })
        except Exception as e:
            print(f'Error en list: {str(e)}')
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                instance = self.get_object()
                
                # Verificar permisos
                if instance.empresa != request.user.empresa:
                    return Response(
                        {"detail": "No tienes permiso para actualizar esta compra."},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                serializer = self.get_serializer(instance, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                
                return Response(serializer.data)
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def cambiar_estado(self, request, pk=None):
        compra = self.get_object()
        nuevo_estado = request.data.get('estado')
        
        if nuevo_estado not in ['BORRADOR', 'CONFIRMADO', 'ANULADO']:
            return Response(
                {"detail": "Estado no válido"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        compra.estado = nuevo_estado
        compra.save()
        
        serializer = self.get_serializer(compra)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def exportar_excel(self, request):
        compras = self.get_queryset()
        from io import BytesIO
        import pandas as pd
        from openpyxl.utils import get_column_letter
        from django.utils import timezone
        from django.http import HttpResponse

        datos = []
        for compra in compras:
            for detalle in compra.detalles.all():
                datos.append({
                    'Número': compra.numero,
                    'Fecha': compra.fecha_emision.strftime('%Y-%m-%d') if compra.fecha_emision else '',
                    'Proveedor': str(compra.proveedor) if compra.proveedor else '',
                    'Producto': detalle.producto.nombre if detalle.producto else '',
                    'Cantidad': float(detalle.cantidad),
                    'Precio Unitario': float(detalle.precio_unitario),
                    'IGV Incluido': 'Sí' if compra.igv_incluido else 'No',
                    'Subtotal': float(compra.subtotal),
                    'IGV': float(compra.igv),
                    'Total': float(compra.total),
                    'Estado': compra.get_estado_display(),
                    'Método de Pago': compra.get_metodo_pago_display(),
                    'Tipo de Compra': compra.get_tipo_compra_display(),
                    'Saldo Pendiente': float(compra.get_saldo_pendiente())
                })

        df = pd.DataFrame(datos)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Compras', index=False)
            worksheet = writer.sheets['Compras']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(str(col))
                ) + 2
                worksheet.column_dimensions[get_column_letter(idx + 1)].width = min(max_length, 50)
        output.seek(0)
        filename = f'Compras_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Access-Control-Expose-Headers'] = 'Content-Disposition'
        return response

    @action(detail=False, methods=['POST'])
    def importar_excel(self, request):
        try:
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No se ha proporcionado ningún archivo'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            excel_file = request.FILES['file']
            allowed_extensions = ['.xlsx', '.xls', '.csv']
            file_extension = os.path.splitext(excel_file.name)[1].lower()

            if file_extension not in allowed_extensions:
                return Response(
                    {'error': 'Formato de archivo no válido. Use Excel o CSV'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Leer el archivo
            if file_extension == '.csv':
                df = pd.read_csv(excel_file)
            else:
                df = pd.read_excel(excel_file)
            
            # Validar columnas requeridas (ajustadas a tu template)
            required_columns = ['empresa', 'proveedor', 'almacen', 'fecha', 'sku', 'nombre_producto', 'cantidad', 'precio_unitario', 'subtotal', 'igv_incluido', 'estado', 'metodo_pago']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return Response(
                    {'error': f'Faltan columnas requeridas: {", ".join(missing_columns)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            compras_creadas = []
            errores = []

            with transaction.atomic():
                for index, row in df.iterrows():
                    try:
                        # Obtener empresa
                        from apps.empresas.models import Empresa
                        empresa = Empresa.objects.get(nombre=row['empresa'])

                        # Obtener o crear proveedor
                        proveedor = Proveedor.objects.get(
                            razon_social=row['proveedor'],
                            empresa=empresa
                        )

                        # Obtener almacén
                        almacen = Almacen.objects.get(
                            nombre=row['almacen'],
                            empresa=empresa
                        )

                        # Obtener o crear producto
                        from apps.inventario.models import Producto
                        producto, creado = Producto.objects.get_or_create(
                            sku=str(row['sku']),
                            empresa=empresa,
                            defaults={
                                'nombre': row.get('nombre_producto', row['sku'])
                            }
                        )

                        # Procesar cantidad y precio_unitario (eliminar comas si las hay)
                        cantidad = Decimal(str(row['cantidad']).replace(',', ''))
                        precio_unitario = Decimal(str(row['precio_unitario']).replace(',', '').replace('$', ''))
                    
                        # Crear la compra
                        compra = Compra.objects.create(
                            empresa=empresa,
                            proveedor=proveedor,
                            almacen=almacen,
                            fecha_emision=pd.to_datetime(row['fecha']).date(),
                            estado=row['estado'],
                            metodo_pago=row['metodo_pago'],
                            igv_incluido=str(row['igv_incluido']).lower() == 'no'  # Si dice "no", significa que NO está incluido
                        )

                        # Crear el detalle de compra
                        CompraDetalle.objects.create(
                            compra=compra,
                            producto=producto,
                            cantidad=cantidad,
                            precio_unitario=precio_unitario
                        )

                        # Actualizar los totales de la compra
                        compra.actualizar_totales()
                        compras_creadas.append(compra.id)

                    except Exception as e:
                        errores.append(f'Error en fila {index + 2}: {str(e)}')
                    
            return Response({
                'mensaje': f'Se importaron {len(compras_creadas)} compras correctamente',
                'compras_creadas': compras_creadas,
                'errores': errores
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error al procesar el archivo: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """
        Endpoint para obtener estadísticas de cuentas por pagar
        """
        try:
            empresa = request.user.empresa
            compras = self.get_queryset().filter(
                tipo_compra__in=['credito_30', 'credito_60'],
                estado__in=['pendiente', 'borrador']
            ).exclude(estado='anulada')
            
            # Calcular total por pagar y compras pendientes
            total_por_pagar = sum(compra.get_saldo_pendiente() for compra in compras)
            compras_pendientes = compras.count()
            
            return Response({
                'total_por_pagar': total_por_pagar,
                'compras_pendientes': compras_pendientes
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get', 'post'])
    def pagos(self, request, pk=None):
        try:
            compra = self.get_object()
            
            if request.method == 'GET':
                # Obtener los pagos existentes
                pagos = PagoCompra.objects.filter(compra=compra)
                serializer = PagoCompraSerializer(pagos, many=True)
                return Response(serializer.data)
            
            elif request.method == 'POST':
                # Crear un nuevo pago
                print(f'Creando pago para compra {compra.id}')
                print(f'Datos recibidos: {request.data}')
                
                # Validar que la compra sea a crédito o tenga saldo pendiente
                if compra.tipo_compra not in ['credito_30', 'credito_60'] and compra.estado == 'pagada':
                    return Response(
                        {'error': 'No se pueden registrar pagos para esta compra'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Obtener el saldo pendiente
                saldo_pendiente = compra.get_saldo_pendiente()
                if saldo_pendiente <= 0:
                    return Response(
                        {'error': 'Esta compra no tiene saldo pendiente'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Validar el monto del nuevo pago
                try:
                    monto_nuevo_pago = Decimal(str(request.data.get('monto', '0')))
                except (TypeError, ValueError) as e:
                    return Response(
                        {'error': f'Monto inválido: {request.data.get("monto")}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if monto_nuevo_pago <= 0:
                    return Response(
                        {'error': 'El monto del pago debe ser mayor a 0'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if monto_nuevo_pago > saldo_pendiente:
                    return Response(
                        {'error': f'El monto del pago (S/ {monto_nuevo_pago}) no puede ser mayor al saldo pendiente (S/ {saldo_pendiente})'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Crear el nuevo pago
                data = request.data.copy()
                data['compra'] = compra.id
                serializer = PagoCompraSerializer(data=data)
                
                if serializer.is_valid():
                    print(f'Datos validados: {serializer.validated_data}')
                    pago = serializer.save()
                    
                    # Actualizar el estado de la compra si es necesario
                    pagos_total = compra.pagos.aggregate(total=Sum('monto'))['total'] or 0
                    if pagos_total >= compra.total:
                        compra.estado = 'pagada'
                        compra.save()
                        print(f'Compra {compra.id} marcada como pagada')
                    
                    return Response({
                        'pago': PagoCompraSerializer(pago).data,
                        'compra_completamente_pagada': pagos_total >= compra.total,
                        'saldo_restante': float(compra.total - pagos_total)
                    }, status=status.HTTP_201_CREATED)
                
                print(f'Errores de validación: {serializer.errors}')
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            print(f'Error en pagos: {str(e)}')
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def compras_pendientes(self, request):
        """
        Endpoint para obtener las compras pendientes de pago con conversión de moneda
        """
        try:
            from apps.core.services.documento_service import DocumentoService
            
            empresa = request.user.empresa
            compras = self.get_queryset().filter(
                empresa=empresa,
                tipo_compra__in=['credito_30', 'credito_60'],
                estado__in=['pendiente', 'borrador']
            ).exclude(
                estado='anulada'
            )
            
            # Obtener tipo de cambio del día
            doc_service = DocumentoService()
            try:
                tipo_cambio_data = doc_service.obtener_tipo_cambio_venta()
                tipo_cambio = float(tipo_cambio_data.get('venta', 3.8)) if tipo_cambio_data else 3.8
            except:
                tipo_cambio = 3.8  # Fallback
            
            # Procesar compras con conversión de moneda
            compras_procesadas = []
            total_general_pen = 0
            
            for compra in compras:
                # Calcular saldo pendiente
                pagos_reales = compra.pagos.exclude(metodo_pago='pendiente')
                total_pagado = sum([float(pago.monto) for pago in pagos_reales])
                saldo_pendiente = float(compra.total) - total_pagado
                
                if saldo_pendiente > 0:  # Solo incluir si tiene saldo pendiente
                    # Convertir a PEN si la compra es en USD
                    saldo_pendiente_pen = saldo_pendiente
                    total_pen = float(compra.total)
                    
                    if compra.moneda == 'USD':
                        saldo_pendiente_pen = saldo_pendiente * tipo_cambio
                        total_pen = float(compra.total) * tipo_cambio
                    
                    # Calcular días restantes hasta vencimiento
                    dias_restantes = None
                    if compra.fecha_vencimiento:
                        dias_restantes = (compra.fecha_vencimiento - timezone.now().date()).days
                    
                    compra_data = {
                        'id': compra.id,
                        'numero': compra.numero,
                        'proveedor': {
                            'id': compra.proveedor.id,
                            'razon_social': compra.proveedor.razon_social,
                            'ruc': compra.proveedor.ruc
                        },
                        'fecha_emision': compra.fecha_emision,
                        'fecha_vencimiento': compra.fecha_vencimiento,
                        'tipo_compra': compra.tipo_compra,
                        'estado': compra.estado,
                        'moneda': compra.moneda,
                        'total': float(compra.total),
                        'total_pen': total_pen,  # Total convertido a PEN
                        'saldo_pendiente': saldo_pendiente,
                        'saldo_pendiente_pen': saldo_pendiente_pen,  # Saldo convertido a PEN
                        'dias_restantes': dias_restantes
                    }
                    
                    compras_procesadas.append(compra_data)
                    total_general_pen += saldo_pendiente_pen
            
            return Response({
                'compras': compras_procesadas,
                'total_general_pen': total_general_pen,
                'tipo_cambio': tipo_cambio,
                'count': len(compras_procesadas)
            })
        except Exception as e:
            print(f'Error en compras_pendientes: {str(e)}')
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'], url_path='saldo-pendiente')
    def saldo_pendiente(self, request, pk=None):
        try:
            compra = self.get_object()
            saldo = compra.get_saldo_pendiente()
            return Response({'saldo_pendiente': saldo})
        except Exception as e:
            print(f'Error en saldo_pendiente: {str(e)}')
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['GET'])
    def get_productos(self, request):
        """
        Endpoint para obtener los productos disponibles para compras
        """
        try:
            from apps.inventario.models import Producto
            from apps.inventario.serializers import ProductoSerializer
            
            # Asegurarnos de obtener la empresa correcta
            empresa = request.user.empresa
            if not empresa:
                return Response(
                    {'error': 'No se encontró una empresa asociada al usuario'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            productos = Producto.objects.filter(
                empresa=empresa,
                is_active=True
            ).order_by('nombre')
            
            serializer = ProductoSerializer(productos, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def create(self, request, *args, **kwargs):
        """
        Método personalizado para crear compras con detalles de productos
        """
        try:
            print(f'Datos recibidos en create: {dict(request.data)}')
            
            with transaction.atomic():
                # Obtener datos básicos de la compra
                empresa = request.user.empresa
                if not empresa:
                    return Response(
                        {'error': 'Usuario no tiene empresa asignada'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Procesar detalles si existen
                detalles_data = []
                if 'detalles' in request.data:
                    try:
                        detalles_json = request.data.get('detalles')
                        if isinstance(detalles_json, str):
                            detalles_data = json.loads(detalles_json)
                        else:
                            detalles_data = detalles_json
                        print(f'Detalles procesados: {detalles_data}')
                    except Exception as e:
                        print(f'Error al procesar detalles: {str(e)}')
                        return Response(
                            {'error': f'Error al procesar detalles: {str(e)}'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                # Validar que haya detalles
                if not detalles_data:
                    return Response(
                        {'error': 'Debe incluir al menos un producto en la compra'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Crear datos para el serializer (sin detalles)
                compra_data = request.data.copy()
                if 'detalles' in compra_data:
                    del compra_data['detalles']

                # Crear la compra usando el serializer
                serializer = self.get_serializer(data=compra_data)
                serializer.is_valid(raise_exception=True)
                compra = serializer.save(empresa=empresa)

                print(f'Compra creada: {compra.id}')

                # Crear los detalles
                from .models import CompraDetalle
                from apps.inventario.models.producto import Producto
                
                print(f"=== CREANDO DETALLES PARA COMPRA {compra.numero} ===")
                print(f"Número de detalles a crear: {len(detalles_data)}")
                
                for idx, detalle_data in enumerate(detalles_data):
                    try:
                        print(f"Creando detalle {idx + 1}/{len(detalles_data)}")
                        
                        # Validar datos del detalle
                        producto_id = detalle_data.get('producto')
                        cantidad = detalle_data.get('cantidad')
                        precio_unitario = detalle_data.get('precio_unitario')

                        print(f"Datos del detalle: producto_id={producto_id}, cantidad={cantidad}, precio={precio_unitario}")

                        if not producto_id or not cantidad or not precio_unitario:
                            raise ValueError('Faltan datos en el detalle del producto')

                        # Obtener el producto
                        producto = Producto.objects.get(
                            id=int(producto_id),
                            empresa=empresa
                        )

                        # Crear el detalle
                        detalle = CompraDetalle.objects.create(
                            compra=compra,
                            producto=producto,
                            cantidad=Decimal(str(cantidad)),
                            precio_unitario=Decimal(str(precio_unitario))
                        )
                        print(f'Detalle creado: ID={detalle.id}, Producto {producto.nombre}, Cantidad {cantidad}, Precio {precio_unitario}')

                    except Exception as e:
                        print(f'Error al crear detalle: {str(e)}')
                        raise ValueError(f'Error al procesar producto: {str(e)}')
                
                print(f"=== DETALLES CREADOS PARA COMPRA {compra.numero} ===")

                # Actualizar totales de la compra
                compra.actualizar_totales()
                print(f'Totales actualizados - Subtotal: {compra.subtotal}, IGV: {compra.igv}, Total: {compra.total}')

                # Si la compra está pagada, actualizar el stock inmediatamente
                if compra.estado == 'pagada':
                    print(f"=== LLAMANDO ACTUALIZAR_STOCK DESDE CREATE COMPRA ===")
                    print(f"Compra: {compra.numero}, Estado: {compra.estado}")
                    compra.actualizar_stock()
                    print(f'Stock actualizado para compra {compra.numero}')
                    print(f"=== FIN ACTUALIZAR_STOCK DESDE CREATE COMPRA ===")

                # Retornar la compra creada
                response_serializer = self.get_serializer(compra)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f'Error en create de CompraViewSet: {str(e)}')
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class ProveedorViewSet(viewsets.ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    permission_classes = [IsAuthenticated, HasEmpresaPermission]

    def get_queryset(self):
        return self.queryset.filter(empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)

    @action(detail=False, methods=['get'])
    def consultar_ruc(self, request):
        """
        Consulta automática de datos de proveedor por RUC usando la API de SUNAT
        """
        ruc = request.query_params.get('ruc')
        
        if not ruc:
            return Response(
                {'error': 'Debe proporcionar un RUC'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(ruc) != 11:
            return Response(
                {'error': 'El RUC debe tener 11 dígitos'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.core.services.documento_service import DocumentoService
            
            # Consultar datos del RUC
            resultado = DocumentoService.consultar_ruc(ruc)
            
            if resultado.get('success'):
                data = resultado['data']
                response_data = {
                    'success': True,
                    'data': {
                        'ruc': data.get('ruc', ruc),
                        'razon_social': data.get('razon_social', ''),
                        'direccion': data.get('direccion', ''),
                        'estado': data.get('estado', ''),
                        'condicion': data.get('condicion', ''),
                        'ubigeo': data.get('ubigeo', ''),
                    }
                }
                return Response(response_data)
            else:
                return Response(
                    {'error': resultado.get('error', 'No se pudo consultar el RUC')}, 
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            return Response(
                {'error': f'Error interno del servidor: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False,
        methods=['get'],
        renderer_classes=[ExcelRenderer],
    )
    def exportar(self, request):
        try:
            proveedores = self.get_queryset()
            
            if not proveedores.exists():
                return Response(
                    {'error': 'No hay proveedores para exportar'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Crear el archivo Excel
            wb = Workbook()
            ws = wb.active
            ws.title = "Proveedores"

            # Definir las columnas
            columns = [
                'RUC',
                'Razón Social',
                'Teléfono',
                'Estado',
                'Fecha Registro'
            ]

            # Escribir los encabezados
            for col_num, column_title in enumerate(columns, 1):
                cell = ws.cell(row=1, column=col_num)
                cell.value = column_title
                cell.font = cell.font.copy(bold=True)

            # Escribir los datos
            for row_num, proveedor in enumerate(proveedores, 2):
                row = [
                    proveedor.ruc,
                    proveedor.razon_social,
                    proveedor.telefono or '',
                    'Activo' if proveedor.activo else 'Inactivo',
                    proveedor.created_at.strftime('%Y-%m-%d') if proveedor.created_at else ''
                ]
                
                for col_num, cell_value in enumerate(row, 1):
                    cell = ws.cell(row=row_num, column=col_num)
                    cell.value = cell_value

            # Ajustar el ancho de las columnas
            for column_cells in ws.columns:
                length = max(len(str(cell.value)) for cell in column_cells)
                ws.column_dimensions[get_column_letter(column_cells[0].column)].width = min(length + 2, 50)

            # Guardar el Excel en memoria
            excel_file = BytesIO()
            wb.save(excel_file)
            excel_file.seek(0)
            
            # Preparar la respuesta
            response = HttpResponse(
                excel_file.getvalue(),
                content_type=ExcelRenderer.media_type
            )
            response['Content-Disposition'] = f'attachment; filename=Proveedores_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
            
            return response

        except Exception as e:
            print(f"Error en exportar: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class OrdenCompraViewSet(viewsets.ModelViewSet):
    queryset = OrdenCompra.objects.all()
    serializer_class = OrdenCompraSerializer
    permission_classes = [IsAuthenticated, HasEmpresaPermission]

    def get_queryset(self):
        return self.queryset.filter(empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)

class RecepcionCompraViewSet(viewsets.ModelViewSet):
    queryset = RecepcionCompra.objects.all()
    serializer_class = RecepcionCompraSerializer
    permission_classes = [IsAuthenticated, HasEmpresaPermission]

    def get_queryset(self):
        return self.queryset.filter(empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)

class ResumenComprasMensual(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, HasEmpresaPermission]

    def list(self, request):
        # Obtener el primer día del mes actual
        today = timezone.now()
        first_day = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Calcular el último día del mes
        if today.month == 12:
            last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        
        # Filtrar compras del mes actual
        compras = Compra.objects.filter(
            empresa=request.user.empresa,
            fecha_emision__range=(first_day, last_day)
        )
        
        # Calcular totales
        total_compras = compras.count()
        monto_total = compras.aggregate(total=Sum('total'))['total'] or Decimal('0')
        
        return Response({
            'total_compras': total_compras,
            'monto_total': float(monto_total),
            'mes': today.strftime('%B %Y')
        })

    def retrieve(self, request, pk=None):
        # Obtener el mes y año específico
        try:
            year, month = map(int, pk.split('-'))
            first_day = timezone.datetime(year, month, 1)
            if month == 12:
                last_day = timezone.datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = timezone.datetime(year, month + 1, 1) - timedelta(days=1)
            
            compras = Compra.objects.filter(
                empresa=request.user.empresa,
                fecha_emision__range=(first_day, last_day)
            )
            
            total_compras = compras.count()
            monto_total = compras.aggregate(total=Sum('total'))['total'] or Decimal('0')
            
            return Response({
                'total_compras': total_compras,
                'monto_total': float(monto_total),
                'mes': first_day.strftime('%B %Y')
            })
        except (ValueError, IndexError):
            return Response(
                {'detail': 'Formato de fecha inválido. Use YYYY-MM'},
                status=status.HTTP_400_BAD_REQUEST
            )

def descargar_template_compras(request):
    """
    Vista para descargar el template de importación de compras actualizado
    """
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Template Compras"

        headers = [
            'empresa',
            'proveedor',
            'almacen',
            'fecha',
            'producto',
            'nombre_producto',
            'cantidad',
            'precio_unitario',
            'subtotal',
            'igv_incluido',
            'estado',
            'metodo_pago'
        ]

        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=template_compras.xlsx'
        wb.save(response)
        return response
    except Exception as e:
        print(f"Error al generar template de compras: {str(e)}")
        return HttpResponse(status=500)

class PagoCompraViewSet(viewsets.ModelViewSet):
    queryset = PagoCompra.objects.all()
    serializer_class = PagoCompraSerializer
    permission_classes = [IsAuthenticated, HasEmpresaPermission]

    def get_queryset(self):
        return self.queryset.filter(compra__empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        compra = serializer.validated_data['compra']
        if compra.empresa != self.request.user.empresa:
            raise PermissionDenied("No tienes permiso para crear pagos para esta compra")
        serializer.save()

        # Actualizar el total pagado y estado de la compra
        compra.pagos_total = compra.pagos.aggregate(total=Sum('monto'))['total'] or 0
        if compra.pagos_total >= compra.total:
            compra.estado = 'pagada'
        compra.save()

    def perform_update(self, serializer):
        compra = serializer.validated_data['compra']
        if compra.empresa != self.request.user.empresa:
            raise PermissionDenied("No tienes permiso para actualizar pagos de esta compra")
        serializer.save()

        # Actualizar el total pagado y estado de la compra
        compra.pagos_total = compra.pagos.aggregate(total=Sum('monto'))['total'] or 0
        if compra.pagos_total >= compra.total:
            compra.estado = 'pagada'
        elif compra.pagos_total < compra.total:
            compra.estado = 'pendiente'
        compra.save()

    def perform_destroy(self, instance):
        compra = instance.compra
        if compra.empresa != self.request.user.empresa:
            raise PermissionDenied("No tienes permiso para eliminar pagos de esta compra")
        instance.delete()

        # Actualizar el total pagado y estado de la compra
        compra.pagos_total = compra.pagos.aggregate(total=Sum('monto'))['total'] or 0
        if compra.pagos_total < compra.total:
            compra.estado = 'pendiente'
        compra.save()
    