import React from 'react';
import {
    Box,
    Skeleton,
    SkeletonText,
    SkeletonCircle,
    SimpleGrid,
    VStack,
    HStack,
    Card,
    CardBody,
    Flex,
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td
} from '@chakra-ui/react';

/**
 * Skeleton loader para una tarjeta de estadística
 */
export const StatCardSkeleton = ({ count = 4 }) => (
    <SimpleGrid columns={{ base: 1, md: 2, lg: count }} spacing={4}>
        {Array.from({ length: count }).map((_, i) => (
            <Card key={i}>
                <CardBody>
                    <VStack align="start" spacing={3}>
                        <Skeleton height="14px" width="60%" />
                        <Skeleton height="32px" width="40%" />
                        <Skeleton height="12px" width="80%" />
                    </VStack>
                </CardBody>
            </Card>
        ))}
    </SimpleGrid>
);

/**
 * Skeleton loader para una tabla
 */
export const TableSkeleton = ({ rows = 5, columns = 6 }) => (
    <Box overflowX="auto">
        <Table>
            <Thead>
                <Tr>
                    {Array.from({ length: columns }).map((_, i) => (
                        <Th key={i}>
                            <Skeleton height="14px" width="80px" />
                        </Th>
                    ))}
                </Tr>
            </Thead>
            <Tbody>
                {Array.from({ length: rows }).map((_, rowIndex) => (
                    <Tr key={rowIndex}>
                        {Array.from({ length: columns }).map((_, colIndex) => (
                            <Td key={colIndex}>
                                <Skeleton 
                                    height="16px" 
                                    width={colIndex === 0 ? "120px" : "60px"} 
                                />
                            </Td>
                        ))}
                    </Tr>
                ))}
            </Tbody>
        </Table>
    </Box>
);

/**
 * Skeleton loader para lista de items
 */
export const ListSkeleton = ({ items = 5, showAvatar = false }) => (
    <VStack spacing={3} align="stretch">
        {Array.from({ length: items }).map((_, i) => (
            <HStack key={i} p={3} bg="gray.50" borderRadius="md">
                {showAvatar && <SkeletonCircle size="10" />}
                <VStack flex={1} align="start" spacing={2}>
                    <Skeleton height="14px" width="70%" />
                    <Skeleton height="12px" width="50%" />
                </VStack>
                <Skeleton height="24px" width="60px" borderRadius="md" />
            </HStack>
        ))}
    </VStack>
);

/**
 * Skeleton loader para un dashboard completo
 */
export const DashboardSkeleton = () => (
    <VStack spacing={6} align="stretch">
        {/* Header */}
        <HStack justify="space-between">
            <VStack align="start" spacing={2}>
                <Skeleton height="28px" width="200px" />
                <Skeleton height="16px" width="300px" />
            </VStack>
            <Skeleton height="36px" width="120px" borderRadius="md" />
        </HStack>

        {/* Stats */}
        <StatCardSkeleton count={4} />

        {/* Content area */}
        <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
            <Card>
                <CardBody>
                    <Skeleton height="20px" width="150px" mb={4} />
                    <ListSkeleton items={3} />
                </CardBody>
            </Card>
            <Card>
                <CardBody>
                    <Skeleton height="20px" width="150px" mb={4} />
                    <ListSkeleton items={3} />
                </CardBody>
            </Card>
        </SimpleGrid>

        {/* Table */}
        <Card>
            <CardBody>
                <Skeleton height="20px" width="200px" mb={4} />
                <TableSkeleton rows={5} columns={5} />
            </CardBody>
        </Card>
    </VStack>
);

/**
 * Skeleton loader para formulario
 */
export const FormSkeleton = ({ fields = 4 }) => (
    <VStack spacing={4} align="stretch">
        {Array.from({ length: fields }).map((_, i) => (
            <Box key={i}>
                <Skeleton height="16px" width="100px" mb={2} />
                <Skeleton height="40px" width="100%" borderRadius="md" />
            </Box>
        ))}
        <Skeleton height="40px" width="120px" borderRadius="md" alignSelf="flex-end" />
    </VStack>
);

/**
 * Skeleton para card de inventario
 */
export const InventoryCardSkeleton = () => (
    <Card>
        <CardBody>
            <HStack justify="space-between" mb={4}>
                <HStack>
                    <SkeletonCircle size="10" />
                    <Skeleton height="20px" width="150px" />
                </HStack>
                <Skeleton height="30px" width="80px" borderRadius="md" />
            </HStack>
            <SimpleGrid columns={2} spacing={4}>
                {Array.from({ length: 4 }).map((_, i) => (
                    <Box key={i}>
                        <Skeleton height="14px" width="60px" mb={1} />
                        <Skeleton height="20px" width="80px" />
                    </Box>
                ))}
            </SimpleGrid>
        </CardBody>
    </Card>
);

/**
 * Componente de animación de entrada
 */
export const FadeInBox = ({ children, delay = 0, ...props }) => (
    <Box
        animation={`fadeIn 0.3s ease-out ${delay}s both`}
        sx={{
            '@keyframes fadeIn': {
                '0%': {
                    opacity: 0,
                    transform: 'translateY(10px)'
                },
                '100%': {
                    opacity: 1,
                    transform: 'translateY(0)'
                }
            }
        }}
        {...props}
    >
        {children}
    </Box>
);

/**
 * Componente de animación de escala
 */
export const ScaleInBox = ({ children, delay = 0, ...props }) => (
    <Box
        animation={`scaleIn 0.2s ease-out ${delay}s both`}
        sx={{
            '@keyframes scaleIn': {
                '0%': {
                    opacity: 0,
                    transform: 'scale(0.95)'
                },
                '100%': {
                    opacity: 1,
                    transform: 'scale(1)'
                }
            }
        }}
        {...props}
    >
        {children}
    </Box>
);

export default {
    StatCardSkeleton,
    TableSkeleton,
    ListSkeleton,
    DashboardSkeleton,
    FormSkeleton,
    InventoryCardSkeleton,
    FadeInBox,
    ScaleInBox
};
