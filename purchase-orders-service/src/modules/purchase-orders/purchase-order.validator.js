import { validate } from '../../common/middleware/validate.js';
import { createPurchaseOrderSchema } from './dto/create-purchase-order.dto.js';
import {
  updatePurchaseOrderSchema,
  changeStatusSchema,
  listQuerySchema,
} from './dto/update-purchase-order.dto.js';

export const validateCreate = validate(createPurchaseOrderSchema);
export const validateUpdate = validate(updatePurchaseOrderSchema);
export const validateChangeStatus = validate(changeStatusSchema);
export const validateListQuery = validate(listQuerySchema, 'query');
