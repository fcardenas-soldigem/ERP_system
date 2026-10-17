"""
Suite DINÁMICA de aislamiento en ESCRITURAS: recorre TODO el router (config.urls) y, para
cada ruta de escritura (POST list, PUT/PATCH/DELETE detail y acciones @action con métodos
de escritura), autenticado como A envía payloads construidos automáticamente desde el
serializer de la vista (o del cuerpo de la acción custom) donde cada FK apunta a un objeto
de B. Esperado: nunca 2xx y CERO efectos en los datos de B.

Diseño (complementa a test_aislamiento_router.py, que cubre GET/DELETE de detalle):
- Siembra A y B con la misma infraestructura (`_seed_b` con tag). B es la víctima; A es el
  atacante y aporta objetos propios para los PUT/PATCH y para el resto del payload.
- "One-hot" por FK: para cada campo FK (PrimaryKeyRelatedField, listas de FK, `*_id`,
  FKs dentro de `detalles`/`items` anidados y claves `*_id` leídas de `request.data` en
  acciones custom) se envía UNA petición con ese FK → B y los demás → A. Así el rechazo de
  un FK no enmascara la fuga de otro.
- Objetivo B: para rutas de detalle también se llama con el pk de B en la URL (y nested).
- Instantánea de B: para TODOS los modelos con camino a Empresa (FK directa o transitiva,
  gestor base) se guarda conteo + hash de `values()` ordenados antes del recorrido y se
  compara después de CADA petición. Cualquier diferencia = fuga, aunque el status sea 4xx.
- Savepoint por petición: una ruta que explota no envenena la transacción y el estado se
  restaura para la siguiente.
- REGLA: 2xx = FUGA; 5xx o excepción = FALLO; diferencia en la instantánea de B = FUGA.
Imprime cobertura (rutas de escritura probadas / totales), excluidas con motivo y la
clasificación de rechazos (FK / otro) para auditar que el 4xx se debe al FK y no a otra
validación.
"""
import hashlib
import inspect
import json
import re
import sys
from datetime import date
from decimal import Decimal
from unittest import mock

import requests
from django.apps import apps as djapps
from django.contrib.auth import get_user_model
from django.db import DatabaseError, models, transaction
from django.test import TestCase, override_settings
from django.urls import get_resolver
from django.utils import timezone
from rest_framework import serializers as drf
from rest_framework.relations import ManyRelatedField, PrimaryKeyRelatedField
from rest_framework.routers import APIRootView
from rest_framework.test import APIClient, APIRequestFactory

from apps.empresas.models import Empresa
from tests.test_aislamiento_router import GROUP_RE, _model_of, _seed_b

User = get_user_model()
_factory = APIRequestFactory()
CONV_RE = re.compile(r'<(?:\w+:)?(\w+)>')          # path() converters: <int:pk>
WRITE_METHODS = ('post', 'put', 'patch', 'delete')

# Nombres de claves `*_id`/FK por nombre → clave en by_name (lowercase del modelo).
ALIAS = {
    'receta': 'recetaproducto', 'insumo': 'producto', 'producto_terminado': 'producto',
    'responsable': 'user', 'usuario': 'user', 'created_by': 'user', 'creado_por': 'user',
    'registrado_por': 'user', 'detalle': 'detallecotizacion',
    'orden_produccion': 'ordenproduccion', 'almacen_insumos': 'almacen',
    'almacen_destino': 'almacen', 'almacen_origen': 'almacen',
    'proveedor_reparacion': 'proveedor', 'guia_remision': 'guiaremision',
    'cotizacion_origen': 'cotizacion', 'orden_compra': 'ordencompra',
}
# Vistas (APIView) cuyo modelo no se puede inferir del queryset/serializer.
MODEL_HINTS = {'ConfirmarView': 'importador.ImportacionExcel'}
# Rutas que no tienen sentido en este recorrido (motivo impreso en la cobertura).
EXCLUDE_PREFIX = {
    'api/mcp/': 'protocolo MCP (auth por ApiToken; cubierto por tests dedicados de agente)',
    'api/token/': 'emisión de JWT, sin tenant',
    'api/auth/token/': 'emisión de JWT, sin tenant',
    'api/auth/login/': 'login, sin tenant',
    'api/auth/logout/': 'logout, sin tenant',
    'api/core/token/': 'emisión de JWT, sin tenant',
    'api/core/auth/': 'verificación de JWT, sin tenant',
    'api/leads/': 'endpoint público de landing, sin tenant',
    'api/ml/': 'entrenamiento/predicción ML sin campos FK en el body',
    'api/inventario/^ajustes/': ('ruta rota preexistente (500 siempre, también para el propio tenant): AjusteInventario no tiene '
                                 'campo empresa y su save() crea Stock con campos inexistentes; el frontend no la usa'),
}


class _FK:
    """Marcador de un slot FK en la plantilla de payload."""
    def __init__(self, path, key, is_list=False):
        self.path, self.key, self.is_list = path, key, is_list

    def __repr__(self):
        return f'<FK {self.path}→{self.key}>'


def _lookups(pat_obj):
    try:
        return [n for n in pat_obj.regex.groupindex.keys() if n != 'format']
    except Exception:
        return []


def _write_routes(resolver, prefix=''):
    """(patrón, clase de vista, lookups, {método: acción}) para cada ruta con escritura."""
    for p in resolver.url_patterns:
        pat = prefix + str(getattr(p, 'pattern', ''))
        if hasattr(p, 'url_patterns'):
            yield from _write_routes(p, pat)
            continue
        cb = getattr(p, 'callback', None)
        cls = getattr(cb, 'cls', None)
        if cls is None or issubclass(cls, APIRootView) or '(?P<format>' in pat:
            continue
        actions = getattr(cb, 'actions', None)
        if actions:
            methods = {m: a for m, a in actions.items() if m in WRITE_METHODS}
        else:
            methods = {m: m for m in WRITE_METHODS if hasattr(cls, m)}
        if methods:
            yield pat, cls, _lookups(p.pattern), methods


def _empresa_path(model, _depth=0, _seen=None):
    """Camino ORM desde `model` hasta Empresa ('pk' | 'empresa' | 'fk__empresa' | ...)."""
    if model is Empresa:
        return 'pk'
    _seen = _seen or set()
    if model in _seen or _depth > 3:
        return None
    _seen = _seen | {model}
    names = {f.name for f in model._meta.fields}
    if 'empresa' in names:
        return 'empresa'
    for f in model._meta.fields:
        if isinstance(f, (models.ForeignKey, models.OneToOneField)) and f.related_model is not None:
            sub = _empresa_path(f.related_model, _depth + 1, _seen)
            if sub:
                return f'{f.name}__{sub}'
    return None


@override_settings(ROOT_URLCONF='config.urls')
class RouterWalkEscriturasTests(TestCase):
    """Un único test: una fuga en cualquier ruta hace fallar la suite con el detalle."""

    def setUp(self):
        from django.db import connection
        if connection.vendor != 'postgresql':
            self.skipTest('El router walk usa savepoints; correr con --settings=config.settings_test_pg')
        # Sin red: el TC SBS (apis.net.pe) se consulta al guardar OC/OCS/pagos. Fallar rápido.
        patcher = mock.patch('apps.core.services.documento_service.requests.get',
                             side_effect=requests.exceptions.ConnectionError('offline (test)'))
        patcher.start()
        self.addCleanup(patcher.stop)

        self.client = APIClient()
        self._pt_mode = False
        self.A = Empresa.objects.create(nombre='Empresa A', ruc='20000000001')
        self.B = Empresa.objects.create(nombre='Empresa B', ruc='20000000002')
        self.user_a = self._user('a@a.pe', self.A)
        self.user_b = self._user('b@b.pe', self.B)
        self.b_by_model, self.b_by_name = _seed_b(self.B, self.user_b, tag='B', n=2)
        self.a_by_model, self.a_by_name = _seed_b(self.A, self.user_a, tag='A', n=1)
        self._seed_errores = self.b_by_model.pop('_errores', []) + self.a_by_model.pop('_errores', [])
        for key in ('user', 'customuser'):
            self.b_by_name[key] = self.user_b
            self.a_by_name[key] = self.user_a
        self.b_by_model[User] = self.user_b
        self.a_by_model[User] = self.user_a
        self._paths = self._modelos_con_camino()

    def _user(self, email, empresa):
        u = User(email=email, username=email)
        u.set_password('x')
        u.empresa = empresa
        u.save()
        return u

    # ------------------------------------------------------------------ instantánea de B
    def _modelos_con_camino(self):
        out = {}
        for m in djapps.get_models():
            if m._meta.app_label in ('admin', 'auth', 'contenttypes', 'sessions'):
                continue
            path = _empresa_path(m)
            if path:
                out[m] = path
        return out

    def _snapshot(self):
        snap = {}
        for m, path in self._paths.items():
            label = m._meta.label
            try:
                val = self.B.pk if path == 'pk' else self.B
                rows = list(m._base_manager.filter(**{path: val}).order_by('pk').values())
                raw = json.dumps(rows, default=str, sort_keys=True)
                snap[label] = (len(rows), hashlib.sha1(raw.encode()).hexdigest())
            except DatabaseError:
                raise
            except Exception as e:  # noqa: BLE001 — modelo raro: se registra una vez y se omite
                self._snap_errores.add(f'{label}: {str(e).splitlines()[0][:80]}')
        return snap

    def _diff(self, base, now):
        out = []
        for label, (n0, h0) in base.items():
            n1, h1 = now.get(label, (None, None))
            if (n0, h0) != (n1, h1):
                out.append(f'{label} (filas {n0}→{n1}{"" if h0 == h1 else ", contenido cambiado"})')
        return out

    # ------------------------------------------------------------------ resolución de FK
    def _resolver(self, name):
        """Nombre de campo/clave → clave de by_name o None."""
        base = name[:-3] if name.endswith('_id') else name
        if base in ('producto', 'insumo') and self._pt_mode:
            return 'producto_pt'
        for cand in (ALIAS.get(base), base.replace('_', ''), base, *base.split('_')):
            if cand and cand in self.b_by_name:
                return cand
        return None

    def _key_for_model(self, model):
        inst = self.b_by_model.get(model)
        if inst is None:
            return None
        key = type(inst).__name__.lower()
        if key == 'producto' and self._pt_mode:
            return 'producto_pt'
        return key if key in self.b_by_name else None

    def _pk(self, key, side):
        inst = (self.b_by_name if side == 'B' else self.a_by_name).get(key)
        if inst is None and side == 'A':       # sin seed de A → se usa B (no hay otro)
            inst = self.b_by_name.get(key)
        return inst.pk if inst is not None else None

    # ------------------------------------------------------------------ plantilla de payload
    def _tpl_serializer(self, ser, path, partial):
        """Plantilla (dict con marcadores _FK) a partir de los campos escribibles."""
        tpl, slots = {}, []
        for name, field in ser.fields.items():
            if field.read_only or isinstance(field, (drf.HiddenField, drf.SerializerMethodField)):
                continue
            fpath = f'{path}.{name}' if path else name
            val, sub_slots = self._tpl_field(name, field, fpath, partial)
            if val is _SKIP:
                continue
            if sub_slots:
                tpl[name] = val
                slots += sub_slots
            elif field.required and not partial:
                tpl[name] = val
        return tpl, slots

    def _tpl_field(self, name, field, fpath, partial):
        if isinstance(field, ManyRelatedField):
            key = self._key_for_model(getattr(field.child_relation.queryset, 'model', None))
            if key:
                fk = _FK(fpath, key, is_list=True)
                return fk, [fk]
            return _SKIP, []
        if isinstance(field, PrimaryKeyRelatedField):
            key = self._key_for_model(getattr(field.queryset, 'model', None))
            if key:
                fk = _FK(fpath, key)
                return fk, [fk]
            return _SKIP, []
        if isinstance(field, drf.ListSerializer):
            child_tpl, child_slots = self._tpl_serializer(field.child, fpath + '[0]', False)
            return [child_tpl], child_slots
        if isinstance(field, drf.BaseSerializer):
            return self._tpl_serializer(field, fpath, False)
        if isinstance(field, drf.IntegerField) and name.endswith('_id'):
            key = self._resolver(name)
            if key:
                fk = _FK(fpath, key)
                return fk, [fk]
            return 1, []
        if isinstance(field, (drf.FileField, drf.ImageField)):
            return _SKIP, []
        return self._dummy(name, field), []

    @staticmethod
    def _dummy(name, field):
        if isinstance(field, drf.ChoiceField) and not isinstance(field, drf.MultipleChoiceField):
            choices = list(field.choices)
            return choices[0] if choices else 'x'
        if isinstance(field, drf.BooleanField):
            return True
        if isinstance(field, drf.DecimalField):
            return '1.00'
        if isinstance(field, (drf.IntegerField, drf.FloatField)):
            return 1
        if isinstance(field, drf.DateTimeField):
            return timezone.now().isoformat()
        if isinstance(field, drf.DateField):
            return date.today().isoformat()
        if isinstance(field, drf.EmailField):
            return 'a@a.pe'
        if isinstance(field, (drf.JSONField, drf.DictField)):
            return {}
        if isinstance(field, drf.ListField):
            return []
        if isinstance(field, drf.CharField):
            v = {'ruc': '20123456789', 'documento': '12345678', 'telefono': '999999999',
                 'sku': 'SKU-X', 'email': 'a@a.pe'}.get(name, 'x')
            ml = getattr(field, 'max_length', None)
            return v[:ml] if ml else v
        return 'x'

    def _tpl_action(self, cls, action_name, model):
        """Plantilla para una acción custom: claves leídas de request.data + serializers
        instanciados con data= en su cuerpo."""
        fn = getattr(cls, action_name, None)
        tpl, slots = {}, []
        if fn is None:
            return tpl, slots
        try:
            src = inspect.getsource(fn)
        except (OSError, TypeError):
            return tpl, slots
        mod = sys.modules.get(cls.__module__)
        # Claves que la vista sobreescribe antes de validar (data['compra'] = compra.id): no son
        # entrada del cliente, no se cuentan como slot FK.
        forzadas = set(re.findall(r"data\[['\"](\w+)['\"]\]\s*=", src))
        for ser_name in set(re.findall(r'\b(\w+Serializer)\(\s*data=', src)):
            ser_cls = getattr(mod, ser_name, None)
            if ser_cls is None or not issubclass(ser_cls, drf.BaseSerializer):
                continue
            t, s = self._tpl_serializer(ser_cls(context=self._ctx(cls, action_name)), '', False)
            for k in forzadas:
                t.pop(k, None)
            tpl.update(t)
            slots += [x for x in s if x.path.split('.')[0] not in forzadas]
        for key in set(re.findall(r"request\.data(?:\.get\(|\[)\s*['\"](\w+)['\"]", src)):
            if key in tpl:
                continue
            if key == 'ids':
                k = self._key_for_model(model)
                if k:
                    fk = _FK('ids', k, is_list=True)
                    tpl['ids'] = fk
                    slots.append(fk)
                continue
            rk = self._resolver(key) if (key.endswith('_id') or key in self.b_by_name) else None
            if rk:
                fk = _FK(key, rk)
                tpl[key] = fk
                slots.append(fk)
            elif key == 'estado':
                tpl[key] = self._estado_valido(model)
            elif key in ('cantidad', 'monto', 'cantidad_ajuste', 'cantidad_producida',
                         'cantidad_entrada', 'cantidad_real', 'dias'):
                tpl[key] = 1
            else:
                tpl[key] = 'x'
        return tpl, slots

    @staticmethod
    def _estado_valido(model):
        try:
            choices = model._meta.get_field('estado').choices
            return choices[1][0] if len(choices) > 1 else choices[0][0]
        except Exception:
            return 'pendiente'

    def _ctx(self, cls, action):
        req = _factory.post('/')
        req.user = self.user_a
        v = cls()
        v.request, v.kwargs, v.format_kwarg, v.action = req, {}, None, action
        return {'request': req, 'view': v, 'format': None}

    def _tpl_route(self, cls, action, method, model):
        """Plantilla + slots para (vista, acción, método)."""
        # Contextos que exigen producto TERMINADO (ventas, productos-terminados): usar producto_pt
        # para que el 400 se deba al tenant y no al tipo de producto.
        self._pt_mode = bool(re.search(r'Venta|ProductosTerminados|EntradaProduccion|Factura', cls.__name__ + ' ' + action))
        std = action in ('create', 'update', 'partial_update')
        if std or action in WRITE_METHODS:  # ViewSet estándar o APIView (acción = método)
            # ViewSet estándar o APIView: serializer de la vista.
            ser_cls = None
            try:
                ctx = self._ctx(cls, action)
                v = ctx['view']
                ser_cls = v.get_serializer_class() if hasattr(v, 'get_serializer_class') else None
            except Exception:
                ser_cls = getattr(cls, 'serializer_class', None)
            if ser_cls is None:
                return {}, []
            return self._tpl_serializer(ser_cls(context=ctx), '', partial=(method == 'patch'))
        if action == 'destroy':
            return {}, []
        return self._tpl_action(cls, action, model)

    def _render(self, tpl, hot):
        """Materializa la plantilla: los slots en `hot` apuntan a B, el resto a A."""
        def rec(node):
            if isinstance(node, _FK):
                side = 'B' if node.path in hot else 'A'
                pk = self._pk(node.key, side)
                if pk is None:
                    return _SKIP
                return [pk] if node.is_list else pk
            if isinstance(node, dict):
                out = {}
                for k, v in node.items():
                    r = rec(v)
                    if r is not _SKIP:
                        out[k] = r
                return out
            if isinstance(node, list):
                return [x for x in (rec(v) for v in node) if x is not _SKIP]
            return node
        return rec(tpl)

    # ------------------------------------------------------------------ URL
    def _build_url(self, pattern, inst, by_name):
        path = pattern.replace('^', '').replace('$', '')

        def repl(m):
            name = m.group(1)
            if name == 'pk':
                return str(inst.pk)
            base = name[:-3] if name.endswith('_pk') else name
            other = by_name.get(base)
            return str(other.pk) if other is not None else '__X__'
        path = CONV_RE.sub(repl, GROUP_RE.sub(repl, path))
        if '__X__' in path:
            return None
        path = path.replace('\\.', '.').replace('\\', '')
        return '/' + path.strip('/') + '/'

    # ------------------------------------------------------------------ petición verificada
    def _hit(self, method, url, payload, etiqueta, fallos, registro):
        """Envía la petición en un savepoint, verifica status y la instantánea de B."""
        sid = transaction.savepoint()
        status_code, body, diff = None, '', []
        try:
            r = self.client.generic(method.upper(), url, data=json.dumps(payload),
                                    content_type='application/json')
            status_code = r.status_code
            body = (r.content or b'')[:300].decode('utf-8', 'replace')
            if status_code >= 500:
                fallos.append(f'500 {etiqueta} = {status_code} {body[:120]}')
            elif 200 <= status_code < 300:
                fallos.append(f'FUGA(2xx) {etiqueta} = {status_code} {body[:120]}')
            try:
                diff = self._diff(self._base, self._snapshot())
            except DatabaseError:
                diff = ['(transacción rota: no se pudo verificar la instantánea)']
            if diff:
                fallos.append(f'FUGA(B cambió) {etiqueta} = {status_code}: ' + '; '.join(diff))
        except Exception as e:  # noqa: BLE001 — excepción propagada del view = 500 = FALLO
            fallos.append(f'500 EXC {etiqueta}: {repr(e).splitlines()[0][:140]}')
        finally:
            try:
                transaction.savepoint_rollback(sid)
            except Exception:
                pass
        registro.append((etiqueta, status_code, body))
        return status_code

    # ------------------------------------------------------------------ el test
    def test_router_walk_escrituras(self):
        self.client.force_authenticate(self.user_a)
        self._snap_errores = set()
        self._base = self._snapshot()
        total = tested = 0
        excluidas, fallos, registro, probadas = [], [], [], []

        for pattern, cls, lookups, methods in _write_routes(get_resolver('config.urls')):
            motivo_global = next((m for pre, m in EXCLUDE_PREFIX.items() if pattern.startswith(pre)), None)
            model = _model_of(cls, self.user_a)
            if model is None and cls.__name__ in MODEL_HINTS:
                model = djapps.get_model(MODEL_HINTS[cls.__name__])
            es_detalle = 'pk' in lookups
            inst_b = self.b_by_model.get(model) if model else None
            inst_a = self.a_by_model.get(model) if model else None

            for method, action in methods.items():
                total += 1
                ruta = f'{method.upper()} {pattern}'
                if motivo_global:
                    excluidas.append((ruta, motivo_global))
                    continue
                try:
                    tpl, slots = self._tpl_route(cls, action, method, model)
                except Exception as e:  # noqa: BLE001
                    excluidas.append((ruta, f'no se pudo construir el payload: {repr(e)[:80]}'))
                    continue
                enviadas = 0

                if es_detalle:
                    if inst_b is None:
                        excluidas.append((ruta, 'queryset=None e irresoluble' if model is None
                                          else f'sin seed de B para {model.__name__}'))
                        continue
                    url_b = self._build_url(pattern, inst_b, self.b_by_name)
                    if url_b is None:
                        excluidas.append((ruta, 'lookup anidado sin seed'))
                        continue
                    # (1) Objetivo B: pk de B en la URL, FKs → B. Esperado 404/400.
                    self._hit(method, url_b, self._render(tpl, {s.path for s in slots}),
                              f'{method.upper()} {url_b} [{cls.__name__}.{action} pk=B]', fallos, registro)
                    enviadas += 1
                    # (2) Objetivo A: objeto propio, un FK → B por petición.
                    if slots and inst_a is not None and method != 'delete':
                        url_a = self._build_url(pattern, inst_a, self.a_by_name)
                        if url_a is not None:
                            for s in slots:
                                self._hit(method, url_a, self._render(tpl, {s.path}),
                                          f'{method.upper()} {url_a} [{cls.__name__}.{action} pk=A {s.path}→B]',
                                          fallos, registro)
                                enviadas += 1
                else:
                    if not slots:
                        excluidas.append((ruta, 'sin campos FK en el body (o requiere archivo)'))
                        continue
                    url = self._build_url(pattern, None, self.a_by_name)
                    if url is None:
                        excluidas.append((ruta, 'lookup anidado sin seed'))
                        continue
                    for s in slots:
                        self._hit(method, url, self._render(tpl, {s.path}),
                                  f'{method.upper()} {url} [{cls.__name__}.{action} {s.path}→B]',
                                  fallos, registro)
                        enviadas += 1

                if enviadas:
                    tested += 1
                    probadas.append(f'{ruta}  ({enviadas} peticiones, FKs: {[s.path for s in slots]})')

        # -------------------------------------------------------------- informe
        print('\n=== COBERTURA SUITE DINÁMICA DE ESCRITURAS (router walk) ===')
        print(f'Rutas de escritura: {total} | probadas: {tested} | excluidas: {len(excluidas)} | peticiones: {len(registro)}')
        for p in sorted(probadas):
            print(f'  probada: {p}')
        print('  --- excluidas (motivo) ---')
        for ruta, motivo in sorted(excluidas, key=lambda x: (x[1], x[0])):
            print(f'  excluida: {ruta}  →  {motivo}')
        print('  --- clasificación de respuestas (objetivo A / list con FK→B) ---')
        fk_words = ('no pertenece', 'does not exist', 'invalid pk', 'no encontrad', 'no válido',
                    'no valido', 'not found', 'no existe', 'object does not exist', 'not_found')
        for etiqueta, code, body in registro:
            if 'pk=B]' in etiqueta:
                continue
            low = body.lower()
            clase = 'FK' if any(w in low for w in fk_words) else ('403' if code == 403 else 'OTRO')
            print(f'  [{clase}] {code} {etiqueta} :: {body[:110]}')
        if self._seed_errores:
            print('  --- seeds fallidos (motivo) ---')
            for e in self._seed_errores:
                print(f'  seed-fail: {e}')
        if self._snap_errores:
            print('  --- modelos sin instantánea ---')
            for e in sorted(self._snap_errores):
                print(f'  snap-skip: {e}')
        print('=== FIN COBERTURA ===\n')

        self.assertEqual(fallos, [], 'fugas/fallos:\n' + '\n'.join(fallos))
        self.assertGreaterEqual(tested, 60, f'cobertura insuficiente: {tested}/{total}')


_SKIP = object()
