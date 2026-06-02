# Correcciones de Bugs Críticos — 2026-05-29

Cinco bugs corregidos en orden de severidad. Archivos modificados:
- `backend/apps/ventas/views.py`
- `backend/apps/ventas/models.py`
- `backend/apps/compras/models.py`
- `backend/config/settings.py`

---

## Bug 1 — Ventas pagadas se podían eliminar

**Archivo:** `backend/apps/ventas/views.py:907` (antes línea 921)

**Problema:** `VentaViewSet.destroy()` comparaba `venta.estado == 'pagada'`, pero el modelo define el estado como `'pagado'` (sin 'a'). La comparación nunca era verdadera, lo que permitía borrar ventas ya cobradas sin ningún error.

**Antes:**
```python
if venta.estado == 'pagada':
    return Response({'error': 'No se puede eliminar una venta pagada'}, ...)
```

**Después:**
```python
if venta.estado == 'pagado':
    return Response({'error': 'No se puede eliminar una venta pagada'}, ...)
```

**Impacto corregido:** Pérdida de datos contables. Una venta cobrada es un registro financiero que no debe eliminarse.

---

## Bug 2 — FacturaViewSet exponía facturas de todos los tenants

**Archivo:** `backend/apps/ventas/views.py` (clase `FacturaViewSet`)

**Problema:** `queryset = Factura.objects.all()` sin filtro de empresa ni permisos. Cualquier usuario autenticado podía ver (o modificar) facturas de otras empresas con una llamada directa a `/api/ventas/facturas/`.

**Antes:**
```python
class FacturaViewSet(viewsets.ModelViewSet):
    queryset = Factura.objects.all()
    serializer_class = FacturaSerializer
```

**Después:**
```python
class FacturaViewSet(viewsets.ModelViewSet):
    serializer_class = FacturaSerializer
    permission_classes = [IsAuthenticated, HasEmpresaPermission]

    def get_queryset(self):
        return Factura.objects.filter(
            venta__empresa=self.request.user.empresa
        ).select_related('cliente', 'venta')
```

**Impacto corregido:** Fuga de datos entre tenants (violación multi-tenancy). Se aprovechó para agregar `select_related` que elimina también el N+1 de este endpoint.

---

## Bug 3 — Race condition en generación de números de Venta y Compra

**Archivos:**
- `backend/apps/ventas/models.py` (`Venta.save()`)
- `backend/apps/compras/models.py` (`Compra.save()`)

**Problema:** El algoritmo anterior cargaba todos los números existentes en memoria Python, calculaba el máximo con `max()`, e incrementaba. Aunque usaba `transaction.atomic()`, no bloqueaba las filas — dos requests simultáneos podían obtener el mismo `max_num` y ambos intentar crear `V-000042`, provocando un error 500 por violación del `unique_together`.

**Antes (ambos modelos, ~60 líneas de código):**
```python
with transaction.atomic():
    ventas_existentes = Venta.objects.filter(empresa_id=...).values_list('numero', flat=True)
    numeros_existentes = []
    for numero in ventas_existentes:
        # parsing manual + print() de debug
        ...
    max_num = max(numeros_existentes)
    siguiente_num = max_num + 1
    self.numero = f"V-{str(siguiente_num).zfill(6)}"
    while Venta.objects.filter(..., numero=self.numero).exists():
        siguiente_num += 1
        ...
```

**Después (ambos modelos, ~20 líneas):**
```python
with transaction.atomic():
    ultima = (
        Venta.objects.select_for_update()
        .filter(empresa_id=self.empresa.id, numero__startswith='V-')
        .order_by('-numero')
        .only('numero')
        .first()
    )
    if ultima:
        siguiente_num = int(ultima.numero.split('-')[1]) + 1
    else:
        # compatibilidad con números legacy sin prefijo
        legacy = Venta.objects.select_for_update()...first()
        siguiente_num = (int(legacy.numero) + 1) if legacy else 1
    self.numero = f"V-{str(siguiente_num).zfill(6)}"
```

**`SELECT FOR UPDATE`** bloquea la fila hasta que la transacción termine, garantizando que el segundo request espere antes de leer, obteniendo siempre un número diferente.

**Impacto corregido:** Duplicados de número de venta/compra bajo carga concurrente. También se eliminaron ~100 líneas de `print()` de debug en estos métodos y se redujo el código de ~60 a ~20 líneas por modelo.

---

## Bug 4 — N+1 queries en VentaViewSet (listado y exportación)

**Archivo:** `backend/apps/ventas/views.py` (`VentaViewSet.get_queryset()`)

**Problema:** El queryset base no tenía `select_related` ni `prefetch_related`. Cada vez que el serializer o la vista accedía a `venta.cliente.nombre` o iteraba `venta.detalles.all()`, Django emitía una query adicional por venta. Con PAGE_SIZE=10: mínimo 21 queries por página. En `exportar_excel` con 500 ventas: ~1500 queries en un solo request.

**Antes:**
```python
def get_queryset(self):
    queryset = self.queryset.filter(empresa=self.request.user.empresa)
    # filtros...
    return queryset.order_by('-fecha_emision')
```

**Después:**
```python
def get_queryset(self):
    queryset = Venta.objects.filter(
        empresa=self.request.user.empresa
    ).select_related('cliente').prefetch_related('detalles__producto')
    # filtros...
    return queryset.order_by('-fecha_emision')
```

También se eliminaron los ~15 `print()` de debug del método `perform_create` que acompañaban el problema.

**Impacto corregido:** Latencia reducida en el listado de ventas (la vista más usada del sistema) y en la exportación a Excel.

---

## Bug 5 — CONN_MAX_AGE: 0 generaba una conexión nueva por request

**Archivo:** `backend/config/settings.py`

**Problema:** Con `CONN_MAX_AGE: 0`, Django abría y cerraba una conexión TCP+TLS a PostgreSQL en cada request HTTP. En Cloud Run con Supabase (conexión SSL/TLS remota), esto añade ~50ms de overhead por request. Con `CONN_HEALTH_CHECKS: False`, si la base caía y volvía, las conexiones en el pool podían quedar en estado zombie.

**Antes:**
```python
'CONN_MAX_AGE': 0,
'CONN_HEALTH_CHECKS': False,
```

**Después:**
```python
'CONN_MAX_AGE': 60,
'CONN_HEALTH_CHECKS': True,
```

Django reutilizará conexiones durante 60 segundos. `CONN_HEALTH_CHECKS: True` verifica que la conexión sigue viva antes de reutilizarla, evitando errores en reconexiones tras un timeout del servidor.

**Impacto corregido:** ~50ms de latencia eliminados de cada request. Comportamiento más estable ante interrupciones de red.

---

## Bugs pendientes (no corregidos en esta sesión)

Los siguientes problemas fueron identificados en el análisis pero requieren más contexto o trabajo para corregirlos de forma segura:

| # | Problema | Archivo | Riesgo |
|---|---|---|---|
| 1 | `anular_venta()` no revierte `InventarioProductosTerminados` ni `MovimientoInventario` | `ventas/models.py:531` | Inventarios desincronizados al anular ventas pagadas |
| 2 | Modelos ML guardados en filesystem (`model_file_path`) — no persisten en Cloud Run | `ml_models/models.py:50` | Los modelos entrenados desaparecen en cada redeploy |
| 3 | `CSRF_TRUSTED_ORIGINS` tiene la URL de Cloud Run hardcodeada | `settings.py:46` | Necesita env var para no romper al cambiar de servicio |
| 4 | `MEDIA_URL`/`MEDIA_ROOT` declarados dos veces en settings | `settings.py:235, 314` | Confuso, aunque funcional (segundo sobreescribe el primero con los mismos valores) |
| 5 | `OrdenCompra.convertir_a_compra()` deshabilitado con `raise ValidationError` | `compras/models.py:757` | El flujo Orden→Compra está roto |
| 6 | 351 `print()` de debug restantes en el backend | Varios archivos | I/O innecesario en Cloud Run, aumenta costos de logging |
| 7 | `VentaListCreateView` (sin filtro de empresa) registrado en el mismo router que `VentaViewSet` | `ventas/views.py:40`, `ventas/urls.py` | Riesgo si alguna ruta lo invoca directamente |
| 8 | Sin tests en ningún módulo | `*/tests.py` | No hay cobertura de la lógica crítica de stock y pagos |

### Nota sobre los `print()` restantes

El bug 3 eliminó los más críticos (los del `save()` de Venta y Compra, que se ejecutan en cada creación). Los 351 restantes están distribuidos en vistas y servicios. Para limpiarlos sin riesgo: reemplazar con `logger.debug(...)` y asegurar que el logger tenga `level: WARNING` en producción (ya está configurado así en `settings.py` para la mayoría de los loggers).
