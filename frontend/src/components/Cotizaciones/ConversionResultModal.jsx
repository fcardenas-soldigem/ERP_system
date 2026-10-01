import React from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter,
  ModalCloseButton, Button, VStack, HStack, Box, Text, Badge, Icon, Divider,
} from '@chakra-ui/react';
import { FaCheckCircle, FaFileInvoiceDollar, FaBoxOpen, FaExclamationTriangle, FaWarehouse } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';

/**
 * F2 — Resultado de la conversión Cotización → Venta.
 * Muestra: venta creada, OCs por proveedor, líneas sin proveedor (aviso) y
 * líneas reservadas de stock. Si la cotización ya estaba convertida, el backend
 * devuelve la venta existente (reutilizada) y se muestra igual.
 */
const ConversionResultModal = ({ isOpen, onClose, result, cotizacionId }) => {
  const navigate = useNavigate();
  if (!result) return null;

  const ocs = result.ocs_creadas || [];
  const sinProveedor = result.lineas_sin_proveedor || [];
  const reservadas = result.lineas_stock_reservadas || 0;

  const irAVenta = () => {
    onClose();
    if (result.venta_id) navigate(`/app/ventas/${result.venta_id}`);
  };

  const asignarProveedor = () => {
    onClose();
    if (cotizacionId) navigate(`/app/cotizaciones/${cotizacionId}/editar`);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg" isCentered>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>
          <HStack spacing={2}>
            <Icon as={FaCheckCircle} color="green.500" />
            <Text>Cotización convertida</Text>
          </HStack>
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack align="stretch" spacing={4}>
            {/* Venta creada */}
            <Box p={3} bg="green.50" borderRadius="md" border="1px solid" borderColor="green.200">
              <HStack justify="space-between">
                <HStack spacing={2}>
                  <Icon as={FaFileInvoiceDollar} color="green.600" />
                  <Text fontWeight="bold">Venta {result.venta_numero}</Text>
                </HStack>
                <Button size="sm" colorScheme="green" variant="outline" onClick={irAVenta}>
                  Ver venta
                </Button>
              </HStack>
            </Box>

            {/* OCs por proveedor */}
            {ocs.length > 0 && (
              <Box>
                <HStack spacing={2} mb={2}>
                  <Icon as={FaBoxOpen} color="blue.500" />
                  <Text fontWeight="semibold">
                    {ocs.length} orden{ocs.length > 1 ? 'es' : ''} de compra (borrador)
                  </Text>
                </HStack>
                <VStack align="stretch" spacing={1}>
                  {ocs.map((oc) => (
                    <HStack key={oc.id} justify="space-between" px={3} py={2} bg="gray.50" borderRadius="md">
                      <Text fontSize="sm"><b>OC-{oc.numero}</b> · {oc.proveedor}</Text>
                      <Badge colorScheme="blue">{oc.lineas} línea{oc.lineas > 1 ? 's' : ''}</Badge>
                    </HStack>
                  ))}
                </VStack>
              </Box>
            )}

            {/* Reservadas de stock (con_stock) */}
            {reservadas > 0 && (
              <HStack spacing={2} px={3} py={2} bg="purple.50" borderRadius="md">
                <Icon as={FaWarehouse} color="purple.500" />
                <Text fontSize="sm">
                  {reservadas} línea{reservadas > 1 ? 's' : ''} reservada{reservadas > 1 ? 's' : ''} de stock
                  (se descuenta al entregar).
                </Text>
              </HStack>
            )}

            {/* Líneas sin proveedor (aviso) */}
            {sinProveedor.length > 0 && (
              <Box p={3} bg="orange.50" borderRadius="md" border="1px solid" borderColor="orange.200">
                <HStack spacing={2} mb={2}>
                  <Icon as={FaExclamationTriangle} color="orange.500" />
                  <Text fontWeight="semibold" color="orange.700">
                    {sinProveedor.length} línea{sinProveedor.length > 1 ? 's' : ''} sin proveedor — no generaron OC
                  </Text>
                </HStack>
                <VStack align="stretch" spacing={1} mb={2}>
                  {sinProveedor.map((l) => (
                    <Text key={l.detalle_id} fontSize="sm" color="orange.800">• {l.descripcion}</Text>
                  ))}
                </VStack>
                <Button size="sm" colorScheme="orange" variant="outline" onClick={asignarProveedor}>
                  Asignar proveedor
                </Button>
              </Box>
            )}

            {ocs.length === 0 && sinProveedor.length === 0 && reservadas === 0 && (
              <Text fontSize="sm" color="gray.500">Sin órdenes de compra ni reservas asociadas.</Text>
            )}
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>Cerrar</Button>
          <Button colorScheme="green" onClick={irAVenta}>Ver venta</Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ConversionResultModal;
