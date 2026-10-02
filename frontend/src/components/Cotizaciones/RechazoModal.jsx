import React, { useState } from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter,
  ModalCloseButton, Button, VStack, Radio, RadioGroup, Textarea, Text, FormControl, FormLabel,
} from '@chakra-ui/react';

export const MOTIVOS_RECHAZO = [
  { value: 'precio', label: 'Precio' },
  { value: 'plazo', label: 'Plazo' },
  { value: 'competidor', label: 'Competidor' },
  { value: 'sin_presupuesto', label: 'Sin presupuesto' },
  { value: 'otro', label: 'Otro' },
];

/**
 * F4a — Modal de rechazo de cotización. Motivo obligatorio (radio); nota
 * obligatoria solo si motivo='otro'. Confirmar deshabilitado hasta elegir motivo.
 */
const RechazoModal = ({ isOpen, onClose, onConfirm, numero }) => {
  const [motivo, setMotivo] = useState('');
  const [nota, setNota] = useState('');

  const notaRequerida = motivo === 'otro';
  const puedeConfirmar = !!motivo && (!notaRequerida || nota.trim().length > 0);

  const confirmar = () => {
    onConfirm({ motivo_rechazo: motivo, motivo_rechazo_nota: nota.trim() || null });
    setMotivo(''); setNota('');
  };

  const cerrar = () => { setMotivo(''); setNota(''); onClose(); };

  return (
    <Modal isOpen={isOpen} onClose={cerrar} isCentered>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Rechazar cotización {numero}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <FormControl isRequired>
            <FormLabel fontSize="sm">Motivo del rechazo</FormLabel>
            <RadioGroup value={motivo} onChange={setMotivo}>
              <VStack align="start" spacing={2}>
                {MOTIVOS_RECHAZO.map((m) => (
                  <Radio key={m.value} value={m.value}>{m.label}</Radio>
                ))}
              </VStack>
            </RadioGroup>
          </FormControl>
          {notaRequerida && (
            <FormControl mt={4} isRequired>
              <FormLabel fontSize="sm">Detalle (obligatorio para “Otro”)</FormLabel>
              <Textarea value={nota} onChange={(e) => setNota(e.target.value)}
                placeholder="Describe el motivo" rows={3} />
            </FormControl>
          )}
          {!notaRequerida && motivo && (
            <FormControl mt={4}>
              <FormLabel fontSize="sm">Nota (opcional)</FormLabel>
              <Textarea value={nota} onChange={(e) => setNota(e.target.value)} rows={2} />
            </FormControl>
          )}
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={cerrar}>Cancelar</Button>
          <Button colorScheme="red" onClick={confirmar} isDisabled={!puedeConfirmar}>
            Rechazar
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default RechazoModal;
