import React, { useState, useRef, useEffect } from 'react';
import {
    Box,
    VStack,
    Input,
    IconButton,
    HStack,
    useToast,
    Text,
    Spinner,
} from '@chakra-ui/react';
import { AttachmentIcon, ArrowForwardIcon } from '@chakra-ui/icons';
import ChatMessage from './ChatMessage';
import { aiService } from '../../services/ai.service';

const Chat = ({ conversationId, onNewMessage }) => {
    const [messages, setMessages] = useState([]);
    const [newMessage, setNewMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const fileInputRef = useRef();
    const messagesEndRef = useRef();
    const toast = useToast();

    useEffect(() => {
        if (conversationId) {
            loadMessages();
        }
    }, [conversationId]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const loadMessages = async () => {
        try {
            const response = await aiService.getMessages(conversationId);
            setMessages(response.data);
        } catch (error) {
            toast({
                title: 'Error al cargar mensajes',
                description: error.message,
                status: 'error',
                duration: 3000,
            });
        }
    };

    const handleSendMessage = async () => {
        if (!newMessage.trim()) return;

        try {
            setIsLoading(true);
            const response = await aiService.sendMessage(conversationId, {
                content: newMessage,
                is_from_assistant: false,
            });
            
            setMessages(prev => [...prev, response.data]);
            setNewMessage('');
            onNewMessage && onNewMessage(response.data);
            
            // Esperar respuesta del asistente
            const assistantResponse = await aiService.getAssistantResponse(conversationId);
            setMessages(prev => [...prev, assistantResponse.data]);
            onNewMessage && onNewMessage(assistantResponse.data);
        } catch (error) {
            toast({
                title: 'Error al enviar mensaje',
                description: error.message,
                status: 'error',
                duration: 3000,
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        try {
            setIsLoading(true);
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await aiService.uploadFile(conversationId, formData);
            setMessages(prev => [...prev, response.data]);
            onNewMessage && onNewMessage(response.data);
            
            // Esperar respuesta del asistente
            const assistantResponse = await aiService.getAssistantResponse(conversationId);
            setMessages(prev => [...prev, assistantResponse.data]);
            onNewMessage && onNewMessage(assistantResponse.data);
        } catch (error) {
            toast({
                title: 'Error al subir archivo',
                description: error.message,
                status: 'error',
                duration: 3000,
            });
        } finally {
            setIsLoading(false);
        }
    };

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    return (
        <Box h="100%" display="flex" flexDirection="column">
            <VStack
                flex="1"
                spacing={4}
                overflowY="auto"
                p={4}
                alignItems="stretch"
            >
                {messages.map((message) => (
                    <ChatMessage key={message.id} message={message} />
                ))}
                <div ref={messagesEndRef} />
            </VStack>

            <Box p={4} borderTopWidth={1}>
                <HStack>
                    <Input
                        value={newMessage}
                        onChange={(e) => setNewMessage(e.target.value)}
                        placeholder="Escribe un mensaje..."
                        onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                        disabled={isLoading}
                    />
                    <IconButton
                        icon={<AttachmentIcon />}
                        onClick={() => fileInputRef.current.click()}
                        disabled={isLoading}
                    />
                    <IconButton
                        icon={isLoading ? <Spinner /> : <ArrowForwardIcon />}
                        onClick={handleSendMessage}
                        disabled={isLoading || !newMessage.trim()}
                        colorScheme="blue"
                    />
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileUpload}
                        style={{ display: 'none' }}
                    />
                </HStack>
            </Box>
        </Box>
    );
};

export default Chat; 