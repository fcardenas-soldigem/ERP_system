import React from 'react';
import {
    Box,
    Flex,
    Text,
    Icon,
    HStack,
    VStack,
    Stat,
    StatLabel,
    StatNumber,
    StatHelpText,
    StatArrow,
    useColorModeValue,
    Tooltip
} from '@chakra-ui/react';
import { 
    FiTrendingUp, 
    FiTrendingDown, 
    FiAlertTriangle,
    FiPackage,
    FiDollarSign,
    FiShoppingCart,
    FiBox,
    FiActivity
} from 'react-icons/fi';

/**
 * Tarjeta de estadística moderna con gradientes y animaciones
 */
export const StatsCard = ({
    title,
    value,
    subtitle,
    icon,
    colorScheme = 'blue',
    trend = null,  // 'up' | 'down' | null
    trendValue = null,
    isLoading = false,
    helpText = null,
    onClick = null
}) => {
    const gradients = {
        blue: 'linear(to-r, blue.400, blue.600)',
        green: 'linear(to-r, green.400, green.600)',
        orange: 'linear(to-r, orange.400, orange.600)',
        purple: 'linear(to-r, purple.400, purple.600)',
        red: 'linear(to-r, red.400, red.600)',
        teal: 'linear(to-r, teal.400, teal.600)',
        cyan: 'linear(to-r, cyan.400, cyan.600)',
        pink: 'linear(to-r, pink.400, pink.600)'
    };

    const bgLight = {
        blue: 'blue.50',
        green: 'green.50',
        orange: 'orange.50',
        purple: 'purple.50',
        red: 'red.50',
        teal: 'teal.50',
        cyan: 'cyan.50',
        pink: 'pink.50'
    };

    return (
        <Tooltip label={helpText} isDisabled={!helpText} placement="top">
            <Box
                bg="white"
                borderRadius="xl"
                boxShadow="sm"
                p={5}
                position="relative"
                overflow="hidden"
                cursor={onClick ? 'pointer' : 'default'}
                onClick={onClick}
                transition="all 0.3s ease"
                _hover={{
                    transform: onClick ? 'translateY(-4px)' : 'none',
                    boxShadow: onClick ? 'lg' : 'sm',
                }}
                borderWidth="1px"
                borderColor="gray.100"
            >
                {/* Decorative gradient bar */}
                <Box
                    position="absolute"
                    top={0}
                    left={0}
                    right={0}
                    h="3px"
                    bgGradient={gradients[colorScheme] || gradients.blue}
                />

                <Flex justify="space-between" align="flex-start">
                    <VStack align="start" spacing={1}>
                        <Text 
                            fontSize="sm" 
                            color="gray.500" 
                            fontWeight="medium"
                            textTransform="uppercase"
                            letterSpacing="wide"
                        >
                            {title}
                        </Text>
                        <Text 
                            fontSize="2xl" 
                            fontWeight="bold" 
                            color="gray.800"
                            lineHeight="shorter"
                        >
                            {value}
                        </Text>
                        {subtitle && (
                            <Text fontSize="xs" color="gray.500">
                                {subtitle}
                            </Text>
                        )}
                        {trend && trendValue && (
                            <HStack spacing={1} mt={1}>
                                <Icon 
                                    as={trend === 'up' ? FiTrendingUp : FiTrendingDown} 
                                    color={trend === 'up' ? 'green.500' : 'red.500'}
                                    boxSize={4}
                                />
                                <Text 
                                    fontSize="xs" 
                                    color={trend === 'up' ? 'green.500' : 'red.500'}
                                    fontWeight="medium"
                                >
                                    {trendValue}
                                </Text>
                            </HStack>
                        )}
                    </VStack>

                    {icon && (
                        <Flex
                            align="center"
                            justify="center"
                            w="48px"
                            h="48px"
                            borderRadius="lg"
                            bg={bgLight[colorScheme] || bgLight.blue}
                        >
                            <Icon 
                                as={icon} 
                                boxSize={6} 
                                color={`${colorScheme}.500`}
                            />
                        </Flex>
                    )}
                </Flex>
            </Box>
        </Tooltip>
    );
};

/**
 * Tarjeta de estadística compacta
 */
export const MiniStatsCard = ({
    title,
    value,
    icon,
    colorScheme = 'blue',
    isAlert = false
}) => (
    <Flex
        align="center"
        bg="white"
        p={3}
        borderRadius="lg"
        boxShadow="sm"
        borderWidth="1px"
        borderColor={isAlert ? `${colorScheme}.200` : 'gray.100'}
        gap={3}
    >
        <Flex
            align="center"
            justify="center"
            w="36px"
            h="36px"
            borderRadius="md"
            bg={isAlert ? `${colorScheme}.100` : `${colorScheme}.50`}
        >
            <Icon 
                as={icon} 
                boxSize={5} 
                color={`${colorScheme}.500`}
            />
        </Flex>
        <VStack align="start" spacing={0}>
            <Text fontSize="xs" color="gray.500" fontWeight="medium">
                {title}
            </Text>
            <Text fontSize="lg" fontWeight="bold" color="gray.800">
                {value}
            </Text>
        </VStack>
    </Flex>
);

/**
 * Tarjeta de alerta/notificación
 */
export const AlertCard = ({
    title,
    message,
    type = 'warning',  // 'warning' | 'error' | 'info' | 'success'
    icon,
    action = null,
    onAction = null
}) => {
    const typeConfig = {
        warning: { bg: 'orange.50', border: 'orange.200', icon: FiAlertTriangle, color: 'orange.600' },
        error: { bg: 'red.50', border: 'red.200', icon: FiAlertTriangle, color: 'red.600' },
        info: { bg: 'blue.50', border: 'blue.200', icon: FiActivity, color: 'blue.600' },
        success: { bg: 'green.50', border: 'green.200', icon: FiTrendingUp, color: 'green.600' }
    };

    const config = typeConfig[type] || typeConfig.warning;

    return (
        <Box
            bg={config.bg}
            borderWidth="1px"
            borderColor={config.border}
            borderRadius="lg"
            p={4}
        >
            <Flex align="start" gap={3}>
                <Icon 
                    as={icon || config.icon} 
                    boxSize={5} 
                    color={config.color}
                    mt={0.5}
                />
                <VStack align="start" spacing={1} flex={1}>
                    <Text fontWeight="semibold" color={config.color} fontSize="sm">
                        {title}
                    </Text>
                    <Text fontSize="sm" color="gray.600">
                        {message}
                    </Text>
                    {action && onAction && (
                        <Text 
                            fontSize="sm" 
                            color={config.color}
                            cursor="pointer"
                            fontWeight="medium"
                            onClick={onAction}
                            _hover={{ textDecoration: 'underline' }}
                        >
                            {action} →
                        </Text>
                    )}
                </VStack>
            </Flex>
        </Box>
    );
};

/**
 * Contenedor de estadísticas en grid
 */
export const StatsGrid = ({ children, columns = { base: 1, md: 2, lg: 4 }, spacing = 4 }) => (
    <Box
        display="grid"
        gridTemplateColumns={{
            base: 'repeat(1, 1fr)',
            md: `repeat(${columns.md || 2}, 1fr)`,
            lg: `repeat(${columns.lg || 4}, 1fr)`
        }}
        gap={spacing}
    >
        {children}
    </Box>
);

export default {
    StatsCard,
    MiniStatsCard,
    AlertCard,
    StatsGrid
};
