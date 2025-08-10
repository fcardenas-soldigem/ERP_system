from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.ventas.models import Venta, Cliente, OrdenVenta, DetalleVenta
from apps.compras.models import OrdenCompra, Proveedor, Compra
from apps.inventario.models.producto import Producto
from apps.inventario.models.stock import Stock
from apps.core.services.documento_service import DocumentoService
from django.db.models import Sum, Count, F, Q, ExpressionWrapper, DecimalField
from django.utils import timezone
from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from datetime import datetime, timedelta
import logging
from django.db.models.functions import TruncDate, ExtractMonth
from calendar import monthrange
from django.db.models import FloatField
from decimal import Decimal

logger = logging.getLogger(__name__)

def obtener_tipo_cambio_venta():
    """
    Obtiene el tipo de cambio del día para convertir USD a PEN
    Retorna el precio de venta (lo que usa el banco para vender dólares)
    """
    try:
        resultado = DocumentoService.consultar_tipo_cambio()
        if resultado.get('success') and resultado.get('data'):
            # Usamos el precio de "venta" porque es lo que cuesta comprar USD con PEN
            venta = resultado['data'].get('venta', 0)
            tipo_cambio = float(venta) if venta and float(venta) > 0 else 3.8
            
            if float(venta) <= 0:
                logger.warning(f"Tipo de cambio de API inválido ({venta}), usando valor por defecto: 3.8")
            else:
                logger.info(f"Tipo de cambio obtenido de API: {tipo_cambio}")
            
            return tipo_cambio
        else:
            logger.warning("No se pudo obtener tipo de cambio, usando valor por defecto")
            return 3.8  # Valor por defecto aproximado
    except Exception as e:
        logger.error(f"Error al obtener tipo de cambio: {e}")
        return 3.8  # Valor por defecto en caso de error

def convertir_a_pen(monto, moneda, tipo_cambio):
    """
    Convierte un monto a PEN según la moneda
    """
    if moneda == 'USD':
        return float(monto) * tipo_cambio
    else:  # PEN o cualquier otra
        return float(monto)

class DashboardResumen(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # LOG de depuración
            logger.info(f"Usuario autenticado: {request.user} (ID: {request.user.id})")
            empresa = getattr(request.user, 'empresa', None)
            logger.info(f"Empresa del usuario: {empresa} (ID: {getattr(empresa, 'id', None)})")
            
            if not empresa:
                return Response({"error": "Usuario sin empresa asignada"}, status=400)

            # Obtener el primer y último día del mes actual
            hoy = timezone.now()
            primer_dia_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if hoy.month == 12:
                ultimo_dia_mes = hoy.replace(year=hoy.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                ultimo_dia_mes = hoy.replace(month=hoy.month + 1, day=1) - timedelta(days=1)
            ultimo_dia_mes = ultimo_dia_mes.replace(hour=23, minute=59, second=59, microsecond=999999)

            logger.info(f"Rango de fechas: {primer_dia_mes} - {ultimo_dia_mes}")

            # Ventas del mes actual
            ventas = Venta.objects.filter(
                empresa=empresa,
                fecha_emision__range=(primer_dia_mes, ultimo_dia_mes),
                estado='pagado'
            )
            
            # Obtener tipo de cambio del día
            tipo_cambio = obtener_tipo_cambio_venta()
            
            # Calcular ventas totales convirtiendo USD a PEN
            ventas_totales = 0.0
            for venta in ventas:
                monto_en_pen = convertir_a_pen(venta.total, venta.moneda, tipo_cambio)
                ventas_totales += monto_en_pen
            
            logger.info(f"Ventas totales (convertidas a PEN): {ventas_totales}")

            # Calcular compras totales del período convirtiendo USD a PEN
            compras = Compra.objects.filter(
                empresa=empresa,
                fecha_emision__range=(primer_dia_mes, ultimo_dia_mes),
                estado='pagada'
            )
            
            compras_totales = 0.0
            for compra in compras:
                monto_en_pen = convertir_a_pen(compra.total, compra.moneda, tipo_cambio)
                compras_totales += monto_en_pen
            
            logger.info(f"Compras totales (convertidas a PEN): {compras_totales}")

            # Calcular utilidad bruta = Ventas - Compras (antes de impuestos)
            # Convertir ventas y compras a valores antes de IGV
            ventas_sin_igv = ventas_totales / 1.18
            compras_sin_igv = compras_totales / 1.18
            
            utilidad_bruta = ventas_sin_igv - compras_sin_igv
            logger.info(f"Ventas sin IGV: {ventas_sin_igv}")
            logger.info(f"Compras sin IGV: {compras_sin_igv}")
            logger.info(f"Utilidad bruta (antes de impuestos): {utilidad_bruta}")

            # La utilidad neta es la misma que la bruta ya que estamos trabajando antes de impuestos
            utilidad_neta = utilidad_bruta
            logger.info(f"Utilidad neta: {utilidad_neta}")

            # Calcular margen de utilidad basado en ventas sin IGV
            margen = (utilidad_neta / ventas_sin_igv * 100) if ventas_sin_igv > 0 else 0
            logger.info(f"Margen: {margen}")

            # Calcular IGV de ventas convirtiendo USD a PEN
            igv_ventas = 0.0
            for venta in ventas:
                igv_en_pen = convertir_a_pen(venta.igv, venta.moneda, tipo_cambio)
                igv_ventas += igv_en_pen
            logger.info(f"IGV ventas (convertido a PEN): {igv_ventas}")

            # Calcular IGV de compras convirtiendo USD a PEN
            igv_compras = 0.0
            for compra in compras:
                igv_en_pen = convertir_a_pen(compra.igv, compra.moneda, tipo_cambio)
                igv_compras += igv_en_pen
            logger.info(f"IGV compras (convertido a PEN): {igv_compras}")

            # Obtener datos de inventario
            productos_stock = Stock.objects.filter(
                producto__empresa=empresa
            ).aggregate(
                total_productos=Count('producto', distinct=True),
                total_cantidad=Sum('cantidad')
            )

            # Productos bajos en stock
            productos_bajo_stock = Producto.objects.filter(
                empresa=empresa,
                is_active=True,
                stock_total__lte=F('stock_minimo'),
                stock_total__gt=0
            ).count()

            response_data = {
                'ventas': {
                    'total': float(ventas_totales),
                    'cantidad': ventas.count(),
                },
                'compras': {
                    'total': float(compras_totales),
                    'cantidad': compras.count(),
                },
                'utilidad': {
                    'total': float(utilidad_neta),
                    'margen': round(float(margen), 2),
                    'utilidad_bruta': float(utilidad_bruta),
                    'impuestos': float(utilidad_bruta * 0.18),
                },
                'impuestos': {
                    'igv_ventas': float(igv_ventas),
                    'igv_compras': float(igv_compras),
                    'por_pagar': float(igv_ventas - igv_compras),
                },
                'inventario': {
                    'total_productos': productos_stock['total_productos'] or 0,
                    'total_cantidad': float(productos_stock['total_cantidad'] or 0),
                    'productos_bajo_stock': productos_bajo_stock,
                },
                'tipo_cambio': {
                    'valor': tipo_cambio,
                    'moneda_base': 'PEN',
                    'nota': 'Todas las cifras mostradas están en soles peruanos. Las ventas/compras en USD han sido convertidas usando el tipo de cambio del día.'
                }
            }

            logger.info("Respuesta del dashboard generada exitosamente")
            return Response(response_data)

        except Exception as e:
            logger.error(f"Error en DashboardResumen: {str(e)}", exc_info=True)
            return Response(
                {"error": "Error al generar el resumen del dashboard", "detail": str(e)},
                status=500
            )

def dashboard_resumen(request):
    # Lógica de tu vista
    return render(request, 'dashboard/resumen.html', {})

def home(request):
    return render(request, 'dashboard/home.html')

class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, days=30):
        fecha_fin = timezone.now()
        fecha_inicio = fecha_fin - timedelta(days=days)
        empresa = request.user.empresa
        
        # Obtener tipo de cambio del día
        tipo_cambio = obtener_tipo_cambio_venta()
        
        # Crear estructura de datos diarios
        labels = []
        ventas_data = []
        compras_data = []
        
        # Generar datos para cada día en el rango
        for i in range(days):
            fecha = (fecha_fin - timedelta(days=days-1-i)).date()
            labels.append(fecha.strftime('%d/%m'))
            
            # Obtener ventas del día
            ventas_dia = Venta.objects.filter(
                empresa=empresa,
                fecha_emision=fecha,
                estado='pagado'
            ).aggregate(total=Sum('total'))['total'] or 0
            
            # Convertir a PEN si es necesario
            ventas_pen = convertir_a_pen(ventas_dia, 'PEN', tipo_cambio)
            ventas_data.append(float(ventas_pen))
            
            # Obtener compras del día
            compras_dia = Compra.objects.filter(
                empresa=empresa,
                fecha_emision=fecha,
                estado='pagada'
            ).aggregate(total=Sum('total'))['total'] or 0
            
            # Convertir a PEN si es necesario
            compras_pen = convertir_a_pen(compras_dia, 'PEN', tipo_cambio)
            compras_data.append(float(compras_pen))

        return Response({
            'ventas': {
                'labels': labels,
                'data': ventas_data
            },
            'compras': {
                'labels': labels, 
                'data': compras_data
            },
            'tipo_cambio': tipo_cambio
        })

class DashboardResumenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa = request.user.empresa

        # Ventas históricas
        ventas = Venta.objects.filter(
            empresa=empresa,
            estado='pagado'
        )
        
        ventas_resumen = ventas.aggregate(
            total_ventas=Sum('total', output_field=FloatField()) or 0,
            cantidad=Count('numero'),
            total_igv=Sum('igv', output_field=FloatField()) or 0
        )

        # Compras históricas
        compras = Compra.objects.filter(
            empresa=empresa,
            estado='pagada'
        )
        
        compras_resumen = compras.aggregate(
            total_compras=Sum('total', output_field=FloatField()) or 0,
            cantidad=Count('numero'),
            total_igv=Sum('igv', output_field=FloatField()) or 0
        )

        # Productos en stock
        productos_stock = Stock.objects.filter(
            producto__empresa=empresa,
            cantidad__gt=0
        ).aggregate(
            total_productos=Count('producto', distinct=True),
            total_cantidad=Sum('cantidad') or 0
        )

        # Productos bajos en stock
        productos_bajo_stock = Producto.objects.filter(
            empresa=empresa,
            stock_total__lte=F('stock_minimo'),
            stock_total__gt=0
        ).count()

        # Calcular utilidad = Ventas - Compras (antes de impuestos)
        ventas_sin_igv = ventas_resumen['total_ventas'] / 1.18
        compras_sin_igv = compras_resumen['total_compras'] / 1.18
        
        # Calcular utilidad bruta
        utilidad_bruta = ventas_sin_igv - compras_sin_igv
        
        # La utilidad neta es la misma que la bruta ya que trabajamos antes de impuestos
        utilidad_neta = utilidad_bruta
        
        # Calcular margen basado en ventas sin IGV
        margen = (utilidad_neta / ventas_sin_igv * 100) if ventas_sin_igv > 0 else 0

        # Calcular IGV por pagar
        igv_por_pagar = ventas_resumen['total_igv'] - compras_resumen['total_igv']

        # Log para debug
        logger.warning(f"Ventas históricas encontradas: {ventas.count()}")
        logger.warning(f"Total ventas histórico: {ventas_resumen['total_ventas']}")
        logger.warning(f"Total IGV ventas: {ventas_resumen['total_igv']}")
        logger.warning(f"Total IGV compras: {compras_resumen['total_igv']}")

        return Response({
            'ventas': {
                'total': ventas_resumen['total_ventas'],
                'cantidad': ventas_resumen['cantidad'] or 0,
            },
            'compras': {
                'total': compras_resumen['total_compras'],
                'cantidad': compras_resumen['cantidad'] or 0,
            },
            'utilidad': {
                'total': utilidad_neta,
                'margen': round(margen, 2),
                'utilidad_bruta': utilidad_bruta,
                'impuestos': utilidad_bruta * 0.18,
            },
            'impuestos': {
                'igv_ventas': ventas_resumen['total_igv'],
                'igv_compras': compras_resumen['total_igv'],
                'por_pagar': igv_por_pagar,
            },
            'inventario': {
                'total_productos': productos_stock['total_productos'] or 0,
                'total_cantidad': productos_stock['total_cantidad'] or 0,
                'productos_bajo_stock': productos_bajo_stock
            }
        })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_stats(request):
    # Obtener fecha hace 30 días
    fecha_30_dias = datetime.now() - timedelta(days=30)
    empresa = request.user.empresa
    
    # Calcular estadísticas
    try:
        total_compras = Compra.objects.filter(
            empresa=empresa,
            fecha_emision__gte=fecha_30_dias
        ).aggregate(total=Sum('total'))['total'] or 0

        total_ventas = Venta.objects.filter(
            empresa=empresa,
            fecha_emision__gte=fecha_30_dias
        ).aggregate(total=Sum('total'))['total'] or 0

        return Response({
            'total_compras': float(total_compras),
            'total_ventas': float(total_ventas)
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)

class UtilityDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Obtener año y mes de los parámetros de consulta
        year = int(request.GET.get('year', datetime.now().year))
        month = int(request.GET.get('month', datetime.now().month))
        empresa = request.user.empresa
        
        # Calcular el primer y último día del mes
        _, last_day = monthrange(year, month)
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month, last_day, 23, 59, 59)
        
        # Calcular el primer y último día del mes anterior
        if month == 1:
            prev_month = 12
            prev_year = year - 1
        else:
            prev_month = month - 1
            prev_year = year
        
        _, prev_last_day = monthrange(prev_year, prev_month)
        prev_start_date = datetime(prev_year, prev_month, 1)
        prev_end_date = datetime(prev_year, prev_month, prev_last_day, 23, 59, 59)

        # Obtener ventas del mes actual
        ventas_mes = Venta.objects.filter(
            empresa=empresa,
            fecha_emision__range=(start_date, end_date),
            estado='pagado'
        ).aggregate(
            total=Sum('total', output_field=FloatField()) or 0
        )['total'] or 0

        # Obtener ventas del mes anterior
        ventas_mes_anterior = Venta.objects.filter(
            empresa=empresa,
            fecha_emision__range=(prev_start_date, prev_end_date),
            estado='pagado'
        ).aggregate(
            total=Sum('total', output_field=FloatField()) or 0
        )['total'] or 0

        # Obtener compras del mes actual
        compras_mes = Compra.objects.filter(
            empresa=empresa,
            fecha_emision__range=(start_date, end_date),
            estado='pagada'
        ).aggregate(
            total=Sum('total', output_field=FloatField()) or 0
        )['total'] or 0

        # Obtener compras del mes anterior
        compras_mes_anterior = Compra.objects.filter(
            empresa=empresa,
            fecha_emision__range=(prev_start_date, prev_end_date),
            estado='pagada'
        ).aggregate(
            total=Sum('total', output_field=FloatField()) or 0
        )['total'] or 0

        # Calcular utilidad (ventas - compras antes de IGV)
        utilidad_mes = (ventas_mes / 1.18) - (compras_mes / 1.18)
        utilidad_mes_anterior = (ventas_mes_anterior / 1.18) - (compras_mes_anterior / 1.18)

        # Calcular porcentajes de crecimiento
        def calcular_crecimiento(actual, anterior):
            if anterior == 0:
                return 0 if actual == 0 else 100
            return ((actual - anterior) / anterior) * 100

        # Obtener datos diarios para el gráfico
        dias_mes = []
        ventas_diarias = []
        compras_diarias = []
        utilidades_diarias = []
        
        for dia in range(1, last_day + 1):
            fecha_inicio = datetime(year, month, dia)
            fecha_fin = datetime(year, month, dia, 23, 59, 59)
            
            dias_mes.append(dia)
            
            ventas_dia = Venta.objects.filter(
                empresa=empresa,
                fecha_emision__range=(fecha_inicio, fecha_fin),
                estado='pagado'
            ).aggregate(
                total=Sum('total', output_field=FloatField()) or 0
            )['total'] or 0
            ventas_diarias.append(ventas_dia)
            
            compras_dia = Compra.objects.filter(
                empresa=empresa,
                fecha_emision__range=(fecha_inicio, fecha_fin),
                estado='pagada'
            ).aggregate(
                total=Sum('total', output_field=FloatField()) or 0
            )['total'] or 0
            compras_diarias.append(compras_dia)
            
            utilidades_diarias.append((ventas_dia / 1.18) - (compras_dia / 1.18))

        # Imprimir para debug
        logger.info(f"Ventas mes: {ventas_mes}")
        logger.info(f"Compras mes: {compras_mes}")
        logger.info(f"Utilidad mes: {utilidad_mes}")
        logger.info(f"Ventas diarias: {ventas_diarias}")
        logger.info(f"Compras diarias: {compras_diarias}")
        logger.info(f"Utilidades diarias: {utilidades_diarias}")

        return Response({
            'labels': dias_mes,
            'utilidades': utilidades_diarias,
            'ventas': ventas_diarias,
            'compras': compras_diarias
        })

class IGVDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return Response({"error": "Usuario sin empresa asignada"}, status=400)

        # Periodo por defecto: últimos 30 días
        hoy = timezone.now()
        hace_30_dias = hoy - timedelta(days=30)

        # Calcular IGV de ventas
        ventas = Venta.objects.filter(
            empresa=empresa,
            fecha_emision__gte=hace_30_dias,
            estado='pagado'
        )
        igv_ventas = sum(venta.igv or Decimal('0.0') for venta in ventas)

        # Calcular IGV de compras
        compras = Compra.objects.filter(
            empresa=empresa,
            fecha_emision__gte=hace_30_dias,
            estado='pagada'
        )
        igv_compras = sum(compra.igv or Decimal('0.0') for compra in compras)

        # IGV por pagar = IGV ventas - IGV compras
        igv_por_pagar = igv_ventas - igv_compras

        return Response({
            "igv_ventas": float(igv_ventas),
            "igv_compras": float(igv_compras),
            "igv_por_pagar": float(igv_por_pagar)
        })

class VentasAnualView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Obtiene datos de ventas por mes para un año específico"""
        year = int(request.GET.get('year', datetime.now().year))
        empresa = request.user.empresa
        
        # Obtener tipo de cambio del día
        tipo_cambio = obtener_tipo_cambio_venta()
        
        # Crear estructura de datos mensuales
        months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        
        ventas_data = []
        
        # Generar datos para cada mes del año
        for month in range(1, 13):
            # Calcular el primer y último día del mes
            _, last_day = monthrange(year, month)
            start_date = datetime(year, month, 1)
            end_date = datetime(year, month, last_day, 23, 59, 59)
            
            # Obtener ventas del mes
            ventas_mes = Venta.objects.filter(
                empresa=empresa,
                fecha_emision__range=(start_date, end_date),
                estado='pagado'
            )
            
            # Calcular total convirtiendo USD a PEN
            total_mes = 0.0
            for venta in ventas_mes:
                monto_en_pen = convertir_a_pen(venta.total, venta.moneda, tipo_cambio)
                total_mes += monto_en_pen
            
            ventas_data.append(float(total_mes))

        return Response({
            'labels': months,
            'data': ventas_data,
            'year': year,
            'tipo_cambio': tipo_cambio
        })

class ComprasAnualView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Obtiene datos de compras por mes para un año específico"""
        year = int(request.GET.get('year', datetime.now().year))
        empresa = request.user.empresa
        
        # Obtener tipo de cambio del día
        tipo_cambio = obtener_tipo_cambio_venta()
        
        # Crear estructura de datos mensuales
        months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        
        compras_data = []
        
        # Generar datos para cada mes del año
        for month in range(1, 13):
            # Calcular el primer y último día del mes
            _, last_day = monthrange(year, month)
            start_date = datetime(year, month, 1)
            end_date = datetime(year, month, last_day, 23, 59, 59)
            
            # Obtener compras del mes
            compras_mes = Compra.objects.filter(
                empresa=empresa,
                fecha_emision__range=(start_date, end_date),
                estado='pagada'
            )
            
            # Calcular total convirtiendo USD a PEN
            total_mes = 0.0
            for compra in compras_mes:
                monto_en_pen = convertir_a_pen(compra.total, compra.moneda, tipo_cambio)
                total_mes += monto_en_pen
            
            compras_data.append(float(total_mes))

        return Response({
            'labels': months,
            'data': compras_data,
            'year': year,
            'tipo_cambio': tipo_cambio
        })

class UtilidadAnualView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Obtiene datos de utilidad por mes para un año específico"""
        year = int(request.GET.get('year', datetime.now().year))
        empresa = request.user.empresa
        
        # Obtener tipo de cambio del día
        tipo_cambio = obtener_tipo_cambio_venta()
        
        # Crear estructura de datos mensuales
        months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
        
        utilidades_data = []
        ventas_data = []
        compras_data = []
        
        # Generar datos para cada mes del año
        for month in range(1, 13):
            # Calcular el primer y último día del mes
            _, last_day = monthrange(year, month)
            start_date = datetime(year, month, 1)
            end_date = datetime(year, month, last_day, 23, 59, 59)
            
            # Obtener ventas del mes
            ventas_mes = Venta.objects.filter(
                empresa=empresa,
                fecha_emision__range=(start_date, end_date),
                estado='pagado'
            )
            
            # Calcular total de ventas convirtiendo USD a PEN
            total_ventas_mes = 0.0
            for venta in ventas_mes:
                monto_en_pen = convertir_a_pen(venta.total, venta.moneda, tipo_cambio)
                total_ventas_mes += monto_en_pen
            
            # Obtener compras del mes
            compras_mes = Compra.objects.filter(
                empresa=empresa,
                fecha_emision__range=(start_date, end_date),
                estado='pagada'
            )
            
            # Calcular total de compras convirtiendo USD a PEN
            total_compras_mes = 0.0
            for compra in compras_mes:
                monto_en_pen = convertir_a_pen(compra.total, compra.moneda, tipo_cambio)
                total_compras_mes += monto_en_pen
            
            # Calcular utilidad (ventas - compras antes de IGV)
            ventas_sin_igv = total_ventas_mes / 1.18
            compras_sin_igv = total_compras_mes / 1.18
            utilidad_mes = ventas_sin_igv - compras_sin_igv
            
            utilidades_data.append(float(utilidad_mes))
            ventas_data.append(float(total_ventas_mes))
            compras_data.append(float(total_compras_mes))

        return Response({
            'labels': months,
            'utilidades': utilidades_data,
            'ventas': ventas_data,
            'compras': compras_data,
            'year': year,
            'tipo_cambio': tipo_cambio
        })

class VentasMensualView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Obtiene datos de ventas por día para un mes específico"""
        year = int(request.GET.get('year', datetime.now().year))
        month = int(request.GET.get('month', datetime.now().month))
        empresa = request.user.empresa
        
        # Obtener tipo de cambio del día
        tipo_cambio = obtener_tipo_cambio_venta()
        
        # Calcular el primer y último día del mes
        _, last_day = monthrange(year, month)
        
        labels = []
        ventas_data = []
        
        # Generar datos para cada día del mes
        for day in range(1, last_day + 1):
            fecha = datetime(year, month, day).date()
            labels.append(f"{day:02d}")
            
            # Obtener ventas del día
            ventas_dia = Venta.objects.filter(
                empresa=empresa,
                fecha_emision=fecha,
                estado='pagado'
            )
            
            # Calcular total convirtiendo USD a PEN
            total_dia = 0.0
            for venta in ventas_dia:
                monto_en_pen = convertir_a_pen(venta.total, venta.moneda, tipo_cambio)
                total_dia += monto_en_pen
                
            ventas_data.append(float(total_dia))

        return Response({
            'labels': labels,
            'data': ventas_data,
            'year': year,
            'month': month,
            'tipo_cambio': tipo_cambio
        })