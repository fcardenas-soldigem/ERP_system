from django.db import models
from apps.empresas.models import Empresa

class Categoria(models.Model):
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.CASCADE, 
        related_name='categorias',
        null=True,  # Permitimos temporalmente valores nulos
        blank=True  # Permitimos temporalmente que el campo esté vacío
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    class Meta:
        ordering = ['nombre']
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        unique_together = ('empresa', 'nombre')
        
    def __str__(self):
        return f"{self.nombre} - {self.empresa.nombre if self.empresa else 'Sin empresa'}"