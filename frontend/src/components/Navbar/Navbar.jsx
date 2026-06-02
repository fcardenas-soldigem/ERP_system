import React from 'react';
import {
  Box, Flex, Text, IconButton, Button,
  Stack, useColorModeValue, useColorMode,
  HStack,
} from '@chakra-ui/react';
import { MoonIcon, SunIcon } from '@chakra-ui/icons';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link as RouterLink } from 'react-router-dom';

// Matches the same set shown in AnimatedSidebar's CORE + AVANZADO sections
// so mobile top-bar has a fast-access strip for the most important routes.
// (Full nav lives in the hamburger drawer in AnimatedSidebar.)
const TOP_LINKS = [
  { text: 'Dashboard',   path: '/app/dashboard' },
  { text: 'Ventas',      path: '/app/ventas' },
  { text: 'Compras',     path: '/app/compras' },
  { text: 'Inventario',  path: '/app/inventario' },
  { text: 'Cotizaciones',path: '/app/cotizaciones' },
];

const Navbar = () => {
  const { colorMode, toggleColorMode } = useColorMode();
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  const bg          = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('neutral.200', 'gray.700');
  const linkColor   = useColorModeValue('neutral.600', 'neutral.300');
  const linkHover   = useColorModeValue('neutral.900', 'white');

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <Box
      bg={bg}
      borderBottom="1px"
      borderColor={borderColor}
      px={4}
      py={0}
      position="sticky"
      top={0}
      zIndex={100}
      boxShadow="xs"
    >
      <Flex align="center" h="48px" gap={4}>

        {/* Quick links — hidden on mobile (sidebar drawer covers it) */}
        <HStack
          spacing={1}
          display={{ base: 'none', md: 'flex' }}
          flex="1"
        >
          {TOP_LINKS.map((link) => (
            <Button
              key={link.text}
              as={RouterLink}
              to={link.path}
              variant="ghost"
              size="sm"
              color={linkColor}
              fontWeight="medium"
              fontSize="sm"
              px={3}
              _hover={{ color: linkHover, bg: 'neutral.100' }}
              _activeLink={{ color: 'primary.600', bg: 'primary.50' }}
            >
              {link.text}
            </Button>
          ))}
        </HStack>

        {/* Right side */}
        <HStack ml="auto" spacing={2}>
          <IconButton
            aria-label="Cambiar tema"
            icon={colorMode === 'light' ? <MoonIcon /> : <SunIcon />}
            onClick={toggleColorMode}
            variant="ghost"
            size="sm"
            color={linkColor}
          />
          {user && (
            <Button
              variant="ghost"
              size="sm"
              color={linkColor}
              fontWeight="medium"
              onClick={handleLogout}
            >
              Cerrar sesión
            </Button>
          )}
        </HStack>
      </Flex>
    </Box>
  );
};

export default Navbar;
