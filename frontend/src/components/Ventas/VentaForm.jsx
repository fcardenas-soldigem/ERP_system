import React, { useState, useEffect } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  FormControl,
  FormLabel,
  Input,
  Select,
  useToast,
  VStack,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  NumberInput,
  NumberInputField,
  Switch,
  Text,
  Box,
  IconButton,
  FormHelperText,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  List,
  ListItem,
  Divider,
  HStack,
  Spinner,
  Alert,
  AlertIcon
} from '@chakra-ui/react';
import { DeleteIcon, SearchIcon } from '@chakra-ui/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ventasService } from '../../services/ventas.service';
import { clientesService } from '../../services/clientes.service';
import { TIPOS_VENTA, METODOS_PAGO, TIPOS_VENTA_DISPLAY, METODOS_PAGO_DISPLAY } from './constants';
import { addDays } from 'date-fns';
import useConsultaDocumentos from '../../hooks/useConsultaDocumentos';
import { getSimboloMoneda } from '../../utils/currency';

const VentaForm = ({ isOpen, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    cliente: '',
    fecha_emision: new Date().toISOString().split('T')[0],
    fecha_vencimiento: null,
    estado: 'pagado',
    tipo_venta: 'contado',
    metodo_pago: 'efectivo',
    igv_incluido: false,
    moneda: 'PEN',
    referencia: '',
    comprobante: null,
    detalles: [{
      producto: '',
      cantidad: 1,
      precio_unitario: 0
    }]
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isAlertOpen, setIsAlertOpen] = useState(false);
  const [productosStockBajo, setProductosStockBajo] = useState([]);
  const [clienteSearch, setClienteSearch] = useState('');
  const [showClienteDropdown, setShowClienteDropdown] = useState(false);
  const [filteredClientes, setFilteredClientes] = useState([]);
  const [selectedClienteIndex, setSelectedClienteIndex] = useState(-1);
  const [documentoSearch, setDocumentoSearch] = useState('');
  const [tipoDocumento, setTipoDocumento] = useState('dni');
  const [consultandoDocumento, setConsultandoDocumento] = useState(false);
  const [modoConsultaDocumento, setModoConsultaDocumento] = useState(false);
  const cancelRef = React.useRef();
  const clienteInputRef = React.useRef();
  const toast = useToast();
  const queryClient = useQueryClient();

  const { 
    consultarDocumento, 
    validarDocumento, 
    loading: consultando, 
    error: errorConsulta,
    limpiarError
  } = useConsultaDocumentos();

  const { data: clientes = [] } = useQuery({
    queryKey: ['clientes'],
    queryFn: ventasService.getClientes
  });

  const { data: productos = [] } = useQuery({
    queryKey: ['productos'],
    queryFn: ventasService.getProductos
  });

  // Efectos para filtrar clientes
  useEffect(() => {
    if (clienteSearch.length > 0) {
      const filtered = clientes.filter(cliente =>
        cliente.nombre.toLowerCase().includes(clienteSearch.toLowerCase()) ||
        cliente.documento.includes(clienteSearch)
      );
      setFilteredClientes(filtered);
      setShowClienteDropdown(true);
    } else {
      setFilteredClientes([]);
      setShowClienteDropdown(false);
    }
  }, [clienteSearch, clientes]);

  // Inicializar clienteSearch cuando se selecciona un cliente externamente
  useEffect(() => {
    if (formData.cliente && clientes.length > 0 && !clienteSearch) {
      const cliente = clientes.find(c => c.id === parseInt(formData.cliente));
      if (cliente) {
        setClienteSearch(cliente.nombre);
      }
    }
  }, [formData.cliente, clientes, clienteSearch]);

  // Función para manejar la selección de cliente
  const handleClienteSelect = (cliente) => {
    setFormData(prev => ({
      ...prev,
      cliente: cliente.id
    }));
    setClienteSearch(cliente.nombre);
    setShowClienteDropdown(false);
  };

  // Función para manejar el cambio en el input de búsqueda de cliente
  const handleClienteSearchChange = (e) => {
    const value = e.target.value;
    setClienteSearch(value);
    setSelectedClienteIndex(-1); // Reset del índice seleccionado
    
    // Si se borra el campo, limpiar también el cliente seleccionado
    if (value === '') {
      setFormData(prev => ({
        ...prev,
        cliente: ''
      }));
    }
  };

  // Función para manejar navegación con teclado
  const handleClienteKeyDown = (e) => {
    if (!showClienteDropdown || filteredClientes.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedClienteIndex(prev => 
          prev < filteredClientes.length - 1 ? prev + 1 : 0
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedClienteIndex(prev => 
          prev > 0 ? prev - 1 : filteredClientes.length - 1
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedClienteIndex >= 0) {
          handleClienteSelect(filteredClientes[selectedClienteIndex]);
        } else if (modoConsultaDocumento && validarDocumento(documentoSearch, tipoDocumento)) {
          handleBuscarOCrearCliente();
        }
        break;
      case 'Escape':
        setShowClienteDropdown(false);
        setSelectedClienteIndex(-1);
        break;
    }
  };

  // Función principal para buscar cliente existente o crear nuevo
  const handleBuscarOCrearCliente = async () => {
    if (!validarDocumento(documentoSearch, tipoDocumento)) {
      toast({
        title: 'Documento inválido',
        description: `El ${tipoDocumento.toUpperCase()} debe tener ${tipoDocumento === 'dni' ? '8' : '11'} dígitos`,
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setConsultandoDocumento(true);
    
    try {
      // 1. Buscar si el cliente ya existe
      const clienteExistente = clientes.find(c => c.documento === documentoSearch);
      
      if (clienteExistente) {
        // Cliente ya existe, seleccionarlo
        handleClienteSelect(clienteExistente);
        setModoConsultaDocumento(false);
        setDocumentoSearch('');
        toast({
          title: '👤 Cliente encontrado',
          description: `Cliente "${clienteExistente.nombre}" cargado correctamente`,
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
        return;
      }

      // 2. Cliente no existe, consultar datos externos y crear
      const datosConsulta = await consultarDocumento(documentoSearch, tipoDocumento);
      
      if (!datosConsulta) {
        toast({
          title: 'No se pudieron obtener los datos',
          description: 'Verifique el número de documento e intente nuevamente',
          status: 'error',
          duration: 3000,
          isClosable: true,
        });
        return;
      }

      // 3. Crear cliente automáticamente con los datos consultados
      let nombreCompleto = '';
      
      if (tipoDocumento === 'dni') {
        nombreCompleto = datosConsulta.nombre_completo || 
          `${datosConsulta.nombres} ${datosConsulta.apellido_paterno} ${datosConsulta.apellido_materno}`.trim();
      } else if (tipoDocumento === 'ruc') {
        nombreCompleto = datosConsulta.razon_social || datosConsulta.nombre_comercial || '';
      }

      if (!nombreCompleto) {
        toast({
          title: 'Datos incompletos',
          description: 'No se pudo obtener el nombre desde la consulta externa',
          status: 'error',
          duration: 3000,
          isClosable: true,
        });
        return;
      }

      const nuevoClienteData = {
        nombre: nombreCompleto,
        documento: documentoSearch,
        tipo_documento: tipoDocumento,
        direccion: tipoDocumento === 'ruc' ? (datosConsulta.direccion || '') : '',
        telefono: '',
        email: ''
      };

      // Crear el cliente
      const nuevoCliente = await clientesService.createCliente(nuevoClienteData);
      
      // Actualizar la lista de clientes en cache
      queryClient.invalidateQueries(['clientes']);
      
      // Seleccionar el nuevo cliente
      handleClienteSelect(nuevoCliente);
      setModoConsultaDocumento(false);
      setDocumentoSearch('');
      
      toast({
        title: '✅ Cliente creado y seleccionado',
        description: `Cliente "${nombreCompleto}" registrado automáticamente`,
        status: 'success',
        duration: 4000,
        isClosable: true,
      });

    } catch (error) {
      console.error('Error al buscar/crear cliente:', error);
      toast({
        title: 'Error al procesar cliente',
        description: 'Hubo un problema al buscar o crear el cliente',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setConsultandoDocumento(false);
    }
  };

  // Función para cambiar entre modo búsqueda por nombre y por documento
  const toggleModoConsultaDocumento = () => {
    setModoConsultaDocumento(!modoConsultaDocumento);
    setClienteSearch('');
    setDocumentoSearch('');
    setShowClienteDropdown(false);
    setFormData(prev => ({ ...prev, cliente: '' }));
    limpiarError();
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleDetalleChange = (index, field, value) => {
    const newDetalles = [...formData.detalles];
    newDetalles[index] = {
      ...newDetalles[index],
      [field]: value
    };

    if (field === 'producto') {
      const producto = productos.find(p => p.id === parseInt(value));
      if (producto) {
        newDetalles[index].precio_unitario = producto.precio_venta || 0;
      }
    }

    setFormData(prev => ({
      ...prev,
      detalles: newDetalles
    }));
  };

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const maxSize = 5 * 1024 * 1024; // 5MB
    const allowedTypes = ['image/jpeg', 'image/png', 'application/pdf'];

    if (file.size > maxSize) {
      toast({
        title: 'Error',
        description: 'El archivo es demasiado grande. Máximo 5MB.',
        status: 'error',
        duration: 3000
      });
      event.target.value = '';
      return;
    }

    if (!allowedTypes.includes(file.type)) {
      toast({
        title: 'Error',
        description: 'Tipo de archivo no permitido. Use PDF, JPG o PNG.',
        status: 'error',
        duration: 3000
      });
      event.target.value = '';
      return;
    }

    setFormData(prev => ({
      ...prev,
      comprobante: file
    }));
  };

  const agregarProducto = () => {
    setFormData(prev => ({
      ...prev,
      detalles: [
        ...prev.detalles,
        { producto: '', cantidad: 1, precio_unitario: 0 }
      ]
    }));
  };

  const eliminarProducto = (index) => {
    if (formData.detalles.length > 1) {
      setFormData(prev => ({
        ...prev,
        detalles: prev.detalles.filter((_, i) => i !== index)
      }));
    }
  };

  const calcularSubtotal = () => {
    return formData.detalles.reduce((acc, detalle) => 
      acc + (detalle.cantidad * detalle.precio_unitario), 0
    );
  };

  const calcularIGV = () => {
    const subtotal = calcularSubtotal();
    return formData.igv_incluido ? 
      subtotal - (subtotal / 1.18) : 
      subtotal * 0.18;
  };

  const calcularTotal = () => {
    const subtotal = calcularSubtotal();
    return formData.igv_incluido ? 
      subtotal : 
      subtotal * 1.18;
  };

  const limpiarFormulario = () => {
    setFormData({
      cliente: '',
      fecha_emision: new Date().toISOString().split('T')[0],
      estado: 'pagado',
      tipo_venta: 'contado',
      metodo_pago: 'efectivo',
      igv_incluido: false,
      moneda: 'PEN',
      referencia: '',
      comprobante: null,
      detalles: [{
        producto: '',
        cantidad: 1,
        precio_unitario: 0
      }]
    });
    // Limpiar estados de búsqueda de cliente
    setClienteSearch('');
    setShowClienteDropdown(false);
    setFilteredClientes([]);
    setSelectedClienteIndex(-1);
    setDocumentoSearch('');
    setTipoDocumento('dni');
    setModoConsultaDocumento(false);
    setConsultandoDocumento(false);
    limpiarError();
    
    // Limpiar el input de archivo
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) fileInput.value = '';
  };

  const crearVentaMutation = useMutation({
    mutationFn: (data) => ventasService.crearVenta(data),
    onSuccess: () => {
      queryClient.invalidateQueries(['ventas']);
      toast({
        title: 'Éxito',
        description: 'Venta creada exitosamente',
        status: 'success',
        duration: 2000
      });
      limpiarFormulario();
      if (onSuccess) onSuccess();
      onClose();
    },
    onError: (error) => {
      console.error('Error al crear venta:', error);
      toast({
        title: 'Error',
        description: error.message || 'Error al crear la venta',
        status: 'error',
        duration: 3000
      });
    }
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validar cliente
    if (!formData.cliente) {
      toast({
        title: 'Error',
        description: 'Debe seleccionar un cliente',
        status: 'error',
        duration: 2000
      });
      return;
    }

    // Validar detalles
    if (!formData.detalles.length || formData.detalles.some(detalle => 
      !detalle.producto || !detalle.cantidad || detalle.cantidad <= 0 || !detalle.precio_unitario || detalle.precio_unitario <= 0
    )) {
      toast({
        title: 'Error',
        description: 'Por favor complete todos los detalles de productos con valores válidos',
        status: 'error',
        duration: 2000
      });
      return;
    }

    try {
      // Preparar los detalles
      const detalles = formData.detalles.map(detalle => ({
        producto: parseInt(detalle.producto),
        cantidad: parseFloat(detalle.cantidad),
        precio_unitario: parseFloat(detalle.precio_unitario)
      }));

      // Crear FormData
      const ventaData = new FormData();
      ventaData.append('cliente', formData.cliente);
      ventaData.append('fecha_emision', formData.fecha_emision);
      ventaData.append('estado', formData.estado);
      ventaData.append('tipo_venta', formData.tipo_venta);
      ventaData.append('metodo_pago', formData.metodo_pago);
      ventaData.append('igv_incluido', String(formData.igv_incluido));
      ventaData.append('moneda', formData.moneda || 'PEN');
      ventaData.append('referencia', formData.referencia || '');
      ventaData.append('detalles', JSON.stringify(detalles));

      // Agregar fecha de vencimiento si es venta a crédito
      if (formData.tipo_venta !== 'contado' && formData.fecha_vencimiento) {
        ventaData.append('fecha_vencimiento', formData.fecha_vencimiento);
      }

      // Agregar comprobante si existe
      if (formData.comprobante) {
        ventaData.append('comprobante', formData.comprobante);
      }

      console.log('Enviando venta:', {
        cliente: formData.cliente,
        fecha_emision: formData.fecha_emision,
        estado: formData.estado,
        tipo_venta: formData.tipo_venta,
        metodo_pago: formData.metodo_pago,
        igv_incluido: formData.igv_incluido,
        referencia: formData.referencia,
        detalles: detalles
      });

      setIsSubmitting(true);
      const response = await crearVentaMutation.mutateAsync(ventaData);
      
      // Verificar si hay productos con stock bajo
      if (response.productos_stock_bajo && response.productos_stock_bajo.length > 0) {
        setProductosStockBajo(response.productos_stock_bajo);
        setIsAlertOpen(true);
      }
    } catch (error) {
      console.error('Error en handleSubmit:', error);
      toast({
        title: 'Error',
        description: error.message || 'Error al crear la venta',
        status: 'error',
        duration: 3000
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTipoVentaChange = (e) => {
    const { value } = e.target;
    let fecha_vencimiento = null;

    // Establecer fecha de vencimiento según el tipo de venta
    if (value === TIPOS_VENTA.CREDITO_30) {
      fecha_vencimiento = addDays(new Date(formData.fecha_emision), 30).toISOString().split('T')[0];
    } else if (value === TIPOS_VENTA.CREDITO_60) {
      fecha_vencimiento = addDays(new Date(formData.fecha_emision), 60).toISOString().split('T')[0];
    }

    setFormData(prev => ({
      ...prev,
      tipo_venta: value,
      fecha_vencimiento
    }));
  };

  return (
    <>
      <Modal isOpen={isOpen} onClose={onClose} size="xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Nueva Venta</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Cliente</FormLabel>
                
                {/* Botón para cambiar entre modos */}
                <HStack mb={2}>
                  <Button 
                    size="sm" 
                    variant={!modoConsultaDocumento ? "solid" : "outline"}
                    colorScheme="blue"
                    onClick={() => modoConsultaDocumento && toggleModoConsultaDocumento()}
                    disabled={!modoConsultaDocumento}
                  >
                    📝 Buscar por nombre
                  </Button>
                  <Button 
                    size="sm" 
                    variant={modoConsultaDocumento ? "solid" : "outline"}
                    colorScheme="green"
                    onClick={() => !modoConsultaDocumento && toggleModoConsultaDocumento()}
                    disabled={modoConsultaDocumento}
                  >
                    🆔 Buscar/Crear por DNI/RUC
                  </Button>
                </HStack>

                {!modoConsultaDocumento ? (
                  // Modo búsqueda por nombre (original)
                  <Box position="relative">
                    <Input
                      ref={clienteInputRef}
                      placeholder="Buscar cliente por nombre o documento..."
                      value={clienteSearch}
                      onChange={handleClienteSearchChange}
                      onKeyDown={handleClienteKeyDown}
                      onFocus={() => {
                        if (filteredClientes.length > 0) {
                          setShowClienteDropdown(true);
                        }
                      }}
                      onBlur={() => {
                        setTimeout(() => {
                          setShowClienteDropdown(false);
                          setSelectedClienteIndex(-1);
                        }, 200);
                      }}
                      autoComplete="off"
                    />
                    {showClienteDropdown && filteredClientes.length > 0 && (
                      <Box
                        position="absolute"
                        top="100%"
                        left="0"
                        right="0"
                        mt={1}
                        bg="white"
                        border="1px solid"
                        borderColor="gray.200"
                        borderRadius="md"
                        boxShadow="lg"
                        zIndex={1000}
                        maxH="200px"
                        overflowY="auto"
                      >
                        <List spacing={0}>
                          {filteredClientes.slice(0, 10).map((cliente, index) => (
                            <ListItem
                              key={cliente.id}
                              p={3}
                              cursor="pointer"
                              bg={selectedClienteIndex === index ? 'blue.50' : 'white'}
                              _hover={{ bg: selectedClienteIndex === index ? 'blue.100' : 'gray.50' }}
                              borderBottom={index < Math.min(filteredClientes.length, 10) - 1 ? '1px solid' : 'none'}
                              borderColor="gray.100"
                              onClick={() => handleClienteSelect(cliente)}
                            >
                              <Text fontSize="sm" fontWeight="medium">
                                {cliente.nombre}
                              </Text>
                              <Text fontSize="xs" color="gray.600">
                                {cliente.documento} • {cliente.email || 'Sin email'}
                              </Text>
                            </ListItem>
                          ))}
                        </List>
                      </Box>
                    )}
                  </Box>
                ) : (
                  // Modo consulta por documento
                  <VStack spacing={3} align="stretch">
                    <HStack>
                      <Select
                        value={tipoDocumento}
                        onChange={(e) => setTipoDocumento(e.target.value)}
                        width="120px"
                      >
                        <option value="dni">DNI</option>
                        <option value="ruc">RUC</option>
                      </Select>
                      <Input
                        placeholder={`Ingrese ${tipoDocumento.toUpperCase()} ${tipoDocumento === 'dni' ? '(8 dígitos)' : '(11 dígitos)'}`}
                        value={documentoSearch}
                        onChange={(e) => setDocumentoSearch(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && validarDocumento(documentoSearch, tipoDocumento)) {
                            handleBuscarOCrearCliente();
                          }
                        }}
                        maxLength={tipoDocumento === 'dni' ? 8 : 11}
                      />
                      <Button
                        leftIcon={consultandoDocumento ? <Spinner size="sm" /> : <SearchIcon />}
                        colorScheme="green"
                        onClick={handleBuscarOCrearCliente}
                        disabled={consultandoDocumento || !validarDocumento(documentoSearch, tipoDocumento)}
                        minWidth="140px"
                      >
                        {consultandoDocumento ? 'Buscando...' : 'Buscar/Crear'}
                      </Button>
                    </HStack>
                    
                    {errorConsulta && (
                      <Alert status="error" borderRadius="md">
                        <AlertIcon />
                        {errorConsulta}
                      </Alert>
                    )}
                  </VStack>
                )}

                <FormHelperText>
                  {formData.cliente ? 
                    `✅ Cliente seleccionado: ${clientes.find(c => c.id === parseInt(formData.cliente))?.nombre || 'Desconocido'}` :
                    modoConsultaDocumento ? 
                      'Ingrese DNI/RUC para buscar cliente existente o crear uno nuevo automáticamente' :
                      'Escriba para buscar cliente por nombre o documento'
                  }
                </FormHelperText>
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Fecha de Emisión</FormLabel>
                <Input
                  type="date"
                  name="fecha_emision"
                  value={formData.fecha_emision}
                  onChange={handleChange}
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Tipo de Venta</FormLabel>
                <Select
                  name="tipo_venta"
                  value={formData.tipo_venta}
                  onChange={handleTipoVentaChange}
                >
                  {Object.entries(TIPOS_VENTA_DISPLAY).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </Select>
              </FormControl>

              {formData.tipo_venta !== TIPOS_VENTA.CONTADO && (
                <FormControl isRequired>
                  <FormLabel>Fecha de Vencimiento</FormLabel>
                  <Input
                    type="date"
                    name="fecha_vencimiento"
                    value={formData.fecha_vencimiento}
                    onChange={handleChange}
                    isReadOnly
                  />
                </FormControl>
              )}

              <FormControl isRequired>
                <FormLabel>Método de Pago</FormLabel>
                <Select
                  name="metodo_pago"
                  value={formData.metodo_pago}
                  onChange={handleChange}
                >
                  {Object.entries(METODOS_PAGO_DISPLAY).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel>IGV Incluido</FormLabel>
                <Switch
                  name="igv_incluido"
                  isChecked={formData.igv_incluido}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    igv_incluido: e.target.checked
                  }))}
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Moneda</FormLabel>
                <Select
                  name="moneda"
                  value={formData.moneda || 'PEN'}
                  onChange={handleChange}
                >
                  <option value="PEN">Sol Peruano (S/)</option>
                  <option value="USD">Dólar Americano ($)</option>
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel>Referencia</FormLabel>
                <Input
                  name="referencia"
                  value={formData.referencia}
                  onChange={handleChange}
                  placeholder="Referencia de la venta"
                />
              </FormControl>

              <FormControl>
                <FormLabel>Comprobante</FormLabel>
                <Input
                  type="file"
                  onChange={handleFileChange}
                  accept=".pdf,.jpg,.jpeg,.png"
                  sx={{
                    '::file-selector-button': {
                      height: '100%',
                      padding: '0 20px',
                      background: 'gray.100',
                      border: 'none',
                      borderRight: '1px solid',
                      borderColor: 'gray.200',
                      cursor: 'pointer',
                      '&:hover': {
                        background: 'gray.200'
                      }
                    }
                  }}
                />
                <FormHelperText>
                  Formatos permitidos: PDF, JPG, PNG. Tamaño máximo: 5MB
                </FormHelperText>
              </FormControl>

              <Table variant="simple">
                <Thead>
                  <Tr>
                    <Th>Producto</Th>
                    <Th>Cantidad</Th>
                    <Th>Precio</Th>
                    <Th>Subtotal</Th>
                    <Th></Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {formData.detalles.map((detalle, index) => (
                    <Tr key={index}>
                      <Td>
                        <Select
                          value={detalle.producto}
                          onChange={(e) => handleDetalleChange(index, 'producto', e.target.value)}
                        >
                          <option value="">Seleccione un producto</option>
                          {productos.map(producto => (
                            <option key={producto.id} value={producto.id}>
                              {producto.nombre} - {producto.sku}
                            </option>
                          ))}
                        </Select>
                      </Td>
                      <Td>
                        <NumberInput
                          min={1}
                          value={detalle.cantidad}
                          onChange={(value) => handleDetalleChange(index, 'cantidad', value)}
                        >
                          <NumberInputField />
                        </NumberInput>
                      </Td>
                      <Td>
                        <NumberInput
                          min={0}
                          value={detalle.precio_unitario}
                          onChange={(value) => handleDetalleChange(index, 'precio_unitario', value)}
                        >
                          <NumberInputField />
                        </NumberInput>
                      </Td>
                      <Td>
                        {(detalle.cantidad * detalle.precio_unitario).toFixed(2)}
                      </Td>
                      <Td>
                        <IconButton
                          icon={<DeleteIcon />}
                          onClick={() => eliminarProducto(index)}
                          isDisabled={formData.detalles.length === 1}
                        />
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>

              <Button onClick={agregarProducto} colorScheme="blue">
                Agregar Producto
              </Button>

              <Box w="100%" p={4} borderWidth="1px" borderRadius="lg">
                <Text fontSize="lg" fontWeight="bold">Resumen</Text>
                <Text>Subtotal: {getSimboloMoneda(formData.moneda)} {calcularSubtotal().toFixed(2)}</Text>
                <Text>IGV: {getSimboloMoneda(formData.moneda)} {calcularIGV().toFixed(2)}</Text>
                <Text fontSize="xl" fontWeight="bold">Total: {getSimboloMoneda(formData.moneda)} {calcularTotal().toFixed(2)}</Text>
              </Box>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Cancelar
            </Button>
            <Button
              colorScheme="blue"
              onClick={handleSubmit}
              isLoading={isSubmitting}
            >
              Guardar
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      <AlertDialog
        isOpen={isAlertOpen}
        leastDestructiveRef={cancelRef}
        onClose={() => setIsAlertOpen(false)}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              ¡Alerta de Stock Bajo!
            </AlertDialogHeader>

            <AlertDialogBody>
              <Text mb={4}>
                Los siguientes productos han quedado con stock bajo después de la venta:
              </Text>
              <Table size="sm">
                <Thead>
                  <Tr>
                    <Th>Producto</Th>
                    <Th isNumeric>Stock Actual</Th>
                    <Th isNumeric>Stock Mínimo</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {productosStockBajo.map((producto) => (
                    <Tr key={producto.id}>
                      <Td>{producto.nombre}</Td>
                      <Td isNumeric color="red.500" fontWeight="bold">
                        {producto.stock_actual}
                      </Td>
                      <Td isNumeric>{producto.stock_minimo}</Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
              <Text mt={4} color="orange.500">
                Se recomienda realizar un pedido de reposición para estos productos.
              </Text>
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={() => setIsAlertOpen(false)}>
                Entendido
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </>
  );
};

export default VentaForm;
