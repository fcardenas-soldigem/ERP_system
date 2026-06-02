import logging
from django.db.models.signals import pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

_estado_anterior_cache = {}


@receiver(pre_save, sender='servicios.OrdenServicio')
def capturar_estado_anterior(sender, instance, **kwargs):
    if instance.pk:
        try:
            anterior = sender.objects.get(pk=instance.pk)
            _estado_anterior_cache[instance.pk] = anterior.estado
        except sender.DoesNotExist:
            _estado_anterior_cache[instance.pk] = None
    else:
        _estado_anterior_cache[None] = None


from django.db.models.signals import post_save


@receiver(post_save, sender='servicios.OrdenServicio')
def registrar_cambio_estado(sender, instance, created, **kwargs):
    from apps.servicios.models import HistorialEstadoOS

    if created:
        HistorialEstadoOS.objects.create(
            orden=instance,
            estado_anterior='',
            estado_nuevo=instance.estado,
            usuario=instance.creado_por,
            notas='Orden creada',
        )
        return

    pk = instance.pk
    estado_anterior = _estado_anterior_cache.pop(pk, None)
    if estado_anterior is not None and estado_anterior != instance.estado:
        HistorialEstadoOS.objects.create(
            orden=instance,
            estado_anterior=estado_anterior,
            estado_nuevo=instance.estado,
            usuario=instance.creado_por,
        )
