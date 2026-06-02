from django.db import models
from django.conf import settings


class PermisoUsuario(models.Model):
    """Permisos granulares por usuario y módulo (para rol 'personalizado')."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='permisos',
    )

    MODULO_CHOICES = [
        ('ventas', 'Ventas'),
        ('cotizaciones', 'Cotizaciones'),
        ('cuentas_cobrar', 'Cuentas por Cobrar'),
        ('compras', 'Compras'),
        ('inventario', 'Inventario'),
        ('produccion', 'Producción'),
        ('reportes', 'Reportes'),
        ('configuracion', 'Configuración'),
        ('dashboard', 'Dashboard'),
    ]
    modulo = models.CharField(max_length=50, choices=MODULO_CHOICES)

    puede_ver = models.BooleanField(default=False)
    puede_crear = models.BooleanField(default=False)
    puede_editar = models.BooleanField(default=False)
    puede_eliminar = models.BooleanField(default=False)

    class Meta:
        app_label = 'core'
        db_table = 'core_permiso_usuario'
        unique_together = ['usuario', 'modulo']
        verbose_name = 'Permiso de Usuario'
        verbose_name_plural = 'Permisos de Usuarios'

    def __str__(self):
        return f"{self.usuario.email} - {self.modulo}"
