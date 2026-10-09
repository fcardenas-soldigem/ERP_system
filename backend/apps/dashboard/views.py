from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.ventas.models import Venta, Cliente, OrdenVenta, DetalleVenta
from apps.compras.models import OrdenCompra, Proveedor, Compra
from apps.inventario.models.producto import Producto
from apps.inventario.models.stock import Stock
from apps.core.services.documento_service import DocumentoService
from apps.core.services.tipo_cambio import desglose_pen, get_tc_actual
from django.core.cache import cache
from django.db.models import Sum, Count, F, Q, ExpressionWrapper, DecimalField, Case, When, Value
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


def _pen_expr(fallback_tc, campo='total'):
    """
    Expresión SQL que valoriza un documento a PEN usando SU tipo_cambio guardado
    (TC histórico de su fecha_emision). Si falta: PEN→×1, USD→×fallback_tc.
    Para usar en annotate()/aggregate() y agrupar en la propia BD.
    """
    return Case(
        When(tipo_cambio__isnull=False, then=F(campo) * F('tipo_cambio')),
        When(moneda='PEN', then=F(campo)),
        default=F(campo) * Value(fallback_tc),
        output_field=DecimalField(max_digits=18, decimal_places=4),
    )


def _total_pen(qs, campo='total', fallback_tc=None):
    """Total consolidado a PEN con el TC por documento."""
    return desglose_pen(qs, campo, fallback_tc=fallback_tc)['total_pen']

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

            cache_key = f'dashboard_mes_{empresa.id}'
            cached = cache.get(cache_key)
            if cached:
                return Response(cached)

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
            
            # TC de fallback SOLO para documentos sin tipo_cambio guardado.
            # Las cifras usan el TC histórico guardado en cada documento.
            fallback_tc = get_tc_actual(empresa)

            # Ventas del mes consolidadas a PEN (TC por documento) + desglose
            ventas_desglose = desglose_pen(ventas, 'total', fallback_tc=fallback_tc)
            ventas_totales = ventas_desglose['total_pen']
            logger.info(f"Ventas totales (PEN, TC por documento): {ventas_totales}")

            # Compras del mes consolidadas a PEN
            compras = Compra.objects.filter(
                empresa=empresa,
                fecha_emision__range=(primer_dia_mes, ultimo_dia_mes),
                estado='pagada'
            )
            compras_desglose = desglose_pen(compras, 'total', fallback_tc=fallback_tc)
            compras_totales = compras_desglose['total_pen']
            logger.info(f"Compras totales (PEN, TC por documento): {compras_totales}")

            tipo_cambio = fallback_tc  # compat: valor mostrado como TC de referencia

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

            # IGV consolidado a PEN (TC por documento)
            igv_ventas = _total_pen(ventas, 'igv', fallback_tc)
            igv_compras = _total_pen(compras, 'igv', fallback_tc)
            logger.info(f"IGV ventas/compras (PEN): {igv_ventas} / {igv_compras}")

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

            # Cuentas por cobrar: ventas pendientes de pago (PEN, TC por documento)
            ventas_pendientes = Venta.objects.filter(empresa=empresa, estado='pendiente')
            por_cobrar = _total_pen(ventas_pendientes, 'total', fallback_tc)

            # Cuentas por pagar: compras pendientes de pago
            compras_pendientes = Compra.objects.filter(empresa=empresa, estado='pendiente')
            por_pagar = _total_pen(compras_pendientes, 'total', fallback_tc)

            # Compras en borrador (no contadas en la utilidad — advertencia)
            compras_borrador = Compra.objects.filter(empresa=empresa, estado='borrador')
            compras_borrador_count = compras_borrador.count()
            compras_borrador_total = _total_pen(compras_borrador, 'total', fallback_tc)

            # F4 #13 — Alertas operativas/comerciales.
            from apps.cotizaciones.models import Cotizacion
            limite_seguimiento = timezone.now().date() - timedelta(days=7)
            cotizaciones_sin_respuesta = Cotizacion.objects.filter(
                empresa=empresa, estado='enviada', fecha_emision__lt=limite_seguimiento,
            ).count()
            # Solo ventas CON historial operativo (H3/punto 10): evita falsos
            # positivos en ventas históricas sin timeline.
            ventas_con_historial = Venta.objects.filter(
                empresa=empresa, historial_operativo__isnull=False,
            ).distinct()
            ventas_fuera_sla = sum(
                1 for v in ventas_con_historial if v.estado_sla_operativo == 'vencido'
            )

            response_data = {
                'ventas': {
                    'total': float(ventas_totales),
                    'cantidad': ventas.count(),
                    'desglose': ventas_desglose,
                },
                'compras': {
                    'total': float(compras_totales),
                    'cantidad': compras.count(),
                    'desglose': compras_desglose,
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
                'cuentas': {
                    'por_cobrar': float(por_cobrar),
                    'por_pagar': float(por_pagar),
                    'ventas_pendientes_count': ventas_pendientes.count(),
                    'compras_pendientes_count': compras_pendientes.count(),
                    'compras_borrador_count': compras_borrador_count,
                    'compras_borrador_total': float(compras_borrador_total),
                },
                'inventario': {
                    'total_productos': productos_stock['total_productos'] or 0,
                    'total_cantidad': float(productos_stock['total_cantidad'] or 0),
                    'productos_bajo_stock': productos_bajo_stock,
                },
                'alertas': {
                    'cotizaciones_sin_respuesta': cotizaciones_sin_respuesta,
                    'ventas_fuera_sla': ventas_fuera_sla,
                },
                'tipo_cambio': {
                    'valor': tipo_cambio,
                    'moneda_base': 'PEN',
                    'nota': 'Cifras en soles. Cada documento en USD se valoriza con el tipo de cambio SBS de su fecha de emisión (histórico), no con el de hoy.'
                }
            }

            logger.info("Respuesta del dashboard generada exitosamente")
            cache.set(cache_key, response_data, 120)
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
        empresa = request.user.empresa
        cache_key = f'dashboard_stats_{empresa.id}_{days}'
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        fecha_fin = timezone.now()
        fecha_inicio = fecha_fin - timedelta(days=days)

        # TC de fallback; las cifras usan el TC guardado por documento.
        fallback_tc = get_tc_actual(empresa)
        tipo_cambio = float(fallback_tc)

        fecha_inicio_date = fecha_inicio.date()
        fecha_fin_date = fecha_fin.date()

        # Agrupar por fecha en la BD valorizando cada documento a PEN con su TC
        ventas_por_fecha = {
            r['fecha_emision']: float(r['t'] or 0)
            for r in Venta.objects.filter(
                empresa=empresa,
                fecha_emision__range=(fecha_inicio_date, fecha_fin_date),
                estado='pagado',
            ).values('fecha_emision').annotate(t=Sum(_pen_expr(fallback_tc)))
        }
        compras_por_fecha = {
            r['fecha_emision']: float(r['t'] or 0)
            for r in Compra.objects.filter(
                empresa=empresa,
                fecha_emision__range=(fecha_inicio_date, fecha_fin_date),
                estado='pagada',
            ).values('fecha_emision').annotate(t=Sum(_pen_expr(fallback_tc)))
        }

        labels = []
        ventas_data = []
        compras_data = []

        for i in range(days):
            fecha = (fecha_fin - timedelta(days=days - 1 - i)).date()
            labels.append(fecha.strftime('%d/%m'))
            ventas_data.append(round(ventas_por_fecha.get(fecha, 0.0), 2))
            compras_data.append(round(compras_por_fecha.get(fecha, 0.0), 2))

        result = {
            'ventas': {'labels': labels, 'data': ventas_data},
            'compras': {'labels': labels, 'data': compras_data},
            'tipo_cambio': tipo_cambio,
        }
        cache.set(cache_key, result, 120)
        return Response(result)

class DashboardResumenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa = request.user.empresa
        cache_key = f'dashboard_historico_{empresa.id}'
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        fallback_tc = get_tc_actual(empresa)
        tipo_cambio = float(fallback_tc)

        # Ventas históricas — consolidadas con el TC guardado por documento
        ventas = Venta.objects.filter(empresa=empresa, estado='pagado')
        ventas_desglose = desglose_pen(ventas, 'total', fallback_tc=fallback_tc)
        total_ventas = ventas_desglose['total_pen']
        total_igv_ventas = _total_pen(ventas, 'igv', fallback_tc)
        cantidad_ventas = ventas.count()

        # Compras históricas
        compras = Compra.objects.filter(empresa=empresa, estado='pagada')
        compras_desglose = desglose_pen(compras, 'total', fallback_tc=fallback_tc)
        total_compras = compras_desglose['total_pen']
        total_igv_compras = _total_pen(compras, 'igv', fallback_tc)
        cantidad_compras = compras.count()

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

        ventas_sin_igv = total_ventas / 1.18
        compras_sin_igv = total_compras / 1.18
        utilidad_bruta = ventas_sin_igv - compras_sin_igv
        margen = (utilidad_bruta / ventas_sin_igv * 100) if ventas_sin_igv > 0 else 0
        igv_por_pagar = total_igv_ventas - total_igv_compras

        # Cuentas por cobrar / pagar reales (pendientes de pago)
        ventas_pendientes_h = Venta.objects.filter(empresa=empresa, estado='pendiente')
        por_cobrar_h = float(_total_pen(ventas_pendientes_h, 'total', fallback_tc))
        compras_pendientes_h = Compra.objects.filter(empresa=empresa, estado='pendiente')
        por_pagar_h = float(_total_pen(compras_pendientes_h, 'total', fallback_tc))
        compras_borrador_h = Compra.objects.filter(empresa=empresa, estado='borrador')
        compras_borrador_count_h = compras_borrador_h.count()
        compras_borrador_total_h = float(_total_pen(compras_borrador_h, 'total', fallback_tc))

        logger.info('DashboardResumenView — ventas=%s compras=%s tc=%s', total_ventas, total_compras, tipo_cambio)

        payload = {
            'ventas': {'total': total_ventas, 'cantidad': cantidad_ventas, 'desglose': ventas_desglose},
            'compras': {'total': total_compras, 'cantidad': cantidad_compras, 'desglose': compras_desglose},
            'utilidad': {
                'total': utilidad_bruta,
                'margen': round(margen, 2),
                'utilidad_bruta': utilidad_bruta,
                'impuestos': utilidad_bruta * 0.18,
            },
            'impuestos': {
                'igv_ventas': total_igv_ventas,
                'igv_compras': total_igv_compras,
                'por_pagar': igv_por_pagar,
            },
            'cuentas': {
                'por_cobrar': por_cobrar_h,
                'por_pagar': por_pagar_h,
                'ventas_pendientes_count': ventas_pendientes_h.count(),
                'compras_pendientes_count': compras_pendientes_h.count(),
                'compras_borrador_count': compras_borrador_count_h,
                'compras_borrador_total': compras_borrador_total_h,
            },
            'inventario': {
                'total_productos': productos_stock['total_productos'] or 0,
                'total_cantidad': productos_stock['total_cantidad'] or 0,
                'productos_bajo_stock': productos_bajo_stock,
            },
            'tipo_cambio': {'valor': tipo_cambio, 'moneda_base': 'PEN'},
        }
        cache.set(cache_key, payload, 120)
        return Response(payload)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_stats(request):
    empresa = request.user.empresa
    cache_key = f'dashboard_simple_stats_{empresa.id}'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    fecha_30_dias = datetime.now() - timedelta(days=30)
    try:
        fallback_tc = get_tc_actual(empresa)
        total_compras = _total_pen(
            Compra.objects.filter(empresa=empresa, fecha_emision__gte=fecha_30_dias),
            'total', fallback_tc,
        )
        total_ventas = _total_pen(
            Venta.objects.filter(empresa=empresa, fecha_emision__gte=fecha_30_dias),
            'total', fallback_tc,
        )

        data = {
            'total_compras': float(total_compras),
            'total_ventas': float(total_ventas)
        }
        cache.set(cache_key, data, 120)
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

class UtilityDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return Response({'error': 'Usuario sin empresa asignada'}, status=400)

        try:
            # Obtener año y mes de los parámetros de consulta
            year = int(request.GET.get('year', datetime.now().year))
            month = int(request.GET.get('month', datetime.now().month))

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

            # TC de fallback; las cifras usan el TC guardado por documento.
            fallback_tc = get_tc_actual(empresa)
            tipo_cambio = float(fallback_tc)

            ventas_mes = _total_pen(Venta.objects.filter(empresa=empresa, fecha_emision__range=(start_date, end_date), estado='pagado'), 'total', fallback_tc)
            ventas_mes_anterior = _total_pen(Venta.objects.filter(empresa=empresa, fecha_emision__range=(prev_start_date, prev_end_date), estado='pagado'), 'total', fallback_tc)
            compras_mes = _total_pen(Compra.objects.filter(empresa=empresa, fecha_emision__range=(start_date, end_date), estado='pagada'), 'total', fallback_tc)
            compras_mes_anterior = _total_pen(Compra.objects.filter(empresa=empresa, fecha_emision__range=(prev_start_date, prev_end_date), estado='pagada'), 'total', fallback_tc)

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

            # Agrupar por día en la BD valorizando cada documento con su TC
            ventas_por_dia = {}
            for r in Venta.objects.filter(
                empresa=empresa, fecha_emision__range=(start_date, end_date), estado='pagado',
            ).values('fecha_emision').annotate(t=Sum(_pen_expr(fallback_tc))):
                f = r['fecha_emision']
                d = f.day if hasattr(f, 'day') else f
                ventas_por_dia[d] = ventas_por_dia.get(d, 0.0) + float(r['t'] or 0)

            compras_por_dia = {}
            for r in Compra.objects.filter(
                empresa=empresa, fecha_emision__range=(start_date, end_date), estado='pagada',
            ).values('fecha_emision').annotate(t=Sum(_pen_expr(fallback_tc))):
                f = r['fecha_emision']
                d = f.day if hasattr(f, 'day') else f
                compras_por_dia[d] = compras_por_dia.get(d, 0.0) + float(r['t'] or 0)

            for dia in range(1, last_day + 1):
                dias_mes.append(dia)
                v_dia = ventas_por_dia.get(dia, 0.0)
                c_dia = compras_por_dia.get(dia, 0.0)
                ventas_diarias.append(round(v_dia, 2))
                compras_diarias.append(round(c_dia, 2))
                utilidades_diarias.append(round((v_dia / 1.18) - (c_dia / 1.18), 2))

            logger.info('UtilityDashboardView — ventas=%s compras=%s utilidad=%s', ventas_mes, compras_mes, utilidad_mes)

            return Response({
                'labels': dias_mes,
                'utilidades': utilidades_diarias,
                'ventas': ventas_diarias,
                'compras': compras_diarias,
            })

        except Exception as e:
            logger.error('Error en UtilityDashboardView: %s', e, exc_info=True)
            return Response(
                {'error': 'Error al generar el dashboard de utilidad', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class IGVDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return Response({"error": "Usuario sin empresa asignada"}, status=400)

        # Periodo por defecto: últimos 30 días
        hoy = timezone.now()
        hace_30_dias = hoy - timedelta(days=30)

        fallback_tc = get_tc_actual(empresa)
        # IGV consolidado a PEN (TC por documento)
        ventas = Venta.objects.filter(
            empresa=empresa,
            fecha_emision__gte=hace_30_dias,
            estado='pagado'
        )
        igv_ventas = _total_pen(ventas, 'igv', fallback_tc)

        compras = Compra.objects.filter(
            empresa=empresa,
            fecha_emision__gte=hace_30_dias,
            estado='pagada'
        )
        igv_compras = _total_pen(compras, 'igv', fallback_tc)

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

        fallback_tc = get_tc_actual(empresa)
        tipo_cambio = float(fallback_tc)

        months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

        # Agrupar por mes en la BD, valorizando cada venta con su TC histórico
        por_mes = {
            r['m']: float(r['t'] or 0)
            for r in Venta.objects.filter(
                empresa=empresa, fecha_emision__year=year, estado='pagado',
            ).annotate(m=ExtractMonth('fecha_emision')).values('m').annotate(t=Sum(_pen_expr(fallback_tc)))
        }
        ventas_data = [por_mes.get(m, 0.0) for m in range(1, 13)]

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

        fallback_tc = get_tc_actual(empresa)
        tipo_cambio = float(fallback_tc)

        months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

        por_mes = {
            r['m']: float(r['t'] or 0)
            for r in Compra.objects.filter(
                empresa=empresa, fecha_emision__year=year, estado='pagada',
            ).annotate(m=ExtractMonth('fecha_emision')).values('m').annotate(t=Sum(_pen_expr(fallback_tc)))
        }
        compras_data = [por_mes.get(m, 0.0) for m in range(1, 13)]

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

        fallback_tc = get_tc_actual(empresa)
        tipo_cambio = float(fallback_tc)

        months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

        ventas_por_mes = {
            r['m']: float(r['t'] or 0)
            for r in Venta.objects.filter(
                empresa=empresa, fecha_emision__year=year, estado='pagado',
            ).annotate(m=ExtractMonth('fecha_emision')).values('m').annotate(t=Sum(_pen_expr(fallback_tc)))
        }
        compras_por_mes = {
            r['m']: float(r['t'] or 0)
            for r in Compra.objects.filter(
                empresa=empresa, fecha_emision__year=year, estado='pagada',
            ).annotate(m=ExtractMonth('fecha_emision')).values('m').annotate(t=Sum(_pen_expr(fallback_tc)))
        }

        ventas_data = [ventas_por_mes.get(m, 0.0) for m in range(1, 13)]
        compras_data = [compras_por_mes.get(m, 0.0) for m in range(1, 13)]
        utilidades_data = [round((v / 1.18) - (c / 1.18), 2) for v, c in zip(ventas_data, compras_data)]

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

        fallback_tc = get_tc_actual(empresa)
        tipo_cambio = float(fallback_tc)

        _, last_day = monthrange(year, month)

        # Agrupar por día en la BD valorizando cada venta con su TC histórico
        por_dia = {}
        for r in Venta.objects.filter(
            empresa=empresa, fecha_emision__year=year, fecha_emision__month=month, estado='pagado',
        ).values('fecha_emision').annotate(t=Sum(_pen_expr(fallback_tc))):
            f = r['fecha_emision']
            por_dia[f.day if hasattr(f, 'day') else f] = float(r['t'] or 0)

        labels = [f"{day:02d}" for day in range(1, last_day + 1)]
        ventas_data = [por_dia.get(day, 0.0) for day in range(1, last_day + 1)]

        return Response({
            'labels': labels,
            'data': ventas_data,
            'year': year,
            'month': month,
            'tipo_cambio': tipo_cambio
        })