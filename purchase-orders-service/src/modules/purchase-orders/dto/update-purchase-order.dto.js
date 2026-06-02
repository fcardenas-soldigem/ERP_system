import Joi from 'joi';

const itemSchema = Joi.object({
  id: Joi.string().uuid().allow(null),
  description: Joi.string().trim().min(1).max(500).required(),
  quantity: Joi.number().positive().required(),
  unit: Joi.string().trim().max(20).default('UND'),
  unitPrice: Joi.number().positive().required(),
});

export const updatePurchaseOrderSchema = Joi.object({
  supplierName: Joi.string().trim().min(1).max(300),
  supplierRuc: Joi.string().trim().pattern(/^\d{8,20}$/),
  supplierAddress: Joi.string().trim().max(500).allow('', null),
  supplierContact: Joi.string().trim().max(200).allow('', null),
  supplierEmail: Joi.string().trim().email().allow('', null),

  companyName: Joi.string().trim().min(1).max(300),
  companyRuc: Joi.string().trim().pattern(/^\d{8,20}$/),
  companyAddress: Joi.string().trim().max(500).allow('', null),

  currency: Joi.string().valid('USD', 'PEN'),
  paymentTerms: Joi.string().trim().max(50).allow('', null),

  issueDate: Joi.date().iso(),
  dueDate: Joi.date().iso().allow(null),

  deliveryConditions: Joi.string().trim().max(2000).allow('', null),
  considerations: Joi.string().trim().max(2000).allow('', null),

  incluyeIgv: Joi.boolean(),
  descuentoTipo: Joi.string().valid('porcentaje', 'monto').allow('', null),
  descuentoValor: Joi.number().min(0).allow(null),
  descuentoMonto: Joi.number().min(0).allow(null),
  descuento_tipo: Joi.string().valid('porcentaje', 'monto').allow('', null),
  descuento_valor: Joi.number().min(0).allow(null),
  descuento_monto: Joi.number().min(0).allow(null),
  orderType: Joi.string().valid('productos', 'servicios').allow('', null),

  items: Joi.array().items(itemSchema).min(1)
    .messages({ 'array.min': 'La orden debe tener al menos 1 item' }),
}).min(1).messages({ 'object.min': 'Debe enviar al menos un campo para actualizar' });

export const changeStatusSchema = Joi.object({
  status: Joi.string().valid('DRAFT', 'APPROVED', 'CLOSED').required(),
});

export const listQuerySchema = Joi.object({
  page: Joi.number().integer().min(1).default(1),
  limit: Joi.number().integer().min(1).max(100).default(20),
  status: Joi.string().valid('DRAFT', 'APPROVED', 'CLOSED'),
  currency: Joi.string().valid('USD', 'PEN'),
  supplierRuc: Joi.string().trim(),
  search: Joi.string().trim().max(200),
  sortBy: Joi.string().valid('createdAt', 'issueDate', 'total', 'poNumber').default('createdAt'),
  sortOrder: Joi.string().valid('asc', 'desc').default('desc'),
  from: Joi.date().iso(),
  to: Joi.date().iso(),
});
