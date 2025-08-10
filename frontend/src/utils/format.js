export const formatCurrency = (amount) => {
    if (amount === null || amount === undefined) return 'S/ 0.00';
    return new Intl.NumberFormat('es-PE', {
        style: 'currency',
        currency: 'PEN',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount).replace('PEN', 'S/');
}; 