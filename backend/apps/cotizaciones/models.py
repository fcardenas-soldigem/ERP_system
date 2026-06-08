from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.conf import settings
from apps.empresas.models import Empresa
from apps.ventas.models import Cliente
from apps.inventario.models import Producto


class Cotizacion(models.Model):
    """
    Modelo para gestionar cotizaciones de productos/servicios
    """
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('enviada', 'Enviada'),
        ('aceptada', 'Aceptada'),
        ('rechazada', 'Rechazada'),
        ('vencida', 'Vencida'),
        ('convertida', 'Convertida a Venta'),
    ]
    
    MONEDA_CHOICES = [
        ('PEN', 'Soles (S/)'),
        ('USD', 'Dólares ($)'),
    ]
    
    # Identificación
    numero = models.CharField(
        max_length=20,
        unique=True,
        help_text="Número de cotización (ej: COT-00000001)"
    )
    
    # Relaciones
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='cotizaciones'
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='cotizaciones'
    )
    usuario_creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='cotizaciones_creadas'
    )
    
    # Información de la cotización
    asunto = models.CharField(max_length=255, help_text="Asunto o título de la cotización")
    descripcion = models.TextField(blank=True, null=True, help_text="Descripción adicional")
    
    # Fechas
    fecha_emision = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField(help_text="Fecha de vencimiento de la cotización")
    fecha_aceptacion = models.DateField(blank=True, null=True)
    
    # Estado y moneda
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    moneda = models.CharField(max_length=3, choices=MONEDA_CHOICES, default='PEN')
    
    # Valores monetarios
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    descuento = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    igv = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Configuración
    incluye_igv = models.BooleanField(default=True)
    precios_incluyen_igv = models.BooleanField(
        default=False,
        help_text="True si los precios ingresados ya incluyen IGV (se extrae). False si los precios no incluyen IGV (se agrega)."
    )
    porcentaje_igv = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('18.00'),
        help_text="Porcentaje de IGV (por defecto 18%)"
    )
    
    # Contacto de la cotización (editable, independiente del cliente)
    contacto_nombre = models.CharField(
        max_length=200, null=True, blank=True,
        verbose_name='Nombre del contacto'
    )
    contacto_email = models.EmailField(
        null=True, blank=True,
        verbose_name='Email del contacto'
    )

    # Condiciones comerciales
    forma_pago = models.CharField(max_length=100, default='Contado')
    pago_facturas = models.CharField(max_length=200, blank=True, null=True, help_text="Horario de pago de facturas")
    tiempo_entrega = models.CharField(max_length=100, blank=True, null=True)
    lugar_entrega = models.TextField(blank=True, null=True)
    validez_oferta = models.CharField(max_length=100, default='30 días')
    
    # Notas y observaciones
    notas = models.TextField(blank=True, null=True, help_text="Notas adicionales para el cliente")
    terminos_condiciones = models.TextField(blank=True, null=True)
    
    # Venta relacionada (si se convierte)
    venta = models.ForeignKey(
        'ventas.Venta',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='cotizacion_origen'
    )
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cotizaciones'
        ordering = ['-fecha_emision', '-numero']
        verbose_name = 'Cotización'
        verbose_name_plural = 'Cotizaciones'
        indexes = [
            models.Index(fields=['empresa', 'estado']),
            models.Index(fields=['cliente']),
            models.Index(fields=['fecha_emision']),
            models.Index(fields=['numero']),
        ]
    
    def __str__(self):
        return f"{self.numero} - {self.cliente.nombre} - {self.get_estado_display()}"
    
    def calcular_totales(self):
        """
        Calcula los totales de la cotización basándose en los detalles
        """
        # Limpiar el cache de prefetch para forzar una consulta fresca a la BD
        if hasattr(self, '_prefetched_objects_cache'):
            self._prefetched_objects_cache.pop('detalles', None)

        detalles = self.detalles.all()
        
        # Calcular subtotal
        self.subtotal = sum(detalle.subtotal for detalle in detalles)
        
        # Aplicar descuento si existe
        subtotal_con_descuento = self.subtotal - self.descuento
        
        # Calcular IGV
        if self.precios_incluyen_igv:
            # Los precios ya incluyen IGV → extraer
            pct = self.porcentaje_igv
            self.igv = (subtotal_con_descuento * pct / (Decimal('100') + pct)).quantize(Decimal('0.01'))
            self.total = subtotal_con_descuento
        elif self.incluye_igv:
            # Los precios NO incluyen IGV → agregar el 18%
            self.igv = (subtotal_con_descuento * self.porcentaje_igv / Decimal('100')).quantize(Decimal('0.01'))
            self.total = subtotal_con_descuento + self.igv
        else:
            self.igv = Decimal('0.00')
            self.total = subtotal_con_descuento
        
        self.save()
    
    def generar_numero(self):
        """
        Genera el número de cotización automáticamente
        """
        if not self.numero:
            # Obtener el último número de cotización de la empresa
            ultima_cotizacion = Cotizacion.objects.filter(
                empresa=self.empresa
            ).order_by('-numero').first()
            
            if ultima_cotizacion and ultima_cotizacion.numero:
                try:
                    # Extraer el número de la última cotización
                    ultimo_numero = int(ultima_cotizacion.numero.split('-')[1])
                    nuevo_numero = ultimo_numero + 1
                except (IndexError, ValueError):
                    nuevo_numero = 1
            else:
                nuevo_numero = 1
            
            self.numero = f"COT-{nuevo_numero:08d}"
    
    def save(self, *args, **kwargs):
        if not self.numero:
            self.generar_numero()
        super().save(*args, **kwargs)


class DetalleCotizacion(models.Model):
    """
    Detalle de productos/servicios en una cotización
    """
    cotizacion = models.ForeignKey(
        Cotizacion,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='detalles_cotizacion',
        blank=True,
        null=True
    )
    
    # Información del item (puede ser producto o servicio personalizado)
    codigo = models.CharField(max_length=50, blank=True, null=True)
    descripcion = models.TextField()
    
    # Cantidades y precios
    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    descuento_item = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Orden de visualización
    orden = models.PositiveIntegerField(default=0)
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'detalles_cotizacion'
        ordering = ['orden', 'id']
        verbose_name = 'Detalle de Cotización'
        verbose_name_plural = 'Detalles de Cotización'
    
    def __str__(self):
        return f"{self.cotizacion.numero} - {self.descripcion[:50]}"
    
    def calcular_subtotal(self):
        """
        Calcula el subtotal del detalle
        """
        self.subtotal = (self.cantidad * self.precio_unitario) - self.descuento_item
        return self.subtotal
    
    def save(self, *args, **kwargs):
        self.calcular_subtotal()
        super().save(*args, **kwargs)
        # Recalcular totales de la cotización
        self.cotizacion.calcular_totales()

