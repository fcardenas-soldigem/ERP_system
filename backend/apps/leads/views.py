import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Lead
from .serializers import LeadSerializer
from .throttling import LeadAnonThrottle

logger = logging.getLogger(__name__)


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class LeadCreateView(APIView):
    """
    POST /api/leads/  — PÚBLICO (landing de acceso anticipado).
    - permission AllowAny (sin auth)
    - throttle anónimo estricto: 5/hora por IP
    - honeypot anti-spam en el serializer (campo 'website')
    Responde 201 con un mensaje de éxito; nunca expone el objeto completo.
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # endpoint público: no exigir sesión/JWT
    throttle_classes = [LeadAnonThrottle]

    def post(self, request):
        serializer = LeadSerializer(data=request.data)
        if not serializer.is_valid():
            # El honeypot devuelve 400 con 'spam detectado'; respondemos 201 falso
            # para no darle feedback al bot, pero NO guardamos.
            if 'spam' in str(serializer.errors).lower():
                logger.info('Lead honeypot activado desde IP %s', _client_ip(request))
                return Response({'message': 'Gracias, te contactaremos pronto.'},
                                status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        lead = serializer.save(ip=_client_ip(request))
        logger.info('Nuevo lead #%s: %s (%s)', lead.id, lead.nombre, lead.email)
        return Response(
            {'message': 'Gracias, te contactaremos pronto.', 'id': lead.id},
            status=status.HTTP_201_CREATED,
        )
