import DOMPurify from 'dompurify';

export const sanitize = (dirty) => DOMPurify.sanitize(dirty);

// Configuración restrictiva para texto enriquecido mínimo
export const sanitizeConfig = {
  ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'br'],
  ALLOWED_ATTR: [],
};

export const sanitizeStrict = (dirty) =>
  DOMPurify.sanitize(dirty, sanitizeConfig);
