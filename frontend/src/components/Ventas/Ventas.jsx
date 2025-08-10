import React from 'react';
import {
  Container,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Heading,
  HStack,
} from '@chakra-ui/react';
import VentaList from './VentaList';
import VentasStats from './VentasStats';
import VentasChatBar from './VentasChatBar';

const Ventas = () => {
  return (
    <>
      <Container maxW="container.xl" py={5}>
        <HStack justify="space-between" mb={5}>
          <Heading>Gestión de Ventas</Heading>
        </HStack>

        <Tabs variant="enclosed" mt={6}>
          <TabList>
            <Tab>Ventas</Tab>
          </TabList>

          <TabPanels>
            <TabPanel>
              <VentaList />
            </TabPanel>
          </TabPanels>
        </Tabs>
      </Container>
      
      {/* Chatbar flotante del asistente de ventas */}
      <VentasChatBar />
    </>
  );
};

export default Ventas;