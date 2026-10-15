"""
Numeración de documentos POR EMPRESA, segura ante concurrencia.

Cada empresa (tenant) tiene su propia secuencia (0001, 0002, ...). La unicidad
se garantiza con un UniqueConstraint(empresa, numero) en cada modelo.

Serialización: dentro de la transacción se toma un lock de fila sobre la
EMPRESA (select_for_update) ANTES de calcular el número. Así toda la numeración
del tenant se serializa, incluida la PRIMERA creación (cuando aún no hay
documentos y "lockear el último registro" no bloquea nada). Esto cierra dos
carreras del patrón "lock del último documento" bajo concurrencia real:
  - tabla vacía: N hilos leen "sin último" y todos calculan 1;
  - recheck de Postgres (EvalPlanQual): dos hilos lockean la MISMA fila máx y
    calculan el mismo siguiente.
El reintento ante IntegrityError queda como red de seguridad.
"""
from django.db import IntegrityError, transaction


def _lock_tenant(instance):
    """Lock de fila del tenant para serializar su numeración (no-op si no hay empresa)."""
    empresa_id = getattr(instance, 'empresa_id', None)
    if empresa_id is None:
        return
    from apps.empresas.models import Empresa
    # Materializa la consulta para que el lock se tome aquí (dentro del atomic).
    list(Empresa.objects.select_for_update().filter(pk=empresa_id).values_list('pk', flat=True))


def guardar_con_numero(instance, generar_numero, guardar, intentos=3):
    """
    Guarda `instance` asignando su `numero` por-empresa, serializado por tenant.

    - Si `instance.numero` ya está seteado (update), solo llama `guardar()`.
    - Si no, dentro de una transacción: lock de la empresa, `instance.numero =
      generar_numero()` y `guardar()`. Ante IntegrityError (colisión residual),
      limpia el número y reintenta hasta `intentos` veces.

    `generar_numero()` devuelve el siguiente número para la empresa.
    `guardar()` ejecuta el `super().save(...)` del modelo.
    """
    if instance.numero:
        return guardar()
    ultimo_error = None
    for intento in range(intentos):
        try:
            with transaction.atomic():
                _lock_tenant(instance)
                instance.numero = generar_numero()
                guardar()
            return
        except IntegrityError as exc:
            ultimo_error = exc
            instance.numero = None
    raise ultimo_error
