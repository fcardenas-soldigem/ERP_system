"""
Numeración de documentos POR EMPRESA, segura ante concurrencia.

Cada empresa (tenant) tiene su propia secuencia (0001, 0002, ...). La unicidad
se garantiza con un UniqueConstraint(empresa, numero) en cada modelo; esta
utilidad reintenta la generación ante una colisión concurrente (IntegrityError).
"""
from django.db import IntegrityError, transaction


def guardar_con_numero(instance, generar_numero, guardar, intentos=3):
    """
    Guarda `instance` asignando su `numero` por-empresa con reintento.

    - Si `instance.numero` ya está seteado (update), solo llama `guardar()`.
    - Si no, dentro de una transacción: `instance.numero = generar_numero()` y
      `guardar()`. Ante IntegrityError (dos requests tomaron el mismo número),
      limpia el número y reintenta hasta `intentos` veces.

    `generar_numero()` debe devolver el siguiente número para la empresa
    (idealmente usando select_for_update sobre el último registro de la empresa).
    `guardar()` ejecuta el `super().save(...)` del modelo.
    """
    if instance.numero:
        return guardar()
    ultimo_error = None
    for intento in range(intentos):
        try:
            with transaction.atomic():
                instance.numero = generar_numero()
                guardar()
            return
        except IntegrityError as exc:
            ultimo_error = exc
            instance.numero = None
    raise ultimo_error
