# FASE 2 — Agente de intake por correo (MCP del ERP)

> Spec de arquitectura e implementación. Investigación read-only; **no se modificó
> código**. Evidencia con `archivo:línea`. Fecha: 2026-10-14. Rama base: `feat/landing`.

## 1. Resumen ejecutivo

Fase 2 automatiza **dos** pasos del workflow de Soldigem con un agente externo
(Claude en claude.ai / Cowork, con Gmail conectado + un **MCP remoto** del ERP,
corriendo como **tarea programada diaria**):

- **F5 — Intake de solicitudes de cotización:** el agente lee correos de pedido de
  cotización, extrae cliente/ítems/cantidades y crea una **Cotización en estado
  nuevo `borrador_agente`**. Nunca la envía.
- **F6 — OC/NR del cliente:** el agente lee correos con OC y/o NR (PDF), los
  concilia contra ventas en `esperando_oc_nr`, adjunta los PDF y pasa la venta a
  **`lista_para_facturar`** si cuadra; si no, registra una **discrepancia**.
- **F7 — Bandeja del agente en el ERP:** pantalla donde un humano confirma o
  descarta en 1 clic lo que el agente propuso. Todo queda en un **log auditable**.

**Principio de seguridad:** el agente **PROPONE**, el humano **CONFIRMA**. El agente
jamás toca dinero ni envía nada al cliente (ver §8).

**Dos bloqueos previos a cualquier línea de código (ver §4):**
1. Los archivos subidos hoy viven en **disco efímero de Cloud Run** y se pierden en
   cada deploy. F6 adjunta PDFs → **hay que mover a almacenamiento persistente (GCS)
   primero**. Esto además arregla una pérdida de datos **ya existente** (comprobantes
   de pago, firmas, logos).
2. No existe modelo de **token de API** ni **log de auditoría** central; ambos son
   nuevos y son requisito de la Fase 2.

---

## 2. Alcance

| Paso del workflow | Hoy | Fase 2 |
|---|---|---|
| 1. Llega correo de solicitud de cotización | Manual (Fabrizio) | **Agente propone** Cotización `borrador_agente` (F5) |
| 2. Buscar precios con proveedores | Manual | Agente **sugiere** precio/costo desde historial (F5) |
| 3. Cotización → aceptada → venta + OC | Manual | **Humano** (sin cambios) |
| 4. Cliente envía OC + NR (PDF) | Manual | **Agente concilia y adjunta** (F6) |
| 5. Emitir factura + subir al portal | Manual | **Humano** (sin cambios) |

Fuera de alcance: aprobar/convertir cotizaciones, crear OC, facturar, registrar
pagos, enviar correos. Siguen 100% humanos.

---

## 3. Estado actual del código (evidencia `archivo:línea`)

### 3.1 Autenticación y multitenancy
- `CustomUser` — `backend/apps/authentication/models.py:10-20`. `USERNAME_FIELD='email'`;
  FK `empresa → empresas.Empresa` (`on_delete=SET_NULL`, `related_name='usuarios'`).
- `Empresa` — `backend/apps/empresas/models.py:7-40`. **PK entero** (BigAutoField,
  `settings.py:324`) + campo `uuid` separado (UUIDField, único). Campos `ruc`, `is_active`,
  `modo_inventario`.
- JWT (SimpleJWT) — `backend/config/settings.py:281-295`. Access **6 h**, refresh 7 d,
  HS256, rotación + blacklist (`token_blacklist` app, `settings.py:104`).
- **No existe** ningún modelo `ApiToken`/`ApiKey`/`APIToken` (grep en `backend/apps`
  solo devuelve vistas JWT). → **hay que crearlo.**
- `HasEmpresaPermission` — `backend/apps/core/permissions.py:8-22`: exige
  `request.user.empresa` y compara `obj.empresa_id == request.user.empresa_id`.
- RBAC por rol: `ModulePermission` — `backend/apps/core/permissions.py:24-213`
  (+ `PermisoUsuario` para rol `personalizado`).
- Clases de auth DRF — `settings.py:267-270`: `JWTAuthentication` + `SessionAuthentication`.
  Backend custom `EmailBackend` — `backend/apps/authentication/backends.py:6-19`.
- Aislamiento de tenant por queryset: `get_queryset().filter(empresa=request.user.empresa)`
  y `perform_create(empresa=...)`. Ej.: `guias/views.py:32-54`, `compras/views.py:54-96`,
  `ventas/views.py:70-77`. Middleware custom `TenantMiddleware` — `settings.py:134`.

### 3.2 Archivos subidos (CRÍTICO)
- FileFields/ImageFields existentes (todos `FileSystemStorage`):
  - `compras`: `Compra.comprobante` (`models.py:173`), `PagoCompra.comprobante` (`:559`),
    `ComprobantePago.archivo` (`:600`, `upload_to` dinámico `:20`), `RecepcionCompra.comprobante` (`:851`).
  - `ventas`: `ComprobantePago.archivo` (`models.py:54`, dinámico `:48`), `Venta.comprobante` (`:166`),
    `PagoVenta.comprobante` (`:939`).
  - `empresas`: `logo` (`models.py:13`), `firma_elaborado` (`:14`), `firma_aprobado` (`:15`).
  - `finanzas`: `GastoOperativo.archivo_adjunto` (`models.py:74`). `importador`: `ImportacionExcel.archivo` (`:18`).
    `core`: `Perfil.foto` (`models/perfil.py:8`).
- `MEDIA_URL='/media/'`, `MEDIA_ROOT=BASE_DIR/media` — `settings.py:256-257`. Servido
  **solo en DEBUG** — `config/urls.py:45-47`.
- **Sin almacenamiento en la nube**: no `django-storages`, `google-cloud-storage`, `boto3`,
  `DEFAULT_FILE_STORAGE`/`STORAGES` en `requirements.txt` ni `settings.py`.
- `Dockerfile`: `python:3.11-slim`, sin volúmenes; `MEDIA_ROOT` resuelve a `/app/media`
  (efímero). `.gcloudignore` excluye `backend/media/`.
- PDFs se generan con `reportlab` en memoria (`BytesIO`) y se devuelven como blob, no se
  guardan (ej. `guias/pdf_generator.py:58`, `compras/views.py:632`).
- **¿Archivos en disco efímero que se pierden en cada deploy? → SÍ.**

### 3.3 Modelos de dominio y estados
- `Cotizacion.estado` — `backend/apps/cotizaciones/models.py:62`, choices (`:15-22`):
  `borrador, enviada, aceptada, rechazada, vencida, convertida`. Default `borrador`.
  Líneas: `DetalleCotizacion` (`:253-355`) con FK `producto` (nullable), `cantidad`,
  `precio_unitario`, `costo_unitario` (snapshot interno), `descripcion`, `codigo`.
- `Venta.estado` (pago) — `ventas/models.py:145`, choices (`:80-85`):
  `borrador, pendiente, pagado, anulado`.
- `Venta.estado_operativo` — `ventas/models.py:176`, choices (`:112-120`):
  `pendiente_compra, comprado, recibido, entregado, `**`esperando_oc_nr`**`, facturado, cobrado`.
  **El estado `esperando_oc_nr` YA existe** (`:117`). FK `cotizacion_origen → cotizaciones.Cotizacion`
  (`:131-137`, 1 cotización → N ventas).
- Transición + auditoría: `Venta.cambiar_estado_operativo(nuevo, usuario, nota)` (`:404-428`)
  escribe en `HistorialEstadoVenta` (`:980-1003`: `venta, estado_anterior, estado_nuevo,
  usuario, fecha, nota`). SLA por estado: `SLA_OPERATIVO_DIAS` (`:129-137`), property
  `estado_sla_operativo` (`:384-396`). Dashboard lee estados — `dashboard/views.py:81+`.
- `Cliente` — `ventas/models.py:22-46`: `nombre`, `documento`, `tipo_documento` (dni/ruc),
  `email` (nullable), `telefono`. Único `(empresa, documento)` (`:43`).
- `OrdenCompra.estado` — `compras/models.py:677`, choices (`:636-642`):
  `borrador, enviada, aprobada, rechazada, completada`. FK `venta` (`:663-668`).
- Catálogo compartido `Producto` — `backend/apps/inventario/models/producto.py:7-100`
  (`sku`, `precio_compra`, `precio_venta`). FKs desde `DetalleCotizacion`, `OrdenCompraDetalle`,
  `CompraDetalle`, `DetalleVenta`. → **historial de precios por ítem es factible** cuando
  `producto_id` no es nulo (líneas free-text no tienen historial).

### 3.4 Despliegue, throttling, auditoría
- **WSGI**: `gunicorn config.wsgi:application --worker-class gthread --workers 2 --threads 4`
  — `Dockerfile:100-110`, puerto 8080. `config/asgi.py:16` existe pero no se usa.
- Django **4.2.7**, DRF **3.14.0** (`requirements.txt:4-5`); `asgiref 3.7.2`, `redis 5.0.1`,
  `openai 1.54.0`, `anthropic 0.40.0` (repo-root). **Sin paquetes MCP/ASGI** (`mcp`, `fastmcp`,
  `uvicorn`, `starlette`, `fastapi`).
- Throttling: `DEFAULT_THROTTLE_RATES={'leads':'5/hour'}` (`settings.py:275-277`);
  `UploadRateThrottle`/`PDFRateThrottle` sin rate (`core/throttling.py:4-9`); `LeadAnonThrottle`
  con IP real tras proxy (`leads/throttling.py`).
- **No hay log de auditoría central**: `AuditMixin` (`created_by/updated_by`,
  `core/models/base.py:170-202`), `SoftDeleteModel` (`deleted_by`, `:102-168`), señales de
  negocio por app. Logging solo a consola (`settings.py:344-385`). `HistorialEstadoVenta` audita
  solo transiciones operativas de Venta.
- CORS/CSRF: `CSRF_TRUSTED_ORIGINS` incluye `*.run.app` y dominios soldigem (`settings.py:58-64`);
  `SECURE_PROXY_SSL_HEADER`, `USE_X_FORWARDED_HOST`, `SameSite=None` (`:65-78`). Apps bajo `/api/`
  (`config/urls.py:14-34`).

---

## 4. Riesgos

| # | Riesgo | Severidad | Evidencia | Mitigación |
|---|---|---|---|---|
| R1 | **Pérdida de archivos**: media en disco efímero de Cloud Run; se borra en cada deploy. Afecta YA a comprobantes/firmas/logos y bloquea F6. | **Crítica** | §3.2 | Migrar a **GCS** (`django-storages[google]`) antes de F6. Migración one-time de media actual. |
| R2 | **Sin token de API revocable y acotado**; JWT de 6 h no sirve para una tarea diaria. | Alta | §3.1 | Modelo `ApiToken` nuevo + auth class dedicada (§6, D1). |
| R3 | **Sin log de auditoría** de acciones del agente. | Alta | §3.4 | Modelo `AgenteAccionLog` nuevo; cada tool MCP escribe (§8). |
| R4 | **Doble procesamiento** del mismo correo → cotizaciones/adjuntos duplicados. | Alta | — | Idempotencia por `gmail_message_id` único (§6, F5/F6). |
| R5 | **Fuga de tenant**: el agente ve datos de otra empresa. | Alta | §3.1 | Token ligado a `empresa`; toda tool filtra por esa empresa; nunca aceptar `empresa` como input. |
| R6 | **MCP streaming bajo WSGI**: si se usa SSE, gthread no escala. | Media | §3.4 | Usar Streamable HTTP con **respuesta JSON única** (sin SSE); tools rápidas < timeout 120 s (D2). |
| R7 | **Conciliación errónea** OC↔Venta (monto/ítems) marca lista_para_facturar algo que no corresponde. | Media | — | Umbral monto ±1% + match de ítems; ante duda → discrepancia, nunca cambia estado (F6). |
| R8 | **Ítems free-text** sin `producto_id` no tienen historial de precios → sugerencia vacía. | Baja | §3.3 | Historial solo si `producto_id`; si no, devolver "sin historial" y dejar precio en blanco. |
| R9 | Estado nuevo rompe dashboard/SLA/alertas que enumeran estados. | Baja | §3.3 | Añadir a `SLA_OPERATIVO_DIAS`, filtros y leyendas del dashboard (F6). |

---

## 5. Investigación — respuestas a los 7 puntos

**1. Token de API por empresa/usuario, revocable, alcance limitado. ¿Sirve el JWT?**
No. El JWT actual es corto (6 h), rota y está atado a una sesión de usuario; una tarea
diaria quedaría sin credencial. Se crea **`ApiToken`** (ver §6/D1): token largo,
**revocable**, ligado a `empresa` (y opcionalmente a un usuario "servicio"), con **scope
fijo `mcp:agent`** que solo habilita el endpoint MCP y sus 7 tools. Se guarda **hasheado**
(solo se muestra una vez al crear). Auth class `ApiTokenAuthentication` resuelve
`request.user`/`empresa` y **no** concede sesión ni JWT.

**2. MCP remoto desde Django vs servicio aparte. Recomendación (el más simple).**
**Servir el MCP desde el mismo backend Django** como endpoint HTTP JSON-RPC en `/api/mcp/`
(DRF `APIView`), respondiendo con `application/json` **de una sola vez** (Streamable HTTP
sin SSE). Esto:
- Reutiliza ORM, modelos, auth y filtrado por `empresa` (multi-tenant gratis).
- **No exige reescribir a ASGI** (funciona con el gunicorn WSGI actual); las tools son
  consultas rápidas a BD, muy por debajo del timeout de 120 s.
- Un servicio aparte en Cloud Run duplicaría credenciales de BD, modelos y lógica de tenant.
Multi-tenant: cada `ApiToken` ve **solo su empresa** porque el endpoint inyecta
`empresa = token.empresa` y ninguna tool acepta `empresa` como parámetro.
(Si en el futuro se necesita SSE/streaming real, añadir un worker `uvicorn` solo para esa ruta.)

**3. Archivos — CRÍTICO. ¿Dónde se guardan hoy?**
En **disco efímero** (`FileSystemStorage`, `MEDIA_ROOT=/app/media`), sin volumen; se pierden
en cada deploy (§3.2). **Propuesta:** **Google Cloud Storage** vía `django-storages[google]`
(`DEFAULT_FILE_STORAGE=storages.backends.gcloud.GoogleCloudStorage`, `GS_BUCKET_NAME`,
credencial por Service Account de Cloud Run). Un solo bucket, prefijos por empresa
(`empresa/<id>/...`). Alternativa: Supabase Storage (ya se usa Supabase como BD) vía API S3;
GCS es más natural estando en Cloud Run (SA sin llaves). **Esto es prerequisito de F6 y
arregla R1 para todos los uploads existentes.**

**4. Estados nuevos e impacto.**
- `Cotizacion.estado += 'borrador_agente'` (`cotizaciones/models.py:15-22`).
- `Venta.estado_operativo += 'lista_para_facturar'` (`ventas/models.py:112-120`), lógicamente
  entre `esperando_oc_nr` y `facturado`.
Impacto: añadir a `SLA_OPERATIVO_DIAS` (`:129-137`), a la lista de estados manuales (`:122-125`)
o mantener `lista_para_facturar` como **solo-agente/solo-sistema**; actualizar filtros, leyendas
y conteos del dashboard (`dashboard/views.py`) y cualquier alerta por estado.
`HistorialEstadoVenta` audita la transición automáticamente si se usa `cambiar_estado_operativo`.

**5. Idempotencia.**
Clave = **`gmail_message_id`** (único por mensaje de Gmail). Se guarda en la propuesta creada
y en `AgenteAccionLog`, con **unique constraint**. Las tools de escritura reciben
`gmail_message_id` y, si ya existe, devuelven el registro existente (no crean duplicado).

**6. Herramientas MCP mínimas.** Ver §7 (tabla con input/output/scope).

**7. Seguridad.** Ver §8 (rate limit, auditoría, lista de lo que el agente NO puede hacer).

---

## 6. Diseño por feature

### Modelos nuevos (comunes)

```text
ApiToken (app nueva `agente` o `apitokens`)
  id            BigAuto
  empresa       FK empresas.Empresa (CASCADE)
  nombre        Char(100)         # etiqueta legible ("Agente intake diario")
  token_prefix  Char(12)          # primeros chars, para mostrar en UI
  token_hash    Char(64)          # sha256 del token; el token en claro se muestra 1 vez
  scope         Char(32) default 'mcp:agent'   # fijo; habilita solo el MCP
  created_by    FK CustomUser (SET_NULL, null)
  created_at    DateTime auto
  last_used_at  DateTime null
  expires_at    DateTime null     # opcional
  revoked_at    DateTime null     # revocación = set timestamp
  index (token_prefix); activo = revoked_at is null and (expires_at is null or >now)

AgenteAccionLog (auditoría; app `agente`)
  id            BigAuto
  empresa       FK empresas.Empresa
  token         FK ApiToken (SET_NULL, null)
  tool          Char(40)          # buscar_cliente, crear_cotizacion_borrador, ...
  gmail_message_id Char(120) null index
  input_resumen JSON              # entrada saneada (sin PII innecesaria)
  resultado     JSON              # id creado / match / discrepancia
  ok            Bool
  created_at    DateTime auto index

PropuestaAgente (bandeja F7; app `agente`)
  id            BigAuto
  empresa       FK empresas.Empresa
  tipo          Char(20)          # 'cotizacion' | 'oc_nr' | 'discrepancia'
  estado        Char(20)          # 'pendiente' | 'confirmada' | 'descartada'
  gmail_message_id Char(120) unique   # idempotencia dura
  remitente     Char(254); asunto Char(300); fecha_correo DateTime
  cotizacion    FK cotizaciones.Cotizacion (null)   # si tipo=cotizacion
  venta         FK ventas.Venta (null)              # si tipo=oc_nr/discrepancia
  detalle       JSON              # resumen para la tarjeta de la bandeja
  creado_at     DateTime auto; resuelto_por FK CustomUser (null); resuelto_at DateTime null

DocumentoVenta (adjuntos OC/NR; app `ventas`)
  id            BigAuto
  venta         FK ventas.Venta (CASCADE, related_name='documentos')
  tipo          Char(4)           # 'oc' | 'nr'
  archivo       FileField(upload_to='ventas/oc_nr/<empresa>/<venta>/')  # → GCS
  numero_oc     Char(60) null; monto Decimal null; moneda Char(3) null
  gmail_message_id Char(120) index
  subido_por    Char(10) default 'agente'   # 'agente' | 'humano'
  created_at    DateTime auto
```

### F5 — Intake de solicitudes
- **Qué hace:** el agente detecta correos de solicitud de cotización, extrae cliente,
  contacto, email, ítems y cantidades; crea `Cotizacion` en **`borrador_agente`** con origen
  (gmail id, remitente, asunto, fecha); sugiere precio/costo desde historial. **Nunca envía.**
- **Modelos/migraciones:**
  - Añadir `'borrador_agente'` a `Cotizacion.ESTADO_CHOICES` (`cotizaciones/models.py:15-22`).
  - Campo `origen_gmail_message_id Char(120) null unique` en `Cotizacion` (idempotencia) **o**
    vía `PropuestaAgente.gmail_message_id` (recomendado: en `PropuestaAgente` para no tocar
    el modelo de dominio de más). Migración additive (sin backfill).
- **MCP tools:** `buscar_cliente`, `historial_precios_item`, `crear_cotizacion_borrador`.
- **Endpoints (confirmación humana, F7):**
  `POST /api/agente/propuestas/<id>/confirmar/` → promueve `borrador_agente → borrador` (queda
  como cotización normal editable); `POST .../descartar/` → marca descartada (y opcionalmente
  borra la cotización borrador). Ambos escriben `AgenteAccionLog`/`resuelto_por`.
- **UI:** tab "Cotizaciones propuestas" en la bandeja (F7).

### F6 — OC/NR del cliente
- **Qué hace:** detecta correos con OC/NR (PDF), extrae número OC, monto, moneda, ítems; busca
  la venta en **`esperando_oc_nr`** que coincide (cliente, monto **±1%**, ítems). Si coincide:
  **adjunta los PDF** (`DocumentoVenta` → GCS) y pasa la venta a **`lista_para_facturar`**. Si no
  coincide o difiere el monto: **registra discrepancia**, sin cambiar estados.
- **Prerequisito:** R1 resuelto (GCS) — sin esto, adjuntar PDFs es inútil.
- **Modelos/migraciones:**
  - Añadir `'lista_para_facturar'` a `Venta.ESTADO_OPERATIVO_CHOICES` (`ventas/models.py:112-120`),
    a `SLA_OPERATIVO_DIAS` (`:129-137`) y, si aplica, a estados manuales (`:122-125`).
  - Crear `DocumentoVenta`. Reusar `Venta.cambiar_estado_operativo()` (`:404-428`) para que
    `HistorialEstadoVenta` audite la transición.
- **MCP tools:** `ventas_esperando_oc_nr`, `adjuntar_documento_venta`, `registrar_discrepancia`.
- **Conciliación:** monto dentro de ±1%; ítems por `producto_id` (o descripción si free-text);
  si varias ventas candidatas → discrepancia "ambigua". Nunca cambia el estado de **pago**.
- **UI:** tabs "OC/NR asociadas" y "Discrepancias" en la bandeja (F7).

### F7 — Bandeja del agente
- **Qué hace:** pantalla `/app/agente` (o `/app/bandeja-agente`) con 3 tabs: Cotizaciones
  `borrador_agente`, OC/NR asociadas (ventas `lista_para_facturar` con sus `DocumentoVenta`),
  Discrepancias. Cada tarjeta muestra origen (correo), lo extraído y botones **Confirmar** /
  **Descartar** (1 clic). Cada acción → `AgenteAccionLog`.
- **Backend:** `GET /api/agente/propuestas/?tipo=&estado=pendiente` (filtrado por empresa),
  `POST .../confirmar/`, `POST .../descartar/`. ViewSet con `IsAuthenticated + HasEmpresaPermission`
  (usuarios, no el token del agente).
- **Frontend (patrón del repo):** servicio `frontend/src/services/agenteService.js`,
  componentes en `frontend/src/components/agente/`, ruta lazy bajo `/app/`. Lista con
  `PAGE_SIZE=20`; menú ⋮ para acciones; `stopPropagation()` en filas clickeables.

---

## 7. Herramientas MCP (contrato)

Todas: **scope por `token.empresa`** (nunca aceptan `empresa` como input), **registran en
`AgenteAccionLog`**, y clasificadas R=lectura / W=escritura segura (sin dinero/envío).

| Tool | Tipo | Input | Output |
|---|---|---|---|
| `buscar_cliente` | R | `{query}` (documento, nombre o email) | `[{id, nombre, documento, email, telefono}]` (0..n) |
| `historial_precios_item` | R | `{producto_id?}` o `{sku?}` o `{descripcion?}` | `{producto_id, ultimos: [{fuente:'cotizacion'|'compra', fecha, precio, costo?, moneda}], sugerido_precio, sugerido_costo}` o `{sin_historial:true}` |
| `ventas_esperando_oc_nr` | R | `{}` | `[{venta_id, numero, cliente, monto, moneda, items:[{producto_id?, descripcion, cantidad, precio}]}]` |
| `crear_cotizacion_borrador` | W | `{cliente:{id?|nombre,documento?,email?}, items:[{producto_id?|descripcion, cantidad, precio?}], origen:{gmail_message_id, remitente, asunto, fecha}}` | `{cotizacion_id, estado:'borrador_agente', creado:true|false, propuesta_id}` (idempotente por `gmail_message_id`) |
| `adjuntar_documento_venta` | W | `{venta_id, tipo:'oc'|'nr', archivo:{nombre, content_base64|url}, numero_oc?, monto?, moneda?, origen:{gmail_message_id,...}}` | `{documento_id, venta_estado_operativo, concilio:true|false}` (si concilia → `lista_para_facturar`) |
| `registrar_discrepancia` | W | `{venta_id?, tipo:'monto'|'ambigua'|'sin_match', detalle, origen:{gmail_message_id,...}}` | `{propuesta_id, estado:'pendiente'}` |
| `listar_propuestas_pendientes` | R | `{tipo?}` | `[{propuesta_id, tipo, estado, resumen, gmail_message_id, creado_at}]` |

Métodos MCP soportados por el endpoint: `initialize`, `tools/list`, `tools/call`. Cualquier
otro → error JSON-RPC. (El archivo en `adjuntar_documento_venta` puede ir base64 inline para
PDFs chicos o como URL de Gmail que el backend descarga; definir límite de tamaño.)

---

## 8. Seguridad

- **Rate limit por token:** nuevo scope `mcp` en `DEFAULT_THROTTLE_RATES` (p. ej. `'60/min'`
  y/o `'600/hour'`) con `SimpleRateThrottle` cuya key = `token.id` (no IP; el agente sale de
  IPs de Anthropic). Es una tarea diaria → límites bajos sobran.
- **Auditoría:** cada tool escribe `AgenteAccionLog` (empresa, token, tool, gmail_message_id,
  input saneado, resultado, ok, timestamp). `last_used_at` del token se actualiza por request.
- **Lo que el agente NO puede hacer** (y cómo se garantiza):
  aprobar cotizaciones, **convertir a venta**, crear **OC**, **facturar**, registrar/cambiar
  **pagos**, cambiar el **estado de pago**, **borrar** nada, **enviar correos**.
  Garantías: (a) el `scope='mcp:agent'` solo habilita `/api/mcp/` y sus 7 tools; (b) ninguna
  de las 7 tools ejecuta esas acciones; (c) el token no concede sesión ni JWT; (d) las tools de
  escritura solo: crean cotización en `borrador_agente`, crean `DocumentoVenta` + ponen
  `lista_para_facturar`, o crean discrepancia/log. Todo lo demás pasa por humano en la bandeja (F7).
- **Tenant:** `empresa` siempre del token; input `empresa` se ignora/rechaza.

---

## 9. Decisiones abiertas (máx. 5, con recomendación)

**D1 — Modelo de token: `ApiToken` nuevo vs reusar DRF TokenAuth vs OAuth.**
*Recomendación:* **`ApiToken` propio** (hasheado, revocable, ligado a empresa, scope fijo).
DRF `authtoken` es 1 token por usuario sin scope ni expiración; OAuth client-credentials es más
robusto pero más obra. Sub-nota: claude.ai/Cowork como **custom connector** suele pedir OAuth
2.1 **o** bearer token; si exige OAuth, envolver `ApiToken` con un shim mínimo de
client-credentials. *Impacto si se elige mal:* token no revocable o fuga de alcance.

**D2 — Transporte MCP: JSON único bajo WSGI vs SSE/ASGI.**
*Recomendación:* **JSON único (Streamable HTTP sin SSE) en el Django WSGI actual.** Tools
rápidas, sin reescritura a ASGI. Reevaluar solo si se necesitan respuestas en streaming.
*Impacto si se elige mal:* complejidad de infra (uvicorn, otro proceso) sin beneficio hoy.

**D3 — Almacenamiento persistente: GCS vs Supabase Storage.**
*Recomendación:* **GCS con `django-storages[google]`** (Service Account de Cloud Run, sin llaves).
Supabase Storage es viable (ya hay Supabase) pero mete credenciales S3. Migración one-time de la
media existente. *Impacto si se elige mal:* re-trabajo de storage y R1 sigue abierto.

**D4 — Dónde vive la idempotencia y el nuevo estado de Venta.**
*Recomendación:* idempotencia en **`PropuestaAgente.gmail_message_id` (unique)**, no en los
modelos de dominio; `lista_para_facturar` como estado **solo-sistema** (no editable a mano) para
no ensuciar el flujo manual. *Impacto si se elige mal:* duplicados o un estado que los usuarios
cambian por error.

**D5 — Identidad del actor del agente: usuario "servicio" vs solo token.**
*Recomendación:* **token sin usuario** + `AgenteAccionLog.actor='agente'`; `HistorialEstadoVenta.usuario`
puede quedar null o apuntar a un `CustomUser` "Agente" por empresa (opcional, mejora trazabilidad en
pantallas que muestran "usuario"). *Impacto si se elige mal:* historiales con "usuario desconocido".

---

## 10. Impacto vs complejidad

| Entregable | Impacto | Complejidad | Notas |
|---|---|---|---|
| **GCS storage (R1)** | **Alto** (desbloquea F6 + arregla pérdida actual) | Media | `django-storages[google]`, settings, SA, migración media |
| `ApiToken` + auth class + throttle | Alto (habilita todo el MCP) | Baja-Media | modelo + 1 auth class + 1 throttle |
| Endpoint `/api/mcp/` (JSON-RPC, 7 tools) | Alto | Media | 1 APIView + dispatch + 7 funciones sobre ORM existente |
| Estados nuevos (`borrador_agente`, `lista_para_facturar`) | Medio | Baja | choices additive + SLA + dashboard |
| `AgenteAccionLog` + `PropuestaAgente` + `DocumentoVenta` | Alto (auditoría + bandeja) | Media | 3 modelos + migraciones |
| F7 bandeja (back + front) | Alto (UX de confirmación) | Media | ViewSet + 1 pantalla React patrón repo |
| Prompt + tarea programada | Alto (orquesta todo) | Baja | config en claude.ai/Cowork |

**Orden sugerido:** R1 (GCS) → ApiToken/auth → endpoint MCP + tools de lectura → estados +
tools de escritura → `PropuestaAgente`/`AgenteAccionLog`/`DocumentoVenta` → F7 bandeja →
prompt/tarea programada.

---

## 11. Prompt de la tarea programada (ejecución diaria del agente)

> **Sistema/contexto del agente** (claude.ai o Cowork, con Gmail + MCP "ERP Soldigem" conectados;
> corre cada mañana). Pegar como instrucción de la tarea:

```
Eres el asistente de intake de Soldigem. Cada mañana revisas el correo y PROPONES
trabajo en el ERP; NUNCA envías nada al cliente, NUNCA apruebas, conviertes, facturas,
registras pagos ni borras. Solo usas las herramientas del MCP "ERP Soldigem".

Procedimiento:
1. Lista los correos no leídos (o de las últimas 24 h) de la bandeja.
2. Clasifica cada correo en: (a) SOLICITUD DE COTIZACIÓN, (b) OC/NR DEL CLIENTE
   (trae PDF de orden de compra y/o nota de recepción), (c) OTRO (ignorar).
3. Idempotencia: por cada correo usa su gmail_message_id. Antes de crear nada, no
   repitas correos ya procesados (las tools son idempotentes por gmail_message_id;
   si una devuelve "ya existe", continúa sin duplicar).

Para (a) SOLICITUD DE COTIZACIÓN:
   - Extrae: cliente (nombre/razón social y RUC/DNI si aparece), email y contacto,
     y la lista de ítems con cantidades (y precio si el cliente lo indica).
   - Llama buscar_cliente para ubicar al cliente; si no existe, incluye sus datos
     en crear_cotizacion_borrador (no lo crees aparte).
   - Para cada ítem, llama historial_precios_item; si hay historial, usa el precio/
     costo sugerido; si no, deja el precio en blanco (lo pondrá el humano).
   - Llama crear_cotizacion_borrador con los ítems y origen={gmail_message_id,
     remitente, asunto, fecha}. Queda en estado borrador_agente. No la envíes.

Para (b) OC/NR DEL CLIENTE:
   - Llama ventas_esperando_oc_nr para ver las ventas que esperan OC/NR.
   - Extrae del PDF: número de OC, monto, moneda e ítems.
   - Busca la venta que coincide por cliente, monto (±1%) e ítems.
     - Si hay UNA coincidencia clara: llama adjuntar_documento_venta por cada PDF
       (tipo 'oc' o 'nr') con el origen del correo. Si concilia, la venta pasa a
       lista_para_facturar.
     - Si no hay match, el monto difiere, o hay varias candidatas: llama
       registrar_discrepancia con el detalle. NO cambies ningún estado.

4. Al terminar, llama listar_propuestas_pendientes y entrégame un resumen corto:
   cuántas cotizaciones borrador creaste, cuántas OC/NR adjuntaste/conciliaste y
   cuántas discrepancias quedaron para revisión humana. No tomes ninguna otra acción.
```

---

## 12. Estado

- **STATUS:** DONE — spec de Fase 2 entregada en `FASE2_SPEC.md`, sin tocar código.
- **Prerequisitos duros antes de implementar:** R1 (GCS) y R2 (ApiToken).
- **Pendiente del usuario:** decidir D1–D5 (§9).
