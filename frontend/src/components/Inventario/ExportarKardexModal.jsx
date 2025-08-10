import React, { useState } from 'react';
import {
    Modal,
    ModalOverlay,
    ModalContent,
    ModalHeader,
    ModalBody,
    ModalFooter,
    ModalCloseButton,
    Button,
    Select,
    VStack,
    FormControl,
    FormLabel,
    Input,
    useToast,
    Text,
    HStack
} from '@chakra-ui/react';
import { inventarioService } from '../../services/inventario.service';

const ExportarKardexModal = ({ isOpen, onClose, productos, almacenes }) => {
    const [filtros, setFiltros] = useState({
        producto_id: '',
        almacen_id: '',
        fecha_inicio: '',
        fecha_fin: ''
    });
    const [loading, setLoading] = useState(false);
    const toast = useToast();

    const handleInputChange = (field, value) => {
        setFiltros(prev => ({
            ...prev,
            [field]: value
        }));
    };

    const exportarKardex = async () => {
        if (!filtros.producto_id || !filtros.almacen_id) {
            toast({
                title: 'Campos requeridos',
                description: 'Debe seleccionar un producto y un almacén',
                status: 'warning',
                duration: 3000,
            });
            return;
        }

        setLoading(true);
        try {
            toast({
                title: 'Exportando...',
                description: 'Generando archivo Excel, por favor espere...',
                status: 'info',
                duration: 3000,
            });

            const response = await inventarioService.descargarKardex(filtros);
            
            // Crear el blob y enlace de descarga
            const blob = new Blob([response], {
                type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            });
            
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            
            // Obtener información del producto y almacén para el nombre del archivo
            const productoSeleccionado = productos.find(p => p.id == filtros.producto_id);
            const almacenSeleccionado = almacenes.find(a => a.id == filtros.almacen_id);
            
            const fechaActual = new Date().toISOString().slice(0, 10);
            const nombreProducto = productoSeleccionado ? productoSeleccionado.sku : 'producto';
            const nombreAlmacen = almacenSeleccionado ? almacenSeleccionado.nombre.replace(/\s+/g, '_') : 'almacen';
            
            let nombreArchivo = `Kardex_${nombreProducto}_${nombreAlmacen}_${fechaActual}.xlsx`;

            // Si hay filtro de fechas, incluirlo en el nombre
            if (filtros.fecha_inicio && filtros.fecha_fin) {
                nombreArchivo = `Kardex_${nombreProducto}_${nombreAlmacen}_${filtros.fecha_inicio}_${filtros.fecha_fin}.xlsx`;
            }

            link.download = nombreArchivo;
            
            document.body.appendChild(link);
            link.click();
            
            // Limpiar
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
            
            toast({
                title: 'Kardex descargado',
                description: 'El kardex se ha descargado exitosamente',
                status: 'success',
                duration: 3000,
            });

            // Limpiar filtros y cerrar modal
            setFiltros({
                producto_id: '',
                almacen_id: '',
                fecha_inicio: '',
                fecha_fin: ''
            });
            onClose();
            
        } catch (error) {
            console.error('Error al descargar kardex:', error);
            toast({
                title: 'Error al descargar kardex',
                description: error.message || 'No se pudo descargar el kardex',
                status: 'error',
                duration: 5000,
            });
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        // Limpiar filtros al cerrar
        setFiltros({
            producto_id: '',
            almacen_id: '',
            fecha_inicio: '',
            fecha_fin: ''
        });
        onClose();
    };

    return (
        <Modal isOpen={isOpen} onClose={handleClose} size="lg">
            <ModalOverlay />
            <ModalContent>
                <ModalHeader>Exportar Kardex a Excel</ModalHeader>
                <ModalCloseButton />
                <ModalBody>
                    <VStack spacing={4}>
                        <Text color="gray.600" fontSize="sm">
                            Seleccione un producto y almacén específico para generar el kardex.
                            Opcionalmente puede filtrar por rango de fechas.
                        </Text>
                        
                        <FormControl isRequired>
                            <FormLabel>Producto</FormLabel>
                            <Select
                                placeholder="Seleccionar producto..."
                                value={filtros.producto_id}
                                onChange={(e) => handleInputChange('producto_id', e.target.value)}
                            >
                                {productos.map(producto => (
                                    <option key={producto.id} value={producto.id}>
                                        {producto.sku} - {producto.nombre}
                                    </option>
                                ))}
                            </Select>
                        </FormControl>

                        <FormControl isRequired>
                            <FormLabel>Almacén</FormLabel>
                            <Select
                                placeholder="Seleccionar almacén..."
                                value={filtros.almacen_id}
                                onChange={(e) => handleInputChange('almacen_id', e.target.value)}
                            >
                                {almacenes.map(almacen => (
                                    <option key={almacen.id} value={almacen.id}>
                                        {almacen.nombre}
                                    </option>
                                ))}
                            </Select>
                        </FormControl>

                        <HStack width="100%" spacing={4}>
                            <FormControl>
                                <FormLabel>Fecha inicio (opcional)</FormLabel>
                                <Input
                                    type="date"
                                    value={filtros.fecha_inicio}
                                    onChange={(e) => handleInputChange('fecha_inicio', e.target.value)}
                                />
                            </FormControl>

                            <FormControl>
                                <FormLabel>Fecha fin (opcional)</FormLabel>
                                <Input
                                    type="date"
                                    value={filtros.fecha_fin}
                                    onChange={(e) => handleInputChange('fecha_fin', e.target.value)}
                                />
                            </FormControl>
                        </HStack>
                    </VStack>
                </ModalBody>

                <ModalFooter>
                    <Button variant="ghost" onClick={handleClose} mr={3}>
                        Cancelar
                    </Button>
                    <Button
                        colorScheme="orange"
                        onClick={exportarKardex}
                        isLoading={loading}
                        loadingText="Exportando..."
                    >
                        Descargar Excel
                    </Button>
                </ModalFooter>
            </ModalContent>
        </Modal>
    );
};

export default ExportarKardexModal; 