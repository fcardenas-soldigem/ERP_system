from django.db import models
from django.conf import settings
from apps.empresas.models import Empresa
from apps.inventario.models.producto import Producto
from apps.inventario.models.stock import Stock
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
import os
from django.core.validators import MinValueValidator
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

class Cliente(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='clientes')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    nombre = models.CharField(max_length=200, verbose_name='Nombre/Razón Social')
    documento = models.CharField(max_length=20, verbose_name='DNI/RUC')  # RUC o DNI
    direccion = models.TextField(blank=True, null=True, verbose_name='Dirección')
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name='Teléfono')
    email = models.EmailField(blank=True, null=True, verbose_name='Email')
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    TIPO_DOCUMENTO_CHOICES = [
        ('dni', 'DNI'),
        ('ruc', 'RUC'),
    ]
    tipo_documento = models.CharField(max_length=10, choices=TIPO_DOCUMENTO_CHOICES, default='dni')

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['-fecha_registro']
        unique_together = ('empresa', 'documento')

    def __str__(self):
        return f"{self.nombre} - {self.documento}"

def comprobante_upload_to(instance, filename):
    # Generar la ruta para el archivo
    return f'ventas/comprobantes/{instance.venta.empresa.id}/{instance.venta.numero}/{filename}'

class ComprobantePago(models.Model):
    venta = models.OneToOneField('Venta', on_delete=models.CASCADE, related_name='comprobante_pago')
    archivo = models.FileField(upload_to=comprobante_upload_to)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=50, choices=[
        ('boleta', 'Boleta'),
        ('factura', 'Factura'),
        ('ticket', 'Ticket'),
        ('otro', 'Otro')
    ])
    numero = models.CharField(max_length=50, blank=True, null=True)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Comprobante de Pago'
        verbose_name_plural = 'Comprobantes de Pago'

    def __str__(self):
        return f'Comprobante {self.tipo} - Venta {self.venta.numero}'

    def delete(self, *args, **kwargs):
        # Eliminar el archivo físico
        if self.archivo:
            if os.path.isfile(self.archivo.path):
                os.remove(self.archivo.path)
        super().delete(*args, **kwargs)

class Venta(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('anulado', 'Anulado')
    ]

    TIPO_VENTA_CHOICES = [
        ('contado', 'Contado'),
        ('credito_30', 'Crédito 30 días'),
        ('credito_60', 'Crédito 60 días')
    ]

    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('tarjeta', 'Tarjeta'),
        ('cheque', 'Cheque')
    ]
    
    MONEDA_CHOICES = [
        ('PEN', 'Sol Peruano (S/)'),
        ('USD', 'Dólar Americano ($)'),
    ]

    id = models.BigAutoField(primary_key=True)
    numero = models.CharField(max_length=20, unique=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT)
    cliente = models.ForeignKey('Cliente', on_delete=models.PROTECT)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    tipo_venta = models.CharField(max_length=20, choices=TIPO_VENTA_CHOICES, default='contado')
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, null=True, blank=True)
    igv_incluido = models.BooleanField(default=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    igv = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pagos_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    moneda = models.CharField(
        max_length=3,
        choices=MONEDA_CHOICES,
        default='PEN',
        verbose_name='Moneda'
    )
    notas = models.TextField(blank=True)
    referencia = models.CharField(max_length=100, blank=True)
    comprobante = models.FileField(upload_to='comprobantes/', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_emision']
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'

    def __str__(self):
        return f"Venta {self.numero} - {self.cliente.nombre}"

    def get_saldo_pendiente(self):
        # Solo considerar pagos que no estén en estado pendiente
        pagado = self.pagos.exclude(metodo_pago='pendiente').aggregate(
            total=models.Sum('monto')
        )['total'] or 0
        return self.total - pagado

    def get_simbolo_moneda(self):
        simbolos = {
            'PEN': 'S/',
            'USD': '$'
        }
        return simbolos.get(self.moneda, 'S/')

    def clean(self):
        if not self.empresa_id:
            raise ValidationError('La venta debe tener una empresa asignada')
        if not self.cliente_id:
            raise ValidationError('La venta debe tener un cliente asignado')
        super().clean()

    def save(self, *args, **kwargs):
        print(f"DEBUG SAVE: Método save llamado, numero actual: {self.numero}")
        if not self.numero:
            if not self.empresa:
                raise ValidationError('La venta debe tener una empresa asignada antes de generar el número')
            
            # Generar número de forma thread-safe
            from django.db import transaction
            with transaction.atomic():
                print(f"DEBUG SAVE: Generando número para empresa: {self.empresa} (ID: {self.empresa.id})")
                
                # Obtener todas las ventas existentes para esta empresa y extraer los números
                # Usar empresa_id para evitar problemas de comparación de objetos
                ventas_existentes = Venta.objects.filter(
                    empresa_id=self.empresa.id
                ).values_list('numero', flat=True)
                
                print(f"DEBUG SAVE: Ventas existentes encontradas: {list(ventas_existentes)}")
                
                # Extraer números numéricos válidos de diferentes formatos
                numeros_existentes = []
                for numero in ventas_existentes:
                    try:
                        if numero:
                            # Manejar diferentes formatos de números
                            if numero.startswith('V-'):
                                # Formato nuevo: V-000001
                                parte_numerica = numero.split('-')[1]
                                if parte_numerica.isdigit():
                                    numeros_existentes.append(int(parte_numerica))
                                    print(f"DEBUG SAVE: Número V- encontrado: {numero} -> {int(parte_numerica)}")
                            elif numero.isdigit():
                                # Formato legacy: 000001, 00000001, etc.
                                numeros_existentes.append(int(numero))
                                print(f"DEBUG SAVE: Número legacy encontrado: {numero} -> {int(numero)}")
                            else:
                                print(f"DEBUG SAVE: Formato no reconocido: {numero}")
                    except (ValueError, IndexError):
                        print(f"DEBUG SAVE: Número inválido ignorado: {numero}")
                        continue
                
                print(f"DEBUG SAVE: Lista de números existentes: {numeros_existentes}")
                
                # Encontrar el siguiente número disponible
                if numeros_existentes:
                    max_num = max(numeros_existentes)
                    siguiente_num = max_num + 1
                    print(f"DEBUG SAVE: Máximo número existente: {max_num}, siguiente será: {siguiente_num}")
                else:
                    siguiente_num = 1
                    print(f"DEBUG SAVE: No hay números existentes, empezando en: {siguiente_num}")
                
                # Generar el número
                self.numero = f"V-{str(siguiente_num).zfill(6)}"
                print(f"DEBUG SAVE: Número generado: {self.numero}")
                
                # Safety check - asegurar que no existe
                existe_check = Venta.objects.filter(empresa_id=self.empresa.id, numero=self.numero).exists()
                print(f"DEBUG SAVE: ¿Existe {self.numero}? {existe_check}")
                
                while Venta.objects.filter(empresa_id=self.empresa.id, numero=self.numero).exists():
                    print(f"DEBUG SAVE: {self.numero} ya existe, incrementando...")
                    siguiente_num += 1
                    self.numero = f"V-{str(siguiente_num).zfill(6)}"
                    print(f"DEBUG SAVE: Nuevo número generado: {self.numero}")
                
                print(f"DEBUG SAVE: Número final para venta: {self.numero}")

        if self.tipo_venta.startswith('credito_'):
            dias = int(self.tipo_venta.split('_')[1])
            if not self.fecha_vencimiento:
                self.fecha_vencimiento = self.fecha_emision + timezone.timedelta(days=dias)

        super().save(*args, **kwargs)

    def actualizar_totales(self):
        detalles = self.detalles.all()
        subtotal = sum(detalle.cantidad * detalle.precio_unitario for detalle in detalles)
        
        if self.igv_incluido:
            self.total = subtotal
            self.subtotal = round(subtotal / Decimal('1.18'), 2)
            self.igv = self.total - self.subtotal
        else:
            self.subtotal = subtotal
            self.igv = round(subtotal * Decimal('0.18'), 2)
            self.total = self.subtotal + self.igv
        
        self.save()

    def actualizar_stock(self):
        print(f"=== ACTUALIZANDO STOCK PARA VENTA {self.numero} ===")
        
        for detalle in self.detalles.all():
            print(f"Procesando producto: {detalle.producto.nombre}, cantidad: {detalle.cantidad}")
            
            # Buscar stock en el almacén del producto o el primer almacén disponible
            almacen = detalle.producto.almacen
            if not almacen:
                almacen = self.empresa.almacenes.first()
                print(f"Usando almacén por defecto: {almacen.nombre if almacen else 'NINGUNO'}")
            else:
                print(f"Usando almacén del producto: {almacen.nombre}")
            
            if almacen:
                stock, created = Stock.objects.get_or_create(
                    producto=detalle.producto,
                    almacen=almacen,
                    empresa=self.empresa,
                    defaults={'cantidad': 0}
                )
                
                stock_anterior = stock.cantidad
                print(f"Stock anterior: {stock_anterior}")
                
                # Reducir la cantidad del stock
                if stock.cantidad >= detalle.cantidad:
                    stock.cantidad -= detalle.cantidad
                    stock.save()
                    print(f"Stock actualizado: {stock_anterior} - {detalle.cantidad} = {stock.cantidad}")
                    
                    # Actualizar stock total del producto
                    detalle.producto.actualizar_stock_total()
                else:
                    # Si no hay suficiente stock, reducir a 0
                    print(f"STOCK INSUFICIENTE: disponible {stock.cantidad}, solicitado {detalle.cantidad}")
                    stock.cantidad = 0
                    stock.save()
                    detalle.producto.actualizar_stock_total()
            else:
                print(f"ERROR: No se encontró almacén para el producto {detalle.producto.nombre}")
        
        print(f"=== FIN ACTUALIZACIÓN STOCK VENTA {self.numero} ===")

    def marcar_como_pagada(self):
        if self.estado == 'pagado':
            return
            
        with transaction.atomic():
            self.estado = 'pagado'
            self.save()

    def anular_venta(self):
        if self.estado == 'pagado':
            for detalle in self.detalles.all():
                almacen = self.empresa.almacenes.first() if hasattr(self.empresa, 'almacenes') else None
                if almacen is None:
                    raise ValidationError('No se encontró un almacén para la empresa.')
                stock, created = Stock.objects.get_or_create(
                    producto=detalle.producto,
                    empresa=self.empresa,
                    almacen=almacen,
                    defaults={'cantidad': 0}
                )
                stock.cantidad += detalle.cantidad
                stock.save()
                detalle.producto.actualizar_stock_total()
        
        self.estado = 'anulado'
        self.save()

    def cancelar_venta(self):
        if self.estado == 'anulado':
            raise ValueError('La venta ya está anulada')
        
        self.estado = 'anulado'
        self.save()

    def actualizar_estado_pago(self):
        # Calcular el total pagado excluyendo los pagos pendientes
        total_pagado = self.pagos.exclude(metodo_pago='pendiente').aggregate(
            total=models.Sum('monto')
        )['total'] or Decimal('0')
        
        self.pagos_total = total_pagado
        
        if self.tipo_venta in ['credito_30', 'credito_60']:
            if total_pagado >= self.total:
                self.estado = 'pagado'
            else:
                self.estado = 'pendiente'
        else:
            if total_pagado >= self.total:
                self.estado = 'pagado'
            elif total_pagado > 0:
                self.estado = 'pendiente'
            else:
                self.estado = 'borrador'
        
        self.save()
        return self.estado

class DetalleVenta(models.Model):
    venta = models.ForeignKey(
        Venta, 
        on_delete=models.CASCADE, 
        related_name='detalles'
    )
    producto = models.ForeignKey('inventario.Producto', on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Detalle de venta'
        verbose_name_plural = 'Detalles de venta'

    def __str__(self):
        return f"{self.producto.nombre} - {self.cantidad} unidades"

    def clean(self):
        if self.cantidad <= 0:
            raise ValidationError('La cantidad debe ser mayor que cero')
        if self.precio_unitario <= 0:
            raise ValidationError('El precio unitario debe ser mayor que cero')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.venta_id:
            self.venta.actualizar_totales()

class Factura(models.Model):
    venta = models.OneToOneField(
        Venta, 
        on_delete=models.CASCADE, 
        related_name='factura'
    )
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='facturas')
    numero_factura = models.CharField(max_length=20)
    fecha = models.DateField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    igv = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.igv:
            self.igv = self.subtotal * Decimal('0.18')
        if not self.total:
            self.total = self.subtotal + self.igv
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        ordering = ['-fecha']
        unique_together = ('cliente', 'numero_factura')

    def __str__(self):
        return f"Factura {self.numero_factura} - {self.cliente.nombre}"

class OrdenVenta(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('completada', 'Completada'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='ordenes_venta')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='ordenes_venta')
    numero_orden = models.CharField(max_length=20)
    fecha_orden = models.DateField()
    fecha_entrega = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    igv = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    notas = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Orden de venta'
        verbose_name_plural = 'Órdenes de venta'
        ordering = ['-fecha_orden']
        unique_together = ('empresa', 'numero_orden')

    def __str__(self):
        return f"OV-{self.numero_orden} - {self.cliente.nombre}"

class PagoVenta(models.Model):
    METODO_PAGO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('tarjeta', 'Tarjeta'),
        ('cheque', 'Cheque')
    ]

    venta = models.ForeignKey(
        Venta, 
        on_delete=models.CASCADE, 
        related_name='pagos',
        verbose_name='Venta'
    )
    fecha = models.DateField(
        verbose_name='Fecha de Pago'
    )
    monto = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name='Monto',
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    metodo_pago = models.CharField(
        max_length=20, 
        choices=METODO_PAGO_CHOICES,
        verbose_name='Método de Pago'
    )
    referencia = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name='Referencia'
    )
    comprobante = models.FileField(
        upload_to='ventas/pagos/', 
        null=True, 
        blank=True,
        verbose_name='Comprobante'
    )
    notas = models.TextField(
        blank=True,
        verbose_name='Notas'
    )

    class Meta:
        verbose_name = 'Pago de Venta'
        verbose_name_plural = 'Pagos de Ventas'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f"Pago {self.id} - Venta {self.venta.numero}"

    def clean(self):
        if self.monto > self.venta.get_saldo_pendiente():
            raise ValidationError('El monto del pago excede el saldo pendiente de la venta')
        
        if self.fecha < self.venta.fecha_emision:
            raise ValidationError('La fecha del pago no puede ser anterior a la fecha de emisión de la venta')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        
        self.venta.actualizar_estado_pago()

@receiver(post_save, sender=PagoVenta)
def actualizar_estado_pago_venta(sender, instance, **kwargs):
    instance.venta.actualizar_estado_pago()

@receiver(post_delete, sender=PagoVenta)
def actualizar_estado_pago_venta_delete(sender, instance, **kwargs):
    instance.venta.actualizar_estado_pago() 