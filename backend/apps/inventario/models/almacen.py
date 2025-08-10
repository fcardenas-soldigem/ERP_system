from django.db import models
from apps.empresas.models import Empresa

class Almacen(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='almacenes')
    nombre = models.CharField(max_length=100)
    direccion = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Almacén'
        verbose_name_plural = 'Almacenes'
        unique_together = ['empresa', 'nombre']

    def __str__(self):
        return f"{self.nombre} - {self.empresa.nombre}"