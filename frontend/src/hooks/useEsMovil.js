import { useBreakpointValue } from '@chakra-ui/react';

/**
 * true bajo el breakpoint `md` de Chakra (< 768 px de ancho de viewport).
 * Por ancho, no por user-agent: una tablet en vertical también es "móvil".
 * ssr:false → el primer render ya trae el valor real (sin parpadeo de layout).
 */
export const useEsMovil = () => useBreakpointValue({ base: true, md: false }, { ssr: false }) ?? false;
