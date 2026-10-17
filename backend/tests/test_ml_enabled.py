"""ML_ENABLED (default False): las rutas /api/ml/ no se montan → 404. Sin borrar código."""
from unittest import mock

from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .test_aislamiento_tenants import TenantSetup


class MLEnabledFlagTests(TestCase):
    def test_default_apagado(self):
        self.assertFalse(settings.ML_ENABLED)

    def test_rutas_ml_vacias_si_apagado(self):
        from config.urls import rutas_ml
        self.assertEqual(rutas_ml(False), [])

    def test_rutas_ml_montadas_si_encendido(self):
        from config import urls as cfg
        with mock.patch.object(cfg, 'include', return_value=([], None, None)) as inc:
            rutas = cfg.rutas_ml(True)
        self.assertEqual(len(rutas), 1)
        inc.assert_called_once_with('apps.ml_models.urls')
        self.assertEqual(str(rutas[0].pattern), 'api/ml/')


@override_settings(ROOT_URLCONF='config.urls')
class MLRutas404Tests(TenantSetup):
    def test_api_ml_es_404_con_flag_apagada(self):
        self.client.force_authenticate(self.user_a)
        for url in ('/api/ml/models/', '/api/ml/models/train/all/', '/api/ml/models/predict/rfm/'):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 404, url)
            r = self.client.post(url, {}, format='json')
            self.assertEqual(r.status_code, 404, url)
