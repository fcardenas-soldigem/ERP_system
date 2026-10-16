"""
Suite DINÁMICA de aislamiento: recorre automáticamente TODO el router (config.urls),
no una lista a mano. Siembra datos de B en la mayor cantidad de modelos posible (incluye
rutas anidadas). Para cada ruta de detalle de B, autenticado como A: GET → nunca 200;
DELETE → no borra. Imprime cobertura (probadas/totales) y las excluidas con su motivo.
"""
import re
from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase, override_settings
from django.urls import get_resolver
from django.utils import timezone
from rest_framework.routers import APIRootView
from rest_framework.test import APIClient, APIRequestFactory

from apps.empresas.models import Empresa

User = get_user_model()
_factory = APIRequestFactory()
GROUP_RE = re.compile(r'\(\?P<([a-z_]+)>[^)]+\)')


def _mk(out, by_name, fn):
    """Crea una instancia de B aislada en un savepoint (si falla, se omite sin envenenar
    la transacción) y la ruta correspondiente queda excluida."""
    sid = transaction.savepoint()
    try:
        inst = fn()
        transaction.savepoint_commit(sid)
        out[type(inst)] = inst
        by_name[type(inst).__name__.lower()] = inst
    except Exception as e:  # noqa: BLE001
        try:
            transaction.savepoint_rollback(sid)
        except Exception:
            pass
        out.setdefault('_errores', []).append(str(e).splitlines()[0][:90])


def _seed_b(empresa, user):
    from apps.ventas.models import Cliente, Venta, PagoVenta, Factura, OrdenVenta
    from apps.compras.models import (Proveedor, Compra, OrdenCompra, OrdenServicioCompra,
                                     RecepcionCompra, PagoCompra)
    from apps.inventario.models.producto import Producto
    from apps.inventario.models.almacen import Almacen
    from apps.inventario.models.categoria import Categoria
    from apps.inventario.models.stock import Stock
    from apps.cotizaciones.models import Cotizacion
    from apps.finanzas.models import CategoriaGasto, GastoOperativo, GastoRecurrente
    from apps.guias.models import GuiaRemision
    from apps.servicios.models import OrdenServicio
    from apps.ai_assistant.models import Conversation, AIInsight
    from apps.core.models import Usuario, Perfil

    out, by_name = {Empresa: empresa}, {'empresa': empresa}
    cli = Cliente.objects.create(empresa=empresa, nombre='Cliente B', documento='10000000002', tipo_documento='ruc')
    out[Cliente] = cli; by_name['cliente'] = cli
    prov = Proveedor.objects.create(empresa=empresa, razon_social='Prov B', ruc='20000000012')
    out[Proveedor] = prov; by_name['proveedor'] = prov
    alm = Almacen.objects.create(empresa=empresa, nombre='Alm B')
    out[Almacen] = alm; by_name['almacen'] = alm
    cat = Categoria.objects.create(empresa=empresa, nombre='Cat B')
    out[Categoria] = cat; by_name['categoria'] = cat
    prod = Producto.objects.create(empresa=empresa, sku='SKU-B', nombre='Prod B')
    out[Producto] = prod; by_name['producto'] = prod
    venta = Venta.objects.create(empresa=empresa, cliente=cli, fecha_emision=date.today(), total=Decimal('100'), moneda='PEN')
    out[Venta] = venta; by_name['venta'] = venta
    catg = CategoriaGasto.objects.create(empresa=empresa, nombre='CatGasto B')
    out[CategoriaGasto] = catg; by_name['categoriagasto'] = catg

    _mk(out, by_name, lambda: Cotizacion.objects.create(empresa=empresa, cliente=cli, usuario_creador=user, asunto='x', fecha_vencimiento=date.today(), moneda='PEN'))
    _mk(out, by_name, lambda: GastoOperativo.objects.create(empresa=empresa, categoria=catg, descripcion='g', monto=Decimal('10'), fecha=date.today()))
    _mk(out, by_name, lambda: GastoRecurrente.objects.create(empresa=empresa, categoria=catg, descripcion='g', monto=Decimal('10')))
    _mk(out, by_name, lambda: Compra.objects.create(empresa=empresa, proveedor=prov, almacen=alm, fecha_emision=date.today()))
    _mk(out, by_name, lambda: OrdenCompra.objects.create(empresa=empresa, fecha_entrega=date.today()))
    _mk(out, by_name, lambda: OrdenServicioCompra.objects.create(empresa=empresa))
    if OrdenCompra in out:
        def _recepcion():
            oc = out[OrdenCompra]
            oc.estado = 'aprobada'
            oc.save(update_fields=['estado'])
            return RecepcionCompra.objects.create(orden=oc, recibido_por='x')
        _mk(out, by_name, _recepcion)
    if Compra in out:
        def _pagocompra():
            Compra.objects.filter(pk=out[Compra].pk).update(total=Decimal('1000'))
            out[Compra].refresh_from_db()
            return PagoCompra.objects.create(compra=out[Compra], monto=Decimal('10'))
        _mk(out, by_name, _pagocompra)

    def _pagoventa():
        Venta.objects.filter(pk=venta.pk).update(total=Decimal('1000'), pagos_total=Decimal('0'))
        venta.refresh_from_db()
        return PagoVenta.objects.create(venta=venta, fecha=date.today(), monto=Decimal('10'), metodo_pago='efectivo')
    _mk(out, by_name, _pagoventa)
    _mk(out, by_name, lambda: Factura.objects.create(venta=venta, cliente=cli, numero_factura='F-B1'))
    _mk(out, by_name, lambda: OrdenVenta.objects.create(empresa=empresa, cliente=cli, numero_orden='OV-B1', fecha_orden=date.today(), fecha_entrega=date.today(), subtotal=Decimal('10'), igv=Decimal('1'), total=Decimal('11')))
    _mk(out, by_name, lambda: GuiaRemision.objects.create(empresa=empresa, numero='G-B1', fecha_traslado=date.today(), motivo='traslado_tecnico', nombre_destinatario='x', direccion_origen='a', direccion_destino='b', creado_por=user))
    _mk(out, by_name, lambda: OrdenServicio.objects.create(empresa=empresa, cliente=cli, proveedor_reparacion=prov, creado_por=user))
    _mk(out, by_name, lambda: Stock.objects.create(empresa=empresa, producto=prod, almacen=alm))
    _mk(out, by_name, lambda: Conversation.objects.create(empresa=empresa, usuario=user))
    _mk(out, by_name, lambda: AIInsight.objects.create(empresa=empresa, tipo='resumen', contenido={'k': 'v'}))
    _mk(out, by_name, lambda: Usuario.objects.create(usuario=user, empresa=empresa, rol='readonly'))
    _mk(out, by_name, lambda: Perfil.objects.get_or_create(usuario=user)[0])
    from apps.agente.models import ApiToken
    _mk(out, by_name, lambda: ApiToken.generar(empresa, 'Token B', creado_por=user)[0])

    from django.apps import apps as djapps
    GM = djapps.get_model
    _mk(out, by_name, lambda: GM('inventario.AjusteInventario').objects.create(motivo='x', tipo='entrada', producto=prod, almacen=alm, cantidad=1, costo_unitario=Decimal('1')))
    _mk(out, by_name, lambda: GM('inventario.InventarioMateriasPrimas').objects.create(empresa=empresa, producto=prod, almacen=alm))
    _mk(out, by_name, lambda: GM('inventario.InventarioProductosTerminados').objects.create(empresa=empresa, producto=prod, almacen=alm))
    _mk(out, by_name, lambda: GM('inventario.MovimientoInventario').objects.create(empresa=empresa, producto=prod, almacen=alm, fecha=timezone.now(), tipo_movimiento='entrada', tipo_documento='ajuste'))
    _mk(out, by_name, lambda: GM('produccion.RecetaProducto').objects.create(empresa=empresa, producto_terminado=prod, nombre='Receta B'))
    if GM('produccion.RecetaProducto') in out:
        _mk(out, by_name, lambda: GM('produccion.OrdenProduccion').objects.create(
            empresa=empresa, numero='OP-B1', receta=out[GM('produccion.RecetaProducto')],
            cantidad_planificada=Decimal('1'), fecha_programada=date.today(),
            almacen_insumos=alm, almacen_destino=alm))
    return out, by_name


def _lookups(pat_obj):
    try:
        return [n for n in pat_obj.regex.groupindex.keys() if n != 'format']
    except Exception:
        return []


def _detail_routes(resolver, prefix=''):
    for p in resolver.url_patterns:
        pat = prefix + str(getattr(p, 'pattern', ''))
        if hasattr(p, 'url_patterns'):
            yield from _detail_routes(p, pat)
            continue
        cls = getattr(getattr(p, 'callback', None), 'cls', None)
        if cls is None or issubclass(cls, APIRootView):
            continue
        if '(?P<format>' in pat:
            continue
        actions = getattr(p.callback, 'actions', {})
        lk = _lookups(p.pattern)
        if lk and ({'get', 'put', 'delete', 'patch'} & set(actions)):
            yield pat, cls, lk


def _model_of(cls, user):
    qs = getattr(cls, 'queryset', None)
    if qs is not None:
        return qs.model
    ser = getattr(cls, 'serializer_class', None)
    model = getattr(getattr(ser, 'Meta', None), 'model', None) if ser is not None else None
    if model is not None:
        return model
    for action in ('retrieve', 'list'):
        v = cls()
        req = _factory.get('/'); req.user = user
        v.request = req; v.kwargs = {}; v.format_kwarg = None; v.action = action
        for getter in ('get_queryset', 'get_serializer_class'):
            try:
                res = getattr(v, getter)()
                m = res.model if getter == 'get_queryset' else getattr(getattr(res, 'Meta', None), 'model', None)
                if m is not None:
                    return m
            except Exception:
                continue
    return None


@override_settings(ROOT_URLCONF='config.urls')
class RouterWalkIsolationTests(TestCase):
    def setUp(self):
        from django.db import connection
        if connection.vendor != 'postgresql':
            self.skipTest('El router walk usa savepoints; correr con DJANGO_SETTINGS_MODULE=config.settings_test_pg')
        self.client = APIClient()
        self.A = Empresa.objects.create(nombre='Empresa A', ruc='20000000001')
        self.B = Empresa.objects.create(nombre='Empresa B', ruc='20000000002')
        self.user_a = self._user('a@a.pe', self.A)
        self.user_b = self._user('b@b.pe', self.B)
        self.b_by_model, self.b_by_name = _seed_b(self.B, self.user_b)
        self._seed_errores = self.b_by_model.pop('_errores', [])

    def _user(self, email, empresa):
        u = User(email=email, username=email); u.set_password('x'); u.empresa = empresa; u.save()
        return u

    def _build_url(self, regex, route_inst):
        """Sustituye cada lookup por el pk correcto (anidadas incluidas)."""
        path = regex.replace('^', '').replace('$', '')

        def repl(m):
            name = m.group(1)
            if name == 'pk':
                return str(route_inst.pk)
            base = name[:-3] if name.endswith('_pk') else name  # venta_pk -> venta
            inst = self.b_by_name.get(base)
            return str(inst.pk) if inst is not None else '__X__'
        path = GROUP_RE.sub(repl, path)
        if '__X__' in path:
            return None
        path = path.replace('\\.', '.').replace('\\', '')
        if not path.startswith('/'):
            path = '/' + path
        if not path.endswith('/'):
            path += '/'
        return path

    def test_router_walk_aislamiento(self):
        self.client.force_authenticate(self.user_a)
        total = tested = 0
        excluidas, fallos, probadas = [], [], []

        for regex, cls, lk in _detail_routes(get_resolver('config.urls')):
            total += 1
            model = _model_of(cls, self.user_a)
            inst = self.b_by_model.get(model) if model else None
            if inst is None:
                motivo = 'queryset=None e irresoluble' if model is None else f'sin seed de B para {model.__name__}'
                excluidas.append((regex, motivo))
                continue
            url = self._build_url(regex, inst)
            if url is None:
                excluidas.append((regex, 'lookup anidado sin seed'))
                continue
            tested += 1
            probadas.append(url)
            # Savepoint por ruta: el DELETE nunca persiste (se revierte al final) y una
            # excepción del view no envenena la transacción del test.
            # REGLA: cualquier 5xx (respuesta o excepción propagada) = FALLO, no se tolera.
            sid = transaction.savepoint()
            try:
                r = self.client.get(url)
                if r.status_code >= 500:
                    fallos.append(f'500 GET {url} ({cls.__name__}) = {r.status_code}')
                elif r.status_code == 200:
                    fallos.append(f'FUGA GET {url} ({cls.__name__}) = 200')
                rd = self.client.delete(url)
                if rd.status_code >= 500:
                    fallos.append(f'500 DELETE {url} ({cls.__name__}) = {rd.status_code}')
                if not type(inst).objects.filter(pk=inst.pk).exists():
                    fallos.append(f'FUGA DELETE {url} borró registro de B')
            except Exception as e:  # noqa: BLE001 — excepción propagada del view = 500 = FALLO
                fallos.append(f'500 EXC {url} ({cls.__name__}): {repr(e).splitlines()[0][:120]}')
            finally:
                try:
                    transaction.savepoint_rollback(sid)
                except Exception:
                    pass

        print('\n=== COBERTURA SUITE DINÁMICA (router walk) ===')
        print(f'Rutas de detalle: {total} | probadas: {tested} | excluidas: {len(excluidas)}')
        for u in sorted(probadas):
            print(f'  probada: {u}')
        print('  --- excluidas (motivo) ---')
        for regex, motivo in sorted(excluidas, key=lambda x: x[1]):
            print(f'  excluida: {regex}  →  {motivo}')
        if self._seed_errores:
            print('  --- seeds fallidos (motivo) ---')
            for e in self._seed_errores:
                print(f'  seed-fail: {e}')
        print('=== FIN COBERTURA ===\n')

        self.assertEqual(fallos, [], 'fugas:\n' + '\n'.join(fallos))
        self.assertGreaterEqual(tested, 45, f'cobertura insuficiente: {tested}/{total}')
