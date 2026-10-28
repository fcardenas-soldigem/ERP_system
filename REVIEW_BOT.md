# Revisión adversarial — fix/review-movil + feat/agente-canales

> Informe íntegro del subagente revisor con contexto limpio (2026-10-27).
> Al final: qué se corrigió a raíz del informe y en qué commit.

## Alcance y método (2 líneas)
Revisión solo-lectura del diff `git diff main...feat/agente-canales` (20 commits: roles 0.1, cookies 0.3, QW1-QW10 y el bot de canales B1), leyendo completos `backend/apps/canales/*`, `core/permissions.py`, serializers de cotizaciones/ventas/finanzas y los viewsets tocados, más barrido de `permission_classes` en todo `backend/apps/` y scan de secretos en el diff.
Foco: escrituras sin chequeo de rol, acciones del bot sin confirmación y fugas entre empresas; verificado contra el código, no contra los comentarios.

## Hallazgos

| # | Severidad | Clase | Archivo:línea | Descripción | Cómo explotarlo | Corrección sugerida |
|---|-----------|-------|---------------|-------------|-----------------|---------------------|
| 1 | alta | rol | `backend/apps/importador/views.py:37,109,138,162,197,212` | Todo `/api/importador/` (upload, preview, **ejecutar**) va solo con `IsAuthenticated`; `ImportService` crea `Producto`, `MovimientoInventario`, clientes, etc. (`importador/services.py:1178,1210,1321`) | Un usuario `solo_lectura` hace POST `/api/importador/upload/` + `/ejecutar/` y crea/pisa inventario y clientes masivamente, saltándose `RolEscritura` | Añadir `RolEscritura` a las 5 vistas del importador |
| 2 | alta | rol | `backend/apps/core/views.py:23,45,61` y `backend/apps/empresas/views.py:10,39,62` | `EmpresaViewSet` (×2; update/PATCH y `upload_logo`/`delete_logo` siguen abiertos), `UsuarioViewSet` y `PerfilViewSet` son `ModelViewSet` con solo `IsAuthenticated` | `solo_lectura` hace PATCH `/api/empresas/<id>/` (razón social, RUC, logo que sale en los PDF de cotización) o crea/edita `Usuario`/`Perfil` vía `/api/core/` | `RolEscritura` en los 5 viewsets (create/destroy de empresa ya están en 405, pero update y las actions no) |
| 3 | alta | confirmación | `backend/apps/canales/nucleo/orquestador.py:338-376` | Confirmación sin bloqueo: `borrador.estado != 'pendiente'` es read-then-act, sin `select_for_update` ni transacción; el webhook deduplica `update_id`, pero **cada pulsación del botón es un update distinto** | Pulsar «✅ Confirmar» dos veces rápido (o reintento de Telegram del callback): dos hilos pasan el chequeo y `confirmar_borrador` corre dos veces → cotización duplicada o **cobro doble** (si el monto era parcial, `PagoVenta.clean` no frena el segundo) | `select_for_update()` + `transaction.atomic()`, o `filter(estado='pendiente').update(estado='confirmado')` condicional antes de ejecutar |
| 4 | media | tenant | `backend/apps/canales/nucleo/servicios.py:256-262` + `backend/apps/cotizaciones/serializers.py:72-100` | `confirmar_borrador` usa `CotizacionSerializer`, `ModelSerializer` plano (NO `EmpresaScopedModelSerializer`): `cliente`, `venta`, `estado`, `fecha_aceptacion`, `usuario_creador` son escribibles sin scope de empresa | Hoy el payload lo arma el servidor (scoped) → **no explotable directamente**; pero cualquier futuro camino que toque `payload` (edición, prompt injection sobre el intérprete, nuevo canal) colaría un `cliente`/`venta` de otra empresa sin error | Usar `CotizacionCreateSerializer` (scoped; es el que ya usa la API web) o re-validar `cliente.empresa_id == usuario.empresa_id` |
| 5 | media | confirmación | `backend/apps/canales/nucleo/orquestador.py:320-333` | `cot:<id>:enviada` escribe `Cotizacion.estado='enviada'` **sin borrador, sin validar el estado actual y sin expiración del botón**; `callback_data` es forjable por un cliente Telegram modificado (Telegram NO verifica que corresponda a un botón real) | Un usuario vinculado (operador) manda `callback_query` con `cot:<id>:enviada` para cualquier id de SU empresa: una cotización `aceptada`/`convertida`/`rechazada` retrocede a `enviada` sin historial. Acotado a empresa y rol, pero es un salto de estado no validado | Permitir la transición solo desde `borrador`/`enviada` y atar el callback a un borrador confirmado reciente |
| 6 | media | rol (condicional) | `backend/apps/ai_assistant/services/perfiles.py:59-61`, `backend/config/settings.py:425` | Las tools de escritura del asistente web (`/api/ai/`) se activan con `LLM_WRITE_TOOLS` **global**, sin chequeo de rol por usuario (no hay `solo_lectura` en todo `ai_assistant`) | Hoy el flag está en `false`; el día que se active, un `solo_lectura` escribe vía chat (`crear_venta`…) saltándose 0.1 | Chequear `usuario.rol in ('admin','operador')` al exponer/ejecutar tools con `escritura=True` (como ya hace el orquestador de canales) |
| 7 | media | otro (bug) | `backend/apps/canales/nucleo/orquestador.py:420-427` + `backend/apps/ventas/models.py:961-971` | Adjuntar foto hace `pago.save(update_fields=['comprobante'])`, que ejecuta `clean()`: para un cobro que **saldó** la venta, `monto > get_saldo_pendiente()` (200 > 0) → `ValidationError` → excepción tragada en `procesar_update` → **silencio total**. La asignación directa a `.name` además salta `validate_upload` y `UploadToEmpresa`, y pisa un comprobante previo sin aviso. No hay NINGÚN test de `_manejar_foto` | Flujo normal del piloto: «registra el cobro completo de F-001» + foto → el bot nunca responde y el comprobante no se adjunta | Adjuntar con `queryset.update(comprobante=ruta)` o saltar `clean()` en ese save; validar contenido/extensión; test del camino foto |
| 8 | media | rol | `backend/apps/agente/token_views.py:19` | Crear/revocar tokens MCP solo exige `IsAuthenticated+HasEmpresaPermission`, sin `RolEscritura` | `solo_lectura` crea un `ApiToken` y accede por `/api/mcp/`; las tools son de lectura (`agente/tools.py:1`), así que impacto bajo, pero es un POST de negocio sin chequeo de rol | Añadir `RolEscritura` |
| 9 | baja | tenant (latente) | `backend/apps/ventas/views.py:45-52` | `VentaListCreateView` y `VentaRetrieveUpdateDestroyView` con `queryset=Venta.objects.all()`, sin permisos propios ni filtro empresa. **Verifiqué que NO están ruteadas** (`ventas/urls.py`) | No explotable hoy; una línea de `path()` futura expone CRUD cross-tenant de ventas | Borrarlas (código muerto peligroso) |
| 10 | baja | otro | `backend/apps/canales/nucleo/orquestador.py:168,290-299` | `/start CODIGO` se procesa ANTES de `_excede_limites` y los chats no vinculados no tienen ningún límite | Cualquier usuario de Telegram martilla `/start XXXXXXXX` (fuerza bruta del código: 32⁸ ≈ 1.1e12, impráctico, pero sin tope de intentos); cada mensaje no vinculado genera consulta a BD + `sendMessage` sin límite → ruido/DoS barato | Rate-limit por `chat_id` también para no vinculados y `/start` |
| 11 | baja | otro | `backend/apps/canales/nucleo/orquestador.py:195-240,64-80` | El texto va íntegro al LLM sin tope de longitud y los contadores `get_or_set`+`incr` no son atómicos entre hilos | Mensajes largos repetidos consumen presupuesto de tokens antes de que el contador (post-hoc) frene; carreras subcuentan el 60/h | Truncar `texto` (~1000 chars) antes de `interpretar`; incrementos atómicos (Redis) |
| 12 | baja | otro | `backend/apps/canales/nucleo/orquestador.py:322,338` + `vistas.py:77` | `partes[1]` no numérico (`cot:abc:enviada`, `b:x:ok`) → `ValueError` en `filter(pk=...)` → excepción tragada → silencio al usuario; además `UpdateProcesado` se marca ANTES de procesar: si el hilo daemon muere (deploy/reinicio de gunicorn), el update se pierde para siempre (Telegram ya recibió 200) | Callback forjado con id basura: bot mudo y log sucio; mensajes perdidos en reinicios | `partes[1].isdigit()`; considerar marcar procesado al final o cola persistente post-piloto |
| 13 | baja | otro | `backend/apps/canales/telegram.py:57` + `orquestador.py:137,173` | Respuestas con `parse_mode='HTML'` interpolando nombres de cliente/venta/usuario sin escapar | Un cliente llamado `<b>Acme` (dato propio) rompe el `sendMessage` (400 de Telegram) → bot mudo para esa consulta. No es XSS, es denegación boba | `django.utils.html.escape()` sobre todo dato de BD interpolado |

**#1 — Importador sin rol.** `UploadView`/vista de ejecutar llevan `permission_classes = [IsAuthenticated]` (`importador/views.py:37` etc.) y `ImportService(imp, request.user)` (`views.py:162`) termina en `Producto.objects.create(...)` (`services.py:1321`) y `MovimientoInventario.objects.create(...)` (`services.py:1178,1210`). `RolEscritura` se añadió en este diff a ventas/compras/inventario/etc., pero este prefijo —que escribe en los mismos modelos de inventario— quedó fuera. Sí filtra por empresa (`_get_empresa`), así que es bypass de rol, no de tenant.

**#2 — core/empresas sin rol.** En `core/views.py:23-61` tres `ModelViewSet` completos (Empresa, Usuario, Perfil) solo piden `IsAuthenticated`; `empresas/views.py` bloquea create/destroy con 405 pero deja `update`/`partial_update` y `upload_logo` (POST, `views.py:39`) abiertos. Un `solo_lectura` puede cambiar RUC/razón social/logo de su empresa, que sale en los PDF que el bot comparte con clientes finales.

**#3 — Doble confirmación.** `orquestador.py:338-343`: `borrador = BorradorAgente.objects.filter(pk=..., usuario=usuario, empresa=usuario.empresa).first()` seguido de `if borrador.estado != 'pendiente'` y en `:368` `servicios.confirmar_borrador(borrador)` sin transacción ni lock. Dos callbacks (update_id distintos → la idempotencia del webhook NO aplica) en dos hilos daemon (`vistas.py:44`) pasan ambos el chequeo. Para cobros parciales, `PagoVenta.clean()` (`ventas/models.py:961`) compara contra el saldo ya reducido y deja pasar el segundo pago → dinero registrado dos veces.

**#5 — cot:enviada.** `orquestador.py:329-330` hace `cot.estado = 'enviada'; cot.save(update_fields=['estado'])` sin mirar el estado actual (choices incluyen `aceptada`/`convertida`, `cotizaciones/models.py:15-22`). Telegram no verifica que el `callback_data` corresponda a un botón real del mensaje. Correctamente acotado a `empresa=usuario.empresa` y rol, pero es la única escritura del bot sin `BorradorAgente` y sin validación de transición.

## Qué verifiqué y está bien

- **Callback `b:` valida usuario Y empresa**: `filter(pk=..., usuario=usuario, empresa=usuario.empresa)` en `orquestador.py:338`; borrador ajeno → «Ese borrador ya no existe» (cubierto en `canales/tests/test_borradores.py`).
- **Rol en el bot, en cada punto de escritura**: preparaciones (`orquestador.py:262-264`), confirmar `ok` re-chequea (`:363-365`), `cot:enviada` (`:326-327`), foto (`:409-410`). Y `rol` es `read_only` en el perfil (`authentication/serializers.py:42`) → sin auto-escalada vía PATCH.
- **Tenant en TODOS los servicios del núcleo**: `buscar_cliente` (`servicios.py:36`), `buscar_producto` (`:50`), `_resolver_venta` (`:65`), `ventas_detenidas` (`:115`), `preparar_cotizacion` cliente y productos (`:134,138,148`), `confirmar_borrador` cobro/estado con `Venta.objects.get(pk=..., empresa=usuario.empresa)` (`:267,284`). La empresa nunca viene del mensaje: sale de `VinculacionTelegram → usuario.empresa` (`orquestador.py:164-175`).
- **PDF firmado**: firma solo del servidor (`TimestampSigner(salt='canales.pdf')`, `orquestador.py:119`), caduca a 72 h (`vistas.py:28,129`); `Cotizacion.objects.get(pk=...)` sin empresa es aceptable porque el pk viene de la firma (inforjable sin `SECRET_KEY`). Es un **bearer link por diseño** (se comparte con el cliente final): quien tenga el link ve el PDF — asumido en B7; conviene dejarlo escrito en la doc del piloto.
- **Webhook**: cabecera secreta obligatoria con 403, incluso si `TG_WEBHOOK_SECRET` está vacío (`vistas.py:67`); idempotencia por `UniqueConstraint (canal, update_id)` (`models.py:72`); payloads no-dict o sin `update_id` ignorados con 200; con tests (`tests/test_webhook.py`).
- **Vinculación**: código `secrets.choice`, 8 chars/alfabeto 32 (`models.py:17-20`), vence en 10 min, un chat ↔ un usuario (OneToOne + liberación del chat previo, `orquestador.py:301`), `/desvincular` funciona.
- **Re-validación al confirmar**: cobro re-chequea saldo (`servicios.py:270-271`) + `PagoVenta.clean()` en BD; `Venta.cambiar_estado_operativo` veta `cobrado` y estados inválidos (`ventas/models.py:412-418`) además del veto en `servicios.py:228`.
- **Serializers scoped**: `DetalleCotizacionSerializer` y `CotizacionCreateSerializer` heredan de `EmpresaScopedModelSerializer` (`cotizaciones/serializers.py:10,189`); la API web usa el scoped para create/update (`cotizaciones/views.py:85-90`); finanzas scoped (`finanzas/serializers.py:40,58`).
- **RolEscritura desplegado** en ventas, compras, cotizaciones, inventario (incl. carga masiva `@api_view`), finanzas, guías, servicios y producción (diff verificado), con suite `core/tests/test_roles_escritura.py`.
- **Sin secretos en el diff**: `TG_BOT_TOKEN`/`TG_WEBHOOK_SECRET` solo desde entorno (`settings.py:88-92`); valores de tests son dummies obvios.
- **Fotos por empresa**: ruta `canales/empresa_{id}/uuid.jpg` (`orquestador.py:412`) y pago buscado con `venta__empresa=usuario.empresa` (`:422`).
- **MCP (`/api/mcp/`)**: solo herramientas de LECTURA (`agente/tools.py:1`), acotadas a `request.empresa`, con throttle y log.

## Veredicto

**Apto para piloto de Telegram CON condiciones.** El núcleo del bot está bien diseñado: tenant por vinculación (nunca por mensaje), rol chequeado en cada punto de escritura, patrón borrador→confirmar respetado en los tres tipos de documento. Pero antes de usuarios reales:

1. **Obligatorio antes del piloto**: cerrar la carrera de doble confirmación (#3 — es dinero) y arreglar el camino de la foto (#7 — falla en el caso más común del flujo de cobro que se va a demostrar).
2. **Obligatorio antes de entregar cuentas `solo_lectura`**: #1 (importador) y #2 (core/empresas) — hoy el rol `solo_lectura` es papel mojado fuera de los prefijos parchados, y 0.1 se vendió como cerrado.
3. **Recomendado la misma semana**: serializer scoped en `confirmar_borrador` (#4), validación de transición en `cot:enviada` (#5) e `isdigit()` en callbacks (#12).
4. **A verificar antes de activar `LLM_WRITE_TOOLS`** (#6): no hay chequeo de rol en el asistente web.

---

## Anexo (post-revisión): qué se corrigió y dónde

| Hallazgo | Estado | Commit |
|---|---|---|
| #1 importador sin rol | **Corregido** (RolEscritura en las 5 vistas) | 4856dd2 |
| #2 core/empresas sin rol | **Corregido** (5 viewsets) | 4856dd2 |
| #3 doble confirmación | **Corregido** (select_for_update + transacción; test de doble toque) | 66e881c |
| #4 serializer sin scope | **Mitigado** (re-validación de cliente/productos contra la empresa antes de serializar) | 66e881c |
| #5 cot:enviada sin validar transición | **Corregido** (solo desde borrador/enviada; test) | 66e881c |
| #6 LLM_WRITE_TOOLS sin rol | **Pendiente documentado** (el flag sigue en false; condición en ENTREGA.md antes de activarlo) | — |
| #7 camino de la foto roto | **Corregido** (update() sin clean(), sin pisar comprobantes, tope 10 MB; además documento_id nunca se persistía — corregido; 3 tests nuevos) | 66e881c |
| #8 tokens MCP sin rol | **Corregido** | 4856dd2 |
| #9 vistas muertas sin tenant | **Corregido** (eliminadas) | 4856dd2 |
| #10 sin límite para no vinculados | **Corregido** (tope por chat_id antes de cualquier trabajo) | 66e881c |
| #11 texto sin tope / contadores no atómicos | **Parcial**: texto truncado a 1000 chars; la atomicidad fina de contadores queda para Redis en prod (documentado) | 66e881c |
| #12 callbacks forjados | **Corregido** (isdigit + respuesta fija); «marcar procesado al final» queda como mejora post-piloto (cola) | 66e881c |
| #13 HTML sin escapar | **Corregido** (escape() en todos los datos interpolados; test) | 66e881c |

El router-walk de roles ahora cubre también api/importador, api/core,
api/empresas y api/agente (login/refresh/verify excluidos por diseño).
Suite tras las correcciones: backend 283 OK en Postgres (36 de canales),
vitest 8 OK, build OK.
