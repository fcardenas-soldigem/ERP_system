import { useAuth } from '../components/context/AuthContext';

/**
 * true si el usuario puede crear/editar (rol admin u operador).
 * Es solo cosmético: oculta botones que el backend igualmente rechaza
 * con 403 (core.permissions.RolEscritura). Si el perfil aún no cargó o
 * no trae rol, se asume que puede (el backend decide).
 */
export const usePuedeEscribir = () => {
  const { user } = useAuth();
  return user?.rol !== 'solo_lectura';
};
