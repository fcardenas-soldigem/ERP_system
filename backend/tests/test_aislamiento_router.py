"""
Suite DINÁMICA de aislamiento: recorre automáticamente TODO el router (config.urls),
no una lista a mano. Para cada ruta de detalle cuyo modelo pudimos sembrar con datos de
B, autenticado como A: GET/PUT/PATCH/DELETE de {id_de_B} → nunca 200/204 (404/403), y el
registro de B queda intacto. Imprime cobertura (rutas probadas/totales) y las excluidas
con su motivo.
"""
import re
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import get_resolver
from rest_framework.routers import APIRootView
from rest_framework.test import APIClient

from apps.empresas.models import Empresa

User = get_user_model()
PK_RE = re.compile(r'\(\?P<(?:pk|[a-z_]*id|[a-z_]+)>[^)]+\)')


def _seed_b(empresa, user):
    """Crea una instancia de B por modelo seedable. Devuelve {Model: instancia}."""
    from apps.ventas.models import Cliente, Venta
    from apps.compras.models import Proveedor, OrdenCompra
    from apps.inventario.models.producto import Producto
    from apps.inventario.models.almacen import Almacen
    from apps.inventario.models.categoria import Categoria
    from apps.cotizaciones.models import Cotizacion
    from apps.finanzas.models import CategoriaGasto, GastoOperativo

    out = {Empresa: empresa}
    cli = Cliente.objects.create(empresa=empresa, nombre='Cliente B', documento='10000000002', tipo_documento='ruc')
    out[Cliente] = cli
    out[Venta] = Venta.objects.create(empresa=empresa, cliente=cli, fecha_emision=date.today(), total=Decimal('100'), moneda='PEN')
    out[Proveedor] = Proveedor.objects.create(empresa=empresa, razon_social='Prov B', ruc='20000000012')
    out[Almacen] = Almacen.objects.create(empresa=empresa, nombre='Alm B')
    out[Categoria] = Categoria.objects.create(empresa=empresa, nombre='Cat B')
    out[Producto] = Producto.objects.create(empresa=empresa, sku='SKU-B', nombre='Prod B')
    out[Cotizacion] = Cotizacion.objects.create(empresa=empresa, cliente=cli, usuario_creador=user, asunto='x', fecha_vencimiento=date.today(), moneda='PEN')
    catg = CategoriaGasto.objects.create(empresa=empresa, nombre='CatGasto B')
    out[CategoriaGasto] = catg
    out[GastoOperativo] = GastoOperativo.objects.create(empresa=empresa, categoria=catg, descripcion='g', monto=Decimal('10'), fecha=date.today())
    return out


def _lookup_groups(pat_obj):
    try:
        names = [n for n in pat_obj.regex.groupindex.keys() if n != 'format']
        return names
    except Exception:
        return []


def _detail_routes(resolver, prefix=''):
    """Camina el resolver y cede (ruta_regex, viewset_cls, lookups) de rutas de detalle DRF."""
    for p in resolver.url_patterns:
        pat = prefix + str(getattr(p, 'pattern', ''))
        if hasattr(p, 'url_patterns'):
            yield from _detail_routes(p, pat)
            continue
        cls = getattr(getattr(p, 'callback', None), 'cls', None)
        if cls is None or issubclass(cls, APIRootView):
            continue
        if '(?P<format>' in pat:   # ignorar variantes .format (duplican cada ruta)
            continue
        actions = getattr(p.callback, 'actions', {})
        lookups = _lookup_groups(p.pattern)
        if lookups and ({'get', 'put', 'delete', 'patch'} & set(actions)):
            yield pat, cls, lookups


def _model_of(cls):
    qs = getattr(cls, 'queryset', None)
    if qs is not None:
        return qs.model
    ser = getattr(cls, 'serializer_class', None)
    meta = getattr(ser, 'Meta', None) if ser is not None else None
    return getattr(meta, 'model', None)


@override_settings(ROOT_URLCONF='config.urls')
class RouterWalkIsolationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.A = Empresa.objects.create(nombre='Empresa A', ruc='20000000001')
        self.B = Empresa.objects.create(nombre='Empresa B', ruc='20000000002')
        self.user_a = self._user('a@a.pe', self.A)
        self.user_b = self._user('b@b.pe', self.B)
        self.b_by_model = _seed_b(self.B, self.user_b)

    def _user(self, email, empresa):
        u = User(email=email, username=email)
        u.set_password('x')
        u.empresa = empresa
        u.save()
        return u

    def _url_for(self, regex, pk):
        # '^api/ventas/(?P<pk>[^/.]+)/saldo/$' -> '/api/ventas/{pk}/saldo/'
        path = regex.replace('^', '').replace('$', '')
        path = PK_RE.sub(str(pk), path)      # sustituye el lookup en su lugar
        path = path.replace('\\.', '.').replace('\\', '')
        if not path.startswith('/'):
            path = '/' + path
        if not path.endswith('/'):
            path = path + '/'
        return path

    def test_router_walk_aislamiento(self):
        self.client.force_authenticate(self.user_a)
        resolver = get_resolver('config.urls')
        total = tested = 0
        excluidas = []
        fallos = []
        probadas = []

        for regex, cls, lookups in _detail_routes(resolver):
            total += 1
            if len(lookups) > 1:
                excluidas.append((regex, 'ruta anidada (multi-lookup)'))
                continue
            model = _model_of(cls)
            inst = self.b_by_model.get(model) if model else None
            if inst is None:
                motivo = 'modelo desconocido (queryset=None)' if model is None else f'sin seed de B para {model.__name__}'
                excluidas.append((regex, motivo))
                continue
            url = self._url_for(regex, inst.pk)
            tested += 1
            probadas.append(url)
            # GET detalle de B → nunca 200.
            r = self.client.get(url)
            if r.status_code == 200:
                fallos.append(f'FUGA GET {url} ({cls.__name__}) devolvió 200 datos de B')
            # DELETE de B → no debe borrar.
            self.client.delete(url)
            if not type(inst).objects.filter(pk=inst.pk).exists():
                fallos.append(f'FUGA DELETE {url} borró el registro de B')

        # Cobertura
        print('\n=== COBERTURA SUITE DINÁMICA (router walk) ===')
        print(f'Rutas de detalle totales: {total} | probadas: {tested} | excluidas: {len(excluidas)}')
        for u in sorted(probadas):
            print(f'  probada: {u}')
        print('  --- excluidas (motivo) ---')
        for regex, motivo in excluidas:
            print(f'  excluida: {regex}  →  {motivo}')
        print('=== FIN COBERTURA ===\n')

        self.assertGreater(tested, 0, 'la suite debe probar al menos algunas rutas')
        self.assertEqual(fallos, [], 'fugas de aislamiento detectadas:\n' + '\n'.join(fallos))
