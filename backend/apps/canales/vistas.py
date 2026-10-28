"""
Vistas del canal (A2/A3) + PDF firmado para compartir por chat.

El webhook devuelve 200 DE INMEDIATO y procesa en un hilo aparte: Telegram
reintenta si tardamos, y el LLM puede tomar segundos. gunicorn corre con
gthread (workers con hilos), así que el hilo sobrevive a la respuesta.
"""
import json
import logging
import threading

from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import IntegrityError, close_old_connections, transaction
from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import HasEmpresaPermission

from .models import UpdateProcesado, VinculacionTelegram
from .telegram import TelegramCanal

logger = logging.getLogger(__name__)

FIRMA_PDF_MAX_EDAD = 72 * 3600  # 72 h


def _procesar_en_hilo(payload):
    # En tests: ejecución en línea (determinista); en prod: hilo daemon.
    if getattr(settings, 'CANALES_WEBHOOK_SINCRONO', False):
        procesar_update(payload)
        return

    def _correr():
        try:
            procesar_update(payload)
        finally:
            # solo en el hilo: la conexión del request no es nuestra
            close_old_connections()

    threading.Thread(target=_correr, daemon=True).start()


def procesar_update(payload):
    try:
        from .nucleo.orquestador import procesar
        canal = TelegramCanal()
        mensaje = canal.recibir(payload)
        if mensaje:
            procesar(canal, mensaje)
    except Exception:
        logger.exception('procesamiento de update falló')


class TelegramWebhookView(APIView):
    """POST /api/canales/telegram/ — entrada única del bot."""

    authentication_classes = []  # autentica la CABECERA secreta, no un usuario
    permission_classes = [AllowAny]

    def post(self, request):
        # A2 — cabecera secreta registrada junto al webhook; sin ella, 403.
        secreto = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        if not settings.TG_WEBHOOK_SECRET or secreto != settings.TG_WEBHOOK_SECRET:
            return Response(status=status.HTTP_403_FORBIDDEN)

        payload = request.data if isinstance(request.data, dict) else {}
        update_id = payload.get('update_id')
        if update_id is None:
            return Response({'ok': True})  # no es un update: lo ignoramos

        # A2 — idempotencia: Telegram reintenta; cada update se procesa una vez.
        # atomic propio: el IntegrityError esperado no debe romper una
        # transacción exterior (ATOMIC_REQUESTS o la de los tests).
        try:
            with transaction.atomic():
                UpdateProcesado.objects.create(canal='telegram', update_id=update_id)
        except IntegrityError:
            return Response({'ok': True, 'duplicado': True})

        _procesar_en_hilo(payload)
        return Response({'ok': True})  # 200 inmediato


class VincularTelegramView(APIView):
    """POST: genera código de 8 caracteres (10 min) y el link t.me (A3).
    GET: estado actual. DELETE: desvincular."""

    permission_classes = [IsAuthenticated, HasEmpresaPermission]

    def get(self, request):
        vinc = VinculacionTelegram.objects.filter(usuario=request.user).first()
        return Response({
            'vinculado': bool(vinc and vinc.vinculado),
            'bot': settings.TG_BOT_USERNAME,
        })

    def post(self, request):
        from django.utils import timezone
        vinc, _ = VinculacionTelegram.objects.get_or_create(
            usuario=request.user,
            defaults={'codigo_expira': timezone.now()},
        )
        if vinc.vinculado:
            return Response({'vinculado': True, 'bot': settings.TG_BOT_USERNAME})
        vinc.regenerar_codigo()
        return Response({
            'vinculado': False,
            'codigo': vinc.codigo,
            'expira_en_minutos': 10,
            'link': f'https://t.me/{settings.TG_BOT_USERNAME}?start={vinc.codigo}',
        })

    def delete(self, request):
        VinculacionTelegram.objects.filter(usuario=request.user).delete()
        return Response({'vinculado': False})


class PDFCotizacionFirmadoView(APIView):
    """GET /api/canales/pdf-cotizacion/?t=<firma> — PDF sin sesión, firmado y
    con vencimiento (72 h): es el link que el bot deja en el chat (B7)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        firma = request.query_params.get('t', '')
        try:
            cot_id = TimestampSigner(salt='canales.pdf').unsign(firma, max_age=FIRMA_PDF_MAX_EDAD)
        except SignatureExpired:
            return Response({'detail': 'El enlace venció. Pide uno nuevo al asistente.'}, status=410)
        except BadSignature:
            return Response(status=status.HTTP_403_FORBIDDEN)

        from apps.cotizaciones.models import Cotizacion
        from apps.cotizaciones.utils.pdf_generator import CotizacionPDFGenerator
        try:
            cot = Cotizacion.objects.get(pk=cot_id)
        except Cotizacion.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        pdf = CotizacionPDFGenerator(cot).generar_pdf()
        resp = HttpResponse(pdf.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="{cot.numero}.pdf"'
        return resp
