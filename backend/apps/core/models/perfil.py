from django.db import models
from django.conf import settings

from apps.core.uploads import UploadToEmpresa, validate_upload

class Perfil(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    direccion = models.TextField(blank=True, default='')
    foto = models.ImageField(upload_to=UploadToEmpresa('perfiles'), validators=[validate_upload], null=True, blank=True)
    
    class Meta:
        app_label = 'core'
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfiles'
        db_table = 'core_perfil'

    def __str__(self):
        return f"Perfil de {self.usuario.username}"