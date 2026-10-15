import { api } from '../lib/api';

// Tokens de API para el MCP del ERP ("Conectar Claude").
export const agenteService = {
  listTokens: async () => {
    const { data } = await api.get('/api/agente/tokens/');
    return data?.results ?? data; // soporta respuesta paginada o lista directa
  },
  createToken: async (payload) => {
    const { data } = await api.post('/api/agente/tokens/', payload);
    return data; // incluye `token` en claro (solo esta vez)
  },
  revokeToken: async (id) => {
    const { data } = await api.post(`/api/agente/tokens/${id}/revocar/`);
    return data;
  },
};
