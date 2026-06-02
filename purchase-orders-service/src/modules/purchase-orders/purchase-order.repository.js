import prisma from '../../prisma/client.js';

const INCLUDE_ITEMS = { items: { orderBy: { sortOrder: 'asc' } } };
const INCLUDE_ALL = { items: { orderBy: { sortOrder: 'asc' } }, files: true };

/**
 * Calcula subtotal, baseImponible, igv, total y descuentoMonto
 * respetando incluyeIgv y la lógica de descuento.
 */
function calcTotals(items, data = {}) {
  const rawSubtotal = items.reduce(
    (acc, i) => acc + Number(i.quantity) * Number(i.unitPrice),
    0,
  );

  const descuentoTipo = data.descuentoTipo || data.descuento_tipo || 'porcentaje';
  const descuentoValorRaw = Number(data.descuentoValor ?? data.descuento_valor ?? 0);
  const descuentoMonto = descuentoTipo === 'porcentaje'
    ? +(rawSubtotal * descuentoValorRaw / 100).toFixed(2)
    : +Math.min(descuentoValorRaw, rawSubtotal).toFixed(2);

  const netoConDesc = Math.max(0, rawSubtotal - descuentoMonto);
  const incluyeIgv = !!(data.incluyeIgv);

  let baseImponible, igv, total;
  if (incluyeIgv) {
    baseImponible = +(netoConDesc / 1.18).toFixed(2);
    igv = +(netoConDesc - baseImponible).toFixed(2);
    total = +netoConDesc.toFixed(2);
  } else {
    baseImponible = +netoConDesc.toFixed(2);
    igv = +(netoConDesc * 0.18).toFixed(2);
    total = +(netoConDesc + igv).toFixed(2);
  }

  return {
    subtotal: +rawSubtotal.toFixed(2),
    baseImponible,
    igv,
    total,
    descuentoMonto,
  };
}

function notDeleted(extra = {}) {
  return { deletedAt: null, ...extra };
}

/**
 * Normaliza el payload del frontend (snake_case + campos desconocidos)
 * a los campos camelCase que espera Prisma, descartando lo que no reconoce.
 */
function toPrismaData(raw) {
  const allowed = [
    'supplierName', 'supplierRuc', 'supplierAddress', 'supplierContact', 'supplierEmail',
    'companyName', 'companyRuc', 'companyAddress', 'companyLogoUrl',
    'currency', 'paymentTerms', 'issueDate', 'dueDate',
    'deliveryConditions', 'considerations',
    'status', 'empresaId',
  ];

  const result = {};
  for (const field of allowed) {
    if (raw[field] !== undefined) result[field] = raw[field];
  }

  // Campos con posible snake_case desde el frontend
  result.incluyeIgv    = !!raw.incluyeIgv;
  result.orderType     = raw.orderType     || 'productos';
  result.descuentoTipo  = raw.descuentoTipo  || raw.descuento_tipo  || 'porcentaje';
  result.descuentoValor = raw.descuentoValor ?? raw.descuento_valor ?? 0;
  result.descuentoMonto = raw.descuentoMonto ?? raw.descuento_monto ?? 0;

  return result;
}

export class PurchaseOrderRepository {
  async create(data, items) {
    return prisma.$transaction(async (tx) => {
      const poNumber = await this.#nextPoNumber(tx);
      const clean = toPrismaData(data);
      const { subtotal, baseImponible, igv, total, descuentoMonto } = calcTotals(items, clean);

      return tx.purchaseOrder.create({
        data: {
          ...clean,
          poNumber,
          subtotal,
          baseImponible,
          igv,
          total,
          descuentoMonto: clean.descuentoMonto || descuentoMonto,
          items: {
            create: items.map((item, idx) => ({
              description: item.description,
              quantity: item.quantity,
              unit: item.unit || 'UND',
              unitPrice: item.unitPrice,
              total: +(Number(item.quantity) * Number(item.unitPrice)).toFixed(2),
              sortOrder: idx,
            })),
          },
        },
        include: INCLUDE_ALL,
      });
    }, { timeout: 30000 });
  }

  async findAll({ page, limit, status, currency, supplierRuc, search, sortBy, sortOrder, from, to }) {
    const where = notDeleted();

    if (status) where.status = status;
    if (currency) where.currency = currency;
    if (supplierRuc) where.supplierRuc = supplierRuc;
    if (from || to) {
      where.issueDate = {};
      if (from) where.issueDate.gte = new Date(from);
      if (to) where.issueDate.lte = new Date(to);
    }
    if (search) {
      where.OR = [
        { poNumber: { contains: search, mode: 'insensitive' } },
        { supplierName: { contains: search, mode: 'insensitive' } },
        { companyName: { contains: search, mode: 'insensitive' } },
      ];
    }

    const skip = (page - 1) * limit;

    const [data, totalCount] = await Promise.all([
      prisma.purchaseOrder.findMany({
        where,
        include: INCLUDE_ITEMS,
        orderBy: { [sortBy]: sortOrder },
        skip,
        take: limit,
      }),
      prisma.purchaseOrder.count({ where }),
    ]);

    return {
      data,
      meta: {
        page,
        limit,
        totalCount,
        totalPages: Math.ceil(totalCount / limit),
      },
    };
  }

  async findById(id) {
    return prisma.purchaseOrder.findFirst({
      where: notDeleted({ id }),
      include: INCLUDE_ALL,
    });
  }

  async update(id, data, items) {
    return prisma.$transaction(async (tx) => {
      if (items) {
        await tx.purchaseOrderItem.deleteMany({ where: { purchaseOrderId: id } });

        const clean = toPrismaData(data);
        const { subtotal, baseImponible, igv, total, descuentoMonto } = calcTotals(items, clean);

        return tx.purchaseOrder.update({
          where: { id },
          data: {
            ...clean,
            subtotal,
            baseImponible,
            igv,
            total,
            descuentoMonto: clean.descuentoMonto || descuentoMonto,
            items: {
              create: items.map((item, idx) => ({
                description: item.description,
                quantity: item.quantity,
                unit: item.unit || 'UND',
                unitPrice: item.unitPrice,
                total: +(Number(item.quantity) * Number(item.unitPrice)).toFixed(2),
                sortOrder: idx,
              })),
            },
          },
          include: INCLUDE_ALL,
        });
      }

      return tx.purchaseOrder.update({
        where: { id },
        data: toPrismaData(data),
        include: INCLUDE_ALL,
      });
    }, { timeout: 30000 });
  }

  async changeStatus(id, status) {
    return prisma.purchaseOrder.update({
      where: { id },
      data: { status },
      include: INCLUDE_ITEMS,
    });
  }

  async softDelete(id) {
    return prisma.purchaseOrder.update({
      where: { id },
      data: { deletedAt: new Date() },
    });
  }

  // ── Private: correlativo atómico ──

  async #nextPoNumber(tx) {
    const year = new Date().getFullYear();

    const seq = await tx.purchaseOrderSequence.upsert({
      where: { year },
      create: { year, lastNumber: 1 },
      update: { lastNumber: { increment: 1 } },
    });

    return `OC-${year}-${String(seq.lastNumber).padStart(6, '0')}`;
  }
}

export const purchaseOrderRepository = new PurchaseOrderRepository();
