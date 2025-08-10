from rest_framework import generics, permissions, viewsets, views, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import Sum, Count, Q, Case, When, ExpressionWrapper, DecimalField, F
from django.db import transaction
from django.utils import timezone
from django.http import HttpResponse
from django.core.exceptions import ValidationError
from decimal import Decimal
import openpyxl
from datetime import datetime, timedelta
import json
import pandas as pd
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404

from .models import (
    Almacen, 
    Categoria, 
    Producto, 
    Stock, 
    AjusteInventario, 
    MovimientoInventario
)
from .serializers import (
    AlmacenSerializer, 
    CategoriaSerializer, 
    ProductoSerializer, 
    StockSerializer,
    AjusteInventarioSerializer,
    MovimientoInventarioSerializer,
    KardexSerializer,
    KardexResumenSerializer,
    MovimientoInventarioCreateSerializer
)
from apps.core.permissions import HasEmpresaPermission

class AlmacenViewSet(viewsets.ModelViewSet):
    serializer_class = AlmacenSerializer
    permission_classes = [IsAuthenticated, HasEmpresaPermission]

    def get_queryset(self):
        return Almacen.objects.filter(empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)

class CategoriaViewSet(viewsets.ModelViewSet):
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated, HasEmpresaPermission]

    def get_queryset(self):
        return Categoria.objects.filter(empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)

class ProductoViewSet(viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated, HasEmpresaPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['categoria', 'almacen']
    search_fields = ['nombre', 'sku', 'descripcion']
    ordering_fields = ['nombre', 'sku', 'stock_total', 'precio_venta']
    ordering = ['sku']

    def get_queryset(self):
        queryset = Producto.objects.filter(empresa=self.request.user.empresa, is_active=True)
        return queryset

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)

    @action(detail=False, methods=['get'])
    def stock_bajo(self, request):
        productos = self.get_queryset().filter(
            stock_total__lte=F('stock_minimo')
        )
        serializer = self.get_serializer(productos, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def check_sku(self, request):
        """Verifica si un SKU ya existe"""
        sku = request.query_params.get('sku', '').strip()
        if not sku:
            return Response({'exists': False})
        
        exists = Producto.objects.filter(
            empresa=request.user.empresa,
            sku__iexact=sku
        ).exists()
        
        return Response({'exists': exists})
    
    @action(detail=False, methods=['get'])
    def valor_total_adquisicion(self, request):
        """Obtiene el valor total de adquisición del inventario"""
        empresa = request.user.empresa
        
        # Calcular valor total de adquisición (precio_compra * stock_total)
        productos = Producto.objects.filter(empresa=empresa, is_active=True)
        valor_total = sum(
            float(producto.precio_compra or 0) * float(producto.stock_total or 0)
            for producto in productos
        )
        
        return Response({'valor_total_adquisicion': valor_total})

class StockViewSet(viewsets.ModelViewSet):
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated, HasEmpresaPermission]

    def get_queryset(self):
        return Stock.objects.filter(empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)

class AjusteInventarioViewSet(viewsets.ModelViewSet):
    serializer_class = AjusteInventarioSerializer
    permission_classes = [IsAuthenticated, HasEmpresaPermission]

    def get_queryset(self):
        return AjusteInventario.objects.filter(empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)

class ResumenInventario(views.APIView):
    """Vista para obtener resumen general del inventario"""
    permission_classes = [IsAuthenticated, HasEmpresaPermission]
    
    def get(self, request):
        empresa = request.user.empresa
        
        # Estadísticas generales
        total_productos = Producto.objects.filter(empresa=empresa, is_active=True).count()
        total_categorias = Categoria.objects.filter(empresa=empresa).count()
        total_almacenes = Almacen.objects.filter(empresa=empresa).count()
        
        # Productos con stock bajo
        productos_stock_bajo = Producto.objects.filter(
            empresa=empresa,
            is_active=True,
            stock_total__lte=F('stock_minimo')
        ).count()
        
        # Productos sin stock
        productos_sin_stock = Producto.objects.filter(
            empresa=empresa,
            is_active=True,
            stock_total=0
        ).count()
        
        # Valor total del inventario
        valor_inventario = Producto.objects.filter(
            empresa=empresa,
            is_active=True
        ).aggregate(
            valor_compra=Sum(F('stock_total') * F('precio_compra')),
            valor_venta=Sum(F('stock_total') * F('precio_venta'))
        )
        
        # Top productos por valor
        top_productos = Producto.objects.filter(
            empresa=empresa,
            is_active=True,
            stock_total__gt=0
        ).annotate(
            valor_stock=ExpressionWrapper(
                F('stock_total') * F('precio_venta'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        ).order_by('-valor_stock')[:5]
        
        # Movimientos recientes (últimos 7 días)
        fecha_limite = timezone.now() - timedelta(days=7)
        movimientos_recientes = MovimientoInventario.objects.filter(
            empresa=empresa,
            fecha__gte=fecha_limite
        ).count()
        
        data = {
            'estadisticas_generales': {
                'total_productos': total_productos,
                'total_categorias': total_categorias,
                'total_almacenes': total_almacenes,
                'productos_stock_bajo': productos_stock_bajo,
                'productos_sin_stock': productos_sin_stock,
                'movimientos_recientes': movimientos_recientes
            },
            'valor_inventario': {
                'valor_compra': valor_inventario['valor_compra'] or 0,
                'valor_venta': valor_inventario['valor_venta'] or 0
            },
            'top_productos': ProductoSerializer(top_productos, many=True).data
        }
        
        return Response(data)

class ProductoEstadisticasView(views.APIView):
    """Vista para estadísticas específicas de productos"""
    permission_classes = [IsAuthenticated, HasEmpresaPermission]
    
    def get(self, request):
        empresa = request.user.empresa
        
        # Distribución por categorías
        categorias_stats = Categoria.objects.filter(empresa=empresa).annotate(
            total_productos=Count('productos', filter=Q(productos__is_active=True)),
            valor_total=Sum(
                ExpressionWrapper(
                    F('productos__stock_total') * F('productos__precio_venta'),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                ),
                filter=Q(productos__is_active=True)
            )
        ).order_by('-total_productos')
        
        # Productos más vendidos (basado en movimientos de salida)
        productos_vendidos = MovimientoInventario.objects.filter(
            empresa=empresa,
            tipo_movimiento='salida',
            tipo_documento='venta',
            fecha__gte=timezone.now() - timedelta(days=30)
        ).values('producto__nombre', 'producto__sku').annotate(
            total_vendido=Sum('cantidad_salida')
        ).order_by('-total_vendido')[:10]
        
        # Rotación de inventario por producto
        rotacion_productos = []
        for producto in Producto.objects.filter(empresa=empresa, is_active=True)[:20]:
            ventas_30d = MovimientoInventario.objects.filter(
                empresa=empresa,
                producto=producto,
                tipo_movimiento='salida',
                tipo_documento='venta',
                fecha__gte=timezone.now() - timedelta(days=30)
            ).aggregate(total=Sum('cantidad_salida'))['total'] or 0
            
            if producto.stock_total > 0 and ventas_30d > 0:
                rotacion = (ventas_30d / producto.stock_total) * 12  # Anualizado
                rotacion_productos.append({
                    'producto': producto.nombre,
                    'sku': producto.sku,
                    'rotacion_anual': round(float(rotacion), 2),
                    'stock_actual': float(producto.stock_total),
                    'ventas_30d': float(ventas_30d)
                })
        
        # Ordenar por rotación
        rotacion_productos.sort(key=lambda x: x['rotacion_anual'], reverse=True)
        
        data = {
            'categorias_stats': [
                {
                    'categoria': cat.nombre,
                    'total_productos': cat.total_productos,
                    'valor_total': float(cat.valor_total or 0)
                }
                for cat in categorias_stats
            ],
            'productos_mas_vendidos': list(productos_vendidos),
            'rotacion_inventario': rotacion_productos[:10]
        }
        
        return Response(data)

class ValorInventarioViewSet(viewsets.ViewSet):
    """ViewSet para consultas de valor de inventario"""
    permission_classes = [IsAuthenticated, HasEmpresaPermission]
    
    def list(self, request):
        """Obtiene el valor del inventario por diferentes criterios"""
        empresa = request.user.empresa
        
        # Valor total por almacén
        valor_por_almacen = []
        for almacen in Almacen.objects.filter(empresa=empresa):
            stocks = Stock.objects.filter(almacen=almacen, empresa=empresa)
            valor_compra = sum(
                stock.cantidad * stock.producto.precio_compra
                for stock in stocks
            )
            valor_venta = sum(
                stock.cantidad * stock.producto.precio_venta
                for stock in stocks
            )
            
            valor_por_almacen.append({
                'almacen': almacen.nombre,
                'valor_total': float(valor_compra),  # Usar precio de compra como valor total
                'valor_compra': float(valor_compra),
                'valor_venta': float(valor_venta),
                'utilidad_potencial': float(valor_venta - valor_compra)
            })
        
        # Valor total por categoría
        valor_por_categoria = []
        for categoria in Categoria.objects.filter(empresa=empresa):
            productos = Producto.objects.filter(categoria=categoria, empresa=empresa, is_active=True)
            valor_compra = sum(
                producto.stock_total * producto.precio_compra
                for producto in productos
            )
            valor_venta = sum(
                producto.stock_total * producto.precio_venta
                for producto in productos
            )
            
            valor_por_categoria.append({
                'categoria': categoria.nombre,
                'valor_total': float(valor_compra),  # Usar precio de compra como valor total
                'valor_compra': float(valor_compra),
                'valor_venta': float(valor_venta),
                'utilidad_potencial': float(valor_venta - valor_compra)
            })
        
        # Resumen general
        total_productos = Producto.objects.filter(empresa=empresa, is_active=True)
        valor_total_compra = sum(
            producto.stock_total * producto.precio_compra
            for producto in total_productos
        )
        valor_total_venta = sum(
            producto.stock_total * producto.precio_venta
            for producto in total_productos
        )
        
        data = {
            'resumen_general': {
                'valor_total': float(valor_total_compra),  # Usar precio de compra como valor total
                'valor_total_compra': float(valor_total_compra),
                'valor_total_venta': float(valor_total_venta),
                'utilidad_potencial': float(valor_total_venta - valor_total_compra)
            },
            'valor_por_almacen': valor_por_almacen,
            'valor_por_categoria': valor_por_categoria
        }
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def reporte_detallado(self, request):
        """Obtiene el reporte detallado del valor del inventario por productos"""
        empresa = request.user.empresa
        
        # Obtener productos con stock
        productos = Producto.objects.filter(
            empresa=empresa, 
            is_active=True,
            stock_total__gt=0
        )
        
        items = []
        for producto in productos:
            valor_total = float(producto.stock_total * producto.precio_compra)
            items.append({
                'producto__nombre': producto.nombre,
                'producto__codigo': producto.sku,
                'descripcion': producto.descripcion,
                'categoria': producto.categoria.nombre if producto.categoria else 'Sin categoría',
                'cantidad_total': float(producto.stock_total),
                'producto__unidad_medida': producto.unidad_medida,
                'estado': producto.get_estado_display(),
                'costo_promedio': float(producto.precio_compra),
                'valor_total': valor_total
            })
        
        return Response(items)

# Clases para importar/exportar productos
class ImportarProductosAPIView(views.APIView):
    """APIView para importar productos desde archivo Excel"""
    permission_classes = [IsAuthenticated, HasEmpresaPermission]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        """Importa productos desde archivo Excel"""
        print("REQUEST.FILES:", request.FILES)  # Debug: ver qué archivos llegan
        archivo = request.FILES.get('file')  # Cambiado de 'archivo' a 'file'
        if not archivo:
            return Response({'error': 'No se proporcionó archivo'}, status=400)
        
        try:
            # Leer archivo Excel
            df = pd.read_excel(archivo)
            
            # Validar columnas requeridas
            columnas_requeridas = ['sku', 'nombre', 'precio_compra', 'precio_venta']
            for col in columnas_requeridas:
                if col not in df.columns:
                    return Response({'error': f'Columna requerida faltante: {col}'}, status=400)
            
            productos_creados = 0
            categorias_creadas = []
            almacenes_creados = []
            errores = []
            
            with transaction.atomic():
                for index, row in df.iterrows():
                    try:
                        # Validar datos básicos
                        if pd.isna(row['sku']) or not str(row['sku']).strip():
                            errores.append(f"Fila {index + 2}: SKU es requerido")
                            continue
                            
                        if pd.isna(row['nombre']) or not str(row['nombre']).strip():
                            errores.append(f"Fila {index + 2}: Nombre es requerido")
                            continue
                            
                        if pd.isna(row['precio_compra']) or row['precio_compra'] <= 0:
                            errores.append(f"Fila {index + 2}: Precio de compra debe ser mayor a 0")
                            continue
                            
                        if pd.isna(row['precio_venta']) or row['precio_venta'] <= 0:
                            errores.append(f"Fila {index + 2}: Precio de venta debe ser mayor a 0")
                            continue
                        
                        # Verificar si el SKU ya existe
                        if Producto.objects.filter(
                            empresa=request.user.empresa,
                            sku=row['sku']
                        ).exists():
                            errores.append(f"Fila {index + 2}: SKU '{row['sku']}' ya existe")
                            continue
                        
                        # Buscar o crear categoría si se proporciona
                        categoria = None
                        if 'categoria' in row and pd.notna(row['categoria']):
                            categoria, created = Categoria.objects.get_or_create(
                                empresa=request.user.empresa,
                                nombre=row['categoria']
                            )
                            if created and categoria.nombre not in categorias_creadas:
                                categorias_creadas.append(categoria.nombre)
                        
                        # Buscar o crear almacén si se proporciona
                        almacen = None
                        if 'almacen' in row and pd.notna(row['almacen']):
                            almacen, created = Almacen.objects.get_or_create(
                                empresa=request.user.empresa,
                                nombre=row['almacen'],
                                defaults={
                                    'direccion': f"Dirección automática para {row['almacen']}"
                                }
                            )
                            if created and almacen.nombre not in almacenes_creados:
                                almacenes_creados.append(almacen.nombre)
                        
                        # Crear producto SIN almacén primero para evitar creación automática de Stock
                        producto = Producto.objects.create(
                            empresa=request.user.empresa,
                            sku=row['sku'],
                            nombre=row['nombre'],
                            descripcion=row.get('descripcion', ''),
                            categoria=categoria,
                            # NO asignar almacen aquí para evitar creación automática de Stock
                            precio_compra=row['precio_compra'],
                            precio_venta=row['precio_venta'],
                            moneda=row.get('moneda', 'PEN'),
                            stock_minimo=row.get('stock_minimo', 0),
                            stock_maximo=row.get('stock_maximo', 0)
                        )
                        
                        # Ahora asignar el almacén manualmente SIN triggear el save()
                        if almacen:
                            producto.almacen = almacen
                            producto.save(update_fields=['almacen'])
                        
                        # Crear stock inicial si se proporciona
                        if 'stock_inicial' in row and pd.notna(row['stock_inicial']) and almacen:
                            try:
                                # Usar get_or_create para evitar duplicados
                                stock_obj, created = Stock.objects.get_or_create(
                                    empresa=request.user.empresa,
                                    producto=producto,
                                    almacen=almacen,
                                    defaults={'cantidad': row['stock_inicial']}
                                )
                                if not created:
                                    # Si ya existe, reemplazamos la cantidad (no sumamos)
                                    stock_obj.cantidad = float(row['stock_inicial'])
                                    stock_obj.save()
                                print(f"Stock creado/actualizado: {stock_obj.cantidad} para {producto.nombre}")
                                    
                            except Exception as stock_error:
                                print(f"Error al guardar stock: {stock_error}")
                                errores.append(f"Fila {index + 2}: Error en stock - {str(stock_error)}")
                        
                        # IMPORTANTE: Siempre actualizar el stock_total del producto al final
                        producto.actualizar_stock_total()
                        print(f"Producto '{producto.nombre}' creado con stock total: {producto.stock_total}")
                        
                        productos_creados += 1
                        
                    except Exception as e:
                        print(f"Error general en fila {index + 2}: {str(e)}")
                        errores.append(f"Fila {index + 2}: {str(e)}")
            
            return Response({
                'success': True,
                'productos_creados': productos_creados,
                'categorias_creadas': categorias_creadas,
                'almacenes_creados': almacenes_creados,
                'errores': errores
            })
            
        except Exception as e:
            return Response({'error': f'Error procesando archivo: {str(e)}'}, status=500)

def descargar_template(request):
    """Descarga template de Excel para importar productos"""
    # Crear workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template Productos"
    
    # Headers
    headers = [
        'sku',
        'nombre',
        'descripcion',
        'categoria',
        'almacen',
        'precio_compra',
        'precio_venta',
        'moneda',
        'stock_minimo',
        'stock_maximo',
        'stock_inicial'
    ]
    
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)
    
    # Datos de ejemplo
    ejemplos = [
        [
            'PROD001',
            'Producto de Ejemplo 1',
            'Descripción del producto 1',
            'Electrónicos',
            'Almacén Lima',
            100.00,
            150.00,
            'PEN',
            10,
            100,
            50
        ],
        [
            'PROD002',
            'Producto de Ejemplo 2',
            'Descripción del producto 2',
            'Ropa',
            'Almacén Arequipa',
            50.00,
            80.00,
            'USD',
            5,
            50,
            25
        ],
        [
            'PROD003',
            'Producto de Ejemplo 3',
            'Descripción del producto 3',
            'Hogar',
            'Almacén Principal',
            200.00,
            300.00,
            'PEN',
            20,
            200,
            100
        ]
    ]
    
    for row_num, ejemplo in enumerate(ejemplos, 2):
        for col, valor in enumerate(ejemplo, 1):
            ws.cell(row=row_num, column=col, value=valor)
    
    # Agregar instrucciones
    instrucciones_row = len(ejemplos) + 3
    ws.cell(row=instrucciones_row, column=1, value="INSTRUCCIONES:")
    ws.cell(row=instrucciones_row + 1, column=1, value="• Las categorías que no existan se crearán automáticamente")
    ws.cell(row=instrucciones_row + 2, column=1, value="• Los almacenes que no existan se crearán automáticamente")
    ws.cell(row=instrucciones_row + 3, column=1, value="• Los campos sku, nombre, precio_compra y precio_venta son obligatorios")
    ws.cell(row=instrucciones_row + 4, column=1, value="• La moneda puede ser 'PEN' o 'USD' (por defecto: PEN)")
    
    # Preparar respuesta
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="template_productos.xlsx"'
    
    wb.save(response)
    return response

class KardexViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar el Kardex (movimientos de inventario)"""
    
    serializer_class = MovimientoInventarioSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['producto', 'almacen', 'tipo_movimiento', 'tipo_documento']
    search_fields = ['producto__nombre', 'producto__sku', 'numero_documento', 'observaciones']
    ordering_fields = ['fecha', 'created_at']
    ordering = ['-fecha', '-id']
    
    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return MovimientoInventario.objects.filter(
            empresa=self.request.user.empresa
        ).select_related('producto', 'almacen')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return MovimientoInventarioCreateSerializer
        return MovimientoInventarioSerializer
    
    @action(detail=False, methods=['get'])
    def kardex_producto(self, request):
        """Obtiene el kardex filtrado específicamente por producto y almacén"""
        serializer = KardexSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        filters = {
            'empresa': request.user.empresa
        }
        
        # Aplicar filtros obligatorios
        if not serializer.validated_data.get('producto_id'):
            return Response(
                {'error': 'El producto_id es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not serializer.validated_data.get('almacen_id'):
            return Response(
                {'error': 'El almacen_id es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        filters['producto_id'] = serializer.validated_data['producto_id']
        filters['almacen_id'] = serializer.validated_data['almacen_id']
        
        queryset = MovimientoInventario.objects.filter(**filters)
        
        # Aplicar filtros opcionales de fecha
        if serializer.validated_data.get('fecha_inicio'):
            queryset = queryset.filter(fecha__gte=serializer.validated_data['fecha_inicio'])
        
        if serializer.validated_data.get('fecha_fin'):
            queryset = queryset.filter(fecha__lte=serializer.validated_data['fecha_fin'])
        
        # Ordenar por fecha y ID para mantener el orden cronológico
        queryset = queryset.order_by('fecha', 'id').select_related('producto', 'almacen')
        
        # Obtener información del producto y almacén
        try:
            producto = Producto.objects.get(
                id=serializer.validated_data['producto_id'],
                empresa=request.user.empresa
            )
            almacen = Almacen.objects.get(
                id=serializer.validated_data['almacen_id'],
                empresa=request.user.empresa
            )
        except (Producto.DoesNotExist, Almacen.DoesNotExist):
            return Response(
                {'error': 'Producto o almacén no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calcular saldo inicial
        saldo_inicial = {'cantidad': 0, 'costo_unitario': 0, 'costo_total': 0}
        
        if queryset.exists():
            primer_movimiento = queryset.first()
            
            # El saldo inicial se calcula restando el efecto del primer movimiento
            if primer_movimiento.cantidad_entrada > 0:
                saldo_inicial['cantidad'] = max(0, 
                    float(primer_movimiento.cantidad_saldo) - float(primer_movimiento.cantidad_entrada)
                )
                saldo_inicial['costo_total'] = max(0, 
                    float(primer_movimiento.costo_saldo) - float(primer_movimiento.costo_total_entrada)
                )
            elif primer_movimiento.cantidad_salida > 0:
                saldo_inicial['cantidad'] = (
                    float(primer_movimiento.cantidad_saldo) + float(primer_movimiento.cantidad_salida)
                )
                saldo_inicial['costo_total'] = (
                    float(primer_movimiento.costo_saldo) + float(primer_movimiento.costo_total_salida)
                )
            
            # Calcular costo unitario inicial
            if saldo_inicial['cantidad'] > 0:
                saldo_inicial['costo_unitario'] = saldo_inicial['costo_total'] / saldo_inicial['cantidad']
        
        # Serializar movimientos
        movimientos_serializer = MovimientoInventarioSerializer(queryset, many=True)
        
        return Response({
            'producto': {
                'id': producto.id,
                'sku': producto.sku,
                'nombre': producto.nombre
            },
            'almacen': {
                'id': almacen.id,
                'nombre': almacen.nombre
            },
            'saldo_inicial': saldo_inicial,
            'movimientos': movimientos_serializer.data,
            'total_movimientos': queryset.count()
        })
    
    @action(detail=False, methods=['get'])
    def resumen_kardex(self, request):
        """Obtiene el resumen del kardex por producto y almacén"""
        empresa = request.user.empresa
        
        # Obtener productos con movimientos
        productos_con_movimientos = MovimientoInventario.objects.filter(
            empresa=empresa
        ).values('producto', 'almacen').distinct()
        
        resumenes = []
        
        for item in productos_con_movimientos:
            producto_id = item['producto']
            almacen_id = item['almacen']
            
            try:
                producto = Producto.objects.get(id=producto_id)
                almacen = Almacen.objects.get(id=almacen_id)
            except (Producto.DoesNotExist, Almacen.DoesNotExist):
                continue
            
            # Obtener stock actual
            stock_info = MovimientoInventario.obtener_stock_actual(
                empresa, producto, almacen
            )
            
            # Obtener totales de entradas y salidas
            movimientos = MovimientoInventario.objects.filter(
                empresa=empresa,
                producto_id=producto_id,
                almacen_id=almacen_id
            )
            
            total_entradas = movimientos.aggregate(
                total=Sum('cantidad_entrada')
            )['total'] or Decimal('0')
            
            total_salidas = movimientos.aggregate(
                total=Sum('cantidad_salida')
            )['total'] or Decimal('0')
            
            ultimo_movimiento = movimientos.first()
            
            resumenes.append({
                'producto': producto,
                'almacen': almacen,
                'stock_actual': stock_info['cantidad'],
                'costo_total': stock_info['costo_total'],
                'costo_promedio': stock_info['costo_promedio'],
                'total_entradas': total_entradas,
                'total_salidas': total_salidas,
                'ultimo_movimiento': ultimo_movimiento.fecha if ultimo_movimiento else None
            })
        
        serializer = KardexResumenSerializer(resumenes, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def exportar_excel(self, request):
        """Exporta el kardex a Excel con la nueva estructura mejorada"""
        serializer = KardexSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        # Validar filtros obligatorios
        if not serializer.validated_data.get('producto_id'):
            return Response(
                {'error': 'El producto_id es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not serializer.validated_data.get('almacen_id'):
            return Response(
                {'error': 'El almacen_id es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        filters = {
            'empresa': request.user.empresa,
            'producto_id': serializer.validated_data['producto_id'],
            'almacen_id': serializer.validated_data['almacen_id']
        }
        
        queryset = MovimientoInventario.objects.filter(**filters)
        
        if serializer.validated_data.get('fecha_inicio'):
            queryset = queryset.filter(fecha__gte=serializer.validated_data['fecha_inicio'])
        
        if serializer.validated_data.get('fecha_fin'):
            queryset = queryset.filter(fecha__lte=serializer.validated_data['fecha_fin'])
        
        queryset = queryset.order_by('fecha', 'id').select_related('producto', 'almacen')
        
        # Obtener información del producto y almacén
        try:
            producto = Producto.objects.get(
                id=serializer.validated_data['producto_id'],
                empresa=request.user.empresa
            )
            almacen = Almacen.objects.get(
                id=serializer.validated_data['almacen_id'],
                empresa=request.user.empresa
            )
        except (Producto.DoesNotExist, Almacen.DoesNotExist):
            return Response(
                {'error': 'Producto o almacén no encontrado'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calcular saldo inicial
        saldo_inicial = {'cantidad': 0, 'costo_unitario': 0, 'costo_total': 0}
        
        if queryset.exists():
            primer_movimiento = queryset.first()
            
            if primer_movimiento.cantidad_entrada > 0:
                saldo_inicial['cantidad'] = max(0, 
                    float(primer_movimiento.cantidad_saldo) - float(primer_movimiento.cantidad_entrada)
                )
                saldo_inicial['costo_total'] = max(0, 
                    float(primer_movimiento.costo_saldo) - float(primer_movimiento.costo_total_entrada)
                )
            elif primer_movimiento.cantidad_salida > 0:
                saldo_inicial['cantidad'] = (
                    float(primer_movimiento.cantidad_saldo) + float(primer_movimiento.cantidad_salida)
                )
                saldo_inicial['costo_total'] = (
                    float(primer_movimiento.costo_saldo) + float(primer_movimiento.costo_total_salida)
                )
            
            if saldo_inicial['cantidad'] > 0:
                saldo_inicial['costo_unitario'] = saldo_inicial['costo_total'] / saldo_inicial['cantidad']
        
        # Crear workbook de Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Kardex"
        
        # Configurar estilos
        from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
        
        # Fuentes
        font_titulo = Font(name='Arial', size=14, bold=True)
        font_header = Font(name='Arial', size=11, bold=True, color='FFFFFF')
        font_subheader = Font(name='Arial', size=10, bold=True)
        font_datos = Font(name='Arial', size=10)
        font_saldo_inicial = Font(name='Arial', size=10, bold=True)
        
        # Rellenos de color
        fill_header = PatternFill(start_color='4F81BD', end_color='4F81BD', fill_type='solid')
        fill_entradas = PatternFill(start_color='C5D9F1', end_color='C5D9F1', fill_type='solid')
        fill_salidas = PatternFill(start_color='F2DCDB', end_color='F2DCDB', fill_type='solid')
        fill_saldos = PatternFill(start_color='E5E0EC', end_color='E5E0EC', fill_type='solid')
        fill_saldo_inicial = PatternFill(start_color='FFFF99', end_color='FFFF99', fill_type='solid')
        
        # Bordes
        border_thick = Border(
            left=Side(style='thick'),
            right=Side(style='thick'),
            top=Side(style='thick'),
            bottom=Side(style='thick')
        )
        border_thin = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Alineación
        align_center = Alignment(horizontal='center', vertical='center')
        align_right = Alignment(horizontal='right', vertical='center')
        
        # ENCABEZADO DEL REPORTE
        ws.merge_cells('A1:J1')
        ws['A1'] = 'KARDEX DE INVENTARIO'
        ws['A1'].font = font_titulo
        ws['A1'].alignment = align_center
        
        # Información del producto y almacén
        ws['A3'] = 'Producto:'
        ws['B3'] = f"{producto.sku} - {producto.nombre}"
        ws['A4'] = 'Almacén:'
        ws['B4'] = almacen.nombre
        ws['A5'] = 'Fecha de reporte:'
        ws['B5'] = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        # Rango de fechas si aplica
        if serializer.validated_data.get('fecha_inicio') and serializer.validated_data.get('fecha_fin'):
            ws['A6'] = 'Período:'
            ws['B6'] = f"{serializer.validated_data['fecha_inicio'].strftime('%d/%m/%Y')} al {serializer.validated_data['fecha_fin'].strftime('%d/%m/%Y')}"
            start_row = 8
        else:
            start_row = 7
        
        # HEADERS PRINCIPALES
        # Fila 1 de headers - FECHA (fusionar verticalmente)
        ws.merge_cells(f'A{start_row}:A{start_row+1}')
        ws[f'A{start_row}'] = 'FECHA'
        ws[f'A{start_row}'].font = font_header
        ws[f'A{start_row}'].fill = fill_header
        ws[f'A{start_row}'].alignment = align_center
        ws[f'A{start_row}'].border = border_thick
        
        # ENTRADAS (fusionar horizontalmente solo en la primera fila)
        ws.merge_cells(f'B{start_row}:D{start_row}')
        ws[f'B{start_row}'] = 'ENTRADAS'
        ws[f'B{start_row}'].font = font_header
        ws[f'B{start_row}'].fill = fill_entradas
        ws[f'B{start_row}'].alignment = align_center
        ws[f'B{start_row}'].border = border_thick
        
        # SALIDAS (fusionar horizontalmente solo en la primera fila)
        ws.merge_cells(f'E{start_row}:G{start_row}')
        ws[f'E{start_row}'] = 'SALIDAS'
        ws[f'E{start_row}'].font = font_header
        ws[f'E{start_row}'].fill = fill_salidas
        ws[f'E{start_row}'].alignment = align_center
        ws[f'E{start_row}'].border = border_thick
        
        # SALDOS (fusionar horizontalmente solo en la primera fila)
        ws.merge_cells(f'H{start_row}:J{start_row}')
        ws[f'H{start_row}'] = 'SALDOS'
        ws[f'H{start_row}'].font = font_header
        ws[f'H{start_row}'].fill = fill_saldos
        ws[f'H{start_row}'].alignment = align_center
        ws[f'H{start_row}'].border = border_thick
        
        # Fila 2 de headers (subheaders) - Solo las columnas no fusionadas
        # La columna A (FECHA) ya está fusionada, así que empezamos desde B
        subheaders_info = [
            # (columna, texto, color_fill)
            (2, 'CANTIDAD', fill_entradas),      # B
            (3, 'COSTO UNIT.', fill_entradas),   # C
            (4, 'COSTO TOTAL', fill_entradas),   # D
            (5, 'CANTIDAD', fill_salidas),       # E
            (6, 'COSTO UNIT.', fill_salidas),    # F
            (7, 'COSTO TOTAL', fill_salidas),    # G
            (8, 'CANTIDAD', fill_saldos),        # H
            (9, 'COSTO UNIT.', fill_saldos),     # I
            (10, 'COSTO TOTAL', fill_saldos),    # J
        ]
        
        for col_num, header_text, color_fill in subheaders_info:
            cell = ws.cell(row=start_row+1, column=col_num, value=header_text)
            cell.font = font_subheader
            cell.alignment = align_center
            cell.border = border_thin
            cell.fill = color_fill
        
        # SALDO INICIAL
        current_row = start_row + 2
        if saldo_inicial['cantidad'] > 0 or saldo_inicial['costo_total'] > 0:
            ws[f'A{current_row}'] = 'SALDO INICIAL'
            ws[f'A{current_row}'].font = font_saldo_inicial
            ws[f'A{current_row}'].fill = fill_saldo_inicial
            ws[f'A{current_row}'].alignment = align_center
            
            # Entradas vacías
            for col in range(2, 5):
                cell = ws.cell(row=current_row, column=col, value='-')
                cell.fill = fill_entradas
                cell.alignment = align_center
                cell.border = border_thin
            
            # Salidas vacías
            for col in range(5, 8):
                cell = ws.cell(row=current_row, column=col, value='-')
                cell.fill = fill_salidas
                cell.alignment = align_center
                cell.border = border_thin
            
            # Saldos iniciales
            ws[f'H{current_row}'] = f"{saldo_inicial['cantidad']:.2f}"
            ws[f'I{current_row}'] = f"$ {saldo_inicial['costo_unitario']:.2f}"
            ws[f'J{current_row}'] = f"$ {saldo_inicial['costo_total']:.2f}"
            
            for col in range(8, 11):
                cell = ws.cell(row=current_row, column=col)
                cell.font = font_saldo_inicial
                cell.fill = fill_saldos
                cell.alignment = align_right
                cell.border = border_thin
            
            current_row += 1
        
        # DATOS DE MOVIMIENTOS
        for movimiento in queryset:
            # Fecha y tipo de movimiento
            fecha_str = movimiento.fecha.strftime('%d/%m/%Y')
            if hasattr(movimiento, 'get_tipo_movimiento_display'):
                fecha_str += f"\n{movimiento.get_tipo_movimiento_display()}"
            if movimiento.numero_documento:
                fecha_str += f"\nDoc: {movimiento.numero_documento}"
            
            ws[f'A{current_row}'] = fecha_str
            ws[f'A{current_row}'].font = font_datos
            ws[f'A{current_row}'].alignment = align_center
            ws[f'A{current_row}'].border = border_thin
            
            # ENTRADAS
            if movimiento.cantidad_entrada > 0:
                ws[f'B{current_row}'] = f"{float(movimiento.cantidad_entrada):.2f}"
                ws[f'C{current_row}'] = f"$ {float(movimiento.costo_unitario):.2f}"
                ws[f'D{current_row}'] = f"$ {float(movimiento.costo_total_entrada):.2f}"
            else:
                ws[f'B{current_row}'] = '-'
                ws[f'C{current_row}'] = '-'
                ws[f'D{current_row}'] = '-'
            
            for col in range(2, 5):
                cell = ws.cell(row=current_row, column=col)
                cell.fill = fill_entradas
                cell.alignment = align_right if cell.value != '-' else align_center
                cell.border = border_thin
                cell.font = font_datos
            
            # SALIDAS
            if movimiento.cantidad_salida > 0:
                ws[f'E{current_row}'] = f"{float(movimiento.cantidad_salida):.2f}"
                ws[f'F{current_row}'] = f"$ {float(movimiento.costo_unitario):.2f}"
                ws[f'G{current_row}'] = f"$ {float(movimiento.costo_total_salida):.2f}"
            else:
                ws[f'E{current_row}'] = '-'
                ws[f'F{current_row}'] = '-'
                ws[f'G{current_row}'] = '-'
            
            for col in range(5, 8):
                cell = ws.cell(row=current_row, column=col)
                cell.fill = fill_salidas
                cell.alignment = align_right if cell.value != '-' else align_center
                cell.border = border_thin
                cell.font = font_datos
            
            # SALDOS
            ws[f'H{current_row}'] = f"{float(movimiento.cantidad_saldo):.2f}"
            ws[f'I{current_row}'] = f"$ {float(movimiento.costo_promedio):.2f}"
            ws[f'J{current_row}'] = f"$ {float(movimiento.costo_saldo):.2f}"
            
            for col in range(8, 11):
                cell = ws.cell(row=current_row, column=col)
                cell.fill = fill_saldos
                cell.alignment = align_right
                cell.border = border_thin
                cell.font = Font(name='Arial', size=10, bold=True)
            
            current_row += 1
        
        # Ajustar ancho de columnas
        column_widths = [20, 12, 12, 15, 12, 12, 15, 12, 12, 15]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width
        
        # Preparar respuesta
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        fecha_actual = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'Kardex_{producto.sku}_{almacen.nombre.replace(" ", "_")}_{fecha_actual}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        wb.save(response)
        return response
    
    @action(detail=False, methods=['post'])
    def ajuste_inventario(self, request):
        """Crea un ajuste de inventario (entrada o salida manual)"""
        data = request.data.copy()
        data['tipo_documento'] = 'ajuste'
        
        # Determinar tipo de movimiento basado en la cantidad
        cantidad_entrada = Decimal(str(data.get('cantidad_entrada', 0)))
        cantidad_salida = Decimal(str(data.get('cantidad_salida', 0)))
        
        if cantidad_entrada > 0:
            data['tipo_movimiento'] = 'ajuste_entrada'
        elif cantidad_salida > 0:
            data['tipo_movimiento'] = 'ajuste_salida'
        
        serializer = MovimientoInventarioCreateSerializer(
            data=data, 
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        movimiento = serializer.save()
        
        response_serializer = MovimientoInventarioSerializer(movimiento)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)