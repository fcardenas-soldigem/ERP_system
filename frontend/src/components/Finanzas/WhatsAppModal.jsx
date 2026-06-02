import React, { useState, useMemo } from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter, ModalCloseButton,
  Button, Select, Textarea, Text, VStack, HStack, Box, Badge, Icon, useToast,
} from '@chakra-ui/react';
import { FiMessageCircle, FiCopy, FiCheck } from 'react-icons/fi';

const fmt = (n) => Number(n ?? 0).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const buildMessage = (moroso) => {
  if (!moroso) return '';
  const fecha = moroso.vencimiento
    ? new Date(moroso.vencimiento + 'T00:00:00').toLocaleDateString('es-PE', { day: 'numeric', month: 'long', year: 'numeric' })
    : 'fecha pendiente';
  return `Hola ${moroso.cliente}, te recordamos que tienes una factura pendiente de pago por S/ ${fmt(moroso.monto)} con vencimiento del ${fecha}. Cualquier consulta estamos atentos.`;
};

const WhatsAppModal = ({ isOpen, onClose, morosos = [] }) => {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [copied, setCopied] = useState(false);
  const toast = useToast();

  const moroso = morosos[selectedIdx] ?? null;
  const mensaje = useMemo(() => buildMessage(moroso), [moroso]);

  const telefono = moroso?.telefono?.replace(/\D/g, '') ?? '';
  const waLink = telefono
    ? `https://wa.me/51${telefono}?text=${encodeURIComponent(mensaje)}`
    : null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(mensaje);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast({ title: 'No se pudo copiar', status: 'error', duration: 2000, isClosable: true });
    }
  };

  const handleWhatsApp = () => {
    if (waLink) {
      window.open(waLink, '_blank', 'noopener,noreferrer');
    } else {
      toast({
        title: 'Sin número de teléfono',
        description: 'Este cliente no tiene teléfono registrado. Copia el mensaje manualmente.',
        status: 'warning',
        duration: 3500,
        isClosable: true,
      });
    }
  };

  if (!morosos.length) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md" isCentered>
      <ModalOverlay bg="blackAlpha.600" />
      <ModalContent borderRadius="2xl" mx={4}>
        <ModalHeader pb={2}>
          <HStack spacing={2}>
            <Icon as={FiMessageCircle} color="green.500" />
            <Text fontSize="md" fontWeight="bold">Enviar recordatorio de pago</Text>
          </HStack>
        </ModalHeader>
        <ModalCloseButton />

        <ModalBody>
          <VStack spacing={4} align="stretch">

            {/* Selector de cliente */}
            {morosos.length > 1 && (
              <Box>
                <Text fontSize="xs" fontWeight="semibold" color="gray.500" mb={1} textTransform="uppercase" letterSpacing="wide">
                  ¿A quién le envías?
                </Text>
                <Select
                  size="sm"
                  borderRadius="lg"
                  value={selectedIdx}
                  onChange={e => setSelectedIdx(Number(e.target.value))}
                >
                  {morosos.map((m, i) => (
                    <option key={i} value={i}>
                      {m.cliente} — S/ {fmt(m.monto)} ({m.dias}d)
                    </option>
                  ))}
                </Select>
              </Box>
            )}

            {/* Datos del cliente seleccionado */}
            {moroso && (
              <Box bg="orange.50" borderRadius="lg" p={3} border="1px solid" borderColor="orange.200">
                <HStack justify="space-between">
                  <Text fontSize="sm" fontWeight="semibold" color="orange.800">{moroso.cliente}</Text>
                  <Badge colorScheme="orange" variant="subtle">{moroso.dias} días de atraso</Badge>
                </HStack>
                <Text fontSize="xs" color="orange.600" mt={1}>
                  Deuda: S/ {fmt(moroso.monto)}
                  {moroso.vencimiento ? ` · venció el ${moroso.vencimiento}` : ''}
                </Text>
                {!telefono && (
                  <Text fontSize="10px" color="orange.500" mt={1}>
                    Sin teléfono registrado — podrás copiar el mensaje igualmente
                  </Text>
                )}
              </Box>
            )}

            {/* Mensaje pre-redactado */}
            <Box>
              <Text fontSize="xs" fontWeight="semibold" color="gray.500" mb={1} textTransform="uppercase" letterSpacing="wide">
                Mensaje (editable)
              </Text>
              <Textarea
                value={mensaje}
                readOnly
                fontSize="sm"
                borderRadius="lg"
                rows={4}
                bg="gray.50"
                resize="none"
                color="gray.700"
              />
            </Box>

          </VStack>
        </ModalBody>

        <ModalFooter gap={2} pt={2}>
          <Button
            size="sm"
            variant="ghost"
            leftIcon={<Icon as={copied ? FiCheck : FiCopy} />}
            onClick={handleCopy}
            color={copied ? 'green.600' : 'gray.600'}
          >
            {copied ? 'Copiado' : 'Copiar mensaje'}
          </Button>
          <Button
            size="sm"
            colorScheme="green"
            leftIcon={<Icon as={FiMessageCircle} />}
            onClick={handleWhatsApp}
            isDisabled={!waLink}
          >
            Abrir WhatsApp
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default WhatsAppModal;
