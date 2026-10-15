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

    def test_throttle_visitantes_distintos_no_se_bloquean(self):
        # 6 visitantes con X-Forwarded-For distinto: ninguno bloquea al otro.
        for i in range(6):
            r = self.client.post(self.url, self._payload(email=f'v{i}@x.pe'),
                                  format='json', HTTP_X_FORWARDED_FOR=f'203.0.113.{i}')
            self.assertEqual(r.status_code, 201, f'visitante {i} no debería bloquearse')
        self.assertEqual(Lead.objects.count(), 6)

    def test_throttle_mismo_visitante_se_bloquea(self):
        # 6 envíos con el mismo X-Forwarded-For: el 6º se bloquea (429).
        ip = '198.51.100.7'
        for i in range(5):
            r = self.client.post(self.url, self._payload(email=f'u{i}@x.pe'),
                                  format='json', HTTP_X_FORWARDED_FOR=ip)
            self.assertEqual(r.status_code, 201, f'envío {i} debería pasar')
        r = self.client.post(self.url, self._payload(email='u6@x.pe'),
                             format='json', HTTP_X_FORWARDED_FOR=ip)
        self.assertEqual(r.status_code, 429)
        self.assertEqual(Lead.objects.count(), 5)

    def test_throttle_cuenta_al_visitante_aunque_roten_los_proxies(self):
        # Mismo visitante (primer IP de XFF) pero proxies que rotan en el resto
        # de la cadena. El throttle debe seguir contándolo como un solo visitante
        # → 6º bloqueado. (Con el comportamiento por defecto de DRF, que usa la
        # cadena completa, cada petición tendría una clave distinta y NUNCA se
        # bloquearía: esta prueba protege contra esa regresión.)
        visitante = '203.0.113.50'
        for i in range(5):
            r = self.client.post(
                self.url, self._payload(email=f'p{i}@x.pe'), format='json',
                HTTP_X_FORWARDED_FOR=f'{visitante}, 10.0.0.{i}, 169.254.1.{i}')
            self.assertEqual(r.status_code, 201, f'envío {i} debería pasar')
        r = self.client.post(
            self.url, self._payload(email='p6@x.pe'), format='json',
            HTTP_X_FORWARDED_FOR=f'{visitante}, 10.0.0.9, 169.254.1.9')
        self.assertEqual(r.status_code, 429)
        self.assertEqual(Lead.objects.count(), 5)

    def test_lead_guarda_ip_del_visitante_no_del_proxy(self):
        # El Lead debe guardar la IP del visitante (primer valor), no la del proxy.
        r = self.client.post(
            self.url, self._payload(), format='json',
            HTTP_X_FORWARDED_FOR='203.0.113.99, 10.0.0.1, 169.254.1.1')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Lead.objects.first().ip, '203.0.113.99')
