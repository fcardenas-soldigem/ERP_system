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

// Formatear moneda con símbolo
export const formatCurrency = (amount, moneda = 'PEN') => {
  const simbolo = getSimboloMoneda(moneda);
  return `${simbolo} ${(amount || 0).toFixed(2)}`;
};

// Formatear moneda usando Intl.NumberFormat
export const formatCurrencyIntl = (amount, moneda = 'PEN') => {
  return new Intl.NumberFormat('es-PE', {
    style: 'currency',
    currency: moneda
  }).format(amount || 0);
}; 