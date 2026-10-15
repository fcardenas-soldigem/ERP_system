import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Lead
from .serializers import LeadSerializer
from .throttling import LeadAnonThrottle, client_ip

logger = logging.getLogger(__name__)


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
                logger.info('Lead honeypot activado desde IP %s', client_ip(request))
                return Response({'message': 'Gracias, te contactaremos pronto.'},
                                status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        lead = serializer.save(ip=client_ip(request))
        logger.info('Nuevo lead #%s: %s (%s)', lead.id, lead.nombre, lead.email)
        return Response(
            {'message': 'Gracias, te contactaremos pronto.', 'id': lead.id},
            status=status.HTTP_201_CREATED,
        )
