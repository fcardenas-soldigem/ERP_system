import {
  Zap, TrendingUp, Coins, FileCheck, Activity, Package, FileText,
  type LucideIcon,
} from 'lucide-react';

export interface Feature {
  icon: LucideIcon;
  title: string;
  body: string;
}

// Las 7 funciones REALES que existen hoy. Nada de "facturación electrónica".
export const FEATURES: Feature[] = [
  {
    icon: Zap,
    title: 'De cotización a venta y OC en 1 clic',
    body: 'Aceptas la cotización y el sistema crea la venta y las órdenes de compra por proveedor, agrupadas solas. Sin recapturar nada.',
  },
  {
    icon: TrendingUp,
    title: 'Margen real por venta',
    body: 'El costo viaja desde la cotización, la OC y la factura del proveedor. Ves la utilidad real de cada venta, no una estimación.',
  },
  {
    icon: Coins,
    title: 'Multimoneda USD / PEN',
    body: 'Cada documento guarda el tipo de cambio SBS del día que se emitió. Los totales históricos no se mueven cuando el dólar cambia.',
  },
  {
    icon: FileCheck,
    title: 'IGV listo para SUNAT',
    body: 'IGV por pagar y crédito fiscal calculados por devengo. Sabes cuánto le debes a SUNAT este mes sin armar el PDT a mano.',
  },
  {
    icon: Activity,
    title: 'Estado operativo de cada venta',
    body: 'Comprado, recibido, entregado, cobrado. Con alertas cuando una venta se demora más de lo normal.',
  },
  {
    icon: Package,
    title: 'Con o sin inventario',
    body: 'Funciona igual si manejas stock o si trabajas a pedido contra proveedor. Una sola herramienta para los dos modelos.',
  },
  {
    icon: FileText,
    title: 'Guías, órdenes de servicio y PDFs',
    body: 'Guías de remisión, órdenes de servicio técnico y documentos en PDF con la cara de tu empresa, listos para enviar.',
  },
];

export const COMING_SOON = [
  'WhatsApp para cotizar y cobrar',
  'Conexión con Shopify',
  'Agentes de IA que hacen el seguimiento por ti',
];

export const RUBROS = [
  'Distribución / mayorista',
  'Integrador / proyectos',
  'Servicio técnico',
  'Comercio B2B',
  'Otro',
];

export const TAMANOS = [
  { value: '1-5', label: '1 a 5 personas' },
  { value: '6-20', label: '6 a 20 personas' },
  { value: '21-50', label: '21 a 50 personas' },
  { value: '50+', label: 'Más de 50 personas' },
];
