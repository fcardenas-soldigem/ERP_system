import React, { createContext, useState, useContext, useEffect } from 'react';
import { authService } from '../../services/auth.service';
import { useToast } from '@chakra-ui/react';
import { useNavigate } from 'react-router-dom';
import AppLoading from '../common/AppLoading';

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const toast = useToast();
    const navigate = useNavigate();

    const checkAuth = async () => {
        try {
            // Attempt a silent token refresh using the httpOnly cookie.
            // If the cookie is present and valid, we get a fresh access token in memory.
            const accessToken = await authService.refreshToken();
            if (accessToken) {
                const userData = await authService.getProfile();
                setUser(userData);
                setIsAuthenticated(true);

                if (userData.empresa_info?.id && !localStorage.getItem('empresa_id')) {
                    localStorage.setItem('empresa_id', userData.empresa_info.id.toString());
                }
            }
        } catch {
            setUser(null);
            setIsAuthenticated(false);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        checkAuth();
    }, []);

    const handleLogin = async (credentials) => {
        try {
            const response = await authService.login(credentials);
            const userData = response.data.user;
            setUser(userData);
            setIsAuthenticated(true);
            
            toast({
                title: '¡Bienvenido!',
                description: 'Has iniciado sesión exitosamente.',
                status: 'success',
                duration: 3000,
                isClosable: true,
            });

            // Redirigir al dashboard después de un login exitoso
            navigate('/app/dashboard');
            return true;
        } catch (error) {
            console.error('Error de login:', error);
            toast({
                title: 'Error de inicio de sesión',
                description: error.response?.data?.detail || 'Credenciales inválidas',
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
            throw error;
        }
    };

    const handleLogout = () => {
        authService.logout();
        setUser(null);
        setIsAuthenticated(false);
        navigate('/login');
    };

    const value = {
        isAuthenticated,
        user,
        loading,
        login: handleLogin,
        logout: handleLogout,
    };

    if (loading) {
        return <AppLoading />;
    }

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth debe ser usado dentro de un AuthProvider');
    }
    return context;
};