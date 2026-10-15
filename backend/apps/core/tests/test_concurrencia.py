"""Creación CONCURRENTE de documentos (Postgres real, hilos).

Verifica que la numeración por-empresa aguanta concurrencia:
  - 10 creaciones simultáneas de la empresa A en COT, V, OC, OCS, OS, Guía →
    números consecutivos (1..10), sin duplicados ni excepciones (500).
  - A y B en paralelo → secuencias independientes (cada una 1..10).

Requiere TransactionTestCase (los hilos usan conexiones propias y necesitan que
los datos de setUp estén COMMITTED) y un backend con bloqueos de fila reales
(Postgres); en SQLite no hay select_for_update efectivo. Correr con:
  manage.py test apps.core.tests.test_concurrencia --settings=config.settings_test_pg
"""
import re
import threading
from datetime import date, timedelta
from unittest import mock

from django.core.management import call_command
from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone

from apps.authentication.models import CustomUser
from apps.compras.models import OrdenCompra, OrdenServicioCompra, Proveedor
from apps.cotizaciones.models import Cotizacion
from apps.empresas.models import Empresa
from apps.guias.models import GuiaRemision
from apps.servicios.models import OrdenServicio
from apps.ventas.models import Cliente, Venta

TIPOS = ('COT', 'V', 'OC', 'OCS', 'OS', 'GR')


def _seq(numero):
    """Secuencia entera del número (soporta 000001, V-000001, COT-00000001, OS-0001, GR-0001)."""
    return int(re.search(r'(\d+)$', numero).group(1))


def _correr(callables):
    """Corre cada callable en su propio hilo, todos arrancando a la vez (barrier).

    Devuelve (resultados, errores). Cada hilo cierra su conexión al terminar.
    """
    n = len(callables)
    barrera = threading.Barrier(n, timeout=30)
    resultados, errores = [], []
    lock = threading.Lock()

    def worker(fn):
        try:
            barrera.wait()
            r = fn()
            with lock:
                resultados.append(r)
        except Exception as e:  # noqa: BLE001 — cualquier excepción cuenta como fallo (500)
            with lock:
                errores.append(repr(e))
        finally:
            connection.close()

    hilos = [threading.Thread(target=worker, args=(fn,)) for fn in callables]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    return resultados, errores


class CreacionConcurrenteTests(TransactionTestCase):
    def _fixture_teardown(self):
        # El flush normal no puede truncar compras_ordencompra: la tabla managed=False
        # compras_ordencompradetalle (creada a mano en settings_test_pg) la referencia.
        # Forzamos TRUNCATE ... CASCADE. post_migrate recrea perms y la tabla unmanaged.
        for db_name in self._databases_names(include_mirrors=False):
            call_command(
                'flush', verbosity=0, interactive=False, database=db_name,
                reset_sequences=False, allow_cascade=True, inhibit_post_migrate=False,
            )

    def setUp(self):
        # La numeración no depende del tipo de cambio; evitamos la llamada de red
        # (api.apis.net.pe) que haría lento/flaky el test concurrente.
        for modelo in ('apps.ventas.models.Venta', 'apps.compras.models.OrdenCompra'):
            p = mock.patch(f'{modelo}.asegurar_tipo_cambio', lambda self: None)
            p.start()
            self.addCleanup(p.stop)
        self.ctx = {}
        for key, ruc in (('A', '20000000001'), ('B', '20000000002')):
            emp = Empresa.objects.create(nombre=key, ruc=ruc, modo_inventario='con_stock')
            user = CustomUser(email=f'u{key}@t.com', nombre='T', apellido='U', empresa=emp, is_superuser=True)
            user.set_password('x')
            user.save()
            self.ctx[key] = {
                'emp': emp,
                'user': user,
                'cliente': Cliente.objects.create(
                    empresa=emp, nombre='C', documento=f'{key}0000001'[:8], tipo_documento='ruc'),
                'prov': Proveedor.objects.create(empresa=emp, razon_social='P', ruc=f'2000000001{key}'[:11]),
            }

    def _creador(self, tipo, key):
        """Devuelve una función sin args que crea un documento `tipo` de la empresa `key`."""
        c = self.ctx[key]
        fv = timezone.now().date() + timedelta(days=30)
        fabrica = {
            'COT': lambda: Cotizacion.objects.create(
                empresa=c['emp'], cliente=c['cliente'], usuario_creador=c['user'], asunto='a', fecha_vencimiento=fv),
            'V': lambda: Venta.objects.create(
                empresa=c['emp'], cliente=c['cliente'], fecha_emision=date.today(), tipo_venta='contado'),
            'OC': lambda: OrdenCompra.objects.create(empresa=c['emp'], fecha_entrega=date.today()),
            'OCS': lambda: OrdenServicioCompra.objects.create(empresa=c['emp']),
            'OS': lambda: OrdenServicio.objects.create(
                empresa=c['emp'], cliente=c['cliente'], proveedor_reparacion=c['prov'], creado_por=c['user']),
            'GR': lambda: GuiaRemision.objects.create(
                empresa=c['emp'], fecha_traslado=date.today(), motivo='venta', nombre_destinatario='D',
                direccion_origen='O', direccion_destino='X', creado_por=c['user']),
        }[tipo]
        return lambda: fabrica().numero

    def test_10_simultaneas_consecutivas_sin_duplicados(self):
        N = 10
        for tipo in TIPOS:
            with self.subTest(tipo=tipo):
                nums, err = _correr([self._creador(tipo, 'A')] * N)
                self.assertEqual(err, [], f'{tipo}: excepciones/500: {err}')
                self.assertEqual(len(nums), N, f'{tipo}: creaciones faltantes')
                self.assertEqual(len(set(nums)), N, f'{tipo}: números duplicados: {sorted(nums)}')
                self.assertEqual(sorted(_seq(n) for n in nums), list(range(1, N + 1)),
                                 f'{tipo}: no consecutivos: {sorted(nums)}')

    def test_A_y_B_secuencias_independientes(self):
        N = 10
        for tipo in TIPOS:
            with self.subTest(tipo=tipo):
                calls = [self._creador(tipo, 'A')] * N + [self._creador(tipo, 'B')] * N
                nums, err = _correr(calls)
                self.assertEqual(err, [], f'{tipo}: excepciones/500: {err}')
                # 2N números; cada empresa debe tener su propia secuencia 1..N.
                seqs = sorted(_seq(n) for n in nums)
                self.assertEqual(seqs, sorted(list(range(1, N + 1)) * 2),
                                 f'{tipo}: secuencias no independientes: {sorted(nums)}')
