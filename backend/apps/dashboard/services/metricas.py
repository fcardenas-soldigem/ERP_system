"""
MetricasService — ÚNICA implementación de las métricas de negocio que
comparten Dashboard, Finanzas y Reportes. No duplicar estas reglas en views.

Definiciones (decididas, aplican en TODO el sistema):

VENTAS (devengo)   : ventas con fecha_emision en el período, excluyendo
                     borrador y anulado. Independiente del estado de pago.
                     Valorizadas en PEN con el tipo_cambio del documento.
COBROS (caja)      : PagoVenta con fecha en el período (sin los 'pendiente').
                     Valorizados con venta.tipo_cambio (simplificación
                     aceptada: no calculamos diferencia de cambio).
PAGOS PROVEEDORES  : PagoCompra con fecha en el período. El pago tiene moneda
                     propia: PEN → tal cual; USD → × compra.tipo_cambio.
IGV                : por devengo (fecha_emision), mismo universo que VENTAS.
MARGEN             : solo sobre líneas del período con costo registrado
                     (producto.precio_compra > 0). Sin costo → None, nunca 0%.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum, Count, F, Case, When, Value, DecimalField

from apps.core.services.tipo_cambio import desglose_pen, get_tc_actual
from apps.ventas.models import Venta, DetalleVenta, PagoVenta
from apps.compras.models import Compra, PagoCompra

_PREC = DecimalField(max_digits=18, decimal_places=4)

# Devengo: todo lo emitido salvo borradores y anulados.
ESTADOS_EXCLUIDOS_VENTA = ('borrador', 'anulado')
ESTADOS_EXCLUIDOS_COMPRA = ('borrador', 'anulada')
# Equivalente positivo, para filter(estado__in=...) en las vistas de series.
ESTADOS_DEVENGO_VENTA = ('pendiente', 'pagado')
ESTADOS_DEVENGO_COMPRA = ('pendiente', 'pagada')


class MetricasService:

    def __init__(self, empresa, fecha_inicio: date, fecha_fin: date):
        self.empresa = empresa
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin
        self.fallback_tc = get_tc_actual(empresa)

    # ── Querysets base ────────────────────────────────────────────────────

    def ventas_qs(self, fecha_inicio=None, fecha_fin=None):
        """Universo VENTAS (devengo) del período."""
        return Venta.objects.filter(
            empresa=self.empresa,
            fecha_emision__range=(fecha_inicio or self.fecha_inicio,
                                  fecha_fin or self.fecha_fin),
        ).exclude(estado__in=ESTADOS_EXCLUIDOS_VENTA)

    def compras_qs(self, fecha_inicio=None, fecha_fin=None):
        """Universo COMPRAS (devengo) del período."""
        return Compra.objects.filter(
            empresa=self.empresa,
            fecha_emision__range=(fecha_inicio or self.fecha_inicio,
                                  fecha_fin or self.fecha_fin),
        ).exclude(estado__in=ESTADOS_EXCLUIDOS_COMPRA)

    # ── VENTAS (devengo) ──────────────────────────────────────────────────

    def ventas_devengo(self, campo='total', fecha_inicio=None, fecha_fin=None) -> dict:
        """Total PEN + desglose + cantidad de las ventas emitidas en el período."""
        qs = self.ventas_qs(fecha_inicio, fecha_fin)
        d = desglose_pen(qs, campo, fallback_tc=self.fallback_tc)
        d['cantidad'] = qs.count()
        return d

    # ── COBROS (caja) ─────────────────────────────────────────────────────

    def _pago_venta_pen_expr(self):
        """Valoriza PagoVenta a PEN con el TC de SU venta (el pago no tiene moneda propia)."""
        return Case(
            When(venta__tipo_cambio__isnull=False, then=F('monto') * F('venta__tipo_cambio')),
            When(venta__moneda='PEN', then=F('monto')),
            default=F('monto') * Value(self.fallback_tc),
            output_field=_PREC,
        )

    def cobros(self, fecha_inicio=None, fecha_fin=None) -> dict:
        """COBROS del período en PEN, con desglose por moneda de la venta."""
        qs = PagoVenta.objects.filter(
            venta__empresa=self.empresa,
            fecha__range=(fecha_inicio or self.fecha_inicio,
                          fecha_fin or self.fecha_fin),
        ).exclude(metodo_pago='pendiente')

        agg = qs.aggregate(
            total_pen=Sum(self._pago_venta_pen_expr()),
            pen=Sum(Case(When(venta__moneda='PEN', then=F('monto')),
                         default=Value(Decimal('0')), output_field=_PREC)),
            usd=Sum(Case(When(venta__moneda='USD', then=F('monto')),
                         default=Value(Decimal('0')), output_field=_PREC)),
            cantidad=Count('id'),
        )
        total_pen = agg['total_pen'] or Decimal('0')
        pen = agg['pen'] or Decimal('0')
        usd = agg['usd'] or Decimal('0')
        return {
            'total_pen': float(total_pen),
            'pen': float(pen),
            'usd': float(usd),
            'tc_promedio': round(float((total_pen - pen) / usd), 4) if usd > 0 else None,
            'tiene_usd': usd > 0,
            'tc_estimado': qs.filter(venta__moneda='USD', venta__tipo_cambio__isnull=True).exists(),
            'cantidad': agg['cantidad'] or 0,
        }

    def cobros_por_fecha(self, fecha_inicio=None, fecha_fin=None) -> dict:
        """{fecha: total_pen} para el gráfico de caja diaria."""
        qs = PagoVenta.objects.filter(
            venta__empresa=self.empresa,
            fecha__range=(fecha_inicio or self.fecha_inicio,
                          fecha_fin or self.fecha_fin),
        ).exclude(metodo_pago='pendiente')
        return {
            r['fecha']: Decimal(str(r['t'] or 0))
            for r in qs.values('fecha').annotate(t=Sum(self._pago_venta_pen_expr()))
        }

    # ── PAGOS A PROVEEDORES (caja) ────────────────────────────────────────

    def _pago_compra_pen_expr(self):
        """PagoCompra tiene moneda propia: PEN → tal cual; USD → × compra.tipo_cambio."""
        return Case(
            When(moneda='PEN', then=F('monto')),
            When(compra__tipo_cambio__isnull=False, then=F('monto') * F('compra__tipo_cambio')),
            default=F('monto') * Value(self.fallback_tc),
            output_field=_PREC,
        )

    def pagos_proveedores(self, fecha_inicio=None, fecha_fin=None) -> Decimal:
        qs = PagoCompra.objects.filter(
            compra__empresa=self.empresa,
            fecha__range=(fecha_inicio or self.fecha_inicio,
                          fecha_fin or self.fecha_fin),
        ).exclude(metodo_pago='pendiente')
        return Decimal(str(qs.aggregate(t=Sum(self._pago_compra_pen_expr()))['t'] or 0))

    def pagos_por_fecha(self, fecha_inicio=None, fecha_fin=None) -> dict:
        qs = PagoCompra.objects.filter(
            compra__empresa=self.empresa,
            fecha__range=(fecha_inicio or self.fecha_inicio,
                          fecha_fin or self.fecha_fin),
        ).exclude(metodo_pago='pendiente')
        return {
            r['fecha']: Decimal(str(r['t'] or 0))
            for r in qs.values('fecha').annotate(t=Sum(self._pago_compra_pen_expr()))
        }

    # ── CUENTAS POR COBRAR (definición única) ─────────────────────────────

    def cuentas_por_cobrar(self) -> dict:
        """
        DEFINICIÓN ÚNICA de "Por cobrar" (Dashboard y Finanzas la usan):
        ventas no anuladas ni borrador con saldo pendiente > 0
        (saldo = total − pagos_total), en PEN con el TC del documento.
        Incluye contado sin pagar y créditos; resta pagos parciales.
        """
        saldo_pen = (F('total') - F('pagos_total')) * Case(
            When(tipo_cambio__isnull=False, then=F('tipo_cambio')),
            When(moneda='PEN', then=Value(Decimal('1.0'))),
            default=Value(self.fallback_tc),
            output_field=_PREC,
        )
        qs = (
            Venta.objects.filter(empresa=self.empresa)
            .exclude(estado__in=ESTADOS_EXCLUIDOS_VENTA)
            .annotate(saldo=F('total') - F('pagos_total'))
            .filter(saldo__gt=0)
        )
        agg = qs.aggregate(
            total_pen=Sum(saldo_pen, output_field=_PREC),
            cantidad=Count('id'),
        )
        return {
            'total_pen': float(agg['total_pen'] or 0),
            'cantidad': agg['cantidad'] or 0,
        }

    # ── IGV (devengo) ─────────────────────────────────────────────────────

    def igv_devengo(self, fecha_inicio=None, fecha_fin=None) -> dict:
        igv_ventas = desglose_pen(
            self.ventas_qs(fecha_inicio, fecha_fin), 'igv', fallback_tc=self.fallback_tc,
        )['total_pen']
        igv_compras = desglose_pen(
            self.compras_qs(fecha_inicio, fecha_fin), 'igv', fallback_tc=self.fallback_tc,
        )['total_pen']
        return {
            'igv_ventas': igv_ventas,
            'igv_compras': igv_compras,
            'igv_por_pagar': igv_ventas - igv_compras,
        }

    # ── MARGEN ────────────────────────────────────────────────────────────

    def margen(self, fecha_inicio=None, fecha_fin=None):
        """
        Utilidad bruta del período por VENTA, no por línea de catálogo:
        cada venta aporta subtotal_pen − costo_pen, donde el costo sigue la
        prioridad factura > oc > cotizacion > catalogo (Venta.costo_info).

        Retorna None si NINGUNA venta del período tiene costo (estado vacío).
        Si solo algunas lo tienen → parcial=True y el cálculo usa solo esas:
        "parcial: X de Y ventas con costo". Nunca inventa 0% ni 100%.
        """
        ventas = list(
            self.ventas_qs(fecha_inicio, fecha_fin)
            .prefetch_related('detalles__producto', 'ordenes_compra')
        )
        ventas_total = len(ventas)
        if ventas_total == 0:
            return None

        ingresos = Decimal('0')
        cogs = Decimal('0')
        con_costo = 0
        for venta in ventas:
            info = venta.costo_info()
            if info is None:
                continue
            con_costo += 1
            ingresos += venta.subtotal_pen or Decimal('0')
            cogs += info['costo_pen']

        if con_costo == 0 or ingresos <= 0:
            return None

        utilidad = ingresos - cogs
        return {
            'ingresos_con_costo': float(ingresos),
            'cogs': float(cogs),
            'utilidad_bruta': float(utilidad),
            'margen_bruto_pct': round(float(utilidad / ingresos * 100), 1),
            # Alias nuevos (contrato del fix de costo/utilidad)
            'utilidad_pen': float(utilidad),
            'margen_pct': round(float(utilidad / ingresos * 100), 1),
            'ventas_con_costo': con_costo,
            'ventas_total': ventas_total,
            'parcial': con_costo < ventas_total,
        }

    # ── TOP PRODUCTOS ─────────────────────────────────────────────────────

    def top_productos(self, limite=10) -> dict:
        """
        Top productos del PERÍODO (devengo). Si el período no tiene datos,
        cae a últimos 90 días y lo etiqueta — el frontend muestra la etiqueta.
        """
        from django.db.models.functions import Coalesce

        def _query(inicio, fin):
            # Líneas de texto libre (producto null) agrupan por su descripción,
            # nunca por nombre vacío.
            return list(
                DetalleVenta.objects
                .filter(venta__empresa=self.empresa,
                        venta__fecha_emision__range=(inicio, fin))
                .exclude(venta__estado__in=ESTADOS_EXCLUIDOS_VENTA)
                .annotate(nombre=Coalesce('producto__nombre', 'descripcion'))
                .exclude(nombre__isnull=True).exclude(nombre='')
                .values('nombre')
                .annotate(total_vendido=Sum('cantidad'))
                .order_by('-total_vendido')[:limite]
            )

        rows = _query(self.fecha_inicio, self.fecha_fin)
        periodo = 'mes'
        if not rows:
            hoy = date.today()
            rows = _query(hoy - timedelta(days=90), hoy)
            periodo = 'ultimos_90_dias'
        def _limpiar(nombre):
            # Descripciones importadas suelen arrastrar separadores ("| Texto")
            return (nombre or '').strip().lstrip('|').strip()

        return {
            'periodo': periodo,
            'labels': [_limpiar(r['nombre']) for r in rows],
            'data': [float(r['total_vendido'] or 0) for r in rows],
        }

    # ── STOCK ─────────────────────────────────────────────────────────────

    def maneja_stock(self) -> bool:
        """False para empresas sin_stock: el resumen no incluye métricas de inventario."""
        return getattr(self.empresa, 'modo_inventario', 'con_stock') != 'sin_stock'
