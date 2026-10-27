import React, { useEffect, useRef, useState } from 'react';
import {
  Box, Flex, Grid, Icon, IconButton, Text, useColorModeValue,
} from '@chakra-ui/react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence, useDragControls } from 'framer-motion';
import { X, ChevronLeft, ChevronRight, Settings, LogOut } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useModoInventario } from '../../../hooks/useModoInventario';
import { seccionesVisibles, CONFIGURACION } from '../navConfig';

const MotionBox = motion(Box);

// Curva de drawer iOS (Ionic): entra rápido y asienta suave. Salida más corta.
const EASE_DRAWER = [0.32, 0.72, 0, 1];
const ENTRA = { duration: 0.32, ease: EASE_DRAWER };
const SALE  = { duration: 0.22, ease: EASE_DRAWER };
// Cierre por gesto: distancia o un "flick" rápido, lo que llegue primero.
const CIERRE_PX = 120;
const CIERRE_VEL = 500;

const enRuta = (pathname, path) => pathname === path || pathname.startsWith(`${path}/`);
const itemActivo = (pathname, item) => (
  item.subItems
    ? item.subItems.some((s) => enRuta(pathname, s.path))
    : enRuta(pathname, item.path)
);

// ─── Tile: ícono de línea sobre cuadro redondeado con tinte suave ─────────────
const Tile = ({ item, activo, onClick }) => {
  const tinte      = useColorModeValue(activo ? 'brand.100' : 'brand.50', 'whiteAlpha.100');
  const iconColor  = useColorModeValue('brand.500', 'brand.300');
  const labelColor = useColorModeValue(activo ? 'brand.600' : 'neutral.700', 'neutral.200');
  return (
    <Flex
      as="button"
      type="button"
      onClick={onClick}
      direction="column"
      align="center"
      gap={2}
      py={2}
      borderRadius="lg"
      transition="transform 140ms cubic-bezier(0.23, 1, 0.32, 1)"
      _active={{ transform: 'scale(0.96)' }}
      sx={{ WebkitTapHighlightColor: 'transparent' }}
    >
      <Flex w="56px" h="56px" borderRadius="16px" bg={tinte} align="center" justify="center">
        <Icon as={item.lineIcon} boxSize="24px" color={iconColor} strokeWidth={1.75} />
      </Flex>
      <Text
        fontSize="12px"
        lineHeight="16px"
        fontWeight={activo ? 600 : 500}
        color={labelColor}
        textAlign="center"
        noOfLines={2}
        px={1}
      >
        {item.name}
      </Text>
    </Flex>
  );
};

// ─── Fila de lista (submódulos, Configuración, Cerrar sesión) ─────────────────
const Fila = ({ icon, label, onClick, activo, chevron = true }) => {
  const color = useColorModeValue(activo ? 'brand.600' : 'neutral.800', 'neutral.100');
  const press = useColorModeValue('neutral.100', 'whiteAlpha.100');
  return (
    <Flex
      as="button"
      type="button"
      onClick={onClick}
      w="100%"
      minH="52px"
      align="center"
      gap={3}
      px={4}
      borderRadius="lg"
      color={color}
      fontSize="md"
      fontWeight={activo ? 600 : 500}
      textAlign="left"
      _active={{ bg: press }}
      sx={{ WebkitTapHighlightColor: 'transparent' }}
    >
      {icon && <Icon as={icon} boxSize="20px" strokeWidth={1.75} color="neutral.500" />}
      <Text flex="1">{label}</Text>
      {chevron && <Icon as={ChevronRight} boxSize="18px" color="neutral.400" />}
    </Flex>
  );
};

/**
 * Lanzador "Más" — hoja a pantalla completa con TODOS los módulos en
 * cuadrícula de 3, agrupados como el sidebar. Módulos con submenú abren su
 * lista dentro de la misma hoja. Cierre: botón, Escape o arrastre hacia abajo
 * desde la cabecera.
 */
const MasSheet = ({ abierto, onClose }) => {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { logout } = useAuth();
  const { conStock } = useModoInventario();
  const dragControls = useDragControls();
  const hojaRef = useRef(null);
  const [grupo, setGrupo] = useState(null);

  const bg       = useColorModeValue('white', 'gray.900');
  const borde    = useColorModeValue('neutral.200', 'gray.700');
  const asa      = useColorModeValue('neutral.300', 'gray.600');
  const etiqueta = useColorModeValue('neutral.400', 'neutral.500');

  const secciones = seccionesVisibles(conStock);

  // Bloquea el scroll del fondo, Escape cierra, foco al botón de cierre.
  useEffect(() => {
    if (!abierto) { setGrupo(null); return undefined; }
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    hojaRef.current?.focus({ preventScroll: true });
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener('keydown', onKey);
    };
  }, [abierto, onClose]);

  const ir = (path) => { navigate(path); onClose(); };

  return (
    <AnimatePresence>
      {abierto && (
        <MotionBox
          key="mas-sheet"
          ref={hojaRef}
          tabIndex={-1}
          outline="none"
          role="dialog"
          aria-modal="true"
          aria-label="Todos los módulos"
          position="fixed"
          inset={0}
          zIndex="overlay"
          bg={bg}
          display="flex"
          flexDirection="column"
          pt="env(safe-area-inset-top)"
          initial={{ y: '100%' }}
          animate={{ y: 0, transition: ENTRA }}
          exit={{ y: '100%', transition: SALE }}
          drag="y"
          dragListener={false}
          dragControls={dragControls}
          dragConstraints={{ top: 0, bottom: 0 }}
          // Hacia arriba no se mueve; hacia abajo sigue al dedo 1:1
          dragElastic={{ top: 0, bottom: 1 }}
          onDragEnd={(_, info) => {
            if (info.offset.y > CIERRE_PX || info.velocity.y > CIERRE_VEL) onClose();
          }}
        >
          {/* Cabecera = zona de arrastre */}
          <Box
            onPointerDown={(e) => dragControls.start(e)}
            sx={{ touchAction: 'none' }}
            borderBottom="1px solid"
            borderColor={borde}
            flexShrink={0}
          >
            <Box mx="auto" mt={2} w="36px" h="4px" borderRadius="full" bg={asa} />
            <Flex align="center" h="52px" px={2}>
              {grupo ? (
                <IconButton
                  aria-label="Volver a módulos"
                  icon={<Icon as={ChevronLeft} boxSize="22px" />}
                  variant="ghost"
                  minW="44px" h="44px"
                  onClick={() => setGrupo(null)}
                />
              ) : <Box w="44px" />}
              <Text flex="1" textAlign="center" fontSize="md" fontWeight={600}>
                {grupo ? grupo.name : 'Módulos'}
              </Text>
              <IconButton
                aria-label="Cerrar"
                icon={<Icon as={X} boxSize="22px" />}
                variant="ghost"
                minW="44px" h="44px"
                onClick={onClose}
              />
            </Flex>
          </Box>

          {/* Contenido desplazable */}
          <Box flex="1" overflowY="auto" overscrollBehavior="contain" px={4} pb="calc(24px + env(safe-area-inset-bottom))">
            {grupo ? (
              <MotionBox
                key={grupo.name}
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0, transition: { duration: 0.18, ease: [0.23, 1, 0.32, 1] } }}
                pt={3}
              >
                {grupo.subItems.map((s) => (
                  <Fila
                    key={s.path}
                    label={s.name}
                    activo={pathname === s.path}
                    onClick={() => ir(s.path)}
                  />
                ))}
              </MotionBox>
            ) : (
              <MotionBox
                key="grid"
                initial={false}
                animate={{ opacity: 1, x: 0, transition: { duration: 0.18, ease: [0.23, 1, 0.32, 1] } }}
              >
                {secciones.map((sec) => (
                  <Box key={sec.id} pt={5}>
                    <Text
                      fontSize="11px"
                      fontWeight={600}
                      letterSpacing="wider"
                      textTransform="uppercase"
                      color={etiqueta}
                      mb={3}
                      px={1}
                    >
                      {sec.label}
                    </Text>
                    <Grid templateColumns="repeat(3, 1fr)" rowGap={4} columnGap={2}>
                      {sec.items.map((item) => (
                        <Tile
                          key={item.name}
                          item={item}
                          activo={itemActivo(pathname, item)}
                          onClick={() => (item.subItems ? setGrupo(item) : ir(item.path))}
                        />
                      ))}
                    </Grid>
                  </Box>
                ))}

                <Box mt={6} pt={2} borderTop="1px solid" borderColor={borde}>
                  <Fila
                    icon={Settings}
                    label={CONFIGURACION.name}
                    activo={enRuta(pathname, CONFIGURACION.path)}
                    onClick={() => ir(CONFIGURACION.path)}
                  />
                  <Fila
                    icon={LogOut}
                    label="Cerrar sesión"
                    chevron={false}
                    onClick={() => { onClose(); logout(); }}
                  />
                </Box>
              </MotionBox>
            )}
          </Box>
        </MotionBox>
      )}
    </AnimatePresence>
  );
};

export default MasSheet;
