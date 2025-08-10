// Estados para las diferentes entidades
export const ESTADOS_COMPRA = {
  PENDIENTE: 'pendiente',
  COMPLETADA: 'completada',
  CANCELADA: 'cancelada'
};

export const ESTADOS_ORDEN_COMPRA = {
  PENDIENTE: 'pendiente',
  APROBADA: 'aprobada',
  RECIBIDA: 'recibida',
  CANCELADA: 'cancelada'
};

// Interfaces/Types para las entidades
export const CompraType = {
  id: 'number',
  empresa: 'number',
  proveedor: 'number',
  proveedor_nombre: 'string',
  almacen: 'number',
  almacen_nombre: 'string',
  numero_orden: 'string',
  fecha: 'string',
  estado: 'string',
  producto: 'number',
  producto_nombre: 'string',
  cantidad: 'number',
  precio_unitario: 'number',
  sku: 'string',
  subtotal: 'number',
  igv: 'number',
  total: 'number',
  igv_incluido: 'boolean'
};

export const OrdenCompraType = {
  id: 'number',
  empresa: 'number',
  proveedor: 'number',
  proveedor_nombre: 'string',
  almacen: 'number',
  almacen_nombre: 'string',
  numero_orden: 'string',
  fecha: 'string',
  estado: 'string',
  producto: 'number',
  producto_nombre: 'string',
  cantidad: 'number',
  precio_unitario: 'number',
  sku: 'string',
  subtotal: 'number',
  igv: 'number',
  total: 'number',
  igv_incluido: 'boolean'
};

export const ProveedorType = {
  id: 'number',
  empresa: 'number',
  nombre: 'string',
  ruc: 'string',
  direccion: 'string',
  telefono: 'string',
  email: 'string',
  activo: 'boolean'
};

export const RecepcionCompraType = {
  id: 'number',
  orden_compra: 'number',
  orden_compra_numero: 'string',
  orden_compra_proveedor: 'string',
  fecha_recepcion: 'string',
  recibido_por: 'string',
  notas: 'string',
  fecha_registro: 'string',
  fecha_actualizacion: 'string'
}; 