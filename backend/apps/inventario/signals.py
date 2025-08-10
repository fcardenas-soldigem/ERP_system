from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from .models import Stock, Producto, Almacen, MovimientoInventario
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal

from apps.compras.models import CompraDetalle
from apps.ventas.models import DetalleVenta

@receiver(post_save, sender=Stock)
def actualizar_stock_producto(sender, instance, **kwargs):
    """
    Actualiza el stock total del producto cuando cambia el stock en un almacén
    """
    instance.producto.actualizar_stock_total()

@receiver(pre_save, sender=Producto)
def validar_stock_minimo(sender, instance, **kwargs):
    """
    Verifica si el producto está por debajo del stock mínimo
    """
    if not hasattr(instance, 'stock_total'):
        instance.stock_total = 0
    
    if not hasattr(instance, 'stock_minimo'):
        instance.stock_minimo = 0
        
    if instance.stock_total <= instance.stock_minimo:
        instance.alerta_stock = True
    else:
        instance.alerta_stock = False

@receiver(post_save, sender=Almacen)
def crear_stock_inicial(sender, instance, created, **kwargs):
    """
    Crea registros de Stock en cero para todos los productos cuando se crea un nuevo almacén
    """
    if created:
        try:
            with transaction.atomic():
                productos = Producto.objects.filter(activo=True)
                stock_objects = [
                    Stock(
                        almacen=instance,
                        producto=producto,
                        cantidad=0
                    ) for producto in productos
                ]
                Stock.objects.bulk_create(stock_objects)
        except Exception as e:
            print(f"Error creando stock inicial: {str(e)}")

@receiver(post_save, sender=CompraDetalle)
def registrar_entrada_compra(sender, instance, created, **kwargs):
    """
    Registra entrada de inventario cuando se crea un detalle de compra
    """
    # DESHABILITADO TEMPORALMENTE - Los signals de compras manejan el stock directamente
    pass
    # if created and hasattr(instance, 'compra') and instance.compra.estado == 'pagada':
    #     try:
    #         # Obtener el primer almacén del producto o el almacén por defecto
    #         almacen = instance.producto.almacen
    #         if not almacen:
    #             # Si no tiene almacén asignado, usar el primer almacén de la empresa
    #             almacen = Almacen.objects.filter(empresa=instance.compra.empresa).first()
    #         
    #         if almacen:
    #             MovimientoInventario.registrar_entrada(
    #                 empresa=instance.compra.empresa,
    #                 producto=instance.producto,
    #                 almacen=almacen,
    #                 cantidad=instance.cantidad,
    #                 costo_unitario=instance.precio_unitario,
    #                 tipo_documento='compra',
    #                 numero_documento=f"COMPRA-{instance.compra.numero}",
    #                 fecha=instance.compra.fecha_emision or timezone.now(),
    #                 observaciones=f"Compra #{instance.compra.numero} - {instance.compra.proveedor.razon_social}",
    #                 documento_id=instance.compra.id,
    #                 usuario=getattr(instance.compra, 'created_by', '')
    #             )
    #     except Exception as e:
    #         # Log del error pero no interrumpir el flujo
    #         print(f"Error al registrar entrada en kardex: {e}")

@receiver(post_save, sender=DetalleVenta)
def registrar_salida_venta(sender, instance, created, **kwargs):
    """
    Registra salida de inventario cuando se crea un detalle de venta
    """
    # DESHABILITADO TEMPORALMENTE - Los signals de ventas manejan el stock directamente
    pass
    # if created and hasattr(instance, 'venta') and instance.venta.estado == 'pagado':
    #     try:
    #         # Obtener el primer almacén del producto o el almacén por defecto
    #         almacen = instance.producto.almacen
    #         if not almacen:
    #             # Si no tiene almacén asignado, usar el primer almacén de la empresa
    #             almacen = Almacen.objects.filter(empresa=instance.venta.empresa).first()
    #         
    #         if almacen:
    #             MovimientoInventario.registrar_salida(
    #                 empresa=instance.venta.empresa,
    #                 producto=instance.producto,
    #                 almacen=almacen,
    #                 cantidad=instance.cantidad,
    #                 tipo_documento='venta',
    #                 numero_documento=f"VENTA-{instance.venta.numero}",
    #                 fecha=instance.venta.fecha_emision or timezone.now(),
    #                 observaciones=f"Venta #{instance.venta.numero} - {instance.venta.cliente.nombre if instance.venta.cliente else 'Cliente General'}",
    #                 documento_id=instance.venta.id,
    #                 usuario=getattr(instance.venta, 'created_by', '')
    #             )
    #     except Exception as e:
    #         # Log del error pero no interrumpir el flujo
    #         print(f"Error al registrar salida en kardex: {e}")

@receiver(post_delete, sender=CompraDetalle)
def revertir_entrada_compra(sender, instance, **kwargs):
    """
    Revierte la entrada de inventario cuando se elimina un detalle de compra
    """
    try:
        # Buscar el movimiento relacionado y crear un movimiento de reversión
        almacen = instance.producto.almacen
        if not almacen:
            almacen = Almacen.objects.filter(empresa=instance.compra.empresa).first()
        
        if almacen:
            MovimientoInventario.registrar_salida(
                empresa=instance.compra.empresa,
                producto=instance.producto,
                almacen=almacen,
                cantidad=instance.cantidad,
                tipo_documento='devolucion_compra',
                numero_documento=f"DEV-COMPRA-{instance.compra.numero}",
                fecha=timezone.now(),
                observaciones=f"Reversión compra #{instance.compra.numero}",
                documento_id=instance.compra.id,
                usuario=''
            )
    except Exception as e:
        print(f"Error al revertir entrada en kardex: {e}")

@receiver(post_delete, sender=DetalleVenta)
def revertir_salida_venta(sender, instance, **kwargs):
    """
    Revierte la salida de inventario cuando se elimina un detalle de venta
    """
    try:
        # Buscar el movimiento relacionado y crear un movimiento de reversión
        almacen = instance.producto.almacen
        if not almacen:
            almacen = Almacen.objects.filter(empresa=instance.venta.empresa).first()
        
        if almacen:
            # Para la reversión de venta, necesitamos estimar un costo unitario
            # Usar el costo promedio actual del producto
            stock_info = MovimientoInventario.obtener_stock_actual(
                instance.venta.empresa, instance.producto, almacen
            )
            costo_unitario = stock_info.get('costo_promedio', instance.producto.precio_compra)
            
            MovimientoInventario.registrar_entrada(
                empresa=instance.venta.empresa,
                producto=instance.producto,
                almacen=almacen,
                cantidad=instance.cantidad,
                costo_unitario=costo_unitario,
                tipo_documento='devolucion_venta',
                numero_documento=f"DEV-VENTA-{instance.venta.numero}",
                fecha=timezone.now(),
                observaciones=f"Reversión venta #{instance.venta.numero}",
                documento_id=instance.venta.id,
                usuario=''
            )
    except Exception as e:
        print(f"Error al revertir salida en kardex: {e}")

# Función para migrar datos existentes al kardex
def migrar_datos_kardex():
    """
    Función utilitaria para migrar datos existentes de compras y ventas al kardex
    """
    from apps.compras.models import CompraDetalle
    from apps.ventas.models import DetalleVenta
    
    print("Iniciando migración de datos al kardex...")
    
    # Migrar compras
    compras_detalle = CompraDetalle.objects.filter(
        compra__estado='pagada'
    ).select_related('compra', 'producto').order_by('compra__fecha_emision', 'compra__id')
    
    for detalle in compras_detalle:
        try:
            almacen = detalle.producto.almacen
            if not almacen:
                almacen = Almacen.objects.filter(empresa=detalle.compra.empresa).first()
            
            if almacen:
                # Verificar si ya existe el movimiento
                existe = MovimientoInventario.objects.filter(
                    empresa=detalle.compra.empresa,
                    producto=detalle.producto,
                    compra_id=detalle.compra.id,
                    tipo_documento='compra'
                ).exists()
                
                if not existe:
                    MovimientoInventario.registrar_entrada(
                        empresa=detalle.compra.empresa,
                        producto=detalle.producto,
                        almacen=almacen,
                        cantidad=detalle.cantidad,
                        costo_unitario=detalle.precio_unitario,
                        tipo_documento='compra',
                        numero_documento=f"COMPRA-{detalle.compra.numero}",
                        fecha=detalle.compra.fecha_emision or timezone.now(),
                        observaciones=f"Migración - Compra #{detalle.compra.numero}",
                        documento_id=detalle.compra.id,
                        usuario='sistema'
                    )
                    print(f"Migrada compra {detalle.compra.numero} - {detalle.producto.sku}")
        except Exception as e:
            print(f"Error migrando compra {detalle.compra.numero}: {e}")
    
    # Migrar ventas
    ventas_detalle = DetalleVenta.objects.filter(
        venta__estado='pagado'
    ).select_related('venta', 'producto').order_by('venta__fecha_emision', 'venta__id')
    
    for detalle in ventas_detalle:
        try:
            almacen = detalle.producto.almacen
            if not almacen:
                almacen = Almacen.objects.filter(empresa=detalle.venta.empresa).first()
            
            if almacen:
                # Verificar si ya existe el movimiento
                existe = MovimientoInventario.objects.filter(
                    empresa=detalle.venta.empresa,
                    producto=detalle.producto,
                    venta_id=detalle.venta.id,
                    tipo_documento='venta'
                ).exists()
                
                if not existe:
                    MovimientoInventario.registrar_salida(
                        empresa=detalle.venta.empresa,
                        producto=detalle.producto,
                        almacen=almacen,
                        cantidad=detalle.cantidad,
                        tipo_documento='venta',
                        numero_documento=f"VENTA-{detalle.venta.numero}",
                        fecha=detalle.venta.fecha_emision or timezone.now(),
                        observaciones=f"Migración - Venta #{detalle.venta.numero}",
                        documento_id=detalle.venta.id,
                        usuario='sistema'
                    )
                    print(f"Migrada venta {detalle.venta.numero} - {detalle.producto.sku}")
        except Exception as e:
            print(f"Error migrando venta {detalle.venta.numero}: {e}")
    
    print("Migración completada.") 