/**
 * Helper ÚNICO de formato de fechas para la UI (locale es-PE).
 * El backend entrega fechas ISO (YYYY-MM-DD); aquí se vuelven dd/mm/yyyy.
 * No usar toLocaleDateString suelto ni mostrar ISO crudo en pantalla.
 */

// 'YYYY-MM-DD' (o Date) → 'dd/mm/yyyy'. Evita el shift de zona horaria
// parseando el ISO como fecha local, no UTC.
export const formatFecha = (iso) => {
  if (!iso) return '—';
  if (iso instanceof Date) {
    return iso.toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit', year: 'numeric' });
  }
  const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return String(iso);
  return `${m[3]}/${m[2]}/${m[1]}`;
};

// Rango corto: '01/10 – 31/10/2026'
export const formatRango = (isoIni, isoFin) => {
  const ini = formatFecha(isoIni);
  const fin = formatFecha(isoFin);
  if (ini === '—' || fin === '—') return `${ini} – ${fin}`;
  return `${ini.slice(0, 5)} – ${fin}`;
};
