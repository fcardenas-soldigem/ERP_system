import React from 'react';
import { Box } from '@chakra-ui/react';
import Navbar from './Navbar';
import Sidebar from './Sidebar';
import ChatBar from '../AIAssistant/ChatBar';

const MainLayout = ({ children }) => {
    return (
        <Box minH="100vh">
            <Navbar />
            <Sidebar />
            <Box ml={{ base: 0, md: 60 }} p="4">
                {children}
            </Box>
            <ChatBar />
        </Box>
    );
};

export default MainLayout; 