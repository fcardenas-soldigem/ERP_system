import { purchaseOrderRepository } from './purchase-order.repository.js';
import { NotFoundError, ConflictError, ForbiddenError } from '../../common/exceptions/AppError.js';
import { generatePdf } from '../../common/utils/pdf-generator.js';
import { parseExcelItems } from '../../common/utils/excel-parser.js';
import { logger } from '../../config/logger.js';

const VALID_TRANSITIONS = {
  DRAFT: ['APPROVED'],
  APPROVED: ['CLOSED', 'DRAFT'],
  CLOSED: [],
};

export class PurchaseOrderService {
  async create(dto) {
    const { items, ...headerData } = dto;

    logger.info('Creando OC para proveedor %s', dto.supplierName);

    const order = await purchaseOrderRepository.create(headerData, items);

    logger.info('OC creada: %s (id=%s)', order.poNumber, order.id);
    return order;
  }

  async findAll(query) {
    return purchaseOrderRepository.findAll(query);
  }

  async findById(id) {
    const order = await purchaseOrderRepository.findById(id);
    if (!order) throw new NotFoundError('Orden de Compra', id);
    return order;
  }

  async update(id, dto) {
    const existing = await this.findById(id);

    if (existing.status !== 'DRAFT') {
      throw new ForbiddenError('Solo se pueden editar órdenes en estado DRAFT');
    }

    const { items, ...headerData } = dto;

    const updated = await purchaseOrderRepository.update(id, headerData, items);
    logger.info('OC actualizada: %s', updated.poNumber);
    return updated;
  }

  async changeStatus(id, newStatus) {
    const existing = await this.findById(id);

    const allowed = VALID_TRANSITIONS[existing.status] || [];
    if (!allowed.includes(newStatus)) {
      throw new ConflictError(
        `No se puede cambiar de ${existing.status} a ${newStatus}. Transiciones válidas: ${allowed.join(', ') || 'ninguna'}`,
      );
    }

    const updated = await purchaseOrderRepository.changeStatus(id, newStatus);
    logger.info('OC %s: %s → %s', updated.poNumber, existing.status, newStatus);
    return updated;
  }

  async softDelete(id) {
    const existing = await this.findById(id);

    if (existing.status === 'APPROVED') {
      throw new ForbiddenError('No se puede eliminar una orden APROBADA. Ciérrela primero.');
    }

    await purchaseOrderRepository.softDelete(id);
    logger.info('OC eliminada (soft): %s', existing.poNumber);
  }

  async generatePdf(id, signatures = {}) {
    const order = await this.findById(id);
    return generatePdf(order, signatures);
  }

  async importFromExcel(buffer) {
    return parseExcelItems(buffer);
  }
}

export const purchaseOrderService = new PurchaseOrderService();
