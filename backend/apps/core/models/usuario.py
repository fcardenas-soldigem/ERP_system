from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.conf import settings
from apps.empresas.models import Empresa

class Usuario(models.Model):
    ROLES = (
        ('admin', 'Administrador'),
        ('vendedor', 'Vendedor'),
        ('almacen', 'Almacén'),
        ('contador', 'Contador'),
    )
    
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    rol = models.CharField(max_length=20, choices=ROLES)
    telefono = models.CharField(max_length=20, blank=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        db_table = 'core_usuario'
    
    def __str__(self):
        return f"{self.usuario.username} - {self.empresa.nombre}"

    # Añade aquí cualquier campo personalizado
    pass