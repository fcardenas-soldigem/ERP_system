import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

/**
 * Hook compartido: modo de inventario de la empresa actual.
 * Cacheado por React Query. Mientras carga, asume 'con_stock' (no oculta de más).
 *
 * Devuelve: { modo, conStock, isLoading }
 */
export function useModoInventario() {
  const { data, isLoading } = useQuery({
    queryKey: ['empresa-modo-inventario'],
    queryFn: async () => {
      const r = await api.get('/api/empresas/');
      const emp = Array.isArray(r.data?.results) ? r.data.results[0]
        : (Array.isArray(r.data) ? r.data[0] : r.data);
      return emp?.modo_inventario || 'con_stock';
    },
    staleTime: 5 * 60 * 1000,
  });
  const modo = data || 'con_stock';
  return { modo, conStock: modo === 'con_stock', isLoading };
}
