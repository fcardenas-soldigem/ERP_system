import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Input,
  Button,
  IconButton,
  Collapse,
  Badge,
  Avatar,
  Spinner,
  useToast,
  Divider,
  Tooltip,
} from '@chakra-ui/react';
import {
  FiMessageCircle,
  FiX,
  FiSend,
  FiMinus,
  FiMaximize2,
  FiShoppingCart,
} from 'react-icons/fi';
import { ventasAssistantService } from '../../services/ventas-assistant.service';

const VentasChatBar = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversation, setConversation] = useState(null);
  const [assistantStatus, setAssistantStatus] = useState('disconnected');
  const toast = useToast();
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const initializeConversation = async () => {
    try {
      setIsLoading(true);
      setAssistantStatus('connecting');
      
      console.log('🛒 Inicializando conversación de ventas...');
      const result = await ventasAssistantService.getOrCreateActiveConversation();
      
      setConversation(result.conversation);
      setMessages(result.messages);
      setAssistantStatus('connected');
      
      console.log('✅ Conversación de ventas inicializada:', result);
      
      if (!result.isExisting) {
        // Si es nueva, cargar mensajes después de un momento
        setTimeout(async () => {
          try {
            const messagesResult = await ventasAssistantService.getMessages(result.conversation.thread_id);
            setMessages(messagesResult.messages || []);
          } catch (error) {
            console.error('❌ Error cargando mensajes iniciales:', error);
          }
        }, 1000);
      }
      
    } catch (error) {
      console.error('❌ Error inicializando conversación:', error);
      setAssistantStatus('error');
      toast({
        title: 'Error de conexión',
        description: 'No se pudo conectar con el asistente de ventas',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const toggleChat = () => {
    if (!isOpen && !conversation) {
      initializeConversation();
    }
    setIsOpen(!isOpen);
    setIsMinimized(false);
  };

  const minimizeChat = () => {
    setIsMinimized(!isMinimized);
  };

  const sendMessage = async () => {
    if (!currentMessage.trim() || !conversation?.thread_id) return;

    const userMessage = currentMessage.trim();
    setCurrentMessage('');
    setIsLoading(true);

    // Agregar mensaje del usuario inmediatamente
    const newUserMessage = {
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, newUserMessage]);

    try {
      console.log('🛒 Enviando mensaje al asistente de ventas:', userMessage);
      const response = await ventasAssistantService.sendMessage(conversation.thread_id, userMessage);
      
      // Agregar respuesta del asistente
      const assistantMessage = {
        role: 'assistant',
        content: response.response,
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, assistantMessage]);
      
      console.log('✅ Respuesta recibida del asistente de ventas');
      
    } catch (error) {
      console.error('❌ Error enviando mensaje:', error);
      toast({
        title: 'Error enviando mensaje',
        description: 'No se pudo procesar tu solicitud',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const getStatusColor = () => {
    switch (assistantStatus) {
      case 'connected': return 'green';
      case 'connecting': return 'yellow';
      case 'error': return 'red';
      default: return 'gray';
    }
  };

  const getStatusText = () => {
    switch (assistantStatus) {
      case 'connected': return 'Conectado';
      case 'connecting': return 'Conectando...';
      case 'error': return 'Error';
      default: return 'Desconectado';
    }
  };

  return (
    <Box position="fixed" bottom="4" right="4" zIndex={1000}>
      {/* Botón flotante para abrir chat */}
      {!isOpen && (
        <Tooltip label="Asistente de Ventas" placement="left">
          <IconButton
            icon={<FiShoppingCart />}
            size="lg"
            colorScheme="blue"
            borderRadius="full"
            boxShadow="lg"
            onClick={toggleChat}
            position="relative"
          >
            <Badge
              position="absolute"
              top="-1"
              right="-1"
              colorScheme={getStatusColor()}
              borderRadius="full"
              boxSize="3"
            />
          </IconButton>
        </Tooltip>
      )}

      {/* Ventana de chat */}
      <Collapse in={isOpen} animateOpacity>
        <Box
          bg="white"
          border="1px solid"
          borderColor="gray.200"
          borderRadius="lg"
          boxShadow="xl"
          w="400px"
          h={isMinimized ? "60px" : "500px"}
          overflow="hidden"
          transition="height 0.2s"
        >
          {/* Header del chat */}
          <HStack
            p={3}
            bg="blue.500"
            color="white"
            justify="space-between"
            cursor={isMinimized ? "pointer" : "default"}
            onClick={isMinimized ? minimizeChat : undefined}
          >
            <HStack spacing={2}>
              <Avatar size="sm" name="Asistente Ventas" bg="blue.600" />
              <VStack spacing={0} align="start">
                <Text fontSize="sm" fontWeight="bold">
                  Asistente de Ventas
                </Text>
                <Text fontSize="xs" opacity={0.8}>
                  {getStatusText()}
                </Text>
              </VStack>
            </HStack>
            <HStack>
              <IconButton
                icon={isMinimized ? <FiMaximize2 /> : <FiMinus />}
                size="sm"
                variant="ghost"
                colorScheme="whiteAlpha"
                onClick={minimizeChat}
              />
              <IconButton
                icon={<FiX />}
                size="sm"
                variant="ghost"
                colorScheme="whiteAlpha"
                onClick={toggleChat}
              />
            </HStack>
          </HStack>

          {/* Contenido del chat */}
          {!isMinimized && (
            <>
              {/* Área de mensajes */}
              <VStack
                spacing={3}
                p={3}
                h="380px"
                overflowY="auto"
                align="stretch"
                bg="gray.50"
              >
                {messages.length === 0 && !isLoading && (
                  <Box textAlign="center" py={8}>
                    <Text color="gray.500" fontSize="sm">
                      ¡Hola! Soy tu asistente de ventas.
                      <br />
                      Puedo ayudarte a crear ventas y buscar información.
                    </Text>
                  </Box>
                )}

                {messages.map((message, index) => (
                  <Box
                    key={index}
                    alignSelf={message.role === 'user' ? 'flex-end' : 'flex-start'}
                    maxW="85%"
                  >
                    <Box
                      bg={message.role === 'user' ? 'blue.500' : 'white'}
                      color={message.role === 'user' ? 'white' : 'gray.800'}
                      px={3}
                      py={2}
                      borderRadius="lg"
                      borderBottomRightRadius={message.role === 'user' ? 'sm' : 'lg'}
                      borderBottomLeftRadius={message.role === 'assistant' ? 'sm' : 'lg'}
                      border={message.role === 'assistant' ? '1px solid' : 'none'}
                      borderColor="gray.200"
                      boxShadow="sm"
                    >
                      <Text fontSize="sm" whiteSpace="pre-wrap">
                        {message.content}
                      </Text>
                    </Box>
                  </Box>
                ))}

                {isLoading && (
                  <Box alignSelf="flex-start">
                    <Box
                      bg="white"
                      px={3}
                      py={2}
                      borderRadius="lg"
                      border="1px solid"
                      borderColor="gray.200"
                    >
                      <HStack spacing={2}>
                        <Spinner size="sm" color="blue.500" />
                        <Text fontSize="sm" color="gray.600">
                          Procesando...
                        </Text>
                      </HStack>
                    </Box>
                  </Box>
                )}

                <div ref={messagesEndRef} />
              </VStack>

              <Divider />

              {/* Input de mensaje */}
              <HStack p={3} bg="white">
                <Input
                  placeholder="Escribe tu mensaje..."
                  value={currentMessage}
                  onChange={(e) => setCurrentMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  disabled={isLoading || assistantStatus !== 'connected'}
                  size="sm"
                  bg="gray.50"
                  border="1px solid"
                  borderColor="gray.200"
                  _focus={{
                    borderColor: 'blue.500',
                    bg: 'white'
                  }}
                />
                <IconButton
                  icon={<FiSend />}
                  size="sm"
                  colorScheme="blue"
                  onClick={sendMessage}
                  disabled={!currentMessage.trim() || isLoading || assistantStatus !== 'connected'}
                />
              </HStack>
            </>
          )}
        </Box>
      </Collapse>
    </Box>
  );
};

export default VentasChatBar; 