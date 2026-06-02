from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
from apps.empresas.models import Empresa

class Stock(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    producto = models.ForeignKey(
        'Producto', 
        on_delete=models.CASCADE,
        related_name='stocks'
    )
    almacen = models.ForeignKey('Almacen', on_delete=models.CASCADE)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['empresa', 'producto', 'almacen']
        verbose_name = 'Stock'
        verbose_name_plural = 'Stocks'

    def __str__(self):
        return f"{self.producto.nombre} - {self.almacen.nombre}: {self.cantidad}"

    def clean(self):
        try:
            # Asegurarse de que cantidad sea Decimal
            if not isinstance(self.cantidad, Decimal):
                self.cantidad = Decimal(str(self.cantidad))
            
            # Validar que no sea negativo
            if self.cantidad < 0:
                raise ValidationError('La cantidad no puede ser negativa')
                
        except (TypeError, ValueError, InvalidOperation):
            raise ValidationError('La cantidad debe ser un número válido')

    def save(self, *args, **kwargs):
        try:
            # Convertir a Decimal si es necesario
            if not isinstance(self.cantidad, Decimal):
                self.cantidad = Decimal(str(self.cantidad))
            
            self.clean()
            super().save(*args, **kwargs)
            
            # Actualizar stock total del producto si es posible
            if hasattr(self.producto, 'actualizar_stock_total'):
                self.producto.actualizar_stock_total()
                
        except Exception as e:
            raise

    @classmethod
    def actualizar_stock_compra(cls, compra_detalle):
        """
        Actualiza el stock cuando se realiza una compra
        """
        stock, created = cls.objects.get_or_create(
            producto=compra_detalle.producto,
            almacen=compra_detalle.compra.almacen,
            empresa=compra_detalle.compra.empresa,
            defaults={'cantidad': 0}
        )
        stock.cantidad += compra_detalle.cantidad
        stock.save()