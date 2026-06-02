import React, { useState } from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalFooter,
  ModalBody, ModalCloseButton, Button, VStack, FormControl,
  FormLabel, Input, Textarea, Badge, Text, HStack,
  useToast,
} from '@chakra-ui/react';
import { FaCheck } from 'react-icons/fa';
import serviciosService from '../../services/serviciosService';

const ESTADOS_RAPIDOS = [
  'Esperando repuestos',
  'En diagnóstico',
  'En reparación',
  'Listo para entrega',
  'Esperando aprobación',
  'Pendiente de revisión',
];

const ModalSeguimiento = ({ isOpen, onClose, ordenId, ordenNumero, onSuccess }) => {
  const toast = useToast();
  const [data, setData] = useState({
    estado_reportado: '',
    fecha_entrega_prometida: '',
    notas: '',
  });
  const [guardando, setGuardando] = useState(false);

  const handleClose = () => {
    setData({ estado_reportado: '', fecha_entrega_prometida: '', notas: '' });
    onClose();
  };

  const handleGuardar = async () => {
    if (!data.estado_reportado.trim()) {
      toast({ title: 'El estado reportado es requerido', status: 'warning', duration: 3000, isClosable: true });
      return;
    }
    if (!data.notas.trim()) {
      toast({ title: 'Las notas son requeridas', status: 'warning', duration: 3000, isClosable: true });
      return;
    }
    try {
      setGuardando(true);
      await serviciosService.agregarSeguimiento(ordenId, {
        ...data,
        fecha_entrega_prometida: data.fecha_entrega_prometida || null,
      });
      toast({
        title: 'Seguimiento registrado',
        description: `${ordenNumero} — ${data.estado_reportado}`,
        status: 'success',
        duration: 2500,
        isClosable: true,
      });
      handleClose();
      onSuccess?.();
    } catch (err) {
      toast({
        title: 'Error al guardar seguimiento',
        description: err.response?.data ? JSON.stringify(err.response.data).slice(0, 120) : err.message,
        status: 'error',
        duration: 4000,
        isClosable: true,
      });
    } finally {
      setGuardando(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="md">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader fontSize="md">
          Registrar seguimiento del proveedor
          {ordenNumero && (
            <Text fontSize="sm" fontWeight="normal" color="gray.500" mt={0.5}>
              {ordenNumero}
            </Text>
          )}
        </ModalHeader>
        <ModalCloseButton />

        <ModalBody>
          <VStack spacing={4} align="stretch">
            <FormControl isRequired>
              <FormLabel fontSize="sm">Estado reportado por el proveedor</FormLabel>
              <Input
                placeholder="Ej: En reparación, Esperando repuestos..."
                value={data.estado_reportado}
                onChange={(e) => setData(p => ({ ...p, estado_reportado: e.target.value }))}
                autoFocus
              />
              {/* Atajos rápidos */}
              <HStack mt={2} flexWrap="wrap" gap={1}>
                {ESTADOS_RAPIDOS.map((s) => (
                  <Badge
                    key={s}
                    as="button"
                    onClick={() => setData(p => ({ ...p, estado_reportado: s }))}
                    colorScheme={data.estado_reportado === s ? 'blue' : 'gray'}
                    variant={data.estado_reportado === s ? 'solid' : 'subtle'}
                    cursor="pointer"
                    fontSize="xs"
                    px={2}
                    py={0.5}
                    borderRadius="full"
                    _hover={{ opacity: 0.8 }}
                  >
                    {data.estado_reportado === s && <FaCheck style={{ display: 'inline', marginRight: 3 }} size={9} />}
                    {s}
                  </Badge>
                ))}
              </HStack>
            </FormControl>

            <FormControl>
              <FormLabel fontSize="sm">Fecha de entrega prometida</FormLabel>
              <Input
                type="date"
                value={data.fecha_entrega_prometida}
                onChange={(e) => setData(p => ({ ...p, fecha_entrega_prometida: e.target.value }))}
              />
            </FormControl>

            <FormControl isRequired>
              <FormLabel fontSize="sm">Notas del seguimiento</FormLabel>
              <Textarea
                placeholder="Detalles del estado, qué se le dijo al cliente, compromisos del proveedor..."
                value={data.notas}
                onChange={(e) => setData(p => ({ ...p, notas: e.target.value }))}
                rows={3}
              />
            </FormControl>
          </VStack>
        </ModalBody>

        <ModalFooter gap={2}>
          <Button variant="ghost" size="sm" onClick={handleClose}>
            Cancelar
          </Button>
          <Button
            colorScheme="blue"
            size="sm"
            isLoading={guardando}
            loadingText="Guardando..."
            onClick={handleGuardar}
          >
            Guardar seguimiento
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ModalSeguimiento;
