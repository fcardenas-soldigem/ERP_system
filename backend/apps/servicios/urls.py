from rest_framework.routers import DefaultRouter
from .views import OrdenServicioViewSet

router = DefaultRouter()
router.register(r'ordenes', OrdenServicioViewSet, basename='orden-servicio')

urlpatterns = router.urls
