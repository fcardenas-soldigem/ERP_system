import React from 'react';
import { Flex, Box, Heading, Text, HStack } from '@chakra-ui/react';

/**
 * PageHeader — encabezado estándar de pantalla.
 * UN h1 por pantalla (jerarquía tipográfica); acciones a la derecha.
 */
const PageHeader = ({ title, subtitle, actions, ...rest }) => (
  <Flex justify="space-between" align="flex-start" wrap="wrap" gap={3} mb={6} {...rest}>
    <Box>
      <Heading as="h1" size="lg" color="neutral.900">{title}</Heading>
      {subtitle && (
        <Text fontSize="sm" color="neutral.500" mt={1}>{subtitle}</Text>
      )}
    </Box>
    {actions && <HStack spacing={2}>{actions}</HStack>}
  </Flex>
);

export default PageHeader;
