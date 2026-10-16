"""
B1 — Registro de una empresa nueva END-TO-END (lo que hará el 2.º tenant).

Flujo real sobre Postgres y URLconf real:
  alta (servicio/comando crear_tenant) → login (/api/auth/login/) → perfil
  (/api/auth/profile/) → crear 1 cotización, 1 venta y 1 orden de compra por la API
  → la numeración del tenant nuevo empieza en 1 y NO choca con la empresa 1.
También: un usuario sin empresa NO puede entrar (antes el login lo colgaba de la
primera empresa del sistema).
"""
import os
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.compras.models import OrdenCompra, Proveedor
from apps.cotizaciones.models import Cotizacion
from apps.empresas.models import Empresa
from apps.empresas.services import registrar_empresa
from apps.inventario.models.producto import Producto
from apps.ventas.models import Cliente, Venta

User = get_user_model()
LOCMEM = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}


@override_settings(ROOT_URLCONF='config.urls', CACHES=LOCMEM)
class RegistroTenantE2ETests(TestCase):
    def setUp(self):
        # Sin red: el tipo de cambio SBS se fija (lo consultan Venta/Cotización/OC al guardar).
        patcher = mock.patch('apps.core.services.tipo_cambio.get_tc_venta', return_value=Decimal('3.70'))
        patcher.start(); self.addCleanup(patcher.stop)
        self.client = APIClient()
        # Empresa 1 ya operando, con documentos numerados.
        self.emp1 = Empresa.objects.create(nombre='Soldigem', ruc='20603231717')
        self.user1 = User(email='u1@soldigem.pe', username='u1@soldigem.pe', empresa=self.emp1, rol='admin')
        self.user1.set_password('clave-segura-1'); self.user1.save()
        self.cli1 = Cliente.objects.create(empresa=self.emp1, nombre='Cliente 1', documento='10000000001', tipo_documento='ruc')
        self.prod1 = Producto.objects.create(empresa=self.emp1, sku='P1', nombre='Prod 1', precio_venta=Decimal('10'))
        self.prov1 = Proveedor.objects.create(empresa=self.emp1, razon_social='Prov 1', ruc='20000000011')
        self.cot1 = Cotizacion.objects.create(empresa=self.emp1, cliente=self.cli1, usuario_creador=self.user1,
                                              asunto='x', fecha_vencimiento=date.today(), moneda='PEN')
        self.venta1 = Venta.objects.create(empresa=self.emp1, cliente=self.cli1, fecha_emision=date.today(), total=Decimal('1'), moneda='PEN')
        self.oc1 = OrdenCompra.objects.create(empresa=self.emp1, proveedor=self.prov1, fecha_entrega=date.today())
        self.assertEqual((self.cot1.numero, self.venta1.numero, self.oc1.numero), ('COT-00000001', 'V-000001', '000001'))

    # ---------- helpers ----------
    def _login(self, email, password):
        self.client.credentials()
        return self.client.post('/api/auth/login/', {'email': email, 'password': password}, format='json')

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    # ---------- tests ----------
    def test_alta_login_perfil_y_primeros_documentos(self):
        # 1) Alta del tenant nuevo (equivale a `manage.py crear_tenant`).
        emp2, admin2 = registrar_empresa(
            nombre='Empresa Dos SAC', ruc='20123456789', admin_email='Admin@Dos.pe',
            admin_password='clave-segura-2', admin_nombre='Ana', admin_apellido='Pérez')
        self.assertEqual(admin2.empresa_id, emp2.id)
        self.assertEqual(admin2.rol, 'admin')
        self.assertFalse(admin2.is_superuser); self.assertFalse(admin2.is_staff)
        self.assertEqual(admin2.email, 'admin@dos.pe')

        # 2) Login.
        r = self._login('admin@dos.pe', 'clave-segura-2')
        self.assertEqual(r.status_code, 200, r.content)
        token = r.json()['token']
        self.assertEqual(r.json()['user']['empresa'], emp2.id)

        # 3) Perfil: ve SU empresa.
        self._auth(token)
        p = self.client.get('/api/auth/profile/')
        self.assertEqual(p.status_code, 200, p.content)
        self.assertEqual(p.json()['empresa'], emp2.id)
        self.assertEqual(p.json()['empresa_data']['ruc'], '20123456789')

        # 4) Maestros propios por la API.
        rc = self.client.post('/api/ventas/clientes/', {'nombre': 'Cliente Dos', 'documento': '20999999991', 'tipo_documento': 'ruc'}, format='json')
        self.assertEqual(rc.status_code, 201, rc.content); cli2 = rc.json()['id']
        rp = self.client.post('/api/inventario/productos/', {'sku': 'D-1', 'nombre': 'Prod Dos', 'precio_venta': '25.00', 'tipo_producto': 'FINISHED'}, format='json')
        self.assertEqual(rp.status_code, 201, rp.content); prod2 = rp.json()['id']
        rpv = self.client.post('/api/compras/proveedores/', {'razon_social': 'Prov Dos', 'ruc': '20999999992'}, format='json')
        self.assertEqual(rpv.status_code, 201, rpv.content); prov2 = rpv.json()['id']

        # 5) 1 COT, 1 V, 1 OC por la API → numeración desde 1.
        rcot = self.client.post('/api/cotizaciones/', {
            'cliente': cli2, 'asunto': 'Primera cotización', 'moneda': 'PEN',
            'fecha_vencimiento': str(date.today() + timedelta(days=15)),
            'detalles': [{'producto': prod2, 'cantidad': '2', 'precio_unitario': '25.00', 'descripcion': 'Prod Dos'}],
        }, format='json')
        self.assertEqual(rcot.status_code, 201, rcot.content)
        self.assertEqual(rcot.json()['numero'], 'COT-00000001')
        self.assertEqual(Cotizacion.objects.get(pk=rcot.json()['id']).empresa_id, emp2.id)

        rv = self.client.post('/api/ventas/', {
            'cliente': cli2, 'fecha_emision': str(date.today()), 'moneda': 'PEN',
            'tipo_venta': 'contado', 'metodo_pago': 'efectivo',
            'detalles': [{'producto': prod2, 'cantidad': '1', 'precio_unitario': '25.00'}],
        }, format='json')
        self.assertEqual(rv.status_code, 201, rv.content)
        self.assertEqual(rv.json()['numero'], 'V-000001')
        self.assertEqual(rv.json()['empresa'], emp2.id)

        roc = self.client.post('/api/compras/ordenes/', {
            'proveedor': prov2, 'fecha_emision': str(date.today()), 'fecha_entrega': str(date.today()),
            'moneda': 'PEN',
            'detalles': [{'producto': prod2, 'cantidad': '1', 'precio_unitario': '20.00'}],
        }, format='json')
        self.assertEqual(roc.status_code, 201, roc.content)
        self.assertEqual(roc.json()['numero'], '000001')
        self.assertEqual(roc.json()['empresa'], emp2.id)

        # 6) La empresa 1 sigue con su propia secuencia (no se la "comió" el tenant 2).
        cot1b = Cotizacion.objects.create(empresa=self.emp1, cliente=self.cli1, usuario_creador=self.user1,
                                          asunto='y', fecha_vencimiento=date.today(), moneda='PEN')
        v1b = Venta.objects.create(empresa=self.emp1, cliente=self.cli1, fecha_emision=date.today(), total=Decimal('1'), moneda='PEN')
        oc1b = OrdenCompra.objects.create(empresa=self.emp1, proveedor=self.prov1, fecha_entrega=date.today())
        self.assertEqual((cot1b.numero, v1b.numero, oc1b.numero), ('COT-00000002', 'V-000002', '000002'))
        # ...y el tenant 2 no ve nada de la 1.
        lv = self.client.get('/api/ventas/').json()
        self.assertEqual([v['numero'] for v in lv['results']], ['V-000001'])
        self.assertEqual(Venta.objects.filter(empresa=emp2).count(), 1)

    def test_comando_crear_tenant(self):
        out = StringIO()
        os.environ['TENANT_ADMIN_PASSWORD'] = 'clave-segura-3'
        try:
            call_command('crear_tenant', '--nombre', 'Tres SAC', '--ruc', '20123456780', '--email', 'admin@tres.pe',
                         '--admin-nombre', 'Luis', '--admin-apellido', 'Q', '--sin-stock', stdout=out)
        finally:
            os.environ.pop('TENANT_ADMIN_PASSWORD', None)
        emp = Empresa.objects.get(ruc='20123456780')
        self.assertEqual(emp.modo_inventario, 'sin_stock')
        self.assertEqual(self._login('admin@tres.pe', 'clave-segura-3').status_code, 200)
        self.assertIn('creada', out.getvalue())

    def test_alta_rechaza_duplicados(self):
        kw = dict(admin_password='clave-segura-9', admin_nombre='x', admin_apellido='y')
        with self.assertRaises(ValidationError):
            registrar_empresa(nombre='Dup', ruc='20603231717', admin_email='nuevo@x.pe', **kw)  # RUC de emp1
        with self.assertRaises(ValidationError):
            registrar_empresa(nombre='Dup', ruc='20123456781', admin_email='U1@soldigem.pe', **kw)  # email existente
        with self.assertRaises(ValidationError):
            registrar_empresa(nombre='Dup', ruc='123', admin_email='z@x.pe', **kw)  # RUC inválido
        self.assertEqual(Empresa.objects.count(), 1)
        self.assertEqual(User.objects.count(), 1)

    def test_usuario_sin_empresa_no_entra_ni_cae_en_la_primera(self):
        # (a) Al guardar un usuario sin empresa, una señal le crea una empresa PROPIA
        #     (nunca lo cuelga de la empresa 1).
        huerfano = User(email='h@h.pe', username='h@h.pe', empresa=None)
        huerfano.set_password('clave-segura-h'); huerfano.save()
        huerfano.refresh_from_db()
        self.assertNotEqual(huerfano.empresa_id, self.emp1.id)
        # (b) Un usuario REALMENTE sin empresa (p. ej. empresa borrada → SET_NULL) no entra
        #     y el login ya NO lo asigna a Empresa.objects.first().
        User.objects.filter(pk=huerfano.pk).update(empresa=None)
        r = self._login('h@h.pe', 'clave-segura-h')
        self.assertEqual(r.status_code, 403, r.content)
        huerfano.refresh_from_db()
        self.assertIsNone(huerfano.empresa_id, 'FUGA: el login asignó al usuario a la primera empresa')
