from django.urls import path

from . import vistas

app_name = 'canales'

urlpatterns = [
    path('telegram/', vistas.TelegramWebhookView.as_view(), name='telegram_webhook'),
    path('telegram/vincular/', vistas.VincularTelegramView.as_view(), name='telegram_vincular'),
    path('pdf-cotizacion/', vistas.PDFCotizacionFirmadoView.as_view(), name='pdf_cotizacion'),
]
