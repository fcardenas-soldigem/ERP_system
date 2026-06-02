import uuid as uuid_lib
from decimal import Decimal
from django.db import models
from django.utils import timezone


class Empresa(models.Model):
    nombre = models.CharField(max_length=200)
    ruc = models.CharField(max_length=11, unique=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    telefono = models.CharField(max_length=9, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True, help_text="Logo de la empresa para cotizaciones y documentos")
    firma_elaborado = models.ImageField(upload_to='firmas/', blank=True, null=True, help_text="Firma digital - Elaborado por")
    firma_aprobado = models.ImageField(upload_to='firmas/', blank=True, null=True, help_text="Firma digital - Aprobado por")
    uuid = models.UUIDField(default=uuid_lib.uuid4, unique=True, editable=False)
    is_active = models.BooleanField(default=True)
    tipo_cambio_usd = models.DecimalField(
        max_digits=8, decimal_places=4, default=Decimal('3.70'),
        verbose_name='Tipo de cambio USD→PEN',
        help_text='Soles por cada dólar. Se usa para convertir montos en USD a PEN en reportes y dashboard.'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['-created_at']

    def __str__(self):
        return self.nombre 