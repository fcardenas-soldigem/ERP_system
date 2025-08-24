from django.db import models, transaction
from django.db.models import F, Sum
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal
from apps.empresas.models import Empresa
from apps.inventario.models.almacen import Almacen
from apps.inventario.models.producto import Producto
from apps.inventario.models.stock import Stock
from django.core.exceptions import ValidationError
import os
from django.utils import timezone
from datetime import timedelta
from django.core.validators import MinValueValidator, MaxValueValidator

def comprobante_upload_to(instance, filename):
    # Generar la ruta para el comprobante
    return f'comprobantes/compras/{instance.compra.empresa.id}/{instance.compra.numero}/{filename}'

class Proveedor(models.Model):
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.CASCADE,
        related_name='proveedores',
        null=False,
        blank=False
    )
    razon_social = models.CharField(max_length=200)
    ruc = models.CharField(max_length=11)
    direccion = models.TextField(max_length=500, blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)  # Ampliado y opcional
    email = models.EmailField(max_length=100, blank=True, null=True)  # Nuevo campo opcional
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['-created_at']
        unique_together = ['empresa', 'ruc']

    def __str__(self):
        return f"{self.razon_social} - {self.ruc}"

    def clean(self):
        if not self.empresa_id:
            raise ValidationError("La empresa es requerida")
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class Compra(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('anulada', 'Anulada')
    ]

    TIPO_COMPRA_CHOICES = [
        ('contado', 'Contado'),
        ('credito_30', 'Crédito 30 días'),
        ('credito_60', 'Crédito 60 días')
    ]

    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('cheque', 'Cheque'),
        ('tarjeta', 'Tarjeta'),
        ('pendiente', 'Pendiente')
    ]
    
    MONEDA_CHOICES = [
        ('PEN', 'Sol Peruano (S/)'),
        ('USD', 'Dólar Americano ($)'),
    ]

    # Campos básicos
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.PROTECT,
        related_name='compras'
    )
    numero = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )
    proveedor = models.ForeignKey(
        'Proveedor',
        on_delete=models.PROTECT,
        related_name='compras'
    )
    almacen = models.ForeignKey(
        'inventario.Almacen',
        on_delete=models.PROTECT,
        related_name='compras'
    )

    # Fechas
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Estado y tipo
    tipo_compra = models.CharField(
        max_length=20,
        choices=TIPO_COMPRA_CHOICES,
        default='contado'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='borrador'
    )
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES,
        default='pendiente'
    )

    # Montos
    igv_incluido = models.BooleanField(default=True)
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    igv = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    moneda = models.CharField(
        max_length=3,
        choices=MONEDA_CHOICES,
        default='PEN',
        verbose_name='Moneda'
    )

    # Campos adicionales
    notas = models.TextField(blank=True, null=True)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    comprobante = models.FileField(
        upload_to='comprobantes/compras/',
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-fecha_emision']
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'

    def __str__(self):
        return f"Compra {self.numero} - {self.proveedor.razon_social}"

    def get_saldo_pendiente(self):
        """
        Calcula el saldo pendiente considerando conversiones de moneda
        """
        from apps.core.services.documento_service import DocumentoService
        
        # Obtener tipo de cambio
        try:
            doc_service = DocumentoService()
            tipo_cambio_data = doc_service.obtener_tipo_cambio_venta()
            tipo_cambio = float(tipo_cambio_data.get('venta', 3.8)) if tipo_cambio_data else 3.8
        except:
            tipo_cambio = 3.8
        
        # Calcular total pagado considerando conversiones
        total_pagado_convertido = Decimal('0')
        pagos_reales = self.pagos.exclude(metodo_pago='pendiente')
        
        for pago in pagos_reales:
            monto_pago = pago.monto
            
            # Convertir a la moneda de la compra si es necesario
            if hasattr(pago, 'moneda') and pago.moneda != self.moneda:
                if self.moneda == 'USD' and pago.moneda == 'PEN':
                    # Convertir PEN a USD
                    monto_pago = monto_pago / Decimal(str(tipo_cambio))
                elif self.moneda == 'PEN' and pago.moneda == 'USD':
                    # Convertir USD a PEN
                    monto_pago = monto_pago * Decimal(str(tipo_cambio))
            
            total_pagado_convertido += monto_pago
        
        # Asegurar que ambos operandos sean Decimal
        return (self.total or Decimal('0')) - total_pagado_convertido

    def clean(self):
        if not self.empresa_id:
            raise ValidationError('La compra debe tener una empresa asignada')
        if not self.proveedor_id:
            raise ValidationError('La compra debe tener un proveedor asignado')
        if not self.almacen_id:
            raise ValidationError('La compra debe tener un almacén asignado')
        
        # Validar que el proveedor pertenezca a la empresa
        if self.proveedor and self.empresa and self.proveedor.empresa != self.empresa:
            raise ValidationError('El proveedor no pertenece a la empresa')
        
        # Validar que el almacén pertenezca a la empresa
        if self.almacen and self.empresa and self.almacen.empresa != self.empresa:
            raise ValidationError('El almacén no pertenece a la empresa')
        
        super().clean()

    def save(self, *args, **kwargs):
        if not self.numero:
            print(f"DEBUG COMPRA SAVE: Generando número para empresa: {self.empresa} (ID: {self.empresa.id})")
            
            # Generar número de forma thread-safe
            from django.db import transaction
            with transaction.atomic():
                # Obtener todas las compras existentes para esta empresa y extraer los números
                compras_existentes = Compra.objects.filter(
                    empresa_id=self.empresa.id
                ).values_list('numero', flat=True)
                
                print(f"DEBUG COMPRA SAVE: Compras existentes encontradas: {list(compras_existentes)}")
                
                # Extraer números numéricos válidos de diferentes formatos
                numeros_existentes = []
                for numero in compras_existentes:
                    try:
                        if numero:
                            # Manejar diferentes formatos de números
                            if numero.startswith('C-'):
                                # Formato nuevo: C-000001
                                parte_numerica = numero.split('-')[1]
                                if parte_numerica.isdigit():
                                    numeros_existentes.append(int(parte_numerica))
                                    print(f"DEBUG COMPRA SAVE: Número C- encontrado: {numero} -> {int(parte_numerica)}")
                            elif numero.isdigit():
                                # Formato legacy: 000001, 00000001, etc.
                                numeros_existentes.append(int(numero))
                                print(f"DEBUG COMPRA SAVE: Número legacy encontrado: {numero} -> {int(numero)}")
                            else:
                                print(f"DEBUG COMPRA SAVE: Formato no reconocido: {numero}")
                    except (ValueError, IndexError):
                        print(f"DEBUG COMPRA SAVE: Número inválido ignorado: {numero}")
                        continue
                
                print(f"DEBUG COMPRA SAVE: Lista de números existentes: {numeros_existentes}")
                
                # Encontrar el siguiente número disponible
                if numeros_existentes:
                    max_num = max(numeros_existentes)
                    siguiente_num = max_num + 1
                    print(f"DEBUG COMPRA SAVE: Máximo número existente: {max_num}, siguiente será: {siguiente_num}")
                else:
                    siguiente_num = 1
                    print(f"DEBUG COMPRA SAVE: No hay números existentes, empezando en: {siguiente_num}")
                
                # Generar el número con formato C-000XXX
                self.numero = f"C-{str(siguiente_num).zfill(6)}"
                print(f"DEBUG COMPRA SAVE: Número generado: {self.numero}")
                
                # Safety check - asegurar que no existe
                existe_check = Compra.objects.filter(empresa_id=self.empresa.id, numero=self.numero).exists()
                print(f"DEBUG COMPRA SAVE: ¿Existe {self.numero}? {existe_check}")
                
                while Compra.objects.filter(empresa_id=self.empresa.id, numero=self.numero).exists():
                    print(f"DEBUG COMPRA SAVE: {self.numero} ya existe, incrementando...")
                    siguiente_num += 1
                    self.numero = f"C-{str(siguiente_num).zfill(6)}"
                    print(f"DEBUG COMPRA SAVE: Nuevo número generado: {self.numero}")
                
                print(f"DEBUG COMPRA SAVE: Número final para compra: {self.numero}")

        # Establecer fecha de vencimiento y lógica de estado/método de pago
        if self.tipo_compra in ['credito_30', 'credito_60']:
            # Para compras a crédito
            dias = 30 if self.tipo_compra == 'credito_30' else 60
            self.fecha_vencimiento = self.fecha_emision + timedelta(days=dias)
            
            # Verificar si hay pagos reales registrados
            pagos_reales_count = self.pagos.exclude(metodo_pago='pendiente').count() if self.id else 0
            
            if pagos_reales_count == 0:
                # Sin pagos reales: establecer como pendiente por defecto
                self.metodo_pago = 'pendiente'
                self.estado = 'pendiente'
            # Si hay pagos reales, el estado se actualizará via actualizar_estado_pago()
        else:
            # Para compras al contado
            self.fecha_vencimiento = self.fecha_emision
            
            # Verificar si hay pagos reales registrados
            pagos_reales_count = self.pagos.exclude(metodo_pago='pendiente').count() if self.id else 0
            
            if pagos_reales_count == 0:
                # Sin pagos reales: establecer como efectivo/pagada por defecto (contado)
                if not self.metodo_pago or self.metodo_pago == 'pendiente':
                    self.metodo_pago = 'efectivo'
                    self.estado = 'pagada'
            # Si hay pagos reales, el estado se actualizará via actualizar_estado_pago()

        super().save(*args, **kwargs)

    def actualizar_totales(self):
        detalles = self.detalles.all()
        subtotal_bruto = sum(detalle.cantidad * detalle.precio_unitario for detalle in detalles)
        
        if self.igv_incluido:
            self.subtotal = subtotal_bruto / Decimal('1.18')
            self.igv = subtotal_bruto - self.subtotal
            self.total = subtotal_bruto
        else:
            self.subtotal = subtotal_bruto
            self.igv = self.subtotal * Decimal('0.18')
            self.total = self.subtotal + self.igv
        
        self.save()

    def actualizar_stock(self):
        print(f"=== ACTUALIZANDO STOCK PARA COMPRA {self.numero} ===")
        
        for detalle in self.detalles.all():
            print(f"Procesando producto: {detalle.producto.nombre}, cantidad: {detalle.cantidad}")
            print(f"Almacén: {self.almacen.nombre}")
            
            stock, created = Stock.objects.get_or_create(
                producto=detalle.producto,
                almacen=self.almacen,
                empresa=self.empresa,
                defaults={'cantidad': 0}
            )
            
            stock_anterior = stock.cantidad
            print(f"Stock anterior: {stock_anterior}")
            
            stock.cantidad += detalle.cantidad
            stock.save()
            
            print(f"Stock actualizado: {stock_anterior} + {detalle.cantidad} = {stock.cantidad}")
            
            detalle.producto.actualizar_stock_total()
        
        print(f"=== FIN ACTUALIZACIÓN STOCK COMPRA {self.numero} ===")

    def marcar_como_pagada(self):
        if self.estado == 'pagada':
            return
            
        with transaction.atomic():
            self.estado = 'pagada'
            self.save()
            self.actualizar_stock()

    def anular_compra(self):
        if self.estado == 'pagada':
            # Revertir el stock
            for detalle in self.detalles.all():
                stock = Stock.objects.get(
                    producto=detalle.producto,
                    almacen=self.almacen,
                    empresa=self.empresa
                )
                stock.cantidad -= detalle.cantidad
                stock.save()
                detalle.producto.actualizar_stock_total()
        
        self.estado = 'anulada'
        self.save()

    def actualizar_estado_pago(self):
        """
        Actualiza el estado de la compra basado en los pagos realizados con conversión de moneda
        """
        from apps.core.services.documento_service import DocumentoService
        
        # Obtener tipo de cambio
        try:
            doc_service = DocumentoService()
            tipo_cambio_data = doc_service.obtener_tipo_cambio_venta()
            tipo_cambio = float(tipo_cambio_data.get('venta', 3.8)) if tipo_cambio_data else 3.8
        except:
            tipo_cambio = 3.8
        
        # Calcular total pagado considerando conversiones
        total_pagado_convertido = Decimal('0')
        pagos_reales = self.pagos.exclude(metodo_pago='pendiente')
        
        for pago in pagos_reales:
            monto_pago = pago.monto
            
            # Convertir a la moneda de la compra si es necesario
            if hasattr(pago, 'moneda') and pago.moneda != self.moneda:
                if self.moneda == 'USD' and pago.moneda == 'PEN':
                    # Convertir PEN a USD
                    monto_pago = monto_pago / Decimal(str(tipo_cambio))
                elif self.moneda == 'PEN' and pago.moneda == 'USD':
                    # Convertir USD a PEN
                    monto_pago = monto_pago * Decimal(str(tipo_cambio))
            
            total_pagado_convertido += monto_pago
        
        # Actualizar estado y método de pago
        if total_pagado_convertido >= self.total:
            self.estado = 'pagada'
            # Establecer método de pago basado en los pagos registrados
            if pagos_reales.count() == 1:
                # Si hay un solo pago, usar su método
                self.metodo_pago = pagos_reales.first().metodo_pago
            else:
                # Si hay múltiples pagos, usar el más reciente
                self.metodo_pago = pagos_reales.order_by('-fecha', '-id').first().metodo_pago
        elif total_pagado_convertido > 0:
            self.estado = 'pendiente'
            # Mantener método de pago como pendiente si aún no está completamente pagado
            if self.metodo_pago == 'pendiente':
                self.metodo_pago = 'pendiente'
        else:
            self.estado = 'borrador'
            if self.metodo_pago not in ['efectivo', 'transferencia', 'cheque', 'tarjeta']:
                self.metodo_pago = 'pendiente'
        
        self.save()

class CompraDetalle(models.Model):
    compra = models.ForeignKey(
        'Compra',
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    producto = models.ForeignKey(
        'inventario.Producto',
        on_delete=models.PROTECT,
        related_name='detalles_compra'
    )
    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    igv = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    notas = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Detalle de Compra'
        verbose_name_plural = 'Detalles de Compra'
        ordering = ['id']

    def __str__(self):
        return f'{self.producto.nombre} - {self.cantidad}'

    def save(self, *args, **kwargs):
        # Calcular subtotal
        self.subtotal = self.cantidad * self.precio_unitario
        
        # Calcular IGV y total según configuración de la compra
        if self.compra.igv_incluido:
            self.total = self.subtotal
            self.igv = self.total - (self.total / Decimal('1.18'))
        else:
            self.igv = self.subtotal * Decimal('0.18')
            self.total = self.subtotal + self.igv
        
        super().save(*args, **kwargs)
        
        # Actualizar totales de la compra
        if not kwargs.get('skip_compra_update', False):
            self.compra.actualizar_totales()

class PagoCompra(models.Model):
    compra = models.ForeignKey(
        'Compra',
        on_delete=models.CASCADE,
        related_name='pagos'
    )
    fecha = models.DateField(default=timezone.now)
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    moneda = models.CharField(
        max_length=3,
        choices=Compra.MONEDA_CHOICES,
        default='PEN',
        verbose_name='Moneda del pago'
    )
    metodo_pago = models.CharField(
        max_length=20,
        choices=Compra.METODO_PAGO_CHOICES,
        default='efectivo'
    )
    referencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Número de operación, cheque, etc.'
    )
    comprobante = models.FileField(
        upload_to='comprobantes/pagos/',
        blank=True,
        null=True
    )
    notas = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Pago de Compra'
        verbose_name_plural = 'Pagos de Compras'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f'Pago {self.id} - Compra {self.compra.numero}'

    def clean(self):
        if not self.compra_id:
            return
            
        # Validar que el monto no exceda el saldo pendiente
        saldo_pendiente = self.compra.get_saldo_pendiente()
        if self.monto > saldo_pendiente:
            raise ValidationError({
                'monto': f'El monto del pago (${self.monto}) excede el saldo pendiente (${saldo_pendiente})'
            })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        
        # Actualizar estado de pago con conversión de moneda
        self.compra.actualizar_estado_pago()

class ComprobantePago(models.Model):
    compra = models.OneToOneField(
        'Compra',
        on_delete=models.CASCADE,
        related_name='comprobante_pago'
    )
    archivo = models.FileField(
        upload_to=comprobante_upload_to,
        verbose_name='Archivo'
    )
    fecha_subida = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(
        max_length=50,
        choices=[
            ('factura', 'Factura'),
            ('boleta', 'Boleta'),
            ('ticket', 'Ticket'),
            ('otro', 'Otro')
        ]
    )
    numero = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Comprobante de Pago'
        verbose_name_plural = 'Comprobantes de Pago'

    def __str__(self):
        return f'Comprobante {self.tipo} - Compra {self.compra.numero}'

    def delete(self, *args, **kwargs):
        # Eliminar el archivo físico
        if self.archivo:
            if os.path.isfile(self.archivo.path):
                os.remove(self.archivo.path)
        super().delete(*args, **kwargs)

class OrdenCompra(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('enviada', 'Enviada'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('completada', 'Completada')
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.PROTECT,
        related_name='ordenes_compra'
    )
    numero = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )
    proveedor_nombre = models.CharField(max_length=200, blank=True, null=True)
    fecha_entrega = models.DateField()
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='borrador'
    )

    # Montos
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    igv = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # Campos adicionales
    notas = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Orden de Compra'
        verbose_name_plural = 'Órdenes de Compra'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"OC-{self.numero} - {self.proveedor_nombre}"

    def clean(self):
        if not self.empresa_id:
            raise ValidationError('La orden debe tener una empresa asignada')

    def save(self, *args, **kwargs):
        if not self.numero:
            ultimo_numero = OrdenCompra.objects.filter(empresa=self.empresa).order_by('-numero').first()
            if ultimo_numero and ultimo_numero.numero:
                try:
                    num = int(ultimo_numero.numero) + 1
                    self.numero = str(num).zfill(6)
                except ValueError:
                    self.numero = '000001'
            else:
                self.numero = '000001'
        super().save(*args, **kwargs)

    def actualizar_totales(self):
        # Funcionalidad temporalmente deshabilitada
        pass

    def convertir_a_compra(self):
        if self.estado != 'aprobada':
            raise ValidationError('Solo se pueden convertir a compra las órdenes aprobadas')

        # Por ahora deshabilitamos esta funcionalidad hasta arreglar la estructura
        raise ValidationError('Funcionalidad temporalmente deshabilitada')

# class OrdenCompraDetalle(models.Model):
#     # Temporalmente comentado porque la tabla no existe
#     pass

class RecepcionCompra(models.Model):
    orden = models.ForeignKey(
        OrdenCompra,
        on_delete=models.CASCADE,
        related_name='recepciones'
    )
    fecha_recepcion = models.DateTimeField(auto_now_add=True)
    recibido_por = models.CharField(max_length=100)
    notas = models.TextField(blank=True, null=True)
    comprobante = models.FileField(
        upload_to='comprobantes/recepciones/',
        null=True,
        blank=True
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Recepción de Compra'
        verbose_name_plural = 'Recepciones de Compra'
        ordering = ['-fecha_recepcion']

    def __str__(self):
        return f"Recepción {self.id} - OC {self.orden.numero}"

    def clean(self):
        if self.orden.estado not in ['enviada', 'aprobada']:
            raise ValidationError('Solo se pueden recibir órdenes enviadas o aprobadas')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        if self.orden.estado == 'enviada':
            self.orden.estado = 'aprobada'
            self.orden.save()

class CompraRecurrente(models.Model):
    FRECUENCIA_CHOICES = [
        ('mensual', 'Mensual'),
        ('trimestral', 'Trimestral'),
        ('semestral', 'Semestral'),
        ('anual', 'Anual')
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.PROTECT,
        related_name='compras_recurrentes'
    )
    proveedor_nombre = models.CharField(max_length=200, blank=True, null=True)
    concepto = models.CharField(max_length=200)
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    frecuencia = models.CharField(
        max_length=20,
        choices=FRECUENCIA_CHOICES,
        default='mensual'
    )
    proximo_pago = models.DateField()
    activo = models.BooleanField(default=True)
    notas = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Compra Recurrente'
        verbose_name_plural = 'Compras Recurrentes'
        ordering = ['proximo_pago']
        unique_together = ['empresa', 'proveedor_nombre', 'concepto']

    def __str__(self):
        return f"{self.concepto} - {self.proveedor_nombre} ({self.get_frecuencia_display()})"

    def clean(self):
        if not self.empresa_id:
            raise ValidationError('La compra recurrente debe tener una empresa asignada')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
