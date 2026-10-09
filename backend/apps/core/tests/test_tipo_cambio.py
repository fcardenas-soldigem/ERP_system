"""
Consolidación a PEN con tipo de cambio HISTÓRICO por documento.

Cubre la regla de negocio: cada documento guarda el TC de su fecha_emision y
se valoriza SIEMPRE con ese TC, aunque el TC de hoy cambie.
"""
from datetime import date
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase

from apps.empresas.models import Empresa
from apps.ventas.models import Cliente, Venta
from apps.core.services import tipo_cambio as tc_mod
from apps.core.services.tipo_cambio import desglose_pen, backfill_tipo_cambio


def _empresa():
    return Empresa.objects.create(nombre='E', ruc='20123456789', modo_inventario='con_stock')


def _cliente(emp):
    return Cliente.objects.create(empresa=emp, nombre='C', documento='12345678', tipo_documento='ruc')


def _set_total(v, monto):
    """
    Venta tiene un pre_save que pone total=0 en creación (los totales se calculan
    desde los detalles). En tests fijamos el total directamente, sin tocar save().
    """
    Venta.objects.filter(id=v.id).update(total=Decimal(str(monto)))
    v.refresh_from_db()
    return v


class TipoCambioPorDocumentoTests(TestCase):
    def setUp(self):
        cache.clear()
        self.emp = _empresa()
        self.cli = _cliente(self.emp)

    def test_doc_pen_tipo_cambio_1(self):
        """Un documento en PEN siempre guarda tipo_cambio = 1.0 (sin red)."""
        v = Venta.objects.create(
            empresa=self.emp, cliente=self.cli, fecha_emision=date(2026, 6, 10),
            tipo_venta='contado', moneda='PEN', total=Decimal('1000'),
        )
        self.assertEqual(v.tipo_cambio, Decimal('1.0'))
        self.assertFalse(v.tc_estimado)

    def test_usd_conserva_tc_historico_aunque_cambie_el_de_hoy(self):
        """
        Una venta USD de hace 3 meses se valoriza con el TC de SU fecha.
        Si el TC de hoy cambia, total_pen NO cambia.
        """
        # TC "histórico" de junio = 3.30
        with mock.patch.object(tc_mod, 'get_tc_venta', return_value=Decimal('3.30')):
            v = Venta.objects.create(
                empresa=self.emp, cliente=self.cli, fecha_emision=date(2026, 6, 15),
                tipo_venta='contado', moneda='USD',
            )
        _set_total(v, 100)
        self.assertEqual(v.tipo_cambio, Decimal('3.30'))
        self.assertEqual(v.total_pen, Decimal('330.00'))

        # Hoy el dólar sube a 3.90 → el documento guardado NO se revaloriza
        v.refresh_from_db()
        self.assertEqual(v.tipo_cambio, Decimal('3.30'))
        self.assertEqual(v.total_pen, Decimal('330.00'))

        # Y el agregado tampoco: usa el TC guardado, no el fallback de hoy (3.90)
        d = desglose_pen(Venta.objects.filter(id=v.id), 'total', fallback_tc=Decimal('3.90'))
        self.assertEqual(d['total_pen'], 330.0)
        self.assertFalse(d['tc_estimado'])

    def test_agregado_mixto_es_suma_de_total_pen(self):
        """Un agregado con USD y PEN = suma de cada total_pen (no suma cruda)."""
        with mock.patch.object(tc_mod, 'get_tc_venta', return_value=Decimal('3.50')):
            v_usd = Venta.objects.create(
                empresa=self.emp, cliente=self.cli, fecha_emision=date(2026, 7, 1),
                tipo_venta='contado', moneda='USD',
            )
        v_pen = Venta.objects.create(
            empresa=self.emp, cliente=self.cli, fecha_emision=date(2026, 7, 2),
            tipo_venta='contado', moneda='PEN',
        )
        _set_total(v_usd, 100)
        _set_total(v_pen, 1000)
        d = desglose_pen(Venta.objects.all(), 'total')
        self.assertEqual(d['total_pen'], 1350.0)   # 1000 + 100×3.50
        self.assertEqual(d['pen'], 1000.0)
        self.assertEqual(d['usd'], 100.0)
        self.assertEqual(d['tc_promedio'], 3.5)
        self.assertTrue(d['tiene_usd'])
        self.assertFalse(d['tc_estimado'])

    def test_tc_estimado_cuando_usd_sin_tc_guardado(self):
        """USD sin tipo_cambio → usa fallback actual y marca tc_estimado=True."""
        # La API falla al emitir → tipo_cambio queda null
        with mock.patch.object(tc_mod, 'get_tc_venta', return_value=None):
            v = Venta.objects.create(
                empresa=self.emp, cliente=self.cli, fecha_emision=date(2026, 8, 1),
                tipo_venta='contado', moneda='USD',
            )
        _set_total(v, 100)
        self.assertIsNone(v.tipo_cambio)
        self.assertTrue(v.tc_estimado)
        d = desglose_pen(Venta.objects.filter(id=v.id), 'total', fallback_tc=Decimal('4.00'))
        self.assertEqual(d['total_pen'], 400.0)     # 100 × fallback
        self.assertTrue(d['tc_estimado'])

    def test_backfill_idempotente(self):
        """Backfill rellena nulls una vez; la segunda corrida no toca nada."""
        with mock.patch.object(tc_mod, 'get_tc_venta', return_value=Decimal('3.40')):
            v_usd = Venta.objects.create(
                empresa=self.emp, cliente=self.cli, fecha_emision=date(2026, 9, 1),
                tipo_venta='contado', moneda='USD', total=Decimal('100'),
            )
        v_pen = Venta.objects.create(
            empresa=self.emp, cliente=self.cli, fecha_emision=date(2026, 9, 2),
            tipo_venta='contado', moneda='PEN', total=Decimal('500'),
        )
        # Simular estado pre-migración: sin tipo_cambio
        Venta.objects.filter(id__in=[v_usd.id, v_pen.id]).update(tipo_cambio=None)

        with mock.patch.object(tc_mod, 'get_tc_venta', return_value=Decimal('3.40')):
            r1 = backfill_tipo_cambio(Venta)
        self.assertEqual(r1, {'pen': 1, 'usd': 1})
        v_usd.refresh_from_db(); v_pen.refresh_from_db()
        self.assertEqual(v_usd.tipo_cambio, Decimal('3.40'))
        self.assertEqual(v_pen.tipo_cambio, Decimal('1.0'))

        # Segunda corrida: nada que rellenar
        with mock.patch.object(tc_mod, 'get_tc_venta', return_value=Decimal('9.99')):
            r2 = backfill_tipo_cambio(Venta)
        self.assertEqual(r2, {'pen': 0, 'usd': 0})
        v_usd.refresh_from_db()
        self.assertEqual(v_usd.tipo_cambio, Decimal('3.40'))  # no se tocó


class GetTcVentaFallbackTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_fin_de_semana_usa_dia_habil_anterior(self):
        """
        Sábado 2026-07-11 no tiene TC SBS → retrocede al viernes 2026-07-10.
        """
        def fake_consultar(fecha=None):
            if fecha == '2026-07-10':   # viernes
                return {'success': True, 'data': {'venta': 3.42}}
            return {'success': False}   # sábado/domingo sin dato

        with mock.patch(
            'apps.core.services.tipo_cambio.DocumentoService.consultar_tipo_cambio',
            side_effect=fake_consultar,
        ):
            tc = tc_mod.get_tc_venta(date(2026, 7, 11))   # sábado
        self.assertEqual(tc, Decimal('3.42'))
