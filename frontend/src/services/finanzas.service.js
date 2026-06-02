import { api } from '../lib/api';

export const finanzasService = {
  getDashboard: (params = {}) =>
    api.get('/api/finanzas/dashboard/', { params }).then(r => r.data),
};
