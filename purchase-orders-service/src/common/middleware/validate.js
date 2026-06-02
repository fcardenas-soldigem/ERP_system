import { ValidationError } from '../exceptions/AppError.js';

/**
 * Express middleware factory – validates req.body (or another source) against a Joi schema.
 * @param {import('joi').ObjectSchema} schema
 * @param {'body'|'query'|'params'} source
 */
export function validate(schema, source = 'body') {
  return (req, _res, next) => {
    const { error, value } = schema.validate(req[source], {
      abortEarly: false,
      stripUnknown: true,
    });

    if (error) {
      const details = error.details.map((d) => d.message);
      return next(new ValidationError('Datos de entrada inválidos', details));
    }

    req[source] = value;
    next();
  };
}
