from django.db import models, transaction
from django.core.exceptions import ValidationError
from apps.empresas.models import Empresa
from .categoria import Categoria
from .almacen import Almacen

class Producto(models.Model):
    ESTADO_CHOICES = [
        ('disponible', 'Disponible'),
        ('sin_stock', 'Sin Stock'),
        ('stock_bajo', 'Stock Bajo'),
    ]
    
    TIPO_PRODUCTO_CHOICES = [
        ('RAW', 'Materia Prima / Insumo'),
        ('SEMIFINISHED', 'Semi-Terminado'),
        ('FINISHED', 'Producto Terminado'),
    ]
    
    MONEDA_CHOICES = [
        ('PEN', 'Sol Peruano (S/)'),
        ('USD', 'Dólar Americano ($)'),
    ]
    
    UNIDAD_MEDIDA_CHOICES = [
        ('unidad', 'Unidad'),
        ('kilo', 'Kilogramo'),
        ('gramo', 'Gramo'),
        ('litro', 'Litro'),
        ('metro', 'Metro'),
        ('decena', 'Decena'),
        ('docena', 'Docena'),
        ('centenar', 'Centenar'),
        ('millar', 'Millar'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='productos')
    sku = models.CharField(max_length=50, verbose_name='SKU')
    nombre = models.CharField(max_length=200, verbose_name='Nombre')
    tipo_producto = models.CharField(
        max_length=20,
        choices=TIPO_PRODUCTO_CHOICES,
        default='RAW',
        verbose_name='Tipo de Producto',
        help_text='Clasificación del producto para producción'
    )
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    stock_total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Stock Total')
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Stock Mínimo')
    alerta_stock = models.BooleanField(default=False)
    categoria = models.ForeignKey(
        Categoria, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name='Categoría',
        related_name='productos'
    )
    almacen = models.ForeignKey(
        Almacen, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name='Almacén'
    )
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    precio_compra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Precio de Compra'
    )
    precio_venta = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Precio de Venta'
    )
    moneda = models.CharField(
        max_length=3,
        choices=MONEDA_CHOICES,
        default='PEN',
        verbose_name='Moneda'
    )
    margen = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Margen de Ganancia (%)'
    )
    stock_maximo = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Stock Máximo')
    unidad_medida = models.CharField(
        max_length=20,
        choices=UNIDAD_MEDIDA_CHOICES,
        default='unidad',
        verbose_name='Unidad de Medida'
    )
    marca = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='Marca',
    )

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['sku']
        unique_together = ('empresa', 'sku')

    def __str__(self):
        return f"{self.sku} - {self.nombre}"

    def clean(self):
        if self.stock_minimo > self.stock_maximo:
            raise ValidationError('El stock mínimo no puede ser mayor al stock máximo')

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        if self.precio_compra and self.precio_venta and self.precio_venta > 0:
            self.margen = ((self.precio_venta - self.precio_compra) / self.precio_venta) * 100
        else:
            self.margen = 0
        
        with transaction.atomic():
            self.clean()
            super().save(*args, **kwargs)
            
            if is_new and self.almacen:
                from .stock import Stock
                Stock.objects.create(
                    empresa=self.empresa,
                    producto=self,
                    almacen=self.almacen,
                    cantidad=self.stock_total or 0
                )

    def get_stock_total(self):
        from .stock import Stock
        total = Stock.objects.filter(
            producto=self,
            empresa=self.empresa
        ).aggregate(
            total=models.Sum('cantidad')
        )['total'] or 0
        return total

    def actualizar_stock_total(self):
        from .stock import Stock
        total = Stock.objects.filter(
            producto=self,
            empresa=self.empresa
        ).aggregate(
            total=models.Sum('cantidad')
        )['total'] or 0
        
        self.stock_total = total
        self.alerta_stock = total <= self.stock_minimo
        self.save(update_fields=['stock_total', 'alerta_stock'])
        return total

    @property
    def estado(self):
        if self.stock_total <= 0:
            return 'sin_stock'
        elif self.stock_total <= self.stock_minimo:
            return 'stock_bajo'
        return 'disponible'

    def get_estado_display(self):
        estados = {
            'disponible': 'Disponible',
            'sin_stock': 'Sin Stock',
            'stock_bajo': 'Stock Bajo'
        }
        return estados.get(self.estado, 'Desconocido')
    
    def get_simbolo_moneda(self):
        simbolos = {
            'PEN': 'S/',
            'USD': '$'
        }
        return simbolos.get(self.moneda, 'S/')
    
    def get_precio_compra_formateado(self):
        return f"{self.get_simbolo_moneda()} {self.precio_compra}"
    
    def get_precio_venta_formateado(self):
        return f"{self.get_simbolo_moneda()} {self.precio_venta}" 