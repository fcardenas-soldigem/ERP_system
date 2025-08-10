import React, { useState, useEffect, useRef } from 'react';
import {
  FormControl,
  FormLabel,
  Spinner,
  Input,
  Box,
  List,
  ListItem,
  Text,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { proveedoresService } from '../../services/proveedores.service';

const ProveedorSelect = ({ value, onChange }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = useRef(null);

  const { data: proveedores = [], isLoading } = useQuery({
    queryKey: ['proveedores'],
    queryFn: proveedoresService.getProveedores,
  });

  // Cerrar la lista cuando se hace clic fuera del componente
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredProveedores = searchTerm
    ? proveedores.filter(proveedor => 
        proveedor.razon_social?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        proveedor.ruc?.includes(searchTerm)
      )
    : proveedores;

  const selectedProveedor = proveedores.find(p => p.id === parseInt(value));

  if (isLoading) return <Spinner />;

  return (
      <FormControl>
        <FormLabel>Proveedor</FormLabel>
        <Box position="relative" ref={wrapperRef}>
          <Input
            placeholder="Buscar proveedor..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setIsOpen(true);
            }}
            onClick={() => setIsOpen(true)}
            onFocus={() => setIsOpen(true)}
          />
          {selectedProveedor && !isOpen && (
            <Text fontSize="sm" color="gray.600" mt={1}>
              Seleccionado: {selectedProveedor.razon_social} - {selectedProveedor.ruc}
            </Text>
          )}
          {isOpen && (
            <List
              position="absolute"
              top="100%"
              left={0}
              right={0}
              bg="white"
              boxShadow="lg"
              borderRadius="md"
              maxH="200px"
              overflowY="auto"
              zIndex={1000}
              border="1px"
              borderColor="gray.200"
              mt={1}
            >
              {filteredProveedores.length > 0 ? (
                filteredProveedores.map((proveedor) => (
                  <ListItem
                    key={proveedor.id}
                    px={4}
                    py={2}
                    cursor="pointer"
                    _hover={{ bg: "gray.100" }}
                    onClick={() => {
                      onChange(proveedor.id.toString());
                      setSearchTerm(proveedor.razon_social);
                      setIsOpen(false);
                    }}
                  >
                    {proveedor.razon_social} - {proveedor.ruc}
                  </ListItem>
                ))
              ) : (
                <ListItem px={4} py={2} color="gray.500">
                  No se encontraron proveedores
                </ListItem>
              )}
            </List>
          )}
        </Box>
      </FormControl>
  );
};

export default ProveedorSelect; 