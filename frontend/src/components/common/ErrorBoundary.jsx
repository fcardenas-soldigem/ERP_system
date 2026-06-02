import React from 'react';
import { Box, Button, Center, Heading, Text, VStack, Code } from '@chakra-ui/react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    // Log to console in development; swap for a real error service (Sentry, etc.) in prod
    if (import.meta.env.DEV) {
      console.error('ErrorBoundary caught:', error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) this.props.onReset();
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    const { error } = this.state;
    const isDev = import.meta.env.DEV;

    return (
      <Center minH={this.props.fullscreen ? '100vh' : '400px'} p={8}>
        <VStack spacing={6} maxW="480px" textAlign="center">
          <Box
            w={12}
            h={12}
            borderRadius="xl"
            bg="error.100"
            display="flex"
            alignItems="center"
            justifyContent="center"
            fontSize="2xl"
          >
            ⚠
          </Box>

          <VStack spacing={2}>
            <Heading size="md" color="neutral.800">
              Algo salió mal
            </Heading>
            <Text color="neutral.500" fontSize="sm">
              Ocurrió un error inesperado. Intenta recargar la página.
            </Text>
          </VStack>

          {isDev && error && (
            <Box
              w="100%"
              p={3}
              bg="neutral.100"
              borderRadius="md"
              textAlign="left"
              maxH="160px"
              overflowY="auto"
            >
              <Code
                fontSize="xs"
                color="error.600"
                display="block"
                whiteSpace="pre-wrap"
                wordBreak="break-all"
              >
                {error.toString()}
              </Code>
            </Box>
          )}

          <VStack spacing={3} w="100%">
            <Button
              colorScheme="primary"
              size="sm"
              onClick={this.handleReset}
            >
              Intentar de nuevo
            </Button>
            <Button
              variant="ghost"
              size="sm"
              color="neutral.500"
              onClick={() => window.location.reload()}
            >
              Recargar página
            </Button>
          </VStack>
        </VStack>
      </Center>
    );
  }
}

export default ErrorBoundary;
