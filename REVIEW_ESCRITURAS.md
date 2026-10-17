# Revisión de seguridad — rama `sec/escrituras-cruzadas` (fugas entre empresas en escrituras)

Revisor independiente (contexto limpio). Base: `main`. Commits revisados: `fe840af`, `a86c90d`, `2b72631`, `d5467a0`, `eed12b6`.
Alcance: diff completo (`git diff main...HEAD`), serializers y vistas de todas las apps, las 57 rutas excluidas del router-walk, eliminación de `TenantMiddleware`, tests nuevos.
Método: lectura de código + ejecución de los tests del autor + 10 pruebas propias (`rev_checks.py`, fuera del repo) contra Postgres local `localhost:5433` (BD de test `test_erp_rev*`; `.env.local` apunta a localhost, no a Supabase) + introspección automática de todos los serializers (FKs escribibles cuyo modelo destino no tiene `empresa`).

---

## 1. Resumen y veredicto

**Veredicto: la rama es mergeable y mejora claramente el aislamiento; NO es suficiente por sí sola para abrir el sistema al primer cliente externo.** Antes de ese hito hay que cerrar un hallazgo P1 que está fuera del diff (asistente IA por `thread_id` sin verificación de tenant) y decidir sobre dos regresiones funcionales preexistentes que el diff deja intactas.

- Todos los fixes del autor cierran la fuga que dicen cerrar; no encontré variantes abiertas (PUT vs PATCH, ruta anidada vs plana, clave alterna) en ninguno de ellos. Verificado con el router-walk (172/229 rutas, 286 peticiones, 0 fugas, 0 5xx) y con pruebas puntuales propias.
- La eliminación de `TenantMiddleware` es correcta y segura: no hay código ni SQL en el repo que consuma `app.current_empresa`; las políticas RLS documentadas como ejecutadas en Supabase son *fail-open* (`OR get_current_empresa_id() IS NULL`), así que no cambia el comportamiento en producción (ver §5).
- **P1 (fuera del diff, confirmado ejecutando):** `GET /api/ai/threads/<thread_id>/messages/` y `GET|POST /api/ai/threads-tools/<thread_id>/messages/` operan sobre un `thread_id` de OpenAI sin comprobar que la conversación pertenezca al usuario/empresa. Un usuario de A que conozca el `thread_id` de B lee la conversación completa de B y puede escribir en ella.
- **P2 funcionales (preexistentes, no introducidas por la rama):** `PATCH /api/ventas/{id}/` sin `detalles` borra todos los detalles de la venta (200 OK); el detalle de `Factura`/`PagoVenta`/`RecepcionCompra`/`PagoCompra` responde 403 para el propio tenant; `POST /api/ventas/ordenes/` devuelve 500 siempre.
- Tests: el router-walk es sólido (instantánea de B por hash + savepoint por petición). Debilidades menores: la clasificación FK/OTRO es solo informativa (sin assert) y el umbral de cobertura (`>= 60`) es laxo; la exclusión "sin campos FK en el body" oculta una ruta que da 500 para todos.

---

## 2. Hallazgos por severidad

### P1

**[P1] (confianza: 9/10) `backend/apps/ai_assistant/views.py:355-372` — lectura de la conversación de otra empresa por `thread_id` sin comprobación de tenant.**

```python
def get(self, request, thread_id):            # MessageView
    client = get_openai_client()
    messages = client.beta.threads.messages.list(thread_id=thread_id)   # línea 361
```
El `POST` de la misma vista sí comprueba `Conversation.objects.get(thread_id=thread_id, usuario=request.user)` (línea 339); el `GET` no. Lo mismo en `MessageViewWithTools.get` (línea 622: `openai_service.get_thread_messages(thread_id)`) y `MessageViewWithTools.post` (línea 603: `send_message_with_tools(thread_id=thread_id, content=..., user=request.user)`), que además escribe el mensaje de A en el hilo de B y crea, vía `openai_service_tools.py:205` (`Conversation.objects.get_or_create(thread_id=thread_id, usuario=user, defaults={'empresa': user.empresa})`), una `Conversation` en la empresa A apuntando al `thread_id` de B.

- **Explotación:** autenticado como A, `GET /api/ai/threads/thread_XXXX/messages/` con el `thread_id` de una conversación de B → 200 con el contenido íntegro. `POST /api/ai/threads-tools/thread_XXXX/messages/ {"content": "..."}` → se añade al hilo de B y la respuesta del asistente se genera con el contexto de B. Mitigante real: el `thread_id` lo genera OpenAI (`thread_` + 24 caracteres) y no es enumerable; hace falta que se filtre (logs, soporte, captura de pantalla). Por eso 9/10 y no 10/10 en exploitabilidad, pero es una primitiva de lectura cross-tenant sin ninguna comprobación, en una ruta que el frontend sí usa (`frontend/src/services/ai.service.js:6-13`).
- **Confirmado ejecutando** (`rev_checks.py`, OpenAI mockeado):
  ```
  [R5] GET /api/ai/threads/<thread de B>/messages/ como A -> 200 {"messages":[{"role":"assistant","content":"datos confidenciales de B"}]}; OpenAI llamado con thread de B=True
  [R6] POST threads-tools/<thread de B>/messages/ como A -> 200; GET -> 200; servicio llamado con call(thread_id='thread_B_SECRET2', content='hola', user=<CustomUser: a@a.pe>)
  ```
- **Fix:** en los tres métodos, resolver primero `get_object_or_404(Conversation, thread_id=thread_id, empresa=request.user.empresa, usuario=request.user)` y usar `conversation.thread_id`; en `_save_user_message/_save_assistant_message` sustituir `get_or_create` por `get` (nunca crear una conversación a partir de un `thread_id` que llega del cliente). Las vistas `ventas-assistant`/`compras-assistant` ya lo hacen bien (`services/*_assistant.py:54`).

### P2

**[P2] (confianza: 10/10) `backend/apps/ventas/serializers.py:457,464` — `PATCH /api/ventas/{id}/` sin `detalles` borra todas las líneas de la venta.** (Preexistente; el diff no toca `update()`, pero sí habilita y prueba el `PATCH {cliente_id}` que dispara este comportamiento.)
```python
detalles_data = validated_data.pop('detalles', [])     # 457
...
instance.detalles.all().delete()                        # 464 — incondicional
for detalle_data in detalles_data: ...
```
- **Confirmado:** `[R1] PATCH venta sin detalles -> 200; detalles restantes=0 (esperado 1)`. El control positivo del autor (`test_venta_patch_cliente_id_de_B_400`, `PATCH {cliente_id: A, notas}` → 200) pasa pero deja la venta sin líneas y con `total` recalculado a 0 (`actualizar_totales`).
- Impacto hoy: el frontend expone `updateVentaEstado`/`actualizarEstadoVenta` (PATCH) en `ventas.service.js:258,410` pero ningún componente las llama; es un riesgo latente de API, no un bug activo de UI.
- **Fix:** `detalles_data = validated_data.pop('detalles', None)` y ejecutar el delete+recreate solo `if detalles_data is not None` (mismo patrón que `CotizacionSerializer.update` y `GuiaRemisionSerializer.update`).

**[P2] (confianza: 10/10) `backend/apps/core/permissions.py:19-20` — 403 en el detalle de modelos sin campo `empresa` para el propio tenant.** (Preexistente; el autor lo reporta.)
```python
def has_object_permission(self, request, view, obj):
    if not hasattr(obj, 'empresa'):
        return False
```
Afecta a `FacturaViewSet`, `PagoVentaViewSet`, `RecepcionCompraViewSet`, `PagoCompraViewSet` (sus `get_queryset` ya filtran por `venta__empresa`/`compra__empresa`/`orden__empresa`, así que no hay fuga, pero GET/PUT/PATCH/DELETE de detalle devuelven 403 a todo el mundo).
- **Confirmado:** `[R2] GET/PATCH/DELETE /api/ventas/facturas/{propia}/ -> 403` y en el router-walk `PUT/PATCH /api/ventas/2/pagos/2/ [pk=A] -> 403`, `PUT/PATCH /api/compras/recepciones/2/`, `/api/compras/pagos/2/` → 403. El frontend tiene `actualizarPago` (PUT a `/ventas/{id}/pagos/{pagoId}/`) en `ventas.service.js:361`, hoy sin uso en UI; la variante de compras (`compras.service.js:386`) sí se usa → "editar pago de compra" está roto en prod.
- **Fix:** en `has_object_permission`, resolver la empresa transitivamente (`obj.empresa_id` o `obj.venta.empresa_id`/`obj.compra.empresa_id`/`obj.orden.empresa_id`) o declarar en esos modelos una `@property empresa_id`; mantener `return False` solo si no hay camino.

### P3

**[P3] (confianza: 10/10) `backend/apps/ventas/serializers.py:500-504` — `OrdenVentaSerializer` con `depth = 1` hace `cliente` de solo lectura → `POST /api/ventas/ordenes/` es 500 (`IntegrityError: cliente_id NOT NULL`) para todos.** Confirmado: `[R4] POST /api/ventas/ordenes/ propio -> 500`. El router-walk la excluyó como "sin campos FK en el body", que es exactamente el síntoma. Fix: quitar `depth=1` (FKs acotadas por `EmpresaScopedModelSerializer`) o desregistrar la ruta si no se usa.

**[P3] (confianza: 9/10) `backend/apps/cotizaciones/serializers.py:70,85,95` — `CotizacionSerializer` (ModelSerializer plano) deja `empresa`, `usuario_creador` y `venta` escribibles y sin acotar.** Hoy no explotable: la vista usa `CotizacionCreateSerializer` para create/update/partial_update (`views.py:85-88`) y este se usa solo para lectura (confirmado: `[R7] PATCH cotizacion empresa=B -> 400`). Es una mina si alguien lo reutiliza en una escritura. Fix: añadir `'empresa', 'usuario_creador', 'venta'` a `read_only_fields` o heredar de `EmpresaScopedModelSerializer`.

**[P3] (confianza: 9/10) `backend/apps/servicios/serializers.py:18` — `ItemOrdenServicioSerializer.item_guia` → `ItemGuia` no tiene campo `empresa`, así que `EmpresaScopedPrimaryKeyRelatedField` no filtra (`_model_tiene_empresa` → False).** Hoy no explotable: `items` es `read_only=True` en `OrdenServicioSerializer` y no hay endpoint que cree items. Fix preventivo: `item_guia = EmpresaScopedPrimaryKeyRelatedField(queryset=ItemGuia.objects.filter(...))` con filtro `guia__empresa`, o extender `_model_tiene_empresa` para seguir una FK (`guia__empresa`).

**[P3] (confianza: 8/10) `backend/apps/core/serializers_base.py:29-31` — límite de diseño del patrón: el field acotado solo filtra si el modelo destino tiene `empresa` directa.** Modelos hijos (`DetalleCotizacion`, `ItemGuia`, `DetalleVenta`, `CompraDetalle`, `PagoVenta`, `Factura`, `RecepcionCompra`…) quedan sin acotar si algún día aparecen como FK escribible. La introspección de todos los serializers hoy solo encuentra los dos casos anteriores (ninguno alcanzable). Fix: en `get_queryset`, si el modelo no tiene `empresa` buscar un camino `fk__empresa` (como hace `_empresa_path` en el test) y filtrar por él.

**[P3] (confianza: 8/10) `backend/apps/ml_models/utils/data_preparation.py:155-185` — `get_product_info(producto_id)` y `get_cliente_info(cliente_id)` sin `empresa`.** Hoy los ids que reciben salen de las reglas entrenadas con datos de la propia empresa, y `get_cliente_info` importa `apps.core.models.Cliente` (no existe) y `producto.codigo` (no existe) → código muerto/roto. `_get_empresa` en `ml_models/views.py:20-33` tiene un fallback a `request.data['empresa_id']` que hoy es inalcanzable (`CustomUser` siempre tiene atributo `empresa`) pero que debería eliminarse.

**[P3] (confianza: 10/10) `backend/apps/compras/serializers.py:33-40` — `compras.AlmacenSerializer` declara `telefono`, que no existe en `Almacen` (`ImproperlyConfigured`).** Sin uso en vistas (código muerto); borrar.

**[P3] (confianza: 7/10) Documentación/SQL de producción desalineada con el código.** `ARQUITECTURA_MULTITENANT_ENTERPRISE.md:1213` y `migrations_sql/README.md` afirman que RLS (55 tablas/45 políticas) y triggers de auditoría se ejecutaron en Supabase el 2026-02-24; los `.sql` ya no están en el repo (solo README). El trigger de auditoría documentado lee `app.current_user` (`MIGRACION_UUID_ENTERPRISE.md:478`) mientras el middleware eliminado fijaba `app.current_user_id` → `audit_log.user_id` siempre fue NULL. Nada de esto es una fuga, pero conviene dejar constancia de que RLS en prod es decorativo (ver §5) y actualizar los documentos.

---

## 3. Verificación de cada fix del autor

| Fix (commit `2b72631` / `eed12b6`) | Cómo se verificó | Resultado |
|---|---|---|
| **ventas**: `cliente_id` acotado en update (`VentaSerializer.validate` rama `else`) | Test del autor `test_venta_patch_cliente_id_de_B_400`; walk `PATCH/PUT /api/ventas/2/ cliente_id→B` → 400 FK; prueba propia R8 con clave alterna `{cliente: B}` → 200 pero `cliente` es nested read-only, no cambia | OK |
| **ventas**: `DetalleVentaSerializer` → `EmpresaScopedModelSerializer`, `venta` read-only | Walk `detalles[0].producto→B` en POST/PUT/PATCH → 400 FK; tests del autor `test_venta_patch_detalle_producto_de_B_400`, `..._con_venta_en_body_se_ignora` | OK (pero ver P2: PATCH sin `detalles` borra líneas) |
| **ventas**: `PagoVentaSerializer` → scoped | Walk `POST /api/ventas/2/pagos/ venta→B` → 400 (motivo "no es a crédito", la vista fuerza `venta` desde la URL); test unitario del autor `test_pago_venta_serializer_venta_de_B_invalida` | OK (defensa en profundidad; PUT/PATCH dan 403 por P2) |
| **inventario**: `MovimientoInventarioSerializer` → scoped (kardex PUT/PATCH) | Walk `PUT/PATCH /api/inventario/kardex/2/ producto→B, almacen→B` → 400 FK; test `test_kardex_patch_producto_o_almacen_de_B_400` | OK |
| **inventario**: `_validar_ref_tenant` para `compra_id`/`venta_id`/`orden_produccion_id` en `EntradaCompra`, `SalidaProduccion`, `EntradaProduccion`, `SalidaVenta` | Walk → 400 `{"compra_id":["Compra no encontrada"]}` etc.; tests del autor; instantánea de B sin cambios | OK |
| **inventario**: `reservar` (MP y PT) valida `orden_produccion_id`/`venta_id` con `get_object_or_404(..., empresa=)` | Walk → 404; tests `test_reservar_*_404` comprueban que `cantidad_reservada` no cambia | OK |
| **guías**: `GuiaRemisionSerializer` → scoped; `fecha_emision` como `date` | Walk `POST/PUT/PATCH /api/guias/guias/ cliente→B` → 400 FK; test `test_guia_post_valido_201_y_cliente_de_B_400` (control positivo 201) | OK |
| **producción**: `responsable_id` filtrado por `empresa` | Walk `POST /api/produccion/ordenes/ responsable_id→B` → 400; test con control positivo 201 | OK |
| **core**: `UsuarioSerializer`/`PerfilSerializer` → scoped; `perform_create` inyecta `empresa`; `PerfilSerializer.fields` corregido | Walk `POST/PUT/PATCH core/usuarios, core/perfiles usuario→B` → 400; propia R10 `PUT perfil usuario=B → 400` | OK |
| **core**: `EmpresaViewSet` (`/api/core/empresas/`) create/destroy → 405 | Test `test_core_empresa_no_se_crea_ni_borra_por_api`; walk `DELETE core/empresas/{A}` → 405 | OK |
| **ai**: `MessageViewSet.get_queryset` 404 si la conversación de la ruta no es del usuario; `upload` acepta `pk` y usa `mensaje.conversation` | Tests `test_ai_upload_sobre_mensaje_de_B_404`, `test_ai_mensajes_de_conversacion_de_B_404`; walk nested y plana → 404 | OK (pero P1 en las vistas `threads*`, fuera del diff) |
| **compras**: `CompraDetalleSerializer.compra` read-only; `PagoCompraSerializer.fecha` como `date` | Test `test_compra_detalle_con_compra_en_body_se_ignora` (con `compra` = otra compra de A y = id de B) y `test_pago_compra_propia_201` | OK |
| **TenantMiddleware eliminado** | `grep` de `current_empresa|set_empresa_actual` en `.py/.sql/.md`: solo docs y `apps/core/logging_json.py` (contexto de logging, independiente del GUC); `test_sin_tenant_middleware` | OK (ver §5) |
| **Login 403 "sin empresa"** (`d5467a0`) | Lectura del diff frontend/backend; sin impacto en aislamiento | OK |

---

## 4. Rutas excluidas del router-walk revisadas a mano (57)

| Ruta(s) | Motivo de exclusión | Revisión manual | Veredicto |
|---|---|---|---|
| `api/token/`, `api/auth/token/`, `api/core/token/` (+`refresh/`), `api/auth/login|logout/`, `api/core/auth/verify/` (10) | sin tenant | Emisión/verificación JWT; `UserSerializer.read_only_fields` incluye `empresa` (`authentication/serializers.py:42`) | OK |
| `PUT api/auth/profile/` | sin FK | `UserProfileView.put` usa `UserSerializer(partial=True)`; `empresa`, `is_staff`, `is_active` read-only | OK |
| `POST api/leads/` | público | Sin tenant por diseño | OK |
| `api/ml/models/train/*`, `predict/*` (7) | sin FK | `_get_empresa` toma `request.user.empresa`; fallback a `empresa_id` del body inalcanzable; `predict_recommendations` acepta `producto_id` pero solo consulta el modelo entrenado con datos propios; `get_product_info` sin `empresa` (P3, código roto) | OK con P3 |
| `POST api/mcp/` | auth por ApiToken | `ApiTokenAuthentication` fija `request.empresa` del token y revoca si el creador cambió de empresa (`agente/authentication.py:37`); todas las tools filtran por `empresa` y no aceptan `empresa` como argumento | OK |
| `POST api/agente/tokens/` | sin FK | `perform_create` con `empresa=request.user.empresa`; queryset por empresa | OK |
| `api/inventario/ajustes/` (4) | ruta rota (500) | `AjusteInventario` sin `empresa`; `get_queryset` filtra `empresa=` sobre un campo inexistente → 500 para todos; `AjusteInventarioSerializer` `fields='__all__'` sin acotar. No es fuga (no funciona para nadie) pero es una ruta viva que explota; desregistrar | P3 funcional |
| `POST api/compras/compras/importar_excel/` | archivo | Proveedor/Almacén/Producto con `empresa=request.user.empresa`; columna `empresa` del Excel ignorada (C2) | OK |
| `POST api/inventario/productos/importar/`, `carga-masiva/validar|cargar/` | archivo | `Categoria/Almacen.get_or_create(empresa=...)`, `Producto.filter(empresa=...)` (`utils/carga_masiva.py:303,391,401`) | OK |
| `POST api/importador/upload/` (y `confirmar/<pk>` probada) | archivo | `ImportacionExcel.get(pk, empresa=)`; resolución de `almacen_id/categoria_id/cliente_id` del mapeo con `empresa=self.empresa` (`services.py:1402-1419`); clientes/proveedores por documento con `empresa=` | OK |
| `POST api/ventas/importar_excel/`, `clientes/importar_clientes/` | archivo | `Cliente/Producto.get_or_create(empresa=empresa, ...)` (`ventas/views.py:832,879`) | OK |
| `POST api/inventario/validar-stock-produccion/` | sin FK (ids dentro de lista) | `Producto.get(id, empresa=)`, `Almacen.get(id, empresa=)`, `InventarioMateriasPrimas.get(empresa=...)` | OK (solo lectura) |
| `POST api/ai/threads/`, `threads-tools/`, `files/upload/`, `ventas-assistant/`, `compras-assistant/` (creación) | sin FK | Crean `Conversation` con `empresa=request.user.empresa` | OK |
| `POST api/ai/threads/<thread_id>/messages/` | sin FK | Comprueba `Conversation.get(thread_id, usuario=request.user)` en POST (`views.py:339`); **el GET de la misma ruta no** | **P1** |
| `POST api/ai/threads-tools/<thread_id>/messages/` | sin FK | Sin comprobación de propiedad del `thread_id` (`views.py:603`); crea `Conversation` en A sobre el hilo de B | **P1** |
| `POST api/ai/ventas-assistant/<thread_id>/messages/`, `compras-assistant/<thread_id>/messages/` | sin FK | `services/*_assistant.py:54` `Conversation.get(thread_id, usuario=user)` | OK |
| `POST api/ai/analista/consulta/`, `reporte-ventas/` | sin FK | Consultas agregadas por `request.user.empresa` | OK |
| `POST api/ai/conversations/`, `messages/`, `insights/`, `assistant/`, `assistant/create_conversation/` | sin FK | `perform_create` inyecta empresa/usuario; `POST api/ai/messages/` plano → 404 (sin `conversation_pk`) | OK |
| `POST api/compras/proveedores/`, `api/ventas/clientes/`, `api/finanzas/categorias/`, `api/inventario/almacenes|categorias/` | sin FK | `empresa` read-only + `perform_create`/`create` inyectan `request.user.empresa` | OK |
| `POST api/core/empresas/`, `api/empresas/` | sin FK | Ambos devuelven 405 | OK |
| `POST api/ventas/ordenes/` | sin FK | `depth=1` deja `cliente` read-only → **500 para todos** (`[R4]`) | P3 funcional |

---

## 5. Eliminación de `TenantMiddleware` — qué queda

- Nada en el código consume `app.current_empresa`/`app.current_empresa_uuid`/`app.current_user_id`: no hay `RunSQL` con RLS/triggers en `apps/*/migrations`, `migrations_sql/` solo contiene el README. `set_empresa_actual`/`set_usuario_actual` (`apps/core/logging_json.py`) son contexto de *logging* (thread-local), los sigue fijando `RequestContextMiddleware`/`CustomJWTAuthentication`/`ApiTokenAuthentication`; coherente.
- El diagnóstico del autor es correcto: con `CONN_MAX_AGE=60` y `ATOMIC_REQUESTS=False` (`settings.py:177-179`) un `SET` de sesión podía filtrarse entre peticiones, y con JWT el middleware veía `AnonymousUser`, así que nunca fijaba nada.
- Riesgo residual: según la documentación, en Supabase existen políticas RLS `USING (empresa_id = get_current_empresa_id() OR get_current_empresa_id() IS NULL)` y un trigger `auto_set_empresa_uuid` con fallback a `empresa_id`. Con el GUC siempre NULL las políticas dejan pasar todo (ya pasaba antes) y el trigger rellena `empresa_uuid` desde `empresa_id`. **No hay cambio funcional**, pero RLS en prod es decorativo y la auditoría nunca registró `user_id`. Recomendación: o se implementa de verdad (`SET LOCAL` dentro de `transaction.atomic()` por petición, políticas *fail-closed*) o se eliminan políticas/triggers para no dar falsa sensación de seguridad.

---

## 6. Tests nuevos — ¿prueban lo que dicen?

**`tests/test_aislamiento_router_escrituras.py`** (router-walk de escrituras): diseño robusto.
- Fortalezas: 2xx = fuga; cualquier diferencia en la instantánea de B (conteo + sha1 de `values()` de todos los modelos con camino a `Empresa`) = fuga aunque el status sea 4xx; savepoint por petición; *one-hot* por FK (un FK → B por petición, el resto → A) evita que un 400 por otro FK enmascare la fuga; el objetivo A (objeto propio + FK→B) es la variante que de verdad detecta fugas por FK.
- Debilidades:
  1. La clasificación `[FK]/[OTRO]/[403]` (líneas 541-547) es solo `print`; no hay assert de que el 4xx se deba al FK. Revisé la salida completa: de las ~170 peticiones con objetivo A, todas son `[FK]` salvo 11 `[403]` (P2 de permisos) y 1 `[OTRO]` (`POST /api/ventas/2/pagos/ venta→B` → "Esta venta no es a crédito": la vista ignora `venta` del body y usa la de la URL, así que el 400 es por otra causa pero no hay fuga; la instantánea de B lo confirma). Sugerencia: convertir en assert `clase != 'OTRO'` con lista blanca explícita.
  2. `assertGreaterEqual(tested, 60)` (línea 560) con 172 probadas: el umbral debería ser ~160 para que una regresión de cobertura falle.
  3. La exclusión genérica "sin campos FK en el body" no envía ninguna petición; oculta rutas que explotan para todos (`POST api/ventas/ordenes/` → 500). Sugerencia: para esas rutas enviar al menos la plantilla sin FKs y fallar con 5xx.
  4. `api/ml/` excluido por prefijo aunque `predict/recommendations` acepta `producto_id`; `ids` solo se resuelve para `bulk-estado`.
  5. Las acciones custom se analizan por regex sobre `request.data[...]`; ids dentro de listas anidadas (`materiales[].producto_id` en `validar-stock-produccion`) no se detectan. Revisados a mano (§4).
- La instantánea omite dos modelos (`seed-fail: Stock() got unexpected keyword arguments 'bodega'...`): es el `save()` roto de `AjusteInventario`, no afecta a la detección en otros modelos.

**`EscriturasCruzadasRouterWalkTests`** (`tests/test_aislamiento_tenants.py`): cada test comprueba status + estado en BD (`refresh_from_db`, conteos) y la mayoría incluye control positivo (201/200 para la propia empresa). No hay asserts débiles tipo `assertNotEqual(500)`. Único punto flojo: el control positivo de `test_venta_patch_cliente_id_de_B_400` no comprueba que los `detalles` sobrevivan (P2 §2).

**`tests/test_sin_tenant_middleware.py`**: comprueba ausencia en `MIDDLEWARE`, módulo eliminado y GUC vacío tras una petición autenticada. Correcto.

---

## 7. Riesgos residuales

1. P1 de los asistentes IA por `thread_id` (fuera del diff).
2. El patrón `EmpresaScopedPrimaryKeyRelatedField` no acota FKs a modelos hijos sin `empresa` directa (hoy sin ruta explotable).
3. Serializers planos con FKs escribibles que hoy solo se usan en lectura (`CotizacionSerializer`) o cuyo nested es read-only (`ItemOrdenServicioSerializer`): minas para futuros cambios.
4. `HasEmpresaPermission.has_object_permission` devuelve `False` sin camino transitivo; cada nuevo modelo hijo repetirá el 403.
5. RLS/auditoría en Supabase sin efecto real; documentación desalineada.
6. Rutas vivas que fallan para todos (`inventario/ajustes/`, `ventas/ordenes/` POST) — ruido en logs y superficie innecesaria.

---

## 8. Qué probar a mano en prod tras el deploy

Con dos usuarios de empresas distintas (A y B) y una cuenta sin empresa:
1. Login con usuario sin empresa → mensaje claro 403 (no pantalla en blanco).
2. `PATCH /api/ventas/{venta_A}/ {"cliente_id": <cliente_B>}` → 400 y la venta conserva su cliente. **Importante:** hacerlo sobre una venta de prueba, porque hoy un PATCH sin `detalles` borra las líneas (P2).
3. `POST /api/guias/guias/` con un cliente propio → 201 (antes 500); con cliente de B → 400.
4. `POST /api/compras/compras/{compra_A}/pagos/ {"monto": ..}` sin `fecha` → 201 (antes 500).
5. `POST /api/inventario/materias-primas/entrada_compra/` con `compra_id` de B → 400; con propia → 201 y kardex actualizado.
6. `POST /api/core/usuarios/ {"usuario": <user_A>, "rol": "admin"}` → 201 con `empresa` = A; con `<user_B>` → 400.
7. `DELETE /api/core/empresas/{A}/` y `POST /api/core/empresas/` → 405.
8. `GET /api/ai/conversations/{conv_B}/messages/` → 404 (antes 200 vacío). Y, hasta cerrar el P1, verificar que `GET /api/ai/threads/<thread_id_B>/messages/` **sí** devuelve datos (es la prueba de que el P1 está presente en prod).
9. Comprobar en Postgres que ninguna conexión conserva `app.current_empresa`: `SELECT current_setting('app.current_empresa', true)` desde la app → vacío.
10. Flujo "editar pago de compra" en la UI (`compras.service.js:386`) → confirmar el 403 preexistente y decidir el fix de permisos.

---

## Apéndice — ejecución

- `tests.test_aislamiento_router_escrituras`: `Ran 1 test in 24.0s — OK`. Cobertura: 229 rutas de escritura, 172 probadas, 57 excluidas, 286 peticiones, 0 fugas, 0 5xx.
- Suites del autor (`test_aislamiento_tenants` incl. `EscriturasCruzadasRouterWalkTests`, `test_sin_tenant_middleware`, `test_aislamiento_router`): `Ran 55 tests in 33.9s — OK` (BD de test `test_erp_rev3`, Postgres local 5433).
- Pruebas propias (`rev_checks.py`, 10 tests, OK; salidas citadas en §2): R1 (borrado de detalles), R2 (403 facturas), R3 (`orden_produccion_id` en PATCH de PT se ignora: 200, no se guarda), R4 (500 ordenes de venta), R5/R6 (P1 threads), R7 (cotización `empresa` no modificable), R8 (`{cliente: B}` ignorado), R9 (`created_by` del kardex es `CharField`, no FK), R10 (perfil `usuario` de B → 400).
- Introspección de serializers: únicos FKs escribibles sin acotar: `CotizacionSerializer.empresa` (no usado en escrituras) e `ItemOrdenServicioSerializer.item_guia` (nested read-only). Resto de `*_id` crudos validados por servicio/`_validar_ref_tenant`.
