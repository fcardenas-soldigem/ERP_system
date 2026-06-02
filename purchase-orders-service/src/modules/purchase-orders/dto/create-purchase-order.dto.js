import Joi from 'joi';

const itemSchema = Joi.object({
  description: Joi.string().trim().min(1).max(500).required()
    .messages({ 'string.empty': 'La descripción del item es obligatoria' }),
  quantity: Joi.number().positive().required()
    .messages({ 'number.positive': 'La cantidad debe ser mayor a 0' }),
  unit: Joi.string().trim().max(20).default('UND'),
  unitPrice: Joi.number().positive().required()
    .messages({ 'number.positive': 'El precio unitario debe ser mayor a 0' }),
});

export const createPurchaseOrderSchema = Joi.object({
  // Proveedor
  supplierName: Joi.string().trim().min(1).max(300).required(),
  supplierRuc: Joi.string().trim().pattern(/^\d{8,20}$/).required()
    .messages({ 'string.pattern.base': 'El RUC del proveedor debe tener entre 8 y 20 dígitos' }),
  supplierAddress: Joi.string().trim().max(500).allow('', null),
  supplierContact: Joi.string().trim().max(200).allow('', null),
  supplierEmail: Joi.string().trim().email().allow('', null),

  // Empresa emisora
  companyName: Joi.string().trim().min(1).max(300).required(),
  companyRuc: Joi.string().trim().pattern(/^\d{8,20}$/).required(),
  companyAddress: Joi.string().trim().max(500).allow('', null),
  companyLogoUrl: Joi.string().trim().uri().max(1000).allow('', null),

  // Configuración
  currency: Joi.string().valid('USD', 'PEN').default('PEN'),
  paymentTerms: Joi.string().trim().max(50).allow('', null),

  // Fechas
  issueDate: Joi.date().iso().required(),
  dueDate: Joi.date().iso().min(Joi.ref('issueDate')).allow(null)
    .messages({ 'date.min': 'La fecha de vencimiento no puede ser anterior a la de emisión' }),

  // Texto libre
  deliveryConditions: Joi.string().trim().max(2000).allow('', null),
  considerations: Joi.string().trim().max(2000).allow('', null),

  // Items – mínimo 1
  items: Joi.array().items(itemSchema).min(1).required()
    .messages({ 'array.min': 'La orden debe tener al menos 1 item' }),

  // IGV incluido
  incluyeIgv: Joi.boolean().default(false),

  // Descuento
  descuentoTipo: Joi.string().valid('porcentaje', 'monto').default('porcentaje').allow('', null),
  descuentoValor: Joi.number().min(0).default(0),
  descuentoMonto: Joi.number().min(0).default(0),
  descuento_tipo: Joi.string().valid('porcentaje', 'monto').allow('', null),
  descuento_valor: Joi.number().min(0).allow(null),
  descuento_monto: Joi.number().min(0).allow(null),

  // Tipo de orden
  orderType: Joi.string().valid('productos', 'servicios').default('productos').allow('', null),

  // Multi-tenancy (opcional)
  empresaId: Joi.number().integer().positive().allow(null),
});
