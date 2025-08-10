from django.db import models
from apps.empresas.models import Empresa

class Almacen(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.TextField()
    is_active = models.BooleanField(default=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='almacenes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Almacén'
        verbose_name_plural = 'Almacenes'
        ordering = ['-created_at']
        unique_together = ['empresa', 'nombre']
        db_table = 'inventario_almacen'  # Especificamos el nombre de la tabla explícitamente 