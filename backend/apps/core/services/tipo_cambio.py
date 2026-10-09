"""
TipoCambioService — tipo de cambio HISTÓRICO por fecha para consolidar a PEN.

Regla de negocio (ERP Soldigem):
- Moneda de consolidación: PEN (lo exige SUNAT).
- Cada documento se valoriza con el TC venta SBS de SU fecha_emision, SIEMPRE.
  Una venta de junio se valoriza al TC de junio, nunca al de hoy.
- PEN → tipo_cambio = 1.0.

Este módulo es la única fuente de TC por fecha. Cachea por fecha (muchos
documentos comparten fecha) y, si una fecha no tiene dato (fin de semana o
feriado SBS), retrocede al día hábil anterior.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional

from django.core.cache import cache
from django.db.models import Case, When, F, Value, Sum, DecimalField, Q

from apps.core.services.documento_service import DocumentoService

logger = logging.getLogger(__name__)

# Los TC históricos no cambian nunca → se pueden cachear agresivamente.
_CACHE_TTL_HISTORICO = 60 * 60 * 24 * 30  # 30 días
_CACHE_TTL_HOY = 60 * 30                   # 30 min (el de hoy puede publicarse tarde)
_MAX_RETROCESO_DIAS = 7                    # fines de semana largos / feriados

# Fallback de último recurso si la API nunca responde y no hay empresa.tipo_cambio_usd.
TC_FALLBACK = Decimal('3.75')

_PREC = DecimalField(max_digits=18, decimal_places=4)


def _parse_fecha(fecha) -> date:
    if isinstance(fecha, datetime):
        return fecha.date()
    if isinstance(fecha, date):
        return fecha
    return datetime.strptime(str(fecha)[:10], '%Y-%m-%d').date()


def _to_decimal(valor) -> Optional[Decimal]:
    try:
        d = Decimal(str(valor))
        return d if d > 0 else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def get_tc_venta(fecha, *, usar_cache: bool = True) -> Optional[Decimal]:
    """
    TC venta SBS para una fecha. Retrocede hasta 7 días hábiles si la fecha
    exacta no tiene dato (fin de semana/feriado). Devuelve Decimal o None si
    la fuente falla por completo — NUNCA levanta excepción.

    Se usa precio de VENTA (lo que cuesta comprar USD con PEN), consistente con
    el helper previo obtener_tipo_cambio_venta() del dashboard.
    """
    try:
        f = _parse_fecha(fecha)
    except (ValueError, TypeError):
        logger.warning("get_tc_venta: fecha inválida %r", fecha)
        return None

    hoy = date.today()
    if f > hoy:
        f = hoy

    for intento in range(_MAX_RETROCESO_DIAS + 1):
        dia = f - timedelta(days=intento)
        key = f"tc_venta_{dia.isoformat()}"
        if usar_cache:
            cached = cache.get(key)
            if cached is not None:
                return Decimal(str(cached))

        data = DocumentoService.consultar_tipo_cambio(dia.isoformat())
        if data.get('success') and data.get('data'):
            tc = _to_decimal(data['data'].get('venta'))
            if tc is not None:
                ttl = _CACHE_TTL_HOY if dia == hoy else _CACHE_TTL_HISTORICO
                cache.set(key, str(tc), ttl)
                if intento > 0:
                    logger.info("TC %s no disponible, usando día hábil %s = %s", f, dia, tc)
                return tc
        # 422/sin dato → probar día anterior

    logger.warning("get_tc_venta: sin TC para %s tras %s días de retroceso", f, _MAX_RETROCESO_DIAS)
    return None


def get_tc_actual(empresa=None) -> Decimal:
    """TC de fallback para estimaciones: empresa.tipo_cambio_usd → TC hoy → constante."""
    if empresa is not None:
        tc = _to_decimal(getattr(empresa, 'tipo_cambio_usd', None))
        if tc is not None:
            return tc
    tc_hoy = get_tc_venta(date.today())
    return tc_hoy if tc_hoy is not None else TC_FALLBACK


def tipo_cambio_para_documento(moneda: str, fecha) -> Optional[Decimal]:
    """
    TC que debe guardar un documento al emitirse.
    PEN → 1.0 siempre. USD → TC histórico de su fecha (o None si la API falla,
    en cuyo caso el caller deja null y loggea; nunca bloquea la creación).
    """
    if moneda == 'PEN':
        return Decimal('1.0')
    if moneda == 'USD':
        return get_tc_venta(fecha)
    # Otras monedas no soportadas hoy
    return None


class TipoCambioMixin:
    """
    Comportamiento compartido para documentos con moneda + fecha_emision.
    El campo `tipo_cambio` se declara en cada modelo (para que la migración sea
    explícita por tabla); este mixin aporta el llenado y las propiedades *_pen.

    Llamar self.asegurar_tipo_cambio() dentro de save() ANTES de persistir.
    Nunca bloquea la creación: si la API falla deja tipo_cambio=None y loggea.
    """

    def asegurar_tipo_cambio(self):
        if self.tipo_cambio is not None:
            return
        fecha = getattr(self, 'fecha_emision', None) or date.today()
        tc = tipo_cambio_para_documento(self.moneda, fecha)
        if tc is None:
            logger.warning(
                "%s sin TC histórico para %s (%s); se guarda tipo_cambio=None",
                type(self).__name__, fecha, self.moneda,
            )
        self.tipo_cambio = tc

    @property
    def tc_estimado(self) -> bool:
        """True si es USD y no tiene TC guardado (el *_pen usa fallback actual)."""
        return self.moneda == 'USD' and self.tipo_cambio is None

    def _tc_efectivo(self) -> Decimal:
        if self.tipo_cambio is not None:
            return Decimal(str(self.tipo_cambio))
        if self.moneda == 'PEN':
            return Decimal('1.0')
        return get_tc_actual(getattr(self, 'empresa', None))

    def _pen(self, campo: str) -> Optional[Decimal]:
        valor = getattr(self, campo, None)
        if valor is None:
            return None
        return (Decimal(str(valor)) * self._tc_efectivo()).quantize(Decimal('0.01'))

    @property
    def total_pen(self) -> Optional[Decimal]:
        return self._pen('total')

    @property
    def subtotal_pen(self) -> Optional[Decimal]:
        return self._pen('subtotal')

    @property
    def igv_pen(self) -> Optional[Decimal]:
        return self._pen('igv')


def desglose_pen(qs, campo: str = 'total', *, fallback_tc: Decimal = None) -> dict:
    """
    Agrega un campo monetario de un queryset consolidando a PEN con el TC
    guardado por documento. Devuelve el total en PEN y el desglose para el
    tooltip del frontend.

    total_pen por fila:
      - tipo_cambio no nulo → total × tipo_cambio
      - PEN con tipo_cambio nulo → total (×1)
      - USD con tipo_cambio nulo → total × fallback_tc (marca tc_estimado)

    Retorna: {total_pen, pen, usd, tc_promedio, tiene_usd, tc_estimado}
    """
    if fallback_tc is None:
        fallback_tc = get_tc_actual()
    fallback_tc = Decimal(str(fallback_tc))

    agg = qs.aggregate(
        total_pen=Sum(
            Case(
                When(tipo_cambio__isnull=False, then=F(campo) * F('tipo_cambio')),
                When(moneda='PEN', then=F(campo)),
                default=F(campo) * Value(fallback_tc),
                output_field=_PREC,
            ),
            output_field=_PREC,
        ),
        pen=Sum(Case(When(moneda='PEN', then=F(campo)), default=Value(Decimal('0')), output_field=_PREC)),
        usd=Sum(Case(When(moneda='USD', then=F(campo)), default=Value(Decimal('0')), output_field=_PREC)),
    )

    total_pen = agg['total_pen'] or Decimal('0')
    pen = agg['pen'] or Decimal('0')
    usd = agg['usd'] or Decimal('0')

    tiene_usd = usd > 0
    # TC promedio ponderado implícito = (total_pen - pen) / usd
    usd_en_pen = total_pen - pen
    tc_promedio = float(usd_en_pen / usd) if usd > 0 else None

    tc_estimado = qs.filter(moneda='USD', tipo_cambio__isnull=True).exists()

    return {
        'total_pen': float(total_pen),
        'pen': float(pen),
        'usd': float(usd),
        'tc_promedio': round(tc_promedio, 4) if tc_promedio is not None else None,
        'tiene_usd': tiene_usd,
        'tc_estimado': tc_estimado,
    }
