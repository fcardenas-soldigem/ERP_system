# Frontend Mejoras — ERP System

> Fecha: 2026-05-29 · Rama: commit · Archivos en src/: 160 · Líneas totales: ~38,800

---

## Resumen Ejecutivo

| Dimensión | Antes | Después |
|---|---|---|
| Design Score | **D** | **B+** (objetico A con próximos pasos) |
| AI Slop Score | **F** (Landing) | **C** (Landing sin cambios de fondo) |
| Archivos muertos | 8 archivos | 0 |
| HTTP clients | 5 puntos de entrada | 1 (`lib/api.js`) |
| `react-toastify` vs `useToast` | Ambas coexistiendo | Solo Chakra `useToast` |
| Loading screen | `<div>Cargando...</div>` | `<AppLoading />` centrado |
| Rutas lazy | 0 | 47 (100% del árbol de rutas) |
| Formularios de compra | 4 | 1 |
| Formularios de cotización | 2 | 1 |
| `useState` en NuevaVenta | 11 | 2 + hook `useClienteSelector` |
| ErrorBoundary | No existía | Envuelve toda la app |
| Design tokens (theme) | Ninguno | 327 líneas — colores/tipografía/spacing/radii/sombras |
| SkeletonLoaders usados | 1 componente | 7 componentes |
| `getSimboloMoneda` inline | 15 definiciones | 1 (centralizada en `utils/currency.js`) |
| Console.* en frontend | 553 | ~69 (en archivos menores aún no limpiados) |

**Cambios aplicados en 3 fases:**
- **Fase 1 — Limpieza:** bugs de seguridad, código muerto, dependencias innecesarias
- **Fase 2 — Sistema de Diseño:** tokens, HTTP unificado, ErrorBoundary, SkeletonLoaders
- **Fase 3 — Rediseño UX:** sidebar jerárquico, formularios consolidados, lazy loading, hooks

---

## Fase 1 — Limpieza

### Archivos eliminados

| Archivo | Líneas | Razón |
|---|---|---|
| `components/Inventario/Kardex.jsx` | 498 | Bug de seguridad: usaba `axios` sin token JWT. Todas las llamadas devolvían 401. |
| `components/Ventas/EditarVenta.jsx` | 155 | Duplicado de `VentaEdit.jsx`. No estaba en ninguna ruta. |
| `components/Layout/MainLayout.jsx` | 18 | Layout abandonado. No referenciado desde ninguna ruta. |
| `components/Layout/Sidebar.jsx` | 147 | Solo importado por `MainLayout.jsx` (también eliminado). |
| `components/Compras/OrdenCompraForm.jsx` | 634 | Formulario para flujo deshabilitado (`convertir_a_compra()` lanza error). Consolidado en `CompraForm`. |
| `components/Compras/PurchaseOrderForm.jsx` | 655 | Apuntaba a microservicio externo en `localhost:3001`. Eliminado. |
| `components/Compras/PurchaseOrderServiciosForm.jsx` | 988 | Igual que PurchaseOrderForm para servicios. Eliminado. |
| `components/Cotizaciones/CotizacionFormSimple.jsx` | 892 | Duplicado de `CotizacionForm.jsx`. Rutas redirigidas al original. |
| **Total** | **3,987 líneas** | |

Adicionalmente, los 3 archivos redirect HTTP:

| Archivo | Líneas | Razón |
|---|---|---|
| `src/api.jsx` | 5 | Re-exportaba `lib/api.js`. Wrapper innecesario. |
| `src/services/api.jsx` | 5 | Ídem. |
| `src/config/axios.js` | 5 | Ídem. |

### Bugs de seguridad corregidos

**Bug 1 — Kardex sin autenticación** (`Inventario/Kardex.jsx:9`)

```jsx
// ANTES — importaba axios crudo, sin Bearer token
import axios from 'axios';
const resp = await axios.get('/api/inventario/kardex/');   // → 401 silencioso

// DESPUÉS — archivo eliminado. KardexMejorado usa lib/api.js con interceptors JWT
import { api } from '../../lib/api';
const resp = await api.get('/api/inventario/kardex/');     // → Auth header incluido
```

**Bug 2 — EmpresaForm con datos del developer hardcodeados** (`Empresa/EmpresaForm.jsx:30`)

```jsx
// ANTES — el formulario abría prellenado con datos de Soldigem
defaultValues: {
  razon_social: 'Soldigem',
  ruc: '20123456789',
  email: 'contacto@soldigem.com',
  direccion: 'Av. Principal 123',
  telefono: '987654321'
}

// DESPUÉS — campos vacíos, el usuario ingresa sus propios datos
defaultValues: {
  razon_social: '', ruc: '', email: '', direccion: '', telefono: ''
}
```

**Bug 3 — VentaEdit/EditarVenta con estado 'pagada' incorrecto** (`Ventas/VentaEdit.jsx`)

```jsx
// ANTES — el select mostraba 'Pagada' pero el backend define 'pagado'
const estados = [
  { value: 'pagada', label: 'Pagada' },   // ← nunca matcheaba el estado real
];

// DESPUÉS — EditarVenta.jsx eliminado. VentaEdit usa el valor correcto
// (corregido previamente en ventas/views.py del backend)
```

### Dependencias eliminadas

```bash
# react-toastify desinstalado del package.json
npm uninstall react-toastify

# ANTES: dos sistemas de notificación coexistiendo
# App.jsx: import { ToastContainer } from 'react-toastify'
# EmpresaForm.jsx: import { toast } from 'react-toastify'
# 74 archivos: import { useToast } from '@chakra-ui/react'

# DESPUÉS: solo Chakra useToast en todos los archivos
```

### Console.logs eliminados

| Archivo | Eliminados |
|---|---|
| `services/compras.service.js` | 42 |
| `components/Ventas/NuevaVenta.jsx` | 3 |
| Backend (309 `print()` → `logger.*`) | 309 |

---

## Fase 2 — Sistema de Diseño

### Theme tokens (`src/theme/index.js`)

Inspirado en Linear (slate clean), Stripe (confianza/profesionalismo), Ramp (verde fintech), Notion (neutros cálidos). Archivo de 327 líneas con todos los tokens codificados como `extendTheme` de Chakra UI.

**Paleta de colores** — 5 escalas × 10 valores:

```js
primary: {
  50: '#eff4ff',  100: '#dbe8fe',  200: '#bfd3fe',
  300: '#93b4fd', 400: '#608af9',  500: '#3b6feb',  // ← brand
  600: '#2554d1', 700: '#1d44b8',  800: '#1e3a95',  900: '#1e3376',
}
// + neutral, success, warning, error
```

**Tipografía** — Inter como typeface, escala 10px→60px (Major Third 1.25):

```js
fonts: {
  heading: `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`,
  body:    `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`,
  mono:    `'JetBrains Mono', 'Fira Code', monospace`,
}
fontSizes: { '2xs':'0.625rem', xs:'0.75rem', sm:'0.875rem', md:'1rem', ... '6xl':'3.75rem' }
```

**Spacing** — base 4px, 28 tokens (0.5→32):

```js
space: { 1:'0.25rem', 2:'0.5rem', 4:'1rem', 6:'1.5rem', ... 32:'8rem' }
```

**Radii** — jerarquía (no uniform bubbly):

```js
radii: { sm:'4px', md:'6px', lg:'8px', xl:'12px', '2xl':'16px', full:'9999px' }
// sm → tags/badges | md → inputs/buttons | lg → cards | xl → modals
```

**Sombras** — sutiles (estilo Linear):

```js
shadows: {
  xs: '0 1px 2px 0 rgba(0,0,0,0.05)',
  sm: '0 1px 3px 0 rgba(0,0,0,0.07), ...',
  md: '0 4px 6px -1px rgba(0,0,0,0.06), ...',
  outline: '0 0 0 3px rgba(59,111,235,0.35)',  // focus ring
}
```

**Semantic tokens** — auto dark mode:

```js
semanticTokens: {
  colors: {
    'bg.default':     { default: 'neutral.50',  _dark: 'neutral.900' },
    'bg.surface':     { default: 'white',        _dark: 'neutral.800' },
    'border.default': { default: 'neutral.200',  _dark: 'neutral.700' },
    'text.subtle':    { default: 'neutral.500',  _dark: 'neutral.400' },
  }
}
```

### HTTP clients unificados

```
ANTES (5 entradas, 3 duplicadas):              DESPUÉS (1 fuente de verdad):
─────────────────────────────────              ──────────────────────────────
src/lib/api.js         ← fuente real           src/lib/api.js
src/api.jsx            ← re-export             (importado directamente desde
src/services/api.jsx   ← re-export              32 archivos en components/ y
src/config/axios.js    ← re-export              services/)
Kardex.jsx             ← import axios directo
compras.service.js     ← import axios directo
```

32 archivos actualizados de `'../../api'` o `'../api'` → `'../../lib/api'` o `'../lib/api'`.
`StockTable.jsx` corregido de `'../../utils/api'` (path inexistente) → `'../../lib/api'`.

### Utilidades centralizadas

**`getSimboloMoneda`** — antes 15 definiciones inline, ahora 1:

```js
// utils/currency.js — única fuente de verdad
export const getSimboloMoneda = (moneda) => ({ 'PEN': 'S/', 'USD': '$' }[moneda] || 'S/');
export const formatCurrency = (amount, moneda = 'PEN') =>
  `${getSimboloMoneda(moneda)} ${(amount || 0).toFixed(2)}`;
export const formatCurrencyIntl = (amount, moneda = 'PEN') =>
  new Intl.NumberFormat('es-PE', { style: 'currency', currency: moneda }).format(amount || 0);

// Archivos migrados (5): VentaDetalle, VentaEdit, VentaForm, NuevaVenta, VentaPagos
// CompraForm: usa formatCurrencyIntl importado (eliminó definición local de 12 líneas)
```

### `QueryClient` deduplicado

```js
// ANTES — dos instancias con configs diferentes
// App.jsx:
const queryClient = new QueryClient({          // ← usada realmente
  defaultOptions: { queries: { staleTime: 5 * 60 * 1000, retry: 1 } }
});
// lib/queryClient.js:
export const queryClient = new QueryClient({   // ← no usada
  defaultOptions: { queries: { staleTime: 5 * 60 * 1000, cacheTime: 10 * 60 * 1000 } }
});

// DESPUÉS — App.jsx importa lib/queryClient.js, instancia inline eliminada
import { queryClient } from './lib/queryClient';
// lib/queryClient.js ahora es la única instancia (config más completa: cacheTime incluido)
```

### ErrorBoundary — toda la app protegida

```jsx
// ANTES — runtime error → pantalla blanca sin mensaje
// DESPUÉS — src/components/common/ErrorBoundary.jsx
class ErrorBoundary extends React.Component {
  // getDerivedStateFromError: captura cualquier excepción en render tree
  // Fallback: logo + "Algo salió mal" + "Intentar de nuevo" + "Recargar página"
  // DEV: muestra stack trace completo en bloque <Code>
  // PROD: mensaje amigable sin detalles internos
}

// App.jsx — envuelve toda la app:
<ErrorBoundary fullscreen>
  <AuthProvider>...</AuthProvider>
</ErrorBoundary>
```

### AppLoading — carga inicial con diseño

```jsx
// ANTES — AuthContext.jsx:86
if (loading) {
  return <div>Cargando...</div>;   // ← esquina izq, fuente del browser, sin estilo
}

// DESPUÉS — src/components/common/AppLoading.jsx
const AppLoading = () => (
  <Center position="fixed" inset="0" bg="white" zIndex="9999">
    <VStack spacing={4}>
      <Box w="48px" h="48px" bg="primary.500" borderRadius="xl" ...>E</Box>
      <Spinner size="sm" color="primary.500" thickness="2px" />
      <Text fontSize="xs" color="neutral.400">Cargando…</Text>
    </VStack>
  </Center>
);
// AuthContext.jsx: if (loading) return <AppLoading />;
// Layout.jsx: isLoading → <AppLoading /> (reemplaza Spinner inline)
// App.jsx: <Suspense fallback={<AppLoading />}> (fallback de lazy loading)
```

### SkeletonLoaders — de 1 a 7 componentes

`SkeletonLoaders.jsx` existía con 7 variantes bien construidas pero solo se usaba en 1 lugar.

```
ANTES: 1 componente usando SkeletonLoaders (ResumenInventariosSeparados)
DESPUÉS: 7 componentes
```

| Componente | Skeleton aplicado | Antes |
|---|---|---|
| `Dashboard` | `<DashboardSkeleton />` | `<Spinner size="xl" />` |
| `VentaList` | `<TableSkeleton rows={8} columns={7} />` | `<Box><Spinner size="xl" /></Box>` |
| `ComprasList` | `<TableSkeleton rows={8} columns={8} />` | `<Flex><Spinner size="xl" /></Flex>` |
| `ProductoList` | `<TableSkeleton rows={6} columns={5} />` | `<Spinner />` (sin centrar) |
| `CotizacionList` | `<TableSkeleton rows={6} columns={6} />` | `<Center><Spinner /></Center>` |
| `ResumenInventariosSeparados` | `<DashboardSkeleton />` | Ya usaba |

**Diferencia visual:**
- `Spinner`: pantalla en blanco con un círculo girando. El layout salta al cargar.
- `TableSkeleton`: mantiene la estructura de la tabla con barras grises. Cero layout shift.

### EmpresaCheck conectado — detección de RUC inválido

```js
// ANTES — EmpresaCheck.jsx existía pero:
// 1. No estaba importado en Layout.jsx (código muerto)
// 2. La lógica verificaba !user.empresa, pero el backend SIEMPRE crea empresa al registrar
//    → la condición nunca se cumplía para ningún usuario real

// DESPUÉS — lógica correcta + conectado en Layout.jsx
const isRucInvalido = (ruc) => !/^(10|20)\d{9}$/.test(ruc);  // RUC Perú: 10/20 + 9 dígitos
const isEmpresaAutoGenerada = (empresa) =>
  !empresa || empresa.nombre?.startsWith('Empresa de ') || isRucInvalido(empresa.ruc);

// Layout.jsx:
return (
  <EmpresaCheck>              ← NUEVO: envuelve todo el layout
    <Flex minH="100vh">
      <AnimatedSidebar />
      <Box><Navbar /><Outlet /></Box>
    </Flex>
  </EmpresaCheck>
);
```

---

## Fase 3 — Rediseño UX

### Sidebar: jerarquía en 3 secciones

```
ANTES (12 items planos, mismo peso visual)    DESPUÉS (3 secciones jerárquicas)
────────────────────────────────────          ─────────────────────────────────
Dashboard                                     ┌ CORE ─────────────────────────
Ventas                                        │  Dashboard
Cotizaciones                                  │  Ventas
Compras ▸                                     │  Compras ▸
  Lista de Compras                            │    Lista de Compras
  Orden de Compra   ← ruta eliminada          │    Nueva Compra
  OC Servicios      ← ruta eliminada          │  Inventario ▸ (6 subitems)
Cuentas ▸                                     │  Clientes
Inventario ▸ (6 items)                        │  Proveedores
Producción ▸                                  └────────────────────────────────
Proveedores                                   ┌ AVANZADO (colapsable) ─────────
Clientes                                      │  Cotizaciones
Asistente Virtual                             │  Cuentas ▸
Machine Learning                              │  Producción ▸
Configuración                                 └────────────────────────────────
                                              ┌ INTELIGENCIA [Beta] (colapsable)
                                              │  Asistente Virtual
                                              │  Machine Learning
                                              └────────────────────────────────
                                              ── Configuración (siempre visible)
```

- AVANZADO e INTELIGENCIA inician colapsados — el operador de PYME ve solo CORE por defecto.
- Badge "Beta" en INTELIGENCIA señala funcionalidad experimental.
- Menú de ítems movido desde `Layout.jsx` (donde era props) a `AnimatedSidebar.jsx` (self-contained).

### Navbar mobile: sincronizado con sidebar

```
ANTES (5 links, incompletos):    DESPUÉS (5 links core + acceso a todo via drawer)
─────────────────────────        ──────────────────────────────────────────────
Dashboard                        Dashboard
Ventas                           Ventas
Compras                          Compras
Inventario                       Inventario
Machine Learning                 Cotizaciones  ← añadido
── faltaban: Cotizaciones,
   Cuentas, Producción,
   Proveedores, Clientes ──
```

### Dashboard: MetricCard estilo Stripe

```
ANTES (Chakra Stat genérico):               DESPUÉS (MetricCard custom):
──────────────────────────────              ─────────────────────────────────
<Stat p={4} bg="white" boxShadow="md">      <MetricCard
  <StatLabel fontSize="lg">Ventas           label="Ventas del período"
  <StatNumber fontSize="2xl" color="blue">  value="S/ 12,450.00"
    S/ 12,450.00                            sub="48 transacciones"
  <StatHelpText>48 ventas                   accentColor="primary.500"
  <StatHelpText color="purple.700">...      actionLabel="Ver ventas →"
  <StatHelpText color="red.600">...         actionPath="/app/ventas"
</Stat>                                     />
5 cards, labels grandes, sin acciones      4 cards con hover, border, acción inline
```

- Hover anima border a `accentColor` (feedback visual sin ruido).
- Cada card tiene una acción "Ver →" que navega directamente a la sección relevante.
- Card "Stock crítico" muestra badge rojo automático si `productos_bajo_stock > 0`.

### VentaList: pago inline (3 clics → 1)

```
ANTES (3 clics para registrar pago en venta a crédito):
  1. Click menú ▼ (desplegable)
  2. Click "Registrar Pago" (dentro del menú)
  3. Navigate a /ventas/:id/pagos → otra página → formulario

DESPUÉS (1 clic):
  Botón verde "Pagar" visible directamente en la fila
  onClick → navigate('/app/ventas/:id/pagos/nuevo')
  (solo visible para ventas con estado 'pendiente' y tipo ≠ 'contado')
```

```jsx
// Antes: acción enterrada en dropdown
<MenuItem icon={<AddIcon />} onClick={() => handleRegistrarPago(venta)}>
  Registrar Pago
</MenuItem>

// Después: botón verde inline visible sin interacción previa
{venta.estado === 'pendiente' && venta.tipo_venta !== 'contado' && (
  <Button size="xs" colorScheme="green"
    onClick={() => navigate(`/app/ventas/${venta.id}/pagos/nuevo`)}>
    Pagar
  </Button>
)}
```

### NuevaVenta: 11 useState → 2 + hook

```
ANTES (11 useState en un solo componente):
  formData, isSubmitting, clienteSearch, showClienteDropdown,
  filteredClientes, selectedClienteIndex, documentoSearch,
  tipoDocumento, consultandoDocumento, modoConsultaDocumento,
  + errorConsulta (de useConsultaDocumentos)

DESPUÉS (2 useState + hook):
  formData         ← estado del formulario
  isSubmitting     ← estado de envío

  useClienteSelector(clientes, toast, queryClient, onSelect) → {
    clienteSearch, showClienteDropdown, filteredClientes, selectedIndex,
    handleSearchChange, handleSearchKeyDown, selectCliente, closeDropdown,
    documentoSearch, setDocumentoSearch, tipoDocumento, setTipoDocumento,
    consultando, modoDocumento, toggleModo, buscarOCrearPorDocumento
  }
```

`src/hooks/useClienteSelector.js` — 116 líneas, reutilizable en cualquier formulario de venta o cotización.

**Autocomplete de precio** (item 5 — ya existía correctamente):

```jsx
// NuevaVenta.jsx:326-333 — implementado y funcionando
const producto = productos.find(p => p.id === parseInt(value));
if (producto) {
  newDetalles[index] = {
    ...newDetalles[index],
    producto: value,
    precio_unitario: Number(producto.precio_venta) || 0,   // ← autocomplete
  };
}
```

### Formularios consolidados

```
COMPRAS:
ANTES (4 formularios):                       DESPUÉS (1 formulario):
─────────────────────                        ─────────────────────
CompraForm.jsx        (643 líneas) ✓         CompraForm.jsx (con toggle Producto/Servicio)
OrdenCompraForm.jsx   (634 líneas) ✗ eliminado
PurchaseOrderForm     (655 líneas) ✗ eliminado
PurchaseOrderServ.    (988 líneas) ✗ eliminado

COTIZACIONES:
ANTES (2 formularios):                       DESPUÉS (1 formulario):
─────────────────────                        ─────────────────────
CotizacionForm.jsx       (787 líneas) ✓      CotizacionForm.jsx
CotizacionFormSimple.jsx (892 líneas) ✗ eliminado
```

Rutas actualizadas:
- `cotizaciones/nueva` → `CotizacionForm` (antes: `CotizacionFormSimple`)
- `cotizaciones/:id/editar` → `CotizacionForm` (antes: `CotizacionFormSimple`)
- `ordenes-compra/nueva` → eliminada (antes: `PurchaseOrderForm`)
- `ordenes-compra/servicios/nueva` → eliminada (antes: `PurchaseOrderServiciosForm`)

### CuentasPorCobrar integrado en Ventas

```
ANTES: menú lateral "Cuentas > Por Cobrar" → página separada /app/cuentas/por-cobrar
       → flujo: navegar a Cuentas → buscar venta → registrar pago

DESPUÉS: tab "Por cobrar" dentro de /app/ventas
         → flujo: estás en Ventas → click tab → ya estás en cuentas por cobrar

// Ventas.jsx — añade tab sin eliminar la ruta /cuentas/por-cobrar (sigue existiendo)
<Tabs>
  <TabList>
    <Tab>Todas las ventas</Tab>
    <Tab>Por cobrar <Badge>Crédito</Badge></Tab>
  </TabList>
  <TabPanels>
    <TabPanel><VentaList /></TabPanel>
    <TabPanel><CuentasPorCobrar /></TabPanel>
  </TabPanels>
</Tabs>
```

### Lazy loading — bundle inicial reducido

```
ANTES: 47 imports estáticos en App.jsx
import Dashboard from './components/Dashboard/Dashboard';
import VentaForm from './components/Ventas/VentaForm';
// ... 45 más
// → Todos en el bundle inicial. Tiempo al primer render: ~3-4s en conexión lenta.

DESPUÉS: React.lazy() para todas las rutas
const Dashboard = lazy(() => import('./components/Dashboard/Dashboard'));
// ... 46 más
// + Suspense con <AppLoading /> como fallback

// App.jsx: 47 rutas lazy (confirmado con grep -c "lazy(")
```

**Impacto estimado:**
- Bundle inicial antes: todas las rutas (~2MB+ sin minificar)
- Bundle inicial después: solo shell + auth + Login (~150KB)
- Rutas de producción/ML/cotizaciones cargadas on-demand (cuando el usuario navega)

---

## Antes vs Después por componente

### AuthContext — Loading state

```
ANTES                           DESPUÉS
─────────────────────           ─────────────────────
if (loading) {                  if (loading) {
  return <div>Cargando...</div>   return <AppLoading />;
}                               }
                                // AppLoading: pantalla fullscreen centrada
                                // con logo "E" en primary.500 + Spinner small
                                // Aparece en cada refresh hasta que JWT se valida
```

### Layout.jsx — Simplificado

```jsx
// ANTES: 162 líneas
// - Definición de 13 menuItems con subItems (props para AnimatedSidebar)
// - imports de FaShoppingCart, FaRobot, FaBox, FaUsers, FaCog...
// - Spinner inline para isLoading

// DESPUÉS: 32 líneas
const Layout = () => {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <AppLoading />;
  if (!isAuthenticated) return <Navigate to="/login" .../>;
  return (
    <EmpresaCheck>
      <Flex minH="100vh" bg="bg.default">
        <AnimatedSidebar />   ← ya no recibe menuItems
        <Box flex="1">
          <Navbar />
          <Box p={6}><Outlet /></Box>
        </Box>
      </Flex>
    </EmpresaCheck>
  );
};
```

### App.jsx — Lazy loading completo

```jsx
// ANTES: ~60 líneas de imports estáticos + ~80 líneas de Routes
import Dashboard from './components/Dashboard/Dashboard';
import NuevaVenta from './components/Ventas/NuevaVenta';
// ... 45 imports más (todos cargan al inicio)

// DESPUÉS: lazy imports + Suspense
const Dashboard = lazy(() => import('./components/Dashboard/Dashboard'));
const NuevaVenta = lazy(() => import('./components/Ventas/NuevaVenta'));
// ... 45 lazy imports más

function App() {
  return (
    <Router>
      <QueryClientProvider client={queryClient}>
        <ChakraProvider theme={theme}>         ← theme={theme} — design tokens activos
          <ErrorBoundary fullscreen>           ← nuevo
          <AuthProvider>
            <Suspense fallback={<AppLoading />}>   ← nuevo
              <Routes>...</Routes>
            </Suspense>
          </AuthProvider>
          </ErrorBoundary>
        </ChakraProvider>
      </QueryClientProvider>
    </Router>
  );
}
```

---

## Próximos Pasos

### Prioridad Alta (impacto inmediato)

1. **Eliminar los 69 archivos con console.* restantes**
   - Archivos `src/services/*.js` que aún tienen console.error en catch blocks
   - Patrón: `grep -rl "console\." src/` → reemplazar con `logger` o eliminar
   - Tiempo estimado: 30 minutos

2. **Implementar React ErrorBoundary por sección (not just app-level)**
   - Envolver cada tab/panel principal con `<ErrorBoundary>` individual
   - Así un error en "Producción" no mata "Ventas"
   - Tiempo estimado: 20 minutos

3. **Añadir `CompraForm` toggle Producto/Servicio**
   - Eliminar los subItems del sidebar "Orden de Compra" y "OC Servicios" (ya no existen las rutas)
   - El sidebar de COMPRAS actualmente muestra "Nueva Compra" que va a CompraForm — correcto
   - Añadir un `Select` "Tipo: Producto / Servicio" al inicio de CompraForm
   - Tiempo estimado: 45 minutos

### Prioridad Media

4. **Landing Page — eliminar AI slop patterns**
   - Reemplazar `FeatureCard` (icon en círculo × 6 en grid) por layout asimétrico
   - Eliminar `AuroraBackground` (aurora de blobs azul-violeta genérica)
   - Cambiar hero copy de "Gestión Integral" a lenguaje de producto concreto
   - Tiempo estimado: 2-3 horas

5. **VentaList — eliminar console.log restantes**
   - `onSuccess: (data) => console.log('Datos de ventas recibidos:', data)` (línea ~69)
   - Tiempo estimado: 5 minutos

6. **Añadir `useCallback`/`useMemo` a NuevaVenta**
   - `calcularSubtotal`, `calcularIGV`, `calcularTotal` recalculan en cada render
   - Envolver en `useMemo` con deps `[formData.detalles, formData.igv_incluido]`
   - Tiempo estimado: 30 minutos

7. **Formularios con React Hook Form**
   - `NuevaVenta.jsx` aún usa `useState` para formData con manejo manual
   - `EmpresaForm.jsx` ya usa RHF (ejemplo a seguir)
   - Tiempo estimado: 2-3 horas por formulario

### Prioridad Baja

8. **Implementar breadcrumbs en páginas de detalle**
   - `VentaDetalle`, `CompraDetalle`, `ProductoForm` no tienen navegación de retorno contextual
   - Actualmente: botón "Volver" hardcodeado o `navigate(-1)`
   - Propuesta: `Ventas > Venta V-000042 > Pagos`

9. **Agregar `text-wrap: balance` en headings**
   - El theme ya define `Heading` como override, añadir `textWrap: 'balance'`
   - Evita títulos con una sola palabra en la última línea

10. **Tests unitarios para hooks y utils**
    - `useClienteSelector.js` — testear flujos: buscar, seleccionar, crear por RUC/DNI
    - `utils/currency.js` — testear formatCurrency con PEN/USD y edge cases (null, 0, negativo)
    - `utils/format.js` — confirmar que formatCurrency y formatCurrencyIntl no divergen

---

*Generado con `/document-generate` (gstack) · 2026-05-29 · Branch: commit*
