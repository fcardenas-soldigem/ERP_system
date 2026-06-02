import logging
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.empresas.models import Empresa
from apps.ventas.models import Cliente

logger = logging.getLogger(__name__)


class GuiaRemision(models.Model):
    MOTIVO_CHOICES = [
        ('ingreso_reparacion', 'Ingreso por Reparación'),
        ('devolucion_cliente', 'Devolución a Cliente'),
        ('traslado_tecnico', 'Traslado Técnico'),
        ('otro', 'Otro'),
    ]

    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('emitida', 'Emitida'),
        ('en_proceso', 'En Proceso'),
        ('entregada', 'Entregada'),
        ('cancelada', 'Cancelada'),
    ]

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='guias_remision',
    )
    numero = models.CharField(max_length=20)
    fecha_emision = models.DateField(default=timezone.now)
    fecha_traslado = models.DateField()
    motivo = models.CharField(max_length=30, choices=MOTIVO_CHOICES)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='guias_remision',
    )
    nombre_destinatario = models.CharField(max_length=200)
    ruc_destinatario = models.CharField(max_length=11, blank=True, null=True)
    direccion_origen = models.CharField(max_length=500)
    direccion_destino = models.CharField(max_length=500)
    observaciones = models.TextField(blank=True, null=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='guias_creadas',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Guía de Remisión'
        verbose_name_plural = 'Guías de Remisión'
        ordering = ['-created_at']
        unique_together = ['empresa', 'numero']

    def __str__(self):
        return f"{self.numero} - {self.nombre_destinatario}"

    @classmethod
    def generar_numero(cls, empresa):
        ultima = (
            cls.objects.filter(empresa=empresa)
            .order_by('-id')
            .first()
        )
        if ultima:
            try:
                secuencia = int(ultima.numero.split('-')[1]) + 1
            except (IndexError, ValueError):
                secuencia = 1
        else:
            secuencia = 1
        return f"GR-{secuencia:04d}"

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self.generar_numero(self.empresa)
        super().save(*args, **kwargs)


class ItemGuia(models.Model):
    guia = models.ForeignKey(
        GuiaRemision,
        on_delete=models.CASCADE,
        related_name='items',
    )
    numero_item = models.IntegerField()
    descripcion = models.CharField(max_length=500)
    serie = models.CharField(max_length=100, blank=True, null=True)
    marca = models.CharField(max_length=100, blank=True, null=True)
    modelo = models.CharField(max_length=100, blank=True, null=True)
    cantidad = models.IntegerField(default=1)
    unidad_medida = models.CharField(max_length=50, default='UNIDAD')
    estado_ingreso = models.CharField(max_length=200, blank=True, null=True)
    accesorios = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Ítem de Guía'
        verbose_name_plural = 'Ítems de Guía'
        ordering = ['numero_item']
        unique_together = ['guia', 'numero_item']

    def __str__(self):
        return f"Item {self.numero_item} - {self.descripcion}"
