import { Router } from 'express';
import multer from 'multer';
import { purchaseOrderController } from './purchase-order.controller.js';
import {
  validateCreate,
  validateUpdate,
  validateChangeStatus,
  validateListQuery,
} from './purchase-order.validator.js';

const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 5 * 1024 * 1024 } });

export const purchaseOrderRoutes = Router();

purchaseOrderRoutes
  .post('/', validateCreate, purchaseOrderController.create)
  .get('/', validateListQuery, purchaseOrderController.findAll)
  .get('/template', purchaseOrderController.downloadTemplate)
  .post('/import', upload.single('file'), purchaseOrderController.importExcel)
  .get('/:id', purchaseOrderController.findById)
  .put('/:id', validateUpdate, purchaseOrderController.update)
  .delete('/:id', purchaseOrderController.softDelete)
  .patch('/:id/status', validateChangeStatus, purchaseOrderController.changeStatus)
  .get('/:id/pdf', purchaseOrderController.generatePdf);
