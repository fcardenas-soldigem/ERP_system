import PDFDocument from 'pdfkit';
import fs from 'fs';
import path from 'path';
import { config } from '../../config/index.js';
import { logger } from '../../config/logger.js';

const PRIMARY = '#2B6CB0';
const PRIMARY_LIGHT = '#EBF8FF';
const DARK = '#1a1a1a';
const GRAY = '#666666';
const BORDER = '#cccccc';
const WHITE = '#ffffff';

const SYM = { PEN: 'S/', USD: '$' };

const fmt = (n) =>
  Number(n).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const fmtDate = (d) =>
  d ? new Date(d).toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '—';

/**
 * Downloads an image from a URL and returns a Buffer, or null on failure.
 */
async function downloadImage(url) {
  try {
    if (!url) return null;
    const res = await fetch(url, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) return null;
    const arrayBuffer = await res.arrayBuffer();
    return Buffer.from(arrayBuffer);
  } catch (err) {
    logger.warn('No se pudo descargar el logo: %s', err.message);
    return null;
  }
}

/**
 * Generates a corporate Purchase Order PDF (blue theme, Interbank-style layout).
 */
export async function generatePdf(order, signatures = {}) {
  let logoBuffer = null;

  if (order.companyLogoUrl) {
    logoBuffer = await downloadImage(order.companyLogoUrl);
  }

  if (!logoBuffer) {
    const localPath = path.resolve(config.companyLogoPath);
    if (fs.existsSync(localPath)) {
      try { logoBuffer = fs.readFileSync(localPath); } catch { /* skip */ }
    }
  }

  const sigBuffers = {};
  if (signatures.firmaElaborado) {
    sigBuffers.elaborado = await downloadImage(signatures.firmaElaborado);
  }
  if (signatures.firmaAprobado) {
    sigBuffers.aprobado = await downloadImage(signatures.firmaAprobado);
  }

  return new Promise((resolve, reject) => {
    const doc = new PDFDocument({ size: 'A4', margin: 36, bufferPages: true });
    const chunks = [];
    doc.on('data', (c) => chunks.push(c));
    doc.on('end', () => resolve(Buffer.concat(chunks)));
    doc.on('error', reject);

    const sym = SYM[order.currency] || 'S/';
    const W = doc.page.width - 72;
    const L = 36;

    drawPageHeader(doc, order, W, L, logoBuffer);
    drawSupplierSection(doc, order, W, L);
    drawCompanySection(doc, order, W, L);
    drawConditionsBar(doc, order, W, L);
    drawItemsTable(doc, order.items, W, L, sym);
    drawObservationsAndTotals(doc, order, W, L, sym);
    drawDeliverySection(doc, order, W, L);
    drawConsiderationsSection(doc, order, W, L);
    drawAuthorizationSection(doc, W, L, sigBuffers);

    // ── Footer en cada página ──
    const totalPages = doc.bufferedPageRange().count;
    for (let i = 0; i < totalPages; i++) {
      doc.switchToPage(i);
      const footerY = doc.page.height - 28;
      doc.moveTo(L, footerY).lineTo(L + W, footerY).strokeColor(BORDER).lineWidth(0.5).stroke();
      doc.font('Helvetica').fontSize(7).fillColor(GRAY);
      doc.text(order.poNumber, L, footerY + 5, { width: W / 3, align: 'left' });
      doc.text(`Página ${i + 1} de ${totalPages}`, L, footerY + 5, { width: W, align: 'center' });
      doc.text(fmtDate(new Date()), L, footerY + 5, { width: W, align: 'right' });
    }

    doc.end();
  });
}

// ─── Drawing helpers ────────────────────────────

function bar(doc, text, y, W, L) {
  const h = 20;
  doc.rect(L, y, W, h).fill(PRIMARY);
  doc.font('Helvetica-Bold').fontSize(9).fillColor(WHITE);
  doc.text(text, L + 8, y + 5, { width: W - 16 });
  return y + h;
}

function hLine(doc, y, W, L) {
  doc.moveTo(L, y).lineTo(L + W, y).strokeColor(BORDER).lineWidth(0.5).stroke();
}

// ─── Sections ───────────────────────────────────

function drawPageHeader(doc, order, W, L, logoBuffer) {
  if (logoBuffer) {
    try { doc.image(logoBuffer, L, 22, { width: 120, height: 60, fit: [120, 60] }); } catch { /* skip */ }
  }

  const rightX = L + W - 230;
  const rightW = 230;

  doc.font('Helvetica').fontSize(7.5).fillColor(GRAY);
  doc.text(`Fecha de Emisión: ${fmtDate(order.issueDate)}`, rightX, 28, { width: rightW, align: 'right' });

  doc.font('Helvetica-Bold').fontSize(9).fillColor(DARK);
  doc.text('Nro Orden de Compra:', rightX, 44, { width: rightW, align: 'right' });

  doc.font('Helvetica-Bold').fontSize(18).fillColor(PRIMARY);
  doc.text(order.poNumber, rightX, 56, { width: rightW, align: 'right' });

  doc.y = 90;
}

function drawSupplierSection(doc, order, W, L) {
  let y = doc.y + 4;
  y = bar(doc, 'DATOS DEL PROVEEDOR', y, W, L);

  const half = W / 2;
  const PAD = 4;
  const LABEL_W = 58; // ancho aprox del label "Razón Social: "
  const valueW = half - PAD * 2 - LABEL_W;

  /** Alto dinámico de una fila según el texto más alto de sus dos columnas */
  function rowHeight(leftVal, rightVal, leftLabelW = LABEL_W, rightLabelW = LABEL_W) {
    const lH = doc.font('Helvetica').fontSize(7.5)
      .heightOfString(leftVal  || '—', { width: half - PAD * 2 - leftLabelW });
    const rH = doc.font('Helvetica').fontSize(7.5)
      .heightOfString(rightVal || '—', { width: half - PAD * 2 - rightLabelW });
    return Math.max(16, Math.max(lH, rH) + 8);
  }

  const nameText = order.supplierName  || '—';
  const addrText = order.supplierAddress || '—';

  const rows = [
    {
      pairs: [['Razón Social', nameText], ['RUC', order.supplierRuc]],
      h: rowHeight(nameText, order.supplierRuc, LABEL_W, 22),
    },
    {
      pairs: [['Dirección', addrText], ['Forma de Pago', order.paymentTerms || '—']],
      h: rowHeight(addrText, order.paymentTerms, LABEL_W, 60),
    },
    {
      pairs: [['Contacto', order.supplierContact], ['Mail', order.supplierEmail]],
      h: 16,
    },
  ];

  const totalH = rows.reduce((sum, r) => sum + r.h, 0);
  doc.rect(L, y, W, totalH).stroke(BORDER);

  for (let ri = 0; ri < rows.length; ri++) {
    const { pairs, h } = rows[ri];
    let x = L + PAD;
    for (const [label, value] of pairs) {
      // Label en negrita
      doc.font('Helvetica-Bold').fontSize(7.5).fillColor(DARK);
      const labelText = `${label}: `;
      const labelW = doc.widthOfString(labelText);
      doc.text(labelText, x, y + PAD, { width: labelW, lineBreak: false });
      // Valor en regular (alineado justo después del label)
      doc.font('Helvetica').fontSize(7.5).fillColor(DARK);
      doc.text(value || '—', x + labelW, y + PAD, { width: half - PAD * 2 - labelW });
      x += half;
    }
    y += h;
    if (ri < rows.length - 1) hLine(doc, y, W, L);
  }

  doc.y = y + 2;
}

function drawCompanySection(doc, order, W, L) {
  let y = doc.y;
  y = bar(doc, 'DATOS DE LA COMPAÑÍA', y, W, L);

  const PAD = 4;
  const half = W / 2;
  const nameText = order.companyName  || '—';
  const addrText = order.companyAddress || '—';

  const facturarLabelW = doc.font('Helvetica-Bold').fontSize(7.5).widthOfString('Facturar a: ');
  const rucLabelW      = doc.font('Helvetica-Bold').fontSize(7.5).widthOfString('RUC: ');
  const addrLabelW     = doc.font('Helvetica-Bold').fontSize(7.5).widthOfString('Dirección: ');

  const nameH = Math.max(16, doc.font('Helvetica').fontSize(7.5)
    .heightOfString(nameText, { width: half - PAD * 2 - facturarLabelW }) + 8);
  const addrH = Math.max(16, doc.font('Helvetica').fontSize(7.5)
    .heightOfString(addrText, { width: W - PAD * 2 - addrLabelW }) + 8);
  const boxH = nameH + addrH;

  doc.rect(L, y, W, boxH).stroke(BORDER);

  // Fila 1: Facturar a + RUC
  doc.font('Helvetica-Bold').fontSize(7.5).fillColor(DARK);
  doc.text('Facturar a: ', L + PAD, y + PAD, { width: facturarLabelW, lineBreak: false });
  doc.font('Helvetica').fontSize(7.5).fillColor(DARK);
  doc.text(nameText, L + PAD + facturarLabelW, y + PAD, { width: half - PAD * 2 - facturarLabelW });

  doc.font('Helvetica-Bold').fontSize(7.5).fillColor(DARK);
  doc.text('RUC: ', L + half + PAD, y + PAD, { width: rucLabelW, lineBreak: false });
  doc.font('Helvetica').fontSize(7.5).fillColor(DARK);
  doc.text(order.companyRuc || '—', L + half + PAD + rucLabelW, y + PAD, { width: half - PAD * 2 - rucLabelW });

  hLine(doc, y + nameH, W, L);

  // Fila 2: Dirección
  doc.font('Helvetica-Bold').fontSize(7.5).fillColor(DARK);
  doc.text('Dirección: ', L + PAD, y + nameH + PAD, { width: addrLabelW, lineBreak: false });
  doc.font('Helvetica').fontSize(7.5).fillColor(DARK);
  doc.text(addrText, L + PAD + addrLabelW, y + nameH + PAD, { width: W - PAD * 2 - addrLabelW });

  doc.y = y + boxH + 2;
}

function drawConditionsBar(doc, order, W, L) {
  let y = doc.y;
  y = bar(doc, 'CONDICIONES DE LA COMPAÑÍA', y, W, L);

  const boxH = 14;
  doc.rect(L, y, W, boxH).stroke(BORDER);

  const moneda = order.currency === 'USD' ? 'Dólar Estadounidense' : 'Sol Peruano';
  doc.font('Helvetica-Bold').fontSize(7.5).fillColor(DARK);
  doc.text(`Moneda: ${moneda}`, L + 4, y + 3, { width: W / 2 });
  doc.text(`Término de Pago: ${order.paymentTerms || '—'}`, L + W / 2, y + 3, { width: W / 2 });

  doc.y = y + boxH;
}

function drawItemsTable(doc, items, W, L, sym) {
  const PAD = 3;
  const cols = [
    { label: 'N°',          w: 26,                           align: 'center' },
    { label: 'Descripción', w: W - 26 - 50 - 36 - 74 - 78,  align: 'left'   },
    { label: 'Cant.',       w: 50,                           align: 'center' },
    { label: 'U.M.',        w: 36,                           align: 'center' },
    { label: 'P. Unitario', w: 74,                           align: 'right'  },
    { label: 'Importe',     w: 78,                           align: 'right'  },
  ];
  const descColW = cols[1].w;

  /**
   * Calcula la altura que ocupará la descripción de un ítem,
   * tratando la primera línea (modelo/SN) como negrita 7.5pt
   * y las siguientes (trabajos) como regular 7pt con sangría.
   */
  function calcDescHeight(descText) {
    if (!descText) return 12;
    const lines = descText.split('\n').filter((l) => l !== undefined);
    let total = 0;
    lines.forEach((line, i) => {
      const font = i === 0 ? 'Helvetica-Bold' : 'Helvetica';
      const size = i === 0 ? 7.5 : 7;
      const usableW = i === 0 ? descColW - PAD * 2 : descColW - PAD * 2 - 6;
      doc.font(font).fontSize(size);
      total += doc.heightOfString(line || ' ', { width: usableW, lineGap: 0.5 });
      if (i < lines.length - 1) total += 1;
    });
    return total;
  }

  /** Dibuja el encabezado de la tabla y devuelve la Y siguiente */
  const drawHeader = (yPos) => {
    doc.rect(L, yPos, W, 16).fill(PRIMARY);
    doc.font('Helvetica-Bold').fontSize(7).fillColor(WHITE);
    let hx = L;
    for (const col of cols) {
      doc.text(col.label, hx + PAD, yPos + 5, { width: col.w - PAD * 2, align: 'center' });
      hx += col.w;
    }
    return yPos + 16;
  };

  let y = drawHeader(doc.y);

  items.forEach((item, idx) => {
    const descText = item.description || '';
    const descLines = descText.split('\n').filter((l) => l !== undefined);

    const descH = calcDescHeight(descText);
    const rowH = Math.max(22, descH + 8);

    // Nueva página si la fila no cabe
    if (y + rowH > 752) {
      doc.addPage();
      y = drawHeader(36);
    }

    // Fondo alternado
    const bg = idx % 2 === 0 ? WHITE : PRIMARY_LIGHT;
    doc.rect(L, y, W, rowH).fillAndStroke(bg, BORDER);

    let x = L;

    // ── N° (centrado vertical) ──
    doc.font('Helvetica').fontSize(7.5).fillColor(GRAY);
    doc.text(String(idx + 1), x + PAD, y + (rowH - 9) / 2, {
      width: cols[0].w - PAD * 2, align: 'center',
    });
    x += cols[0].w;

    // ── Descripción (primera línea en negrita, resto sangrado) ──
    let descY = y + PAD + 1;
    descLines.forEach((line, li) => {
      const isHeader = li === 0;
      const font = isHeader ? 'Helvetica-Bold' : 'Helvetica';
      const size = isHeader ? 7.5 : 7;
      const indent = isHeader ? 0 : 6;
      const usableW = descColW - PAD * 2 - indent;
      doc.font(font).fontSize(size).fillColor(isHeader ? DARK : '#444444');
      const lh = doc.heightOfString(line || ' ', { width: usableW, lineGap: 0.5 });
      doc.text(line, x + PAD + indent, descY, { width: usableW, align: 'left', lineGap: 0.5 });
      descY += lh + 1;
    });
    x += cols[1].w;

    // ── Cant. / U.M. / P.Unit / Importe (centrados verticalmente) ──
    const midY = y + (rowH - 9) / 2;
    const rightCells = [
      { text: fmt(item.quantity),             align: 'center' },
      { text: item.unit || 'UND',             align: 'center' },
      { text: `${sym} ${fmt(item.unitPrice)}`, align: 'right'  },
      { text: `${sym} ${fmt(item.total)}`,    align: 'right'  },
    ];
    rightCells.forEach((cell, i) => {
      const col = cols[i + 2];
      doc.font('Helvetica').fontSize(7.5).fillColor(DARK);
      doc.text(cell.text, x + PAD, midY, { width: col.w - PAD * 2, align: cell.align });
      x += col.w;
    });

    y += rowH;
  });

  doc.y = y;
}

function drawObservationsAndTotals(doc, order, W, L, sym) {
  const incluyeIgv = !!order.incluyeIgv;
  const subtotalN     = Number(order.subtotal ?? 0);
  const baseImponible = Number(order.baseImponible ?? 0);
  const igvN          = Number(order.igv ?? 0);
  const totalN        = Number(order.total ?? 0);
  const descuentoMonto = Number(order.descuentoMonto ?? 0);

  // Construir filas de totales dinámicamente
  const rows = [];

  if (incluyeIgv) {
    rows.push({ label: 'Sub Total (c/IGV):', val: subtotalN, bold: false });
  } else {
    rows.push({ label: 'Sub Total:', val: subtotalN, bold: false });
  }

  if (descuentoMonto > 0) {
    rows.push({ label: 'Descuento:', val: `-${sym} ${fmt(descuentoMonto)}`, raw: true, bold: false, color: '#CC3333' });
    const netoConDesc = subtotalN - descuentoMonto;
    rows.push({ label: 'Subtotal neto:', val: netoConDesc, bold: false, color: '#555555' });
  }

  if (incluyeIgv) {
    rows.push({ label: 'Base imponible:', val: baseImponible, bold: false, color: '#555555' });
    rows.push({ label: 'IGV 18% (incluido):', val: igvN, bold: false });
  } else {
    rows.push({ label: 'IGV (18%):', val: igvN, bold: false });
  }

  rows.push({ label: 'TOTAL:', val: totalN, bold: true });

  const rH = 15;
  const totW = 195;
  const totH = rows.length * rH;
  const obsW = W - totW;
  const obsH = Math.max(totH, 40);

  let y = doc.y + 2;
  if (y > 720) { doc.addPage(); y = 36; }

  // Observaciones
  doc.rect(L, y, obsW, obsH).stroke(BORDER);
  doc.font('Helvetica-Bold').fontSize(7).fillColor(DARK);
  doc.text('Observaciones:', L + 4, y + 4, { width: obsW - 8 });
  doc.font('Helvetica').fontSize(7).fillColor(GRAY);
  doc.text(order.considerations || '—', L + 4, y + 14, { width: obsW - 8, height: obsH - 18 });

  // Totales
  const tx = L + obsW;
  rows.forEach((row, i) => {
    const rowY = y + i * rH;
    const isTotalRow = row.bold;

    // Fondo
    if (isTotalRow) {
      doc.rect(tx, rowY, totW, rH).fill(PRIMARY).stroke(BORDER);
    } else {
      doc.rect(tx, rowY, totW, rH).fillAndStroke(WHITE, BORDER);
    }

    const textColor = isTotalRow ? WHITE : (row.color || DARK);
    const font = isTotalRow ? 'Helvetica-Bold' : 'Helvetica';
    const fontSize = isTotalRow ? 9 : 7.5;
    const labelW = 100;

    doc.font(font).fontSize(fontSize).fillColor(textColor);
    doc.text(row.label, tx + 5, rowY + (rH - fontSize) / 2, { width: labelW });

    const valText = row.raw ? row.val : `${sym}  ${fmt(row.val)}`;
    doc.font(font).fontSize(fontSize).fillColor(textColor);
    doc.text(valText, tx + labelW + 5, rowY + (rH - fontSize) / 2, {
      width: totW - labelW - 12,
      align: 'right',
    });
  });

  doc.y = y + obsH + 4;
}

function drawDeliverySection(doc, order, W, L) {
  if (!order.deliveryConditions) return;
  let y = doc.y + 2;
  if (y > 720) { doc.addPage(); y = 36; }
  y = bar(doc, 'CONDICIONES DE ENTREGA', y, W, L);
  doc.rect(L, y, W, 28).stroke(BORDER);
  doc.font('Helvetica').fontSize(7.5).fillColor(DARK);
  doc.text(order.deliveryConditions, L + 4, y + 4, { width: W - 8 });
  doc.y = y + 30;
}

function drawConsiderationsSection(doc, order, W, L) {
  if (!order.considerations) return;
  let y = doc.y + 2;
  if (y > 720) { doc.addPage(); y = 36; }
  y = bar(doc, 'CONSIDERACIONES', y, W, L);
  doc.rect(L, y, W, 22).stroke(BORDER);
  doc.font('Helvetica').fontSize(7.5).fillColor(DARK);
  doc.text(order.considerations, L + 4, y + 4, { width: W - 8 });
  doc.y = y + 24;
}

function drawAuthorizationSection(doc, W, L, sigBuffers = {}) {
  let y = doc.y + 2;
  if (y > 650) { doc.addPage(); y = 36; }
  y = bar(doc, 'AUTORIZACIONES', y, W, L);

  const half = W / 2;
  const sigW = 160;
  const sigImgH = 60;

  const positions = [
    { x: L + (half - sigW) / 2, label: 'Preparada por', buf: sigBuffers.elaborado },
    { x: L + half + (half - sigW) / 2, label: 'Aprobada por', buf: sigBuffers.aprobado },
  ];

  for (const { x, label, buf } of positions) {
    if (buf) {
      try {
        doc.image(buf, x + (sigW - 120) / 2, y + 8, { width: 120, height: sigImgH, fit: [120, sigImgH] });
      } catch { /* skip */ }
    }
  }

  y += sigImgH + 16;

  for (const { x, label } of positions) {
    doc.moveTo(x, y).lineTo(x + sigW, y).strokeColor(DARK).lineWidth(0.5).stroke();
    doc.font('Helvetica').fontSize(8).fillColor(GRAY);
    doc.text(label, x, y + 4, { width: sigW, align: 'center' });
  }
}
