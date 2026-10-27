import React from 'react';
import {
  Avatar, Box, Flex, Grid, Icon, Menu, MenuButton, MenuDivider, MenuItem,
  MenuList, Text, useColorMode, useColorModeValue,
} from '@chakra-ui/react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Moon, Sun, LogOut, Settings } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { PRODUCT_NAME, PRODUCT_INITIALS } from '../../../config/brand';
import { tituloDePantalla, CONFIGURACION } from '../navConfig';

export const MOBILE_HEADER_H = '52px';

/**
 * Cabecera móvil (< md): empresa a la izquierda, pantalla actual al centro,
 * avatar a la derecha (tema, configuración, cerrar sesión). Sin hamburguesa:
 * la navegación vive en la barra inferior.
 */
const MobileHeader = () => {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { colorMode, toggleColorMode } = useColorMode();

  const bg    = useColorModeValue('white', 'gray.800');
  const borde = useColorModeValue('neutral.200', 'gray.700');
  const sutil = useColorModeValue('neutral.600', 'neutral.300');

  const empresa = user?.empresa_info?.nombre || PRODUCT_NAME;
  const nombreUsuario = (
    [user?.nombre, user?.apellido].filter(Boolean).join(' ')
    || user?.username
    || (user?.email ? user.email.split('@')[0] : 'Cuenta')
  );

  return (
    <Box
      as="header"
      position="fixed"
      top={0}
      left={0}
      right={0}
      zIndex="sticky"
      bg={bg}
      borderBottom="1px solid"
      borderColor={borde}
      pt="env(safe-area-inset-top)"
    >
      <Grid
        h={MOBILE_HEADER_H}
        px={4}
        templateColumns="minmax(0, 1fr) auto minmax(0, 1fr)"
        alignItems="center"
        columnGap={3}
      >
        <Flex align="center" gap={2} minW={0}>
          <Flex
            w="28px" h="28px" flexShrink={0}
            bg="brand.500" color="white" borderRadius="8px"
            align="center" justify="center"
            fontSize="sm" fontWeight={700}
          >
            {PRODUCT_INITIALS}
          </Flex>
          <Text fontSize="13px" fontWeight={500} color={sutil} noOfLines={1}>
            {empresa}
          </Text>
        </Flex>

        <Text as="h1" fontSize="md" fontWeight={600} noOfLines={1} maxW="44vw" textAlign="center">
          {tituloDePantalla(pathname)}
        </Text>

        <Flex justify="flex-end">
          <Menu placement="bottom-end" autoSelect={false}>
            <MenuButton
              aria-label="Cuenta"
              w="44px" h="44px" mr="-6px"
              display="flex" alignItems="center" justifyContent="center"
              sx={{ WebkitTapHighlightColor: 'transparent' }}
            >
              <Avatar size="sm" name={nombreUsuario} bg="brand.500" color="white" />
            </MenuButton>
            <MenuList minW="220px">
              <Box px={3} py={2}>
                <Text fontSize="sm" fontWeight={600} noOfLines={1}>{nombreUsuario}</Text>
                <Text fontSize="xs" color="neutral.500" noOfLines={1}>{user?.email || ''}</Text>
              </Box>
              <MenuDivider />
              <MenuItem minH="44px" icon={<Icon as={Settings} boxSize="16px" />} onClick={() => navigate(CONFIGURACION.path)}>
                {CONFIGURACION.name}
              </MenuItem>
              <MenuItem
                minH="44px"
                icon={<Icon as={colorMode === 'light' ? Moon : Sun} boxSize="16px" />}
                onClick={toggleColorMode}
              >
                {colorMode === 'light' ? 'Modo oscuro' : 'Modo claro'}
              </MenuItem>
              <MenuItem minH="44px" icon={<Icon as={LogOut} boxSize="16px" />} onClick={logout}>
                Cerrar sesión
              </MenuItem>
            </MenuList>
          </Menu>
        </Flex>
      </Grid>
    </Box>
  );
};

export default MobileHeader;
