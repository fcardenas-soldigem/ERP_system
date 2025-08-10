from django.db import models

class Empresa(models.Model):
    razon_social = models.CharField(max_length=200)
    ruc = models.CharField(max_length=11, unique=True)
    direccion = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['razon_social']

    def __str__(self):
        return self.razon_social 