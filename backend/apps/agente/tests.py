"""
Tests del MCP base (Fase 2): aislamiento por empresa, 401 (sin token / revocado /
expirado), auditoría por llamada y rate limit.
"""
import json
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.agente.models import AgenteAccionLog, ApiToken
from apps.agente.throttling import MCPTokenThrottle
from apps.cotizaciones.models import Cotizacion, DetalleCotizacion
from apps.empresas.models import Empresa
from apps.inventario.models.producto import Producto
from apps.ventas.models import Cliente, Venta

User = get_user_model()
LOCMEM = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
MCP_URL = '/api/mcp/'


def rpc_call(name, arguments=None, rpc_id=1):
    return {'jsonrpc': '2.0', 'id': rpc_id, 'method': 'tools/call',
            'params': {'name': name, 'arguments': arguments or {}}}


@override_settings(CACHES=LOCMEM)
class MCPTestBase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.empA = Empresa.objects.create(nombre='Empresa A', ruc='20100000001')
        self.empB = Empresa.objects.create(nombre='Empresa B', ruc='20100000002')
        self.userA = self._user('a@a.pe', self.empA)
        self.userB = self._user('b@b.pe', self.empB)
        self.tokA_obj, self.tokA = ApiToken.generar(self.empA, 'A', creado_por=self.userA)
        self.tokB_obj, self.tokB = ApiToken.generar(self.empB, 'B', creado_por=self.userB)
        self._seed(self.empA, self.userA, '20111111111', 'clienteA@x.pe')
        self._seed(self.empB, self.userB, '20122222222', 'clienteB@x.pe')

    def _user(self, email, empresa):
        u = User(email=email, username=email)
        u.set_password('x')
        u.empresa = empresa
        u.save()
        return u

    def _seed(self, emp, user, documento, email):
        cliente = Cliente.objects.create(
            empresa=emp, nombre=f'Cliente {emp.nombre}', documento=documento,
            tipo_documento='ruc', email=email, telefono='999888777')
        producto = Producto.objects.create(empresa=emp, sku=f'SKU-{emp.id}', nombre='ItemDemo')
        # Venta esperando OC/NR del cliente
        Venta.objects.create(
            empresa=emp, numero=f'V-{emp.id}', cliente=cliente, fecha_emision=date.today(),
            estado_operativo='esperando_oc_nr', total=Decimal('100.00'), moneda='PEN')
        # Cotización con un detalle (para historial de precios)
        cot = Cotizacion.objects.create(
            empresa=emp, cliente=cliente, usuario_creador=user, asunto='Pedido',
            fecha_vencimiento=date.today() + timedelta(days=30), moneda='PEN')
        DetalleCotizacion.objects.create(
            cotizacion=cot, producto=producto, cantidad=Decimal('1'),
            precio_unitario=Decimal('99.00'), costo_unitario=Decimal('60.00'),
            descripcion='ItemDemo')

    def call(self, token, name, arguments=None):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return self.client.post(MCP_URL, rpc_call(name, arguments), format='json')

    def payload(self, res):
        text = res.json()['result']['content'][0]['text']
        return json.loads(text)


class AuthTests(MCPTestBase):
    def test_sin_token_401(self):
        self.client.credentials()
        res = self.client.post(MCP_URL, {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize'}, format='json')
        self.assertEqual(res.status_code, 401)

    def test_token_invalido_401(self):
        res = self.call('sgm_tokeninventado', 'buscar_cliente', {'texto': 'x'})
        self.assertEqual(res.status_code, 401)

    def test_token_revocado_401(self):
        self.tokA_obj.revocar()
        res = self.call(self.tokA, 'buscar_cliente', {'texto': 'x'})
        self.assertEqual(res.status_code, 401)

    def test_token_expirado_401(self):
        self.tokA_obj.expires_at = timezone.now() - timedelta(days=1)
        self.tokA_obj.save(update_fields=['expires_at'])
        res = self.call(self.tokA, 'buscar_cliente', {'texto': 'x'})
        self.assertEqual(res.status_code, 401)

    def test_initialize_y_tools_list(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tokA}')
        ini = self.client.post(MCP_URL, {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize'}, format='json')
        self.assertEqual(ini.status_code, 200)
        self.assertIn('serverInfo', ini.json()['result'])
        lst = self.client.post(MCP_URL, {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'}, format='json')
        nombres = {t['name'] for t in lst.json()['result']['tools']}
        self.assertEqual(nombres, {'buscar_cliente', 'historial_precios_item',
                                   'ventas_esperando_oc_nr', 'listar_propuestas_pendientes'})


class TenantIsolationTests(MCPTestBase):
    def test_buscar_cliente_aislado(self):
        # A busca "Cliente" → ve solo su cliente; nunca el de B.
        data = self.payload(self.call(self.tokA, 'buscar_cliente', {'texto': 'Cliente'}))
        rucs = {c['ruc'] for c in data['clientes']}
        self.assertIn('20111111111', rucs)
        self.assertNotIn('20122222222', rucs)

    def test_ventas_esperando_oc_nr_aislado(self):
        data = self.payload(self.call(self.tokA, 'ventas_esperando_oc_nr'))
        numeros = {v['numero'] for v in data['ventas']}
        self.assertIn(f'V-{self.empA.id}', numeros)
        self.assertNotIn(f'V-{self.empB.id}', numeros)
        # B ve lo suyo, no lo de A
        dataB = self.payload(self.call(self.tokB, 'ventas_esperando_oc_nr'))
        numerosB = {v['numero'] for v in dataB['ventas']}
        self.assertEqual(numerosB, {f'V-{self.empB.id}'})

    def test_historial_precios_aislado(self):
        data = self.payload(self.call(self.tokA, 'historial_precios_item', {'descripcion': 'ItemDemo'}))
        # Debe haber al menos la cotización de A; ninguna entrada debe venir de otra empresa.
        self.assertTrue(any(e['fuente'] == 'cotizacion' for e in data['entradas']))
        # B tiene su propio historial, no el de A (mismo nombre de ítem, distinta empresa).
        dataB = self.payload(self.call(self.tokB, 'historial_precios_item', {'descripcion': 'ItemDemo'}))
        # Cada empresa ve solo 1 cotización (la suya).
        self.assertEqual(len([e for e in data['entradas'] if e['fuente'] == 'cotizacion']), 1)
        self.assertEqual(len([e for e in dataB['entradas'] if e['fuente'] == 'cotizacion']), 1)

    def test_listar_propuestas_vacio(self):
        data = self.payload(self.call(self.tokA, 'listar_propuestas_pendientes'))
        self.assertEqual(data['propuestas'], [])


class AuditTests(MCPTestBase):
    def test_cada_llamada_genera_log(self):
        self.assertEqual(AgenteAccionLog.objects.count(), 0)
        self.call(self.tokA, 'buscar_cliente', {'texto': 'Cliente'})
        self.call(self.tokA, 'ventas_esperando_oc_nr')
        logs = AgenteAccionLog.objects.all()
        self.assertEqual(logs.count(), 2)
        log = logs.filter(herramienta='buscar_cliente').first()
        self.assertEqual(log.empresa_id, self.empA.id)
        self.assertEqual(log.token_id, self.tokA_obj.id)
        self.assertTrue(log.ok)
        self.assertEqual(log.argumentos, {'texto': 'Cliente'})
        self.assertTrue(log.resultado_resumen)  # p. ej. "1 clientes"

    def test_initialize_no_genera_log(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tokA}')
        self.client.post(MCP_URL, {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}, format='json')
        self.assertEqual(AgenteAccionLog.objects.count(), 0)


class RateLimitTests(MCPTestBase):
    # DRF fija THROTTLE_RATES en import, así que override_settings no llega al throttle;
    # parcheamos el rate directo en la clase del throttle (lo reduce de 60/min).
    def test_rate_limit(self):
        cache.clear()
        with mock.patch.object(MCPTokenThrottle, 'THROTTLE_RATES', {'mcp': '3/min'}):
            for i in range(3):
                res = self.call(self.tokA, 'ventas_esperando_oc_nr')
                self.assertEqual(res.status_code, 200, f'llamada {i} debería pasar')
            res = self.call(self.tokA, 'ventas_esperando_oc_nr')
            self.assertEqual(res.status_code, 429)

    def test_rate_limit_por_token(self):
        # El límite es por token: agotar A no bloquea a B.
        cache.clear()
        with mock.patch.object(MCPTokenThrottle, 'THROTTLE_RATES', {'mcp': '2/min'}):
            for _ in range(2):
                self.call(self.tokA, 'ventas_esperando_oc_nr')
            blocked = self.call(self.tokA, 'ventas_esperando_oc_nr')
            self.assertEqual(blocked.status_code, 429)
            ok_b = self.call(self.tokB, 'ventas_esperando_oc_nr')
            self.assertEqual(ok_b.status_code, 200)
