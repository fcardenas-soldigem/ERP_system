# FASE 1 — Especificación técnica

> Modelo de negocio: **back-to-back** (Soldigem). No hay stock: cada compra existe porque hay una venta aprobada.
> Pero el ERP es **SaaS multi-empresa**: debe servir por igual a empresas **con stock** y **sin stock**, sin código duplicado (D6).
> Objetivo de la fase: que el registro ocurra como **consecuencia del flujo**, con mínimos clics.
> Filtro aplicado (CLAUDE.md): simplicidad → velocidad → claridad → menos fricción.

**Alcance:** F1 costo/proveedor por línea · F2 conversión 1 clic (1 OC por proveedor) · F3 timeline operativo de venta · F4 cierre de cotizaciones no ganadas · **D6 modelo dual con/sin inventario** (transversal).

**Secuencia de implementación:** **F1 → F2 → F3 → F4** (D6 se construye junto a F2/F3 porque define `origen` y el gatillo de descuento).

**Decisiones D1–D6: CERRADAS** (§5). Decisiones abiertas nuevas: 3 (§6).

**No se tocó código en esta sesión.** Este documento es solo la especificación.

---

## 0. Resumen ejecutivo

- El flujo de conversión **ya existe, ya es atómico e idempotente** (`conversion_service.py:96`). F2 lo extiende, no lo reescribe.
- **Convertir una cotización NO mueve inventario hoy**, y con D6 seguirá sin moverlo en la conversión. El stock de líneas `stock` se **reserva** al convertir y se **descuenta al entregar** (F3), no al pagar.
- **Cambio crítico de gatillo de stock:** hoy se descuenta al pasar a `pagado` (`ventas/views.py:497-498`). Es incorrecto con crédito (la mercadería sale antes del pago). Nuevo gatillo: estado operativo **`entregado`**, solo para líneas `origen='stock'`.
- El modelo dual se resuelve con 3 flags (`Empresa.modo_inventario`, `Producto.controla_stock`, `DetalleVenta.origen`) y una **decisión automática de `origen` en la conversión**. Cero código duplicado.
- La infra de **reserva ya existe** y se reutiliza: `reservar_para_venta` (`inventario_productos_terminados.py:233`), `liberar_reserva` (`:261`), `procesar_venta(desde_reserva=True)` (`:286`).
- Migraciones nuevas: todas **aditivas o nullable** (incluye volver `DetalleVenta.producto` nullable y un backfill de datos). Sin downtime.

---

## 1. Estado actual (investigación con evidencia)

### 1.1 Cotizaciones
- `Cotizacion` — `backend/apps/cotizaciones/models.py:10`. Estados (`:14-21`): `borrador, enviada, aceptada, rechazada, vencida, convertida`. `fecha_vencimiento` (`:58`), `venta` FK SET_NULL nullable (`:126`). **Nada asigna `vencida` hoy.** No hay motivo de rechazo.
- `DetalleCotizacion` — `models.py:213`. Tiene `producto` (FK nullable, `:222`), `codigo`, `descripcion`, `cantidad`, `precio_unitario`, `descuento_item`, `subtotal`, `orden`. **No** tiene `proveedor` ni `costo_unitario`.
- Endpoints — `views.py`: `cambiar-estado` (`:117`), `convertir-venta` (`:228`). Rechazo sin motivo (`:176-177`).
- Servicio — `conversion_service.py:96`: `@transaction.atomic` (`:96`), idempotente por `venta_id` (`:109`), `ProductosFaltantesError` si línea sin producto (`:116`), crea **una** `Venta` en `estado='pendiente'` (`:135`). **No crea OC. No llama `actualizar_stock()`.**
- **Por qué daba 400:** `ProductosFaltantesError` (línea sin producto, `views.py:146`) y `CotizacionNoConvertibleError` (estado no convertible, `:154`). Los 400 recientes eran de payload en el serializador (`producto:""` vs `null`, bytes nulos), ya corregidos.

### 1.2 Ventas — ¿mueve stock? (crítico para D6)
- `Venta` — `backend/apps/ventas/models.py:78`. Estados (`:79-84`): `borrador, pendiente, pagado, anulado` = **estado de PAGO**. No hay estado operativo.
- `DetalleVenta` — `models.py:505`: `producto` FK **PROTECT no-null** (`:511`), `cantidad`, `precio_unitario`. **No tiene `descripcion` ni `origen`.** → D1/D6 requieren volverlo nullable y añadir campos (ver §3, §4).
- Descuento de stock (`actualizar_stock()`, `:232`) se dispara **solo si `estado=='pagado'`**: `views.py:497-498`, `:552`, `serializers.py:365`, `admin.py:206`. Signals `post_save` **deshabilitados** (`signals.py:8-20`, `pass`).
- **Conclusión:** la conversión crea venta `pendiente` → no descuenta. El descuento actual al `pagado` es el gatillo que D6 corrige.

### 1.3 Compras — vínculo y stock
- `OrdenCompra` — `backend/apps/compras/models.py:620`. Estados `borrador/enviada/aprobada/rechazada/completada`. `proveedor` SET_NULL nullable (`:640`) + `proveedor_nombre` (`:647`). **No tiene FK a `Venta`.**
- `OrdenCompraDetalle` — `models.py:752`, **`managed=False`** (`:780`, tabla `compras_ordencompradetalle`). Se pueden insertar filas vía ORM; no se pueden añadir columnas por migración normal. **→ Deuda técnica, ver R4.**
- **Una OC no mueve stock.** `RecepcionCompra.save()` solo cambia `enviada→aprobada` (`:819`). `convertir_a_compra()` deshabilitado (`:745`). El stock lo mueve solo `Compra.actualizar_stock()` (`:308`) al pagar una `Compra`.

### 1.4 Dashboard — alertas
- Backend `DashboardResumen.get` (`backend/apps/dashboard/views.py:61`) arma `response_data` con `inventario.productos_bajo_stock` (`:217`), etc. Cache 120 s (`:227`).
- Frontend `Dashboard.jsx:27` `buildAlerts(resumen)` empuja `{level,message,actionLabel,actionPath}`; los pinta `AlertsBar` (`:14`). Patrón reusable para F4.

### 1.5 Órdenes de Servicio — patrón para F3
- `OrdenServicio` — `backend/apps/servicios/models.py:9`: `dias_sla` (`:69`), propiedades `dias_transcurridos` (`:122`), `estado_sla` → `sin_fecha/vencido/critico/alerta/ok` (`:133`), `en_riesgo` (`:146`).
- `HistorialEstadoOS` (`:239`): `orden`, `estado_anterior`, `estado_nuevo`, `fecha`, `usuario`, `notas`.
- Signals (`servicios/signals.py`): dict global de módulo `_estado_anterior_cache` (`:7`) — frágil bajo concurrencia → F3 usará endpoint explícito (D3).

### 1.6 Inventario — infra de reserva (habilita D6)
- `InventarioProductosTerminados` — `backend/apps/inventario/models/inventario_productos_terminados.py`: `cantidad_reservada` (`:33`), `reservar_para_venta(...)` (`:233`), `liberar_reserva(...)` (`:261`), `procesar_venta(..., desde_reserva=True)` (`:286`: descuenta de reservada si `True`, de disponible si `False`).
- `Producto.stock_total` (`producto.py:48`) = agregado mantenido por `actualizar_stock_total()` (`:149`). `Producto.tipo_producto` existe (`:40`); **no** existe `controla_stock` (lo añade D6).

---

## 2. Riesgos encontrados

| # | Riesgo | Sev. | Mitigación |
|---|--------|------|-----------|
| R1 | F2 dispara descuento de inventario al convertir | Alta | Ya mitigado: venta nace `pendiente`, OC no mueve stock. Con D6, líneas `stock` **reservan** (no descuentan) al convertir; descuentan solo en `entregado`. **Nunca** `actualizar_stock()` en la conversión. Test obligatorio. |
| R2 | Doble clic crea venta/OCs duplicadas | Alta | Conversión `@transaction.atomic` + retorno por `venta_id` (`conversion_service.py:109`). OCs: crear solo las faltantes con `filter(venta=venta, proveedor=...)`. |
| R3 | Fuga de costo/proveedor al PDF del cliente | Alta | El PDF (`utils/pdf_generator.py`) usa campos explícitos; no se añaden `costo_unitario`/`proveedor`. Test que verifica ausencia en el PDF. |
| **R4** | **`OrdenCompraDetalle` es `managed=False` (DEUDA TÉCNICA)** | **Media-Alta** | **Registrada formalmente.** La tabla existe fuera del estado de Django (migración 0007 la sacó del modelo, la tabla persistió). Esto ya **causó la cascada de bugs de columnas `NOT NULL`** al insertar filas sin columnas que la BD exigía. En Fase 1 se mantiene `managed=False` e insertamos filas vía ORM (D2). **Deuda a saldar en Fase 2:** adoptar la tabla con `managed=True` + migración `--fake`/`state_operations` que reconcilie columnas reales vs modelo, para que futuros `INSERT` no vuelvan a chocar con constraints invisibles. |
| R5 | Ventas convertidas antes de F2 no tienen OC | Baja | Generar OCs faltantes por `filter(venta=venta)` en vez de retornar ciego. |
| R6 | Historial con dict global (patrón servicios) | Media | F3 usa endpoint explícito que escribe historial en la misma transacción (D3). |
| **R7** | **Doble descuento de stock en ventas históricas** al cambiar el gatillo a `entregado` | **Alta** | Backfill `DetalleVenta.stock_descontado=True` en migración de datos para toda línea cuya venta ya está `pagado` (§4.4). El flag es la guarda de idempotencia. |
| R8 | Volver `DetalleVenta.producto` nullable rompe supuestos de código que asume producto presente | Media | Auditar usos de `detalle.producto` en ventas (`actualizar_stock`, PDF, guías). Las ramas de stock ya se saltan cuando `origen='pedido_proveedor'`; las líneas sin producto nunca entran a stock. |
| R9 | Empresa `sin_stock` con código de inventario aún activo (importador, señales) | Media | `controla_stock` y `origen='pedido_proveedor'` cortan toda ruta de stock; el menú se oculta (D6.1). Endpoints de inventario quedan accesibles pero inertes en Fase 1 (OD-C). |

---

## 3. Diseño por feature

### F1 — Costo y proveedor por línea de cotización

**Campos** — `DetalleCotizacion` (`cotizaciones/models.py:213`):
```python
proveedor = models.ForeignKey('compras.Proveedor', on_delete=models.SET_NULL,
    null=True, blank=True, related_name='detalles_cotizacion')
costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
```
**Margen = calculado, no guardado** (propiedades `margen_unitario`, `margen_pct`).
**Migración:** `cotizaciones/0005` (combinada con F4).
**Serializador** (`serializers.py:8`): añadir `proveedor`, `proveedor_nombre` (read-only), `costo_unitario`, `margen_unitario`, `margen_pct` (read-only). Valor inicial sugerido en UI: `producto.precio_compra` si hay producto.
**PDF:** sin cambios (R3).
**UI** `CotizacionForm.jsx`: sección colapsable "Costeo interno" por fila (proveedor autocomplete + costo), margen en vivo (badge). Nunca en la vista de cliente.

---

### F2 — Conversión en 1 clic (1 OC por proveedor)

**Campos** — `OrdenCompra` (`compras/models.py:620`):
```python
venta = models.ForeignKey('ventas.Venta', on_delete=models.SET_NULL,
    null=True, blank=True, related_name='ordenes_compra')
cotizacion_origen = models.ForeignKey('cotizaciones.Cotizacion', on_delete=models.SET_NULL,
    null=True, blank=True, related_name='ordenes_compra')
```
**Migración:** `compras/0018`.

**Lógica** — extender `convertir_cotizacion_a_venta` (`conversion_service.py:96`), todo en el `@transaction.atomic` existente:
1. Crear/reutilizar venta. **D1 ajustada:** producto y proveedor **ambos opcionales**; las líneas de texto libre son válidas (requiere `DetalleVenta` nullable + `descripcion`, ver §4). Ya no se lanza `ProductosFaltantesError`.
2. Para cada línea, calcular `origen` (ver §4.3, tabla de comportamiento).
3. Líneas `origen='stock'` (solo empresas `con_stock`): **reservar** con `reservar_para_venta(...)`. No descuentan.
4. Líneas `origen='pedido_proveedor'`: agrupar por `proveedor_id`. Para cada proveedor sin OC previa de esta venta (`not OrdenCompra.objects.filter(venta=venta, proveedor=prov).exists()`, R2/R5), crear **una** `OrdenCompra` `borrador` con `venta`, `cotizacion_origen`, e insertar sus `OrdenCompraDetalle` vía ORM (R4/D2).
5. Líneas `pedido_proveedor` **sin proveedor** (texto libre sin proveedor asignado): no generan OC; se devuelven en `lineas_sin_proveedor` como aviso (no error).
6. **Nunca** `actualizar_stock()` (R1).

**Respuesta:**
```json
{ "venta_creada": true, "venta_id": 123, "venta_numero": "V-000123",
  "ocs_creadas": [{"id":9,"numero":"000009","proveedor":"ACME SAC","lineas":3}],
  "lineas_stock_reservadas": 2, "lineas_sin_proveedor": [{"detalle_id":5,"descripcion":"..."}],
  "message": "Venta V-000123: 1 OC creada, 2 líneas reservadas de stock, 1 línea sin proveedor." }
```
**UI:** toast/modal resumen con links a venta y OCs + acción "asignar proveedor" para las líneas sueltas. Camino feliz = 1 clic.

---

### F3 — Timeline operativo de la venta (+ gatillo de stock de D6)

**Campo** — `Venta`:
```python
ESTADO_OPERATIVO_CHOICES = [('pendiente_compra','Pendiente de compra'),('comprado','Comprado'),
  ('recibido','Recibido'),('entregado','Entregado'),('esperando_oc_nr','Esperando OC/NR'),
  ('facturado','Facturado'),('cobrado','Cobrado')]
estado_operativo = models.CharField(max_length=30, choices=ESTADO_OPERATIVO_CHOICES, default='pendiente_compra')
```
**Modelo** `HistorialEstadoVenta` (espejo de `HistorialEstadoOS`): `venta`, `estado_anterior`, `estado_nuevo`, `fecha` (`auto_now_add`), `usuario`, `notas`.
**SLA:** constante `SLA_OPERATIVO = {'pendiente_compra':3,'comprado':5,...}`; propiedades `dias_en_estado_actual`, `estado_sla_operativo` (`ok/alerta/critico/vencido`).
**Cambio de estado:** endpoint explícito `POST /api/ventas/{id}/avanzar-estado-operativo/` (D3): en una transacción actualiza `estado_operativo`, crea `HistorialEstadoVenta` y, **al entrar a `entregado`, descuenta el stock de las líneas `origen='stock'` no descontadas** (ver §4.4).
**Migración:** `ventas/0017`.
**UI:** stepper + botón "Avanzar" (1 clic) + historial con fechas + badge SLA.

---

### F4 — Cierre de cotizaciones no ganadas

**Campos** — `Cotizacion`:
```python
MOTIVO_RECHAZO_CHOICES = [('precio','Precio'),('plazo','Plazo'),('competidor','Competidor'),
  ('sin_presupuesto','Sin presupuesto'),('otro','Otro')]
motivo_rechazo = models.CharField(max_length=20, choices=MOTIVO_RECHAZO_CHOICES, null=True, blank=True)
motivo_rechazo_nota = models.TextField(null=True, blank=True)
```
**Migración:** `cotizaciones/0005` (con F1).
**Rechazo obligatorio:** en `cambiar-estado` (`views.py:176`), si `estado=='rechazada'` y falta `motivo_rechazo` → 400.
**Vencimiento derivado (D4, sin cron):** propiedad `esta_vencida` (`estado in (borrador,enviada) and fecha_vencimiento < hoy`), expuesta en el serializador. No se sobrescribe `estado`.
**Seguimiento (alerta dashboard, sin emails):** `enviada` con `fecha_emision < hoy − N` (N=7, D5). Backend añade `cotizaciones: {seguimiento_pendiente, vencidas}` al payload de `/api/dashboard/resumen/`; frontend añade ramas en `buildAlerts` (`Dashboard.jsx:27`).

---

## 4. D6 — Modelo dual (con / sin inventario)

Objetivo: una sola base de código sirve a empresas con stock y back-to-base, por configuración.

### 4.1 Flags nuevos

| Flag | Modelo | Tipo / default | Regla |
|------|--------|----------------|-------|
| `modo_inventario` | `Empresa` | `CharField('con_stock'/'sin_stock')`, default **`con_stock`** | No rompe a nadie. Soldigem = `sin_stock`. En `sin_stock` se **oculta el menú Inventario** (UI). |
| `controla_stock` | `Producto` | `BooleanField`, default **`True`** | Servicios / productos no inventariables = `False`. |
| `origen` | `DetalleVenta` | `CharField('stock'/'pedido_proveedor')`, default **`pedido_proveedor`** | Decidido **automáticamente** en la conversión (§4.3). |
| `stock_descontado` | `DetalleVenta` | `BooleanField`, default **`False`** | Guarda de idempotencia del descuento (§4.4, R7). |

Además, para soportar líneas de texto libre en ventas (D1 ajustada):
- `DetalleVenta.producto` → **nullable** (`null=True, blank=True`).
- `DetalleVenta.descripcion` → **nuevo** (`CharField/TextField null=True, blank=True`) para líneas sin producto.

### 4.2 Menú Inventario oculto en `sin_stock`
Frontend: gating del ítem de navegación (`AnimatedSidebar.jsx` / `Navbar.jsx`) por `empresa.modo_inventario`. Exponer `modo_inventario` en el serializador de empresa / endpoint de perfil. Sin gating de endpoints en Fase 1 (OD-C).

### 4.3 Decisión automática de `origen` (en la conversión)

```
si empresa.modo_inventario == 'sin_stock':
    origen = 'pedido_proveedor'          # SIEMPRE, sin excepción
si empresa.modo_inventario == 'con_stock':
    si (detalle.producto and detalle.producto.controla_stock
        and disponible(producto) >= detalle.cantidad):
        origen = 'stock'                 # reserva, no descuenta
    en otro caso:                        # stock insuficiente / no controla / sin producto
        origen = 'pedido_proveedor'      # línea COMPLETA a la OC
```
**Stock parcial — decisión (la más simple):** si `disponible < cantidad`, la **línea completa** va a `pedido_proveedor`. **No se divide la línea.** Dividir generaría dos sub-líneas, dos orígenes, reserva parcial y reconciliación — complejidad que Fase 1 no necesita (filtro CLAUDE: menos fricción). Dividir queda como mejora futura si el negocio lo pide.

`disponible(producto)` = `producto.stock_total` (ver OD-A).

### 4.4 Momento del descuento de stock (CAMBIO CRÍTICO)

- **Antes:** descuento al pasar a `pagado` (`ventas/views.py:497-498`). Incorrecto con crédito.
- **Ahora:** descuento al entrar a estado operativo **`entregado`** (F3), **solo** para líneas `origen='stock'` con `stock_descontado=False`.
  - Al entregar: por cada línea `stock` no descontada → `procesar_venta(..., desde_reserva=True)` (consume la reserva creada en la conversión) → `stock_descontado=True`.
  - **Idempotencia:** el flag evita doble descuento si se reentrega o se reintenta.
- **Reversión de `entregado`:** si `estado_operativo` retrocede desde `entregado`, por cada línea `stock` con `stock_descontado=True` → reintegrar (re-reservar con `reservar_para_venta` o entrada equivalente) y `stock_descontado=False`. Simétrico y reversible.
- **Ventas históricas (migración de datos, R7):** backfill `stock_descontado=True` para toda `DetalleVenta` cuya `venta.estado == 'pagado'` (ya descontaron bajo la regla vieja). Las ventas no pagadas quedan `False` y descontarán al entregar bajo la regla nueva. Opcional: setear `estado_operativo` coherente (p. ej. `cobrado`) en ventas ya pagadas para que el timeline refleje la realidad.
- **Líneas `pedido_proveedor` NUNCA mueven stock**, en ninguna empresa (ver §4.5). En `sin_stock` esto es absoluto.
- El gatillo viejo en `pagado` (`views.py:497-498`, `:552`, `serializers.py:365`, `admin.py:206`) se **retira**; el descuento pasa a vivir solo en la transición a `entregado`.

### 4.5 Empresas `con_stock` con líneas `pedido_proveedor` — ¿neto cero o ignorar?

**Decisión (la más simple): IGNORAR el inventario para líneas `pedido_proveedor`.**
Estas líneas son back-to-back dentro de una empresa con stock: la mercadería entra del proveedor y sale al cliente sin llegar a almacén. El movimiento "neto cero" (entrada en recepción de OC + salida en entrega) añadiría dos movimientos por línea que siempre se cancelan: ruido, sin señal de inventario real, y obligaría a que la recepción de OC mueva stock (algo que hoy no hace, `compras/models.py:819`). **Las líneas `pedido_proveedor` no tocan inventario; la trazabilidad la da la OC vinculada a la venta** (`OrdenCompra.venta`, F2). Neto-cero trazable queda como opción de Fase 2 si un cliente lo exige.

### 4.6 Tabla de comportamiento

| Empresa | Producto | Disponibilidad | `origen` | ¿Mueve stock? | ¿Cuándo? |
|---------|----------|----------------|----------|---------------|----------|
| `sin_stock` | cualquiera (o texto libre) | n/a | `pedido_proveedor` | **No** | nunca |
| `con_stock` | `controla_stock=True` | `stock_total ≥ cantidad` | `stock` | **Sí** | reserva al convertir; **descuenta al `entregado`** |
| `con_stock` | `controla_stock=True` | `stock_total < cantidad` | `pedido_proveedor` | **No** | nunca (línea completa a OC) |
| `con_stock` | `controla_stock=False` (servicio) | n/a | `pedido_proveedor` | **No** | nunca |
| `con_stock` | sin producto (texto libre) | n/a | `pedido_proveedor` | **No** | nunca |

---

## 5. Decisiones cerradas (D1–D6)

- **D1 (AJUSTADA):** en la conversión, **producto y proveedor son ambos opcionales**. Se permiten líneas de texto libre; toda línea sin producto (y toda línea sin stock disponible) se trata como `pedido_proveedor`. Se elimina `ProductosFaltantesError` como bloqueo. Requiere `DetalleVenta.producto` nullable + `descripcion` (§4.1).
- **D2:** `OrdenCompraDetalle` se mantiene `managed=False`; las líneas de OC se insertan vía ORM. La condición `managed=False` queda **registrada como deuda técnica en R4** (origen de la cascada de bugs de columnas `NOT NULL`), a saldar en Fase 2.
- **D3:** historial de estado operativo vía **endpoint explícito** (no signal); escribe `HistorialEstadoVenta` en la misma transacción.
- **D4:** vencimiento de cotizaciones **100% derivado en lectura** (`esta_vencida`), sin cron, sin sobrescribir `estado`.
- **D5:** umbrales de días (**N=7** seguimiento, `SLA_OPERATIVO` por estado) como **constante global** en Fase 1; configurable por empresa en Fase 2.
- **D6:** modelo dual con `Empresa.modo_inventario`, `Producto.controla_stock`, `DetalleVenta.origen`; decisión automática de `origen`; gatillo de descuento movido a `entregado`; `pedido_proveedor` nunca mueve stock (§4).

---

## 6. Decisiones abiertas nuevas (máx. 3)

**OD-A — Fuente de "disponible" para decidir `origen`.**
Hay dos fuentes: `Producto.stock_total` (agregado ya mantenido, usado por el dashboard) e `InventarioProductosTerminados.cantidad_disponible` (detalle por almacén).
Recomendación: **usar `Producto.stock_total`**. Es la autoridad que ya ve el usuario, una sola lectura, sin elegir almacén en la conversión. La reserva fina por almacén se resuelve en el paso de reserva. Si en el futuro se opera multi-almacén real, migrar a `cantidad_disponible`.

**OD-B — Reserva al convertir: ¿reutilizar la infra o diferir?**
La infra existe (`reservar_para_venta`/`procesar_venta(desde_reserva=True)`), pero depende de que `InventarioProductosTerminados` esté poblado para ese producto/almacén.
Recomendación: **reutilizar la reserva existente** (Layer 1, ya construida y probada). **Degradación segura:** si no hay registro de `InventarioProductosTerminados` para el producto, saltar la reserva y descontar directo en `entregado` con `desde_reserva=False`. La línea sigue siendo `origen='stock'`; solo cambia el mecanismo interno. Así la reserva nunca bloquea la conversión.

**OD-C — `sin_stock`: ¿solo ocultar menú o también bloquear endpoints de inventario?**
Recomendación: **solo ocultar la UI en Fase 1**. Bloquear endpoints por permiso puede romper el importador y otras rutas que tocan inventario de forma indirecta; en `sin_stock` esas rutas quedan inertes (ningún flujo genera `origen='stock'`). Gating de endpoints por `modo_inventario` en Fase 2, con auditoría previa de quién los llama.

---

## 7. Lista final de migraciones (todas aditivas / nullable)

| # | Migración | App | Contenido | Tipo |
|---|-----------|-----|-----------|------|
| 1 | `empresas/0006_empresa_modo_inventario` | empresas | `modo_inventario` CharField default `'con_stock'` | Aditiva |
| 2 | `inventario/0011_producto_controla_stock` | inventario | `controla_stock` Bool default `True` | Aditiva |
| 3 | `cotizaciones/0005_detalle_costeo_y_motivo_rechazo` | cotizaciones | `DetalleCotizacion.proveedor`, `costo_unitario` (F1) + `Cotizacion.motivo_rechazo`, `motivo_rechazo_nota` (F4) | Aditiva/nullable |
| 4 | `compras/0018_ordencompra_venta` | compras | `OrdenCompra.venta`, `cotizacion_origen` (F2) | Aditiva/nullable |
| 5 | `ventas/0017_estado_operativo_historial` | ventas | `Venta.estado_operativo` + modelo `HistorialEstadoVenta` (F3) | Aditiva |
| 6 | `ventas/0018_detalleventa_dual` | ventas | `DetalleVenta.origen`, `stock_descontado`, `descripcion`; `producto` → nullable (D1/D6) | Aditiva / nullable |
| 7 | `ventas/0019_backfill_stock_descontado` | ventas | **Data migration**: `stock_descontado=True` donde `venta.estado='pagado'` (R7) | Datos (idempotente) |

Notas:
- Volver `producto` nullable (#6) es seguro: las filas existentes conservan su valor.
- #5 y #6 pueden combinarse si se implementan juntas; se listan separadas por claridad de feature.
- Ninguna migración borra datos ni columnas. Reversibles.

---

## 8. Checklist de pruebas (cubre AMBOS modos de empresa)

**Empresa `sin_stock` (Soldigem):**
- [ ] Toda línea convertida queda `origen='pedido_proveedor'`, con y sin producto.
- [ ] La conversión no crea `MovimientoInventario` ni cambia `Stock` en ningún estado, incluido `entregado`.
- [ ] Línea de texto libre (sin producto) convierte OK y, con proveedor, entra a su OC.
- [ ] Menú Inventario oculto para usuarios de la empresa.

**Empresa `con_stock`:**
- [ ] Producto `controla_stock=True` con `stock_total ≥ cantidad` → `origen='stock'`, se **reserva** al convertir (sube `cantidad_reservada`), **no** baja `cantidad_disponible`.
- [ ] Misma línea: al pasar a `entregado` se descuenta (consume reserva) y `stock_descontado=True`; al pagar **antes** de entregar **no** se descuenta.
- [ ] `stock_total < cantidad` → línea completa `pedido_proveedor`, sin reserva, sin división.
- [ ] Producto `controla_stock=False` (servicio) → `pedido_proveedor`, nunca mueve stock.
- [ ] Reversión de `entregado` reintegra stock y pone `stock_descontado=False` (idempotente).
- [ ] Línea `pedido_proveedor` en empresa `con_stock` no mueve stock en ningún momento (§4.5).

**Transversal (ambos modos):**
- [ ] Doble clic en aceptar/convertir no duplica venta ni OCs (R2, R5).
- [ ] 2 proveedores → exactamente 2 OCs agrupadas; líneas `stock` no entran a OC.
- [ ] Línea `pedido_proveedor` sin proveedor aparece en `lineas_sin_proveedor` (D1).
- [ ] Backfill: ventas ya `pagado` no vuelven a descontar al entregar (R7).
- [ ] PDF de cliente no contiene `costo_unitario` ni proveedor (R3).
- [ ] Rechazar sin `motivo_rechazo` → 400; con motivo, persiste (F4).
- [ ] `esta_vencida=True` para enviada vencida, sin tocar `estado` (D4).
- [ ] `avanzar-estado-operativo` crea `HistorialEstadoVenta` con usuario y fecha (F3).
- [ ] Dashboard reporta `seguimiento_pendiente` y `vencidas` (F4).

---

## 9. Impacto vs complejidad

| Feature | Valor | Complejidad | Migración | Riesgo | Orden |
|---------|-------|-------------|-----------|--------|-------|
| F1 costo/proveedor | Alto (habilita F2/F3) | Baja | cotizaciones/0005 | Bajo (R3) | 1º |
| F2 conversión + OC | Muy alto (núcleo) | Media | compras/0018 | Medio (R2,R4,R5) | 2º |
| F3 timeline + gatillo stock | Alto | Media-Alta | ventas/0017-0019 | Alto (R1,R7,R8) | 3º |
| F4 cierre no ganadas | Medio-alto | Baja | cotizaciones/0005 | Bajo | 4º |
| D6 modelo dual | Estructural (SaaS) | Media | empresas/0006, inventario/0011, ventas/0018 | Medio (R8,R9) | junto a F2/F3 |

**Secuencia: F1 → F2 → F3 → F4**, con D6 entretejido en F2 (decisión de `origen`) y F3 (gatillo de descuento).

---

## Apéndice — Referencias archivo:línea

- Conversión: `backend/apps/cotizaciones/services/conversion_service.py:96,109,116,135`
- Cotización/Detalle: `backend/apps/cotizaciones/models.py:10,58,126,213,222` · endpoints `views.py:117,176,228`
- Venta/DetalleVenta + stock: `backend/apps/ventas/models.py:78,232,505,511` · `views.py:497,552` · `signals.py:8,15`
- Orden de compra (deuda R4): `backend/apps/compras/models.py:620,640,752,780,819`
- Servicios (patrón F3): `backend/apps/servicios/models.py:122,133,239` · `signals.py:7,25`
- Inventario (reserva D6): `backend/apps/inventario/models/inventario_productos_terminados.py:33,233,261,286` · `producto.py:40,48,149`
- Dashboard: `backend/apps/dashboard/views.py:61,217,227` · `frontend/src/components/Dashboard/Dashboard.jsx:27,33`
</content>
