import React, { useState, useEffect, useRef } from 'react';
import {
    Box,
    IconButton,
    Drawer,
    DrawerBody,
    DrawerHeader,
    DrawerOverlay,
    DrawerContent,
    DrawerCloseButton,
    useDisclosure,
    VStack,
    HStack,
    Input,
    Text,
    Badge,
    useColorModeValue,
    Button,
    useToast,
    Spinner,
    Divider
} from '@chakra-ui/react';
import { ChatIcon, AttachmentIcon, ArrowUpIcon, AddIcon, DeleteIcon } from '@chakra-ui/icons';
import { aiService } from '../../services/ai.service';

const ChatBar = ({ onSelectConversation, selectedConversationId }) => {
    const { isOpen, onOpen, onClose } = useDisclosure();
    const [messages, setMessages] = useState([]);
    const [newMessage, setNewMessage] = useState('');
    const [conversationId, setConversationId] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const fileInputRef = useRef();
    const messagesEndRef = useRef();
    const toast = useToast();
    const [conversations, setConversations] = useState([]);
    
    const bgColor = useColorModeValue('gray.50', 'gray.700');
    const borderColor = useColorModeValue('gray.200', 'gray.600');
    const hoverBgColor = useColorModeValue('gray.100', 'gray.600');
    const selectedBgColor = useColorModeValue('blue.100', 'blue.700');

    useEffect(() => {
        if (isOpen && !conversationId) {
            initializeChat();
        }
    }, [isOpen]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        loadConversations();
    }, []);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const initializeChat = async () => {
        try {
            setIsLoading(true);
            const conversation = await aiService.createConversation();
            setConversationId(conversation.data.id);
            const initialMessages = await aiService.getMessages(conversation.data.id);
            setMessages(initialMessages);
        } catch (error) {
            toast({
                title: 'Error',
                description: 'No se pudo inicializar el chat',
                status: 'error',
                duration: 3000,
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleSendMessage = async () => {
        if (!newMessage.trim() || !conversationId) return;

        try {
            setIsLoading(true);
            await aiService.sendMessage(conversationId, newMessage);
            const updatedMessages = await aiService.getMessages(conversationId);
            setMessages(updatedMessages);
            setNewMessage('');
        } catch (error) {
            toast({
                title: 'Error',
                description: 'No se pudo enviar el mensaje',
                status: 'error',
                duration: 3000,
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file || !conversationId) return;

        try {
            setIsLoading(true);
            const tipo = file.name.toLowerCase().includes('compra') ? 'compra' : 'venta';
            await aiService.uploadFile(conversationId, file, tipo);
            const updatedMessages = await aiService.getMessages(conversationId);
            setMessages(updatedMessages);
        } catch (error) {
            toast({
                title: 'Error',
                description: error.response?.data?.error || 'Error al procesar el archivo',
                status: 'error',
                duration: 5000,
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            handleSendMessage();
        }
    };

    const loadConversations = async () => {
        try {
            const response = await aiService.getConversations();
            setConversations(response.data);
            
            // Si no hay conversación seleccionada y hay conversaciones, seleccionar la primera
            if (!selectedConversationId && response.data.length > 0) {
                onSelectConversation(response.data[0].id);
            }
        } catch (error) {
            toast({
                title: 'Error al cargar conversaciones',
                description: error.message,
                status: 'error',
                duration: 3000,
            });
        }
    };

    const handleNewConversation = async () => {
        try {
            const response = await aiService.createConversation();
            setConversations(prev => [...prev, response.data]);
            onSelectConversation(response.data.id);
        } catch (error) {
            toast({
                title: 'Error al crear conversación',
                description: error.message,
                status: 'error',
                duration: 3000,
            });
        }
    };

    const handleDeleteConversation = async (id, event) => {
        event.stopPropagation();
        try {
            await aiService.deleteConversation(id);
            setConversations(prev => prev.filter(conv => conv.id !== id));
            
            // Si la conversación eliminada era la seleccionada, seleccionar otra
            if (id === selectedConversationId) {
                const remainingConversations = conversations.filter(conv => conv.id !== id);
                if (remainingConversations.length > 0) {
                    onSelectConversation(remainingConversations[0].id);
                } else {
                    onSelectConversation(null);
                }
            }
        } catch (error) {
            toast({
                title: 'Error al eliminar conversación',
                description: error.message,
                status: 'error',
                duration: 3000,
            });
        }
    };

    return (
        <>
            {/* Botón flotante del chat */}
            <Box
                position="fixed"
                bottom="4"
                right="4"
                zIndex="999"
            >
                <IconButton
                    icon={<ChatIcon />}
                    onClick={onOpen}
                    colorScheme="blue"
                    size="lg"
                    rounded="full"
                    shadow="lg"
                    aria-label="Abrir chat"
                    _hover={{
                        transform: 'scale(1.1)',
                    }}
                    transition="all 0.2s"
                />
            </Box>

            {/* Drawer del chat */}
            <Drawer
                isOpen={isOpen}
                placement="right"
                onClose={onClose}
                size="md"
            >
                <DrawerOverlay />
                <DrawerContent bg={bgColor}>
                    <DrawerCloseButton />
                    <DrawerHeader 
                        borderBottomWidth="1px" 
                        borderColor={borderColor}
                        bg={useColorModeValue('blue.50', 'blue.900')}
                    >
                        <HStack>
                            <ChatIcon />
                            <Text>Asistente AI</Text>
                        </HStack>
                    </DrawerHeader>

                    <DrawerBody p={0}>
                        {/* Área de mensajes */}
                        <VStack 
                            spacing={4} 
                            p={4} 
                            overflowY="auto" 
                            height="calc(100vh - 180px)"
                            align="stretch"
                        >
                            {messages.map((message) => (
                                <Box
                                    key={message.id}
                                    alignSelf={message.is_from_assistant ? 'flex-start' : 'flex-end'}
                                    maxW="70%"
                                >
                                    <HStack spacing={2} mb={1}>
                                        <Badge colorScheme={message.is_from_assistant ? 'blue' : 'green'}>
                                            {message.is_from_assistant ? 'Asistente' : 'Tú'}
                                        </Badge>
                                        <Text fontSize="xs" color="gray.500">
                                            {new Date(message.created_at).toLocaleTimeString()}
                                        </Text>
                                    </HStack>
                                    <Box
                                        p={3}
                                        bg={message.is_from_assistant ? 'blue.50' : 'green.50'}
                                        borderRadius="lg"
                                        borderWidth={1}
                                        borderColor={borderColor}
                                    >
                                        <Text whiteSpace="pre-wrap">{message.content}</Text>
                                    </Box>
                                </Box>
                            ))}
                            <div ref={messagesEndRef} />
                        </VStack>

                        {/* Área de entrada de mensaje */}
                        <Box
                            p={4}
                            borderTopWidth="1px"
                            borderColor={borderColor}
                            bg={bgColor}
                        >
                            <HStack spacing={2}>
                                <Input
                                    value={newMessage}
                                    onChange={(e) => setNewMessage(e.target.value)}
                                    onKeyPress={handleKeyPress}
                                    placeholder="Escribe un mensaje..."
                                    disabled={isLoading}
                                />
                                <IconButton
                                    icon={<AttachmentIcon />}
                                    onClick={() => fileInputRef.current.click()}
                                    disabled={isLoading}
                                    aria-label="Adjuntar archivo"
                                />
                                <IconButton
                                    icon={isLoading ? <Spinner /> : <ArrowUpIcon />}
                                    onClick={handleSendMessage}
                                    disabled={isLoading || !newMessage.trim()}
                                    colorScheme="blue"
                                    aria-label="Enviar mensaje"
                                />
                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    onChange={handleFileUpload}
                                    accept=".xlsx,.csv"
                                    style={{ display: 'none' }}
                                />
                            </HStack>
                        </Box>
                    </DrawerBody>
                </DrawerContent>
            </Drawer>

            <Box
                w="300px"
                h="100%"
                borderRightWidth={1}
                p={4}
                bg={bgColor}
            >
                <VStack spacing={4} align="stretch">
                    <Button
                        leftIcon={<AddIcon />}
                        onClick={handleNewConversation}
                        colorScheme="blue"
                        size="sm"
                    >
                        Nueva Conversación
                    </Button>
                    
                    <Divider />
                    
                    <VStack spacing={2} align="stretch" overflowY="auto">
                        {conversations.map((conversation) => (
                            <HStack
                                key={conversation.id}
                                p={2}
                                borderRadius="md"
                                cursor="pointer"
                                bg={conversation.id === selectedConversationId ? selectedBgColor : 'transparent'}
                                _hover={{ bg: conversation.id === selectedConversationId ? selectedBgColor : hoverBgColor }}
                                onClick={() => onSelectConversation(conversation.id)}
                            >
                                <Text flex="1" isTruncated>
                                    {new Date(conversation.created_at).toLocaleDateString()} - 
                                    {new Date(conversation.created_at).toLocaleTimeString()}
                                </Text>
                                <IconButton
                                    icon={<DeleteIcon />}
                                    size="sm"
                                    variant="ghost"
                                    colorScheme="red"
                                    onClick={(e) => handleDeleteConversation(conversation.id, e)}
                                />
                            </HStack>
                        ))}
                    </VStack>
                </VStack>
            </Box>
        </>
    );
};

export default ChatBar; 