import React from 'react';
import {
  Box, Heading, HStack, Tabs, TabList, TabPanels, Tab, TabPanel,
  Badge,
} from '@chakra-ui/react';
import VentaList from './VentaList';
import VentasChatBar from './VentasChatBar';
import CuentasPorCobrar from '../Cuentas/CuentasPorCobrar';

const Ventas = () => (
  <>
    <Box>
      <HStack justify="space-between" mb={4}>
        <Heading size="md" fontWeight="semibold">Ventas</Heading>
      </HStack>

      <Tabs variant="line" colorScheme="primary" isLazy>
        <TabList borderBottomColor="neutral.200">
          <Tab fontSize="sm" fontWeight="medium">Todas las ventas</Tab>
          <Tab fontSize="sm" fontWeight="medium">
            Por cobrar
            <Badge ml={2} colorScheme="orange" variant="subtle" fontSize="10px" borderRadius="sm">
              Crédito
            </Badge>
          </Tab>
        </TabList>

        <TabPanels>
          <TabPanel px={0} pt={4}>
            <VentaList />
          </TabPanel>
          <TabPanel px={0} pt={4}>
            <CuentasPorCobrar />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Box>

    <VentasChatBar />
  </>
);

export default Ventas;
