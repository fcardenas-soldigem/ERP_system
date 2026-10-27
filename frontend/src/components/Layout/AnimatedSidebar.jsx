import React, { useState } from 'react';
import {
  Box, VStack, Icon, Text, Flex, Badge,
  useColorModeValue, Collapse, IconButton,
  Tooltip, Avatar, HStack, Divider,
  useColorMode,
} from '@chakra-ui/react';
import { NavLink } from 'react-router-dom';
import {
  ChevronDownIcon, ChevronUpIcon,
  ChevronLeftIcon, ChevronRightIcon,
} from '@chakra-ui/icons';
import { motion, AnimatePresence } from 'framer-motion';
import { Moon, Sun, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useModoInventario } from '../../hooks/useModoInventario';
import { PRODUCT_NAME, PRODUCT_INITIALS } from '../../config/brand';
import { FaCog } from 'react-icons/fa';
import { seccionesVisibles, CONFIGURACION } from './navConfig';
import { useEsMovil } from '../../hooks/useEsMovil';

const MotionBox  = motion(Box);
const MotionFlex = motion(Flex);
const MotionText = motion(Text);

// ─── SectionLabel ─────────────────────────────────────────────────────────────
const SectionLabel = ({ label, badge, isCollapsed, isExpanded, onToggle, collapsible }) => {
  const labelColor = useColorModeValue('neutral.400', 'neutral.500');
  if (isCollapsed) return <Divider my={2} />;
  return (
    <Flex
      align="center"
      justify="space-between"
      px={5}
      pt={4}
      pb={1}
      cursor={collapsible ? 'pointer' : 'default'}
      onClick={collapsible ? onToggle : undefined}
      role={collapsible ? 'button' : undefined}
    >
      <HStack spacing={2}>
        <Text
          fontSize="10px"
          fontWeight="semibold"
          letterSpacing="wider"
          color={labelColor}
          textTransform="uppercase"
        >
          {label}
        </Text>
        {badge && (
          <Badge fontSize="8px" colorScheme="purple" variant="subtle" borderRadius="sm">
            {badge}
          </Badge>
        )}
      </HStack>
      {collapsible && (
        <Icon
          as={isExpanded ? ChevronUpIcon : ChevronDownIcon}
          color={labelColor}
          boxSize="12px"
        />
      )}
    </Flex>
  );
};

// ─── NavItem ──────────────────────────────────────────────────────────────────
const NavItem = ({ icon, children, to, subItems, isOpen, onToggle, isCollapsed, badge }) => {
  const activeBg    = useColorModeValue('primary.50',  'blue.900');
  const activeColor = useColorModeValue('primary.600', 'blue.200');
  const hoverBg     = useColorModeValue('neutral.100', 'gray.700');
  const textColor   = useColorModeValue('neutral.700', 'neutral.200');

  if (subItems) {
    return (
      <Box width="100%">
        <Tooltip label={isCollapsed ? children : ''} placement="right" hasArrow>
          <MotionFlex
            align="center"
            px={isCollapsed ? 3 : 4}
            py={2}
            mx={isCollapsed ? 2 : 3}
            borderRadius="md"
            cursor="pointer"
            onClick={onToggle}
            color={textColor}
            justify={isCollapsed ? 'center' : 'flex-start'}
            whileTap={{ scale: 0.98 }}
            _hover={{ bg: hoverBg, color: activeColor }}
            transition="background-color 120ms ease, color 120ms ease"
          >
            <Icon mr={isCollapsed ? 0 : 3} fontSize="16px" as={icon} />
            <AnimatePresence>
              {!isCollapsed && (
                <MotionText
                  flex="1"
                  fontSize="sm"
                  fontWeight="medium"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.15 }}
                >
                  {children}
                </MotionText>
              )}
            </AnimatePresence>
            {!isCollapsed && (
              <Icon as={isOpen ? ChevronUpIcon : ChevronDownIcon} boxSize="14px" opacity={0.6} />
            )}
          </MotionFlex>
        </Tooltip>

        {!isCollapsed && (
          <Collapse in={isOpen}>
            <VStack pl={9} pr={3} mt={0.5} spacing={0.5} align="stretch">
              {subItems.map((item, i) => (
                <NavLink key={i} to={item.path} style={{ textDecoration: 'none' }}>
                  {({ isActive }) => (
                    <Flex
                      align="center"
                      px={3}
                      py={1.5}
                      borderRadius="md"
                      bg={isActive ? activeBg : 'transparent'}
                      color={isActive ? activeColor : useColorModeValue('neutral.600', 'neutral.400')}
                      _hover={{ bg: hoverBg, color: activeColor }}
                      transition="background-color 120ms ease, color 120ms ease"
                      cursor="pointer"
                      fontSize="sm"
                      justify="space-between"
                    >
                      <Text fontSize="sm">{item.name}</Text>
                      {item.badge && (
                        <Badge fontSize="8px" colorScheme="blue" variant="subtle" borderRadius="sm" ml={1}>
                          {item.badge}
                        </Badge>
                      )}
                    </Flex>
                  )}
                </NavLink>
              ))}
            </VStack>
          </Collapse>
        )}
      </Box>
    );
  }

  return (
    <NavLink to={to} style={{ textDecoration: 'none', width: '100%' }}>
      {({ isActive }) => (
        <Tooltip label={isCollapsed ? children : ''} placement="right" hasArrow>
          <MotionFlex
            align="center"
            px={isCollapsed ? 3 : 4}
            py={2}
            mx={isCollapsed ? 2 : 3}
            borderRadius="md"
            cursor="pointer"
            bg={isActive ? activeBg : 'transparent'}
            color={isActive ? activeColor : textColor}
            justify={isCollapsed ? 'center' : 'flex-start'}
            whileTap={{ scale: 0.98 }}
            _hover={{ bg: hoverBg, color: activeColor }}
            transition="background-color 120ms ease, color 120ms ease"
          >
            <Icon mr={isCollapsed ? 0 : 3} fontSize="16px" as={icon} />
            <AnimatePresence>
              {!isCollapsed && (
                <>
                  <MotionText
                    fontSize="sm"
                    fontWeight={isActive ? 'semibold' : 'medium'}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.15 }}
                    flex="1"
                  >
                    {children}
                  </MotionText>
                  {badge && (
                    <Badge fontSize="8px" colorScheme="blue" variant="subtle" borderRadius="sm" ml={1}>
                      {badge}
                    </Badge>
                  )}
                </>
              )}
            </AnimatePresence>
          </MotionFlex>
        </Tooltip>
      )}
    </NavLink>
  );
};

// ─── SidebarContent ───────────────────────────────────────────────────────────
const SidebarContent = ({ isCollapsed, onToggleCollapse }) => {
  const [openMenus, setOpenMenus] = useState({});
  // Avanzado/Inteligencia start collapsed
  const [expandedSections, setExpandedSections] = useState({
    core: true,
    avanzado: false,
    inteligencia: false,
  });
  const { user, logout } = useAuth();
  const { colorMode, toggleColorMode } = useColorMode();
  // Nombre real: nombre+apellido del perfil; fallback al email sin dominio.
  const nombreUsuario = (
    [user?.nombre, user?.apellido].filter(Boolean).join(' ')
    || user?.username
    || (user?.email ? user.email.split('@')[0] : 'Cuenta')
  );
  // D6 — en empresas sin_stock se oculta el menú Inventario (y submenús).
  const { conStock } = useModoInventario();
  const secciones = React.useMemo(() => seccionesVisibles(conStock), [conStock]);

  const bgColor     = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('neutral.200', 'gray.700');
  const brandColor  = useColorModeValue('primary.500', 'primary.400');

  const toggleMenu = (name) => {
    if (!isCollapsed) {
      setOpenMenus(p => ({ ...p, [name]: !p[name] }));
    }
  };

  const toggleSection = (id) => {
    setExpandedSections(p => ({ ...p, [id]: !p[id] }));
  };

  return (
    <MotionBox
      bg={bgColor}
      borderRight="1px"
      borderRightColor={borderColor}
      h="100vh"
      position="sticky"
      top="0"
      animate={{ width: isCollapsed ? '64px' : '240px' }}
      // Curva de drawer iOS: nítida, sin la blandura de easeInOut
      transition={{ duration: 0.2, ease: [0.32, 0.72, 0, 1] }}
      display="flex"
      flexDirection="column"
      overflow="hidden"
    >
      {/* Logo */}
      <Flex
        align="center"
        justify={isCollapsed ? 'center' : 'flex-start'}
        px={isCollapsed ? 2 : 4}
        py={3}
        borderBottom="1px"
        borderColor={borderColor}
        minH="56px"
      >
        <Box
          w="32px" h="32px"
          bg="brand.500"
          borderRadius="lg"
          display="flex" alignItems="center" justifyContent="center"
          color="white" fontWeight="bold" fontSize="md"
          flexShrink={0}
        >
          {PRODUCT_INITIALS}
        </Box>
        <AnimatePresence>
          {!isCollapsed && (
            <MotionText
              ml={3}
              fontSize="md"
              fontWeight="bold"
              color="brand.600"
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }}
              transition={{ duration: 0.2 }}
              whiteSpace="nowrap"
              overflow="hidden"
            >
              {PRODUCT_NAME}
            </MotionText>
          )}
        </AnimatePresence>
      </Flex>

      {/* Navigation */}
      <VStack
        spacing={0}
        align="stretch"
        flex="1"
        overflowY="auto"
        overflowX="hidden"
        py={2}
        css={{
          '&::-webkit-scrollbar': { width: '3px' },
          '&::-webkit-scrollbar-thumb': { background: borderColor, borderRadius: '24px' },
        }}
      >
        {secciones.map((section) => {
          const isExpanded = expandedSections[section.id];
          const showItems = !section.collapsible || isExpanded;

          return (
            <Box key={section.id}>
              <SectionLabel
                label={section.label}
                badge={section.badge}
                isCollapsed={isCollapsed}
                isExpanded={isExpanded}
                onToggle={() => toggleSection(section.id)}
                collapsible={section.collapsible}
              />
              <Collapse in={!isCollapsed ? showItems : true}>
                <VStack spacing={0.5} align="stretch" mb={1}>
                  {section.items.map((item) => (
                    <NavItem
                      key={item.name}
                      icon={item.icon}
                      to={item.path}
                      subItems={item.subItems}
                      isOpen={openMenus[item.name]}
                      onToggle={() => toggleMenu(item.name)}
                      isCollapsed={isCollapsed}
                      badge={item.badge}
                    >
                      {item.name}
                    </NavItem>
                  ))}
                </VStack>
              </Collapse>
            </Box>
          );
        })}

        {/* Configuración at bottom */}
        <Box mt="auto" pt={2}>
          <Divider mb={2} />
          <NavItem icon={FaCog} to={CONFIGURACION.path} isCollapsed={isCollapsed}>
            {CONFIGURACION.name}
          </NavItem>
        </Box>
      </VStack>

      {/* User — nombre real + tema + cerrar sesión (la top-bar ya no existe) */}
      <Box px={isCollapsed ? 2 : 3} py={3} borderTop="1px" borderColor={borderColor}>
        <Flex
          align="center"
          gap={isCollapsed ? 0 : 2}
          p={2}
          borderRadius="md"
          justify={isCollapsed ? 'center' : 'flex-start'}
        >
          <Avatar size="xs" name={nombreUsuario} bg="brand.500" flexShrink={0} />
          <AnimatePresence>
            {!isCollapsed && (
              <MotionBox
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                overflow="hidden"
                flex="1"
                minW={0}
              >
                <Text fontSize="xs" fontWeight="medium" noOfLines={1}>
                  {nombreUsuario}
                </Text>
                <Text fontSize="10px" color="neutral.400" noOfLines={1}>
                  {user?.email || ''}
                </Text>
              </MotionBox>
            )}
          </AnimatePresence>
          {!isCollapsed && (
            <HStack spacing={0.5} flexShrink={0}>
              <Tooltip label={colorMode === 'light' ? 'Modo oscuro' : 'Modo claro'} hasArrow>
                <IconButton
                  aria-label="Cambiar tema"
                  icon={<Icon as={colorMode === 'light' ? Moon : Sun} boxSize="14px" />}
                  size="xs" variant="ghost"
                  onClick={(e) => { e.stopPropagation(); toggleColorMode(); }}
                />
              </Tooltip>
              <Tooltip label="Cerrar sesión" hasArrow>
                <IconButton
                  aria-label="Cerrar sesión"
                  icon={<Icon as={LogOut} boxSize="14px" />}
                  size="xs" variant="ghost"
                  onClick={(e) => { e.stopPropagation(); logout(); }}
                />
              </Tooltip>
            </HStack>
          )}
        </Flex>
      </Box>

      {/* Collapse toggle */}
      <Box px={2} pb={2} borderTop="1px" borderColor={borderColor}>
        <Tooltip label={isCollapsed ? 'Expandir' : 'Colapsar'} placement="right" hasArrow>
          <IconButton
            icon={isCollapsed ? <ChevronRightIcon /> : <ChevronLeftIcon />}
            onClick={onToggleCollapse}
            variant="ghost"
            size="sm"
            w="full"
            aria-label="Toggle sidebar"
            color="neutral.400"
            _hover={{ color: 'primary.500' }}
          />
        </Tooltip>
      </Box>
    </MotionBox>
  );
};

// ─── AnimatedSidebar (export) ─────────────────────────────────────────────────
const AnimatedSidebar = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const esMovil = useEsMovil();

  // En móvil la navegación es la barra inferior + cabecera (MobileShell).
  if (esMovil) return null;

  return (
    <SidebarContent
      isCollapsed={isCollapsed}
      onToggleCollapse={() => setIsCollapsed(c => !c)}
    />
  );
};

export default AnimatedSidebar;
