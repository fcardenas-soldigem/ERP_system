import React, { useState, useEffect, useRef } from 'react';
import { Box, VStack, Input, Button, Text, Flex, useToast, HStack, IconButton } from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';
import { aiService } from '../../services/ai.service';

const AIAssistant = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [threadId, setThreadId] = useState(null);
    const [isInitialized, setIsInitialized] = useState(false);
    const initializingRef = useRef(false);
    const messagesEndRef = useRef(null);
    const toast = useToast();

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        console.log('🔄 useEffect - initializeThread ejecutándose');
        console.log('🔄 isInitialized:', isInitialized);
        console.log('🔄 initializingRef.current:', initializingRef.current);
        
        if (!isInitialized && !initializingRef.current) {
            console.log('✅ Iniciando thread por primera vez');
            initializingRef.current = true;
            initializeThread();
        }
    }, []);

    useEffect(() => {
        console.log('🔄 useEffect - messages cambiaron:', messages);
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        console.log('🔄 useEffect - threadId cambió:', threadId);
    }, [threadId]);

    const initializeThread = async () => {
        try {
            console.log('🚀 Inicializando thread...');
            const response = await aiService.createThread();
            console.log('✅ Thread creado:', response);
            
            console.log('🔧 Actualizando estados...');
            console.log('🔧 setThreadId:', response.thread_id);
            setThreadId(response.thread_id);
            
            if (response.message) {
                console.log('🔧 setMessages con mensaje:', response.message);
                setMessages([{ role: 'assistant', content: response.message }]);
            } else {
                console.log('❌ No hay mensaje en la respuesta');
            }
            
            setIsInitialized(true);
            console.log('✅ Estados actualizados');
        } catch (error) {
            console.error('❌ Error initializing thread:', error);
            initializingRef.current = false; // Reset para permitir reintentos
            toast({
                title: 'Error',
                description: error.response?.data?.error || 'No se pudo inicializar el asistente',
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        }
    };

    const handleSendMessage = async () => {
        console.log('🔵 handleSendMessage llamado');
        console.log('🔵 input:', input);
        console.log('🔵 threadId:', threadId);
        console.log('🔵 isLoading:', isLoading);
        
        if (!input.trim()) {
            console.log('❌ Input vacío');
            return;
        }
        
        if (!threadId) {
            console.log('❌ No hay threadId');
            return;
        }
        
        if (isLoading) {
            console.log('❌ Ya está cargando');
            return;
        }

        const userMessage = input;
        console.log('✅ Enviando mensaje:', userMessage);
        setInput('');
        setIsLoading(true);

        try {
            // Agregar mensaje del usuario inmediatamente
            console.log('📝 Agregando mensaje del usuario');
            setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

            // Enviar mensaje al backend
            console.log('📡 Llamando aiService.sendMessage...');
            const response = await aiService.sendMessage(threadId, userMessage);
            console.log('📡 Respuesta recibida:', response);
            
            if (response.message) {
                console.log('✅ Agregando respuesta del asistente');
                setMessages(prev => [...prev, { role: 'assistant', content: response.message }]);
            } else {
                console.log('❌ No hay mensaje en la respuesta');
            }
        } catch (error) {
            console.error('❌ Error sending message:', error);
            toast({
                title: 'Error',
                description: error.response?.data?.error || 'No se pudo enviar el mensaje',
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
        } finally {
            console.log('🔄 Finalizando, setIsLoading(false)');
            setIsLoading(false);
        }
    };

    console.log('🎨 Renderizando componente...');
    console.log('🎨 messages:', messages);
    console.log('🎨 threadId:', threadId);
    console.log('🎨 isInitialized:', isInitialized);

    const resetChat = () => {
        console.log('🔄 Reseteando chat...');
        setMessages([]);
        setThreadId(null);
        setIsInitialized(false);
        initializingRef.current = false;
        setInput('');
        setIsLoading(false);
    };

    return (
        <Box h="100vh" p={4}>
            <VStack h="full" spacing={4}>
                {/* Header con botón de reset */}
                <HStack w="full" justify="space-between">
                    <Text fontSize="lg" fontWeight="bold">Asistente Virtual ERP</Text>
                    <IconButton
                        icon={<RepeatIcon />}
                        aria-label="Reiniciar chat"
                        size="sm"
                        onClick={resetChat}
                        colorScheme="gray"
                        variant="outline"
                    />
                </HStack>
                <Box 
                    flex="1" 
                    w="full" 
                    overflowY="auto" 
                    borderWidth={1} 
                    borderRadius="md" 
                    p={4}
                >
                    {messages.length === 0 && (
                        <Text color="gray.500" textAlign="center">
                            {isInitialized ? 'No hay mensajes aún...' : 'Inicializando asistente...'}
                        </Text>
                    )}
                    {messages.map((message, index) => (
                        <Flex
                            key={index}
                            justify={message.role === 'user' ? 'flex-end' : 'flex-start'}
                            mb={4}
                        >
                            <Box
                                maxW="70%"
                                bg={message.role === 'user' ? 'blue.500' : 'gray.100'}
                                color={message.role === 'user' ? 'white' : 'black'}
                                p={3}
                                borderRadius="lg"
                            >
                                <Text>{message.content}</Text>
                            </Box>
                        </Flex>
                    ))}
                    {isLoading && (
                        <Flex justify="flex-start" mb={4}>
                            <Box
                                maxW="70%"
                                bg="gray.100"
                                p={3}
                                borderRadius="lg"
                            >
                                <Text color="gray.500">El asistente está escribiendo...</Text>
                            </Box>
                        </Flex>
                    )}
                    <div ref={messagesEndRef} />
                </Box>
                <Flex w="full">
                    <Input
                        flex="1"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Escribe tu mensaje... (Enter para enviar)"
                        onKeyPress={(e) => {
                            console.log('⌨️ Key pressed:', e.key);
                            if (e.key === 'Enter' && !e.shiftKey) {
                                console.log('✅ Enter detectado, llamando handleSendMessage');
                                e.preventDefault();
                                handleSendMessage();
                            }
                        }}
                        disabled={isLoading}
                        mr={2}
                    />
                    <Button
                        colorScheme="blue"
                        onClick={() => {
                            console.log('🖱️ Botón Enviar clickeado');
                            handleSendMessage();
                        }}
                        isLoading={isLoading}
                        disabled={!input.trim() || !threadId}
                        loadingText="Enviando..."
                    >
                        Enviar
                    </Button>
                </Flex>
            </VStack>
        </Box>
    );
};

export default AIAssistant; 