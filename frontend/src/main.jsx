import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { QueryClientProvider } from '@tanstack/react-query';
import { ChakraProvider } from '@chakra-ui/react';
import { queryClient } from './lib/queryClient';

// Importar utilidad de debug para autenticación
import './utils/debugAuth.js';

// Configurar lockdown
if (typeof window !== 'undefined' && window.lockdown) {
  window.lockdown(lockdownOptions);
}

// Suprimir logs en producción
if (process.env.NODE_ENV === 'production') {
  console.log = () => {};
  console.warn = () => {};
  console.error = () => {};
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ChakraProvider>
        <App />
      </ChakraProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
