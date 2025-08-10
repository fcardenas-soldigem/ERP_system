from django.db import models

class Empresa(models.Model):
    ruc = models.CharField(max_length=11, unique=True)
    razon_social = models.CharField(max_length=200, blank=True, default='')
    direccion = models.TextField(blank=True, default='')
    telefono = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        db_table = 'core_empresa'
    
    def __str__(self):
        return self.razon_social or self.ruc 