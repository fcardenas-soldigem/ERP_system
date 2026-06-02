import logging
from django.db import models
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class OrdenServicio(models.Model):
    ESTADO_CHOICES = [
        ('diagnostico_pendiente', 'Diagnóstico Pendiente'),
        ('diagnostico_completado', 'Diagnóstico Completado'),
        ('cotizacion_enviada', 'Cotización Enviada'),
        ('cotizacion_aprobada', 'Cotización Aprobada'),
        ('en_reparacion', 'En Reparación'),
        ('reparacion_completada', 'Reparación Completada'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]

    PRIORIDAD_CHOICES = [
        ('normal', 'Normal'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='ordenes_servicio',
    )
    numero = models.CharField(max_length=20, blank=True)
    guia_remision = models.ForeignKey(
        'guias.GuiaRemision',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_servicio',
    )
    cliente = models.ForeignKey(
        'ventas.Cliente',
        on_delete=models.PROTECT,
        related_name='ordenes_servicio',
    )
    proveedor_reparacion = models.ForeignKey(
        'compras.Proveedor',
        on_delete=models.PROTECT,
        related_name='ordenes_servicio',
    )
    fecha_ingreso = models.DateField(default=timezone.now)
    fecha_diagnostico = models.DateField(null=True, blank=True)
    fecha_cotizacion_enviada = models.DateField(null=True, blank=True)
    fecha_aprobacion = models.DateField(null=True, blank=True)
    fecha_inicio_reparacion = models.DateField(null=True, blank=True)
    fecha_entrega_estimada = models.DateField(null=True, blank=True)
    fecha_entrega_real = models.DateField(null=True, blank=True)
    cotizacion = models.ForeignKey(
        'cotizaciones.Cotizacion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_servicio',
    )
    estado = models.CharField(
        max_length=30,
        choices=ESTADO_CHOICES,
        default='diagnostico_pendiente',
    )
    dias_sla = models.IntegerField(default=30)
    prioridad = models.CharField(
        max_length=10,
        choices=PRIORIDAD_CHOICES,
        default='normal',
    )
    notas_internas = models.TextField(null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ordenes_servicio_creadas',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Orden de Servicio'
        verbose_name_plural = 'Órdenes de Servicio'
        ordering = ['-created_at']
        unique_together = ['empresa', 'numero']

    def __str__(self):
        return f"{self.numero} - {self.cliente}"

    @classmethod
    def generar_numero(cls, empresa):
        ultima = (
            cls.objects.filter(empresa=empresa)
            .order_by('-id')
            .first()
        )
        if ultima and ultima.numero:
            try:
                secuencia = int(ultima.numero.split('-')[1]) + 1
            except (IndexError, ValueError):
                secuencia = cls.objects.filter(empresa=empresa).count() + 1
        else:
            secuencia = 1
        return f"OS-{secuencia:04d}"

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self.generar_numero(self.empresa)
        if not self.fecha_entrega_estimada and self.fecha_ingreso:
            from datetime import timedelta
            if isinstance(self.fecha_ingreso, str):
                from django.utils.dateparse import parse_date
                fecha = parse_date(self.fecha_ingreso)
            else:
                fecha = self.fecha_ingreso
            self.fecha_entrega_estimada = fecha + timedelta(days=self.dias_sla)
        super().save(*args, **kwargs)

    @property
    def dias_transcurridos(self):
        fin = self.fecha_entrega_real or timezone.now().date()
        return (fin - self.fecha_ingreso).days

    @property
    def dias_restantes_sla(self):
        if self.fecha_entrega_estimada:
            return (self.fecha_entrega_estimada - timezone.now().date()).days
        return None

    @property
    def estado_sla(self):
        dias = self.dias_restantes_sla
        if dias is None:
            return 'sin_fecha'
        if dias < 0:
            return 'vencido'
        if dias <= 5:
            return 'critico'
        if dias <= 10:
            return 'alerta'
        return 'ok'

    @property
    def en_riesgo(self):
        return self.estado_sla in ['vencido', 'critico', 'alerta']


class ItemOrdenServicio(models.Model):
    ESTADO_ITEM_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_diagnostico', 'En Diagnóstico'),
        ('diagnosticado', 'Diagnosticado'),
        ('en_reparacion', 'En Reparación'),
        ('reparado', 'Reparado'),
        ('no_reparable', 'No Reparable'),
        ('entregado', 'Entregado'),
    ]

    orden = models.ForeignKey(
        OrdenServicio,
        on_delete=models.CASCADE,
        related_name='items',
    )
    numero_item = models.IntegerField()
    descripcion = models.CharField(max_length=500)
    numero_serie = models.CharField(max_length=100, null=True, blank=True)
    marca = models.CharField(max_length=100, null=True, blank=True)
    modelo = models.CharField(max_length=100, null=True, blank=True)
    falla_cliente = models.TextField(null=True, blank=True)
    falla_diagnostico = models.TextField(null=True, blank=True)
    falla_adicional = models.BooleanField(default=False)
    estado_item = models.CharField(
        max_length=20,
        choices=ESTADO_ITEM_CHOICES,
        default='pendiente',
    )
    costo_proveedor = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    precio_cliente = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    margen = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    notas = models.TextField(null=True, blank=True)
    item_guia = models.ForeignKey(
        'guias.ItemGuia',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items_orden_servicio',
    )

    class Meta:
        verbose_name = 'Ítem de Orden de Servicio'
        verbose_name_plural = 'Ítems de Orden de Servicio'
        ordering = ['numero_item']
        unique_together = ['orden', 'numero_item']

    def __str__(self):
        return f"Item {self.numero_item} - {self.descripcion}"

    def save(self, *args, **kwargs):
        if self.precio_cliente is not None and self.costo_proveedor is not None:
            self.margen = self.precio_cliente - self.costo_proveedor
        super().save(*args, **kwargs)


class SeguimientoProveedor(models.Model):
    orden = models.ForeignKey(
        OrdenServicio,
        on_delete=models.CASCADE,
        related_name='seguimientos',
    )
    fecha = models.DateField(default=timezone.now)
    estado_reportado = models.CharField(max_length=200)
    fecha_entrega_prometida = models.DateField(null=True, blank=True)
    notas = models.TextField()
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='seguimientos_proveedor',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Seguimiento de Proveedor'
        verbose_name_plural = 'Seguimientos de Proveedor'
        ordering = ['-fecha', '-created_at']

    def __str__(self):
        return f"{self.orden.numero} - {self.fecha} - {self.estado_reportado}"


class HistorialEstadoOS(models.Model):
    orden = models.ForeignKey(
        OrdenServicio,
        on_delete=models.CASCADE,
        related_name='historial',
    )
    estado_anterior = models.CharField(max_length=30, blank=True)
    estado_nuevo = models.CharField(max_length=30)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='historial_estado_os',
    )
    notas = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        verbose_name = 'Historial de Estado OS'
        verbose_name_plural = 'Historial de Estados OS'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.orden.numero}: {self.estado_anterior} → {self.estado_nuevo}"
