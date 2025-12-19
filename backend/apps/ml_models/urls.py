from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.ml_models.views import MLModelViewSet

router = DefaultRouter()
router.register(r'models', MLModelViewSet, basename='ml-models')

urlpatterns = [
    path('', include(router.urls)),
]
