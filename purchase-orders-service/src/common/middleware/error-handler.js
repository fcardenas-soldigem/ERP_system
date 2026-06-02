import { logger } from '../../config/logger.js';
import { AppError } from '../exceptions/AppError.js';

// eslint-disable-next-line no-unused-vars
export function errorHandler(err, _req, res, _next) {
  if (err instanceof AppError) {
    logger.warn(`[${err.code}] ${err.message}`);
    return res.status(err.statusCode).json({
      success: false,
      code: err.code,
      message: err.message,
      ...(err.details && { details: err.details }),
    });
  }

  // Prisma known errors
  if (err.code === 'P2002') {
    logger.warn('Prisma unique constraint: %s', err.meta?.target);
    return res.status(409).json({
      success: false,
      code: 'DUPLICATE',
      message: `Ya existe un registro con ese valor único (${err.meta?.target})`,
    });
  }

  if (err.code === 'P2025') {
    return res.status(404).json({
      success: false,
      code: 'NOT_FOUND',
      message: 'Registro no encontrado',
    });
  }

  // Joi validation
  if (err.isJoi) {
    return res.status(400).json({
      success: false,
      code: 'VALIDATION_ERROR',
      message: 'Datos inválidos',
      details: err.details.map((d) => d.message),
    });
  }

  logger.error('Unhandled error:', err);
  return res.status(500).json({
    success: false,
    code: 'INTERNAL_ERROR',
    message: 'Error interno del servidor',
  });
}
