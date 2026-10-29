import React, { useState, useEffect } from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter,
  ModalCloseButton, Button, Text, Textarea, FormControl, FormLabel,
  FormErrorMessage, VStack, Box,
} from '@chakra-ui/react';

/**
 * Anular ≠ eliminar: la venta conserva su número. El modal muestra número y
 * total para confirmar que es la venta correcta, y exige el motivo.
 */
const AnularVentaModal = ({ venta, isOpen, onClose, onConfirm, isLoading, formatCurrency }) => {
  const [motivo, setMotivo] = useState('');
  const [tocado, setTocado] = useState(false);

  useEffect(() => {
    if (isOpen) { setMotivo(''); setTocado(false); }
  }, [isOpen]);

  if (!venta) return null;
  const invalido = !motivo.trim();

  return (
    <Modal isOpen={isOpen} onClose={onClose} isCentered>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Anular venta</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack align="stretch" spacing={4}>
            <Box bg="gray.50" p={3} borderRadius="md">
              <Text fontWeight="bold" fontSize="lg">{venta.numero}</Text>
              <Text>{venta.cliente_nombre}</Text>
              <Text fontWeight="semibold">
                Total: {formatCurrency(venta.total, venta.moneda)}
              </Text>
            </Box>
            <Text fontSize="sm" color="gray.600">
              La venta no se borra: queda anulada con su número, sale de cuentas
              por cobrar y de los reportes, y se revierte el stock si ya se entregó.
            </Text>
            <FormControl isRequired isInvalid={tocado && invalido}>
              <FormLabel>Motivo de la anulación</FormLabel>
              <Textarea
                value={motivo}
                onChange={(e) => setMotivo(e.target.value)}
                onBlur={() => setTocado(true)}
                placeholder="Ej.: el cliente desistió del pedido"
                autoFocus
              />
              <FormErrorMessage>El motivo es obligatorio.</FormErrorMessage>
            </FormControl>
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>Volver</Button>
          <Button
            colorScheme="red"
            isDisabled={invalido}
            isLoading={isLoading}
            onClick={() => onConfirm(motivo.trim())}
          >
            Anular {venta.numero}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default AnularVentaModal;
