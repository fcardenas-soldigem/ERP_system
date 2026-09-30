"""URLconf mínima para tests.

Evita importar apps.ml_models.urls (que carga el stack de ML: joblib/sklearn),
no instalado en el entorno de desarrollo. Los tests de servicios/modelos no
necesitan las rutas HTTP.
"""
urlpatterns = []
