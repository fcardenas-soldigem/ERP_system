import React, { useState, useEffect } from 'react';
import {
  Box,
  Heading,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Select,
  Input,
  Button,
  Flex,
  Text,
  useToast,
  HStack,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  IconButton,
  Stack,
  Card,
  CardBody
} from '@chakra-ui/react';
import { DownloadIcon, ChevronDownIcon, SearchIcon } from '@chakra-ui/icons';
import { Line } from 'react-chartjs-2';
import * as XLSX from 'xlsx';
import { inventarioService } from '../../services/inventario.service';

const ValorInventario = () => {
  const [items, setItems] = useState([]);
  const [bodegas, setBodegas] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [filtros, setFiltros] = useState({
    bodega: '',
    categoria: '',
    fechaHasta: '',
    fechaDesde: '',
    busqueda: '',
    estado: 'todos'
  });
  const [total, setTotal] = useState(0);
  const [datosGrafico, setDatosGrafico] = useState(null);
  const toast = useToast();

  useEffect(() => {
    cargarDatosIniciales();
  }, []);

  const cargarDatosIniciales = async () => {
    try {
      const [bodegasData, categoriasData] = await Promise.all([
        inventarioService.getBodegas(),
        inventarioService.getCategorias()
      ]);
      setBodegas(bodegasData);
      setCategorias(categoriasData);
    } catch (error) {
      mostrarError('No se pudieron cargar los datos iniciales');
    }
  };

  const generarReporte = async () => {
    try {
      const data = await inventarioService.getValorInventario(filtros);
      setItems(data);
      const totalValor = data.reduce((sum, item) => sum + item.valor_total, 0);
      setTotal(totalValor);
      generarDatosGrafico(data);
    } catch (error) {
      mostrarError('No se pudo generar el reporte');
    }
  };

  const generarDatosGrafico = (data) => {
    // Agrupar por categoría
    const porCategoria = data.reduce((acc, item) => {
      const cat = item.categoria || 'Sin categoría';
      acc[cat] = (acc[cat] || 0) + item.valor_total;
      return acc;
    }, {});

    setDatosGrafico({
      labels: Object.keys(porCategoria),
      datasets: [{
        label: 'Valor de inventario por categoría (precio de compra)',
        data: Object.values(porCategoria),
        backgroundColor: 'rgba(0, 168, 132, 0.2)',
        borderColor: 'rgba(0, 168, 132, 1)',
        borderWidth: 1
      }]
    });
  };

  const exportarExcel = () => {
    const dataToExport = items.map(item => ({
      'Ítem': item.producto__nombre,
      'Referencia': item.producto__codigo,
      'Descripción': item.descripcion,
      'Cantidad': item.cantidad_total,
      'Unidad': item.producto__unidad_medida,
      'Estado': item.estado,
      'Precio de Compra': item.costo_promedio,
      'Total': item.valor_total
    }));

    const ws = XLSX.utils.json_to_sheet(dataToExport);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Valor Inventario');
    XLSX.writeFile(wb, `valor_inventario_${new Date().toISOString()}.xlsx`);
  };

  const exportarPDF = () => {
    // Implementar exportación a PDF usando jsPDF
  };

  const mostrarError = (mensaje) => {
    toast({
      title: 'Error',
      description: mensaje,
      status: 'error',
      duration: 3000,
    });
  };

  return (
    <Box p={4}>
      <Flex justify="space-between" align="center" mb={6}>
        <Heading size="lg">Valor de inventario</Heading>
        <Menu>
          <MenuButton
            as={Button}
            rightIcon={<ChevronDownIcon />}
            colorScheme="teal"
          >
            Exportar
          </MenuButton>
          <MenuList>
            <MenuItem onClick={exportarExcel} icon={<DownloadIcon />}>
              Exportar a Excel
            </MenuItem>
            <MenuItem onClick={exportarPDF} icon={<DownloadIcon />}>
              Exportar a PDF
            </MenuItem>
          </MenuList>
        </Menu>
      </Flex>

      <Stack spacing={4} mb={6}>
        <HStack spacing={4}>
          <Input
            type="date"
            value={filtros.fechaDesde}
            onChange={(e) => setFiltros({...filtros, fechaDesde: e.target.value})}
            placeholder="Fecha desde"
          />
          <Input
            type="date"
            value={filtros.fechaHasta}
            onChange={(e) => setFiltros({...filtros, fechaHasta: e.target.value})}
            placeholder="Fecha hasta"
          />
        </HStack>
        
        <HStack spacing={4}>
          <Select
            value={filtros.bodega}
            onChange={(e) => setFiltros({...filtros, bodega: e.target.value})}
            placeholder="Seleccionar bodega"
          >
            {bodegas.map(bodega => (
              <option key={bodega.id} value={bodega.id}>
                {bodega.nombre}
              </option>
            ))}
          </Select>
          
          <Select
            value={filtros.categoria}
            onChange={(e) => setFiltros({...filtros, categoria: e.target.value})}
            placeholder="Seleccionar categoría"
          >
            {categorias.map(categoria => (
              <option key={categoria.id} value={categoria.id}>
                {categoria.nombre}
              </option>
            ))}
          </Select>

          <Select
            value={filtros.estado}
            onChange={(e) => setFiltros({...filtros, estado: e.target.value})}
          >
            <option value="todos">Todos los estados</option>
            <option value="activo">Activo</option>
            <option value="inactivo">Inactivo</option>
          </Select>
        </HStack>

        <Flex>
          <Input
            placeholder="Buscar por nombre o referencia"
            value={filtros.busqueda}
            onChange={(e) => setFiltros({...filtros, busqueda: e.target.value})}
            mr={4}
          />
          <Button colorScheme="teal" onClick={generarReporte} leftIcon={<SearchIcon />}>
            Generar reporte
          </Button>
        </Flex>
      </Stack>

      <Flex gap={4} mb={6}>
        <Card flex={1}>
          <CardBody>
            <Text fontSize="lg" mb={4}>Valor total del inventario</Text>
            <Text fontSize="2xl" fontWeight="bold" color="teal.500">
              ${total.toFixed(2)}
            </Text>
          </CardBody>
        </Card>
        
        {datosGrafico && (
          <Card flex={2}>
            <CardBody>
              <Line data={datosGrafico} options={{
                responsive: true,
                plugins: {
                  legend: {
                    position: 'top',
                  },
                  title: {
                    display: true,
                    text: 'Valor de inventario por categoría (precio de compra)'
                  }
                }
              }} />
            </CardBody>
          </Card>
        )}
      </Flex>

      <Table variant="simple">
        <Thead>
          <Tr>
            <Th>Ítem</Th>
            <Th>Referencia</Th>
            <Th>Descripción</Th>
            <Th>Cantidad</Th>
            <Th>Unidad</Th>
            <Th>Estado</Th>
            <Th isNumeric>Precio de Compra</Th>
            <Th isNumeric>Total</Th>
          </Tr>
        </Thead>
        <Tbody>
          {items.map((item) => (
            <Tr key={item.producto__codigo}>
              <Td>{item.producto__nombre}</Td>
              <Td>{item.producto__codigo}</Td>
              <Td>{item.descripcion}</Td>
              <Td isNumeric>{item.cantidad_total}</Td>
              <Td>{item.producto__unidad_medida}</Td>
              <Td>{item.estado}</Td>
              <Td isNumeric>${item.costo_promedio.toFixed(2)}</Td>
              <Td isNumeric>${item.valor_total.toFixed(2)}</Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </Box>
  );
};

export default ValorInventario;