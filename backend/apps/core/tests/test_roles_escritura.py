"""
Router-walk de escrituras con rol solo_lectura → 100 % 403.

Recorre TODA la URLconf de /api/ y, para cada ruta de un viewset de negocio,
intenta cada método de escritura que la ruta soporta con un usuario
solo_lectura. Cualquier respuesta distinta de 403 es un fallo: si mañana se
registra un viewset nuevo sin RolEscritura, este test lo descubre solo.
"""
from django.contrib.auth import get_user_model
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.test import APIClient, APITestCase

from apps.empresas.models import Empresa

User = get_user_model()

METODOS_ESCRITURA = ('post', 'put', 'patch', 'delete')

# Prefijos de negocio que DEBEN estar cerrados para solo_lectura (0.1).
PREFIJOS_NEGOCIO = (
    'api/ventas', 'api/cotizaciones', 'api/compras', 'api/guias',
    'api/servicios', 'api/inventario', 'api/finanzas', 'api/produccion',
    # REVIEW_BOT #1/#2/#8: también escriben negocio y quedaban fuera
    'api/importador', 'api/core', 'api/empresas', 'api/agente',
)

# Rutas bajo los prefijos que no son escrituras de negocio: la autenticación
# es pública por diseño (login/refresh/verify emiten o validan tokens).
EXCLUIR = ('api/core/token', 'api/core/auth/')


def _rutas_api(resolver=None, prefijo=''):
    """[(ruta, callback)] para toda la URLconf, con el path completo."""
    resolver = resolver or get_resolver()
    rutas = []
    for p in resolver.url_patterns:
        if isinstance(p, URLResolver):
            rutas += _rutas_api(p, prefijo + str(p.pattern))
        elif isinstance(p, URLPattern):
            rutas.append((prefijo + str(p.pattern), p.callback))
    return rutas


def _concretar(ruta):
    """Sustituye parámetros de URL por valores dummy (pk inexistente: la
    permission corre antes que el 404, así que 403 sigue siendo lo esperado)."""
    import re
    ruta = re.sub(r'\(\?P<[^>]+>[^)]+\)', '999999', ruta)   # regex groups
    ruta = re.sub(r'<[^>]+>', '999999', ruta)                 # path converters
    ruta = ruta.replace('^', '').replace('$', '')
    ruta = re.sub(r'/\?$', '/', ruta)                          # «/?» opcional del router
    url = '/' + ruta.lstrip('/')
    return url if url.endswith('/') else url + '/'


class RolesEscrituraRouterWalkTests(APITestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre='Empresa Roles', ruc='20999999991')
        cls.lector = User.objects.create_user(
            username='lector@roles.test', email='lector@roles.test',
            password='x', nombre='Solo', apellido='Lectura',
            empresa=cls.empresa, rol='solo_lectura',
        )
        cls.operador = User.objects.create_user(
            username='operador@roles.test', email='operador@roles.test',
            password='x', nombre='Ope', apellido='Rador',
            empresa=cls.empresa, rol='operador',
        )

    def _rutas_negocio(self):
        vistas = []
        for ruta, cb in _rutas_api():
            if not ruta.startswith(PREFIJOS_NEGOCIO):
                continue
            if any(e in ruta for e in EXCLUIR):
                continue
            # las rutas con sufijo de formato («.json») duplican las normales
            if 'format' in ruta:
                continue
            # métodos que la ruta realmente acepta
            acciones = getattr(cb, 'actions', None)  # viewsets
            if acciones:
                metodos = [m for m in acciones if m in METODOS_ESCRITURA]
            else:
                cls = getattr(cb, 'view_class', None) or getattr(cb, 'cls', None)
                metodos = [m for m in METODOS_ESCRITURA if cls and hasattr(cls, m)]
            if metodos:
                vistas.append((ruta, metodos))
        return vistas

    def test_solo_lectura_recibe_403_en_toda_escritura(self):
        rutas = self._rutas_negocio()
        self.assertGreater(len(rutas), 25, 'el walk no encontró rutas: ¿cambió la URLconf?')
        self.client.force_authenticate(self.lector)
        abiertas = []
        for ruta, metodos in rutas:
            url = _concretar(ruta)
            for metodo in metodos:
                resp = getattr(self.client, metodo)(url, {}, format='json')
                if resp.status_code != 403:
                    abiertas.append(f'{metodo.upper()} {url} → {resp.status_code}')
        self.assertEqual(abiertas, [], 'escrituras abiertas para solo_lectura:\n' + '\n'.join(abiertas))

    def test_solo_lectura_puede_leer(self):
        self.client.force_authenticate(self.lector)
        for url in ('/api/ventas/', '/api/cotizaciones/', '/api/compras/'):
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, f'GET {url} → {resp.status_code}')

    def test_operador_no_queda_bloqueado(self):
        """El cierre es por rol, no un cierre global: un operador sí escribe."""
        self.client.force_authenticate(self.operador)
        resp = self.client.post('/api/ventas/clientes/', {
            'nombre': 'Cliente Operador', 'documento': '45678912',
            'tipo_documento': 'dni',
        }, format='json')
        self.assertIn(resp.status_code, (200, 201), resp.content)

    def test_acciones_custom_cerradas(self):
        """Las @action de dinero/estado devuelven 403 para solo_lectura."""
        self.client.force_authenticate(self.lector)
        for url in (
            '/api/ventas/1/cambiar-estado-operativo/',
            '/api/ventas/1/pagos/',
            '/api/cotizaciones/1/duplicar/',
            '/api/cotizaciones/1/cambiar-estado/',
        ):
            resp = self.client.post(url, {}, format='json')
            self.assertEqual(resp.status_code, 403, f'POST {url} → {resp.status_code}')
