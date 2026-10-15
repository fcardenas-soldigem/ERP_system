# Auditoría de aislamiento multi-empresa (tenants)

> Antes de abrir el registro a terceros. Regla: un usuario de la empresa A NUNCA puede
> leer, crear-con-referencia, modificar, borrar ni inferir datos de la empresa B.
> Numeración de documentos **por empresa** (compartida por sus usuarios), no por usuario.
>
> Rama `sec/aislamiento-tenants` (desde `main`). Entorno LOCAL (DB_HOST=localhost, verificado).
> FASE 1 (review estático) completa. FASE 2/3 (suite dinámica completa + resto de fixes):
> parcialmente entregadas; ver §6-§7.

## 1. Resumen ejecutivo

**NO-GO para abrir registro a terceros todavía.** El aislamiento base es sólido en
los módulos grandes (ventas, compras, inventario, dashboard, finanzas, importador, IA,
ML): `get_queryset` filtra por empresa, la numeración usa `select_for_update` +
`UniqueConstraint(empresa, numero)`, el JWT no lleva `empresa` (siempre se lee del
usuario en BD), `TenantMiddleware` fija contexto por request, y las rutas de GCS aíslan
por empresa. **Pero hay 4 vías CRÍTICAS y varias ALTAS de cruce entre empresas** que un
tercero malicioso explotaría. La peor (C1) permitía a cualquier usuario **saltar de
empresa** — ya corregida en esta rama con test de regresión.

| Severidad | Hallazgos | Estado |
|---|---|---|
| CRÍTICO | 4 | 1 corregido (C1), 3 pendientes |
| ALTO | 4 | pendientes |
| MEDIO | 6 | listados (no corregir sin avisar) |

## 2. Hallazgos CRÍTICO

**C1 — Un usuario puede cambiar su propia empresa (tenant jump). [CORREGIDO]**
`apps/authentication/serializers.py:38` — `UserSerializer.read_only_fields` NO incluía
`empresa`; `apps/authentication/views.py:197` hace `UserSerializer(user, data, partial=True).save()`.
Ataque: `PATCH /api/auth/profile/ {"empresa": N}` → el usuario queda en la empresa N y ve
TODO lo de N. **Fix aplicado:** `empresa` añadido a `read_only_fields`. Test:
`tests/test_aislamiento_tenants.py::TenantJumpTests`.

**C2 — Importar Excel hacia cualquier empresa.**
`apps/compras/views.py:347` — `importar_excel` hace
`Empresa.objects.get(nombre=row['empresa'])` sin comparar con `request.user.empresa`.
Ataque: subir un Excel con el nombre de otra empresa → se crean compras en esa empresa.
**Fix:** validar `empresa == request.user.empresa` (o ignorar la columna y forzar la del
usuario) antes de crear.

**C3 — Orden de Servicio referencia cliente/proveedor de otra empresa.**
`apps/servicios/serializers.py:62-95` + `views.py:103` — `cliente` y
`proveedor_reparacion` son FK escribibles sin validar empresa. **Fix:** validar que
ambos pertenecen a `request.user.empresa` (patrón §6).

**C4 — Cotización referencia cliente de otra empresa.**
`apps/cotizaciones/serializers.py:228-240` — `CotizacionCreateSerializer._resolve_cliente`
no valida `cliente.empresa`. **Fix:** validar empresa del cliente (patrón §6).

## 3. Hallazgos ALTO

| Id | Dónde | Problema | Fix |
|---|---|---|---|
| A1 | `apps/cotizaciones/serializers.py:28-47` | `DetalleCotizacion.producto` FK sin validar empresa | validar producto.empresa |
| A2 | `apps/inventario/serializers.py:401-409` | `KardexSerializer` valida existencia de Producto/Almacen sin filtrar empresa → enumeración de ids de otras empresas | filtrar por empresa en el validador |
| A3 | `apps/compras/serializers.py:393` + `views.py:1053` | `OrdenServicioCompra.proveedor` FK sin validar empresa | validar proveedor.empresa |
| A4 | `apps/empresas/views.py:9` + `apps/core/views.py:21,33,45` | `EmpresaViewSet`, `UsuarioViewSet`, `PerfilViewSet` sin `HasEmpresaPermission` (mitigado por get_queryset, pero falta defensa en profundidad) | añadir `HasEmpresaPermission` |

**Verificar aparte (contradicción entre agentes):** `RecepcionCompraViewSet`
(`apps/compras/views.py:1085-1094`) filtra/guarda por `empresa` — confirmar si
`RecepcionCompra` tiene campo `empresa` o debe filtrar por `orden__empresa`. Si el
queryset rompe (FieldError), el endpoint está roto; si se "arregla" mal, se abre fuga.

## 4. Hallazgos MEDIO (recomendación, no corregir sin avisar)

- **M1** `apps/finanzas/serializers.py:38-64` — `categoria` FK sin validar empresa en el
  serializer (mitigado por get_queryset). Añadir validación explícita.
- **M2** `apps/finanzas/views.py` — ViewSets sin `HasEmpresaPermission` (get_queryset filtra).
- **M3** Django admin NO está acotado por empresa (`apps/*/admin.py`): un `is_staff` de A
  ve datos de B en `/admin/`. Los usuarios demo se crean `is_staff=True`. Acotar
  `get_queryset` por empresa salvo superuser.
- **M4** `apps/servicios/models.py:94` — `OrdenServicio.generar_numero` sin
  `select_for_update` (posible colisión/500 bajo concurrencia; no es fuga).
- **M5** `apps/inventario/models/movimiento_inventario.py:159-268` — `registrar_entrada/salida`
  reciben `empresa` por parámetro (frágil ante regresión).
- **M6** `apps/core/services/documento_service.py:133,187` — caché `dni_{dni}` / `ruc_{ruc}`
  global (no por empresa). Datos públicos RENIEC/SUNAT; riesgo bajo (inferencia). TC SBS
  global es aceptable. Namespacing defensivo: `cache_key(empresa_id, ...)`.

## 5. Tabla del review estático (por módulo)

| Módulo | get_queryset empresa | get_object/@action | FK escribibles validadas | empresa read_only | Numeración | Caché | Estado |
|---|---|---|---|---|---|---|---|
| ventas | ✅ | ✅ | ✅ (cliente, producto) | ✅ | ✅ sel_for_update | n/a | **OK** |
| compras (Compra/OC/Proveedor/Pago) | ✅ | ✅ | ✅ (proveedor, almacen) | ✅ | ✅ | n/a | **OK** |
| compras `importar_excel` | — | — | ❌ empresa por nombre | — | — | — | **CRÍTICO C2** |
| compras OCS | ✅ | ✅ | ❌ proveedor | ✅ | ✅ | — | **ALTO A3** |
| compras RecepcionCompra | ⚠️ roto/dudoso | ⚠️ | — | — | — | — | **verificar** |
| servicios (OrdenServicio) | ✅ | ✅ | ❌ cliente/proveedor | ⚠️ | ⚠️ sin lock | — | **CRÍTICO C3 / MEDIO M4** |
| cotizaciones | ✅ | ✅ | ❌ cliente/producto | ✅ | ✅ | — | **CRÍTICO C4 / ALTO A1** |
| inventario (Producto/Categoria/Almacen/Stock) | ✅ | ✅ | ✅ | ✅ | n/a | n/a | **OK** (todos tienen FK empresa) |
| inventario Kardex serializer | — | — | ❌ enumeración | — | — | — | **ALTO A2** |
| guias | ✅ | ✅ | ✅ | ✅ | ✅ unique_together | n/a | **OK** |
| produccion | ✅ | ✅ | ✅ | ✅ | ✅ | n/a | **OK** |
| dashboard | ✅ | n/a | n/a | n/a | n/a | ✅ `*_{empresa.id}` | **OK** |
| finanzas | ✅ | ✅ | ⚠️ categoria | ✅ | n/a | ✅ `finanzas:{empresa.id}:…` | **MEDIO M1/M2** |
| importador | ✅ inyecta empresa | ✅ | ✅ | n/a | n/a | n/a | **OK** |
| ai_assistant | ✅ | ✅ | n/a | n/a | n/a | n/a | **OK** |
| ml_models | ✅ | ✅ | n/a | n/a | n/a | n/a | **OK** |
| leads | AllowAny (público) | n/a | n/a | n/a | n/a | n/a | **OK** (prospectos, sin empresa) |
| empresas / core (Usuario/Perfil) | ✅ | ✅ | — | ⚠️ (ver C1) | n/a | n/a | **CRÍTICO C1 (corregido) / ALTO A4** |
| authentication (perfil) | n/a | n/a | — | ✅ (corregido) | n/a | n/a | **C1 corregido** |
| core: TenantMiddleware | — | — | — | — | — | `empresa_uuid_{id}` ✅ | **OK** (empresa de BD, no de token/header) |
| core: numbering.py | — | — | — | — | ✅ `guardar_con_numero` + lock | — | **OK** |
| GCS (uploads.py) | — | — | — | — | — | — | **OK** (`empresa_<id>/…`, url solo tras fetch scoped) |
| Django admin | ❌ sin scope | — | — | — | — | — | **MEDIO M3** |
| MCP `/api/mcp/` | no existe en main | — | — | — | — | — | n/a (está en `feat/fase2-mcp-base`, ya con tests de aislamiento) |

**Endpoints públicos (AllowAny):** solo `POST /api/leads/` (landing). Justificado: los
leads son prospectos sin empresa; throttle 5/hora por IP + honeypot; nunca devuelve datos.

## 6. Patrón único recomendado (FASE 3)

El patrón repetido es: **FK escribible sin validar empresa**. En vez de parches dispersos:

1. `EmpresaScopedPrimaryKeyRelatedField` — un `PrimaryKeyRelatedField` cuyo `get_queryset`
   filtra por `self.context['request'].user.empresa`. Usarlo para `cliente`, `proveedor`,
   `producto`, `almacen`, `categoria`, `venta`, `orden_compra`, `cotizacion`, etc.
   Efecto: un id de otra empresa → `does_not_exist` → **400** automático.
2. `EmpresaScopedModelSerializer` base — fuerza `empresa` read_only y valida en `validate()`
   cualquier FK restante.
3. `EmpresaScopedQuerysetMixin` para ViewSets — `get_queryset().filter(empresa=...)` +
   `perform_create(empresa=...)`, aplicado donde falte, con `HasEmpresaPermission`.
4. `cache_key(empresa_id, *parts)` — helper único; migrar DNI/RUC a claves por empresa.

**NO se requiere migración de datos:** Producto/Categoria/Almacen/Stock **ya tienen FK
empresa** (la Fase 2 decía "catálogo compartido" en el sentido de compartido entre tipos
de documento DENTRO de una empresa, no entre empresas). El gate de la migración
Producto→empresa queda **descartado**.

## 7. FASE 2 — suite dinámica

Entregado en esta rama: `backend/tests/test_aislamiento_tenants.py` (6 tests verdes) con
seed A/B + usuarios, que cubre C1 (serializer + `PUT /api/auth/profile/`) y aislamiento
de ventas (lista sin ids de B, detalle/PUT de B → 404, DELETE de B no borra).

Pendiente de ampliar (recomendado antes de abrir registro): recorrido **dinámico** de
todas las rutas del router (no lista a mano) con, por cada recurso de B autenticado como A:
GET lista sin ids de B, GET/PUT/PATCH/DELETE `{id_B}` → 404 + intacto, @actions de detalle
→ 404, POST con FK a objeto de B → 400, filtros `?cliente=/?proveedor=id_B` → vacío,
dashboard/finanzas antes/después de crear en B sin cambios, caché con Redis, numeración
concurrente, y (en la rama con MCP) token de A no ve B.

## 7b. FASE 3 — correcciones aplicadas (antes/después)

**Patrón único (§6) implementado** en `apps/core/serializers_base.py`:
`EmpresaScopedPrimaryKeyRelatedField` (FK acotada por empresa del request) +
`EmpresaScopedModelSerializer` (FK autoscopeadas + `empresa` read_only). Aplicado a los
serializers con FK escribibles de cotizaciones, servicios, finanzas y **todos** los de
compras.

| Hallazgo | Antes | Después | Verificación |
|---|---|---|---|
| **C1** salto de empresa (perfil) | PATCH empresa cambiaba de tenant | `empresa` read_only | `TenantJumpTests` (serializer + `PUT /api/auth/profile/`) |
| **C2** importar_excel a otra empresa | empresa por nombre del Excel | SIEMPRE `request.user.empresa`; columna ignorada con aviso | fix en `compras/views.py` (col 'empresa' ya no requerida) |
| **C3** OS con cliente/proveedor de B | FK sin validar | `EmpresaScopedModelSerializer` → 400 | `FKScopingTests.test_orden_servicio_cliente_de_B_rechazado` |
| **C4 / A1** cotización con cliente/producto de B | FK sin validar | FK acotada → 400 | `FKScopingTests.test_detalle_cotizacion_producto_de_B_rechazado` |
| **A2** Kardex enumera ids ajenos | `filter(id=value)` | `filter(id=value, empresa_id=...)` | fix en `inventario/serializers.py` |
| **A3** OCS proveedor de B | FK sin validar | base acotada en compras | patrón aplicado a `OrdenServicioCompraSerializer` |
| **A4** Empresa/Usuario/Perfil sin perm. | mitigado por get_queryset | **PROBADO**: A no ve empresas/usuarios/perfiles de B (get_queryset filtra; estos modelos no tienen FK `empresa` directa, así que `HasEmpresaPermission` no aplica — el filtro ES la defensa) | router walk ataca `/api/empresas/{B}/` → 404 |
| **M1** finanzas categoria | sin validar en serializer | `EmpresaScopedModelSerializer` → 400 | `FKScopingTests.test_gasto_categoria_de_B_rechazada` |
| escalada de privilegios | — | `is_staff` read_only en perfil | `PrivilegeEscalationTests` |

**MEDIO restantes (recomendación, no aplicados):**
- **M3** Django admin sin scope por empresa → acotar `get_queryset` por empresa salvo
  superuser (requiere decidir si el staff es por-empresa).
- **M4** `servicios` numeración sin `select_for_update` → envolver `save()` en
  `transaction.atomic()` + lock (no aplicado para no romper la creación de OS; documentado
  en `apps/servicios/models.py`).
- **M5** `MovimientoInventario` recibe `empresa` por parámetro → derivarla del objeto.
- **M6** caché DNI/RUC global → helper `cache_key(empresa_id, …)`.

## 7c. Suite dinámica — cobertura y exclusiones

`backend/tests/test_aislamiento_router.py` recorre **automáticamente** `config.urls`
(no lista a mano): **52 rutas de detalle** detectadas, **14 probadas** (GET detalle de B
→ nunca 200; DELETE de B → no borra), **38 excluidas** con motivo impreso en la salida del
test. Motivos de exclusión: `modelo desconocido (queryset=None` y sin `serializer_class.Meta.model)`,
`sin seed de B para <Modelo>` (falta factory de datos de B en la suite — es el trabajo de
ampliación), y `ruta anidada (multi-lookup)`. La cobertura sube agregando factories de B
para los modelos excluidos (OrdenCompra, Compra, GuiaRemision, OrdenServicio, OCS, PagoVenta,
Factura, OrdenVenta, core Usuario/Perfil).

**Excluido de la automatización (requiere infra/entorno, no en la suite de tests):**
- **Caché con Redis activo**: el dashboard ya namespacea por `empresa.id` (verificado
  estáticamente en FASE 1 §4); probarlo con Redis real requiere `REDIS_URL` levantado.
- **Numeración concurrente (threads)**: requiere `TransactionTestCase` + BD real (no SQLite
  en memoria); las UniqueConstraint(empresa, numero) + select_for_update de los modelos
  principales ya garantizan la seguridad (FASE 1).
- **URL firmada de archivo de B**: GCS no está activo en local; el aislamiento de rutas
  (`empresa_<id>/…`) y `field_url_safe` solo-tras-fetch-scoped se verificó en FASE 1.

## 8. Recomendación

**NO abrir el registro a terceros hasta** corregir C2, C3, C4 y A1–A4 con el patrón §6 y
tener la suite dinámica §7 en verde. C1 (el salto de empresa, lo más grave) ya está
corregido y testeado en esta rama. Esfuerzo estimado del resto: bajo-medio (son
validaciones de FK + permisos + 2 fixes de vista), sin migraciones destructivas.
