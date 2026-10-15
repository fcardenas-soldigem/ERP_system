"""Campos DRF reutilizables para archivos.

`SafeFileURLField` es un FileField cuya REPRESENTACIÓN (lectura) nunca lanza: la URL
se resuelve con `field_url_safe`, así una firma de GCS fallida (SA sin llave privada)
devuelve None en vez de tumbar el endpoint. La escritura (subida) es la de FileField.
"""
from rest_framework import serializers

from apps.core.uploads import field_url_safe


class SafeFileURLField(serializers.FileField):
    """FileField con lectura tolerante: devuelve la URL vía `field_url_safe` (None si
    el archivo falta o el storage no puede firmar), absolutizada si hay `request`."""

    def to_representation(self, value):
        url = field_url_safe(value)
        if not url:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url
