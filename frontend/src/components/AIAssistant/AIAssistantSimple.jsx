import React, { useState, useEffect, useRef } from 'react';
import { Box, VStack, Input, Button, Text, Flex, useToast, HStack, Badge, IconButton } from '@chakra-ui/react';
import { AddIcon, RepeatIcon } from '@chakra-ui/icons';
import { aiService } from '../../services/ai.service';

const AIAssistantSimple = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [threadId, setThreadId] = useState(null);
    const [conversationId, setConversationId] = useState(null);
    const [conversationTitle, setConversationTitle] = useState('');
    const [initialized, setInitialized] = useState(false);
    const [isExistingConversation, setIsExistingConversation] = useState(false);
    const [isLoadingMessages, setIsLoadingMessages] = useState(false);
    const toast = useToast();
    const messagesEndRef = useRef(null);

    // Auto-scroll to bottom when messages change
    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    // Inicializar solo una vez
    useEffect(() => {
        if (!initialized) {
            console.log('🚀 Inicializando componente...');
            initializeChat();
            setInitialized(true);
        }
    }, [initialized]);

    const initializeChat = async () => {
        try {
            console.log('📡 Obteniendo o creando conversación activa CON TOOLS...');
            setIsLoadingMessages(true);
            
            const result = await aiService.getOrCreateActiveConversationWithTools();
            console.log('✅ Result:', result);
            
            if (result.conversation) {
                setConversationId(result.conversation.id);
                setThreadId(result.conversation.thread_id);
                setConversationTitle(result.conversation.title || 'Conversación con Jorge');
                setIsExistingConversation(result.isExisting);
                
                console.log('✅ Conversación configurada:', {
                    id: result.conversation.id,
                    threadId: result.conversation.thread_id,
                    isExisting: result.isExisting
                });
            }
            
            if (result.messages && result.messages.length > 0) {
                // Convertir mensajes al formato esperado
                const formattedMessages = result.messages.map(msg => ({
                    role: msg.role,
                    content: msg.content
                }));
                setMessages(formattedMessages);
                console.log('✅ Mensajes cargados:', formattedMessages.length);
                
                if (result.isExisting) {
                    toast({
                        title: '📖 Conversación Cargada',
                        description: `Se cargaron ${formattedMessages.length} mensajes de tu conversación anterior`,
                        status: 'info',
                        duration: 3000,
                        isClosable: true,
                    });
                }
            }
            
        } catch (error) {
            console.error('❌ Error inicializando chat:', error);
            
            // Si hay error, intentar crear una nueva conversación
            try {
                console.log('🔄 Intentando crear nueva conversación...');
                await createNewConversation();
            } catch (secondError) {
                console.error('❌ Error creando nueva conversación:', secondError);
                toast({
                    title: 'Error',
                    description: 'No se pudo inicializar el chat con Jorge',
                    status: 'error',
                    duration: 5000,
                    isClosable: true,
                });
            }
        } finally {
            setIsLoadingMessages(false);
        }
    };

    const createNewConversation = async () => {
        try {
            console.log('🆕 Creando nueva conversación CON TOOLS...');
            setIsLoadingMessages(true);
            
            const response = await aiService.createNewConversationWithTools();
            console.log('✅ Nueva conversación creada:', response);
            
            if (response.thread_id) {
                setThreadId(response.thread_id);
                setConversationId(response.conversation_id);
                setConversationTitle('Conversación con Jorge');
                setIsExistingConversation(false);
                console.log('✅ Nueva conversación configurada');
            }
            
            if (response.message) {
                setMessages([{ role: 'assistant', content: response.message }]);
                console.log('✅ Mensaje inicial agregado');
            }
            
            toast({
                title: '🆕 Nueva Conversación',
                description: 'Se ha creado una nueva conversación con Jorge',
                status: 'success',
                duration: 2000,
                isClosable: true,
            });
            
        } catch (error) {
            console.error('❌ Error creando nueva conversación:', error);
            toast({
                title: 'Error',
                description: 'No se pudo crear una nueva conversación',
                status: 'error',
                duration: 3000,
                isClosable: true,
            });
        } finally {
            setIsLoadingMessages(false);
        }
    };

    const sendMessage = async () => {
        if (!input.trim() || !threadId || isLoading) {
            console.log('❌ Validación falló:', { input: input.trim(), threadId, isLoading });
            return;
        }

        const userMessage = input;
        console.log('📤 Enviando CON TOOLS:', userMessage);
        
        // Limpiar input y mostrar mensaje del usuario
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setIsLoading(true);

        try {
            console.log('📡 Llamando sendMessageWithTools...');
            const response = await aiService.sendMessageWithTools(threadId, userMessage);
            console.log('📨 Respuesta:', response);

            if (response.message) {
                setMessages(prev => [...prev, { role: 'assistant', content: response.message }]);
                console.log('✅ Mensaje del asistente agregado');
            }
        } catch (error) {
            console.error('❌ Error enviando mensaje:', error);
            toast({
                title: 'Error',
                description: 'No se pudo enviar el mensaje',
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
            console.log('⌨️ Enter presionado');
            sendMessage();
        }
    };

    const handleButtonClick = () => {
        console.log('🖱️ Botón clickeado');
        sendMessage();
    };

    console.log('🎨 Render - messages:', messages.length, 'threadId:', !!threadId);

    return (
        <Box h="100vh" p={4}>
            <VStack h="full" spacing={4}>
                {/* Header con título y controles */}
                <HStack w="full" justify="space-between" align="center">
                    <HStack>
                        <Text fontSize="xl" fontWeight="bold" color="blue.600">
                            🤖 Jorge - Asistente ERP
                        </Text>
                        {isExistingConversation && (
                            <Badge colorScheme="green" fontSize="sm">
                                📖 Conversación Continuada
                            </Badge>
                        )}
                    </HStack>
                    
                    <HStack spacing={2}>
                        <IconButton
                            icon={<AddIcon />}
                            size="sm"
                            colorScheme="blue"
                            variant="outline"
                            onClick={createNewConversation}
                            isLoading={isLoadingMessages}
                            title="Nueva Conversación"
                        />
                        <IconButton
                            icon={<RepeatIcon />}
                            size="sm"
                            colorScheme="gray"
                            variant="outline"
                            onClick={() => {
                                setInitialized(false);
                                setMessages([]);
                                setThreadId(null);
                                setConversationId(null);
                            }}
                            title="Recargar"
                        />
                    </HStack>
                </HStack>

                {/* Área de chat */}
                <Box 
                    flex="1" 
                    w="full" 
                    overflowY="auto" 
                    borderWidth={2} 
                    borderColor="blue.200"
                    borderRadius="md" 
                    p={4}
                    bg="gray.50"
                >
                    {isLoadingMessages ? (
                        <Flex justify="center" align="center" h="100%">
                            <VStack>
                                <Text color="gray.500">Cargando conversación...</Text>
                                <Text fontSize="sm" color="gray.400">
                                    {isExistingConversation ? 'Recuperando mensajes anteriores' : 'Iniciando nueva conversación'}
                                </Text>
                            </VStack>
                        </Flex>
                    ) : messages.length === 0 ? (
                        <Text textAlign="center" color="gray.500">
                            {threadId ? 'Listo para chatear...' : 'Inicializando...'}
                        </Text>
                    ) : (
                        <>
                            {messages.map((message, index) => (
                                <Flex
                                    key={index}
                                    justify={message.role === 'user' ? 'flex-end' : 'flex-start'}
                                    mb={4}
                                >
                                    <Box
                                        maxW="80%"
                                        bg={message.role === 'user' ? 'blue.500' : 'white'}
                                        color={message.role === 'user' ? 'white' : 'black'}
                                        p={3}
                                        borderRadius="lg"
                                        boxShadow="md"
                                        borderWidth={message.role === 'assistant' ? 1 : 0}
                                        borderColor="gray.200"
                                    >
                                        <Text whiteSpace="pre-wrap">{message.content}</Text>
                                    </Box>
                                </Flex>
                            ))}
                            <div ref={messagesEndRef} />
                        </>
                    )}

                    {isLoading && (
                        <Flex justify="flex-start" mb={4}>
                            <Box
                                bg="yellow.100"
                                p={3}
                                borderRadius="lg"
                                borderWidth={1}
                                borderColor="yellow.300"
                            >
                                <Text color="yellow.800">Jorge está escribiendo...</Text>
                            </Box>
                        </Flex>
                    )}
                </Box>

                {/* Input area */}
                <HStack w="full" spacing={2}>
                    <Input
                        flex="1"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Escribe tu mensaje aquí... (Enter para enviar)"
                        onKeyPress={handleKeyPress}
                        disabled={isLoading || !threadId || isLoadingMessages}
                        bg="white"
                        borderWidth={2}
                        _focus={{ borderColor: 'blue.400' }}
                    />
                    <Button
                        colorScheme="blue"
                        onClick={handleButtonClick}
                        isLoading={isLoading}
                        disabled={!input.trim() || !threadId || isLoadingMessages}
                        loadingText="Enviando..."
                        px={6}
                    >
                        Enviar
                    </Button>
                </HStack>

                {/* Status */}
                <HStack spacing={4} fontSize="sm" color="gray.500">
                    <Text>Conversación: {conversationId || 'N/A'}</Text>
                    <Text>Mensajes: {messages.length}</Text>
                    <Text>Estado: {isLoadingMessages ? '⏳ Cargando' : threadId ? '✅ Conectado' : '❌ Desconectado'}</Text>
                </HStack>
            </VStack>
        </Box>
    );
};

export default AIAssistantSimple; 