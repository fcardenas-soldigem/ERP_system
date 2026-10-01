"""
Numeración POR EMPRESA (multi-tenant). Dos empresas pueden tener su documento
#1 sin colisión; la secuencia es independiente por empresa; y la creación
concurrente no duplica números.
"""
from datetime import date, timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from apps.empresas.models import Empresa
from apps.authentication.models import CustomUser
from apps.ventas.models import Cliente, Venta
from apps.compras.models import Proveedor, OrdenCompra, OrdenServicioCompra
from apps.cotizaciones.models import Cotizacion


def _empresa(n):
    return Empresa.objects.create(nombre=f'E{n}', ruc=f'20{n:09d}', modo_inventario='con_stock')


def _user(emp, n):
    u = CustomUser(email=f'u{n}@t.com', nombre='T', apellido='U', empresa=emp, is_superuser=True)
    u.set_password('x'); u.save()
    return u


def _cliente(emp, n):
    return Cliente.objects.create(empresa=emp, nombre='C', documento=f'{n:08d}', tipo_documento='ruc')


class NumeracionPorEmpresaTests(TestCase):
    def test_dos_empresas_documento_1_sin_colision(self):
        A, B = _empresa(11), _empresa(12)
        uA, uB = _user(A, 1), _user(B, 2)
        cA, cB = _cliente(A, 1), _cliente(B, 2)
        fv = timezone.now().date() + timedelta(days=30)

        # Cotización #1 de cada empresa
        cotA = Cotizacion.objects.create(empresa=A, cliente=cA, usuario_creador=uA, asunto='a', fecha_vencimiento=fv)
        cotB = Cotizacion.objects.create(empresa=B, cliente=cB, usuario_creador=uB, asunto='b', fecha_vencimiento=fv)
        self.assertEqual(cotA.numero, 'COT-00000001')
        self.assertEqual(cotB.numero, 'COT-00000001')  # misma secuencia, distinta empresa

        # Venta #1 de cada empresa
        vA = Venta.objects.create(empresa=A, cliente=cA, fecha_emision=date.today(), tipo_venta='contado')
        vB = Venta.objects.create(empresa=B, cliente=cB, fecha_emision=date.today(), tipo_venta='contado')
        self.assertEqual(vA.numero, 'V-000001')
        self.assertEqual(vB.numero, 'V-000001')

        # OrdenCompra #1 de cada empresa
        ocA = OrdenCompra.objects.create(empresa=A, fecha_entrega=date.today())
        ocB = OrdenCompra.objects.create(empresa=B, fecha_entrega=date.today())
        self.assertEqual(ocA.numero, '000001')
        self.assertEqual(ocB.numero, '000001')

        # OrdenServicioCompra #1 de cada empresa
        ocsA = OrdenServicioCompra.objects.create(empresa=A)
        ocsB = OrdenServicioCompra.objects.create(empresa=B)
        self.assertEqual(ocsA.numero, '000001')
        self.assertEqual(ocsB.numero, '000001')

    def test_secuencia_independiente_por_empresa(self):
        A, B = _empresa(21), _empresa(22)
        cA, cB = _cliente(A, 1), _cliente(B, 2)
        n1 = Venta.objects.create(empresa=A, cliente=cA, fecha_emision=date.today(), tipo_venta='contado').numero
        n2 = Venta.objects.create(empresa=A, cliente=cA, fecha_emision=date.today(), tipo_venta='contado').numero
        n3 = Venta.objects.create(empresa=B, cliente=cB, fecha_emision=date.today(), tipo_venta='contado').numero
        self.assertEqual([n1, n2, n3], ['V-000001', 'V-000002', 'V-000001'])


class NumeracionRetryTests(TestCase):
    def test_retry_ante_colision(self):
        """
        Simula una colisión concurrente: _siguiente_numero devuelve en el primer
        intento un número que ya existe (IntegrityError), y el helper reintenta
        y obtiene el siguiente. Determinista, sin hilos.
        """
        emp = _empresa(31)
        cli = _cliente(emp, 1)
        Venta.objects.create(empresa=emp, cliente=cli, fecha_emision=date.today(), tipo_venta='contado')  # V-000001

        real = Venta._siguiente_numero
        llamadas = {'n': 0}

        def fake(self):
            llamadas['n'] += 1
            if llamadas['n'] == 1:
                return 'V-000001'  # colisiona con el existente
            return real(self)

        with mock.patch.object(Venta, '_siguiente_numero', fake):
            v2 = Venta.objects.create(empresa=emp, cliente=cli, fecha_emision=date.today(), tipo_venta='contado')

        self.assertGreaterEqual(llamadas['n'], 2, 'no reintentó tras la colisión')
        self.assertEqual(v2.numero, 'V-000002')  # obtuvo el siguiente, sin duplicar
