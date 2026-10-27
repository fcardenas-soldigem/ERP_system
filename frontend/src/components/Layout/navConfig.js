// ─── Estructura de navegación — única fuente para sidebar (escritorio) y móvil ─
// `icon` (react-icons/fa) lo usa el sidebar; `lineIcon` (lucide, trazo) lo usa
// la navegación móvil. Sección 'avanzado' e 'inteligencia' empiezan colapsadas.
// Sin badges "Nuevo"/"Beta": si está en el menú, es parte del producto.
// Orden CORE por frecuencia de uso real: Cotizaciones es el módulo más usado.
import {
  FaChartBar, FaShoppingCart, FaBox, FaUsers, FaIndustry,
  FaFileInvoice, FaMoneyBillWave, FaRobot, FaBrain,
  FaChartLine, FaFileUpload, FaTruck, FaTools,
} from 'react-icons/fa';
import {
  LayoutDashboard, FileText, ShoppingCart, Package, LineChart, Boxes,
  Users, Building2, Truck, Wrench, FileUp, Wallet, Factory, Bot, Brain,
} from 'lucide-react';

export const MENU_SECTIONS = [
  {
    id: 'core',
    label: 'CORE',
    collapsible: false,
    items: [
      { name: 'Dashboard',    icon: FaChartBar,    lineIcon: LayoutDashboard, path: '/app/dashboard' },
      { name: 'Cotizaciones', icon: FaFileInvoice, lineIcon: FileText,        path: '/app/cotizaciones' },
      { name: 'Ventas',       icon: FaShoppingCart, lineIcon: ShoppingCart,   path: '/app/ventas' },
      {
        name: 'Compras', icon: FaBox, lineIcon: Package,
        subItems: [
          { name: 'Facturas de Compra', path: '/app/compras' },
          { name: 'Nueva Compra',       path: '/app/compras/nueva' },
          { name: 'Órdenes de Compra',  path: '/app/compras/ordenes' },
          { name: 'OC de Servicio',     path: '/app/compras/ordenes-servicio' },
        ],
      },
      {
        name: 'Finanzas', icon: FaChartLine, lineIcon: LineChart,
        subItems: [
          { name: 'Dashboard Financiero', path: '/app/finanzas' },
          { name: 'Gastos Operativos',    path: '/app/finanzas/gastos' },
        ],
      },
      {
        name: 'Inventario', icon: FaBox, lineIcon: Boxes,
        subItems: [
          { name: 'Resumen',            path: '/app/inventario/resumen-separado' },
          { name: 'General',            path: '/app/inventario' },
          { name: 'Materias Primas',    path: '/app/inventario/materias-primas' },
          { name: 'Prod. Terminados',   path: '/app/inventario/productos-terminados' },
          { name: 'Kardex',             path: '/app/inventario/kardex' },
          { name: 'Carga Masiva',       path: '/app/inventario/carga-masiva' },
        ],
      },
      { name: 'Clientes',    icon: FaUsers, lineIcon: Users,     path: '/app/clientes' },
      { name: 'Proveedores', icon: FaUsers, lineIcon: Building2, path: '/app/proveedores' },
      { name: 'Guías de Remisión', icon: FaTruck, lineIcon: Truck, path: '/app/guias' },
      { name: 'Órdenes de Servicio', icon: FaTools, lineIcon: Wrench, path: '/app/servicios' },
      { name: 'Importar Excel', icon: FaFileUpload, lineIcon: FileUp, path: '/app/importador' },
    ],
  },
  {
    id: 'avanzado',
    label: 'AVANZADO',
    collapsible: true,
    items: [
      {
        name: 'Cuentas', icon: FaMoneyBillWave, lineIcon: Wallet,
        subItems: [
          { name: 'Por Cobrar', path: '/app/cuentas/por-cobrar' },
          { name: 'Por Pagar',  path: '/app/cuentas/por-pagar' },
        ],
      },
      {
        name: 'Producción', icon: FaIndustry, lineIcon: Factory,
        subItems: [
          { name: 'Dashboard',   path: '/app/produccion/dashboard' },
          { name: 'Recetas BOM', path: '/app/produccion/recetas' },
          { name: 'Órdenes',     path: '/app/produccion/ordenes' },
        ],
      },
    ],
  },
  {
    id: 'inteligencia',
    label: 'INTELIGENCIA',
    collapsible: true,
    items: [
      { name: 'Asistente Virtual', icon: FaRobot, lineIcon: Bot, path: '/app/ai-assistant' },
      // Módulo ML apagado por defecto en prod (backend: ML_ENABLED). Se muestra solo con VITE_ML_ENABLED=true.
      ...(import.meta.env.VITE_ML_ENABLED === 'true' ? [{ name: 'Machine Learning', icon: FaBrain, lineIcon: Brain, path: '/app/ml-dashboard' }] : []),
    ],
  },
];

// D6 — en empresas sin_stock se oculta el menú Inventario (y submenús).
export const seccionesVisibles = (conStock) => (
  conStock
    ? MENU_SECTIONS
    : MENU_SECTIONS.map((s) => ({ ...s, items: s.items.filter((it) => it.name !== 'Inventario') }))
);

// ─── Crear documento (FAB "+" móvil) ─────────────────────────────────────────
// Lista (ruta exacta) → documentos que crea. Con más de un tipo, el FAB abre
// una hoja para elegir; con uno, navega directo.
const NUEVA_COTIZACION = {
  titulo: 'Nueva cotización',
  documentos: [
    { label: 'Cotización de productos', icon: Package, path: '/app/cotizaciones/nueva' },
    { label: 'Cotización de servicios', icon: Wrench,  path: '/app/cotizaciones/servicios/nueva' },
  ],
};

export const CREAR_DOCUMENTO = {
  '/app/dashboard':                NUEVA_COTIZACION,
  '/app/cotizaciones':             NUEVA_COTIZACION,
  '/app/ventas':                   { titulo: 'Nueva venta', documentos: [{ label: 'Nueva venta', icon: ShoppingCart, path: '/app/ventas/nueva' }] },
  '/app/compras':                  { titulo: 'Nueva compra', documentos: [{ label: 'Nueva compra', icon: Package, path: '/app/compras/nueva' }] },
  '/app/compras/ordenes':          { titulo: 'Nueva orden de compra', documentos: [{ label: 'Nueva orden de compra', icon: Package, path: '/app/compras/orden-compra/nueva' }] },
  '/app/compras/ordenes-servicio': { titulo: 'Nueva OC de servicio', documentos: [{ label: 'Nueva OC de servicio', icon: Wrench, path: '/app/compras/orden-servicio/nueva' }] },
};

// Títulos de pantalla para la cabecera móvil. Gana el prefijo más largo.
const TITULOS = [
  ['/app/dashboard', 'Inicio'],
  ['/app/cotizaciones/nueva', 'Nueva cotización'],
  ['/app/cotizaciones/servicios/nueva', 'Nueva cotización'],
  ['/app/cotizaciones', 'Cotizaciones'],
  ['/app/ventas/nueva', 'Nueva venta'],
  ['/app/ventas', 'Ventas'],
  ['/app/compras/nueva', 'Nueva compra'],
  ['/app/compras/orden-compra', 'Orden de compra'],
  ['/app/compras/ordenes-servicio', 'OC de servicio'],
  ['/app/compras/orden-servicio', 'OC de servicio'],
  ['/app/compras/ordenes', 'Órdenes de compra'],
  ['/app/compras', 'Compras'],
  ['/app/proveedores', 'Proveedores'],
  ['/app/clientes', 'Clientes'],
  ['/app/finanzas/gastos', 'Gastos'],
  ['/app/finanzas', 'Finanzas'],
  ['/app/inventario/kardex', 'Kardex'],
  ['/app/inventario', 'Inventario'],
  ['/app/importador', 'Importar Excel'],
  ['/app/cuentas/por-cobrar', 'Por cobrar'],
  ['/app/cuentas/por-pagar', 'Por pagar'],
  ['/app/produccion', 'Producción'],
  ['/app/guias', 'Guías'],
  ['/app/servicios', 'Servicios'],
  ['/app/ai-assistant', 'Jorge'],
  ['/app/ml-dashboard', 'Machine Learning'],
  ['/app/configuracion', 'Configuración'],
];

export const tituloDePantalla = (pathname) => {
  let mejor = null;
  for (const [prefijo, titulo] of TITULOS) {
    const coincide = pathname === prefijo || pathname.startsWith(`${prefijo}/`);
    if (coincide && (!mejor || prefijo.length > mejor[0].length)) mejor = [prefijo, titulo];
  }
  return mejor ? mejor[1] : '';
};
