import React from 'react';
import { VStack, Icon, Text, Button } from '@chakra-ui/react';
import { Inbox } from 'lucide-react';

/**
 * EmptyState — estado vacío estándar: ícono + texto + CTA opcional.
 * Neutro (sin rojos/verdes): un vacío no es un error.
 */
const EmptyState = ({ icon = Inbox, title, description, ctaLabel, onCta, ...rest }) => (
  <VStack spacing={3} py={10} px={6} textAlign="center" {...rest}>
    <Icon as={icon} boxSize="32px" color="neutral.300" strokeWidth={1.5} />
    <Text fontWeight="semibold" color="neutral.700">{title}</Text>
    {description && (
      <Text fontSize="sm" color="neutral.500" maxW="360px">{description}</Text>
    )}
    {ctaLabel && (
      <Button variant="secondary" size="sm" onClick={onCta} mt={1}>
        {ctaLabel}
      </Button>
    )}
  </VStack>
);

export default EmptyState;
