import React from 'react';
import {
  Box,
  Button,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Icon,
  SimpleGrid,
  useColorMode,
  IconButton,
  Flex,
  Badge,
} from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { MoonIcon, SunIcon } from '@chakra-ui/icons';
import {
  FaChartLine,
  FaRobot,
  FaShieldAlt,
  FaCloud,
  FaMobileAlt,
  FaBrain,
  FaArrowRight,
  FaCheckCircle,
} from 'react-icons/fa';
import { AuroraBackground } from '../components/Landing/AuroraBackground';

const MotionBox = motion(Box);
const MotionButton = motion(Button);

const FeatureCard = ({ icon, title, description }) => {
  return (
    <MotionBox
      bg="white"
      p={6}
      borderRadius="xl"
      boxShadow="lg"
      whileHover={{ scale: 1.05, y: -5 }}
      transition={{ duration: 0.3 }}
    >
      <VStack spacing={4} align="start">
        <Box
          p={3}
          bg="blue.50"
          borderRadius="lg"
        >
          <Icon as={icon} boxSize={8} color="blue.500" />
        </Box>
        <Heading size="md">{title}</Heading>
        <Text color="gray.600">
          {description}
        </Text>
      </VStack>
    </MotionBox>
  );
};

const LandingPage = () => {
  const navigate = useNavigate();
  const { colorMode, toggleColorMode } = useColorMode();

  const features = [
    {
      icon: FaChartLine,
      title: 'Gestión Integral',
      description: 'Control completo de ventas, compras, inventario y finanzas en un solo lugar.',
    },
    {
      icon: FaBrain,
      title: 'Machine Learning',
      description: 'Predicciones inteligentes de ventas, churn y recomendaciones de productos.',
    },
    {
      icon: FaRobot,
      title: 'Asistente IA',
      description: 'Consulta tus datos con lenguaje natural gracias a la integración con OpenAI.',
    },
    {
      icon: FaShieldAlt,
      title: 'Seguridad Avanzada',
      description: 'Autenticación JWT, encriptación y aislamiento multi-tenant.',
    },
    {
      icon: FaCloud,
      title: 'Cloud Ready',
      description: 'Desplegable en cualquier servidor con Docker y escalable horizontalmente.',
    },
    {
      icon: FaMobileAlt,
      title: 'Responsive',
      description: 'Diseño adaptable que funciona perfectamente en cualquier dispositivo.',
    },
  ];

  return (
    <AuroraBackground>
      {/* Header */}
      <Box
        position="absolute"
        top={0}
        left={0}
        right={0}
        zIndex={10}
      >
        <Container maxW="container.xl" py={4}>
          <Flex justify="space-between" align="center">
            <HStack spacing={3}>
              <Box
                w="50px"
                h="50px"
                bg="blue.500"
                borderRadius="lg"
                display="flex"
                alignItems="center"
                justifyContent="center"
                color="white"
                fontWeight="bold"
                fontSize="2xl"
              >
                E
              </Box>
              <Heading size="lg" color="blue.600" _dark={{ color: "blue.300" }}>
                ERP System
              </Heading>
            </HStack>
            <HStack spacing={3}>
              <IconButton
                icon={colorMode === 'light' ? <MoonIcon /> : <SunIcon />}
                onClick={toggleColorMode}
                variant="ghost"
                aria-label="Toggle color mode"
              />
              <Button
                variant="ghost"
                onClick={() => navigate('/login')}
              >
                Iniciar Sesión
              </Button>
            </HStack>
          </Flex>
        </Container>
      </Box>

      {/* Hero Section */}
      <Container maxW="container.xl" py={20} px={4}>
        <VStack spacing={8} textAlign="center" w="full">
          <MotionBox
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.8 }}
          >
            <Badge
              colorScheme="blue"
              fontSize="md"
              px={4}
              py={2}
              borderRadius="full"
              mb={4}
            >
              🚀 Sistema ERP de Nueva Generación
            </Badge>
            <Heading
              as="h1"
              size="3xl"
              bgGradient="linear(to-r, blue.400, purple.500)"
              bgClip="text"
              mb={4}
            >
              Gestiona tu Empresa con
              <br />
              Inteligencia Artificial
            </Heading>
            <Text
              fontSize="xl"
              color="gray.600"
              maxW="2xl"
              mx="auto"
            >
              Sistema ERP completo con Machine Learning integrado para
              predicciones inteligentes, análisis avanzado y automatización.
            </Text>
          </MotionBox>

          <MotionBox
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.8 }}
            w="full"
          >
            <HStack spacing={4} justify="center" flexWrap="wrap" w="full">
              <MotionButton
                size="lg"
                colorScheme="blue"
                rightIcon={<FaArrowRight />}
                onClick={() => navigate('/login')}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                px={8}
                py={6}
                fontSize="lg"
              >
                Comenzar Ahora
              </MotionButton>
              <Button
                size="lg"
                variant="outline"
                colorScheme="blue"
                px={8}
                py={6}
                fontSize="lg"
              >
                Ver Demo
              </Button>
            </HStack>
          </MotionBox>

          {/* Stats */}
          <MotionBox
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6, duration: 0.8 }}
            w="full"
            mt={12}
          >
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={8}>
              <VStack>
                <Heading size="2xl" color="blue.500">
                  8+
                </Heading>
                <Text color="gray.600">
                  Módulos Integrados
                </Text>
              </VStack>
              <VStack>
                <Heading size="2xl" color="blue.500">
                  3
                </Heading>
                <Text color="gray.600">
                  Modelos de ML
                </Text>
              </VStack>
              <VStack>
                <Heading size="2xl" color="blue.500">
                  50+
                </Heading>
                <Text color="gray.600">
                  APIs REST
                </Text>
              </VStack>
            </SimpleGrid>
          </MotionBox>
        </VStack>
      </Container>

      {/* Features Section */}
      <Box bg="gray.50" py={20} w="full">
        <Container maxW="container.xl" px={4}>
          <VStack spacing={12} w="full">
            <MotionBox
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              textAlign="center"
            >
              <Heading size="2xl" mb={4}>
                Características Principales
              </Heading>
              <Text fontSize="lg" color="gray.600">
                Todo lo que necesitas para gestionar tu empresa de manera eficiente
              </Text>
            </MotionBox>

            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={8} w="full">
              {features.map((feature, index) => (
                <MotionBox
                  key={index}
                  initial={{ opacity: 0, y: 40 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1, duration: 0.5 }}
                >
                  <FeatureCard {...feature} />
                </MotionBox>
              ))}
            </SimpleGrid>
          </VStack>
        </Container>
      </Box>

      {/* Modules Section */}
      <Container maxW="container.xl" py={20} px={4}>
        <VStack spacing={12} w="full">
            <MotionBox
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              textAlign="center"
            >
              <Heading size="2xl" mb={4}>
                Módulos Incluidos
              </Heading>
              <Text fontSize="lg" color="gray.600">
                Sistema completo para todas las áreas de tu empresa
              </Text>
            </MotionBox>

          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6} w="full">
            {[
              'Ventas y Facturación',
              'Compras y Proveedores',
              'Inventario y Kardex',
              'Cotizaciones Profesionales',
              'Clientes y CRM',
              'Machine Learning',
              'Asistente Virtual IA',
              'Reportes y Analytics',
            ].map((module, index) => (
              <MotionBox
                key={index}
                initial={{ opacity: 0, x: index % 2 === 0 ? -40 : 40 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1, duration: 0.5 }}
              >
                <HStack
                  p={4}
                  bg="white"
                  borderRadius="lg"
                  boxShadow="md"
                >
                  <Icon as={FaCheckCircle} color="green.500" boxSize={6} />
                  <Text fontSize="lg" fontWeight="medium">
                    {module}
                  </Text>
                </HStack>
              </MotionBox>
            ))}
          </SimpleGrid>
        </VStack>
      </Container>

      {/* CTA Section */}
      <Box
        bg="blue.500"
        _dark={{ bg: "blue.600" }}
        py={20}
        w="full"
      >
        <Container maxW="container.xl" px={4}>
          <MotionBox
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <VStack spacing={8} textAlign="center">
              <Heading size="2xl" color="white">
                ¿Listo para Transformar tu Empresa?
              </Heading>
              <Text fontSize="xl" color="whiteAlpha.900" maxW="2xl">
                Únete a las empresas que ya están usando inteligencia artificial
                para optimizar sus operaciones.
              </Text>
              <MotionButton
                size="lg"
                bg="white"
                color="blue.500"
                _hover={{ bg: "gray.100" }}
                rightIcon={<FaArrowRight />}
                onClick={() => navigate('/login')}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                px={8}
                py={6}
                fontSize="lg"
              >
                Iniciar Sesión Ahora
              </MotionButton>
            </VStack>
          </MotionBox>
        </Container>
      </Box>

      {/* Footer */}
      <Box
        bg="gray.900"
        color="white"
        py={8}
        w="full"
      >
        <Container maxW="container.xl" px={4}>
          <Flex
            justify="space-between"
            align="center"
            flexWrap="wrap"
            gap={4}
          >
            <Text>© 2025 ERP System. Todos los derechos reservados.</Text>
            <HStack spacing={6}>
              <Text cursor="pointer" _hover={{ color: "blue.300" }}>
                Términos
              </Text>
              <Text cursor="pointer" _hover={{ color: "blue.300" }}>
                Privacidad
              </Text>
              <Text cursor="pointer" _hover={{ color: "blue.300" }}>
                Soporte
              </Text>
            </HStack>
          </Flex>
        </Container>
      </Box>
    </AuroraBackground>
  );
};

export default LandingPage;

