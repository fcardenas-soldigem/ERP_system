// F3 — Estado operativo de la venta (timeline). Fuente única para lista y detalle.

export const ESTADOS_OPERATIVOS = [
  'pendiente_compra',
  'comprado',
  'recibido',
  'entregado',
  'esperando_oc_nr',
  'facturado',
  'cobrado',
];

export const ESTADO_OPERATIVO_LABEL = {
  pendiente_compra: 'Pendiente de compra',
  comprado: 'Comprado',
  recibido: 'Recibido',
  entregado: 'Entregado',
  esperando_oc_nr: 'Esperando OC/NR',
  facturado: 'Facturado',
  cobrado: 'Cobrado',
};

// Siguiente estado manual + verbo del botón. 'facturado'→cobrado NO aquí
// (cobrado se sincroniza con el pago). 'cobrado' es terminal.
export const SIGUIENTE_ESTADO = {
  pendiente_compra: 'comprado',
  comprado: 'recibido',
  recibido: 'entregado',
  entregado: 'esperando_oc_nr',
  esperando_oc_nr: 'facturado',
};

export const VERBO_SIGUIENTE = {
  pendiente_compra: 'Marcar comprado',
  comprado: 'Marcar recibido',
  recibido: 'Marcar entregado',
  entregado: 'Esperando OC/NR',
  esperando_oc_nr: 'Marcar facturado',
};

// Colores por SLA (sigue la paleta Chakra del sistema).
export const SLA_COLOR_SCHEME = {
  ok: 'green',
  alerta: 'orange',
  vencido: 'red',
  sin_sla: 'gray',
};

export const SLA_LABEL = {
  ok: 'En tiempo',
  alerta: 'Por vencer',
  vencido: 'Vencido',
  sin_sla: 'Sin SLA',
};

export function estadoAnterior(actual) {
  const i = ESTADOS_OPERATIVOS.indexOf(actual);
  return i > 0 ? ESTADOS_OPERATIVOS[i - 1] : null;
}
