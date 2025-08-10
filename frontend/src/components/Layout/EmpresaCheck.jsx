import React, { useState, useEffect } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  Text,
  Button,
  useDisclosure,
} from '@chakra-ui/react';
import { useAuth } from '../context/AuthContext';
import EmpresaForm from '../Empresa/EmpresaForm';

const EmpresaCheck = ({ children }) => {
  const { user } = useAuth();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [showEmpresaForm, setShowEmpresaForm] = useState(false);

  useEffect(() => {
    // Solo mostrar el formulario si el usuario está autenticado pero no tiene empresa
    if (user && !user.empresa) {
      setShowEmpresaForm(true);
    } else {
      setShowEmpresaForm(false);
    }
  }, [user]);

  // Si el usuario tiene empresa, mostrar el contenido normal
  if (user?.empresa) {
    return children;
  }

  // Si no tiene empresa, mostrar el modal
  return (
    <>
      <Modal isOpen={true} onClose={() => {}} closeOnOverlayClick={false}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Configuración Necesaria</ModalHeader>
          <ModalBody pb={6}>
            <Text mb={4}>
              Para comenzar a usar el sistema, necesitas crear una empresa.
            </Text>
            <Button colorScheme="blue" onClick={onOpen}>
              Crear Empresa
            </Button>
          </ModalBody>
        </ModalContent>
      </Modal>

      <EmpresaForm isOpen={showEmpresaForm} onClose={() => setShowEmpresaForm(false)} />
    </>
  );
};

export default EmpresaCheck; 