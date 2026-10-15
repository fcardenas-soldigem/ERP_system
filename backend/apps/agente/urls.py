from rest_framework.routers import DefaultRouter

from .token_views import ApiTokenViewSet

router = DefaultRouter()
router.register('tokens', ApiTokenViewSet, basename='apitoken')

urlpatterns = router.urls
