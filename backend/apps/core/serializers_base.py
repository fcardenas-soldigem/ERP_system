"""
Patrón único de aislamiento multi-empresa para serializers (auditoría §6).

- `EmpresaScopedPrimaryKeyRelatedField`: un PrimaryKeyRelatedField cuyo queryset se
  filtra por la empresa del usuario autenticado, SOLO si el modelo destino tiene campo
  `empresa`. Un id de otra empresa → `does_not_exist` → 400 automático (evita referencias
  cruzadas: cliente, proveedor, producto, almacén, venta, OC, cotización, categoría…).
- `EmpresaScopedModelSerializer`: ModelSerializer base que (1) usa ese field para TODAS
  las FK autogeneradas y (2) fuerza `empresa` a read_only. Heredar de esta base acota
  automáticamente cualquier FK escribible sin declarar validadores uno por uno.
"""
from rest_framework import serializers


def _model_tiene_empresa(model):
    try:
        return any(f.name == 'empresa' for f in model._meta.fields)
    except Exception:
        return False


class EmpresaScopedPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        qs = super().get_queryset()
        if qs is None:
            return qs
        request = self.context.get('request', None)
        empresa_id = getattr(getattr(request, 'user', None), 'empresa_id', None)
        if empresa_id and _model_tiene_empresa(qs.model):
            return qs.filter(empresa_id=empresa_id)
        return qs


class EmpresaScopedModelSerializer(serializers.ModelSerializer):
    # Todas las FK autogeneradas usan el field acotado por empresa.
    serializer_related_field = EmpresaScopedPrimaryKeyRelatedField

    def get_fields(self):
        fields = super().get_fields()
        # 'empresa' NUNCA la fija el cliente: se inyecta en perform_create.
        if 'empresa' in fields:
            fields['empresa'].read_only = True
        return fields
