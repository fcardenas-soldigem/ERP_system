# Cambios Frontend - 29 Mayo 2026

## Resumen

Sesión de revisión y corrección del frontend tras una refactorización arquitectónica amplia.
Se identificaron y corrigieron bugs críticos, imports rotos, rutas incorrectas y código deprecado.

---

## Correcciones aplicadas

### 1. Bug crítico de sintaxis — `compras.service.js`

**Archivo:** `frontend/src/services/compras.service.js`

**Problema:** Al eliminar un `console.log` previamente, quedó un bloque de objeto huérfano (líneas 11–14) que rompía la compilación del módulo completo de compras.

**Solución:** Se eliminó el bloque huérfano y se limpió la función `getCompras`.

---

### 2. Imports rotos a `config/axios.js` (archivo eliminado)

**Archivos corregidos:**
- `frontend/src/services/produccion.service.js`
- `frontend/src/services/cotizacionesService.js`
- `frontend/src/services/mlService.js`

**Cambio:** `import api from '../config/axios'` → `import api from '../lib/api'`

---

### 3. Imports rotos a `services/api.jsx` (archivo eliminado)

**Archivos corregidos:**
- `frontend/src/hooks/useConsultaDocumentos.js`
- `frontend/src/hooks/useTipoCambio.js`
- `frontend/src/components/Inventario/CargaMasivaInventario.jsx`
- `frontend/src/utils/debugAuth.js`

**Cambio:** Referencias a `../services/api.jsx` o `../../services/api` → `../lib/api` / `../../lib/api`

---

### 4. Rutas incorrectas en `InventarioEnlaces.jsx`

**Archivo:** `frontend/src/components/Inventario/InventarioEnlaces.jsx`

**Problema:** Las rutas no tenían el prefijo `/app`, que es obligatorio según la estructura de `App.jsx` (`<Route path="/app" ...>`). Los botones no navegaban a ningún lado.

**Cambios:**
| Antes | Después |
|-------|---------|
| `/inventario/kardex-mejorado` | `/app/inventario/kardex` |
| `/inventario` | `/app/inventario` |
| `/inventario/nuevo` | `/app/inventario/nuevo` |

También se eliminó la referencia a "Kardex Clásico" (componente `Kardex.jsx` fue borrado en la refactorización).

---

### 5. `vite.config.mjs` — dos problemas

**Archivo:** `frontend/vite.config.mjs`

**Problema 1:** `react-toastify` listado en `optimizeDeps.include` aunque ya no es dependencia del proyecto (fue removido en la refactorización del stack UI).

**Problema 2 (crítico):** El proxy `/api` apuntaba a `localhost:8000` cuando el backend Django corre en el puerto `8080`.

**Solución:**
- Eliminado `react-toastify` de `optimizeDeps`
- Proxy `/api` corregido de `localhost:8000` → `localhost:8080`

---

### 6. React Query v5 — `cacheTime` deprecado

**Archivos corregidos:**
- `frontend/src/lib/queryClient.js`
- `frontend/src/components/Ventas/NuevaVenta.jsx` (2 ocurrencias)

**Cambio:** `cacheTime` → `gcTime` (renombrado en React Query v5, `cacheTime` es ignorado silenciosamente)

---

### 8. Conversión automática Cotización → Venta al aceptar

**Objetivo del usuario:** que al aceptar una cotización, se cree automáticamente la venta en el módulo de ventas.

**Estado previo:** el endpoint `POST /api/cotizaciones/{id}/convertir-venta/` existía pero **estaba roto** (intentaba pasar `forma_pago` y `descuento` a campos inexistentes de Venta, faltaba `fecha_emision`, sin `transaction.atomic`, sin actualizar totales). Además "aceptar" no creaba venta — solo registraba fecha.

**Archivos creados:**
- `backend/apps/cotizaciones/services/__init__.py`
- `backend/apps/cotizaciones/services/conversion_service.py`

**Archivos modificados:**
- `backend/apps/cotizaciones/views.py`
- `backend/apps/cotizaciones/serializers.py`
- `frontend/src/components/Cotizaciones/CotizacionList.jsx`
- `frontend/src/components/Cotizaciones/CotizacionDetalle.jsx`

**Lógica del servicio `conversion_service.convertir_cotizacion_a_venta()`:**

1. **Transaccional** (`@transaction.atomic`).
2. **Validaciones:** no convertir si está `rechazada`, `vencida` o `convertida`; debe tener al menos una línea con producto.
3. **Mapeo `forma_pago` (texto libre) → `tipo_venta` + `metodo_pago` (choices):**
   - `"contado"` / `"efectivo"` → `contado` + `efectivo`
   - `"credito_30"` / `"crédito 30"` → `credito_30`
   - `"credito_60"` / `"crédito 60"` → `credito_60`
   - `"transferencia"` / `"tarjeta"` / `"cheque"` → `contado` + método
   - Default → `contado` + `efectivo`
4. **Mapeo IGV** según la combinación `incluye_igv` + `precios_incluyen_igv` de la cotización.
5. **Descuento global prorrateado** en los precios unitarios (DetalleVenta no tiene campo descuento).
6. **Descuento por ítem** absorbido en el precio unitario neto.
7. **Servicios sin producto:** se omiten con mensaje claro de error si no quedan líneas convertibles.
8. **Venta resultante:** estado `pendiente`, `fecha_emision = hoy`, `referencia = numero_cotizacion`, notas con trazabilidad.
9. **`venta.actualizar_totales()`** se llama tras crear los detalles.
10. **Idempotencia:** si la cotización ya tiene venta enlazada, retorna esa misma venta.

**Endpoint `cambiar-estado` actualizado:** ahora al recibir `estado=aceptada` automáticamente:
- Registra `fecha_aceptacion`
- Llama al servicio de conversión
- Marca la cotización como `convertida` con FK a la nueva venta
- Devuelve `{venta_creada, venta_id, venta_numero, message}` en la respuesta

**Endpoint `convertir-venta` actualizado:** ahora delega al servicio (manejo consistente de errores y mismo mapeo).

**Frontend - `CotizacionList.jsx`:**
- Al convertir, navega a `/app/ventas/{id}` en vez de solo refrescar la lista
- Mejor parseo de errores (`error.response.data.error || .detail`)

**Frontend - `CotizacionDetalle.jsx`:**
- `handleCambiarEstado` detecta `venta_creada` en la respuesta y navega automáticamente a la venta
- Botón "Convertir a Venta" se oculta si ya existe `venta_info`
- **Banner verde** con enlace "Ver venta" si la cotización ya tiene venta asociada (mostrando número, total, moneda y estado de la venta)

**Frontend - serializer:**
- Nuevo campo `venta_info` con `{id, numero, estado, total, moneda}` para que el frontend muestre la venta enlazada sin hacer un request adicional

**Flujo final:**

```
Usuario → "Marcar como Aceptada" en CotizacionDetalle
       ↓
Backend cambiar_estado('aceptada')
       ↓
   fecha_aceptacion = hoy
   convertir_cotizacion_a_venta()
       ↓
   Venta creada (estado=pendiente, en módulo ventas)
   Cotización.estado = 'convertida'
   Cotización.venta = venta_nueva
       ↓
Frontend recibe {venta_id, venta_numero, message}
       ↓
Toast "Cotización aceptada → Venta V-000123 creada"
Redirige a /app/ventas/{id}
```

---

### 9. Bloques huérfanos de `getSimboloMoneda` en módulo Ventas

**Archivos corregidos:**
- `frontend/src/components/Ventas/NuevaVenta.jsx`
- `frontend/src/components/Ventas/VentaDetalle.jsx`
- `frontend/src/components/Ventas/VentaEdit.jsx`
- `frontend/src/components/Ventas/VentaPagos.jsx`
- `frontend/src/components/Ventas/VentaForm.jsx`

**Problema:** Al mover `getSimboloMoneda` a `utils/currency.js`, en cada archivo quedaron 3 líneas huérfanas (un `return` sin declaración de función):

```js
  // Función para obtener el símbolo de moneda
    return simbolos[moneda] || 'S/';
  };
```

Esto generaba `Unexpected "}"` en esbuild y rompía el build del módulo de Ventas completo.

**Solución:** Se eliminaron las líneas huérfanas en los 5 archivos. La función importada `getSimboloMoneda` ya funcionaba correctamente.

---

## Estado del frontend tras las correcciones

| Punto | Estado |
|-------|--------|
| Módulo de compras compilable | ✅ Resuelto |
| Imports a archivos eliminados | ✅ Resuelto (0 referencias rotas) |
| Rutas de inventario funcionales | ✅ Resuelto |
| Proxy Vite apuntando al puerto correcto (8080) | ✅ Resuelto |
| Dependencias inexistentes en optimizeDeps | ✅ Resuelto |
| React Query v5 compatible | ✅ Resuelto |
| Errores de lint | ✅ Cero errores |

---

## Refactorización arquitectónica previa (contexto)

Estos bugs fueron consecuencia de una refactorización mayor del frontend que incluyó:

- **Stack UI:** MUI + Bootstrap + Redux + react-toastify eliminados → Chakra UI + React Query
- **Capa HTTP unificada:** `api.jsx` + `config/axios.js` + `services/api.jsx` eliminados → `src/lib/api.js`
- **Routing consolidado:** `router.jsx` + `router/index.jsx` + `router/routes.js` eliminados → rutas inline en `App.jsx`
- **Layouts consolidados:** `MainLayout.jsx` + `Sidebar.jsx` eliminados → `Layout.jsx` actualizado
- **Nuevos módulos:** inventarios separados, carga masiva, órdenes de compra (2 flujos), cotizaciones de servicios, wizard de recetas
- **UX:** `ErrorBoundary`, `AppLoading`, `SkeletonLoaders`, `StatsCard`, theme Chakra custom

---

### 10. Fix bug crítico + modal "Productos por registrar" en conversión Cotización → Venta

**Fecha:** 29 Mayo 2026

**Error reportado:** `"Error al convertir a venta: Producto() got unexpected keyword arguments: 'activo'"`

**Causa raíz:** El código anterior intentaba crear productos automáticamente en el inventario cuando una línea de cotización no tenía `producto_id`. Al hacerlo pasaba el campo `activo=True`, que no existe en el modelo `Producto` (el campo correcto es `is_active`).

**Decisión de diseño cambiada:** El backend **no debe crear productos automáticamente**. Si faltan productos, debe retornar un `400` con los datos de las líneas faltantes y el frontend debe presentar un modal para que el usuario los registre.

---

#### Backend — `backend/apps/cotizaciones/services/conversion_service.py`

Reescrito por completo. Se eliminó `_obtener_o_crear_producto_servicio`. Nuevas funciones:

| Función | Descripción |
|---------|-------------|
| `detectar_productos_faltantes(cotizacion)` | Devuelve lista de detalles sin `producto_id` con sus datos |
| `ProductosFaltantesError` | Nueva excepción que lleva la lista de productos faltantes |
| `convertir_cotizacion_a_venta()` | Ahora lanza `ProductosFaltantesError` en vez de crear productos |

Payload del error:
```json
{
  "error": "productos_faltantes",
  "message": "2 producto(s) sin registrar en inventario.",
  "productos_faltantes": [
    {
      "detalle_id": 42,
      "descripcion": "Servicio de instalación",
      "codigo": "",
      "cantidad": "1.00",
      "precio_unitario": "350.00"
    }
  ],
  "cotizacion_id": 29,
  "moneda": "PEN"
}
```

---

#### Backend — `backend/apps/cotizaciones/views.py`

- Importado `ProductosFaltantesError`
- Acciones `cambiar_estado` y `convertir_venta` ahora capturan `ProductosFaltantesError` y retornan el payload `400` anterior
- **Nuevo endpoint:** `POST /api/cotizaciones/{id}/vincular-producto/`
  - Body: `{ detalle_id: int, producto_id: int }`
  - Enlaza un detalle de la cotización con un producto recién creado en el inventario
  - Lo usa el modal del frontend tras crear cada producto

---

#### Frontend — `frontend/src/services/cotizacionesService.js`

Agregado método:
```js
vincularProducto(cotizacionId, detalleId, productoId)
// POST /api/cotizaciones/{id}/vincular-producto/
```

---

#### Frontend — `frontend/src/components/Cotizaciones/CrearProductosCotizacionModal.jsx` *(nuevo)*

Modal Chakra UI estilo Linear/Stripe que:

- Se abre cuando el backend responde `error: "productos_faltantes"`
- Muestra un formulario por cada producto faltante
- **Prellenados** desde la cotización:
  - Nombre → descripción del ítem
  - Descripción → descripción del ítem
  - Precio de venta → precio unitario del ítem
  - Moneda → moneda de la cotización
- **Vacíos para completar:**
  - SKU (requerido)
  - Precio de compra
  - Categoría (dropdown cargado desde `inventarioAPI.getCategorias()`)
  - Almacén (dropdown cargado desde `inventarioAPI.getAlmacenes()`)
  - Unidad de medida (dropdown: unidad, kilo, gramo, litro, metro, decena, docena, centenar, millar)
- Al confirmar:
  1. Crea cada producto via `inventarioAPI.createProducto()`
  2. Vincula cada uno con su detalle via `cotizacionesService.vincularProducto()`
  3. Reintenta `cotizacionesService.convertirVenta()` automáticamente
  4. Navega a la nueva venta con toast de confirmación

---

#### Frontend — `CotizacionDetalle.jsx` y `CotizacionList.jsx`

**Antes:** Los errores de conversión mostraban un toast genérico.

**Después:** Tanto `handleConvertirVenta` como `handleCambiarEstado` detectan `error === "productos_faltantes"` y abren el modal en vez del toast.

---

#### Flujo completo actualizado

```
Usuario → "Convertir a Venta" o "Marcar como Aceptada"
       ↓
Backend intenta convertir
       ↓ (todos los productos existen)
   Venta creada → toast → navega a /app/ventas/{id}

       ↓ (faltan productos)
   HTTP 400 { error: "productos_faltantes", productos_faltantes: [...] }
       ↓
Frontend abre modal "Productos por registrar"
Usuario completa SKU, precio compra, categoría, almacén, unidad
       ↓
Modal crea productos en inventario (POST /api/inventario/productos/)
Modal vincula cada producto con su detalle (POST /api/cotizaciones/{id}/vincular-producto/)
Modal reintenta conversión (POST /api/cotizaciones/{id}/convertir-venta/)
       ↓
Venta creada → toast "Venta V-000X creada" → navega a /app/ventas/{id}
```

---

## Pendientes (decisiones de diseño, no bugs)

- Definir arquitectura única para órdenes de compra (Django vs microservicio Node en `:3001`)
- Modularizar componentes >400 líneas: `CotizacionFormSimple`, `RecetaWizard`, `PurchaseOrderForm`, `Configuracion`
- Adoptar tokens del theme (`primary`/`neutral`) en componentes que usan colores genéricos de Chakra (`gray.*`, `blue.*`)
- Implementar lazy loading de rutas en `App.jsx` para reducir bundle inicial
- Hacer `git add` de archivos nuevos sin trackear (`src/lib/`, `src/theme/`, `src/components/common/`, etc.)
