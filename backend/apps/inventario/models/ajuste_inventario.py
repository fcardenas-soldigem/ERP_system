from django.db import models
from .producto import Producto
from .almacen import Almacen
from .stock import Stock

class AjusteInventario(models.Model):
    TIPO_AJUSTE = [
        ('entrada', 'Entrada por ajuste'),
        ('salida', 'Salida por ajuste'),
    ]
    
    fecha = models.DateTimeField(auto_now_add=True)
    motivo = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPO_AJUSTE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    almacen = models.ForeignKey(Almacen, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        Stock.objects.create(
            producto=self.producto,
            bodega=self.almacen,
            cantidad=self.cantidad,
            tipo_movimiento='ajuste',
            referencia=f'Ajuste #{self.id}',
            costo_unitario=self.costo_unitario
        ) 