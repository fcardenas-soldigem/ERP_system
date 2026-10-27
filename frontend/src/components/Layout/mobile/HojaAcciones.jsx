import React, { useEffect } from 'react';
import { Box, Flex, Icon, Text, useColorModeValue } from '@chakra-ui/react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight } from 'lucide-react';

const MotionBox = motion(Box);

const EASE_DRAWER = [0.32, 0.72, 0, 1];
const CIERRE_PX = 80;
const CIERRE_VEL = 500;

/**
 * Hoja inferior de opciones (móvil). Se cierra tocando el fondo, con Escape
 * o arrastrando hacia abajo. `opciones`: [{ label, icon, onClick }].
 */
const HojaAcciones = ({ abierta, titulo, opciones = [], onClose }) => {
  const bg    = useColorModeValue('white', 'gray.800');
  const asa   = useColorModeValue('neutral.300', 'gray.600');
  const texto = useColorModeValue('neutral.800', 'neutral.100');
  const tinte = useColorModeValue('brand.50', 'whiteAlpha.100');
  const icono = useColorModeValue('brand.500', 'brand.300');
  const press = useColorModeValue('neutral.100', 'whiteAlpha.100');

  useEffect(() => {
    if (!abierta) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener('keydown', onKey);
    };
  }, [abierta, onClose]);

  return (
    <AnimatePresence>
      {abierta && (
        <Box key="hoja-acciones" position="fixed" inset={0} zIndex="overlay">
          <MotionBox
            position="absolute"
            inset={0}
            bg="blackAlpha.400"
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1, transition: { duration: 0.2 } }}
            exit={{ opacity: 0, transition: { duration: 0.15 } }}
          />
          <MotionBox
            role="dialog"
            aria-modal="true"
            aria-label={titulo}
            position="absolute"
            left={0}
            right={0}
            bottom={0}
            bg={bg}
            borderTopRadius="16px"
            px={3}
            pb="calc(12px + env(safe-area-inset-bottom))"
            initial={{ y: '100%' }}
            animate={{ y: 0, transition: { duration: 0.28, ease: EASE_DRAWER } }}
            exit={{ y: '100%', transition: { duration: 0.2, ease: EASE_DRAWER } }}
            drag="y"
            dragConstraints={{ top: 0, bottom: 0 }}
            dragElastic={{ top: 0, bottom: 1 }}
            onDragEnd={(_, info) => {
              if (info.offset.y > CIERRE_PX || info.velocity.y > CIERRE_VEL) onClose();
            }}
          >
            <Box mx="auto" mt={2} mb={1} w="36px" h="4px" borderRadius="full" bg={asa} />
            <Text px={3} py={3} fontSize="md" fontWeight={600}>{titulo}</Text>
            {opciones.map((op) => (
              <Flex
                key={op.label}
                as="button"
                type="button"
                onClick={op.onClick}
                w="100%"
                minH="60px"
                px={3}
                gap={3}
                align="center"
                textAlign="left"
                borderRadius="lg"
                color={texto}
                _active={{ bg: press }}
                sx={{ WebkitTapHighlightColor: 'transparent' }}
              >
                <Flex w="40px" h="40px" borderRadius="12px" bg={tinte} align="center" justify="center" flexShrink={0}>
                  <Icon as={op.icon} boxSize="20px" color={icono} strokeWidth={1.75} />
                </Flex>
                <Text flex="1" fontSize="md" fontWeight={500}>{op.label}</Text>
                <Icon as={ChevronRight} boxSize="18px" color="neutral.400" />
              </Flex>
            ))}
          </MotionBox>
        </Box>
      )}
    </AnimatePresence>
  );
};

export default HojaAcciones;
