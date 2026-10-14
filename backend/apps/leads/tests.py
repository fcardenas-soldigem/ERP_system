"""
Captura pública de leads: endpoint sin auth, throttle, honeypot, validación.
"""
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.leads.models import Lead

# Cache local por test → el throttle cuenta aislado y no arrastra entre casos.
LOCMEM = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}


@override_settings(CACHES=LOCMEM)
class LeadCaptureTests(TestCase):
    def setUp(self):
        cache.clear()  # el throttle vive en cache; aislar cada test
        self.client = APIClient()
        self.url = reverse('lead-create')

    def _payload(self, **over):
        data = {
            'nombre': 'Juan Pérez', 'empresa': 'Distribuidora ABC',
            'email': 'juan@abc.pe', 'telefono': '987654321',
            'rubro': 'Distribución', 'tamano': '6-20',
            'usa_inventario': True, 'mensaje': 'Quiero probar',
            'utm_source': 'facebook', 'utm_campaign': 'early-access',
        }
        data.update(over)
        return data

    def test_crea_lead_publico_sin_auth(self):
        r = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Lead.objects.count(), 1)
        lead = Lead.objects.first()
        self.assertEqual(lead.email, 'juan@abc.pe')
        self.assertEqual(lead.utm_source, 'facebook')
        self.assertTrue(lead.usa_inventario)

    def test_solo_campos_obligatorios(self):
        r = self.client.post(self.url, {'nombre': 'Ana', 'email': 'ana@x.pe',
                                        'empresa': 'X SAC'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Lead.objects.count(), 1)

    def test_email_invalido_400(self):
        r = self.client.post(self.url, self._payload(email='no-es-email'), format='json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Lead.objects.count(), 0)

    def test_nombre_vacio_400(self):
        r = self.client.post(self.url, self._payload(nombre=''), format='json')
        self.assertEqual(r.status_code, 400)

    def test_honeypot_descarta_sin_guardar(self):
        # Bot: rellena el campo señuelo 'website'. Respondemos 201 pero NO guardamos.
        r = self.client.post(self.url, self._payload(website='http://spam.ru'), format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Lead.objects.count(), 0)

    def test_throttle_5_por_hora(self):
        for i in range(5):
            r = self.client.post(self.url, self._payload(email=f'u{i}@x.pe'), format='json')
            self.assertEqual(r.status_code, 201, f'envío {i} debería pasar')
        # El 6º excede el límite
        r = self.client.post(self.url, self._payload(email='u6@x.pe'), format='json')
        self.assertEqual(r.status_code, 429)
        self.assertEqual(Lead.objects.count(), 5)
