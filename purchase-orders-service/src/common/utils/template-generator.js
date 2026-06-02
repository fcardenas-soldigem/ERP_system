import * as XLSX from 'xlsx';

/**
 * Generates an Excel template buffer with the expected columns and example data.
 */
export function generateTemplate() {
  const wb = XLSX.utils.book_new();

  const data = [
    {
      Descripcion: 'Tubo de acero inoxidable 1/2" x 6m',
      Cantidad: 100,
      Unidad: 'UND',
      'Precio Unitario': 45.50,
    },
    {
      Descripcion: 'Válvula esférica 1/2"',
      Cantidad: 50,
      Unidad: 'UND',
      'Precio Unitario': 28.00,
    },
    {
      Descripcion: '',
      Cantidad: '',
      Unidad: '',
      'Precio Unitario': '',
    },
  ];

  const ws = XLSX.utils.json_to_sheet(data);

  ws['!cols'] = [
    { wch: 45 },
    { wch: 12 },
    { wch: 10 },
    { wch: 16 },
  ];

  XLSX.utils.book_append_sheet(wb, ws, 'Items');

  const instructions = [
    ['INSTRUCCIONES'],
    [''],
    ['Columnas requeridas:'],
    ['  - Descripcion: Nombre del producto o servicio'],
    ['  - Cantidad: Cantidad numérica (mayor a 0)'],
    ['  - Unidad: UND, KG, LT, MT, GLN, etc. (opcional, por defecto UND)'],
    ['  - Precio Unitario: Precio por unidad (mayor a 0)'],
    [''],
    ['Notas:'],
    ['  - Las filas vacías se ignoran automáticamente'],
    ['  - Los nombres de columna son flexibles: "descripcion", "description", "item", etc.'],
    ['  - Elimine las filas de ejemplo antes de subir su archivo'],
  ];

  const wsHelp = XLSX.utils.aoa_to_sheet(instructions);
  wsHelp['!cols'] = [{ wch: 60 }];
  XLSX.utils.book_append_sheet(wb, wsHelp, 'Instrucciones');

  return Buffer.from(XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' }));
}
