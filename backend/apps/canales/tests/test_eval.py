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

from apps.canales.eval.mensajes import (CASOS, EDITA_CANTIDAD, MENSAJE_PILOTO,
                                        SEGUIMIENTO_CLIENTE, umbral)
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
    16: ('preparar_cotizacion', {'cliente': 'transportes lima', 'items': [{'producto': 'monitores lg', 'cantidad': 2}]}),
    17: ('preparar_cotizacion', {'cliente': 'ferreteria el sol', 'items': [{'producto': 'jabra 750', 'cantidad': 1}]}),
    18: ('preparar_cotizacion', {'cliente': 'comercial galvez', 'items': [{'producto': 'chalecos reflectivos', 'cantidad': 12}]}),
    19: ('preparar_cotizacion', {'cliente': 'minera andes', 'moneda': 'USD',
                                 'items': [{'producto': 'monitores lg 27', 'cantidad': 2, 'precio_unitario': 420}]}),
    20: (None, None),   # fuera de alcance: el modelo no llama ninguna tool
}

# fix V2 — argumentos que un modelo perfecto daría en el caso del piloto
_ITEM_PEDESTAL = {'descripcion': 'PEDESTAL CON INCLINACIÓN 90° TV 32 A 75 PULG / VESA MAX 600X400MM / CARGA 75KG',
                  'cantidad': 4, 'precio_unitario': '441.00', 'precio_incluye_igv': True}
_ITEM_GABINETE = {'descripcion': 'Gabinete de Piso para Servidores / 32 RU / 60x80x150 cm',
                  'cantidad': 1, 'precio_unitario': '1750', 'precio_incluye_igv': True}
_ARGS_PILOTO = {'items': [_ITEM_PEDESTAL, _ITEM_GABINETE], 'moneda': 'PEN'}
_ARGS_CON_CLIENTE = {**_ARGS_PILOTO, 'cliente': 'Uhman Perú sac'}
_ARGS_CANTIDAD_6 = {**_ARGS_CON_CLIENTE,
                    'items': [{**_ITEM_PEDESTAL, 'cantidad': 6}, _ITEM_GABINETE]}

ORACULO.update({
    21: ('preparar_cotizacion', _ARGS_PILOTO),
    23: (None, None),                                   # pide aclaración, sin tool
    24: ('resumen_ventas', {'periodo': 'mes'}),
    26: ('preparar_cotizacion', {'cliente': 'acme', 'items': [
        {'descripcion': 'teclado logitech k120', 'cantidad': 2, 'precio_unitario': 35}]}),
})

# casos multi-turno: el guion se indexa por el TEXTO de cada turno
ORACULO_TURNOS = {
    MENSAJE_PILOTO: ('preparar_cotizacion', _ARGS_PILOTO),
    SEGUIMIENTO_CLIENTE: ('preparar_cotizacion', _ARGS_CON_CLIENTE),
    'Cliente Uhman Perú sac': ('preparar_cotizacion', _ARGS_CON_CLIENTE),
    EDITA_CANTIDAD: ('preparar_cotizacion', _ARGS_CANTIDAD_6),
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
    guion = {c['texto']: ORACULO[c['id']] for c in CASOS if 'texto' in c and c['id'] in ORACULO}
    guion.update(ORACULO_TURNOS)
    guion.update(sobrescribir or {})
    return LLMGuionado(guion)


class DatasetTests(SimpleTestCase):
    def test_ids_unicos_y_tools_existentes(self):
        self.assertEqual(len({c['id'] for c in CASOS}), len(CASOS))
        for c in CASOS:
            self.assertTrue(c['final'] in (None, 'aclaracion') or c['final'] in CATALOGO, c['id'])

    def test_cubre_todas_las_intenciones(self):
        self.assertLessEqual(set(CATALOGO), {c['final'] for c in CASOS})

    def test_umbral_90_por_ciento(self):
        self.assertEqual(umbral(20), 18)
        self.assertEqual(umbral(26), 24)   # con los 6 casos del fix V2

    def test_son_26_casos_con_los_del_fix_v2(self):
        self.assertEqual(len(CASOS), 26)
        self.assertIsNone(next(c for c in CASOS if c['id'] == 20)['final'])
        # los casos que crearían datos incorrectos están marcados como críticos
        criticos = {c['id'] for c in CASOS if c.get('critico')}
        self.assertEqual(criticos, {21, 22, 23, 25, 26})


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
        casos = [c for c in CASOS if c['id'] in ORACULO or 'turnos' in c]
        self.assertEqual(len(casos), len(CASOS))   # nadie se queda sin oráculo
        resultados = evaluar(self.usuario, casos, cliente_llm=_guion())
        malos = [(r.id, r.estado, r.fallos) for r in resultados if r.estado != 'correcto']
        self.assertEqual(malos, [])

    def test_consultas_cuestan_una_ronda(self):
        """#5, #7 y #11 (stock, RUC, precio): 1 ronda, 70 tokens del guion."""
        for id_ in (5, 7, 11):
            caso = next(c for c in CASOS if c['id'] == id_)
            r = evaluar(self.usuario, [caso], cliente_llm=_guion())[0]
            self.assertEqual((r.estado, r.rondas, r.tokens), ('correcto', 1, 70), id_)

    def _con_rondas_previas(self, id_, invalidos):
        """El modelo manda `invalidos` llamadas inválidas (distintas) antes de la buena."""
        caso = next(c for c in CASOS if c['id'] == id_)

        class Tardio:
            def __init__(self):
                self.n = 0

            def chat(self, system, messages, tools, temperature=0.2):
                self.n += 1
                if self.n <= invalidos:
                    return respuesta_llm('buscar_producto', {'query': '', 'n': self.n})  # inválido
                return respuesta_llm(*ORACULO[id_])

        return evaluar(self.usuario, [caso], cliente_llm=Tardio())[0]

    def test_consulta_con_2_rondas_sigue_correcta(self):
        r = self._con_rondas_previas(11, invalidos=1)
        self.assertEqual((r.estado, r.rondas), ('correcto', 2))

    def test_consulta_con_mas_de_2_rondas_es_parcial(self):
        r = self._con_rondas_previas(11, invalidos=2)
        self.assertEqual((r.estado, r.rondas), ('parcial', 3))
        self.assertIn('consulta con 3 rondas', r.fallos[-1])

    def test_preparacion_con_3_rondas_no_se_penaliza(self):
        """La regla de rondas es para consultas; cotizar puede corregirse."""
        r = self._con_rondas_previas(1, invalidos=2)
        self.assertEqual((r.estado, r.rondas), ('correcto', 3))

    def test_tool_equivocada_es_incorrecto(self):
        caso = next(c for c in CASOS if c['id'] == 11)
        r = evaluar(self.usuario, [caso], cliente_llm=_guion(
            {caso['texto']: ('consultar_venta', {'cliente_query': 'lg'})}))[0]
        self.assertEqual(r.estado, 'incorrecto')
        self.assertIn('tool final', r.fallos[0])

    def test_producto_ambiguo_sin_opciones_es_parcial(self):
        """Si alguien borra un monitor LG, el ítem ya no es ambiguo: el eval lo detecta."""
        from apps.inventario.models.producto import Producto
        Producto.objects.filter(empresa=self.empresa, sku='LG27').update(is_active=False)
        caso = next(c for c in CASOS if c['id'] == 16)
        r = evaluar(self.usuario, [caso], cliente_llm=_guion())[0]
        self.assertEqual(r.estado, 'parcial')

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

    def test_umbral_exige_consultas_de_maximo_2_rondas(self):
        """18/20 correctos NO basta si alguna consulta pasó de 2 rondas."""
        from apps.canales.eval import runner
        real = runner.evaluar

        def con_una_lenta(usuario, casos, cliente_llm=None):
            res = real(usuario, casos, cliente_llm)
            r = next(r for r in res if r.id == 5)
            r.rondas = 3            # simula una consulta lenta que, aun así, acertó
            return res

        err = StringIO()
        with mock.patch('apps.canales.nucleo.interprete.get_llm_client', return_value=_guion()), \
             mock.patch('apps.canales.management.commands.eval_agente.evaluar', side_effect=con_una_lenta):
            with self.assertRaises(SystemExit):
                call_command('eval_agente', email='demo@eval.pe', stdout=StringIO(), stderr=err)
        self.assertIn('consulta(s) con >2 rondas', err.getvalue())

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
