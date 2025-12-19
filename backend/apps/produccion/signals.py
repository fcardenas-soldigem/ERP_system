from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from .models import OrdenProduccion, ConsumoReal
from apps.inventario.models import MovimientoInventario


@receiver(post_save, sender=OrdenProduccion)
def orden_produccion_post_save(sender, instance, created, **kwargs):
    """
    Signal para manejar eventos después de guardar una orden de producción.
    """
    # Crear registros de MovimientoInventario cuando la orden se finaliza
    if instance.estado == 'finalizada' and instance.fecha_fin:
        # Este signal se activa después de que el servicio finalizar_orden
        # ya haya actualizado los stocks, aquí solo registramos para auditoría
        pass  # La lógica principal está en el servicio


@receiver(post_save, sender=ConsumoReal)
def consumo_real_post_save(sender, instance, created, **kwargs):
    """
    Signal para actualizar información relacionada cuando se registra un consumo.
    """
    # Aquí podríamos agregar lógica adicional si es necesario
    pass
