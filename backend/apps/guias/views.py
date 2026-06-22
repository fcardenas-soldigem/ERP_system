import logging
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q
from apps.core.permissions import HasEmpresaPermission
from .models import GuiaRemision
from .serializers import GuiaRemisionSerializer, GuiaRemisionListSerializer
from .pdf_generator import GuiaRemisionPDF

logger = logging.getLogger(__name__)

ESTADOS_VALIDOS = {
    'borrador': ['emitida', 'cancelada'],
    'emitida': ['en_proceso', 'cancelada'],
    'en_proceso': ['entregada', 'cancelada'],
    'entregada': [],
    'cancelada': [],
}


class GuiaPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class GuiaRemisionViewSet(viewsets.ModelViewSet):
    queryset = GuiaRemision.objects.all()
    permission_classes = [IsAuthenticated, HasEmpresaPermission]
    pagination_class = GuiaPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return GuiaRemisionListSerializer
        return GuiaRemisionSerializer

    def _get_empresa(self):
        if not hasattr(self.request.user, 'empresa'):
            raise PermissionDenied('Usuario no tiene empresa asignada.')
        return self.request.user.empresa

    def get_queryset(self):
        empresa = self._get_empresa()
        qs = (
            GuiaRemision.objects.filter(empresa=empresa)
            .select_related('cliente', 'creado_por')
            .prefetch_related('items')
            .order_by('-created_at')
        )

        params = self.request.query_params

        tipo = params.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)

        estado = params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)

        numero = params.get('numero')
        if numero:
            qs = qs.filter(numero__icontains=numero)

        fecha_desde = params.get('fecha_desde')
        if fecha_desde:
            qs = qs.filter(fecha_emision__gte=fecha_desde)

        fecha_hasta = params.get('fecha_hasta')
        if fecha_hasta:
            qs = qs.filter(fecha_emision__lte=fecha_hasta)

        search = params.get('search')
        if search:
            qs = qs.filter(
                Q(numero__icontains=search)
                | Q(nombre_destinatario__icontains=search)
                | Q(ruc_destinatario__icontains=search)
            )

        return qs

    def perform_create(self, serializer):
        empresa = self._get_empresa()
        serializer.save(empresa=empresa, creado_por=self.request.user)

    @action(detail=True, methods=['post'], url_path='cambiar-estado')
    def cambiar_estado(self, request, pk=None):
        guia = self.get_object()
        nuevo_estado = request.data.get('estado')

        if not nuevo_estado:
            return Response(
                {'error': 'El campo "estado" es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        estados_permitidos = ESTADOS_VALIDOS.get(guia.estado, [])
        if nuevo_estado not in estados_permitidos:
            return Response(
                {
                    'error': f'Transición no permitida: {guia.estado} → {nuevo_estado}.',
                    'estados_permitidos': estados_permitidos,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        guia.estado = nuevo_estado
        guia.save(update_fields=['estado', 'updated_at'])
        return Response(GuiaRemisionSerializer(guia).data)

    @action(detail=True, methods=['get'], url_path='pdf')
    def pdf(self, request, pk=None):
        guia = self.get_object()
        try:
            buffer = GuiaRemisionPDF(guia).generar()
            filename = GuiaRemisionPDF.nombre_archivo(guia)
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response
        except Exception as exc:
            logger.error('Error generando PDF guia %s: %s', guia.numero, exc, exc_info=True)
            return Response(
                {'error': 'Error al generar el PDF.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
