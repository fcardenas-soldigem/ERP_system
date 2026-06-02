import React from 'react';
import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Navbar from '../Navbar/Navbar';
import AnimatedSidebar from './AnimatedSidebar';
import EmpresaCheck from './EmpresaCheck';
import AppLoading from '../common/AppLoading';
import { Box, Flex } from '@chakra-ui/react';

const Layout = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <AppLoading />;

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return (
    <EmpresaCheck>
      <Flex minH="100vh" bg="bg.default">
        <AnimatedSidebar />
        <Box flex="1" overflow="auto" minW={0}>
          <Navbar />
          <Box p={6}>
            <Outlet />
          </Box>
        </Box>
      </Flex>
    </EmpresaCheck>
  );
};

export default Layout;
