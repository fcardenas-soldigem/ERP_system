import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { produccionService } from '../../services/produccion.service';
import RecetaWizard from './RecetaWizard';
import {
  Box,
  Heading,
  Text,
  Flex,
  SimpleGrid,
  Card,
  CardHeader,
  CardBody,
  Button,
  Stat,
  StatLabel,
  StatNumber,
  HStack,
  VStack,
  Badge,
  Input,
  InputGroup,
  InputLeftElement,
  Select,
  useColorModeValue,
  Spinner,
  Icon,
  IconButton,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  useDisclosure,
  Alert,
  AlertIcon
} from '@chakra-ui/react';
import { 
  SearchIcon, 
  AddIcon, 
  ChevronRightIcon,
  EditIcon,
  CopyIcon,
  DeleteIcon,
  ChevronDownIcon
} from '@chakra-ui/icons';
import { FiClipboard, FiPackage, FiClock, FiDollarSign } from 'react-icons/fi';

const RecetasList = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  
  const [showWizard, setShowWizard] = useState(false);
  const [recetaToEdit, setRecetaToEdit] = useState(null);
  const [busqueda, setBusqueda] = useState('');
  const [filtroEstado, setFiltroEstado] = useState('');
  const [recetaToDelete, setRecetaToDelete] = useState(null);
  const { isOpen: isDeleteOpen, onOpen: onDeleteOpen, onClose: onDeleteClose } = useDisclosure();

  // Query para recetas
  const { data: recetas = [], isLoading, error } = useQuery({
    queryKey: ['recetas'],
    queryFn: async () => {
      const response = await produccionService.getRecetas();
      // Axios devuelve { data: {...} }, y Django REST usa paginación { results: [...] }
      const data = response.data;
      return Array.isArray(data) ? data : data?.results || [];
    }
  });

  // Mutation para eliminar
  const deleteMutation = useMutation({
    mutationFn: (id) => produccionService.deleteReceta(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['recetas']);
      onDeleteClose();
      setRecetaToDelete(null);
    }
  });

  // Filtrar recetas
  const recetasFiltradas = recetas.filter(receta => {
    if (busqueda) {
      const search = busqueda.toLowerCase();
      if (!receta.nombre?.toLowerCase().includes(search) &&
          !receta.producto_terminado_nombre?.toLowerCase().includes(search)) {
        return false;
      }
    }
    if (filtroEstado === 'activa' && !receta.is_active) return false;
    if (filtroEstado === 'inactiva' && receta.is_active) return false;
    return true;
  });

  const handleCreate = () => {
    setRecetaToEdit(null);
    setShowWizard(true);
  };

  const handleEdit = (receta) => {
    setRecetaToEdit(receta);
    setShowWizard(true);
  };

  const handleDuplicate = async (receta) => {
    const duplicatedData = {
      ...receta,
      nombre: `${receta.nombre} (copia)`,
      is_active: false
    };
    delete duplicatedData.id;
    
    try {
      await produccionService.createReceta(duplicatedData);
      queryClient.invalidateQueries(['recetas']);
    } catch (error) {
      console.error('Error al duplicar receta:', error);
    }
  };

  const handleDeleteClick = (receta) => {
    setRecetaToDelete(receta);
    onDeleteOpen();
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-PE', {
      style: 'currency',
      currency: 'PEN'
    }).format(amount || 0);
  };

  if (isLoading) {
    return (
      <Box p={6}>
        <Flex justify="center" align="center" h="300px" direction="column">
          <Spinner size="xl" color="blue.500" thickness="4px" mb={4} />
          <Text color="gray.600">Cargando recetas...</Text>
        </Flex>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={6}>
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          No se pudieron cargar las recetas
        </Alert>
      </Box>
    );
  }

  return (
    <Box p={6}>
      {/* Header */}
      <Flex justify="space-between" align="center" mb={6} flexWrap="wrap" gap={4}>
        <Box>
          <Heading size="lg" bgGradient="linear(to-r, green.600, teal.600)" bgClip="text">
            Recetas de Producción (BOM)
          </Heading>
          <Text color="gray.600" mt={1}>
            Define las fórmulas y materiales para tus productos
          </Text>
        </Box>
        <Button
          leftIcon={<AddIcon />}
          colorScheme="green"
          onClick={handleCreate}
        >
          Nueva Receta
        </Button>
      </Flex>

      {/* Filtros */}
      <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} mb={6} borderRadius="xl">
        <CardBody>
          <HStack spacing={4}>
            <InputGroup flex={1}>
              <InputLeftElement pointerEvents="none">
                <SearchIcon color="gray.400" />
              </InputLeftElement>
              <Input
                placeholder="Buscar por nombre o producto..."
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
              />
            </InputGroup>
            <Select 
              w="200px"
              value={filtroEstado}
              onChange={(e) => setFiltroEstado(e.target.value)}
            >
              <option value="">Todos los estados</option>
              <option value="activa">🟢 Activas</option>
              <option value="inactiva">⚪ Inactivas</option>
            </Select>
          </HStack>
        </CardBody>
      </Card>

      {/* Lista de recetas */}
      {recetasFiltradas.length === 0 ? (
        <Card bg={cardBg} borderWidth="1px" borderColor={borderColor} borderRadius="xl">
          <CardBody>
            <VStack py={12} spacing={4}>
              <Icon as={FiClipboard} boxSize={12} color="gray.400" />
              <Text fontSize="lg" fontWeight="medium" color="gray.600">
                {busqueda || filtroEstado ? "No se encontraron recetas" : "No hay recetas creadas"}
              </Text>
              <Text color="gray.500" textAlign="center">
                {busqueda || filtroEstado 
                  ? "Intenta con otros filtros"
                  : "Crea tu primera receta para comenzar"
                }
              </Text>
              {!busqueda && !filtroEstado && (
                <Button leftIcon={<AddIcon />} colorScheme="green" onClick={handleCreate}>
                  Nueva Receta
                </Button>
              )}
            </VStack>
          </CardBody>
        </Card>
      ) : (
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
          {recetasFiltradas.map((receta) => (
            <Card 
              key={receta.id}
              bg={cardBg} 
              borderWidth="2px" 
              borderColor={receta.is_active ? 'green.200' : borderColor}
              borderRadius="xl"
              overflow="hidden"
              transition="all 0.3s"
              _hover={{ shadow: 'lg', transform: 'translateY(-4px)' }}
            >
              {/* Barra de color */}
              <Box h="4px" bgGradient={receta.is_active ? "linear(to-r, green.400, teal.400)" : "linear(to-r, gray.300, gray.400)"} />
              
              <CardHeader pb={2}>
                <Flex justify="space-between" align="start">
                  <Box flex={1} mr={2}>
                    <Text fontWeight="bold" fontSize="md" noOfLines={1}>
                      {receta.nombre}
                    </Text>
                    <Text fontSize="sm" color="gray.600" noOfLines={1}>
                      {receta.producto_terminado_nombre}
                    </Text>
                  </Box>
                  <Badge colorScheme={receta.is_active ? 'green' : 'gray'} fontSize="xs">
                    {receta.is_active ? '✓ Activa' : 'Inactiva'}
                  </Badge>
                </Flex>
              </CardHeader>

              <CardBody pt={0}>
                {/* Métricas */}
                <SimpleGrid columns={2} spacing={3} mb={4}>
                  <Stat size="sm" textAlign="center" p={2} bg="blue.50" borderRadius="lg">
                    <StatNumber fontSize="xl" color="blue.600">
                      {receta.cantidad_producida || 1}
                    </StatNumber>
                    <StatLabel fontSize="xs">und. produce</StatLabel>
                  </Stat>
                  <Stat size="sm" textAlign="center" p={2} bg="purple.50" borderRadius="lg">
                    <StatNumber fontSize="xl" color="purple.600">
                      {receta.detalles?.length || receta.total_materiales || 0}
                    </StatNumber>
                    <StatLabel fontSize="xs">materiales</StatLabel>
                  </Stat>
                </SimpleGrid>

                {/* Info adicional */}
                <VStack spacing={2} align="stretch" fontSize="sm">
                  {receta.tiempo_estimado > 0 && (
                    <Flex justify="space-between" color="gray.600">
                      <HStack><Icon as={FiClock} /><Text>Tiempo:</Text></HStack>
                      <Text fontWeight="medium">{(receta.tiempo_estimado / 60).toFixed(1)} hrs</Text>
                    </Flex>
                  )}
                  {(receta.costo_total || receta.costo_materiales) > 0 && (
                    <Flex justify="space-between" color="gray.600">
                      <HStack><Icon as={FiDollarSign} /><Text>Costo:</Text></HStack>
                      <Text fontWeight="medium" color="green.600">
                        {formatCurrency(receta.costo_total || receta.costo_materiales)}
                      </Text>
                    </Flex>
                  )}
                </VStack>

                {/* Acciones */}
                <Flex justify="space-between" align="center" mt={4} pt={4} borderTopWidth="1px">
                  <Button
                    size="sm"
                    variant="ghost"
                    colorScheme="blue"
                    rightIcon={<ChevronRightIcon />}
                    onClick={() => navigate(`/app/produccion/recetas/${receta.id}`)}
                  >
                    Ver detalle
                  </Button>
                  
                  <HStack spacing={1}>
                    <IconButton
                      size="sm"
                      variant="ghost"
                      icon={<EditIcon />}
                      onClick={() => handleEdit(receta)}
                      aria-label="Editar"
                      _hover={{ bg: 'blue.50', color: 'blue.600' }}
                    />
                    <IconButton
                      size="sm"
                      variant="ghost"
                      icon={<CopyIcon />}
                      onClick={() => handleDuplicate(receta)}
                      aria-label="Duplicar"
                      _hover={{ bg: 'purple.50', color: 'purple.600' }}
                    />
                    <IconButton
                      size="sm"
                      variant="ghost"
                      icon={<DeleteIcon />}
                      onClick={() => handleDeleteClick(receta)}
                      aria-label="Eliminar"
                      _hover={{ bg: 'red.50', color: 'red.600' }}
                    />
                  </HStack>
                </Flex>
              </CardBody>
            </Card>
          ))}
        </SimpleGrid>
      )}

      {/* Estadísticas */}
      <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4} mt={8}>
        <Stat textAlign="center" p={4} bg={cardBg} borderRadius="xl" borderWidth="1px" borderColor={borderColor}>
          <StatNumber color="blue.600">{recetas.length}</StatNumber>
          <StatLabel>Total recetas</StatLabel>
        </Stat>
        <Stat textAlign="center" p={4} bg={cardBg} borderRadius="xl" borderWidth="1px" borderColor={borderColor}>
          <StatNumber color="green.600">{recetas.filter(r => r.is_active).length}</StatNumber>
          <StatLabel>Activas</StatLabel>
        </Stat>
        <Stat textAlign="center" p={4} bg={cardBg} borderRadius="xl" borderWidth="1px" borderColor={borderColor}>
          <StatNumber color="purple.600">{new Set(recetas.map(r => r.producto_terminado)).size}</StatNumber>
          <StatLabel>Productos únicos</StatLabel>
        </Stat>
        <Stat textAlign="center" p={4} bg={cardBg} borderRadius="xl" borderWidth="1px" borderColor={borderColor}>
          <StatNumber color="orange.600">{recetas.reduce((sum, r) => sum + (r.detalles?.length || 0), 0)}</StatNumber>
          <StatLabel>Total materiales</StatLabel>
        </Stat>
      </SimpleGrid>

      {/* Wizard */}
      <RecetaWizard
        isOpen={showWizard}
        onClose={() => {
          setShowWizard(false);
          setRecetaToEdit(null);
        }}
        recetaToEdit={recetaToEdit}
      />

      {/* Modal de eliminación */}
      <Modal isOpen={isDeleteOpen} onClose={onDeleteClose} isCentered>
        <ModalOverlay />
        <ModalContent borderRadius="xl">
          <ModalHeader>Eliminar Receta</ModalHeader>
          <ModalCloseButton />
          <ModalBody textAlign="center" py={6}>
            <Icon as={DeleteIcon} boxSize={12} color="red.400" mb={4} />
            <Text color="gray.600" mb={2}>
              ¿Estás seguro de eliminar esta receta?
            </Text>
            <Text fontWeight="bold" fontSize="lg">
              "{recetaToDelete?.nombre}"
            </Text>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onDeleteClose}>
              Cancelar
            </Button>
            <Button
              colorScheme="red"
              onClick={() => deleteMutation.mutate(recetaToDelete?.id)}
              isLoading={deleteMutation.isLoading}
            >
              Eliminar
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default RecetasList;
