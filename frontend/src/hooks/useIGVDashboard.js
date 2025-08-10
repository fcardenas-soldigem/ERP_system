import { useState, useEffect } from 'react';
import { getIGVDashboard } from '../services/igv.service';

export const useIGVDashboard = () => {
  const [igvData, setIGVData] = useState({
    igv_ventas: 0,
    igv_compras: 0,
    igv_por_pagar: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchIGVData = async () => {
      try {
        setLoading(true);
        const data = await getIGVDashboard();
        setIGVData(data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchIGVData();
  }, []);

  return { igvData, loading, error };
}; 