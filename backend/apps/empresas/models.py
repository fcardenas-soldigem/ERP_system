from django.db import models
from django.utils import timezone

class Empresa(models.Model):
    nombre = models.CharField(max_length=200)
    ruc = models.CharField(max_length=11, unique=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    telefono = models.CharField(max_length=9, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True, help_text="Logo de la empresa para cotizaciones y documentos")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['-created_at']

    def __str__(self):
        return self.nombre 