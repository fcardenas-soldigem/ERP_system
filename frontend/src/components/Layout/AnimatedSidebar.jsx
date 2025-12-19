import React, { useState } from 'react';
import {
  Box,
  VStack,
  Icon,
  Text,
  Flex,
  useColorModeValue,
  Collapse,
  IconButton,
  Tooltip,
  Avatar,
  HStack,
  Divider,
  useBreakpointValue,
  Drawer,
  DrawerBody,
  DrawerHeader,
  DrawerOverlay,
  DrawerContent,
  DrawerCloseButton,
  useDisclosure,
} from '@chakra-ui/react';
import { NavLink } from 'react-router-dom';
import { ChevronDownIcon, ChevronUpIcon, ChevronLeftIcon, ChevronRightIcon, HamburgerIcon } from '@chakra-ui/icons';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';

// Componente Motion con Chakra UI
const MotionBox = motion(Box);
const MotionFlex = motion(Flex);
const MotionText = motion(Text);

const MenuItem = ({ icon, children, to, subItems, isOpen, onToggle, isCollapsed }) => {
  const activeBg = useColorModeValue('blue.50', 'blue.900');
  const activeColor = useColorModeValue('blue.600', 'blue.200');
  const hoverBg = useColorModeValue('gray.100', 'gray.700');
  const textColor = useColorModeValue('gray.700', 'gray.200');

  if (subItems) {
    return (
      <Box width="100%">
        <Tooltip label={isCollapsed ? children : ''} placement="right" hasArrow>
          <MotionFlex
            align="center"
            p={isCollapsed ? "3" : "4"}
            mx={isCollapsed ? "2" : "4"}
            borderRadius="lg"
            role="group"
            cursor="pointer"
            onClick={onToggle}
            color={textColor}
            justify={isCollapsed ? "center" : "flex-start"}
            whileHover={{ scale: 1.02, x: 5 }}
            whileTap={{ scale: 0.98 }}
            transition={{ duration: 0.2 }}
            _hover={{
              bg: hoverBg,
              color: activeColor,
            }}
          >
            <Icon
              mr={isCollapsed ? "0" : "4"}
              fontSize="20"
              as={icon}
            />
            <AnimatePresence>
              {!isCollapsed && (
                <MotionText
                  flex="1"
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: "auto" }}
                  exit={{ opacity: 0, width: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  {children}
                </MotionText>
              )}
            </AnimatePresence>
            {!isCollapsed && (
              <Icon
                as={isOpen ? ChevronUpIcon : ChevronDownIcon}
                transition="all .25s ease-in-out"
              />
            )}
          </MotionFlex>
        </Tooltip>
        {!isCollapsed && (
          <Collapse in={isOpen}>
            <VStack pl={8} mt={1} spacing={1}>
              {subItems.map((item, index) => (
                <NavLink
                  key={index}
                  to={item.path}
                  style={{ textDecoration: 'none', width: '100%' }}
                >
                  {({ isActive }) => (
                    <MotionFlex
                      align="center"
                      p="3"
                      mx="4"
                      borderRadius="lg"
                      cursor="pointer"
                      bg={isActive ? activeBg : 'transparent'}
                      color={isActive ? activeColor : textColor}
                      whileHover={{ scale: 1.02, x: 5 }}
                      whileTap={{ scale: 0.98 }}
                      _hover={{
                        bg: hoverBg,
                        color: activeColor,
                      }}
                    >
                      <Text fontSize="sm">{item.name}</Text>
                    </MotionFlex>
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
    <NavLink
      to={to}
      style={{ textDecoration: 'none', width: '100%' }}
    >
      {({ isActive }) => (
        <Tooltip label={isCollapsed ? children : ''} placement="right" hasArrow>
          <MotionFlex
            align="center"
            p={isCollapsed ? "3" : "4"}
            mx={isCollapsed ? "2" : "4"}
            borderRadius="lg"
            cursor="pointer"
            bg={isActive ? activeBg : 'transparent'}
            color={isActive ? activeColor : textColor}
            justify={isCollapsed ? "center" : "flex-start"}
            whileHover={{ scale: 1.02, x: 5 }}
            whileTap={{ scale: 0.98 }}
            transition={{ duration: 0.2 }}
            _hover={{
              bg: hoverBg,
              color: activeColor,
            }}
          >
            <Icon
              mr={isCollapsed ? "0" : "4"}
              fontSize="20"
              as={icon}
            />
            <AnimatePresence>
              {!isCollapsed && (
                <MotionText
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: "auto" }}
                  exit={{ opacity: 0, width: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  {children}
                </MotionText>
              )}
            </AnimatePresence>
          </MotionFlex>
        </Tooltip>
      )}
    </NavLink>
  );
};

const SidebarContent = ({ menuItems, isCollapsed, onToggleCollapse }) => {
  const [openMenus, setOpenMenus] = useState({});
  const { user } = useAuth();
  
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const brandColor = useColorModeValue('blue.600', 'blue.300');

  const toggleMenu = (menuName) => {
    if (!isCollapsed) {
      setOpenMenus(prev => ({
        ...prev,
        [menuName]: !prev[menuName]
      }));
    }
  };

  return (
    <MotionBox
      bg={bgColor}
      borderRight="1px"
      borderRightColor={borderColor}
      h="100vh"
      position="sticky"
      top="0"
      animate={{
        width: isCollapsed ? "80px" : "280px",
      }}
      transition={{
        duration: 0.3,
        ease: "easeInOut"
      }}
      display="flex"
      flexDirection="column"
    >
      {/* Header con Logo */}
      <Flex
        align="center"
        justify={isCollapsed ? "center" : "space-between"}
        p={4}
        borderBottom="1px"
        borderColor={borderColor}
      >
        <AnimatePresence>
          {!isCollapsed && (
            <MotionFlex
              align="center"
              gap={3}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <Box
                w="40px"
                h="40px"
                bg={brandColor}
                borderRadius="lg"
                display="flex"
                alignItems="center"
                justifyContent="center"
                color="white"
                fontWeight="bold"
                fontSize="xl"
              >
                E
              </Box>
              <Text fontSize="xl" fontWeight="bold" color={brandColor}>
                ERP System
              </Text>
            </MotionFlex>
          )}
        </AnimatePresence>
        
        {isCollapsed && (
          <Box
            w="40px"
            h="40px"
            bg={brandColor}
            borderRadius="lg"
            display="flex"
            alignItems="center"
            justifyContent="center"
            color="white"
            fontWeight="bold"
            fontSize="xl"
          >
            E
          </Box>
        )}
      </Flex>

      {/* Menu Items */}
      <VStack
        spacing={1}
        align="stretch"
        flex="1"
        overflowY="auto"
        overflowX="hidden"
        py={4}
        css={{
          '&::-webkit-scrollbar': {
            width: '4px',
          },
          '&::-webkit-scrollbar-track': {
            width: '6px',
          },
          '&::-webkit-scrollbar-thumb': {
            background: borderColor,
            borderRadius: '24px',
          },
        }}
      >
        {menuItems.map((item, index) => (
          <MenuItem
            key={index}
            icon={item.icon}
            to={item.path}
            subItems={item.subItems}
            isOpen={openMenus[item.name]}
            onToggle={() => toggleMenu(item.name)}
            isCollapsed={isCollapsed}
          >
            {item.name}
          </MenuItem>
        ))}
      </VStack>

      <Divider />

      {/* User Profile */}
      <MotionBox
        p={4}
        borderTop="1px"
        borderColor={borderColor}
      >
        <Tooltip label={isCollapsed ? user?.username || 'Usuario' : ''} placement="right" hasArrow>
          <Flex
            align="center"
            gap={3}
            p={2}
            borderRadius="lg"
            cursor="pointer"
            justify={isCollapsed ? "center" : "flex-start"}
            _hover={{
              bg: useColorModeValue('gray.100', 'gray.700'),
            }}
          >
            <Avatar
              size="sm"
              name={user?.username || 'Usuario'}
              bg={brandColor}
            />
            <AnimatePresence>
              {!isCollapsed && (
                <MotionBox
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: "auto" }}
                  exit={{ opacity: 0, width: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <Text fontSize="sm" fontWeight="medium">
                    {user?.username || 'Usuario'}
                  </Text>
                  <Text fontSize="xs" color="gray.500">
                    {user?.email || 'usuario@erp.com'}
                  </Text>
                </MotionBox>
              )}
            </AnimatePresence>
          </Flex>
        </Tooltip>
      </MotionBox>

      {/* Toggle Button */}
      <Box p={2} borderTop="1px" borderColor={borderColor}>
        <Tooltip label={isCollapsed ? "Expandir" : "Colapsar"} placement="right" hasArrow>
          <IconButton
            icon={isCollapsed ? <ChevronRightIcon /> : <ChevronLeftIcon />}
            onClick={onToggleCollapse}
            variant="ghost"
            w="full"
            aria-label="Toggle sidebar"
          />
        </Tooltip>
      </Box>
    </MotionBox>
  );
};

const AnimatedSidebar = ({ menuItems }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const isMobile = useBreakpointValue({ base: true, md: false });

  const toggleCollapse = () => {
    setIsCollapsed(!isCollapsed);
  };

  // En móvil, mostrar un drawer
  if (isMobile) {
    return (
      <>
        <IconButton
          icon={<HamburgerIcon />}
          onClick={onOpen}
          position="fixed"
          top={4}
          left={4}
          zIndex={1000}
          colorScheme="blue"
          aria-label="Open menu"
        />
        <Drawer isOpen={isOpen} placement="left" onClose={onClose}>
          <DrawerOverlay />
          <DrawerContent>
            <DrawerCloseButton />
            <DrawerHeader>Menú</DrawerHeader>
            <DrawerBody p={0}>
              <SidebarContent
                menuItems={menuItems}
                isCollapsed={false}
                onToggleCollapse={() => {}}
              />
            </DrawerBody>
          </DrawerContent>
        </Drawer>
      </>
    );
  }

  // En desktop, mostrar sidebar normal
  return (
    <SidebarContent
      menuItems={menuItems}
      isCollapsed={isCollapsed}
      onToggleCollapse={toggleCollapse}
    />
  );
};

export default AnimatedSidebar;


