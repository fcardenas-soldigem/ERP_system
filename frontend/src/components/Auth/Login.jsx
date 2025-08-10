import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  VStack,
  Text,
  useToast,
  Container,
  Heading,
} from '@chakra-ui/react';
import { useAuth } from '../context/AuthContext';

const Login = () => {
  const [credentials, setCredentials] = useState({
    email: '',
    password: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const toast = useToast();
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await login(credentials);
      // La redirección ahora se maneja en el AuthContext
    } catch (error) {
      console.error('Error en login:', error);
      toast({
        title: 'Error de autenticación',
        description: error.response?.data?.detail || 'Credenciales inválidas',
        status: 'error',
        duration: 3000,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Container maxW="md" centerContent py={10}>
      <VStack spacing={8} w="100%">
        <Heading>Iniciar Sesión</Heading>
        <Box w="100%" p={8} borderWidth={1} borderRadius="lg">
          <form onSubmit={handleSubmit}>
            <VStack spacing={4}>
              <FormControl id="email" isRequired>
                <FormLabel>Email</FormLabel>
                <Input
                  type="email"
                  value={credentials.email}
                  onChange={(e) => setCredentials({ ...credentials, email: e.target.value })}
                />
              </FormControl>
              <FormControl id="password" isRequired>
                <FormLabel>Contraseña</FormLabel>
                <Input
                  type="password"
                  value={credentials.password}
                  onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
                />
              </FormControl>
              <Button
                type="submit"
                colorScheme="blue"
                width="full"
                mt={4}
                isLoading={isLoading}
              >
                Iniciar Sesión
              </Button>
            </VStack>
          </form>
        </Box>
      </VStack>
    </Container>
  );
};

export default Login; 
