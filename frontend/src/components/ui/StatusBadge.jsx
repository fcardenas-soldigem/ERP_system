import React from 'react';
import { Badge } from '@chakra-ui/react';

/**
 * StatusBadge — EL ÚNICO mapa estado → color del sistema.
 * Ventas, compras, OC, cotizaciones y guías usan esta tabla; prohibido
 * definir colorScheme de estados en pantallas individuales.
 *
 * Semántica (3 colores + neutral + brand, nada de morados/naranjas):
 *   verde  = terminado bien (pagado, aprobada, aceptada, entregada…)
 *   ámbar  = esperando algo (pendiente, enviada, parcial…)
 *   rojo   = terminado mal (anulado, rechazada, vencida)
 *   gris   = aún no es real (borrador)
 *   brand  = en proceso operativo (convertida, facturada, completada)
 */
const ESTADO_COLOR = {
  // Comunes
  borrador: 'gray',
  pendiente: 'yellow',
  anulado: 'red',
  anulada: 'red',
  // Ventas / pagos
  pagado: 'green',
  pagada: 'green',
  parcial: 'yellow',
  // OC / OCS
  enviada: 'yellow',
  aprobada: 'green',
  rechazada: 'red',
  completada: 'blue',
  facturada: 'blue',
  // Cotizaciones
  aceptada: 'green',
  vencida: 'red',
  convertida: 'blue',
  // Guías / entregas
  emitida: 'yellow',
  entregada: 'green',
  en_transito: 'yellow',
};

const LABELS = {
  en_transito: 'En tránsito',
};

const StatusBadge = ({ estado, children, ...rest }) => {
  const key = String(estado ?? '').toLowerCase();
  const colorScheme = ESTADO_COLOR[key] ?? 'gray';
  const label = children ?? LABELS[key] ?? (key.charAt(0).toUpperCase() + key.slice(1));
  return (
    <Badge colorScheme={colorScheme} variant="subtle" {...rest}>
      {label}
    </Badge>
  );
};

export { ESTADO_COLOR };
export default StatusBadge;
