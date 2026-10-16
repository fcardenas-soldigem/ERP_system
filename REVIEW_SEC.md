# REVIEW_SEC — rama `sec/aislamiento-tenants` (vs `main`)

Fecha: 2026-10-16 · Entorno: local, Postgres `localhost:5433` (nunca Supabase) · Sin push, sin deploy.
Commits de esta sesión: `4712b76 … bfc26ec` (16 commits sobre los 8 previos de la rama + merge de `feat/fase2-mcp-base`).

## 1. Qué cambió

### Bloque A — aislamiento
| # | Cambio | Archivos | Test |
|---|---|---|---|
| A1 | Conversaciones/mensajes de IA privadas **por usuario** (antes solo por empresa). | `ai_assistant/views.py` | `AIConversacionesPorUsuarioTests` |
| A2 | `ventas_pendientes`: el endpoint vivo es `GET /api/ventas/ventas_pendientes/` (`VentaViewSet.ventas_pendientes`, `ventas/views.py:667`); único consumidor `frontend/src/services/ventas.service.js:400` ← `components/Cuentas/CuentasPorCobrar.jsx:50`. El duplicado eliminado (`/api/ventas/{pk}/pagos/ventas_pendientes/`) no tenía consumidores. Nada que restaurar. | — | `VentasPendientesEndpointTests` |
| A3 | Caché con **Redis real**: sin fugas (claves por `empresa_id`). Bugs corregidos: `productos_list`/`inventario_mp_list` nunca se invalidaban; `invalidate_*` hacía `cache.clear()` global (borraba caché de todas las empresas y sesiones). | `core/cache_utils.py` | `tests/test_cache_redis_tenants.py` (se omite sin Redis) |
| A4 | Tests dedicados de C2 (Excel `empresa=B` → queda en A + aviso) y A3-OCS (proveedor de B → 400). | — | `ImportarExcelYOCSAislamientoTests` |
| A5 | Merge `feat/fase2-mcp-base`. `ApiToken` de B en el router-walk (46/52). Todas las tools MCP recorridas con token de A sobre datos de B; revocado/expirado/sin token → 401; JWT → 403; tokens acotados por empresa. | `apps/agente/*`, `config/urls.py`, `config/test_urls.py` | `MCPAislamientoTests`, `apps/agente/tests.py` |
| + | `EmpresaViewSet`: sin `create`/`destroy` (cualquier usuario podía **borrar su empresa en cascada**). | `empresas/views.py` | `EmpresaEndpointTests` |
| + (D2) | Escrituras FK cruzadas cerradas: `Factura`, `OrdenVenta`, kardex, recetas, `OrdenProduccion` → `EmpresaScopedModelSerializer`. `recepciones` daba 500 (`orden_compra`→`orden`). MCP: error genérico, token muere con su creador, `dias` 1..365. | `ventas/inventario/produccion/compras serializers.py`, `agente/*` | `EscrituraFKCruzadaTests`, `MCPEndurecimientoTests` |

### Bloque B — robustez
| # | Cambio | Archivos | Test |
|---|---|---|---|
| B1 | Alta de tenant: `empresas/services.registrar_empresa` + `manage.py crear_tenant` (contraseña solo por `TENANT_ADMIN_PASSWORD`). **Login ya no asigna `Empresa.objects.first()`** a usuarios sin empresa → 403. | `empresas/services.py`, `empresas/management/commands/crear_tenant.py`, `authentication/views.py` | `tests/test_registro_tenant_e2e.py` (alta → login → perfil → COT-00000001 / V-000001 / OC 000001; empresa 1 sigue en …02) |
| B2 | `apps/core/errors.py` (`respuesta_error`, `error_interno`, `mensaje_seguro`). 73 respuestas que devolvían `str(e)` → `{"error": "<mensaje de negocio>"}` (+ 500 + log con traceback); 14 mensajes de validación limpios. Antes/después abajo. | 9 `views.py` | `tests/test_errores_genericos.py` |
| B3 | Logging JSON a stdout: `severity, message, timestamp, logger, request_id, path, user_id, empresa_id, exception` (+ `logging.googleapis.com/trace`). Middleware de contexto, JWT y ApiToken publican user/empresa. Sin email/DNI/RUC/montos en logs. | `core/logging_json.py`, `core/middleware/request_context.py`, `core/authentication.py`, `settings.py` | `tests/test_logging_json.py` |

**B2 — antes → después (sitios que devolvían `str(e)` al cliente):**

| Archivo | Antes | Después |
|---|---|---|
| `compras/views.py` | 16 | 1 (`FacturaError` → 400, mensaje de negocio) |
| `ventas/views.py` | 14 | 1 (`DjangoValidationError` en cambiar_estado → 400) |
| `cotizaciones/views.py` | 6 | 4 (`ProductosFaltantesError`/`CotizacionNoConvertibleError` → 400) |
| `dashboard/views.py` | 1 | 0 |
| `importador/views.py` | 3 | 0 |
| `ai_assistant/views.py` | 22 | 0 |
| `inventario/views.py` | 17 | 0 (9 `ValidationError` → 400 con `mensaje_seguro`) |
| `produccion/views.py` | 6 | 0 (5 `DjangoValidationError` → 400 con `mensaje_seguro`) |
| `ml_models/views.py` | 16 | 6 (`ValueError` → 400) |
| `agente/mcp.py` | 1 | 0 |

Los restantes son todos `except <ExcepciónDeNegocio>` con 400: conservan su mensaje por diseño.

### Bloque C — deploy (solo archivos, nada ejecutado)
- `DEPLOY.md`: backup `pg_dump` (credenciales de entorno) → build con tag (`cloudbuild.yaml` con `_TAG`) → digest → job `erp-migrate` → deploy `--no-traffic` + canary 10 % → promoción → rollback. Incluye tabla de migraciones (C2).
- `scripts/alerta_5xx.sh`: política Cloud Monitoring (>3 5xx / 5 min → email), con `--dry-run`. **No ejecutado.**

## 2. Suite completa (D1)

`python manage.py test --settings=config.settings_test_pg` (Postgres local, Redis `redis:7` en Docker durante la sesión):

| | |
|---|---|
| Tests | **175** |
| OK | **174** |
| Errores | 1: `backend/test_import.py` (script legado del commit inicial, importa un símbolo inexistente; preexistente y documentado) |
| Omitidos | 0 (los tests de Redis corrieron) |
| Router-walk | 46/52 rutas de detalle probadas, 0 fugas, 0 5xx |

Frontend: `npm run build` OK tras el merge del MCP.

## 3. Riesgos (ordenados)

### Alto
- **Serializers escribibles sin scope fuera de los convertidos.** El revisor listó ~45 FKs en `inventario`, `produccion`, `ventas` (`PagoVenta`, `DetalleVenta`), `guias`, `cotizaciones`. Esta sesión cerró los 3 verificados (Factura, kardex, recetas) + OrdenVenta/OrdenProduccion, pero **no hay inventario automático**: el router-walk solo cubre GET/DELETE de detalle. Mitigación propuesta: extender el router-walk con POST/PUT que inyecten cada FK con un id de B (y un smoke `GET list` que nunca dé 5xx).
- **Usuarios con `empresa_id IS NULL` en prod** dejarán de entrar (antes caían en Soldigem). Ejecutar antes del deploy: `SELECT id, email FROM authentication_customuser WHERE empresa_id IS NULL;` y asignarles empresa en el admin.

### Medio
- **Cambio de contrato de errores**: algunos endpoints pasan de 400+`str(e)` a 404/500 genérico (`CompraViewSet.retrieve/list/update`, `saldo_pendiente`, `pagos`, `AIAssistantViewSet.procesar_archivo`). Claves `detail`/`error` conservadas por endpoint; el frontend no debería romper, pero mostrará "Error al …" en vez del texto interno.
- **Login 403 y la UI muestra "Credenciales inválidas"**: `Login.jsx` lee `data.detail`; el backend devuelve `data.error`. Ajuste de una línea en el frontend (no hecho: fuera del alcance backend).
- **`ValueError` se trata como error de negocio** (`core/errors.py`): si una librería lanza `ValueError` con detalle interno, llega al cliente con 400. Aceptado por diseño (el código de negocio usa `ValueError`); vigilar.
- **Access log de gunicorn** sigue en texto y con query string (`/api/core/consultar-dni/?dni=…`): DNI/RUC llegan a Cloud Logging por esa vía. Sugerencia: `--access-logformat` sin query o pasar a POST.
- **`select_for_update` sobre `empresas_empresa`** en la numeración serializa la creación de documentos por tenant hasta el commit exterior: correcto, pero vigilar latencia/deadlocks.
- **Migración `agente/0001`** nunca se ha aplicado sobre el historial real (la suite desactiva migraciones). Es aditiva; el job `erp-migrate` es la primera ejecución.

### Bajo
- `ProveedorViewSet.list` cachea aunque haya `?search=` (devuelve la lista completa cacheada; funcional, no fuga).
- Señal `post_save` crea "Empresa de <nombre>" con RUC aleatorio para usuarios guardados sin empresa (diseño confuso; no es fuga).
- Numeración de `guias`/`servicios` por `order_by('-numero')` lexicográfico: rompe en el documento 10 000.
- `invalidate_inventario_mp/pt` no cubre la variante por almacén (`:almacen:<id>`), hoy sin llamadores; `invalidate_cache()`/`invalidate_empresa_cache()` quedan como código muerto con fallback `cache.clear()`.
- `X-Request-ID` se copia sin truncar a logs/respuesta (JSON lo escapa; conviene `[:64]`).
- `AgenteAccionLog.argumentos` guarda el texto buscado (puede ser RUC/DNI/email): definir retención.
- Índice `token_hash` duplicado (unique + AddIndex): redundante, inocuo.
- `Dockerfile` deja los `ENV` dummy en la imagen: si Cloud Run arrancara sin `--set-secrets`, correría con claves públicas en vez de fallar. Sugerencia: assert en `settings.py` que rechace valores `dummy-*`.

## 4. Qué probar a mano en prod después del deploy

1. Login de un usuario real → `GET /api/auth/profile/` devuelve su `empresa` y `empresa_data.ruc`.
2. Login de un usuario sin empresa (si existe) → 403 y **no** entra a Soldigem.
3. Dashboard (`/api/dashboard/resumen/`, `resumen-historico/`, `stats/30/`), ventas, compras, productos, proveedores: cargan; con `REDIS_URL`, la segunda carga es rápida y muestra los mismos datos.
4. Crear/editar un producto → aparece en la lista **inmediatamente** (invalidación por clave exacta).
5. `GET /api/compras/compras/999999/` → `{"detail": "…"}` 404; forzar un error (p. ej. archivo Excel corrupto en `importar_excel`) → `{"error": "Error al procesar el archivo"}` 500 sin traceback.
6. `GET /api/compras/recepciones/` → 200 (antes 500).
7. Cuentas por cobrar (UI) → consume `/api/ventas/ventas_pendientes/` → 200.
8. Asistente IA: un segundo usuario de la misma empresa no ve las conversaciones del primero (`/api/ai/conversations/`).
9. Configuración → "Conectar Claude": crear token (se muestra una vez), `POST /api/mcp/` `tools/list` con `Bearer`; revocar → 401; sin token → 401; con JWT → 403.
10. Cloud Logging: entradas con `jsonPayload.severity`, `jsonPayload.request_id`, `jsonPayload.empresa_id`, `jsonPayload.user_id`; ningún email/DNI/monto en `jsonPayload.message`.
11. Respuestas llevan cabecera `X-Request-ID` (para correlacionar un error reportado por un usuario con su log).
12. Alta del 2.º tenant: `TENANT_ADMIN_PASSWORD=… manage.py crear_tenant …` (como Cloud Run Job o local con `DOTENV_FILE=.env.production`) → login → primera cotización `COT-00000001`, sin tocar la numeración de Soldigem.

## 5. Qué quedó fuera

- **Frontend**: no se ajustó `Login.jsx` (lee `detail`, el 403 trae `error`); no se hizo QA en navegador de la pantalla "Conectar Claude" (solo `npm run build`).
- **Inventario exhaustivo de serializers escribibles** y extensión del router-walk a POST/PUT con FK de B (riesgo alto arriba). Serializers no verificados por el revisor: `GuiaRemisionSerializer.cliente` (bug preexistente `date/datetime` impidió probar), `core.UsuarioSerializer.usuario`, `ItemOrdenServicio.item_guia`.
- `backend/test_import.py` legado (sigue fallando al importar; borrar o arreglar).
- Access log de gunicorn en JSON/sin query string.
- Política de retención de `AgenteAccionLog`; restricción de creación de tokens MCP a `rol='admin'` (hoy cualquier rol de la empresa puede emitirlos, 90 días por defecto).
- `scripts/alerta_5xx.sh` y todo `DEPLOY.md` quedan **sin ejecutar** por regla.
- `graphify update .` ejecutado (grafo al día; `graphify-out/` no se commitea).

## 6. Informe del subagente de revisión independiente (D2) — tal cual

> Contexto limpio; revisó el diff vs `main` **antes** del commit `bfc26ec` (que cierra sus hallazgos ALTO/MEDIO de Factura, kardex, recetas, recepciones, MCP `str(exc)`, ciclo de vida del token y `dias`). El resto sigue vigente y está recogido en §3/§5.

# Informe de revisión independiente — sec/aislamiento-tenants vs main

## Resumen

Revisé el diff completo (`git diff main...HEAD`, 64 archivos, +3182/−477) y ejecuté localmente (Postgres :5433, con Redis disponible) la suite nueva de la rama (`tests`, `apps.agente`, `apps.core.tests.test_concurrencia`): **63 tests, OK**, router-walk 46/52. Además escribí y ejecuté una prueba empírica propia de "FK cruzada por POST" sobre endpoints que la rama NO convirtió al patrón `EmpresaScopedModelSerializer`. Resultado: la rama cierra lo que dice cerrar (salto de empresa por perfil, admin, MCP, caché, login huérfano, numeración), pero **quedan 3 escrituras cross-tenant verificadas** (facturas, kardex, recetas) que preexisten en `main` y que ni el router-walk (solo GET/DELETE de detalle) ni `FKScopingTests` cubren. No encontré secretos en el diff. La migración nueva es aditiva y segura. El contexto de logging con contextvars es correcto para gthread.

## Hallazgos

### ALTO

**[ALTO] (9/10) `backend/apps/ventas/serializers.py:481-484` — Un usuario de A puede crear una `Factura` sobre una venta de B (escritura cross-tenant verificada).**
Línea: `class FacturaSerializer(serializers.ModelSerializer):` … `fields = '__all__'`. `venta` y `cliente` son `PrimaryKeyRelatedField` sin acotar; `Factura` no tiene campo `empresa` y `FacturaViewSet.get_queryset` (`apps/ventas/views.py:416`) filtra por `venta__empresa`. Prueba ejecutada: `POST /api/ventas/facturas/ {"numero_factura":"F-2","venta":<ventaB>,"cliente":<cliB>}` autenticado como A → **201**, `Factura.objects.filter(venta=ventaB).exists() == True`. Impacto: A inserta un comprobante que B verá en su lista y, al ser `OneToOneField(venta)`, **bloquea a B de facturar su propia venta**. Preexistente en `main` (mismo `fields='__all__'`), no cerrado por la rama a pesar del commit "cierre CRÍTICO/ALTO". Recomendación: heredar de `EmpresaScopedModelSerializer` y, en `perform_create`, verificar `venta.empresa_id == request.user.empresa_id`.

### MEDIO

**[MEDIO] (9/10) `backend/apps/inventario/serializers.py:429` — `POST /api/inventario/kardex/` acepta `producto`/`almacen` de otra empresa.**
Línea: `class MovimientoInventarioCreateSerializer(serializers.ModelSerializer):` (no hereda del patrón nuevo, sin `validate_producto`). Prueba: como A, `POST /api/inventario/kardex/ {"producto":<prodB>,"almacen":<almB>,"tipo_movimiento":"entrada","tipo_documento":"ajuste","cantidad_entrada":5,...}` → **201** y `MovimientoInventario.objects.filter(producto=prodB).exists() == True`. Impacto: fila de kardex de A referenciando maestros de B (respuesta devuelve datos del producto de B → enumeración/confirmación de ids y nombres de B). El stock de B no cambia porque `obtener_stock_actual` filtra por `empresa` (`movimiento_inventario.py:363`). Preexistente en `main`. Recomendación: misma base scoped o `validate_producto/validate_almacen` como ya hacen `StockSerializer`/`InventarioMateriasPrimasCreateSerializer` ("Este producto no pertenece a tu empresa").

**[MEDIO] (9/10) `backend/apps/produccion/serializers.py:116` y `:10` — Recetas con `producto_terminado`/`insumo` de otra empresa.**
Líneas: `class RecetaProductoCreateSerializer(serializers.ModelSerializer):` y `class RecetaDetalleSerializer(serializers.ModelSerializer):`. Prueba: como A, `POST /api/produccion/recetas/ {"producto_terminado":<prodB>,"nombre":"r","detalles":[{"insumo":<prodB2>,"cantidad":1}]}` → **201**, `RecetaProducto.objects.filter(producto_terminado=prodB).exists() == True`. Preexistente en `main`. Mismo remedio. (Mismo riesgo no verificado, confianza 5/10: `OrdenProduccionSerializer.receta/almacen_*`, `GuiaRemisionSerializer.cliente` — el POST de guías en mi prueba falló por un bug preexistente de serialización `date`/`datetime`, así que no pude confirmarlo.)

**[MEDIO] (8/10) `backend/apps/agente/authentication.py:32-42` + `token_views.py` — Ciclo de vida del ApiToken desacoplado del usuario y sin control de rol.**
Líneas: `if not token.activo:` … `return (token.creado_por, token)`. El token sigue válido aunque `creado_por` sea desactivado (`is_active=False`), cambie de empresa o sea borrado (`SET_NULL` → `request.user = None`, el permiso `EsTokenMCP` sigue aceptando). `ApiTokenViewSet` permite a **cualquier rol** de la empresa emitir tokens de 90 días (y con `dias=0`, `expires_at=None` → sin expiración). `scopes` se guarda pero nunca se comprueba. Impacto: un empleado dado de baja conserva acceso de lectura a clientes/ventas/precios vía MCP hasta que alguien revoque a mano. Recomendación: en `authenticate` exigir `token.creado_por and token.creado_por.is_active and token.creado_por.empresa_id == token.empresa_id`; restringir creación a `rol='admin'`; acotar `dias` a `1..365`.

**[MEDIO] (8/10) `backend/apps/agente/mcp.py:83` — El endpoint MCP devuelve `str(exc)` de errores inesperados (contradice B2).**
Línea: `{'type': 'text', 'text': f'Error: {exc}'}], 'isError': True})`. Cualquier excepción interna (DB, atributo, etc.) va al cliente con su mensaje; además no se hace `logger.exception`, solo `resultado_resumen=str(exc)[:200]` en BD (`:81`). Recomendación: devolver mensaje genérico (`mensaje_seguro`) y `logger.exception`.

### BAJO

**[BAJO] (10/10) `backend/apps/compras/serializers.py:364-368` + `views.py:1061-1070` — `/api/compras/recepciones/` da 500 en cualquier GET/POST (preexistente, pero la rama lo tocó y lo "arregló" a ciegas).**
Línea: `fields = ['id', 'orden_compra', ...]` pero el modelo tiene `orden` (`compras/models.py:848`). Verificado: `GET /api/compras/recepciones/` → `ImproperlyConfigured('Field name `orden_compra` is not valid for model `RecepcionCompra`.')`. El nuevo `perform_create` (`validated_data.get('orden')`) es correcto para el modelo pero nunca se ejecuta. El router-walk no lo detecta porque el detalle de B da 404 antes de instanciar el serializer. Igual: `POST /api/inventario/ajustes/` → `TypeError: AjusteInventario() got unexpected keyword arguments: 'empresa'` (`inventario/views.py:219`), y `AlmacenSerializer`/`PerfilSerializer` de compras/core tampoco instancian (`telefono` inexistente). Recomendación: corregir `orden_compra→orden` y añadir al router-walk un smoke `GET list` como A (nunca 5xx).

**[BAJO] (9/10) `backend/apps/authentication/views.py:133-134` vs `frontend/src/components/Auth/Login.jsx:38` — Regresión de contrato de login: 400→403 y la UI no muestra el mensaje.**
Backend: `{'error': 'Tu usuario no tiene una empresa asignada...'}, status=status.HTTP_403_FORBIDDEN`. Frontend: `description: error.response?.data?.detail || 'Credenciales inválidas'`. El usuario sin empresa verá "Credenciales inválidas" (mensaje engañoso). No rompe nada (el interceptor de `frontend/src/lib/api.js:61` solo reacciona a 401). Recomendación: usar `detail` o leer `data.error` en Login.jsx/AuthContext.jsx:86. Nota: el DEPLOY.md ya advierte revisar `empresa_id IS NULL` en prod antes del deploy.

**[BAJO] (8/10) `backend/apps/agente/token_views.py:28` — `dias` sin acotar → 500.**
Línea: `dias = int(request.data.get('dias') or 90)`. Verificado: `timedelta(days=int('99999999999'))` → `OverflowError` no capturado → 500 genérico. `dias` negativo crea un token ya expirado. Recomendación: `max(1, min(dias, 365))`.

**[BAJO] (8/10) `backend/apps/core/errors.py:63` — `ValueError` interno se devuelve textual al cliente.**
Línea: `return str(exc) or 'Valor inválido.'`. `ValueError` se usa como "error de negocio" pero lo lanzan también librerías (pandas, decimal, int()). Riesgo bajo de fuga de detalle interno; coherente con el diseño pero conviene documentarlo o acotar a una excepción de negocio propia.

**[BAJO] (7/10) `backend/apps/core/cache_utils.py:171-175` vs `:155/:167` — Invalidación por claves exactas no cubre la variante por almacén.**
`invalidate_inventario_mp` borra `inventario_mp:<emp>` y `inventario_mp_list:<emp>`, pero `get/set_inventario_mp(empresa_id, almacen_id)` escriben `inventario_mp:<emp>:almacen:<id>`. Hoy **no hay llamadores** de `get_inventario_mp/set_inventario_mp` en `apps/` (verificado por grep), así que no hay regresión activa; es una trampa latente si alguien los usa. Por otro lado, `invalidate_empresa_cache()` sigue existiendo con el fallback `cache.clear()` (sin llamadores). Recomendación: borrar el código muerto o incluir la clave por almacén.

**[BAJO] (7/10) `backend/apps/guias/models.py:86` y `servicios/models.py:102` — Numeración por `order_by('-numero')` lexicográfico.**
Línea: `.order_by('-numero').only('numero').first()`. Con 4 dígitos (`OS-9999`/`GR-9999`), el siguiente `OS-10000` ordena por debajo de `OS-9999` → se vuelve a calcular 10000 → IntegrityError ×3 → 500 a partir del documento 10 000. Lejano pero determinista. Recomendación: ordenar por `-id` dentro del lock de tenant (que ya serializa) o ampliar padding.

### INFO

- **`backend/apps/core/numbering.py:27`** `list(Empresa.objects.select_for_update().filter(pk=empresa_id)...)`: el lock de fila sobre `empresas_empresa` se mantiene hasta el commit de la transacción **exterior** (p. ej. la creación de una venta con detalles en `transaction.atomic()`), serializando toda la creación de documentos del tenant. Correcto para seguridad; vigilar latencia y posibles deadlocks si alguna ruta actualiza `Empresa` y luego crea documentos en la misma transacción (no encontré ninguna).
- **`backend/apps/core/middleware/request_context.py:27`** + `config/settings.py:128/135`: el middleware va antes de `AuthenticationMiddleware`, así que `request.user` nunca existe ahí; el comentario "user/empresa quedan aquí si la sesión ya autenticó" no se cumple (sesión/admin loguean `user_id=None`). Inofensivo.
- **`request_context.py:18`** `request_id = request.META.get('HTTP_X_REQUEST_ID') or ...`: cabecera controlada por el cliente, sin truncar, copiada a todos los logs y a la respuesta. JSON la escapa (sin inyección), pero conviene `[:64]` y validar charset.
- **`backend/apps/agente/mcp.py:36`** `out[k] = v[:200]`: `AgenteAccionLog.argumentos` guarda el `texto` de `buscar_cliente` (RUC/DNI/email buscados) pese al help_text "sin datos sensibles". Es BD, no log; decidir política de retención.
- **`backend/apps/agente/tests.py`** `test_initialize_no_genera_log` prueba `tools/list`, no `initialize` (nombre engañoso).
- **`Dockerfile:69-72`** `ENV DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}` …: los dummies de build quedan como ENV en la imagen; si Cloud Run arrancara sin `--set-secrets`, el proceso correría con `SECRET_KEY`/`JWT_SIGNING_KEY` públicos en vez de fallar. Preexistente (no está en el diff); sugerir `check --deploy` o un assert en `settings.py` que rechace valores `dummy-*`.
- **Migración `agente/0001`:60** `AddIndex(fields=['token_hash'])` duplica el índice único implícito de `unique=True` (índice redundante, sin riesgo).
- `DEPLOY.md` expone el número de proyecto/SA (`25656632090-compute@developer.gserviceaccount.com`); `.gcloudignore` excluye `*.md`, así que no entra en la imagen. No es secreto.
- `admin.site.has_permission = _solo_superuser_plataforma` (`core/apps.py`): correcto (función asignada a instancia, firma `(request)`), pero es un monkeypatch global; preferible `AdminSite` propia. Verificado por `test_admin_plataforma`.
- Cambios de contrato 400→404/500 por `respuesta_error` en `CompraViewSet.retrieve/list/update`, `saldo_pendiente`, `pagos` (clave `detail` conservada) y en `AIAssistantViewSet.procesar_archivo` (antes 400 siempre, ahora 500 si no es de negocio). El frontend consume `data.detail` en 30 sitios y `data.error` en 86; las claves se mantienen por endpoint, así que no detecté ruptura.

## Migraciones

| Migración | Operaciones | Reversible | Locks sobre tablas existentes | NOT NULL sin default en tabla existente |
|---|---|---|---|---|
| `backend/apps/agente/migrations/0001_initial.py` (A) | `CreateModel ApiToken` (FK→`empresas.Empresa` CASCADE, FK→usuario SET_NULL, `token_hash` unique), `CreateModel AgenteAccionLog` (FK→Empresa, FK→ApiToken), `AddIndex token_hash` (redundante) | Sí (`migrate agente zero`, sin datos previos) | Solo `ADD CONSTRAINT` FK: `SHARE ROW EXCLUSIVE` breve sobre `empresas_empresa` y `authentication_customuser` | No (todas las columnas nacen con tablas nuevas) |

`makemigrations --check` implícito: los cambios de modelo de la rama (`guias`, `servicios`, `authentication.telefono` en signal) no alteran esquema. Nota: `settings_test_pg` desactiva migraciones, así que la suite **no** valida que `agente/0001` aplique sobre el historial real; el job `erp-migrate` del DEPLOY.md es la primera vez que corre. Depende de `empresas/0008`, ya en `main`.

## Secretos / datos personales en logs

- **Secretos:** ninguno en el diff ni en archivos nuevos (`cloudbuild.yaml`, `DEPLOY.md`, `scripts/alerta_5xx.sh`, `crear_tenant.py`, `agente.service.js`, `ConectarClaude.jsx`). `crear_tenant` lee la contraseña solo de `TENANT_ADMIN_PASSWORD` (correcto; `--email/--ruc` quedan en el historial de shell: dato personal, no secreto). `.env*` ignorados por git; no hay `.env` trackeado. `DEPLOY.md:58` usa `PGPASSWORD="$DB_PASSWORD"` desde entorno y lo `unset`; correcto.
- **Logs (grep `logger.` en líneas añadidas):** todas las líneas nuevas usan ids (`user_id`, `empresa_id`, `proveedor_id`, `producto_id`, `lead.id`); se eliminaron email/DNI/RUC/montos de `authentication/views.py`, `documento_service.py`, `dashboard/views.py`, `factura_service.py`, `importador/services.py`, `leads/views.py`, `tenant.py`. Verificado con `test_log_de_login_sin_email_y_con_contexto`.
- **Fuera del diff (INFO):** el access log de gunicorn (`Dockerfile`, `--access-logfile -`, formato por defecto) registra la línea de petición completa, incluido el query string de `GET /api/core/consultar-dni/?dni=...` y `consultar-ruc/?ruc=...` → DNI/RUC siguen llegando a Cloud Logging por esa vía. Sugerir `--access-logformat` sin query string o mover a POST.

## Calidad de tests

Ejecutados localmente: `tests` + `apps.agente` + `apps.core.tests.test_concurrencia` → **63 OK** (Redis local disponible: `test_cache_redis_tenants` corrió, no se omitió).

- **Prueban lo que dicen y fallarían sin el fix:** `test_profile_put_no_salta_de_empresa` (C1), `test_usuario_sin_empresa_no_entra_ni_cae_en_la_primera` (usa `.update(empresa=None)` para esquivar la señal `create_user_empresa`; sin el fix el login asignaría `Empresa.objects.first()`), `test_C2_excel_con_empresa_B_queda_en_A_con_aviso`, `test_A3_OCS_proveedor_de_B_rechazado`, `test_crear_producto_invalida_lista_de_su_empresa` (requiere Redis), `test_admin_plataforma`, `test_concurrencia` (hilos reales sobre Postgres, buen test), `AIConversacionesPorUsuarioTests`, `test_error_inesperado_en_retrieve_es_500_generico`.
- **Débiles / pasan sin fix:**
  - `test_aislamiento_router.RouterWalkIsolationTests`: solo GET/DELETE de **detalle** de B. No ejercita POST/PUT con FK de B ni `list` propio → es exactamente el hueco donde están los 3 hallazgos ALTO/MEDIO y los 500 de `recepciones`/`ajustes`.
  - `FKScopingTests` solo prueba 3 serializers ya convertidos; no hay inventario de "serializers escribibles sin scope" (mi script lo listó: ~45 FKs en `inventario`, `produccion`, `ventas` (Factura/PagoVenta/DetalleVenta), `guias`, `cotizaciones.CotizacionSerializer.empresa` escribible aunque solo se usa en retrieve).
  - `MCPAislamientoTests.test_token_de_A_no_lee_B_por_ninguna_tool`: `listar_propuestas_pendientes` devuelve `[]` siempre → pasa trivialmente; el resto sí es significativo.
  - `test_cache_redis_tenants` se omite silenciosamente sin Redis (`skipTest`); en el pre-deploy del DEPLOY.md no hay forma de distinguir "pasó" de "omitido" salvo mirar `skipped=`.
  - `AuditTests.test_initialize_no_genera_log` no prueba `initialize`.
  - `test_errores_genericos.test_dashboard_error_inesperado` solo asegura `!= 200` y que no aparece "SECRETO"; no fija el código ni la clave.

## Qué NO revisé / límites

- Frontend: solo `Login.jsx`, `lib/api.js`, `AuthContext.jsx` y los dos archivos nuevos del agente; no revisé los 30/86 consumidores de `detail`/`error` uno a uno.
- No ejecuté la suite completa de `apps.*` (solo las suites nuevas de la rama + concurrencia); no corrí `makemigrations --check` ni `check --deploy`.
- No verifiqué POST cross-FK en `OrdenProduccion`, `GuiaRemision` (bug `date`/`datetime` preexistente impidió la prueba), `OrdenVenta`, `core.UsuarioSerializer.usuario`, `ItemOrdenServicio.item_guia`, `PagoVenta` sin ruta anidada (`/api/ventas/{pk}/pagos/` sí valida la venta por URL, verificado: 400).
- No analicé `apps/ai_assistant/services.py` (uso de OpenAI con datos del tenant) ni `TenantMiddleware` más allá del cambio de log.
- Concurrencia de contextvars: análisis estático (middleware primero, `iniciar_contexto` resetea todo al entrar y `limpiar_contexto` en `finally`; gthread reutiliza hilos pero cada petición reinicia las 5 variables; `StreamingHttpResponse`/hilos secundarios logean con contexto `None`, nunca con el de otra petición). No lo probé bajo carga.
- Herramientas usadas: diff completo, scripts propios en scratchpad (`enum_ser.py`, `xfk_tests.py`) y la suite de la rama sobre Postgres local. Ningún archivo del repo fue modificado; no hubo push, deploy ni acceso a BD remota.
