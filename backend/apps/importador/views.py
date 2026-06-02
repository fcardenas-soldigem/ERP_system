import logging

from django.db import transaction
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventario.models.almacen import Almacen
from apps.inventario.models.categoria import Categoria
from apps.ventas.models import Cliente

from .models import ImportacionExcel, MapeoColumnas
from .serializers import ImportacionExcelSerializer
from .services import ExcelParserService, ImportService, PreviewService

logger = logging.getLogger(__name__)


def _get_empresa(request):
    """Obtiene la empresa del usuario, siguiendo el mismo patrón que el resto del ERP."""
    try:
        return request.user.empresa
    except Exception:
        return None


# ─── POST /api/importador/upload/ ─────────────────────────────────────────────

class UploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    _MAX_FILE_SIZE_MB = 10

    def post(self, request):
        archivo = request.FILES.get('archivo')
        if not archivo:
            return Response({'error': 'No se proporcionó archivo'}, status=400)

        ext = archivo.name.lower().rsplit('.', 1)[-1]
        if ext not in ('xlsx', 'xls', 'csv'):
            return Response(
                {'error': f'Formato ".{ext}" no soportado. Use .xlsx, .xls o .csv'},
                status=400,
            )

        max_bytes = self._MAX_FILE_SIZE_MB * 1024 * 1024
        if archivo.size > max_bytes:
            return Response(
                {'error': f'El archivo supera el límite de {self._MAX_FILE_SIZE_MB} MB'},
                status=400,
            )

        empresa = _get_empresa(request)
        if not empresa:
            return Response({'error': 'No se encontró empresa para este usuario'}, status=400)

        importacion = ImportacionExcel.objects.create(
            empresa=empresa,
            usuario=request.user,
            archivo=archivo,
            nombre_archivo=archivo.name,
            estado='procesando',
        )

        try:
            preview_svc = PreviewService()
            preview = preview_svc.get_preview(importacion.archivo.path, empresa)
            importacion.preview_json = preview
            importacion.estado = 'preview'
            importacion.save(update_fields=['preview_json', 'estado'])

            # Contexto de defaults disponibles
            almacenes  = list(Almacen.objects.filter(empresa=empresa, is_active=True).values('id', 'nombre'))
            categorias = list(Categoria.objects.filter(empresa=empresa).values('id', 'nombre'))
            clientes   = list(Cliente.objects.filter(empresa=empresa, activo=True).values('id', 'nombre', 'documento'))

            return Response({
                'id':             importacion.id,
                'nombre_archivo': importacion.nombre_archivo,
                'preview':        preview,
                'defaults_ctx': {
                    'almacenes':  almacenes,
                    'categorias': categorias,
                    'clientes':   clientes,
                },
            })

        except Exception as exc:
            logger.error("Error en preview: %s", exc, exc_info=True)
            importacion.estado = 'error'
            importacion.errores_json = [str(exc)]
            importacion.save(update_fields=['estado', 'errores_json'])
            return Response({'error': str(exc)}, status=400)


# ─── GET /api/importador/preview/<id>/ ────────────────────────────────────────

class PreviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        empresa = _get_empresa(request)
        try:
            imp = ImportacionExcel.objects.get(pk=pk, empresa=empresa)
        except ImportacionExcel.DoesNotExist:
            return Response({'error': 'No encontrado'}, status=404)

        almacenes  = list(Almacen.objects.filter(empresa=empresa, is_active=True).values('id', 'nombre'))
        categorias = list(Categoria.objects.filter(empresa=empresa).values('id', 'nombre'))
        clientes   = list(Cliente.objects.filter(empresa=empresa, activo=True).values('id', 'nombre', 'documento'))

        return Response({
            'id':             imp.id,
            'nombre_archivo': imp.nombre_archivo,
            'estado':         imp.estado,
            'preview':        imp.preview_json,
            'defaults_ctx': {
                'almacenes':  almacenes,
                'categorias': categorias,
                'clientes':   clientes,
            },
        })


# ─── POST /api/importador/confirmar/<id>/ ─────────────────────────────────────

class ConfirmarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        empresa = _get_empresa(request)
        try:
            imp = ImportacionExcel.objects.get(pk=pk, empresa=empresa)
        except ImportacionExcel.DoesNotExist:
            return Response({'error': 'No encontrado'}, status=404)

        if imp.estado not in ('preview', 'error'):
            return Response(
                {'error': f'La importación está en estado "{imp.estado}" y no puede confirmarse'},
                status=400,
            )

        hojas_config = request.data.get('hojas_config', [])
        modo_parcial = bool(request.data.get('modo_parcial', True))

        if not hojas_config:
            return Response({'error': 'No se proporcionó configuración de hojas'}, status=400)

        # Guardar mapeo para autocompletar futuras
        self._save_mappings(empresa, hojas_config)

        svc = ImportService(imp, request.user)
        try:
            if modo_parcial:
                svc.run(hojas_config, modo_parcial=True)
            else:
                with transaction.atomic():
                    svc.run(hojas_config, modo_parcial=False)
        except Exception as exc:
            return Response({'error': str(exc)}, status=500)

        return Response(ImportacionExcelSerializer(imp).data)

    def _save_mappings(self, empresa, hojas_config):
        for hoja_cfg in hojas_config:
            if not hoja_cfg.get('incluir', True):
                continue
            mapeo = hoja_cfg.get('mapeo_columnas', {})
            if not mapeo:
                continue
            nombre = hoja_cfg.get('nombre_hoja', '')
            columnas = list(mapeo.keys())
            obj, created = MapeoColumnas.objects.get_or_create(
                empresa=empresa,
                nombre_hoja=nombre,
                defaults={'columnas_origen': columnas, 'mapeo': mapeo},
            )
            if not created:
                obj.usos += 1
                obj.mapeo = mapeo
                obj.save(update_fields=['usos', 'mapeo'])


# ─── GET /api/importador/estado/<id>/ ─────────────────────────────────────────

class EstadoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        empresa = _get_empresa(request)
        try:
            imp = ImportacionExcel.objects.get(pk=pk, empresa=empresa)
        except ImportacionExcel.DoesNotExist:
            return Response({'error': 'No encontrado'}, status=404)

        return Response(ImportacionExcelSerializer(imp).data)


# ─── GET /api/importador/historial/ ───────────────────────────────────────────

class HistorialView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa = _get_empresa(request)
        qs = ImportacionExcel.objects.filter(empresa=empresa).order_by('-fecha')[:20]
        return Response(ImportacionExcelSerializer(qs, many=True).data)
