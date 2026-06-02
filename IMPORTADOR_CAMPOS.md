# REPORTE DE CAMPOS OBLIGATORIOS POR ENTIDAD

> Generado por investigación sistemática del código fuente — 2026-05-30  
> Archivos analizados: `backend/apps/compras/models.py`, `serializers.py`, `views.py`,
> `backend/apps/inventario/models/producto.py`, `serializers.py`,
> `backend/apps/ventas/models.py`, `serializers.py`, `views.py`,
> `frontend/src/components/Proveedores/ProveedorForm.jsx`,
> `frontend/src/components/Inventario/ProductoForm.jsx`,
> `frontend/src/components/Compras/CompraForm.jsx`,
> `frontend/src/components/Ventas/NuevaVenta.jsx`,
> `backend/apps/importador/services.py`

---

## PROVEEDOR

**Fuente:** `backend/apps/compras/models.py` (L23-56) · `backend/apps/compras/serializers.py` (L37-55)

### Campos obligatorios
| Campo | Tipo | Restricción |
|---|---|---|
| `razon_social` | CharField(200) | No puede ser vacío |
| `ruc` | CharField(11) | Exactamente 11 dígitos. Unique per empresa |

### Campos opcionales
| Campo | Tipo | Default / Nota |
|---|---|---|
| `direccion` | TextField(500) | null=True, blank=True |
| `telefono` | CharField(15) | null=True, blank=True; si se ingresa, mín 7 caracteres |
| `email` | EmailField(100) | null=True, blank=True; formato email |
| `activo` | BooleanField | default=True |

### Campos autogenerados
| Campo | Cómo se genera |
|---|---|
| `empresa` | Inyectado desde `request.user.empresa` (NO está en el serializer) |
| `id` | PK autoincremental |
| `created_at` | `auto_now_add=True` |
| `updated_at` | `auto_now=True` |

### Constraint clave
`unique_together = ['empresa', 'ruc']` → No puede existir dos proveedores con el mismo RUC dentro de la misma empresa.

---

## PRODUCTO

**Fuente:** `backend/apps/inventario/models/producto.py` (L7-190) · `backend/apps/inventario/serializers.py` (L48-282)

### Campos obligatorios (todos los tipos)
| Campo | Tipo | Restricción |
|---|---|---|
| `sku` | CharField(50) | Unique per empresa. El importador lo autogenera desde el nombre si no se proporciona |
| `nombre` | CharField(200) | No puede ser vacío |
| `tipo_producto` | CharField choices | RAW / SEMIFINISHED / FINISHED — default='RAW' |

### Campos obligatorios condicionales (dependen de `tipo_producto`)
| Condición | Campo | Regla |
|---|---|---|
| tipo = RAW o SEMIFINISHED | `precio_compra` | > 0 obligatorio (error si es 0 o null) |
| tipo = RAW o SEMIFINISHED | `precio_venta` | FORZADO a 0 por el serializer, no enviar |
| tipo = FINISHED | `precio_venta` | > 0 obligatorio (error si es 0 o null) |
| tipo = FINISHED | `precio_venta` | >= `precio_compra` |

### Campos opcionales
| Campo | Tipo | Default |
|---|---|---|
| `descripcion` | TextField | blank=True |
| `categoria` | FK(Categoria) | null=True (SET_NULL) — pero el formulario lo pone como required |
| `almacen` | FK(Almacen) | null=True (SET_NULL) — pero el formulario lo pone como required |
| `stock_minimo` | Decimal | default=0 |
| `stock_maximo` | Decimal | default=0 |
| `unidad_medida` | CharField choices | default='unidad' |
| `marca` | CharField(100) | blank=True, default='' |
| `moneda` | CharField(3) | default='PEN' |
| `is_active` | BooleanField | default=True |

### Campos autogenerados
| Campo | Cómo se genera |
|---|---|
| `empresa` | Inyectado desde `request.user.empresa` |
| `stock_total` | Calculado dinámicamente desde tabla `Stock` |
| `alerta_stock` | `stock_total <= stock_minimo` |
| `margen` | `(precio_venta - precio_compra) / precio_venta * 100` |
| `id`, `created_at`, `updated_at` | Auto |

### FK requeridas (deben existir en la empresa antes de crear el producto)
- `categoria` → Tabla `inventario_categoria` — se crea automáticamente en el importador si no existe
- `almacen` → Tabla `inventario_almacen` — **debe existir**; si no hay almacen el importador usa el primero activo de la empresa

### Validación de stock mínimo/máximo
`stock_minimo <= stock_maximo` (validado en `clean()`, serializer y formulario)

### Comportamiento al crear con almacen
Si `almacen` está asignado al crear el producto, se crea automáticamente un registro en `Stock` con la cantidad inicial. Si `tipo_producto` es RAW/SEMIFINISHED, también se crea en `InventarioMateriasPrimas`. Si es FINISHED, en `InventarioProductosTerminados`.

---

## COMPRA (cabecera + detalle)

**Fuente:** `backend/apps/compras/models.py` (L58-514) · `backend/apps/compras/serializers.py` (L76-206)

### Cabecera (Compra) — campos obligatorios
| Campo | Tipo | Restricción |
|---|---|---|
| `proveedor` | FK(Proveedor) | Debe pertenecer a la misma empresa |
| `almacen` | FK(Almacen) | Debe pertenecer a la misma empresa |
| `fecha_emision` | DateField | Fecha de la factura |

### Cabecera — campos opcionales
| Campo | Tipo | Default | Nota |
|---|---|---|---|
| `tipo_compra` | CharField choices | 'contado' | contado / credito_30 / credito_60 |
| `estado` | CharField choices | 'borrador' | borrador / pendiente / pagada / anulada |
| `metodo_pago` | CharField choices | 'pendiente' | efectivo / transferencia / cheque / tarjeta / pendiente |
| `igv_incluido` | BooleanField | True | Si los precios de detalle incluyen IGV |
| `moneda` | CharField(3) | 'PEN' | PEN / USD |
| `notas` | TextField | null | |
| `referencia` | CharField(100) | null | Número de operación, cheque, etc. |
| `comprobante` | FileField | null | Archivo PDF/imagen |
| `fecha_vencimiento` | DateField | auto-calculado | Auto: +30 o +60 días según tipo_compra |

### Cabecera — campos autogenerados
| Campo | Cómo se genera |
|---|---|
| `numero` | Auto: formato `C-000001` (SELECT FOR UPDATE para evitar race condition) |
| `empresa` | Inyectado desde `request.user.empresa` |
| `subtotal` | Recalculado desde suma de detalles |
| `igv` | Calculado: subtotal × 0.18 (o extraído si igv_incluido) |
| `total` | subtotal + igv |

### Detalle (CompraDetalle) — campos obligatorios
| Campo | Tipo | Restricción |
|---|---|---|
| `producto` | FK(Producto) | Debe existir en la empresa |
| `cantidad` | Decimal | > 0 (MinValueValidator 0.01) |
| `precio_unitario` | Decimal | > 0 (MinValueValidator 0.01) |

### Detalle — campos autogenerados
| Campo | Cómo se genera |
|---|---|
| `compra` | Asignado automáticamente en `create()` |
| `subtotal` | `cantidad × precio_unitario` |
| `igv` | Según `compra.igv_incluido` |
| `total` | Según `compra.igv_incluido` |

### FK requeridas
- `proveedor` → debe existir en `compras_proveedor` para la empresa
- `almacen` → debe existir en `inventario_almacen` para la empresa
- `producto` → debe existir en `inventario_producto` para la empresa

### Lógica de stock (cuándo se actualiza el inventario)
```
Al crear compra por serializer:
  → si estado in ['pagada', 'pendiente']: llama compra.actualizar_stock()
  → si estado = 'borrador': NO actualiza stock

compra.actualizar_stock() hace:
  1. Stock.objects.get_or_create(producto, almacen, empresa)
  2. stock.cantidad += detalle.cantidad
  3. producto.actualizar_stock_total()
  4. Si producto.tipo_producto in ['RAW','SEMIFINISHED']:
       → también crea registro en InventarioMateriasPrimas
       → crea MovimientoInventario tipo='entrada_compra'

Al marcar_como_pagada() desde borrador/pendiente:
  → también llama actualizar_stock()

Regla: stock solo sube cuando la compra está pagada o pendiente.
Borrador NO mueve inventario.
```

---

## VENTA (cabecera + detalle)

**Fuente:** `backend/apps/ventas/models.py` (L78-667) · `backend/apps/ventas/serializers.py` (L88-413)

### Cabecera (Venta) — campos obligatorios
| Campo | Tipo | Restricción |
|---|---|---|
| `cliente` | FK(Cliente) | Debe pertenecer a la empresa. Se pasa como `cliente_id` en el request |
| `fecha_emision` | DateField | Fecha de la venta |
| `tipo_venta` | CharField choices | contado / credito_30 / credito_60 — validado en serializer |
| `metodo_pago` | CharField choices | efectivo / transferencia / cheque / tarjeta — **no puede ser null ni 'pendiente' al crear** |

### Cabecera — campos opcionales
| Campo | Tipo | Default |
|---|---|---|
| `igv_incluido` | BooleanField | False (el serializer acepta string 'true'/'1'/'si') |
| `moneda` | CharField(3) | 'PEN' |
| `modo_venta` | CharField choices | 'stock' — stock / pedido |
| `notas` | TextField | blank |
| `referencia` | CharField(100) | blank |
| `comprobante` | FileField | null |
| `fecha_vencimiento` | DateField | auto-calculado para crédito |

### Cabecera — campos autogenerados
| Campo | Cómo se genera |
|---|---|
| `numero` | Auto: formato `V-000001` (SELECT FOR UPDATE) |
| `empresa` | Inyectado desde `request.user.empresa` |
| `subtotal`, `igv`, `total` | Calculados desde detalles |
| `pagos_total` | Suma de pagos registrados |

### Detalle (DetalleVenta) — campos obligatorios
| Campo | Tipo | Restricción |
|---|---|---|
| `producto` | FK(Producto) | **Solo FINISHED** — RAW/SEMIFINISHED rechazados con error explícito |
| `cantidad` | Decimal | > 0 |
| `precio_unitario` | Decimal | > 0 |

**REGLA CRÍTICA:** Los productos de tipo RAW o SEMIFINISHED NO pueden venderse directamente. Solo los de tipo FINISHED. El serializer lanza error: `"es una materia prima/insumo y no puede venderse directamente"`.

### FK requeridas
- `cliente` → debe existir en `ventas_cliente` para la empresa (también acepta creación on-the-fly por RUC/DNI desde el frontend)
- `producto` → debe existir, ser FINISHED, y pertenecer a la empresa
- Al menos un detalle con producto válido

### Lógica de stock (cuándo y cómo se actualiza)
```
Al crear venta por serializer (create()):
  → llama venta.actualizar_stock() inmediatamente

venta.actualizar_stock() según modo_venta:

MODO 'stock' (default):
  1. Stock.get_or_create(producto, almacen, empresa)
  2. stock.cantidad -= cantidad (si stock < cantidad, queda en 0 con warning)
  3. Si producto.tipo_producto == 'FINISHED':
       → InventarioProductosTerminados.procesar_venta(...)
  4. Crea MovimientoInventario tipo='salida_venta'
  5. producto.actualizar_stock_total()

MODO 'pedido' (para ventas a pedido sin stock PT):
  1. Busca RecetaProducto activa para el producto
  2. Por cada ingrediente de la receta:
       → InventarioMateriasPrimas.consumir_en_produccion(...)
       → Crea MovimientoInventario tipo='salida_venta' para la MP
  3. Crea MovimientoInventario virtual para el PT
  4. Si no hay receta: cae en modo 'stock' como fallback

Stock negativo: no lanza error, simplemente queda en 0 con log warning.
```

---

## MAPEO EXCEL → SISTEMA

El importador (`backend/apps/importador/services.py`) soporta dos formatos:

- **standard**: cada fila = 1 compra + 1 venta (para archivos de gestión histórica con todo junto)
- **referenced**: hojas separadas (PROVEEDORES, PRODUCTOS, COMPRAS, VENTAS) con IDs cruzados

### Tabla de mapeo: columna Excel → campo del sistema

| Campo del sistema | Aliases detectados automáticamente | Entidades |
|---|---|---|
| `producto_nombre` | producto, productos, descripcion, item, articulo, nombre producto, nombre, detalle | Todas |
| `id_producto` | id producto, id_producto, cod producto, codigo producto | Compras, Ventas, referenciado |
| `cantidad` | cantidad, cant, qty, unidades, cant vendida | Compras, Ventas |
| `proveedor_nombre` | proveedor, proveedores, razon social, nombre proveedor, empresa | Compras |
| `proveedor_ruc` | ruc, ruc proveedor, ruc del proveedor, ruc/dni, numero ruc, n ruc | Compras, Proveedores |
| `id_proveedor` | id proveedor, id_proveedor, cod proveedor, codigo proveedor | Compras, referenciado |
| `cliente_nombre` | cliente, clientes, nombre cliente, comprador | Ventas |
| `precio_compra` | precio de compra, precio compra, pc, p compra, costo unitario, valor compra | Compras |
| `precio_final_compra` | precio final - c, pf, total compra, importe compra | Compras |
| `precio_venta` | precio de venta, precio venta, pv, p venta, precio unitario | Ventas |
| `precio_final_venta` | precio final - v, pfv, total venta, importe venta, precio final | Ventas |
| `fecha_compra` | fecha de compra, fecha compra, fecha, fecha de ingreso, fecha factura | Compras |
| `fecha_entrega` | fecha de entrega, fecha entrega, fecha de venta, fecha despacho | Ventas |
| `estado` | estado, estado pago, condicion, situacion | Compras, Ventas |
| `marca` | marca, brand, fabricante | Productos |
| `categoria_nombre` | categoria, rubro | Productos |
| `direccion` | direccion | Proveedores |
| `telefono` | telefono | Proveedores |
| `email` | email, correo | Proveedores |

### Qué pasa si falta cada campo obligatorio

#### Para PROVEEDOR (hoja tipo "proveedores" en modo referenced)
| Campo faltante | Consecuencia |
|---|---|
| `nombre` / `proveedor_nombre` | Fila ignorada completamente (no crea proveedor) |
| `ruc` | Se genera un **RUC sintético** (`'9' + MD5(empresa_id:nombre)[:10]`) para garantizar unicidad. El proveedor se crea igualmente. |

#### Para PRODUCTO (hoja tipo "productos" en modo referenced)
| Campo faltante | Consecuencia |
|---|---|
| `producto_nombre` | Fila ignorada |
| `sku` | Se autogenera desde los primeros 12 chars del nombre (mayúsculas, espacios→guión). Si colisiona, agrega contador. |
| `precio_compra` | Queda en 0 — puede causar error en serializer si tipo=RAW/SEMIFINISHED al editar después |
| `precio_venta` | Queda en 0 — puede causar error en serializer si tipo=FINISHED al editar después |
| `categoria` | Usa la primera categoría de la empresa. Si no hay ninguna, `categoria=null` |
| `almacen` | Usa el primer almacén activo de la empresa. **Si no existe ningún almacén activo: el producto se crea sin almacén, pero NO se genera Stock ni inventario separado** |

#### Para COMPRA (hoja tipo "compras" o formato standard)
| Campo faltante | Consecuencia |
|---|---|
| `producto_nombre` / `id_producto` | Fila ignorada |
| `proveedor_nombre` / `id_proveedor` | En modo standard: usa "Proveedor Genérico" con RUC sintético. En modo compras-referenciado: usa "Proveedor Genérico" |
| `almacen` | **Error fatal**: `ValueError: "Sin almacén disponible"`. La fila falla y se registra en `errores_json` (modo parcial) o detiene toda la importación (modo completo) |
| `fecha_compra` | Se usa `date.today()` como fallback |
| `precio_compra` | Queda en 0.01 (mínimo para que CompraDetalle pase la validación MinValueValidator) |
| `cantidad` | Default 1 |
| `estado` | Mapeado: pagada/paid/completado → 'pagada'; parcial → 'parcial'; resto → 'pendiente'. Si pagada: stock se actualiza |

#### Para VENTA (hoja tipo "ventas" o formato standard)
| Campo faltante | Consecuencia |
|---|---|
| `producto_nombre` / `id_producto` | Fila ignorada |
| `cliente` (via defaults.cliente_id) | **Error fatal**: `ValueError: "Sin cliente disponible"`. La fila falla. El importador NO crea clientes automáticamente desde la columna `cliente_nombre` en hoja de ventas — **el cliente_id debe configurarse como default en el wizard** |
| `fecha_entrega` | **Error fatal** en hoja de ventas referenciada. En modo standard: usa fecha_compra como fallback |
| `precio_venta` | Queda en 0.01 (mínimo) |
| `cantidad` | Default 1 |
| `almacen` | El importador intenta usarlo para descontar stock, pero si es null no descuenta (no lanza error) |

---

## ISSUES CRÍTICOS DETECTADOS EN EL IMPORTADOR ACTUAL

1. **Cliente no se puede crear desde Excel**: El campo `cliente_nombre` existe en los aliases pero el `_import_venta_row` solo lee `defaults.get('cliente_id')`. Si el usuario no configura un cliente por defecto en el wizard (paso 2), TODAS las ventas fallan con `"Sin cliente disponible"`.

2. **Precio 0 para materias primas**: El importador crea productos con `precio_venta=0`. Si después se intenta editar ese producto tipo RAW/SEMIFINISHED desde el formulario normal, el serializer lanzará error porque `precio_compra` es 0 también (si no se proporcionó). Los productos creados con precios 0 quedan en estado inconsistente con las validaciones del serializer de producción.

3. **RUC sintético**: Los proveedores creados sin RUC real reciben un RUC generado por MD5. Si luego el usuario intenta crear manualmente ese mismo proveedor con el RUC real, puede causar duplicados (el RUC real pasa la validación, pero la razón social ya existe).

4. **Stock para compras en modo importación**: El importador usa `_stock_entrada` directamente (bypass del serializer), sin crear registros en `InventarioMateriasPrimas` para productos RAW/SEMIFINISHED. El `Compra.actualizar_stock()` (que sí lo hace) NO es llamado por el importador — solo el helper `_stock_entrada` que solo actualiza la tabla `Stock` genérica.

5. **Orden de importación en formato referenced**: Proveedores y Productos deben estar ANTES de Compras y Ventas. Si el Excel tiene las hojas en orden incorrecto, los lookups `_prov_lookup`/`_prod_lookup` estarán vacíos y se crearán entidades nuevas en lugar de reutilizar las existentes.

6. **metodo_pago en ventas**: El serializer de Venta rechaza `metodo_pago=null` o `metodo_pago='pendiente'` con error. El importador hace `Venta.objects.filter(pk=venta.pk).update(estado='pagado', metodo_pago='efectivo')` con UPDATE directo (bypass del serializer), evitando la validación. Esto funciona hoy, pero si el importador pasa por el serializer directamente fallaría.
