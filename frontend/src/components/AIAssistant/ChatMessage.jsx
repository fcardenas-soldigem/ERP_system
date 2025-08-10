import React from 'react';
import {
    Box,
    HStack,
    Text,
    Badge,
    useColorModeValue
} from '@chakra-ui/react';

const ChatMessage = ({ message }) => {
    const borderColor = useColorModeValue('gray.200', 'gray.600');

    return (
        <Box
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
    );
};

export default ChatMessage; 