"""
FinanzasService — todos los KPIs financieros del módulo de finanzas.

Principios de diseño:
- Reutiliza datos existentes: Venta, Compra, Producto, PagoVenta, PagoCompra.
- NO duplica lógica ya presente en dashboard/views.py para utilidad diaria.
- Usa select_related y prefetch_related en todos los querysets pesados.
- Los métodos retornan dicts limpios — la view solo orquesta y cachea.
- El "saldo actual" es balance de transacciones registradas (cobros - pagos del sistema),
  NO el saldo bancario real. Se muestra con disclaimer.
"""

import logging
from datetime import date, timedelta, datetime
from calendar import monthrange
from decimal import Decimal

from django.db.models import (
    Sum, Count, Avg, F, Q, ExpressionWrapper, DecimalField, FloatField,
    Case, When, Value,
)
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.ventas.models import Venta, DetalleVenta, PagoVenta, Cliente
from apps.compras.models import Compra, CompraDetalle, PagoCompra
from apps.inventario.models.producto import Producto
from apps.inventario.models.stock import Stock

logger = logging.getLogger(__name__)


class FinanzasService:

    def __init__(self, empresa, fecha_inicio: date, fecha_fin: date, tipo_cambio_usd: Decimal | None = None):
        self.empresa = empresa
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin
        self.hoy = date.today()
        # Tipo de cambio: prioridad empresa.tipo_cambio_usd → parámetro → fallback 3.70
        self.tipo_cambio_usd = (
            Decimal(str(getattr(empresa, 'tipo_cambio_usd', None) or tipo_cambio_usd or '3.70'))
        )

    def _pen(self, monto, moneda: str) -> Decimal:
        """Convierte monto a PEN según la moneda. PEN → sin cambio. USD → × tipo_cambio_usd."""
        monto = Decimal(str(monto or 0))
        if moneda == 'USD':
            return (monto * self.tipo_cambio_usd).quantize(Decimal('0.01'))
        return monto

    def _sum_pen(self, qs, campo: str) -> Decimal:
        """Suma un campo monetario de un queryset con conversión por moneda."""
        pen = qs.filter(moneda='PEN').aggregate(t=Sum(campo, output_field=DecimalField()))['t'] or Decimal('0')
        usd = qs.filter(moneda='USD').aggregate(t=Sum(campo, output_field=DecimalField()))['t'] or Decimal('0')
        return Decimal(str(pen)) + Decimal(str(usd)) * self.tipo_cambio_usd

    # ──────────────────────────────────────────────────────────────────────────
    # FLUJO DE CAJA
    # ──────────────────────────────────────────────────────────────────────────

    def calcular_flujo_caja(self) -> dict:
        """
        Saldo operativo = total cobrado (PagoVenta) - total pagado (PagoCompra)
        en el rango dado. NO incluye sueldos, alquiler ni retiros del dueño.

        Proyección 30 días = saldo_actual + cuentas_por_cobrar_vigentes
                           - cuentas_por_pagar_vigentes
        """
        # Cobros realizados en el período
        cobros = PagoVenta.objects.filter(
            venta__empresa=self.empresa,
            fecha__range=(self.fecha_inicio, self.fecha_fin),
        ).exclude(metodo_pago='pendiente').aggregate(
            total=Sum('monto', output_field=DecimalField())
        )['total'] or Decimal('0')

        # Pagos realizados en el período
        pagos = PagoCompra.objects.filter(
            compra__empresa=self.empresa,
            fecha__range=(self.fecha_inicio, self.fecha_fin),
        ).exclude(metodo_pago='pendiente').aggregate(
            total=Sum('monto', output_field=DecimalField())
        )['total'] or Decimal('0')

        saldo_actual = cobros - pagos

        # Cuentas por cobrar vigentes (no vencidas o pendientes)
        cxc_pendiente = Venta.objects.filter(
            empresa=self.empresa,
            estado='pendiente',
            tipo_venta__in=['credito_30', 'credito_60'],
        ).aggregate(
            total=Sum(F('total') - F('pagos_total'), output_field=DecimalField())
        )['total'] or Decimal('0')

        # Cuentas por pagar vigentes
        cxp_pendiente = Compra.objects.filter(
            empresa=self.empresa,
            estado='pendiente',
            tipo_compra__in=['credito_30', 'credito_60'],
        ).aggregate(
            total=Sum('total', output_field=DecimalField())
        )['total'] or Decimal('0')

        # Descuento los pagos ya realizados de compras crédito
        cxp_pagado = PagoCompra.objects.filter(
            compra__empresa=self.empresa,
            compra__estado='pendiente',
        ).exclude(metodo_pago='pendiente').aggregate(
            total=Sum('monto', output_field=DecimalField())
        )['total'] or Decimal('0')
        cxp_real = max(Decimal('0'), cxp_pendiente - cxp_pagado)

        proyeccion_30 = saldo_actual + cxc_pendiente - cxp_real

        # Saldo diario acumulativo para el gráfico
        saldo_diario = self._saldo_diario_acumulativo()

        return {
            'saldo_actual': float(saldo_actual),
            'cobros_periodo': float(cobros),
            'pagos_periodo': float(pagos),
            'proyeccion_30_dias': float(proyeccion_30),
            'cxc_pendiente': float(cxc_pendiente),
            'cxp_pendiente': float(cxp_real),
            'saldo_diario': saldo_diario,
            'disclaimer': (
                'Incluye solo cobros de ventas y pagos de compras registradas. '
                'No incluye sueldos, alquiler ni otros gastos fuera del sistema.'
            ),
        }

    def _saldo_diario_acumulativo(self) -> list:
        """
        Construye el array de saldo acumulado día a día para el gráfico.
        Agrupa PagoVenta y PagoCompra por fecha y va acumulando.
        """
        cobros_diarios = (
            PagoVenta.objects
            .filter(
                venta__empresa=self.empresa,
                fecha__range=(self.fecha_inicio, self.fecha_fin),
            )
            .exclude(metodo_pago='pendiente')
            .values('fecha')
            .annotate(total=Sum('monto', output_field=DecimalField()))
            .order_by('fecha')
        )

        pagos_diarios = (
            PagoCompra.objects
            .filter(
                compra__empresa=self.empresa,
                fecha__range=(self.fecha_inicio, self.fecha_fin),
            )
            .exclude(metodo_pago='pendiente')
            .values('fecha')
            .annotate(total=Sum('monto', output_field=DecimalField()))
            .order_by('fecha')
        )

        # Build lookup dicts
        cobros_map = {r['fecha']: r['total'] for r in cobros_diarios}
        pagos_map  = {r['fecha']: r['total'] for r in pagos_diarios}

        # Walk every day in range
        resultado = []
        saldo_acumulado = Decimal('0')
        delta = self.fecha_fin - self.fecha_inicio

        for i in range(delta.days + 1):
            dia = self.fecha_inicio + timedelta(days=i)
            neto = cobros_map.get(dia, Decimal('0')) - pagos_map.get(dia, Decimal('0'))
            saldo_acumulado += neto
            resultado.append({
                'fecha': dia.isoformat(),
                'saldo': float(saldo_acumulado),
                'cobros': float(cobros_map.get(dia, Decimal('0'))),
                'pagos': float(pagos_map.get(dia, Decimal('0'))),
            })

        return resultado

    # ──────────────────────────────────────────────────────────────────────────
    # RENTABILIDAD
    # ──────────────────────────────────────────────────────────────────────────

    def calcular_rentabilidad(self) -> dict:
        """
        Utilidad bruta = Ventas netas (sin IGV) - COGS
        COGS = Σ (DetalleVenta.cantidad × Producto.precio_compra) para ventas pagadas.
        Nota: usa precio_compra del catálogo — estimado, no costo exacto FIFO.

        BUG-03 fix: Venta.total incluye IGV (18% Perú). Comparar total (con IGV)
        contra COGS (sin IGV) infla el margen ~8-10 puntos porcentuales.
        Usamos Venta.subtotal que el modelo siempre almacena como base imponible neta,
        independientemente de si igv_incluido=True/False (ver Venta.actualizar_totales).
        """
        ventas_qs = Venta.objects.filter(
            empresa=self.empresa,
            estado='pagado',
            fecha_emision__range=(self.fecha_inicio, self.fecha_fin),
        )

        # subtotal = base imponible neta sin IGV — convertido a PEN por moneda
        ventas_neto = self._sum_pen(ventas_qs, 'subtotal')

        # COGS desde DetalleVenta — precio_compra ya es precio sin IGV
        cogs = (
            DetalleVenta.objects
            .filter(
                venta__empresa=self.empresa,
                venta__estado='pagado',
                venta__fecha_emision__range=(self.fecha_inicio, self.fecha_fin),
            )
            .select_related('producto')
            .aggregate(
                cogs=Sum(
                    F('cantidad') * F('producto__precio_compra'),
                    output_field=DecimalField()
                )
            )['cogs'] or Decimal('0')
        )

        utilidad_bruta = ventas_neto - cogs
        margen_bruto_pct = float((utilidad_bruta / ventas_neto * 100) if ventas_neto > 0 else 0)

        # Gastos operativos del período
        from apps.finanzas.models import GastoOperativo
        gastos_qs = GastoOperativo.objects.filter(
            empresa=self.empresa,
            fecha__range=(self.fecha_inicio, self.fecha_fin),
            estado='pagado',
        )
        gastos_pen = sum(
            (g.monto * self.tipo_cambio_usd if g.moneda == 'USD' else g.monto)
            for g in gastos_qs
        )
        utilidad_neta = utilidad_bruta - gastos_pen
        margen_neto_pct = float((utilidad_neta / ventas_neto * 100) if ventas_neto > 0 else 0)
        tiene_gastos = gastos_qs.exists()

        # Semáforo de margen
        if margen_bruto_pct >= 30:
            semaforo_margen = 'verde'
        elif margen_bruto_pct >= 15:
            semaforo_margen = 'amarillo'
        else:
            semaforo_margen = 'rojo'

        # Mes anterior para comparativo — también usa subtotal (neto sin IGV), convertido a PEN
        mes_ant_inicio, mes_ant_fin = self._mes_anterior()
        ventas_ant_qs = Venta.objects.filter(
            empresa=self.empresa,
            estado='pagado',
            fecha_emision__range=(mes_ant_inicio, mes_ant_fin),
        )
        ventas_anterior_neto = self._sum_pen(ventas_ant_qs, 'subtotal')

        cogs_anterior = (
            DetalleVenta.objects
            .filter(
                venta__empresa=self.empresa,
                venta__estado='pagado',
                venta__fecha_emision__range=(mes_ant_inicio, mes_ant_fin),
            )
            .select_related('producto')
            .aggregate(
                cogs=Sum(F('cantidad') * F('producto__precio_compra'), output_field=DecimalField())
            )['cogs'] or Decimal('0')
        )
        utilidad_anterior = ventas_anterior_neto - cogs_anterior

        vs_mes_anterior_pct = float(
            ((utilidad_bruta - utilidad_anterior) / utilidad_anterior * 100)
            if utilidad_anterior != 0 else 0
        )

        # Top productos por margen
        por_producto = self._rentabilidad_por_producto()

        # Desglose de gastos por categoría
        from django.db.models import Sum as _Sum
        desglose_gastos = []
        if tiene_gastos:
            cats_qs = (
                gastos_qs
                .values('categoria__id', 'categoria__nombre', 'categoria__es_fijo')
                .annotate(total_pen=_Sum('monto'))
                .order_by('-total_pen')
            )
            total_pen_float = float(gastos_pen) or 1
            for row in cats_qs:
                t = float(row['total_pen'] or 0)
                desglose_gastos.append({
                    'categoria':  row['categoria__nombre'],
                    'total':      t,
                    'porcentaje': round(t / total_pen_float * 100, 1),
                })

        return {
            'ventas_mes': float(ventas_neto),           # neto sin IGV
            'ventas_mes_con_igv': float(ventas_qs.aggregate(  # para referencia
                t=Sum('total', output_field=DecimalField()))['t'] or 0),
            'costo_ventas_mes': float(cogs),
            'utilidad_bruta': float(utilidad_bruta),
            'margen_bruto_pct': round(margen_bruto_pct, 1),
            'semaforo_margen': semaforo_margen,
            'vs_mes_anterior_pct': round(vs_mes_anterior_pct, 1),
            'ventas_anterior': float(ventas_anterior_neto),
            'utilidad_anterior': float(utilidad_anterior),
            'por_producto': por_producto,
            'gastos_operativos': float(gastos_pen),
            'utilidad_neta': float(utilidad_neta),
            'margen_neto_pct': round(margen_neto_pct, 1),
            'tiene_gastos_registrados': tiene_gastos,
            'desglose_gastos': desglose_gastos,
            'nota': 'Ventas y márgenes calculados sobre base neta (sin IGV 18%). COGS estimado con precio de catálogo actual.',
        }

    def _rentabilidad_por_producto(self) -> list:
        """Top 10 productos por utilidad bruta en el período."""
        rows = (
            DetalleVenta.objects
            .filter(
                venta__empresa=self.empresa,
                venta__estado='pagado',
                venta__fecha_emision__range=(self.fecha_inicio, self.fecha_fin),
            )
            .select_related('producto')
            .values('producto__id', 'producto__nombre')
            .annotate(
                ingresos=Sum(
                    F('cantidad') * Case(
                        When(venta__igv_incluido=True, then=F('precio_unitario') / Value(Decimal('1.18'))),
                        default=F('precio_unitario'),
                        output_field=DecimalField(),
                    ),
                    output_field=DecimalField(),
                ),
                cogs=Sum(F('cantidad') * F('producto__precio_compra'), output_field=DecimalField()),
                unidades=Sum('cantidad', output_field=DecimalField()),
            )
            .order_by('-ingresos')[:10]
        )

        resultado = []
        for r in rows:
            ingresos = r['ingresos'] or Decimal('0')
            cogs     = r['cogs']     or Decimal('0')
            utilidad = ingresos - cogs
            margen   = float((utilidad / ingresos * 100) if ingresos > 0 else 0)
            resultado.append({
                'nombre':    r['producto__nombre'],
                'ingresos':  float(ingresos),
                'cogs':      float(cogs),
                'utilidad':  float(utilidad),
                'margen_pct': round(margen, 1),
                'unidades':  float(r['unidades'] or 0),
            })
        return resultado

    # ──────────────────────────────────────────────────────────────────────────
    # CUENTAS POR COBRAR (DSO + AGING + MOROSOS)
    # ──────────────────────────────────────────────────────────────────────────

    def calcular_cuentas_cobrar(self) -> dict:
        """
        DSO = (Promedio CxC / Ventas período) × días_período
        Solo ventas a crédito (credito_30, credito_60) con estado pendiente.

        Aging basado en days past due (días desde fecha_vencimiento hasta hoy).
        """
        ventas_credito = (
            Venta.objects
            .filter(
                empresa=self.empresa,
                estado='pendiente',
                tipo_venta__in=['credito_30', 'credito_60'],
            )
            .select_related('cliente')
            .prefetch_related('pagos')
        )

        total_pendiente = Decimal('0')
        aging = {'vigente': Decimal('0'), '30_dias': Decimal('0'), '60_dias': Decimal('0'), '90_dias': Decimal('0')}
        morosos = []

        for venta in ventas_credito:
            saldo = venta.get_saldo_pendiente()
            if saldo <= 0:
                continue
            total_pendiente += saldo

            dias_atraso = 0
            if venta.fecha_vencimiento:
                dias_atraso = (self.hoy - venta.fecha_vencimiento).days

            if dias_atraso <= 0:
                aging['vigente'] += saldo
            elif dias_atraso <= 30:
                aging['30_dias'] += saldo
            elif dias_atraso <= 60:
                aging['60_dias'] += saldo
            else:
                aging['90_dias'] += saldo

            if dias_atraso > 0:
                morosos.append({
                    'venta_id':   venta.id,
                    'venta_num':  venta.numero,
                    'cliente':    venta.cliente.nombre if venta.cliente else '—',
                    'cliente_id': venta.cliente_id,
                    'telefono':   venta.cliente.telefono if venta.cliente else '',
                    'monto':      float(saldo),
                    'dias':       dias_atraso,
                    'vencimiento': venta.fecha_vencimiento.isoformat() if venta.fecha_vencimiento else None,
                })

        # Ordenar morosos por días de atraso desc
        morosos.sort(key=lambda x: x['dias'], reverse=True)

        # DSO rolling 90 días: evita valores absurdos al inicio del mes
        # Fórmula: (CxC / Ventas_90d) × 90 — estable sin importar el día del mes
        ventana_90 = self.hoy - timedelta(days=90)
        ventas_90d = Venta.objects.filter(
            empresa=self.empresa,
            estado='pagado',
            fecha_emision__range=(ventana_90, self.hoy),
        ).aggregate(total=Sum('subtotal', output_field=DecimalField()))['total'] or Decimal('0')

        dso = int(total_pendiente / ventas_90d * 90) if ventas_90d > 0 else None
        indice_morosidad_pct = float(
            (aging['30_dias'] + aging['60_dias'] + aging['90_dias']) / total_pendiente * 100
            if total_pendiente > 0 else 0
        )

        return {
            'total': float(total_pendiente),
            'dso': dso,
            'aging': {k: float(v) for k, v in aging.items()},
            'morosos': morosos[:10],
            'indice_morosidad_pct': round(indice_morosidad_pct, 1),
            'dso_explicacion': (
                f'En promedio tus clientes tardan {dso} días en pagarte.'
                if dso is not None else 'Sin datos suficientes (menos de 90 días de ventas).'
            ),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # CUENTAS POR PAGAR (DPO + AGING + PRÓXIMOS)
    # ──────────────────────────────────────────────────────────────────────────

    def calcular_cuentas_pagar(self) -> dict:
        """
        DPO = (Promedio CxP / COGS período) × días_período
        Compras a crédito con estado pendiente.
        """
        compras_credito = (
            Compra.objects
            .filter(
                empresa=self.empresa,
                estado='pendiente',
                tipo_compra__in=['credito_30', 'credito_60'],
            )
            .select_related('proveedor')
            .prefetch_related('pagos')
        )

        total_pendiente = Decimal('0')
        aging = {'vigente': Decimal('0'), '30_dias': Decimal('0'), '60_dias': Decimal('0'), '90_dias': Decimal('0')}
        proximos_pagos = []

        for compra in compras_credito:
            saldo = compra.get_saldo_pendiente()
            if saldo <= 0:
                continue
            total_pendiente += saldo

            dias_vencimiento = 0
            if compra.fecha_vencimiento:
                dias_vencimiento = (compra.fecha_vencimiento - self.hoy).days
                dias_atraso = -dias_vencimiento
            else:
                dias_atraso = 0

            # Aging
            if dias_atraso <= 0:
                aging['vigente'] += saldo
            elif dias_atraso <= 30:
                aging['30_dias'] += saldo
            elif dias_atraso <= 60:
                aging['60_dias'] += saldo
            else:
                aging['90_dias'] += saldo

            # Próximos 7 días
            if compra.fecha_vencimiento and 0 <= dias_vencimiento <= 7:
                proximos_pagos.append({
                    'compra_id':  compra.id,
                    'compra_num': compra.numero,
                    'proveedor':  compra.proveedor.razon_social if compra.proveedor else '—',
                    'monto':      float(saldo),
                    'vence':      compra.fecha_vencimiento.isoformat(),
                    'dias_restantes': dias_vencimiento,
                    'urgente': dias_vencimiento <= 2,
                })

        proximos_pagos.sort(key=lambda x: x['dias_restantes'])

        # DPO rolling 90 días: mismo principio que DSO — base estable de 90 días
        # Fórmula: (CxP / Compras_90d) × 90
        ventana_90 = self.hoy - timedelta(days=90)
        compras_90d = Compra.objects.filter(
            empresa=self.empresa,
            fecha_emision__range=(ventana_90, self.hoy),
        ).aggregate(total=Sum('total', output_field=DecimalField()))['total'] or Decimal('0')

        dpo = int(total_pendiente / compras_90d * 90) if compras_90d > 0 else None

        return {
            'total': float(total_pendiente),
            'dpo': dpo,
            'aging': {k: float(v) for k, v in aging.items()},
            'proximos_pagos': proximos_pagos[:10],
            'alerta_esta_semana': len(proximos_pagos) > 0,
            'dpo_explicacion': (
                f'En promedio pagas a tus proveedores en {dpo} días.'
                if dpo is not None else 'Sin datos suficientes (menos de 90 días de compras).'
            ),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # CRECIMIENTO
    # ──────────────────────────────────────────────────────────────────────────

    def calcular_crecimiento(self) -> dict:
        """Revenue growth vs mes anterior. Ticket promedio. Nuevos clientes."""
        mes_ant_inicio, mes_ant_fin = self._mes_anterior()

        # Ventas mes actual — convertidas a PEN por moneda
        ventas_actual_qs = Venta.objects.filter(
            empresa=self.empresa,
            estado='pagado',
            fecha_emision__range=(self.fecha_inicio, self.fecha_fin),
        )
        total_actual = self._sum_pen(ventas_actual_qs, 'total')
        count_actual = ventas_actual_qs.aggregate(count=Count('id'))['count'] or 0

        # Ventas mes anterior — convertidas a PEN por moneda
        ventas_ant_qs_crecimiento = Venta.objects.filter(
            empresa=self.empresa,
            estado='pagado',
            fecha_emision__range=(mes_ant_inicio, mes_ant_fin),
        )
        total_anterior = self._sum_pen(ventas_ant_qs_crecimiento, 'total')
        count_anterior = ventas_ant_qs_crecimiento.aggregate(count=Count('id'))['count'] or 0

        # Revenue growth
        revenue_growth_pct = float(
            ((total_actual - total_anterior) / total_anterior * 100)
            if total_anterior > 0 else 0
        )

        # Ticket promedio
        ticket_actual   = float(total_actual / count_actual) if count_actual > 0 else 0
        ticket_anterior = float(total_anterior / count_anterior) if count_anterior > 0 else 0

        # Nuevos clientes (primer venta en el período)
        clientes_con_venta_anterior = set(
            Venta.objects
            .filter(empresa=self.empresa, fecha_emision__lt=self.fecha_inicio)
            .values_list('cliente_id', flat=True)
            .distinct()
        )
        clientes_actual = set(
            ventas_actual_qs.values_list('cliente_id', flat=True).distinct()
        )
        nuevos_clientes = len(clientes_actual - clientes_con_venta_anterior)

        return {
            'revenue_growth_pct': round(revenue_growth_pct, 1),
            'ventas_mes': float(total_actual),
            'ventas_anterior': float(total_anterior),
            'transacciones_mes': count_actual,
            'transacciones_anterior': count_anterior,
            'ticket_promedio': round(ticket_actual, 2),
            'ticket_promedio_anterior': round(ticket_anterior, 2),
            'ticket_variacion_pct': round(
                ((ticket_actual - ticket_anterior) / ticket_anterior * 100)
                if ticket_anterior > 0 else 0, 1
            ),
            'nuevos_clientes': nuevos_clientes,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # KPIs AVANZADOS (Nivel 2)
    # ──────────────────────────────────────────────────────────────────────────

    def calcular_avanzados(self, *, cxc: dict, cxp: dict, flujo: dict, rent: dict) -> dict:
        """
        CCC = DSO + DIO - DPO
        DIO = (Inventory Value / COGS) × días_período
        Ratio liquidez = (CxC + Saldo operativo) / CxP
        Concentración top 3 clientes
        Índice morosidad

        Recibe como keyword-only arguments los resultados ya calculados por la view,
        evitando re-ejecutar las 4 queries pesadas (BUG-01 fix).
        """
        # Aliases para legibilidad — no hay nueva I/O aquí
        caja = flujo

        dso = cxc['dso'] or 0
        dpo = cxp['dpo'] or 0

        # DIO = (Valor inventario / COGS) × días
        dias_periodo = (self.fecha_fin - self.fecha_inicio).days or 30
        inventario_valor = (
            Producto.objects
            .filter(empresa=self.empresa)
            .aggregate(
                total=Sum(
                    F('stock_total') * F('precio_compra'),
                    output_field=DecimalField()
                )
            )['total'] or Decimal('0')
        )
        cogs = Decimal(str(rent['costo_ventas_mes'])) or Decimal('1')
        dio = int((inventario_valor / cogs * dias_periodo) if cogs > 0 else 0)

        ccc = dso + dio - dpo

        # Ratio liquidez = (CxC + saldo_actual) / CxP
        numerador   = cxc['total'] + max(0, caja['saldo_actual'])
        denominador = cxp['total']
        ratio_liquidez = round(numerador / denominador, 2) if denominador > 0 else 99.0
        semaforo_liquidez = 'verde' if ratio_liquidez >= 1.2 else ('amarillo' if ratio_liquidez >= 0.8 else 'rojo')

        # Concentración top 3 clientes
        top3 = (
            Venta.objects
            .filter(
                empresa=self.empresa,
                estado='pagado',
                fecha_emision__range=(self.fecha_inicio, self.fecha_fin),
            )
            .values('cliente__nombre')
            .annotate(total=Sum('total', output_field=DecimalField()))
            .order_by('-total')[:3]
        )
        ventas_mes = rent['ventas_mes'] or 1
        top3_total = sum(r['total'] or 0 for r in top3)
        concentracion_pct = round(float(top3_total) / ventas_mes * 100, 1)
        concentracion_alerta = concentracion_pct > 50

        # Saldo neto mes anterior (cobros reales - pagos reales) para delta
        mes_ant_inicio, mes_ant_fin = self._mes_anterior()
        cobros_ant = PagoVenta.objects.filter(
            venta__empresa=self.empresa,
            fecha__range=(mes_ant_inicio, mes_ant_fin),
        ).exclude(metodo_pago='pendiente').aggregate(
            total=Sum('monto', output_field=DecimalField())
        )['total'] or Decimal('0')
        pagos_ant = PagoCompra.objects.filter(
            compra__empresa=self.empresa,
            fecha__range=(mes_ant_inicio, mes_ant_fin),
        ).exclude(metodo_pago='pendiente').aggregate(
            total=Sum('monto', output_field=DecimalField())
        )['total'] or Decimal('0')
        saldo_neto_anterior = float(cobros_ant - pagos_ant)

        return {
            'ccc_dias': ccc,
            'dio_dias': dio,
            'dso_dias': dso,
            'dpo_dias': dpo,
            'ratio_liquidez': ratio_liquidez,
            'semaforo_liquidez': semaforo_liquidez,
            'concentracion_top3_pct': concentracion_pct,
            'concentracion_alerta': concentracion_alerta,
            'top3_clientes': [
                {'nombre': r['cliente__nombre'], 'total': float(r['total'] or 0)} for r in top3
            ],
            'indice_morosidad_pct': cxc['indice_morosidad_pct'],
            'saldo_neto_mes':      caja['saldo_actual'],
            'saldo_neto_anterior': saldo_neto_anterior,
            'explicaciones': {
                'ccc': f'Tu dinero tarda {ccc} días en dar la vuelta completa: vendes → cobras → pagas.',
                'dio': f'Tu inventario dura {dio} días antes de venderse.',
                'ratio_liquidez': (
                    f'Por cada S/1 que debes, tienes S/{ratio_liquidez} disponible.'
                    if ratio_liquidez < 99 else 'Sin deudas pendientes.'
                ),
                'concentracion': (
                    f'El {concentracion_pct}% de tus ventas viene de solo 3 clientes. '
                    + ('⚠️ Riesgo de concentración alto.' if concentracion_alerta else 'Diversificación aceptable.')
                ),
            },
        }

    # ──────────────────────────────────────────────────────────────────────────
    # OBLIGACIONES FISCALES (IGV)
    # ──────────────────────────────────────────────────────────────────────────

    def calcular_obligaciones_fiscales(self) -> dict:
        """
        IGV por pagar = IGV de ventas del mes - IGV de compras del mes.
        Período: mes calendario de hoy (independiente del rango del dashboard).
        Vencimiento SUNAT: día 15 del mes siguiente.

        Usa Sum('igv') sobre el campo almacenado — más eficiente que el loop
        de Python que usa IGVDashboardView en dashboard/views.py.
        """
        primer_dia = self.hoy.replace(day=1)
        _, ultimo = monthrange(self.hoy.year, self.hoy.month)
        ultimo_dia = self.hoy.replace(day=ultimo)

        ventas_mes_qs = Venta.objects.filter(
            empresa=self.empresa,
            fecha_emision__range=(primer_dia, ultimo_dia),
            estado='pagado',
        )
        igv_ventas = self._sum_pen(ventas_mes_qs, 'igv')

        compras_mes_qs = Compra.objects.filter(
            empresa=self.empresa,
            fecha_emision__range=(primer_dia, ultimo_dia),
            estado='pagada',
        )
        igv_compras = self._sum_pen(compras_mes_qs, 'igv')

        igv_por_pagar = igv_ventas - igv_compras

        # Día 15 del mes siguiente — vencimiento estándar SUNAT PDT 621
        if self.hoy.month == 12:
            vencimiento = date(self.hoy.year + 1, 1, 15)
        else:
            vencimiento = date(self.hoy.year, self.hoy.month + 1, 15)

        dias_para_vencer = (vencimiento - self.hoy).days

        if dias_para_vencer <= 0:
            estado = 'vencido'
        elif dias_para_vencer <= 15:
            estado = 'proximo'
        else:
            estado = 'vigente'

        return {
            'igv_ventas':          float(igv_ventas),
            'igv_compras':         float(igv_compras),
            'igv_por_pagar':       float(igv_por_pagar),
            'proximo_vencimiento': vencimiento.isoformat(),
            'dias_para_vencer':    dias_para_vencer,
            'estado':              estado,
            'periodo':             primer_dia.strftime('%B %Y'),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # SEMÁFORO GENERAL
    # ──────────────────────────────────────────────────────────────────────────

    def calcular_semaforo(self, flujo, rentabilidad, cxc, cxp) -> dict:
        """
        Verde: liquidez OK + margen OK + morosidad baja + sin pagos urgentes.
        Amarillo: algún indicador en zona de precaución.
        Rojo: liquidez crítica O margen negativo O burn rate activo.
        """
        alertas = []
        puntuacion = 100  # Empieza perfecto, se restan puntos

        # Liquidez
        if flujo['proyeccion_30_dias'] < 0:
            puntuacion -= 40
            alertas.append({'nivel': 'rojo', 'mensaje': 'Proyección de caja negativa en 30 días'})
        elif flujo['proyeccion_30_dias'] < flujo['saldo_actual'] * 0.3:
            puntuacion -= 20
            alertas.append({'nivel': 'amarillo', 'mensaje': 'Caja proyectada ajustada'})

        # Margen
        semaforo_margen = rentabilidad.get('semaforo_margen', 'verde')
        if semaforo_margen == 'rojo':
            puntuacion -= 30
            alertas.append({'nivel': 'rojo', 'mensaje': f'Margen bruto bajo: {rentabilidad["margen_bruto_pct"]}%'})
        elif semaforo_margen == 'amarillo':
            puntuacion -= 10
            alertas.append({'nivel': 'amarillo', 'mensaje': f'Margen bruto moderado: {rentabilidad["margen_bruto_pct"]}%'})

        # Morosidad
        morosidad = cxc.get('indice_morosidad_pct', 0)
        if morosidad > 30:
            puntuacion -= 20
            alertas.append({'nivel': 'amarillo', 'mensaje': f'{morosidad:.0f}% de cuentas por cobrar vencidas'})

        # Pagos urgentes
        if cxp.get('alerta_esta_semana'):
            proximos = cxp.get('proximos_pagos', [])
            total_urgente = sum(p['monto'] for p in proximos if p.get('urgente'))
            if total_urgente > 0:
                puntuacion -= 10
                alertas.append({'nivel': 'amarillo', 'mensaje': f'S/ {total_urgente:,.2f} vence en menos de 2 días'})

        if puntuacion >= 75:
            semaforo = 'verde'
            mensaje = 'Tu negocio está financieramente saludable'
        elif puntuacion >= 45:
            semaforo = 'amarillo'
            mensaje = 'Hay aspectos que requieren atención'
        else:
            semaforo = 'rojo'
            mensaje = 'Situación financiera crítica — actúa hoy'

        return {
            'color': semaforo,
            'puntuacion': puntuacion,
            'mensaje': mensaje,
            'alertas': alertas[:5],
        }

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _mes_anterior(self):
        """Retorna (primer_dia, ultimo_dia) del mes anterior al fecha_inicio."""
        primer_dia = self.fecha_inicio.replace(day=1)
        ultimo_dia_anterior = primer_dia - timedelta(days=1)
        primer_dia_anterior = ultimo_dia_anterior.replace(day=1)
        return primer_dia_anterior, ultimo_dia_anterior
