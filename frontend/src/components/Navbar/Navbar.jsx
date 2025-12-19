import React, { useState } from 'react';
import {
  Box,
  Flex,
  Text,
  IconButton,
  Button,
  Stack,
  Collapse,
  useColorModeValue,
  useBreakpointValue,
  useDisclosure,
  Container,
  useColorMode,
  Drawer,
  DrawerBody,
  DrawerHeader,
  DrawerOverlay,
  DrawerContent,
  DrawerCloseButton,
  VStack
} from '@chakra-ui/react';
import { HamburgerIcon, CloseIcon, MoonIcon, SunIcon } from '@chakra-ui/icons';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link as RouterLink } from 'react-router-dom';

const Navbar = () => {
  const { isOpen, onToggle, onClose } = useDisclosure();
  const { colorMode, toggleColorMode } = useColorMode();
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const menuItems = [
    { text: 'Dashboard', path: '/dashboard' },
    { text: 'Ventas', path: '/ventas' },
    { text: 'Compras', path: '/compras' },
    { text: 'Inventario', path: '/inventario' },
    { text: 'Machine Learning', path: '/ml-dashboard' }
  ];

  const NavDrawer = () => (
    <Drawer isOpen={isOpen} placement="left" onClose={onClose}>
      <DrawerOverlay />
      <DrawerContent>
        <DrawerCloseButton />
        <DrawerHeader>ERP System</DrawerHeader>
        <DrawerBody>
          <VStack spacing={4} align="stretch">
            {menuItems.map((item) => (
              <Button
                key={item.text}
                as={RouterLink}
                to={item.path}
                variant="ghost"
                w="full"
                onClick={onClose}
              >
                {item.text}
              </Button>
            ))}
          </VStack>
        </DrawerBody>
      </DrawerContent>
    </Drawer>
  );

  return (
    <Box>
      <Flex
        bg={useColorModeValue('white', 'gray.800')}
        color={useColorModeValue('gray.600', 'white')}
        minH={'60px'}
        py={{ base: 2 }}
        px={{ base: 4 }}
        borderBottom={1}
        borderStyle={'solid'}
        borderColor={useColorModeValue('gray.200', 'gray.900')}
        align={'center'}
      >
        <Container maxW="container.xl">
          <Flex align="center" justify="space-between">
            <Flex>
              <IconButton
                display={{ base: 'flex', md: 'none' }}
                onClick={onToggle}
                icon={isOpen ? <CloseIcon w={3} h={3} /> : <HamburgerIcon w={5} h={5} />}
                variant={'ghost'}
                aria-label={'Toggle Navigation'}
                mr={2}
              />

              <Text
                textAlign={useBreakpointValue({ base: 'center', md: 'left' })}
                fontFamily={'heading'}
                color={useColorModeValue('gray.800', 'white')}
                fontWeight="bold"
              >
                ERP System
              </Text>
            </Flex>

            <Stack
              direction={'row'}
              spacing={6}
              display={{ base: 'none', md: 'flex' }}
              alignItems={'center'}
            >
              {menuItems.map((item) => (
                <Button
                  key={item.text}
                  as={RouterLink}
                  to={item.path}
                  variant="ghost"
                  color={useColorModeValue('gray.600', 'white')}
                  _hover={{
                    bg: useColorModeValue('gray.100', 'gray.700')
                  }}
                >
                  {item.text}
                </Button>
              ))}
            </Stack>

            <Stack
              flex={{ base: 1, md: 0 }}
              justify={'flex-end'}
              direction={'row'}
              spacing={6}
            >
              <IconButton
                aria-label="Toggle color mode"
                icon={colorMode === 'light' ? <MoonIcon /> : <SunIcon />}
                onClick={toggleColorMode}
                variant="ghost"
              />
              
              {user && (
                <Button
                  variant="ghost"
                  onClick={handleLogout}
                >
                  Cerrar Sesión
                </Button>
              )}
            </Stack>
          </Flex>
        </Container>
      </Flex>

      <NavDrawer />
    </Box>
  );
};

export default Navbar; 