"""
Views del módulo de Finanzas.

- FinanzasDashboardView: endpoint único de KPIs financieros (existente).
- CategoriaGastoViewSet: CRUD de categorías de gastos.
- GastoOperativoViewSet: CRUD + resumen de gastos operativos.
- GastoRecurrenteViewSet: CRUD + acción para generar gastos del mes.
"""

import logging
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Sum, DecimalField
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CategoriaGasto, GastoOperativo, GastoRecurrente
from .serializers import (
    CategoriaGastoSerializer,
    GastoOperativoSerializer,
    GastoRecurrenteSerializer,
)
from .services import FinanzasService

logger = logging.getLogger(__name__)

CACHE_TTL = 5 * 60  # 5 minutos


# ──────────────────────────────────────────────────────────────────────────────
# DASHBOARD EXISTENTE
# ──────────────────────────────────────────────────────────────────────────────

class FinanzasDashboardView(APIView):
    """
    GET /api/finanzas/dashboard/
    Params:
      ?periodo=mes|semana|trimestre  (default: mes)
      ?fecha_inicio=YYYY-MM-DD       (override manual)
      ?fecha_fin=YYYY-MM-DD          (override manual)

    Retorna el JSON completo de KPIs financieros para el período.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return Response({'error': 'Usuario sin empresa asignada'}, status=400)

        # ── Determinar rango de fechas ─────────────────────────────────────
        periodo = request.query_params.get('periodo', 'mes')
        hoy = date.today()

        if request.query_params.get('fecha_inicio') and request.query_params.get('fecha_fin'):
            try:
                fecha_inicio = date.fromisoformat(request.query_params['fecha_inicio'])
                fecha_fin    = date.fromisoformat(request.query_params['fecha_fin'])
            except ValueError:
                return Response({'error': 'Fechas inválidas. Usar formato YYYY-MM-DD.'}, status=400)
        elif periodo == 'semana':
            fecha_inicio = hoy - timedelta(days=hoy.weekday())  # Lunes
            fecha_fin    = hoy
        elif periodo == 'trimestre':
            mes_inicio   = ((hoy.month - 1) // 3) * 3 + 1
            fecha_inicio = hoy.replace(month=mes_inicio, day=1)
            _, ultimo_dia = monthrange(hoy.year, mes_inicio + 2)
            fecha_fin    = hoy.replace(month=mes_inicio + 2, day=ultimo_dia)
        else:  # mes (default)
            fecha_inicio = hoy.replace(day=1)
            _, ultimo_dia = monthrange(hoy.year, hoy.month)
            fecha_fin    = hoy.replace(day=ultimo_dia)

        # ── Cache key por empresa + período ───────────────────────────────
        cache_key = (
            f'finanzas:{empresa.id}:{fecha_inicio.isoformat()}:{fecha_fin.isoformat()}'
        )
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        # ── Calcular todos los KPIs ────────────────────────────────────────
        try:
            tc = getattr(empresa, 'tipo_cambio_usd', None) or Decimal('3.70')
            svc = FinanzasService(empresa, fecha_inicio, fecha_fin, tipo_cambio_usd=tc)

            flujo                 = svc.calcular_flujo_caja()
            rentabilidad          = svc.calcular_rentabilidad()
            cxc                   = svc.calcular_cuentas_cobrar()
            cxp                   = svc.calcular_cuentas_pagar()
            crecimiento           = svc.calcular_crecimiento()
            obligaciones_fiscales = svc.calcular_obligaciones_fiscales()
            avanzados    = svc.calcular_avanzados(cxc=cxc, cxp=cxp, flujo=flujo, rent=rentabilidad)
            semaforo     = svc.calcular_semaforo(flujo, rentabilidad, cxc, cxp)

            payload = {
                'meta': {
                    'empresa_id':     empresa.id,
                    'periodo':        periodo,
                    'fecha_inicio':   fecha_inicio.isoformat(),
                    'fecha_fin':      fecha_fin.isoformat(),
                    'generado_en':    hoy.isoformat(),
                    'moneda_base':    'PEN',
                    'tipo_cambio_usd': float(tc),
                    'nota_moneda':    f'Todos los montos están en soles (PEN). Las ventas/compras en USD se convirtieron al TC configurado S/{float(tc):.2f}.',
                },
                'semaforo':             semaforo,
                'obligaciones_fiscales': obligaciones_fiscales,
                'flujo_caja':           flujo,
                'rentabilidad':         rentabilidad,
                'cuentas_cobrar':       cxc,
                'cuentas_pagar':        cxp,
                'crecimiento':          crecimiento,
                'avanzados':            avanzados,
            }

            cache.set(cache_key, payload, CACHE_TTL)
            return Response(payload)

        except Exception as e:
            logger.error('Error calculando KPIs financieros empresa=%s: %s', empresa.id, e, exc_info=True)
            return Response(
                {'error': 'No se pudieron calcular los indicadores financieros.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ──────────────────────────────────────────────────────────────────────────────
# GASTOS OPERATIVOS — ViewSets
# ──────────────────────────────────────────────────────────────────────────────

class CategoriaGastoViewSet(viewsets.ModelViewSet):
    """
    CRUD de categorías de gastos. Filtradas siempre por empresa del usuario.
    """
    serializer_class = CategoriaGastoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        empresa = getattr(self.request.user, 'empresa', None)
        if not empresa:
            return CategoriaGasto.objects.none()
        qs = CategoriaGasto.objects.filter(empresa=empresa)
        # Filtro opcional: solo activas
        solo_activas = self.request.query_params.get('activo')
        if solo_activas is not None:
            qs = qs.filter(activo=solo_activas.lower() in ('true', '1', 'yes'))
        return qs

    def perform_create(self, serializer):
        empresa = getattr(self.request.user, 'empresa', None)
        if not empresa:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('Usuario sin empresa asignada.')
        serializer.save(empresa=empresa)


class GastoOperativoViewSet(viewsets.ModelViewSet):
    """
    CRUD de gastos operativos con filtros por fecha, categoría y estado.

    Filtros disponibles (query params):
      ?fecha_inicio=YYYY-MM-DD
      ?fecha_fin=YYYY-MM-DD
      ?categoria=<id>
      ?estado=pagado|pendiente|programado

    Acciones extra:
      GET  /api/finanzas/gastos/resumen/?fecha=YYYY-MM
    """
    serializer_class = GastoOperativoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        empresa = getattr(self.request.user, 'empresa', None)
        if not empresa:
            return GastoOperativo.objects.none()

        qs = GastoOperativo.objects.filter(empresa=empresa).select_related('categoria')

        fecha_inicio = self.request.query_params.get('fecha_inicio')
        fecha_fin    = self.request.query_params.get('fecha_fin')
        categoria    = self.request.query_params.get('categoria')
        estado       = self.request.query_params.get('estado')

        if fecha_inicio:
            try:
                qs = qs.filter(fecha__gte=date.fromisoformat(fecha_inicio))
            except ValueError:
                pass
        if fecha_fin:
            try:
                qs = qs.filter(fecha__lte=date.fromisoformat(fecha_fin))
            except ValueError:
                pass
        if categoria:
            qs = qs.filter(categoria_id=categoria)
        if estado:
            qs = qs.filter(estado=estado)

        return qs

    def perform_create(self, serializer):
        empresa = getattr(self.request.user, 'empresa', None)
        if not empresa:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('Usuario sin empresa asignada.')
        serializer.save(empresa=empresa, creado_por=self.request.user)

    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        """
        GET /api/finanzas/gastos/resumen/?fecha=YYYY-MM

        Retorna totales agrupados por categoría para el período indicado.
        Si no se envía ?fecha, usa el mes actual.
        """
        empresa = getattr(request.user, 'empresa', None)
        if not empresa:
            return Response({'error': 'Usuario sin empresa asignada.'}, status=400)

        # Parsear período
        fecha_param = request.query_params.get('fecha')
        hoy = date.today()
        try:
            if fecha_param:
                anio, mes = [int(x) for x in fecha_param.split('-')]
            else:
                anio, mes = hoy.year, hoy.month
        except (ValueError, AttributeError):
            return Response({'error': 'Formato de fecha inválido. Usar YYYY-MM.'}, status=400)

        _, ultimo = monthrange(anio, mes)
        fecha_inicio = date(anio, mes, 1)
        fecha_fin    = date(anio, mes, ultimo)

        # Queryset del período
        qs = GastoOperativo.objects.filter(
            empresa=empresa,
            fecha__range=(fecha_inicio, fecha_fin),
            estado='pagado',
        ).select_related('categoria')

        # Totales globales
        total_gastos   = Decimal('0')
        total_fijos    = Decimal('0')
        total_variables = Decimal('0')
        tc = getattr(empresa, 'tipo_cambio_usd', Decimal('3.70'))

        def a_pen(gasto):
            m = gasto.monto
            if gasto.moneda == 'USD':
                return m * tc
            return m

        # Agrupar por categoría
        cat_map = {}
        for g in qs:
            monto_pen = a_pen(g)
            total_gastos += monto_pen
            if g.categoria.es_fijo:
                total_fijos += monto_pen
            else:
                total_variables += monto_pen

            cid = g.categoria_id
            if cid not in cat_map:
                cat_map[cid] = {
                    'id':       g.categoria.id,
                    'categoria': g.categoria.nombre,
                    'es_fijo':  g.categoria.es_fijo,
                    'color':    g.categoria.color,
                    'icono':    g.categoria.icono,
                    'total':    Decimal('0'),
                }
            cat_map[cid]['total'] += monto_pen

        # Calcular porcentajes
        por_categoria = []
        for cat in sorted(cat_map.values(), key=lambda x: x['total'], reverse=True):
            pct = float(cat['total'] / total_gastos * 100) if total_gastos > 0 else 0
            por_categoria.append({
                'id':          cat['id'],
                'categoria':   cat['categoria'],
                'total':       float(cat['total']),
                'porcentaje':  round(pct, 1),
                'es_fijo':     cat['es_fijo'],
                'color':       cat['color'],
                'icono':       cat['icono'],
            })

        # Mes anterior para comparativo
        if mes == 1:
            mes_ant, anio_ant = 12, anio - 1
        else:
            mes_ant, anio_ant = mes - 1, anio
        _, ultimo_ant = monthrange(anio_ant, mes_ant)
        fecha_inicio_ant = date(anio_ant, mes_ant, 1)
        fecha_fin_ant    = date(anio_ant, mes_ant, ultimo_ant)

        qs_ant = GastoOperativo.objects.filter(
            empresa=empresa,
            fecha__range=(fecha_inicio_ant, fecha_fin_ant),
            estado='pagado',
        ).select_related('categoria')

        total_anterior = sum(a_pen(g) for g in qs_ant)
        diferencia     = total_gastos - total_anterior
        diferencia_pct = float(
            (diferencia / total_anterior * 100) if total_anterior > 0 else 0
        )

        # Nombre del mes en español (simple)
        MESES_ES = [
            '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        ]
        nombre_mes = f'{MESES_ES[mes]} {anio}'

        return Response({
            'periodo':         nombre_mes,
            'fecha_inicio':    fecha_inicio.isoformat(),
            'fecha_fin':       fecha_fin.isoformat(),
            'total_gastos':    float(total_gastos),
            'total_fijos':     float(total_fijos),
            'total_variables': float(total_variables),
            'por_categoria':   por_categoria,
            'comparativo_mes_anterior': {
                'total_anterior':  float(total_anterior),
                'diferencia':      float(diferencia),
                'diferencia_pct':  round(diferencia_pct, 1),
            },
        })


class GastoRecurrenteViewSet(viewsets.ModelViewSet):
    """
    CRUD de gastos recurrentes.

    Acción extra:
      POST /api/finanzas/recurrentes/<id>/generar_mes/
      Genera un GastoOperativo para el mes actual si aún no existe.
    """
    serializer_class = GastoRecurrenteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        empresa = getattr(self.request.user, 'empresa', None)
        if not empresa:
            return GastoRecurrente.objects.none()
        return GastoRecurrente.objects.filter(empresa=empresa).select_related('categoria')

    def perform_create(self, serializer):
        empresa = getattr(self.request.user, 'empresa', None)
        if not empresa:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('Usuario sin empresa asignada.')
        serializer.save(empresa=empresa)

    @action(detail=True, methods=['post'], url_path='generar_mes')
    def generar_mes(self, request, pk=None):
        """
        POST /api/finanzas/recurrentes/<id>/generar_mes/

        Genera un GastoOperativo para el mes actual si no fue generado ya.
        Actualiza el campo `ultimo_generado` del recurrente.
        """
        recurrente = self.get_object()
        hoy = date.today()
        primer_dia = hoy.replace(day=1)
        _, ultimo = monthrange(hoy.year, hoy.month)
        ultimo_dia = hoy.replace(day=ultimo)

        # Verificar si ya existe para este mes
        ya_existe = GastoOperativo.objects.filter(
            empresa=recurrente.empresa,
            categoria=recurrente.categoria,
            descripcion=recurrente.descripcion,
            fecha__range=(primer_dia, ultimo_dia),
            es_recurrente=True,
        ).exists()

        if ya_existe:
            return Response(
                {'detail': 'Ya existe un gasto generado para este mes.'},
                status=status.HTTP_200_OK,
            )

        # Calcular fecha del gasto según dia_del_mes
        try:
            dia = min(recurrente.dia_del_mes, ultimo)
            fecha_gasto = date(hoy.year, hoy.month, dia)
        except ValueError:
            fecha_gasto = primer_dia

        gasto = GastoOperativo.objects.create(
            empresa=recurrente.empresa,
            categoria=recurrente.categoria,
            descripcion=recurrente.descripcion,
            monto=recurrente.monto,
            moneda=recurrente.moneda,
            fecha=fecha_gasto,
            es_recurrente=True,
            frecuencia=recurrente.frecuencia,
            estado='programado',
            creado_por=request.user,
        )

        # Actualizar último generado
        recurrente.ultimo_generado = hoy
        recurrente.save(update_fields=['ultimo_generado', 'updated_at'])

        serializer = GastoOperativoSerializer(gasto)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
