import React from 'react';
import {
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Button,
  HStack,
  Text,
  Box,
  IconButton
} from '@chakra-ui/react';
import { DeleteIcon } from '@chakra-ui/icons';

const CarritoCompra = ({ 
  items, 
  onRemoveItem, 
  subtotal, 
  igv, 
  total 
}) => {
  return (
    <Box>
      <Text fontSize="xl" fontWeight="bold" mb={4}>
        Carrito de Compra
      </Text>
      
      <Table variant="simple">
        <Thead>
          <Tr>
            <Th>PRODUCTO</Th>
            <Th>PRECIO</Th>
            <Th>CANTIDAD</Th>
            <Th>SUBTOTAL</Th>
            <Th>ACCIONES</Th>
          </Tr>
        </Thead>
        <Tbody>
          {items.map((item) => (
            <Tr key={item.id}>
              <Td>{item.producto.nombre}</Td>
              <Td>S/ {item.precio_unitario}</Td>
              <Td>{item.cantidad}</Td>
              <Td>S/ {(item.precio_unitario * item.cantidad).toFixed(2)}</Td>
              <Td>
                <IconButton
                  aria-label="Eliminar producto"
                  icon={<DeleteIcon />}
                  colorScheme="red"
                  variant="ghost"
                  onClick={() => onRemoveItem(item.id)}
                />
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>

      <Box mt={4} textAlign="right">
        <HStack justify="flex-end" spacing={8} mb={2}>
          <Text>Subtotal:</Text>
          <Text>S/ {subtotal.toFixed(2)}</Text>
        </HStack>
        <HStack justify="flex-end" spacing={8} mb={2}>
          <Text>IGV (18%):</Text>
          <Text>S/ {igv.toFixed(2)}</Text>
        </HStack>
        <HStack justify="flex-end" spacing={8} mb={4}>
          <Text fontWeight="bold">Total:</Text>
          <Text fontWeight="bold">S/ {total.toFixed(2)}</Text>
        </HStack>
      </Box>
    </Box>
  );
};

export default CarritoCompra; 