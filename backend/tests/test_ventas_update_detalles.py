"""
PATCH/PUT /api/ventas/<id>/ sin 'detalles' NO debe borrar las líneas de la venta.

Antes, VentaSerializer.update hacía pop('detalles', []) + detalles.all().delete(): cualquier
PATCH parcial (notas, cliente_id) dejaba la venta sin líneas (200 OK). Hoy ningún componente
del frontend llama a PUT/PATCH /api/ventas/<id>/ (los cambios de estado van por las acciones
cambiar_estado / cambiar-estado-operativo), así que no hubo pérdida en prod, pero el bug
estaba expuesto por API. Compra/Cotización/Guía/OC/OCS ya usaban el patrón `None`.
"""
from datetime import date
from decimal import Decimal

from django.test import override_settings

from apps.ventas.models import DetalleVenta, Venta

from .test_aislamiento_tenants import TenantSetup


@override_settings(ROOT_URLCONF='config.urls')
class VentaUpdateSinDetallesTests(TenantSetup):
    def setUp(self):
        super().setUp()
        # Solo los productos terminados pueden venderse (validación del serializer).
        self.prod_a.tipo_producto = 'FINISHED'
        self.prod_a.save(update_fields=['tipo_producto'])
        self.venta = Venta.objects.create(
            empresa=self.A, cliente=self.cli_a, fecha_emision=date.today(), moneda='PEN',
            tipo_venta='contado', estado='pendiente')
        DetalleVenta.objects.create(venta=self.venta, producto=self.prod_a, descripcion='Prod A',
                                    cantidad=Decimal('2'), precio_unitario=Decimal('100'))
        DetalleVenta.objects.create(venta=self.venta, producto=None, descripcion='Servicio libre',
                                    cantidad=Decimal('1'), precio_unitario=Decimal('50'))
        self.client.force_authenticate(self.user_a)

    def test_patch_sin_detalles_conserva_las_lineas(self):
        r = self.client.patch(f'/api/ventas/{self.venta.id}/', {'notas': 'solo cambio notas'}, format='json')
        self.assertEqual(r.status_code, 200, r.content[:300])
        self.assertEqual(self.venta.detalles.count(), 2, 'un PATCH sin detalles borraba las líneas')
        self.venta.refresh_from_db()
        self.assertEqual(self.venta.notas, 'solo cambio notas')

    def test_put_con_detalles_las_reemplaza(self):
        payload = {
            'cliente_id': self.cli_a.id, 'fecha_emision': str(date.today()), 'moneda': 'PEN',
            'tipo_venta': 'contado', 'notas': 'reemplazo',
            'detalles': [{'producto': self.prod_a.id, 'descripcion': 'Prod A', 'cantidad': '5',
                          'precio_unitario': '10.00'}],
        }
        r = self.client.put(f'/api/ventas/{self.venta.id}/', payload, format='json')
        self.assertEqual(r.status_code, 200, r.content[:300])
        self.assertEqual(self.venta.detalles.count(), 1)
        self.assertEqual(self.venta.detalles.first().cantidad, Decimal('5'))

    def test_patch_con_lista_vacia_explicita_si_borra(self):
        r = self.client.patch(f'/api/ventas/{self.venta.id}/', {'detalles': []}, format='json')
        self.assertEqual(r.status_code, 200, r.content[:300])
        self.assertEqual(self.venta.detalles.count(), 0)
