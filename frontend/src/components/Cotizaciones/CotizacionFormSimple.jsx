import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  Select,
  Grid,
  GridItem,
  Heading,
  VStack,
  HStack,
  IconButton,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  NumberInput,
  NumberInputField,
  useToast,
  Flex,
  Text,
  Divider,
  Card,
  CardBody
} from '@chakra-ui/react';
import { FaPlus, FaTrash, FaSave, FaArrowLeft, FaEye, FaFilePdf, FaImage } from 'react-icons/fa';
import { useNavigate, useParams } from 'react-router-dom';
import cotizacionesService from '../../services/cotizacionesService';
import { clientesService } from '../../services/clientes.service';
import { productosService } from '../../services/productos.service';
import { api } from '../../api';

const CotizacionFormSimple = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [clientes, setClientes] = useState([]);
  const [productos, setProductos] = useState([]);
  const [empresaInfo, setEmpresaInfo] = useState(null);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  
  const [formData, setFormData] = useState({
    cliente: '',
    fecha_emision: new Date().toISOString().split('T')[0],
    fecha_vencimiento: '',
    moneda: 'USD',
    forma_pago: 'CREDITO 30 DIAS',
    pago_facturas: 'Viernes de 09:00 - 13:00',
    tiempo_entrega: '',
    lugar_entrega: '',
    validez_oferta: '30 días',
    detalles: []
  });

  useEffect(() => {
    cargarDatos();
    if (!id) {
      // Fecha de vencimiento por defecto: 30 días
      const fecha = new Date();
      fecha.setDate(fecha.getDate() + 30);
      setFormData(prev => ({
        ...prev,
        fecha_vencimiento: fecha.toISOString().split('T')[0]
      }));
    }
  }, [id]);

  const cargarDatos = async () => {
    try {
      const [clientesData, productosData, empresaData] = await Promise.all([
        clientesService.getClientes(),
        productosService.getProductos(),
        api.get('/api/empresas/')
      ]);
      
      const clientesArray = Array.isArray(clientesData?.results) 
        ? clientesData.results 
        : Array.isArray(clientesData) 
          ? clientesData 
          : [];
      
      const productosArray = Array.isArray(productosData?.results) 
        ? productosData.results 
        : Array.isArray(productosData) 
          ? productosData 
          : [];
      
      setClientes(clientesArray);
      setProductos(productosArray);
      
      // Obtener info de la empresa
      if (empresaData.data && empresaData.data.length > 0) {
        setEmpresaInfo(empresaData.data[0]);
      }
    } catch (error) {
      console.error('Error al cargar datos:', error);
      setClientes([]);
      setProductos([]);
    }
  };

  const handleLogoUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validar tipo de archivo
    if (!file.type.startsWith('image/')) {
      toast({
        title: 'Error',
        description: 'Solo se permiten archivos de imagen',
        status: 'error',
        duration: 3000,
      });
      return;
    }

    // Validar tamaño (máx 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast({
        title: 'Error',
        description: 'El archivo no debe superar los 5MB',
        status: 'error',
        duration: 3000,
      });
      return;
    }

    try {
      setUploadingLogo(true);
      const formData = new FormData();
      formData.append('logo', file);

      const response = await api.post(
        `/api/empresas/${empresaInfo.id}/upload_logo/`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      setEmpresaInfo(response.data);
      toast({
        title: 'Logo actualizado',
        description: 'El logo se ha subido correctamente',
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      console.error('Error al subir logo:', error);
      toast({
        title: 'Error al subir logo',
        description: error.response?.data?.error || error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setUploadingLogo(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const agregarDetalle = () => {
    setFormData(prev => ({
      ...prev,
      detalles: [
        ...prev.detalles,
        {
          producto: '',
          codigo: '',
          descripcion: '',
          cantidad: 1,
          precio_unitario: 0,
          descuento_item: 0,
          orden: prev.detalles.length
        }
      ]
    }));
  };

  const eliminarDetalle = (index) => {
    setFormData(prev => ({
      ...prev,
      detalles: prev.detalles.filter((_, i) => i !== index)
    }));
  };

  const handleDetalleChange = (index, field, value) => {
    setFormData(prev => {
      const nuevosDetalles = [...prev.detalles];
      nuevosDetalles[index] = {
        ...nuevosDetalles[index],
        [field]: value
      };

      if (field === 'producto' && value) {
        const producto = productos.find(p => p.id === parseInt(value));
        if (producto) {
          nuevosDetalles[index] = {
            ...nuevosDetalles[index],
            codigo: producto.sku || '',
            descripcion: producto.nombre,
            precio_unitario: producto.precio_venta || 0
          };
        }
      }

      return { ...prev, detalles: nuevosDetalles };
    });
  };

  const calcularSubtotalDetalle = (detalle) => {
    const subtotal = (detalle.cantidad * detalle.precio_unitario) - (detalle.descuento_item || 0);
    return subtotal > 0 ? subtotal : 0;
  };

  const calcularTotales = () => {
    const subtotal = formData.detalles.reduce((sum, detalle) => {
      return sum + calcularSubtotalDetalle(detalle);
    }, 0);

    // IGV siempre se suma (18%)
    const igv = subtotal * 0.18;
    const total = subtotal + igv;

    return {
      subtotal: subtotal.toFixed(2),
      igv: igv.toFixed(2),
      total: total.toFixed(2)
    };
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.cliente) {
      toast({
        title: 'Error',
        description: 'Debe seleccionar un cliente',
        status: 'error',
        duration: 3000,
      });
      return;
    }

    if (formData.detalles.length === 0) {
      toast({
        title: 'Error',
        description: 'Debe agregar al menos un producto',
        status: 'error',
        duration: 3000,
      });
      return;
    }

    try {
      setLoading(true);
      
      // Preparar datos con valores por defecto
      const dataToSend = {
        ...formData,
        asunto: `Cotización para ${clientes.find(c => c.id === parseInt(formData.cliente))?.nombre || 'Cliente'}`,
        incluye_igv: false, // IGV se suma al final
        porcentaje_igv: 18,
        descuento: 0
      };

      if (id) {
        await cotizacionesService.update(id, dataToSend);
        toast({
          title: 'Cotización actualizada',
          status: 'success',
          duration: 3000,
        });
      } else {
        await cotizacionesService.create(dataToSend);
        toast({
          title: 'Cotización creada',
          status: 'success',
          duration: 3000,
        });
      }
      navigate('/app/cotizaciones');
    } catch (error) {
      toast({
        title: 'Error al guardar',
        description: error.response?.data?.detail || error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const totales = calcularTotales();
  const simboloMoneda = formData.moneda === 'PEN' ? 'S/' : 'US$';

  const handleVisualizarPDF = async () => {
    if (!id) {
      toast({
        title: 'Guarda la cotización primero',
        description: 'Debes guardar la cotización antes de visualizarla',
        status: 'warning',
        duration: 3000,
      });
      return;
    }
    
    try {
      const response = await api.get(`/api/cotizaciones/${id}/export_pdf/`, {
        responseType: 'blob',
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      window.open(url, '_blank');
      window.URL.revokeObjectURL(url);
    } catch (error) {
      toast({
        title: 'Error al visualizar PDF',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  const handleDescargarPDF = async () => {
    if (!id) {
      toast({
        title: 'Guarda la cotización primero',
        description: 'Debes guardar la cotización antes de descargarla',
        status: 'warning',
        duration: 3000,
      });
      return;
    }
    
    await cotizacionesService.exportarPDF(id);
  };

  return (
    <Box p={6} maxW="1400px" mx="auto">
      <Flex justify="space-between" align="center" mb={6}>
        <Heading size="lg">{id ? 'Editar Cotización' : 'Nueva Cotización'}</Heading>
        <HStack>
          {id && (
            <>
              <Button
                leftIcon={<FaEye />}
                colorScheme="purple"
                variant="outline"
                onClick={handleVisualizarPDF}
              >
                Visualizar PDF
              </Button>
              <Button
                leftIcon={<FaFilePdf />}
                colorScheme="red"
                variant="outline"
                onClick={handleDescargarPDF}
              >
                Descargar PDF
              </Button>
            </>
          )}
          <Button
            leftIcon={<FaArrowLeft />}
            variant="ghost"
            onClick={() => navigate('/app/cotizaciones')}
          >
            Volver
          </Button>
        </HStack>
      </Flex>

      <form onSubmit={handleSubmit}>
        <VStack spacing={6} align="stretch">
          {/* Logo de la Empresa */}
          <Card>
            <CardBody>
              <Flex justify="space-between" align="center">
                <Box>
                  <Heading size="md" mb={2}>Logo de la Empresa</Heading>
                  <Text fontSize="sm" color="gray.600">
                    Este logo aparecerá en las cotizaciones PDF
                  </Text>
                </Box>
                <HStack spacing={4}>
                  {empresaInfo?.logo_url && (
                    <Box
                      borderWidth={1}
                      borderRadius="md"
                      p={2}
                      bg="gray.50"
                    >
                      <img
                        src={empresaInfo.logo_url}
                        alt="Logo empresa"
                        style={{ maxHeight: '80px', maxWidth: '200px' }}
                      />
                    </Box>
                  )}
                  <FormControl w="auto">
                    <Input
                      type="file"
                      accept="image/*"
                      onChange={handleLogoUpload}
                      display="none"
                      id="logo-upload"
                    />
                    <Button
                      as="label"
                      htmlFor="logo-upload"
                      leftIcon={<FaImage />}
                      colorScheme="blue"
                      variant="outline"
                      isLoading={uploadingLogo}
                      loadingText="Subiendo..."
                      cursor="pointer"
                    >
                      {empresaInfo?.logo_url ? 'Cambiar Logo' : 'Subir Logo'}
                    </Button>
                  </FormControl>
                </HStack>
              </Flex>
            </CardBody>
          </Card>
          {/* Información Principal */}
          <Card>
            <CardBody>
              <Grid templateColumns="repeat(4, 1fr)" gap={4}>
                <GridItem colSpan={2}>
                  <FormControl isRequired>
                    <FormLabel fontWeight="bold">Cliente</FormLabel>
                    <Select
                      name="cliente"
                      value={formData.cliente}
                      onChange={handleChange}
                      placeholder="Seleccione un cliente"
                      size="lg"
                    >
                      {clientes.map(cliente => (
                        <option key={cliente.id} value={cliente.id}>
                          {cliente.nombre}
                        </option>
                      ))}
                    </Select>
                  </FormControl>
                </GridItem>

                <GridItem>
                  <FormControl isRequired>
                    <FormLabel fontWeight="bold">Fecha de Emisión</FormLabel>
                    <Input
                      type="date"
                      name="fecha_emision"
                      value={formData.fecha_emision}
                      onChange={handleChange}
                      size="lg"
                    />
                  </FormControl>
                </GridItem>

                <GridItem>
                  <FormControl isRequired>
                    <FormLabel fontWeight="bold">Moneda</FormLabel>
                    <Select 
                      name="moneda" 
                      value={formData.moneda} 
                      onChange={handleChange}
                      size="lg"
                    >
                      <option value="USD">Dólares (US$)</option>
                      <option value="PEN">Soles (S/)</option>
                    </Select>
                  </FormControl>
                </GridItem>
              </Grid>
            </CardBody>
          </Card>

          {/* Condiciones de Compra */}
          <Card>
            <CardBody>
              <Heading size="md" mb={4}>Condiciones de Compra</Heading>
              <Grid templateColumns="repeat(2, 1fr)" gap={4}>
                <GridItem>
                  <FormControl isRequired>
                    <FormLabel fontWeight="bold">Forma de Pago</FormLabel>
                    <Input
                      name="forma_pago"
                      value={formData.forma_pago}
                      onChange={handleChange}
                      placeholder="Ej: CREDITO 30 DIAS"
                      size="lg"
                    />
                  </FormControl>
                </GridItem>

                <GridItem>
                  <FormControl>
                    <FormLabel fontWeight="bold">Pago de Facturas</FormLabel>
                    <Input
                      name="pago_facturas"
                      value={formData.pago_facturas}
                      onChange={handleChange}
                      placeholder="Ej: Viernes de 09:00 - 13:00"
                      size="lg"
                    />
                  </FormControl>
                </GridItem>

                <GridItem>
                  <FormControl isRequired>
                    <FormLabel fontWeight="bold">Fecha de Entrega</FormLabel>
                    <Input
                      type="date"
                      name="fecha_vencimiento"
                      value={formData.fecha_vencimiento}
                      onChange={handleChange}
                      size="lg"
                    />
                  </FormControl>
                </GridItem>

                <GridItem>
                  <FormControl>
                    <FormLabel fontWeight="bold">Lugar de Entrega</FormLabel>
                    <Input
                      name="lugar_entrega"
                      value={formData.lugar_entrega}
                      onChange={handleChange}
                      placeholder="Ej: Av. Francisco Javier Mariategui, 138"
                      size="lg"
                    />
                  </FormControl>
                </GridItem>
              </Grid>
            </CardBody>
          </Card>

          {/* Productos */}
          <Card>
            <CardBody>
              <Flex justify="space-between" align="center" mb={4}>
                <Heading size="md">Productos</Heading>
                <Button
                  leftIcon={<FaPlus />}
                  colorScheme="blue"
                  onClick={agregarDetalle}
                >
                  Agregar Producto
                </Button>
              </Flex>

              {formData.detalles.length === 0 ? (
                <Text color="gray.500" textAlign="center" py={8}>
                  No hay productos agregados. Haga clic en "Agregar Producto" para comenzar.
                </Text>
              ) : (
                <Box overflowX="auto">
                  <Table variant="simple">
                    <Thead bg="gray.50">
                      <Tr>
                        <Th width="30px">#</Th>
                        <Th width="200px">Producto</Th>
                        <Th width="120px">Código</Th>
                        <Th>Descripción</Th>
                        <Th width="100px">Cantidad</Th>
                        <Th width="120px">V. Unitario</Th>
                        <Th width="120px">Total</Th>
                        <Th width="50px"></Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {formData.detalles.map((detalle, index) => (
                        <Tr key={index}>
                          <Td>{index + 1}</Td>
                          <Td>
                            <Select
                              value={detalle.producto}
                              onChange={(e) => handleDetalleChange(index, 'producto', e.target.value)}
                              placeholder="Seleccionar"
                            >
                              {productos.map(prod => (
                                <option key={prod.id} value={prod.id}>
                                  {prod.nombre}
                                </option>
                              ))}
                            </Select>
                          </Td>
                          <Td>
                            <Input
                              value={detalle.codigo}
                              onChange={(e) => handleDetalleChange(index, 'codigo', e.target.value)}
                              placeholder="SKU"
                            />
                          </Td>
                          <Td>
                            <Input
                              value={detalle.descripcion}
                              onChange={(e) => handleDetalleChange(index, 'descripcion', e.target.value)}
                              placeholder="Descripción del producto"
                              isRequired
                            />
                          </Td>
                          <Td>
                            <NumberInput
                              value={detalle.cantidad}
                              onChange={(value) => handleDetalleChange(index, 'cantidad', parseFloat(value) || 1)}
                              min={0.01}
                              step={1}
                            >
                              <NumberInputField />
                            </NumberInput>
                          </Td>
                          <Td>
                            <NumberInput
                              value={detalle.precio_unitario}
                              onChange={(value) => handleDetalleChange(index, 'precio_unitario', parseFloat(value) || 0)}
                              min={0}
                              step={0.01}
                            >
                              <NumberInputField />
                            </NumberInput>
                          </Td>
                          <Td fontWeight="bold" fontSize="lg">
                            {simboloMoneda} {calcularSubtotalDetalle(detalle).toFixed(2)}
                          </Td>
                          <Td>
                            <IconButton
                              icon={<FaTrash />}
                              colorScheme="red"
                              variant="ghost"
                              onClick={() => eliminarDetalle(index)}
                            />
                          </Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
              )}

              {/* Totales */}
              {formData.detalles.length > 0 && (
                <Box mt={6} p={6} bg="gray.50" borderRadius="md">
                  <Grid templateColumns="1fr 200px" gap={3} maxW="500px" ml="auto">
                    <Text fontWeight="bold" fontSize="lg">Sub-Total Venta:</Text>
                    <Text textAlign="right" fontSize="lg" fontWeight="bold">
                      {simboloMoneda} {totales.subtotal}
                    </Text>

                    <Text fontWeight="bold" fontSize="lg">Total Descuento:</Text>
                    <Text textAlign="right" fontSize="lg" fontWeight="bold">
                      {simboloMoneda} 0.00
                    </Text>

                    <Text fontWeight="bold" fontSize="lg">Valor de Venta:</Text>
                    <Text textAlign="right" fontSize="lg" fontWeight="bold">
                      {simboloMoneda} {totales.subtotal}
                    </Text>

                    <Text fontWeight="bold" fontSize="lg">IGV 18%:</Text>
                    <Text textAlign="right" fontSize="lg" fontWeight="bold">
                      {simboloMoneda} {totales.igv}
                    </Text>

                    <Divider gridColumn="1 / -1" borderColor="gray.400" borderWidth="2px" my={2} />

                    <Text fontSize="xl" fontWeight="bold" color="green.600">TOTAL VENTA:</Text>
                    <Text fontSize="xl" fontWeight="bold" color="green.600" textAlign="right">
                      {simboloMoneda} {totales.total}
                    </Text>
                  </Grid>
                </Box>
              )}
            </CardBody>
          </Card>

          {/* Botones */}
          <Flex justify="flex-end" gap={4}>
            <Button
              variant="outline"
              size="lg"
              onClick={() => navigate('/app/cotizaciones')}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              colorScheme="blue"
              size="lg"
              leftIcon={<FaSave />}
              isLoading={loading}
              loadingText="Guardando..."
            >
              Guardar Cotización
            </Button>
          </Flex>
        </VStack>
      </form>
    </Box>
  );
};

export default CotizacionFormSimple;

