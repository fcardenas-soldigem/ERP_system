export const TIPOS_COMPRA = {
  CONTADO: 'contado',
  CREDITO_30: 'credito_30',
  CREDITO_60: 'credito_60'
};

export const TIPOS_COMPRA_DISPLAY = {
  [TIPOS_COMPRA.CONTADO]: 'Contado',
  [TIPOS_COMPRA.CREDITO_30]: 'Crédito 30 días',
  [TIPOS_COMPRA.CREDITO_60]: 'Crédito 60 días'
};

export const METODOS_PAGO = {
  EFECTIVO: 'efectivo',
  TRANSFERENCIA: 'transferencia',
  CHEQUE: 'cheque',
  TARJETA: 'tarjeta',
  PENDIENTE: 'pendiente'
};

export const METODOS_PAGO_DISPLAY = {
  [METODOS_PAGO.EFECTIVO]: 'Efectivo',
  [METODOS_PAGO.TRANSFERENCIA]: 'Transferencia',
  [METODOS_PAGO.CHEQUE]: 'Cheque',
  [METODOS_PAGO.TARJETA]: 'Tarjeta',
  [METODOS_PAGO.PENDIENTE]: 'Pendiente'
};

export const ESTADOS_COMPRA = {
  BORRADOR: 'borrador',
  PENDIENTE: 'pendiente',
  PAGADA: 'pagada',
  ANULADA: 'anulada'
};

export const ESTADOS_DISPLAY = {
  [ESTADOS_COMPRA.BORRADOR]: 'Borrador',
  [ESTADOS_COMPRA.PENDIENTE]: 'Pendiente',
  [ESTADOS_COMPRA.PAGADA]: 'Pagada',
  [ESTADOS_COMPRA.ANULADA]: 'Anulada'
};

export const IGV_RATE = 0.18; 