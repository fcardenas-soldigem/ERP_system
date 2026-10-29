import { useAuth } from '../components/context/AuthContext';

/**
 * true si el usuario es administrador (p. ej. para anular ventas).
 * Cosmético, como usePuedeEscribir: el backend responde 403 a operador y
 * solo_lectura de todas formas.
 */
export const useEsAdmin = () => {
  const { user } = useAuth();
  return user?.rol === 'admin' || Boolean(user?.is_superuser);
};
