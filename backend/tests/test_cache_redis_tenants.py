"""
A3 — Aislamiento de caché con Redis REAL (no LocMem).

Requiere un Redis en REDIS_TEST_URL (por defecto redis://localhost:6379/1; p. ej.
`docker run -d --name erp-test-redis -p 6379:6379 redis:7`). Si no responde, se omite.

Escenario: A "calienta" la caché (dashboard, productos, ventas, compras, proveedores);
después B pide lo mismo y debe ver SOLO lo suyo: su respuesta "caliente" (tras A) es
idéntica a su respuesta "fría" (caché vacía) y distinta a la de A.
"""
import os
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.compras.models import Compra, Proveedor
from apps.empresas.models import Empresa
from apps.inventario.models.almacen import Almacen
from apps.inventario.models.producto import Producto
from apps.ventas.models import Cliente, Venta

User = get_user_model()
REDIS_TEST_URL = os.getenv('REDIS_TEST_URL', 'redis://localhost:6379/1')
CACHES_REDIS = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_TEST_URL,
        'KEY_PREFIX': 'erp_test',
        'TIMEOUT': 300,
    }
}

# Endpoints que cachean por empresa (ver grep de cache.get/set en apps/*/views.py).
ENDPOINTS = [
    '/api/dashboard/resumen/',
    '/api/dashboard/resumen-historico/',
    '/api/dashboard/stats/30/',
    '/api/inventario/productos/',
    '/api/ventas/',
    '/api/compras/compras/',
    '/api/compras/proveedores/',
]


def _redis_disponible():
    try:
        import redis
        redis.Redis.from_url(REDIS_TEST_URL, socket_connect_timeout=1).ping()
        return True
    except Exception:
        return False


@override_settings(ROOT_URLCONF='config.urls', CACHES=CACHES_REDIS)
class CacheRedisAislamientoTests(TestCase):
    def setUp(self):
        if not _redis_disponible():
            self.skipTest(f'Redis no disponible en {REDIS_TEST_URL}')
        cache.clear()
        self.client = APIClient()
        self.A = Empresa.objects.create(nombre='Empresa A', ruc='20000000001')
        self.B = Empresa.objects.create(nombre='Empresa B', ruc='20000000002')
        self.user_a = self._user('a@a.pe', self.A)
        self.user_b = self._user('b@b.pe', self.B)
        self._seed(self.A, 'A', Decimal('1000'))
        self._seed(self.B, 'B', Decimal('7'))

    def tearDown(self):
        cache.clear()

    def _user(self, email, empresa):
        u = User(email=email, username=email); u.set_password('x'); u.empresa = empresa; u.save()
        return u

    def _seed(self, empresa, tag, total):
        cli = Cliente.objects.create(empresa=empresa, nombre=f'Cliente {tag}', documento=f'1000000000{1 if tag == "A" else 2}', tipo_documento='ruc')
        Venta.objects.create(empresa=empresa, cliente=cli, fecha_emision=date.today(), total=total, moneda='PEN')
        Producto.objects.create(empresa=empresa, sku=f'SKU-{tag}', nombre=f'Prod {tag}')
        prov = Proveedor.objects.create(empresa=empresa, razon_social=f'Prov {tag}', ruc=f'2000000001{1 if tag == "A" else 2}')
        alm = Almacen.objects.create(empresa=empresa, nombre=f'Alm {tag}')
        c = Compra.objects.create(empresa=empresa, proveedor=prov, almacen=alm, fecha_emision=date.today())
        Compra.objects.filter(pk=c.pk).update(total=total)

    def _get(self, user, url):
        self.client.force_authenticate(user)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200, f'{url}: {r.status_code} {r.content[:200]}')
        return r.json()

    def test_B_solo_ve_lo_suyo_tras_calentar_A(self):
        fallos = []
        for url in ENDPOINTS:
            cache.clear()
            frio_b = self._get(self.user_b, url)       # respuesta de B sin caché
            cache.clear()
            caliente_a = self._get(self.user_a, url)   # A calienta la caché
            caliente_b = self._get(self.user_b, url)   # B pide lo mismo
            if caliente_b != frio_b:
                fallos.append(f'{url}: B caliente != B frío → {str(caliente_b)[:160]}')
            if caliente_b == caliente_a:
                fallos.append(f'{url}: B recibió la respuesta cacheada de A')
            texto = str(caliente_b)
            for marca in ('Cliente A', 'SKU-A', 'Prod A', 'Prov A'):
                if marca in texto:
                    fallos.append(f'{url}: la respuesta de B contiene "{marca}"')
        self.assertEqual(fallos, [], '\n'.join(fallos))

    def test_claves_en_redis_llevan_empresa(self):
        """Cada clave que el ERP escribe en Redis contiene el id de la empresa."""
        import redis
        r = redis.Redis.from_url(REDIS_TEST_URL)
        cache.clear()
        for url in ENDPOINTS:
            self._get(self.user_a, url)
        claves = [k.decode() for k in r.keys('*erp_test*')]
        self.assertTrue(claves, 'A no escribió ninguna clave en Redis')
        sin_empresa = [k for k in claves if str(self.A.id) not in k]
        self.assertEqual(sin_empresa, [], f'claves sin empresa_id: {sin_empresa}')

    def test_crear_producto_invalida_lista_de_su_empresa(self):
        """Regresión: ProductoViewSet.list cacheaba 'productos_list:<id>' pero
        invalidate_productos borraba 'productos:<id>' → lista rancia 2 min."""
        antes = self._get(self.user_a, '/api/inventario/productos/')
        self.client.force_authenticate(self.user_a)
        r = self.client.post('/api/inventario/productos/', {'sku': 'SKU-A2', 'nombre': 'Nuevo A', 'precio_venta': '10.00'}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        despues = self._get(self.user_a, '/api/inventario/productos/')
        self.assertNotEqual(antes, despues, 'la lista de productos siguió cacheada tras crear uno')
        self.assertIn('SKU-A2', str(despues))
        # ...y la caché de B sigue intacta (no se hizo cache.clear() global).
        self._get(self.user_b, '/api/inventario/productos/')
        import redis
        claves_b = [k for k in redis.Redis.from_url(REDIS_TEST_URL).keys('*erp_test*') if str(self.B.id) in k.decode()]
        self.assertTrue(claves_b)
