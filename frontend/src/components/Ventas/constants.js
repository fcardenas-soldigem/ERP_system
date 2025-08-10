export const ESTADOS_VENTA = {
  BORRADOR: 'borrador',
  PENDIENTE: 'pendiente',
  PAGADO: 'pagado',
  ANULADO: 'anulado'
};

export const TIPOS_VENTA = {
  CONTADO: 'contado',
  CREDITO_30: 'credito_30',
  CREDITO_60: 'credito_60'
};

export const METODOS_PAGO = {
  EFECTIVO: 'efectivo',
  TRANSFERENCIA: 'transferencia',
  CHEQUE: 'cheque',
  TARJETA: 'tarjeta'
};

export const ESTADOS_DISPLAY = {
  [ESTADOS_VENTA.BORRADOR]: 'Borrador',
  [ESTADOS_VENTA.PENDIENTE]: 'Pendiente',
  [ESTADOS_VENTA.PAGADO]: 'Pagado',
  [ESTADOS_VENTA.ANULADO]: 'Anulado'
};

export const TIPOS_VENTA_DISPLAY = {
  [TIPOS_VENTA.CONTADO]: 'Contado',
  [TIPOS_VENTA.CREDITO_30]: 'Crédito 30 días',
  [TIPOS_VENTA.CREDITO_60]: 'Crédito 60 días'
};

export const METODOS_PAGO_DISPLAY = {
  [METODOS_PAGO.EFECTIVO]: 'Efectivo',
  [METODOS_PAGO.TRANSFERENCIA]: 'Transferencia',
  [METODOS_PAGO.CHEQUE]: 'Cheque',
  [METODOS_PAGO.TARJETA]: 'Tarjeta'
};

export const IGV_RATE = 0.18;

export const ESTADOS_VENTA_COLORS = {
  [ESTADOS_VENTA.BORRADOR]: 'gray',
  [ESTADOS_VENTA.PENDIENTE]: 'yellow',
  [ESTADOS_VENTA.PAGADO]: 'green',
  [ESTADOS_VENTA.ANULADO]: 'red'
}; 