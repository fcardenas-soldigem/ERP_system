import React, { useState, useEffect } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  Text,
  Button,
  VStack,
  Badge,
  useDisclosure,
} from '@chakra-ui/react';
import { useAuth } from '../context/AuthContext';
import EmpresaForm from '../Empresa/EmpresaForm';

// RUC válido en Perú: 11 dígitos, empieza con 10 (persona natural) o 20 (persona jurídica)
const isRucInvalido = (ruc) => {
  if (!ruc) return true;
  return !/^(10|20)\d{9}$/.test(ruc);
};

// Detecta empresa auto-generada por el backend al registrar usuario
const isEmpresaAutoGenerada = (empresa) => {
  if (!empresa) return true;
  const nombre = empresa.nombre || empresa.razon_social || '';
  return nombre.startsWith('Empresa de ') || isRucInvalido(empresa.ruc);
};

const EmpresaCheck = ({ children }) => {
  const { user } = useAuth();
  const { isOpen: isFormOpen, onOpen: openForm, onClose: closeForm } = useDisclosure();
  const [needsSetup, setNeedsSetup] = useState(false);

  useEffect(() => {
    if (user) {
      setNeedsSetup(!user.empresa || isEmpresaAutoGenerada(user.empresa_info || user.empresa));
    }
  }, [user]);

  if (!needsSetup) return children;

  const empresa = user?.empresa_info || user?.empresa;
  const hasAutoRuc = empresa && isRucInvalido(empresa.ruc);
  const hasAutoNombre = empresa && (empresa.nombre || '').startsWith('Empresa de ');

  return (
    <>
      <Modal isOpen={true} onClose={() => {}} closeOnOverlayClick={false} isCentered>
        <ModalOverlay backdropFilter="blur(4px)" />
        <ModalContent>
          <ModalHeader>Configura tu empresa</ModalHeader>
          <ModalBody pb={6}>
            <VStack spacing={4} align="stretch">
              {(hasAutoRuc || hasAutoNombre) && empresa ? (
                <Text color="neutral.600" fontSize="sm">
                  Tu cuenta tiene datos de empresa temporales. Actualízalos antes de emitir
                  cotizaciones, compras o ventas.
                </Text>
              ) : (
                <Text color="neutral.600" fontSize="sm">
                  Para usar el sistema necesitas registrar los datos de tu empresa.
                </Text>
              )}

              {hasAutoRuc && (
                <Badge colorScheme="orange" alignSelf="start">
                  RUC pendiente: {empresa?.ruc}
                </Badge>
              )}

              <Button colorScheme="primary" onClick={openForm}>
                {empresa ? 'Actualizar datos de empresa' : 'Crear empresa'}
              </Button>
            </VStack>
          </ModalBody>
        </ModalContent>
      </Modal>

      <EmpresaForm isOpen={isFormOpen} onClose={closeForm} />
    </>
  );
};

export default EmpresaCheck; 