/**
 * Utilidades para manejo de monedas
 */

// Obtener el símbolo de moneda
export const getSimboloMoneda = (moneda) => {
  const simbolos = {
    'PEN': 'S/',
    'USD': '$'
  };
  return simbolos[moneda] || 'S/';
};

// Formatear moneda con símbolo.
// Number() coacciona montos string (DRF serializa DecimalField como string).
export const formatCurrency = (amount, moneda = 'PEN') => {
  const simbolo = getSimboloMoneda(moneda);
  return `${simbolo} ${(Number(amount) || 0).toFixed(2)}`;
};

// Formatear moneda usando Intl.NumberFormat
export const formatCurrencyIntl = (amount, moneda = 'PEN') => {
  return new Intl.NumberFormat('es-PE', {
    style: 'currency',
    currency: moneda
  }).format(Number(amount) || 0);
};

// Normaliza lo que el usuario teclea en un campo de monto MIENTRAS edita.
// - Acepta coma o punto como separador decimal (teclado numérico en Perú);
//   normaliza la coma a punto.
// - Permite estados intermedios: "" y "6371." (no bloquear mientras se escribe).
// - Rechaza cualquier otro caracter devolviendo null, para que el caller
//   IGNORE la pulsación y no borre lo ya escrito.
// La conversión a número se hace al enviar (parseFloat), no aquí.
export const sanitizeMontoInput = (value) => {
  const v = String(value ?? '').replace(/,/g, '.');
  if (v === '' || /^\d*\.?\d*$/.test(v)) return v;
  return null;
}; 