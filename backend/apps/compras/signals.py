from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Compra, CompraDetalle
from apps.inventario.models import Stock
from django.db import transaction

@receiver(post_save, sender=CompraDetalle)
def actualizar_totales_compra(sender, instance, created, **kwargs):
    """
    Actualiza los totales de la compra cuando se modifica un detalle
    """
    if not hasattr(instance, '_actualizando_totales'):
        instance.compra.actualizar_totales()

@receiver(post_save, sender=Compra)
def actualizar_stock_compra(sender, instance, created, **kwargs):
    """
    DESHABILITADO - El stock se actualiza desde la vista create para evitar duplicación
    """
    pass 