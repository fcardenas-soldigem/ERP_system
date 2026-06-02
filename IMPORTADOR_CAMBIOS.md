# Módulo de Importación Excel — Registro de Cambios

> Rama: `commit` · Fecha: 2026-05-30

---

## Resumen ejecutivo

Se investigó y corrigió el módulo de importación Excel (`backend/apps/importador/`). El importador fallaba silenciosamente en compras y tenía lógica incorrecta en proveedores, productos, ventas y el wizard del frontend. Los cambios cubren 3 archivos: 1 backend y 2 frontend.

---

## 1. `backend/apps/importador/services.py`

### BUG CRÍTICO — Compras no se importaban (causa raíz)

**Método:** `_create_compra`

**Problema:** El método guardaba la `Compra` en base de datos y luego lanzaba `raise ValueError` si el precio era 0 o no estaba mapeado. Esto ocurría **antes** de crear el `CompraDetalle`. En modo parcial (default), la transacción atómica hacía rollback — ninguna compra quedaba en DB. El fallback a `producto.precio_compra` era código muerto e inalcanzable porque el `raise` siempre lo precedía.

```python
# ANTES — lógica rota
compra.save()                             # Guarda la compra

if not precio_compra or precio <= 0:
    raise ValueError("Precio no detectado...")  # ← Lanza AQUÍ antes del detalle

if not precio_compra or precio <= 0:      # ← CÓDIGO MUERTO: nunca se ejecuta
    precio_compra = producto.precio_compra

detalle = CompraDetalle(...)
detalle.save()
# actualizar_stock() nunca llamado
```

```python
# DESPUÉS — lógica correcta
# 1. Precio resuelto ANTES de tocar la base de datos
if not precio_compra or precio_compra <= 0:
    precio_compra = (
        producto.precio_compra
        if producto.precio_compra and producto.precio_compra > 0
        else Decimal('0.01')
    )
    logger.info("Usando precio del producto: %s", precio_compra)

compra.save()
detalle.save()                            # Detalle siempre se crea
self.stats['compras_creadas'] += 1

# 2. Stock actualizado correctamente
compra.refresh_from_db()
if compra.estado == 'pagada':
    compra.actualizar_stock()             # Actualiza Stock + InventarioMateriasPrimas
```

---

### BUG — `moneda` no se pasaba al constructor de `Compra`

**Método:** `_create_compra`

El parámetro `moneda` llegaba a la función pero nunca se asignaba al objeto `Compra`. Todas las compras quedaban con la moneda por defecto del modelo (`'PEN'`), ignorando el valor del Excel.

```python
# ANTES
def _create_compra(..., *, moneda='USD'):   # default incorrecto además
    compra = Compra(
        empresa=...,
        proveedor=...,
        # moneda ← AUSENTE
    )

# DESPUÉS
def _create_compra(..., *, moneda='PEN'):   # default correcto para ERP peruano
    compra = Compra(
        ...
        moneda=moneda,                      # ← campo asignado
    )
```

---

### BUG — `_resolve_moneda()` devolvía `'USD'` como default

Lógica invertida: si no había columna de moneda en el Excel, retornaba `'USD'`. Para un ERP peruano, el default es `'PEN'`.

```python
# ANTES — default incorrecto
def _resolve_moneda(self, row, ftoc) -> str:
    val = self._get_val(row, ftoc.get('moneda'))
    if val:
        v = str(val).strip().upper()
        if v in ('PEN', 'SOL', 'SOLES', 'S/', 'S./', 'NS/'):
            return 'PEN'
    return 'USD'   # ← Devuelve USD si no hay columna

# DESPUÉS — default correcto
def _resolve_moneda(self, row, ftoc) -> str:
    val = self._get_val(row, ftoc.get('moneda'))
    if val:
        v = str(val).strip().upper()
        if v in ('USD', 'DOLLAR', 'DOLLARS', '$'):
            return 'USD'
    return 'PEN'   # ← Default PEN
```

---

### BUG — `_create_venta` tenía `moneda='USD'` como default

Mismo problema que `_create_compra`: el default era `'USD'` en vez de `'PEN'`.

```python
# ANTES
def _create_venta(..., notas='', *, moneda='USD'):

# DESPUÉS
def _create_venta(..., notas='', *, moneda='PEN'):
```

---

### NUEVO — `_format_cell` helper para preview

Nuevo helper que limpia valores de celdas Excel para la vista previa. Convierte floats enteros (ej. `20390342048.0`) a string limpio (`"20390342048"`), y maneja `NaT`/`NaN` como `None`.

```python
def _format_cell(val) -> str | None:
    if isinstance(val, float) and val == int(val):
        return str(int(val))   # "20390342048.0" → "20390342048"
    ...
```

Ahora el preview en el wizard muestra RUC y DNI correctamente sin el `.0` de Excel.

---

### NUEVO — `_get_or_create_cliente` — clientes desde columna Excel

Antes, las ventas fallaban con `"Sin cliente disponible"` si no se configuraba un cliente por defecto en el wizard. Ahora el importador puede crear clientes directamente desde la columna `cliente` del Excel.

```python
def _get_or_create_cliente(self, nombre: str) -> 'Cliente':
    # Busca por nombre exacto primero
    existing = Cliente.objects.filter(empresa=..., nombre__iexact=nombre).first()
    if existing:
        return existing
    # Crea con DNI sintético de 8 dígitos si no existe
    syn_doc = ('9' + hashlib.md5(f"{empresa_id}:{nombre}".encode()).hexdigest()[:7])[:8]
    cliente, _ = Cliente.objects.get_or_create(...)
    return cliente
```

**Flujo actualizado en `_import_venta_row`:**
```
1. Intenta defaults.cliente_id (configurado en wizard)
2. Si no hay → busca/crea desde columna 'cliente' del Excel
3. Si tampoco → ValueError claro con instrucciones
```

---

### NUEVO — `_get_or_create_proveedor` — fix RUC float

Excel almacena RUC como float: `20390342048.0`. El importador fallaba la validación de 11 dígitos porque el string tenía `.0`.

```python
ruc_clean = str(ruc).strip().replace(' ', '').replace('-', '')
# NUEVO: convierte "20390342048.0" → "20390342048"
if '.' in ruc_clean:
    try:
        ruc_clean = str(int(float(ruc_clean)))
    except (ValueError, OverflowError):
        pass
```

---

### NUEVO — `_get_or_create_producto` — pricing por tipo

El importador creaba productos con `precio_venta=0` para todos los tipos. El serializer de producción rechaza eso en edición posterior.

```python
# Ahora respeta las reglas del ProductoSerializer:
if tipo_producto == 'FINISHED' and (not precio_venta or precio_venta <= 0):
    precio_venta = precio_compra if precio_compra > 0 else Decimal('0.01')
elif tipo_producto in ('RAW', 'SEMIFINISHED'):
    precio_venta = Decimal('0')   # Forzado igual que el serializer
```

---

### MEJORADO — `_build_warnings` — advertencias por entidad

Antes generaba las mismas advertencias para todos los tipos de hoja. Ahora cada tipo muestra solo las advertencias relevantes a su entidad.

| Tipo hoja | Advertencias anteriores | Advertencias nuevas |
|---|---|---|
| `proveedores` | Sin fecha, sin proveedor | Sin columna de nombre de proveedor |
| `productos` | Sin fecha, sin precio compra y venta | Sin nombre de producto; sin precio compra; sin precio venta |
| `compras` | Sin fecha (general) | Sin producto; sin fecha; sin proveedor (usa genérico); sin precio compra |
| `ventas` | Sin precio venta (general) | Sin producto; sin fecha; sin precio venta |
| `standard` | Igual que antes | Igual (comportamiento sin cambios) |

---

## 2. `frontend/src/components/Importador/HojaPreview.jsx`

### CAMBIO — `StatusBadge` — lógica por tipo de entidad

Antes el badge solo chequeaba si había una columna `producto_nombre` mapeada. Ahora verifica los campos obligatorios reales de cada entidad.

| Tipo | Badge verde requiere |
|---|---|
| `proveedores` | Columna de nombre mapeada |
| `productos` | Columna de nombre mapeada |
| `compras` | Nombre de producto + `almacen_id` default + fecha (columna o default) |
| `ventas` | Nombre de producto + cliente (columna o default) + fecha (columna o default) |
| `standard` | Nombre de producto + `almacen_id` default + cliente (columna o default) |

---

### CAMBIO — "Datos faltantes" — campos relevantes por entidad

Antes mostraba los mismos 4 inputs (fecha, cliente, almacén, categoría) para todos los tipos de hoja.

| Tipo hoja | ANTES mostraba | AHORA muestra |
|---|---|---|
| `proveedores` | Fecha + Cliente + Almacén + Categoría | **Nada** (no necesita defaults) |
| `productos` | Fecha + Cliente + Almacén + Categoría | Almacén + Categoría |
| `compras` | Fecha + Cliente + Almacén + Categoría | **Almacén** (req) + Fecha (si no hay columna) |
| `ventas` | Fecha + Cliente + Almacén + Categoría | **Cliente** (req) + Fecha (si no hay columna) |
| `standard` | Igual | Almacén (req) + Cliente (req, si no hay col) + Fecha + Categoría |

Los campos marcados como requeridos (`*`) muestran borde rojo si no están completados, para guiar al usuario antes de importar.

---

## 3. `frontend/src/pages/Importador/ImportadorWizard.jsx`

### CAMBIO — Hojas `proyectos` ignoradas

Las hojas de tipo `proyectos` no tienen modelo en el ERP y causaban confusión. Ahora se filtran silenciosamente del wizard.

```javascript
// ANTES: mostraba todas las hojas
preview.hojas.map(hoja => <HojaPreview .../>)

// DESPUÉS: omite proyectos
const hojasVisibles = preview.hojas.filter(h => h.tipo_hoja !== 'proyectos');
hojasVisibles.map(hoja => <HojaPreview .../>)
```

---

### CAMBIO — Botón "Confirmar importación" — validación real

Antes se habilitaba con cualquier hoja seleccionada. Ahora verifica que todas las hojas activas tengan sus campos obligatorios cubiertos.

```javascript
// ANTES
isDisabled={hojasIncluidas.length === 0}

// DESPUÉS
isDisabled={!isReadyToImport}

// isReadyToImport verifica por tipo:
// compras → producto + almacen_id + (fecha en col o default)
// ventas  → producto + (cliente en col o default) + fecha
// etc.
```

El botón muestra un `title` explicativo cuando está deshabilitado: _"Completa los campos requeridos en todas las hojas activas"_.

---

## Flujo de importación corregido (orden garantizado)

```
1. Proveedores  → get_or_create por RUC (real o sintético)
2. Productos    → get_or_create por nombre+marca; precios corregidos por tipo
3. Compras      → precio resuelto ANTES de guardar → Compra → CompraDetalle → actualizar_stock()
4. Ventas       → cliente desde columna Excel si no hay default → Venta → DetalleVenta → actualizar_stock()
```

En formato `referenced` (hojas separadas), el orden siempre es el indicado arriba independientemente del orden de las hojas en el Excel.

---

## Archivos modificados

| Archivo | Tipo de cambio |
|---|---|
| `backend/apps/importador/services.py` | Bug fixes + nuevos métodos |
| `frontend/src/components/Importador/HojaPreview.jsx` | Lógica por entidad reescrita |
| `frontend/src/pages/Importador/ImportadorWizard.jsx` | Filtro proyectos + validación botón |
| `IMPORTADOR_CAMPOS.md` | Documento de referencia de campos por entidad (generado por investigación) |
