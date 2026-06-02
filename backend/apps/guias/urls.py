from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GuiaRemisionViewSet

router = DefaultRouter()
router.register(r'guias', GuiaRemisionViewSet, basename='guia')

urlpatterns = [
    path('', include(router.urls)),
]
