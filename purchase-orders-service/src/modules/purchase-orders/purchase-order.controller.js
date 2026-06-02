import { purchaseOrderService } from './purchase-order.service.js';
import { asyncHandler } from '../../common/middleware/async-handler.js';
import { generateTemplate } from '../../common/utils/template-generator.js';

export const purchaseOrderController = {
  create: asyncHandler(async (req, res) => {
    const order = await purchaseOrderService.create(req.body);
    res.status(201).json({ success: true, data: order });
  }),

  findAll: asyncHandler(async (req, res) => {
    const result = await purchaseOrderService.findAll(req.query);
    res.json({ success: true, ...result });
  }),

  findById: asyncHandler(async (req, res) => {
    const order = await purchaseOrderService.findById(req.params.id);
    res.json({ success: true, data: order });
  }),

  update: asyncHandler(async (req, res) => {
    const order = await purchaseOrderService.update(req.params.id, req.body);
    res.json({ success: true, data: order });
  }),

  changeStatus: asyncHandler(async (req, res) => {
    const order = await purchaseOrderService.changeStatus(req.params.id, req.body.status);
    res.json({ success: true, data: order });
  }),

  softDelete: asyncHandler(async (req, res) => {
    await purchaseOrderService.softDelete(req.params.id);
    res.json({ success: true, message: 'Orden eliminada correctamente' });
  }),

  generatePdf: asyncHandler(async (req, res) => {
    const signatures = {
      firmaElaborado: req.query.firmaElaborado || null,
      firmaAprobado: req.query.firmaAprobado || null,
    };
    const pdfBuffer = await purchaseOrderService.generatePdf(req.params.id, signatures);

    res.set({
      'Content-Type': 'application/pdf',
      'Content-Disposition': `inline; filename="orden-compra-${req.params.id}.pdf"`,
      'Content-Length': pdfBuffer.length,
    });
    res.end(pdfBuffer);
  }),

  importExcel: asyncHandler(async (req, res) => {
    if (!req.file) {
      return res.status(400).json({
        success: false,
        message: 'Debe adjuntar un archivo .xlsx',
      });
    }

    const items = await purchaseOrderService.importFromExcel(req.file.buffer);
    res.json({ success: true, data: { items, count: items.length } });
  }),

  downloadTemplate: asyncHandler(async (_req, res) => {
    const buffer = generateTemplate();
    res.set({
      'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'Content-Disposition': 'attachment; filename="template_orden_compra.xlsx"',
      'Content-Length': buffer.length,
    });
    res.end(buffer);
  }),
};
