"""
Eval de punta a punta (puntos 3 y 4) — sin red.

El ORÁCULO es un LLM falso que responde perfecto a cada caso: si no da 100 %
correcto, el problema está en el dataset, el fixture o los chequeos (no en el
modelo). Así el eval se valida antes de gastar llamadas a Vertex.

(Que los schemas de las tools sean aceptables para Vertex lo cubre
tests/test_schemas_gemini.py, que construye FunctionDeclaration real.)
"""
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from apps.canales.eval.mensajes import CASOS, umbral
from apps.canales.eval.runner import evaluar, preparar_datos
from apps.canales.nucleo.interprete import CATALOGO
from apps.empresas.models import Empresa
from apps.ventas.models import Cliente

from .base import respuesta_llm

User = get_user_model()

# respuesta perfecta del modelo para cada caso: (tool, argumentos)
ORACULO = {
    1: ('preparar_cotizacion', {'cliente': 'transportes lima', 'items': [{'producto': 'jabra 750', 'cantidad': 3}]}),
    2: ('consultar_venta', {'cliente_query': 'acme'}),
    3: ('preparar_cobro', {'venta_numero': 'V-090012', 'monto': 500, 'metodo_pago': 'transferencia'}),
    4: ('cambiar_estado_operativo', {'cliente_query': 'minera andes', 'nuevo_estado': 'entregado'}),
    5: ('buscar_producto', {'query': 'teclados logitech'}),
    6: ('ventas_detenidas', {}),
    7: ('buscar_cliente', {'query': 'constructora sol'}),
    8: ('preparar_cotizacion', {'cliente': 'galvez', 'items': [
        {'producto': 'cascos', 'cantidad': 10, 'precio_unitario': 25},
        {'producto': 'chalecos', 'cantidad': 10, 'precio_unitario': 25}]}),
    9: ('preparar_cobro', {'cliente_query': 'ferreteria union', 'metodo_pago': 'efectivo'}),
    10: ('cambiar_estado_operativo', {'cliente_query': 'distribuidora norte', 'nuevo_estado': 'recibido'}),
    11: ('buscar_producto', {'query': 'monitor lg 24'}),
    12: ('consultar_venta', {'venta_numero': 'V-090003'}),
    13: ('preparar_cotizacion', {'cliente': 'inversiones ramirez', 'items': [
        {'producto': 'laptop hp 640', 'cantidad': 2}, {'producto': 'mouse inalambrico', 'cantidad': 1}]}),
    14: ('preparar_cobro', {'cliente_query': 'andino', 'monto': 2000}),
    15: ('cambiar_estado_operativo', {'cliente_query': 'corporacion delta', 'nuevo_estado': 'facturado'}),
}


class LLMGuionado:
    """Responde según el texto del usuario; tras un resultado de tool, texto."""

    def __init__(self, guion):
        self.guion = guion          # texto → (tool, args)

    def chat(self, system, messages, tools, temperature=0.2):
        if messages[-1].role == 'tool':
            return respuesta_llm(None, texto='listo')
        tool, args = self.guion.get(messages[-1].content, (None, None))
        return respuesta_llm(tool, args)


def _guion(sobrescribir=None):
    guion = {c['texto']: ORACULO[c['id']] for c in CASOS if c['id'] in ORACULO}
    guion.update(sobrescribir or {})
    return LLMGuionado(guion)


class DatasetTests(SimpleTestCase):
    def test_ids_unicos_y_tools_existentes(self):
        self.assertEqual(len({c['id'] for c in CASOS}), len(CASOS))
        for c in CASOS:
            self.assertTrue(c['final'] is None or c['final'] in CATALOGO, c['id'])

    def test_cubre_todas_las_intenciones(self):
        self.assertLessEqual(set(CATALOGO), {c['final'] for c in CASOS})

    def test_umbral_13_de_15(self):
        self.assertEqual(umbral(15), 13)


class EvalPuntaAPuntaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre='Empresa Eval', ruc='20888888881')
        cls.usuario = User.objects.create_user(
            username='eval@x.pe', email='eval@x.pe', password='x',
            nombre='Eval', apellido='X', empresa=cls.empresa, rol='admin')
        preparar_datos(cls.empresa)

    def test_oraculo_saca_todo_correcto(self):
        """Valida el eval mismo: dataset + fixture + chequeos son alcanzables."""
        casos = [c for c in CASOS if c['id'] in ORACULO]
        resultados = evaluar(self.usuario, casos, cliente_llm=_guion())
        malos = [(r.id, r.estado, r.fallos) for r in resultados if r.estado != 'correcto']
        self.assertEqual(malos, [])

    def test_lectura_intermedia_cuenta_rondas_y_tokens(self):
        caso = next(c for c in CASOS if c['id'] == 5)
        r = evaluar(self.usuario, [caso], cliente_llm=_guion())[0]
        self.assertEqual((r.estado, r.rondas, r.tokens), ('correcto', 2, 140))

    def test_buscar_y_despues_cotizar_es_correcto(self):
        """Lo que hizo gemini en #1/#8/#13: ya no es un fallo del eval."""
        caso = next(c for c in CASOS if c['id'] == 1)

        class BuscaPrimero:
            def __init__(self):
                self.n = 0

            def chat(self, system, messages, tools, temperature=0.2):
                self.n += 1
                if self.n == 1:
                    return respuesta_llm('buscar_producto', {'query': 'jabra 750'})
                return respuesta_llm(*ORACULO[1])

        r = evaluar(self.usuario, [caso], cliente_llm=BuscaPrimero())[0]
        self.assertEqual((r.estado, r.rondas), ('correcto', 2))

    def test_tool_equivocada_es_incorrecto(self):
        caso = next(c for c in CASOS if c['id'] == 11)
        r = evaluar(self.usuario, [caso], cliente_llm=_guion(
            {caso['texto']: ('consultar_venta', {'cliente_query': 'lg'})}))[0]
        self.assertEqual(r.estado, 'incorrecto')
        self.assertIn('tool final', r.fallos[0])

    def test_tool_correcta_con_cantidad_mal_es_parcial(self):
        caso = next(c for c in CASOS if c['id'] == 1)
        r = evaluar(self.usuario, [caso], cliente_llm=_guion({caso['texto']: (
            'preparar_cotizacion', {'cliente': 'transportes lima', 'items': [{'producto': 'jabra 750', 'cantidad': 5}]})}))[0]
        self.assertEqual(r.estado, 'parcial')
        self.assertIn('cantidad', r.fallos[0])

    def test_error_del_proveedor_es_incorrecto_sin_reventar(self):
        class Roto:
            def chat(self, *a, **k):
                raise RuntimeError('sin credenciales')
        r = evaluar(self.usuario, CASOS[:1], cliente_llm=Roto())[0]
        self.assertEqual(r.estado, 'incorrecto')
        self.assertIn('RuntimeError', r.fallos[0])


class ComandoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre='Empresa Demo Eval', ruc='20888888882')
        User.objects.create_user(username='demo@eval.pe', email='demo@eval.pe', password='x',
                                 nombre='D', apellido='E', empresa=cls.empresa, rol='admin')

    def test_transaccion_se_revierte_y_reporta(self):
        out = StringIO()
        with mock.patch('apps.canales.nucleo.interprete.get_llm_client', return_value=_guion()):
            call_command('eval_agente', email='demo@eval.pe', caso=1, stdout=out)
        texto = out.getvalue()
        self.assertIn('# 1 ✓ correcto', texto)
        self.assertIn('rondas=1', texto)
        self.assertIn('1/1 correctos', texto)
        # el fixture del eval NO quedó en la BD
        self.assertFalse(Cliente.objects.filter(empresa=self.empresa, documento='20600000001').exists())

    def test_sin_usuario_pide_seed_demo(self):
        from django.core.management import CommandError
        with self.assertRaises(CommandError) as cm:
            call_command('eval_agente', email='nadie@x.pe', stdout=StringIO())
        self.assertIn('seed_demo', str(cm.exception))
