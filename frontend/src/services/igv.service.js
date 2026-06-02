import { api } from '../lib/api';

export const getIGVDashboard = async () => {
  try {
    const response = await api.get('/api/dashboard/igv/');
    return response.data;
  } catch (error) {
    console.error('Error al obtener IGV del dashboard:', error);
    throw error;
  }
}; 