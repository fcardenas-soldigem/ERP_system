"""
Modelos de Gastos Operativos para el módulo de Finanzas.
"""

from django.conf import settings
from django.db import models
from apps.empresas.models import Empresa


class CategoriaGasto(models.Model):
    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name='categorias_gasto'
    )
    nombre = models.CharField(max_length=100)
    icono = models.CharField(max_length=50, blank=True)   # nombre react-icon, ej: "FiUsers"
    color = models.CharField(max_length=20, blank=True)   # hex color, ej: "#7c3aed"
    es_fijo = models.BooleanField(
        default=False,
        help_text='True = gasto fijo (planilla, alquiler). False = variable.'
    )
    orden = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['orden', 'nombre']
        unique_together = [['empresa', 'nombre']]
        verbose_name = 'Categoría de Gasto'
        verbose_name_plural = 'Categorías de Gasto'

    def __str__(self):
        return f'{self.nombre} ({self.empresa})'


class GastoOperativo(models.Model):
    ESTADO_CHOICES = [
        ('pagado', 'Pagado'),
        ('pendiente', 'Pendiente'),
        ('programado', 'Programado'),
    ]
    COMPROBANTE_CHOICES = [
        ('factura', 'Factura'),
        ('boleta', 'Boleta'),
        ('recibo_honorarios', 'Recibo x Hon.'),
        ('sin_comprobante', 'Sin comprobante'),
    ]
    MONEDA_CHOICES = [
        ('PEN', 'Sol Peruano'),
        ('USD', 'Dólar'),
    ]

    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name='gastos_operativos'
    )
    categoria = models.ForeignKey(
        CategoriaGasto, on_delete=models.PROTECT, related_name='gastos'
    )
    descripcion = models.CharField(max_length=300)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=3, default='PEN', choices=MONEDA_CHOICES)
    fecha = models.DateField()
    es_recurrente = models.BooleanField(default=False)
    frecuencia = models.CharField(
        max_length=20, blank=True, null=True,
        help_text='mensual / quincenal / semanal'
    )
    comprobante_tipo = models.CharField(
        max_length=30, blank=True, null=True, choices=COMPROBANTE_CHOICES
    )
    comprobante_numero = models.CharField(max_length=50, blank=True, null=True)
    proveedor_servicio = models.CharField(max_length=200, blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pagado')
    notas = models.TextField(blank=True, null=True)
    archivo_adjunto = models.FileField(upload_to='gastos/', null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='gastos_creados',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha', '-created_at']
        verbose_name = 'Gasto Operativo'
        verbose_name_plural = 'Gastos Operativos'

    def __str__(self):
        return f'{self.descripcion} — S/{self.monto} ({self.fecha})'


class GastoRecurrente(models.Model):
    FRECUENCIA_CHOICES = [
        ('mensual', 'Mensual'),
        ('quincenal', 'Quincenal'),
        ('semanal', 'Semanal'),
    ]

    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name='gastos_recurrentes'
    )
    categoria = models.ForeignKey(
        CategoriaGasto, on_delete=models.PROTECT, related_name='gastos_recurrentes'
    )
    descripcion = models.CharField(max_length=300)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=3, default='PEN')
    frecuencia = models.CharField(
        max_length=20, choices=FRECUENCIA_CHOICES, default='mensual'
    )
    dia_del_mes = models.IntegerField(default=1, help_text='Día del mes (1-31)')
    activo = models.BooleanField(default=True)
    ultimo_generado = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['descripcion']
        verbose_name = 'Gasto Recurrente'
        verbose_name_plural = 'Gastos Recurrentes'

    def __str__(self):
        return f'{self.descripcion} — {self.get_frecuencia_display()} S/{self.monto}'
