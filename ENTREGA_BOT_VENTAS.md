# ENTREGA — feat/bot-ventas

Rama `feat/bot-ventas` desde `main` (4a32ea4). LOCAL, sin push ni deploy.
Caso real: «crea venta para bruno perez 10 headsets jabra evolve 20 $39 la
unidad mas igv» terminó como la cotización COT-00000107 sin aviso.

## 1. Cómo crea ventas la web (investigado ANTES de tocar nada)

**Venta directa**: `POST /api/ventas/` → `VentaViewSet.perform_create` →
`VentaSerializer`:
- `validate()` resuelve `cliente_id` acotado a la empresa, valida cada detalle
  (producto de la empresa, que NO sea materia prima, cantidad y precio > 0) y
  tipo/método de pago.
- `create()` (transacción atómica) crea la `Venta`, sus `DetalleVenta` y llama
  `actualizar_totales()` (con `igv_incluido`: True = precios con IGV, se
  extrae; False = base, se agrega 18 %).
- Pasos posteriores (vivían en la vista): crédito_30/60 → estado `pendiente` +
  `fecha_vencimiento` + **PagoVenta placeholder `pendiente` por el total**
  (así entra a CxC); contado → la web lo manda con estado **`pagado`**
  (default del formulario) y se sincroniza el estado operativo; `entrega
  inmediata` opcional; invalidación de cachés (listas + dashboard).

**Efectos**: numeración `V-xxxxxxxx` por empresa (en `save()`, con lock);
**stock y kárdex NO se mueven al crear** — se descuentan al entrar al estado
operativo `entregado` (`aplicar_entrega_stock`, guarda estricta: solo líneas
`origen='stock'` CON producto; una línea libre jamás mueve stock); CxC = saldo
`total − pagos_total` (+ placeholder en crédito).

**Conversión**: el botón de la web usa
`apps/cotizaciones/services/conversion_service.convertir_cotizacion_a_venta`
(atómica, idempotente, decide origen por línea, genera OCs por proveedor, marca
la cotización `convertida` y la liga a la venta). **Existe: el bot la reutiliza
tal cual.**

**Refactor del punto 1**: los pasos post-serializer se extrajeron a
`apps/ventas/services/creacion_venta.py` (`crear_venta` /
`completar_creacion_venta`), usados por la vista **y** por el bot. No hay ruta
de creación paralela. El serializer ganó soporte de líneas libres
(`producto: null` + `descripcion`, que `DetalleVenta` ya soportaba desde D1);
el flujo de la web no cambia (siempre manda producto).

## 2. Causa del incidente y cambios

**Causa**: «crear venta» no tenía herramienta en el bot. El modelo, con
`preparar_cotizacion` como única tool de documentos, la usó y el bot creó una
cotización sin avisar el cambio de tipo.

**Cambios** (por punto del pedido):
- **(2) `preparar_venta`**: mismo patrón de borrador que la cotización (núcleo
  compartido `_payload_documento`: líneas libres con precio, meta-frases, IGV,
  moneda, cliente difuso/nuevo, historial). El borrador dice «🧾 Venta para X»
  con tipo (contado/crédito) y método. Confirmar → `crear_venta` (servicio de
  la web). El rol `solo_lectura` se valida al preparar **y al confirmar**
  (`confirmar_borrador` lo re-exige: callback_data es forjable). Toda línea de
  venta exige precio. Test: línea libre de venta **no mueve stock ni kárdex**
  ni al entregar (extensión del test de cotizaciones).
- **(3) `convertir_cotizacion_en_venta`**: borrador de conversión por número
  («COT-00000107», «COT-107», «107») o por cliente (su última cotización
  abierta); confirmar usa `convertir_cotizacion_a_venta` de la web.
  Ya-convertida / rechazada / vencida / sin líneas → error claro.
- **(4) Honestidad**: regla en el system prompt (NUNCA cambiar el tipo de
  documento pedido; sin herramienta → ninguna tool) y el mensaje de fuera de
  alcance ahora es explícito: «Eso no puedo hacerlo desde el chat. Sí puedo:
  …». Caso de eval #30 («anula la factura 5»).
- **(5) Cliente nuevo por DNI/RUC**: `aplicar_documento` consulta APIS.NET.PE
  con `DocumentoService.consultar_documento` — **el mismo servicio que la
  web** (ella lo usa vía /api/core/consultar-*) — y usa el nombre oficial de
  RENIEC/SUNAT. El borrador muestra «✅ DNI 70771234 → **BRUNO ALONSO PEREZ
  QUISPE** (escribiste «Bruno Perez»)» para confirmarlo. Si APIS falla: aviso
  «No pude verificar…», log con **severity ERROR**, y se usa el nombre tal
  como lo escribió el usuario — igual que la web, que permite el ingreso
  manual (no existe un flag «sin verificar» en el modelo Cliente).
- **(6) PDF firmado**: el token ahora firma `cot_id:empresa_id` (atado a
  documento **y** empresa); manipulado, de otra empresa o con el formato viejo
  → **403**; expiración **7 días** (antes 72 h) → **410** con mensaje. Tests
  de los cuatro casos.

## 3. Migraciones (SQL)

Una sola, **sin SQL** (choices):

```
canales.0004_tipos_venta_en_borrador
BEGIN;
-- Alter field tipo on borradoragente
-- (no-op)
COMMIT;
```

`makemigrations --check`: sin cambios pendientes. Nada que revisar en Supabase.

## 4. Evals

Casos nuevos 27–31 (`apps/canales/eval/mensajes.py`): el mensaje real de Bruno
(VENTA en USD, precio base «mas igv», línea libre), su multi-turno con el
cliente después, «convierte la COT-107 en venta» (fixture `COT-00000107`),
«anula la factura 5» (honesto, sin tool) y venta con cliente nuevo por DNI.
Críticos: 27–30. Umbral: ≥ 90 % (28/31) + críticos. Oráculo sin red: **31/31**.

**Ajuste pre-deploy (condición de pago)**: `preparar_venta` ya NO asume
contado. Solo si el usuario la dijo («al contado»/«ya pagó» → contado con su
medio, o el default web `efectivo`; «a N días» → crédito con vencimiento a N
días exactos); sin condición, el borrador queda incompleto y pregunta con
botones **[Crédito 30 días] [Crédito 15 días] [Contado]** (la ficha del
Cliente no guarda condición/plazo: no hay valor previo que ofrecer —
verificado). El borrador siempre muestra la condición y, en crédito, la fecha
de vencimiento. La conversión aplica la misma regla (solo se prellena si la
cotización dice crédito explícito en forma_pago; el default «Contado» no
cuenta). Regresión web: `tests/test_ventas_creacion_web.py` prueba que POST
/api/ventas/ contado/crédito_30/crédito_60 produce EXACTAMENTE lo de antes del
refactor (estado, placeholder, vencimiento, numeración V-xxxxxx).

**Eval real con gemini-3.1-flash-lite (tras el ajuste): 32/32 correctos en una
sola corrida** (83,011 tokens, media 1.6 s; umbral 29/32 superado, todos los
críticos ✓), incluido el #32: «crea venta para Interbank 2 jabra a 500 soles»
→ condición PENDIENTE (asumirla cuenta como fallo). Corrida previa (31 casos):
- Corrida principal: 24/24 hasta el caso 24; en el 25 Vertex dio un timeout
  transitorio (30 s) y justo ahí venció el token de la sesión → 25–31 cayeron
  con error de credencial (no del modelo).
- Reintento con token fresco: 25 ✓, 27 ✓, 28 ✓ (preparar_venta, 2 rondas),
  29 ✓ (convertir_cotizacion_en_venta), 30 ✓ (sin tool, honesto), 31 ✓;
  el 26 repitió timeout transitorio y pasó al reintentarse (1.5 s, 1 ronda).
- Métricas típicas: 1–2 rondas, ~2,100 tokens/caso, media ~1.5 s (los
  multi-turno 3–8 s).

## 5. Tests y suite

- Nuevos: `apps/canales/tests/test_bot_ventas.py` (14) — venta e2e de Bruno
  con DNI verificado (total $460.20 al céntimo, estado `pagado` contado, línea
  libre), crédito con placeholder (flujo web), stock intacto al entregar línea
  libre, rol en confirmar, conversión e2e con el servicio web, honestidad,
  APIS ok/caído, y los 4 casos del PDF firmado.
- Ajustados: texto del fallback honesto (2 asserts) y el confirm de cotización
  ahora mockea APIS (muestra «RUC … →»).
- Suite `canales+ventas+cotizaciones`: **163/163 OK**. Suite completa del backend en Postgres: **405 tests OK (3 skipped), 0 fallos** (tras el ajuste de condición); `makemigrations --check`: sin cambios.

## 6. Archivos

- `apps/ventas/services/creacion_venta.py` (NUEVO), `apps/ventas/views.py`,
  `apps/ventas/serializers.py` — servicio de dominio + líneas libres.
- `apps/canales/nucleo/{esquemas,servicios,interprete,orquestador,contexto}.py`
  — preparar_venta, conversión, honestidad, APIS, link PDF con empresa.
- `apps/canales/models.py` + `migrations/0004` — tipos venta/conversion_venta.
- `apps/canales/vistas.py` — PDF: 7 días + token documento+empresa.
- `apps/canales/eval/{mensajes,runner}.py`, tests.

Frontend: sin cambios.
