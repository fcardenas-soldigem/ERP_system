"""C11 — integridad del dataset del eval y del comparador (el LLM real se
evalúa con `manage.py eval_agente`; aquí no sale nada a la red)."""
from django.test import SimpleTestCase

from apps.canales.eval.mensajes import CASOS, comparar
from apps.canales.nucleo import esquemas as E
from apps.canales.nucleo.interprete import CATALOGO


class EvalDatasetTests(SimpleTestCase):
    def test_son_15_casos_y_las_tools_existen(self):
        self.assertEqual(len(CASOS), 15)
        self.assertEqual(len({c['id'] for c in CASOS}), 15)
        for caso in CASOS:
            self.assertIn(caso['tool'], CATALOGO, caso['id'])
            self.assertTrue(caso['texto'].strip())

    def test_cubre_las_tareas_del_piloto(self):
        tools = {c['tool'] for c in CASOS}
        self.assertLessEqual(
            {'preparar_cotizacion', 'preparar_cobro', 'cambiar_estado_operativo',
             'consultar_venta', 'consultar_stock', 'ventas_detenidas'}, tools)

    def test_comparador_acepta_match_laxo(self):
        caso = CASOS[0]  # cotización: cliente (texto) + items.0.cantidad
        entrada = E.PrepararCotizacion(
            cliente='Transportes Lima SAC',
            items=[{'producto_id': 7, 'cantidad': 3}])
        ok, detalle = comparar(caso, 'preparar_cotizacion', entrada)
        self.assertTrue(ok, detalle)

    def test_comparador_rechaza_tool_y_params_equivocados(self):
        caso = CASOS[2]  # cobro V-000012 monto 500
        ok, _ = comparar(caso, 'consultar_venta', E.ConsultarVenta(venta_numero='V-000012'))
        self.assertFalse(ok)
        ok, detalle = comparar(caso, 'preparar_cobro', E.PrepararCobro(venta_numero='V-000012', monto=400))
        self.assertFalse(ok)
        self.assertIn('monto', detalle)


class EsquemasParaVertexTests(SimpleTestCase):
    def test_ningun_esquema_lleva_ref(self):
        """El adaptador de Vertex no acepta $ref: las tools deben ir inlineadas."""
        import json
        from apps.canales.nucleo.interprete import _tools
        for spec in _tools():
            plano = json.dumps(spec.parameters)
            self.assertNotIn('$ref', plano, spec.name)
            self.assertNotIn('$defs', plano, spec.name)
