import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App.jsx';
import { AuthProvider } from './components/context/AuthContext.jsx';
import reportWebVitals from './reportWebVitals.js';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChakraProvider } from '@chakra-ui/react';
import lockdownOptions from './lockdown-config';

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

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000,
    },
  },
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ChakraProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ChakraProvider>
    </QueryClientProvider>
  </React.StrictMode>
);

reportWebVitals();