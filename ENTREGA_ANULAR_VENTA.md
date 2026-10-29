# ENTREGA — fix/anular-venta

Rama desde `main` (c4110b3). LOCAL, sin push ni deploy.

## 1. Causa del error «_.deleteVenta is not a function»

- `VentaList.jsx` llama `ventasService.deleteVenta(id)` **desde el commit
  inicial del frontend (`5b35d7a`)**; el servicio nunca tuvo ese método (expone
  `eliminarVenta`). `git log -S deleteVenta -- frontend/src/services/` no
  devuelve ningún commit. **No es una regresión de hoy**: el commit de líneas
  libres (`a895667`) solo cambió el mapeo de `detalles` en `crearVenta` y no
  quitó ningún método exportado.
- Detrás del botón había además un **borrado físico**: `VentaViewSet` tenía DOS
  `destroy()`; el que valía borraba la venta (si no estaba pagada) y liberaba su
  correlativo para reutilizarse.

## 2. Cambios

**Backend** — `POST /api/ventas/{id}/anular/ {"motivo": "..."}`, único camino
(`apps/ventas/services/anulacion_venta.py`; el método del modelo, la acción del
admin y `cambiar_estado` delegan o redirigen):

| Regla | Comportamiento |
|---|---|
| Rol | Solo admin. Operador y solo_lectura → **403**; otra empresa → **404** |
| Motivo | Obligatorio (400 si falta) |
| Doble anulación | **400** «La venta V-xxxxxx ya está anulada» |
| Número | Se conserva; el correlativo nunca se reutiliza |
| Trazabilidad | `estado=anulado`, `anulado_por`, `anulado_en`, `motivo_anulacion` |
| Pagos reales | **Bloquea**: «… Primero revierte los pagos». La reversión **existe** (`DELETE /api/ventas/{id}/pagos/{pago_id}/` y `ventasService.eliminarPago`) |
| Placeholder de crédito | Se marca `anulado=True` con nota; **no se borra** |
| Stock / kárdex | Líneas entregadas (`stock_descontado`): se reintegra al inventario + movimiento **`devolucion_venta`** en el kárdex; salidas legadas `salida_venta` también se revierten; el movimiento original **nunca** se borra. Líneas libres: intactas |
| Guía de remisión | No tiene FK a la venta (se vincula por el texto «…desde Venta V-xxx»). **Borrador → se cancela en cascada; emitida / en proceso / entregada → bloquea** («Cancélalas primero en Guías»), porque ya es un documento de traslado en circulación y su módulo tiene su propio estado `cancelada` |
| Orden de servicio | **No aplica**: `servicios` no se vincula a ventas (solo a Cliente) |
| Cotización de origen | Vuelve a **«aceptada»** y se desliga (`venta=None`). Motivo: la conversión es idempotente por `cotizacion.venta_id`; con el vínculo intacto, reconvertir devolvería la venta ANULADA. La traza queda en la venta anulada (`referencia` = número de cotización). Reconvertir crea una venta NUEVA con otro número |
| OCs vinculadas | No se tocan (compromisos con proveedores); se listan en `avisos` |
| Efectos | Sale de CxC, por cobrar, ventas del mes, KPIs y dashboard (cachés invalidadas), `resumen_ventas` del bot y reportes |
| DELETE físico | `DELETE /api/ventas/{id}/` → **405** |

Auditoría de agregados: CxC, devengo, margen, `resumen_ventas` y el reporte de
clientes ya excluían anuladas. **Cuatro no** y se corrigieron: KPI
`total_ventas_mes` del analista IA, «ventas fuera de SLA» del dashboard, la tool
`esperando_oc_nr` del agente y «clientes recurrentes» de finanzas.

**Frontend**: modal de anulación (número, cliente y total para confirmar +
motivo obligatorio; muestra los avisos del backend), solo para admin
(`useEsAdmin`); badge gris «Anulada», fila atenuada y sin acciones de pago /
avance operativo / guía; filtro por estado (pendiente / pagado / anulada); banner
en el detalle con motivo, quién y cuándo. `eliminarVenta` se reemplazó por
`anularVenta`: la UI ya no puede borrar ventas.

## 3. Migración `ventas.0027_anulacion_trazable` (aditiva)

```sql
BEGIN;
ALTER TABLE "ventas_pagoventa" ADD COLUMN "anulado" boolean DEFAULT false NOT NULL;
ALTER TABLE "ventas_pagoventa" ALTER COLUMN "anulado" DROP DEFAULT;
ALTER TABLE "ventas_venta" ADD COLUMN "anulado_en" timestamp with time zone NULL;
ALTER TABLE "ventas_venta" ADD COLUMN "anulado_por_id" bigint NULL CONSTRAINT "ventas_venta_anulado_por_id_7c56a2a7_fk_authentic" REFERENCES "authentication_customuser"("id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "ventas_venta_anulado_por_id_7c56a2a7_fk_authentic" IMMEDIATE;
ALTER TABLE "ventas_venta" ADD COLUMN "motivo_anulacion" text DEFAULT '' NOT NULL;
ALTER TABLE "ventas_venta" ALTER COLUMN "motivo_anulacion" DROP DEFAULT;
CREATE INDEX "ventas_venta_anulado_por_id_7c56a2a7" ON "ventas_venta" ("anulado_por_id");
COMMIT;
```

Las tres columnas `NOT NULL` llevan `DEFAULT` constante: en Postgres ≥ 11 eso
es solo metadatos (no reescribe la tabla). El `CREATE INDEX` sobre
`ventas_venta` toma un lock de escritura mientras se construye (tabla pyme:
segundos). Las ventas que ya estaban «anuladas» en prod quedan con
`anulado_por/anulado_en` NULL y motivo vacío (no hay de dónde reconstruirlos).

Ojo: la rama local `feat/pdf-venta` (no mergeada) también trae un
`ventas.0027_…`; si se mergea después habrá que renumerarla a 0028.

## 4. Mismo patrón en otros módulos (reporte; no corregido aquí)

**Borrado físico desde la UI** (botón que hace `DELETE` y el backend usa el
`destroy` por defecto de `ModelViewSet`, sin guardas):
- Cotizaciones — `CotizacionList.jsx` → `cotizacionesService.delete`.
- Órdenes de compra — `OrdenesCompraList.jsx` → `comprasService.deleteOrden`.
- Órdenes de compra de servicio — `OrdenesServicioCompraList.jsx` →
  `comprasService.deleteOrdenServicio`.

No es trivial: cada uno necesita su propia regla de anulación (OC aprobada
con recepción, cotización convertida, etc.). Recomiendo una rama por módulo
con el mismo patrón de esta.

**Llamadas a métodos inexistentes** (escaneo automático de todo `src/`,
verificado a mano): `comprasService.aprobarOrden`, `createOrdenCompra`,
`getRecepciones`, `getOrdenesCompra`, `createRecepcion`, `confirmarRecepcion`
(en `Compras/OrdenesCompra.jsx` y `Compras/RecepcionCompra.jsx`) y
`aiService.getAssistantResponse`, `deleteConversation` (en
`AIAssistant/Chat.jsx` y `ChatBar.jsx`). **Ninguno de esos 4 componentes se
importa en ningún lugar**: es código muerto, sin impacto en prod. Recomiendo
borrarlos en una limpieza aparte.

## 5. Pruebas

- `tests/test_anular_venta.py`: 14 tests (CxC/totales/KPIs conservando el
  número, placeholder anulado, bot, caché, pago real → 400, doble → 400,
  motivo, guía emitida/borrador, operador/solo_lectura → 403, otra empresa →
  404, DELETE → 405, kárdex con reversa y original intacto, salida legada,
  cotización reconvertible).
- Suite completa backend en Postgres: **428 tests OK (3 skipped), 0 fallos**. Frontend: vitest
  12/12 y `vite build` OK. `makemigrations --check`: sin cambios.
