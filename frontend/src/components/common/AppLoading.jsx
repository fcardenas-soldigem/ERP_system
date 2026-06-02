import React from 'react';
import { Box, Center, Spinner, Text, VStack } from '@chakra-ui/react';

const AppLoading = () => (
  <Center
    position="fixed"
    inset="0"
    bg="white"
    zIndex="9999"
    _dark={{ bg: 'neutral.900' }}
  >
    <VStack spacing={4}>
      {/* Logo mark */}
      <Box
        w="48px"
        h="48px"
        borderRadius="xl"
        bg="primary.500"
        display="flex"
        alignItems="center"
        justifyContent="center"
        color="white"
        fontWeight="bold"
        fontSize="xl"
        letterSpacing="tight"
        boxShadow="md"
      >
        E
      </Box>

      <Spinner
        size="sm"
        color="primary.500"
        thickness="2px"
        speed="0.65s"
      />

      <Text fontSize="xs" color="neutral.400" letterSpacing="wide">
        Cargando…
      </Text>
    </VStack>
  </Center>
);

export default AppLoading;
