/**
 * Wraps an async Express handler so thrown errors reach the error-handler middleware.
 */
export const asyncHandler = (fn) => (req, res, next) =>
  Promise.resolve(fn(req, res, next)).catch(next);
