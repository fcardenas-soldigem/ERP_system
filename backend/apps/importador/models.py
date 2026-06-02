from django.db import models
from django.conf import settings
from apps.empresas.models import Empresa


class ImportacionExcel(models.Model):
    ESTADO_CHOICES = [
        ('procesando', 'Procesando'),
        ('preview',    'En Preview'),
        ('importando', 'Importando'),
        ('completado', 'Completado'),
        ('parcial',    'Parcial (con errores)'),
        ('error',      'Error'),
    ]

    empresa         = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='importaciones')
    usuario         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    archivo         = models.FileField(upload_to='importaciones/', null=True, blank=True)
    nombre_archivo  = models.CharField(max_length=255)
    fecha           = models.DateTimeField(auto_now_add=True)
    estado          = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='procesando')

    # Contadores
    total_filas        = models.IntegerField(default=0)
    filas_importadas   = models.IntegerField(default=0)
    filas_con_error    = models.IntegerField(default=0)

    # Stats de entidades creadas
    proveedores_creados = models.IntegerField(default=0)
    productos_creados   = models.IntegerField(default=0)
    compras_creadas     = models.IntegerField(default=0)
    ventas_creadas      = models.IntegerField(default=0)

    # JSON blobs
    preview_json  = models.JSONField(default=dict, blank=True)
    mapeo_json    = models.JSONField(default=dict, blank=True)
    errores_json  = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Importación Excel'
        verbose_name_plural = 'Importaciones Excel'

    def __str__(self):
        return f"Importación {self.nombre_archivo} — {self.fecha:%Y-%m-%d %H:%M}"


class MapeoColumnas(models.Model):
    """Guarda mapeos validados para autocompletar importaciones futuras."""

    empresa         = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='mapeos_columnas')
    nombre_hoja     = models.CharField(max_length=100)
    columnas_origen = models.JSONField()   # ["PRODUCTO", "PROVEEDOR", ...]
    mapeo           = models.JSONField()   # {"PRODUCTO": "producto_nombre", ...}
    usos            = models.IntegerField(default=1)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Mapeo de Columnas'
        verbose_name_plural = 'Mapeos de Columnas'

    def __str__(self):
        return f"Mapeo '{self.nombre_hoja}' — {self.empresa}"
