"""
Rutas de subida, validación y lectura segura de archivos.

Centraliza:
  - `UploadToEmpresa(tipo)`: callable de `upload_to` que genera rutas aisladas por
    empresa `empresa_<id>/<tipo>/<uuid>.<ext>` (aislamiento multi-tenant también en
    el storage). Es `@deconstructible` para que las migraciones lo serialicen.
  - `validate_upload`: valida tipo (pdf/jpg/png/webp) y tamaño máximo (settings).
  - `read_field_bytes` / `field_url_safe`: lectura tolerante a archivos faltantes,
    para no romper PDFs ni serializers cuando el blob no existe en el storage (GCS).

Con GCS no hay ruta local: NUNCA usar `FieldFile.path`. Para leer un archivo (p. ej.
logo/firma en un PDF) usar `read_field_bytes`; para exponer una URL usar `field_url_safe`.
"""
import os
import tempfile
import uuid
from contextlib import contextmanager

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


def _resolve_empresa_id(instance):
    """Resuelve el id de la empresa dueña del archivo, para aislar la ruta.

    Prueba, en orden: FK directa `empresa`, el propio registro si ES una Empresa,
    relaciones indirectas (compra/venta/orden/recepción/pago) y, por último, el
    usuario asociado. Devuelve None si no puede resolverla (se usa 'sin_empresa').
    """
    eid = getattr(instance, 'empresa_id', None)
    if eid:
        return eid
    emp = getattr(instance, 'empresa', None)
    if emp is not None and getattr(emp, 'pk', None):
        return emp.pk
    # El registro ES el tenant (Empresa.logo / firma_*).
    if type(instance).__name__ == 'Empresa' and getattr(instance, 'pk', None):
        return instance.pk
    # Relaciones indirectas comunes.
    for rel in ('compra', 'venta', 'orden_compra', 'orden', 'recepcion', 'pago'):
        if getattr(instance, f'{rel}_id', None):
            rel_obj = getattr(instance, rel, None)
            rel_eid = getattr(rel_obj, 'empresa_id', None) if rel_obj else None
            if rel_eid:
                return rel_eid
    # Vía usuario.
    for uattr in ('user', 'usuario'):
        u = getattr(instance, uattr, None)
        if u is not None and getattr(u, 'empresa_id', None):
            return u.empresa_id
    return None


@deconstructible
class UploadToEmpresa:
    """`upload_to` que aísla por empresa: `empresa_<id>/<tipo>/<uuid>.<ext>`."""

    def __init__(self, tipo):
        self.tipo = tipo

    def __call__(self, instance, filename):
        ext = os.path.splitext(filename or '')[1].lower().lstrip('.') or 'bin'
        empresa_id = _resolve_empresa_id(instance) or 'sin_empresa'
        return f'empresa_{empresa_id}/{self.tipo}/{uuid.uuid4().hex}.{ext}'

    def __eq__(self, other):
        return isinstance(other, UploadToEmpresa) and other.tipo == self.tipo

    def __hash__(self):
        return hash(('UploadToEmpresa', self.tipo))


SPREADSHEET_EXTENSIONS = {'xlsx', 'xls', 'csv'}


def _check_size(f):
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    size = getattr(f, 'size', None)
    if size and size > max_bytes:
        raise ValidationError(f'El archivo supera el máximo de {settings.MAX_UPLOAD_SIZE_MB} MB.')


def _ext(f):
    return os.path.splitext(getattr(f, 'name', '') or '')[1].lower().lstrip('.')


def validate_upload(f):
    """Documentos/imágenes: tamaño (<= MAX_UPLOAD_SIZE_MB) y tipo (pdf/jpg/png/webp)."""
    _check_size(f)
    if _ext(f) not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        permitidos = ', '.join(sorted(settings.ALLOWED_UPLOAD_EXTENSIONS)).upper()
        raise ValidationError(f'Tipo de archivo no permitido. Usa: {permitidos}.')


def validate_spreadsheet(f):
    """Importador: tamaño y tipo de hoja de cálculo (xlsx/xls/csv)."""
    _check_size(f)
    if _ext(f) not in SPREADSHEET_EXTENSIONS:
        raise ValidationError('Tipo de archivo no permitido. Usa: XLSX, XLS o CSV.')


def read_field_bytes(fieldfile):
    """Bytes del archivo, o None si el campo está vacío o el blob no existe.

    Usa la API de storage (`open`), compatible con GCS y disco local. No usa `.path`.
    """
    if not fieldfile:
        return None
    try:
        with fieldfile.open('rb') as fh:
            return fh.read()
    except Exception:
        return None


def field_url_safe(fieldfile):
    """URL del archivo, o None si está vacío o no se puede resolver (nunca lanza)."""
    if not fieldfile:
        return None
    try:
        return fieldfile.url
    except Exception:
        return None


def field_exists(fieldfile):
    """True si el campo tiene un blob presente en el storage (consulta la red en GCS)."""
    if not fieldfile:
        return False
    try:
        return fieldfile.storage.exists(fieldfile.name)
    except Exception:
        return False


@contextmanager
def field_as_tempfile(fieldfile, suffix=''):
    """Materializa el archivo en un tempfile local y cede su ruta.

    Para librerías que exigen una ruta de filesystem (pandas/openpyxl). Funciona
    con GCS (descarga) y disco local. Cede None si el archivo no existe. Limpia el
    tempfile al salir.
    """
    data = read_field_bytes(fieldfile)
    if data is None:
        yield None
        return
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(data)
        tmp.flush()
        tmp.close()
        yield tmp.name
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
