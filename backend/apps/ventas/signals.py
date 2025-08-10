from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Venta, DetalleVenta
from apps.inventario.models import Stock
from django.db import transaction
from django.core.exceptions import ValidationError

@receiver(post_save, sender=DetalleVenta)
def actualizar_stock_venta(sender, instance, created, **kwargs):
    """
    DESHABILITADO - El stock se actualiza desde la vista perform_create para evitar duplicación
    """
    pass

@receiver(post_save, sender=Venta)
def procesar_venta_pagada(sender, instance, created, **kwargs):
    """
    DESHABILITADO - El stock se actualiza desde la vista perform_create para evitar duplicación
    """
    pass

@receiver(pre_save, sender=Venta)
def validar_venta(sender, instance, **kwargs):
    """
    Realiza validaciones antes de guardar una venta
    """
    if not instance.pk:  # Si es una nueva venta
        # Establecer valores iniciales
        instance.subtotal = 0
        instance.igv = 0
        instance.total = 0
    
    # Validar que la venta tenga empresa asignada
    if not instance.empresa:
        raise ValidationError("La venta debe tener una empresa asignada") 