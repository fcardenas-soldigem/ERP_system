import React, { useEffect, useState } from 'react';
import { 
  Box, 
  Heading, 
  Button, 
  Table, 
  Thead, 
  Tbody, 
  Tr, 
  Th, 
  Td, 
  useToast, 
  Modal, 
  ModalOverlay, 
  ModalContent, 
  ModalHeader, 
  ModalFooter, 
  ModalBody, 
  ModalCloseButton, 
  FormControl, 
  FormLabel, 
  Input, 
  FormErrorMessage, 
  IconButton, 
  Flex, 
  Spacer,
  Select,
  VStack,
  HStack,
  Alert,
  AlertIcon,
  Spinner,
  Badge,
  Text
} from '@chakra-ui/react';
import { AddIcon, EditIcon, DeleteIcon, SearchIcon, AttachmentIcon } from '@chakra-ui/icons';
import { clientesService } from '../../services/clientes.service';
import useConsultaDocumentos from '../../hooks/useConsultaDocumentos';
import ImportarClientes from './ImportarClientes';

const Clientes = () => {
  const [clientes, setClientes] = useState([]);
  const [show, setShow] = useState(false);
  const [showImportar, setShowImportar] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterTerm, setFilterTerm] = useState('');
  const [errors, setErrors] = useState({});
  const [datosConsulta, setDatosConsulta] = useState(null);
  const [clienteActual, setClienteActual] = useState({
    id: null,
    nombre: '',
    documento: '',
    tipo_documento: 'dni',
    direccion: '',
    telefono: '',
    email: '',
    activo: true
  });

  const { 
    consultarDocumento, 
    validarDocumento, 
    loading: consultando, 
    error: errorConsulta,
    limpiarError
  } = useConsultaDocumentos();

  const toast = useToast();

  useEffect(() => {
    fetchClientes();
  }, [searchTerm, filterTerm]);

  const fetchClientes = async () => {
    try {
      const params = {};
      if (searchTerm) params.search = searchTerm;
      if (filterTerm) params.filter = filterTerm;
      
      const data = await clientesService.getClientes(params);
      setClientes(data);
    } catch (error) {
      console.error('Error al obtener clientes:', error);
      toast({
        title: 'Error al obtener los clientes',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const handleClose = () => {
    setShow(false);
    setClienteActual({
      id: null,
      nombre: '',
      documento: '',
      tipo_documento: 'dni',
      direccion: '',
      telefono: '',
      email: '',
      activo: true
    });
    setErrors({});
    setDatosConsulta(null);
    limpiarError();
  };

  const handleShow = () => setShow(true);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setClienteActual((prev) => ({
      ...prev,
      [name]: value
    }));

    // Limpiar datos de consulta si se cambia el documento o tipo
    if (name === 'documento' || name === 'tipo_documento') {
      setDatosConsulta(null);
      limpiarError();
    }
  };

  const handleConsultarDocumento = async () => {
    const { documento, tipo_documento } = clienteActual;
    
    if (!validarDocumento(documento, tipo_documento)) {
      toast({
        title: 'Documento inválido',
        description: `El ${tipo_documento.toUpperCase()} debe tener ${tipo_documento === 'dni' ? '8' : '11'} dígitos`,
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    const datos = await consultarDocumento(documento, tipo_documento);
    
    if (datos) {
      setDatosConsulta(datos);
      
      // Autocompletar campos según el tipo de documento
      if (tipo_documento === 'dni') {
        setClienteActual(prev => ({
          ...prev,
          nombre: datos.nombre_completo || `${datos.nombres} ${datos.apellido_paterno} ${datos.apellido_materno}`.trim()
        }));
      } else if (tipo_documento === 'ruc') {
        setClienteActual(prev => ({
          ...prev,
          nombre: datos.razon_social || datos.nombre_comercial || '',
          direccion: datos.direccion || prev.direccion
        }));
      }

      toast({
        title: '✅ Consulta exitosa',
        description: `Datos obtenidos de ${tipo_documento === 'dni' ? 'RENIEC' : 'SUNAT'}`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
  };

  const handleFilterChange = (e) => {
    setFilterTerm(e.target.value);
  };

  const validate = () => {
    const newErrors = {};
    if (!clienteActual.nombre) newErrors.nombre = 'El nombre es obligatorio';
    if (!clienteActual.documento) newErrors.documento = 'El documento es obligatorio';
    else if (!validarDocumento(clienteActual.documento, clienteActual.tipo_documento)) {
      newErrors.documento = `Debe tener ${clienteActual.tipo_documento === 'dni' ? '8' : '11'} dígitos`;
    }
    // Teléfono opcional, pero si se proporciona debe ser válido
    if (clienteActual.telefono && !/^\d{9}$/.test(clienteActual.telefono)) {
      newErrors.telefono = 'Debe tener 9 dígitos';
    }
    // Email opcional, pero si se proporciona debe ser válido
    if (clienteActual.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(clienteActual.email)) {
      newErrors.email = 'Email inválido';
    }
    return newErrors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const validationErrors = validate();
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) return;
    
    try {
      if (clienteActual.id) {
        await clientesService.updateCliente(clienteActual.id, clienteActual);
        toast({
          title: 'Cliente actualizado exitosamente',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
      } else {
        await clientesService.createCliente(clienteActual);
        toast({
          title: 'Cliente creado exitosamente',
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
      }
      fetchClientes();
      handleClose();
    } catch (error) {
      toast({
        title: 'Error al crear/actualizar el cliente',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const handleEdit = (cliente) => {
    setClienteActual(cliente);
    setDatosConsulta(null);
    handleShow();
  };

  const handleDelete = async (id) => {
    try {
      await clientesService.deleteCliente(id);
      toast({
        title: 'Cliente eliminado exitosamente',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      fetchClientes();
    } catch (error) {
      console.error('Error al eliminar cliente:', error);
      toast({
        title: 'Error al eliminar el cliente',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const handleImportarSuccess = () => {
    fetchClientes(); // Actualizar la lista de clientes
    setShowImportar(false);
  };

  return (
    <Box maxW="1200px" mx="auto" mt={8}>
      <Flex mb={4} align="center">
        <Heading size="lg" color="teal.600">
          💼 Gestión de Clientes
        </Heading>
        <Spacer />
        <HStack spacing={2}>
          <Button 
            leftIcon={<AttachmentIcon />} 
            colorScheme="blue" 
            variant="outline"
            onClick={() => setShowImportar(true)}
          >
            Importar Clientes
          </Button>
          <Button leftIcon={<AddIcon />} colorScheme="teal" onClick={handleShow}>
            Agregar Cliente
          </Button>
        </HStack>
      </Flex>

      {/* Filtros de búsqueda */}
      <HStack mb={4} spacing={4}>
        <Input
          placeholder="Buscar por nombre, documento o email..."
          value={searchTerm}
          onChange={handleSearchChange}
          width="300px"
        />
        <Select
          placeholder="Filtrar por tipo"
          value={filterTerm}
          onChange={handleFilterChange}
          width="200px"
        >
          <option value="dni">Solo DNI</option>
          <option value="ruc">Solo RUC</option>
          <option value="activo">Solo Activos</option>
          <option value="inactivo">Solo Inactivos</option>
        </Select>
      </HStack>

      <Table variant="simple" size="md" mb={8} bg="white" borderRadius="md" boxShadow="sm">
        <Thead bg="gray.50">
          <Tr>
            <Th>ID</Th>
            <Th>Nombre</Th>
            <Th>Documento</Th>
            <Th>Tipo</Th>
            <Th>Dirección</Th>
            <Th>Teléfono</Th>
            <Th>Email</Th>
            <Th>Estado</Th>
            <Th>Acciones</Th>
          </Tr>
        </Thead>
        <Tbody>
          {clientes.map((cliente) => (
            <Tr key={cliente.id} _hover={{ bg: "gray.50" }}>
              <Td>{cliente.id}</Td>
              <Td fontWeight="medium">{cliente.nombre}</Td>
              <Td>{cliente.documento}</Td>
              <Td>
                <Badge
                  colorScheme={cliente.tipo_documento === 'dni' ? 'blue' : 'purple'}
                  variant="solid"
                >
                  {cliente.tipo_documento?.toUpperCase()}
                </Badge>
              </Td>
              <Td>{cliente.direccion}</Td>
              <Td>{cliente.telefono}</Td>
              <Td>{cliente.email}</Td>
              <Td>
                <Badge
                  colorScheme={cliente.activo ? 'green' : 'red'}
                  variant="solid"
                >
                  {cliente.activo ? 'Activo' : 'Inactivo'}
                </Badge>
              </Td>
              <Td>
                <HStack spacing={1}>
                  <IconButton 
                    icon={<EditIcon />} 
                    size="sm" 
                    colorScheme="blue"
                    onClick={() => handleEdit(cliente)} 
                    aria-label="Editar" 
                  />
                  <IconButton 
                    icon={<DeleteIcon />} 
                    size="sm" 
                    colorScheme="red" 
                    onClick={() => handleDelete(cliente.id)} 
                    aria-label="Eliminar" 
                  />
                </HStack>
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>

      {/* Modal de formulario con consulta integrada */}
      <Modal isOpen={show} onClose={handleClose} isCentered size="lg">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>
            {clienteActual.id ? '✏️ Editar Cliente' : '➕ Agregar Cliente'}
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <form id="cliente-form" onSubmit={handleSubmit}>
              <VStack spacing={4} align="stretch">
                
                {/* Tipo de Documento */}
                <FormControl>
                  <FormLabel>Tipo de Documento</FormLabel>
                  <Select
                    name="tipo_documento"
                    value={clienteActual.tipo_documento}
                    onChange={handleInputChange}
                  >
                    <option value="dni">DNI (Personas naturales)</option>
                    <option value="ruc">RUC (Empresas)</option>
                  </Select>
                </FormControl>

                {/* Documento con consulta automática */}
                <FormControl isInvalid={!!errors.documento}>
                  <FormLabel>
                    {clienteActual.tipo_documento === 'dni' ? 'DNI' : 'RUC'}
                  </FormLabel>
                  <HStack>
                    <Input 
                      name="documento" 
                      value={clienteActual.documento} 
                      onChange={handleInputChange}
                      placeholder={clienteActual.tipo_documento === 'dni' ? 'Ingrese DNI (8 dígitos)' : 'Ingrese RUC (11 dígitos)'}
                      maxLength={clienteActual.tipo_documento === 'dni' ? 8 : 11}
                    />
                    <Button
                      leftIcon={consultando ? <Spinner size="sm" /> : <SearchIcon />}
                      colorScheme="blue"
                      onClick={handleConsultarDocumento}
                      disabled={
                        consultando || 
                        !validarDocumento(clienteActual.documento, clienteActual.tipo_documento)
                      }
                      minWidth="120px"
                    >
                      {consultando ? 'Consultando...' : 'Consultar'}
                    </Button>
                  </HStack>
                  <FormErrorMessage>{errors.documento}</FormErrorMessage>
                </FormControl>

                {/* Error de consulta */}
                {errorConsulta && (
                  <Alert status="error" borderRadius="md">
                    <AlertIcon />
                    {errorConsulta}
                  </Alert>
                )}

                {/* Datos consultados exitosamente */}
                {datosConsulta && (
                  <Alert status="success" borderRadius="md">
                    <AlertIcon />
                    <Box>
                      <Text fontWeight="bold" mb={1}>
                        ✅ Datos obtenidos de {clienteActual.tipo_documento === 'dni' ? 'RENIEC' : 'SUNAT'}
                      </Text>
                      {clienteActual.tipo_documento === 'dni' ? (
                        <VStack align="start" spacing={1} fontSize="sm">
                          <Text><strong>Nombres:</strong> {datosConsulta.nombres}</Text>
                          <Text><strong>Apellidos:</strong> {datosConsulta.apellido_paterno} {datosConsulta.apellido_materno}</Text>
                        </VStack>
                      ) : (
                        <VStack align="start" spacing={1} fontSize="sm">
                          <Text><strong>Razón Social:</strong> {datosConsulta.razon_social}</Text>
                          <Text><strong>Estado:</strong> {datosConsulta.estado}</Text>
                          <Text><strong>Condición:</strong> {datosConsulta.condicion}</Text>
                        </VStack>
                      )}
                    </Box>
                  </Alert>
                )}

                {/* Nombre/Razón Social */}
                <FormControl isInvalid={!!errors.nombre}>
                  <FormLabel>
                    {clienteActual.tipo_documento === 'dni' ? 'Nombre Completo' : 'Razón Social'}
                  </FormLabel>
                  <Input 
                    name="nombre" 
                    value={clienteActual.nombre} 
                    onChange={handleInputChange}
                    placeholder={clienteActual.tipo_documento === 'dni' ? 'Nombre completo del cliente' : 'Razón social de la empresa'}
                  />
                  <FormErrorMessage>{errors.nombre}</FormErrorMessage>
                </FormControl>

                {/* Dirección */}
                <FormControl>
                  <FormLabel>Dirección <Text as="span" fontSize="sm" color="gray.500">(opcional)</Text></FormLabel>
                  <Input 
                    name="direccion" 
                    value={clienteActual.direccion || ''} 
                    onChange={handleInputChange}
                    placeholder="Dirección completa (opcional)"
                  />
                </FormControl>

                {/* Teléfono */}
                <FormControl isInvalid={!!errors.telefono}>
                  <FormLabel>Teléfono <Text as="span" fontSize="sm" color="gray.500">(opcional)</Text></FormLabel>
                  <Input 
                    name="telefono" 
                    value={clienteActual.telefono || ''} 
                    onChange={handleInputChange}
                    placeholder="Número de teléfono (9 dígitos) - opcional"
                    maxLength={9}
                  />
                  <FormErrorMessage>{errors.telefono}</FormErrorMessage>
                </FormControl>

                {/* Email */}
                <FormControl isInvalid={!!errors.email}>
                  <FormLabel>Email <Text as="span" fontSize="sm" color="gray.500">(opcional)</Text></FormLabel>
                  <Input 
                    name="email" 
                    type="email"
                    value={clienteActual.email || ''} 
                    onChange={handleInputChange}
                    placeholder="correo@ejemplo.com (opcional)"
                  />
                  <FormErrorMessage>{errors.email}</FormErrorMessage>
                </FormControl>

              </VStack>
            </form>
          </ModalBody>
          <ModalFooter>
            <Button colorScheme="teal" mr={3} type="submit" form="cliente-form">
              {clienteActual.id ? 'Actualizar' : 'Agregar'}
            </Button>
            <Button onClick={handleClose}>Cancelar</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Modal de Importar Clientes */}
      <ImportarClientes
        isOpen={showImportar}
        onClose={() => setShowImportar(false)}
        onSuccess={handleImportarSuccess}
      />
    </Box>
  );
};

export default Clientes; 