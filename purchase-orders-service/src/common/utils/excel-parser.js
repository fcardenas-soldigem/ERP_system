import * as XLSX from 'xlsx';
import { ValidationError } from '../exceptions/AppError.js';

/**
 * Column mapping – keys are lowercase/normalized header names,
 * values are our internal field names.
 */
const COLUMN_MAP = {
  descripcion: 'description',
  description: 'description',
  desc: 'description',
  item: 'description',
  producto: 'description',

  cantidad: 'quantity',
  quantity: 'quantity',
  qty: 'quantity',
  cant: 'quantity',

  unidad: 'unit',
  unit: 'unit',
  und: 'unit',

  'precio unitario': 'unitPrice',
  'precio_unitario': 'unitPrice',
  'unit price': 'unitPrice',
  unitprice: 'unitPrice',
  precio: 'unitPrice',
  'p.unit': 'unitPrice',
  'p. unit': 'unitPrice',
  'p.u.': 'unitPrice',
};

function normalize(header) {
  return String(header).toLowerCase().trim().replace(/[_\-.]+/g, ' ').replace(/\s+/g, ' ');
}

/**
 * Parses an Excel buffer and returns an array of validated items.
 * @param {Buffer} buffer
 * @returns {Array<{description: string, quantity: number, unitPrice: number, unit: string}>}
 */
export function parseExcelItems(buffer) {
  const workbook = XLSX.read(buffer, { type: 'buffer' });
  const sheetName = workbook.SheetNames[0];

  if (!sheetName) {
    throw new ValidationError('El archivo Excel no contiene hojas');
  }

  const rows = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], { defval: '' });

  if (rows.length === 0) {
    throw new ValidationError('El archivo Excel está vacío');
  }

  // Detect column mapping from the first row's keys
  const rawHeaders = Object.keys(rows[0]);
  const mapping = {};

  for (const raw of rawHeaders) {
    const norm = normalize(raw);
    if (COLUMN_MAP[norm]) {
      mapping[raw] = COLUMN_MAP[norm];
    }
  }

  if (!Object.values(mapping).includes('description')) {
    throw new ValidationError(
      'No se encontró la columna de descripción. Use: descripcion, description, item o producto',
    );
  }
  if (!Object.values(mapping).includes('unitPrice')) {
    throw new ValidationError(
      'No se encontró la columna de precio unitario. Use: precio unitario, unitPrice o precio',
    );
  }
  if (!Object.values(mapping).includes('quantity')) {
    throw new ValidationError(
      'No se encontró la columna de cantidad. Use: cantidad, quantity o qty',
    );
  }

  const items = [];
  const errors = [];

  rows.forEach((row, idx) => {
    const mapped = {};
    for (const [rawKey, field] of Object.entries(mapping)) {
      mapped[field] = row[rawKey];
    }

    const description = String(mapped.description || '').trim();
    const quantity = parseFloat(mapped.quantity);
    const unitPrice = parseFloat(mapped.unitPrice);
    const unit = String(mapped.unit || 'UND').trim();

    if (!description) {
      errors.push(`Fila ${idx + 2}: descripción vacía`);
      return;
    }
    if (isNaN(quantity) || quantity <= 0) {
      errors.push(`Fila ${idx + 2}: cantidad inválida (${mapped.quantity})`);
      return;
    }
    if (isNaN(unitPrice) || unitPrice <= 0) {
      errors.push(`Fila ${idx + 2}: precio unitario inválido (${mapped.unitPrice})`);
      return;
    }

    items.push({ description, quantity, unitPrice, unit });
  });

  if (errors.length > 0 && items.length === 0) {
    throw new ValidationError('Ninguna fila válida en el archivo', errors);
  }

  if (items.length === 0) {
    throw new ValidationError('El archivo no contiene items válidos');
  }

  return items;
}
