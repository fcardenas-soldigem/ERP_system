from django.urls import path
from . import views

urlpatterns = [
    path('upload/',              views.UploadView.as_view(),    name='importador-upload'),
    path('preview/<int:pk>/',    views.PreviewView.as_view(),   name='importador-preview'),
    path('confirmar/<int:pk>/',  views.ConfirmarView.as_view(), name='importador-confirmar'),
    path('estado/<int:pk>/',     views.EstadoView.as_view(),    name='importador-estado'),
    path('historial/',           views.HistorialView.as_view(), name='importador-historial'),
]
