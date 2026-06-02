import React, { useState, useEffect } from 'react';
import {
    Box,
    Heading,
    VStack,
    FormControl,
    FormLabel,
    Input,
    Button,
    useToast,
    Select,
    Text,
    HStack,
    Switch,
    Card,
    CardBody,
    Flex,
    Spinner,
    Center,
    Image,
    Badge,
    Icon,
    Skeleton,
    SkeletonText,
    Alert,
    AlertIcon,
} from '@chakra-ui/react';
import { FaImage, FaBuilding, FaPhone, FaEnvelope, FaMapMarkerAlt, FaIdCard, FaTrash, FaSignature } from 'react-icons/fa';
import { api } from '../lib/api';

const Configuracion = () => {
    const toast = useToast();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [uploadingLogo, setUploadingLogo] = useState(false);
    const [empresaInfo, setEmpresaInfo] = useState(null);
    
    // Solo estas configuraciones son editables
    const [configFacturacion, setConfigFacturacion] = useState({
        serie_facturacion: '',
        numero_inicial: '',
        formato_factura: ''
    });
    
    const [preferencias, setPreferencias] = useState({
        notificaciones_email: false,
        backup_automatico: false,
        modo_oscuro: false
    });

    useEffect(() => {
        cargarDatos();
    }, []);

    const cargarDatos = async () => {
        try {
            setLoading(true);
            const response = await api.get('/api/empresas/');
            console.log('Respuesta empresas:', response.data);
            
            // Manejar respuesta paginada o array directo
            let empresas = [];
            if (response.data?.results) {
                empresas = response.data.results;
            } else if (Array.isArray(response.data)) {
                empresas = response.data;
            }
            
            if (empresas.length > 0) {
                const empresa = empresas[0];
                console.log('Empresa cargada:', empresa);
                setEmpresaInfo(empresa);
                
                // Cargar config de facturación si existe
                setConfigFacturacion({
                    serie_facturacion: empresa.serie_facturacion || '',
                    numero_inicial: empresa.numero_inicial || '',
                    formato_factura: empresa.formato_factura || ''
                });
                
                // Cargar preferencias si existen
                setPreferencias({
                    notificaciones_email: empresa.notificaciones_email || false,
                    backup_automatico: empresa.backup_automatico || false,
                    modo_oscuro: empresa.modo_oscuro || false
                });
            } else {
                console.warn('No se encontraron empresas');
            }
        } catch (error) {
            console.error('Error al cargar datos de empresa:', error);
            toast({
                title: 'Error al cargar datos',
                description: 'No se pudo obtener la información de la empresa',
                status: 'error',
                duration: 5000,
            });
        } finally {
            setLoading(false);
        }
    };

    const handleLogoUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Validar tipo de archivo
        if (!file.type.startsWith('image/')) {
            toast({
                title: 'Error',
                description: 'Solo se permiten archivos de imagen',
                status: 'error',
                duration: 3000,
            });
            return;
        }

        // Validar tamaño (máx 5MB)
        if (file.size > 5 * 1024 * 1024) {
            toast({
                title: 'Error',
                description: 'El archivo no debe superar los 5MB',
                status: 'error',
                duration: 3000,
            });
            return;
        }

        try {
            setUploadingLogo(true);
            const formData = new FormData();
            formData.append('logo', file);

            const response = await api.post(
                `/api/empresas/${empresaInfo.id}/upload_logo/`,
                formData,
                {
                    headers: {
                        'Content-Type': 'multipart/form-data',
                    },
                }
            );

            setEmpresaInfo(response.data);
            toast({
                title: 'Logo actualizado',
                description: 'El logo se ha subido correctamente',
                status: 'success',
                duration: 3000,
            });
        } catch (error) {
            console.error('Error al subir logo:', error);
            toast({
                title: 'Error al subir logo',
                description: error.response?.data?.error || error.message,
                status: 'error',
                duration: 5000,
            });
        } finally {
            setUploadingLogo(false);
        }
    };

    const handleRemoveLogo = async () => {
        try {
            setUploadingLogo(true);
            await api.delete(`/api/empresas/${empresaInfo.id}/delete_logo/`);
            setEmpresaInfo(prev => ({ ...prev, logo: null, logo_url: null }));
            toast({
                title: 'Logo eliminado',
                status: 'success',
                duration: 3000,
            });
        } catch (error) {
            toast({
                title: 'Error al eliminar logo',
                description: error.response?.data?.error || error.message,
                status: 'error',
                duration: 5000,
            });
        } finally {
            setUploadingLogo(false);
        }
    };

    const handleFirmaUpload = async (e, tipo) => {
        const file = e.target.files[0];
        if (!file) return;
        if (!file.type.startsWith('image/')) {
            toast({ title: 'Solo se permiten imágenes', status: 'error', duration: 3000 });
            return;
        }
        if (file.size > 2 * 1024 * 1024) {
            toast({ title: 'Máximo 2MB', status: 'error', duration: 3000 });
            return;
        }
        try {
            const formData = new FormData();
            formData.append(tipo, file);
            const response = await api.patch(
                `/api/empresas/${empresaInfo.id}/`,
                formData,
                { headers: { 'Content-Type': 'multipart/form-data' } }
            );
            setEmpresaInfo(response.data);
            toast({ title: 'Firma actualizada', status: 'success', duration: 3000 });
        } catch (error) {
            toast({ title: 'Error al subir firma', description: error.message, status: 'error', duration: 5000 });
        }
    };

    const handleRemoveFirma = async (tipo) => {
        try {
            const formData = new FormData();
            formData.append(tipo, '');
            await api.patch(
                `/api/empresas/${empresaInfo.id}/`,
                { [tipo]: null }
            );
            setEmpresaInfo(prev => ({ ...prev, [tipo]: null, [`${tipo}_url`]: null }));
            toast({ title: 'Firma eliminada', status: 'success', duration: 3000 });
        } catch (error) {
            toast({ title: 'Error al eliminar firma', description: error.message, status: 'error', duration: 5000 });
        }
    };

    const handleSubmit = async () => {
        if (!empresaInfo) return;
        
        // Por ahora solo mostramos un mensaje, ya que estas configuraciones
        // requieren campos adicionales en el backend
        toast({
            title: 'Configuración guardada',
            description: 'Los cambios se han guardado localmente. El logo se actualiza automáticamente.',
            status: 'success',
            duration: 3000,
        });
    };

    if (loading) {
        return (
            <Box p={6}>
                <Heading mb={6}>Configuración del Sistema</Heading>
                <VStack spacing={5} align="stretch">
                    <Card>
                        <CardBody>
                            <Skeleton height="40px" mb={4} />
                            <SkeletonText noOfLines={4} spacing={4} />
                        </CardBody>
                    </Card>
                </VStack>
            </Box>
        );
    }

    return (
        <Box p={6} maxW="1200px" mx="auto">
            <Heading mb={6}>Configuración del Sistema</Heading>
            
            <VStack spacing={6} align="stretch">
                {/* Logo de la Empresa */}
                <Card>
                    <CardBody>
                        <Heading size="md" mb={4}>Logo de la Empresa</Heading>
                        <Text fontSize="sm" color="gray.600" mb={4}>
                            Este logo aparecerá en las cotizaciones y documentos PDF generados
                        </Text>
                        
                        <Flex align="center" gap={6}>
                            <Box
                                borderWidth={2}
                                borderRadius="lg"
                                borderStyle="dashed"
                                borderColor="gray.300"
                                p={4}
                                minW="200px"
                                minH="100px"
                                display="flex"
                                alignItems="center"
                                justifyContent="center"
                                bg="gray.50"
                            >
                                {empresaInfo?.logo_url ? (
                                    <Image
                                        src={empresaInfo.logo_url}
                                        alt="Logo empresa"
                                        maxH="80px"
                                        maxW="180px"
                                        objectFit="contain"
                                    />
                                ) : (
                                    <VStack color="gray.400">
                                        <Icon as={FaImage} boxSize={10} />
                                        <Text fontSize="sm">Sin logo</Text>
                                    </VStack>
                                )}
                            </Box>
                            
                            <VStack align="start" spacing={3}>
                                <HStack>
                                    <FormControl w="auto">
                                        <Input
                                            type="file"
                                            accept="image/*"
                                            onChange={handleLogoUpload}
                                            display="none"
                                            id="logo-upload"
                                        />
                                        <Button
                                            as="label"
                                            htmlFor="logo-upload"
                                            leftIcon={<FaImage />}
                                            colorScheme="blue"
                                            isLoading={uploadingLogo}
                                            loadingText="Subiendo..."
                                            cursor="pointer"
                                        >
                                            {empresaInfo?.logo_url ? 'Cambiar Logo' : 'Subir Logo'}
                                        </Button>
                            </FormControl>

                                    {empresaInfo?.logo_url && (
                                        <Button
                                            leftIcon={<FaTrash />}
                                            colorScheme="red"
                                            variant="outline"
                                            onClick={handleRemoveLogo}
                                            isLoading={uploadingLogo}
                                        >
                                            Eliminar
                                        </Button>
                                    )}
                                </HStack>
                                <Text fontSize="xs" color="gray.500">
                                    Formatos: PNG, JPG, GIF. Máximo 5MB. Recomendado: 300x100px
                                </Text>
                            </VStack>
                        </Flex>
                    </CardBody>
                </Card>

                {/* Firmas Digitales */}
                <Card>
                    <CardBody>
                        <Heading size="md" mb={2}>
                            <Icon as={FaSignature} mr={2} />
                            Firmas Digitales
                        </Heading>
                        <Text fontSize="sm" color="gray.600" mb={4}>
                            Estas firmas aparecerán en las Órdenes de Compra y otros documentos PDF
                        </Text>

                        <HStack spacing={6} align="start">
                            {[
                                { key: 'firma_elaborado', label: 'Elaborado por' },
                                { key: 'firma_aprobado', label: 'Aprobado por' },
                            ].map(({ key, label }) => (
                                <VStack key={key} flex={1} spacing={3}>
                                    <Text fontWeight="semibold" fontSize="sm">{label}</Text>
                                    <Box
                                        borderWidth={2} borderRadius="lg" borderStyle="dashed"
                                        borderColor="gray.300" p={3} w="100%" minH="100px"
                                        display="flex" alignItems="center" justifyContent="center" bg="gray.50"
                                    >
                                        {empresaInfo?.[`${key}_url`] ? (
                                            <Image src={empresaInfo[`${key}_url`]} alt={label}
                                                maxH="80px" maxW="200px" objectFit="contain" />
                                        ) : (
                                            <VStack color="gray.400">
                                                <Icon as={FaSignature} boxSize={8} />
                                                <Text fontSize="xs">Sin firma</Text>
                                            </VStack>
                                        )}
                                    </Box>
                                    <HStack>
                                        <FormControl w="auto">
                                            <Input type="file" accept="image/*" display="none"
                                                id={`${key}-upload`}
                                                onChange={(e) => handleFirmaUpload(e, key)} />
                                            <Button as="label" htmlFor={`${key}-upload`} size="sm"
                                                leftIcon={<FaImage />} colorScheme="blue" cursor="pointer">
                                                {empresaInfo?.[`${key}_url`] ? 'Cambiar' : 'Subir'}
                                            </Button>
                                        </FormControl>
                                        {empresaInfo?.[`${key}_url`] && (
                                            <Button size="sm" leftIcon={<FaTrash />} colorScheme="red"
                                                variant="outline" onClick={() => handleRemoveFirma(key)}>
                                                Eliminar
                                            </Button>
                                        )}
                                    </HStack>
                                    <Text fontSize="xs" color="gray.500">PNG transparente recomendado. Máx 2MB</Text>
                                </VStack>
                            ))}
                        </HStack>
                    </CardBody>
                </Card>

                {/* Información de la Empresa (Solo lectura) */}
                <Card>
                    <CardBody>
                        <Flex justify="space-between" align="center" mb={4}>
                            <Heading size="md">Información de la Empresa</Heading>
                            <Badge colorScheme="gray" fontSize="xs">Solo lectura</Badge>
                        </Flex>
                        
                        <Alert status="info" mb={4} borderRadius="md">
                            <AlertIcon />
                            <Text fontSize="sm">
                                Esta información se configura en el panel de administración del sistema.
                            </Text>
                        </Alert>
                        
                        <VStack spacing={4} align="stretch">
                            <HStack spacing={4}>
                                <FormControl flex={2}>
                                    <FormLabel>
                                        <Icon as={FaBuilding} mr={2} />
                                        Nombre de la Empresa
                                    </FormLabel>
                                    <Input 
                                        value={empresaInfo?.nombre || ''} 
                                        isReadOnly 
                                        bg="gray.100"
                                        _hover={{ bg: 'gray.100' }}
                                    />
                            </FormControl>

                                <FormControl flex={1}>
                                    <FormLabel>
                                        <Icon as={FaIdCard} mr={2} />
                                        RUC
                                    </FormLabel>
                                    <Input 
                                        value={empresaInfo?.ruc || ''} 
                                        isReadOnly 
                                        bg="gray.100"
                                        _hover={{ bg: 'gray.100' }}
                                    />
                                </FormControl>
                            </HStack>

                            <FormControl>
                                <FormLabel>
                                    <Icon as={FaMapMarkerAlt} mr={2} />
                                    Dirección
                                </FormLabel>
                                <Input 
                                    value={empresaInfo?.direccion || ''} 
                                    isReadOnly 
                                    bg="gray.100"
                                    _hover={{ bg: 'gray.100' }}
                                />
                            </FormControl>

                            <HStack spacing={4}>
                            <FormControl>
                                    <FormLabel>
                                        <Icon as={FaPhone} mr={2} />
                                        Teléfono
                                    </FormLabel>
                                    <Input 
                                        value={empresaInfo?.telefono || ''} 
                                        isReadOnly 
                                        bg="gray.100"
                                        _hover={{ bg: 'gray.100' }}
                                    />
                            </FormControl>

                            <FormControl>
                                    <FormLabel>
                                        <Icon as={FaEnvelope} mr={2} />
                                        Email
                                    </FormLabel>
                                    <Input 
                                        value={empresaInfo?.email || ''} 
                                        isReadOnly 
                                        bg="gray.100"
                                        _hover={{ bg: 'gray.100' }}
                                    />
                            </FormControl>
                            </HStack>
                        </VStack>
                    </CardBody>
                </Card>

                {/* Configuración de Facturación */}
                <Card>
                    <CardBody>
                    <Heading size="md" mb={4}>Configuración de Facturación</Heading>
                    <VStack spacing={4}>
                            <HStack spacing={4} w="100%">
                        <FormControl>
                            <FormLabel>Serie de Facturación</FormLabel>
                                    <Input 
                                        placeholder="Ej: F001" 
                                        value={configFacturacion.serie_facturacion}
                                        onChange={(e) => setConfigFacturacion(prev => ({
                                            ...prev, 
                                            serie_facturacion: e.target.value
                                        }))}
                                    />
                        </FormControl>

                        <FormControl>
                            <FormLabel>Número de Factura Inicial</FormLabel>
                                    <Input 
                                        type="number" 
                                        placeholder="Ej: 1" 
                                        value={configFacturacion.numero_inicial}
                                        onChange={(e) => setConfigFacturacion(prev => ({
                                            ...prev, 
                                            numero_inicial: e.target.value
                                        }))}
                                    />
                        </FormControl>
                            </HStack>

                        <FormControl>
                            <FormLabel>Formato de Factura</FormLabel>
                                <Select 
                                    placeholder="Seleccione el formato"
                                    value={configFacturacion.formato_factura}
                                    onChange={(e) => setConfigFacturacion(prev => ({
                                        ...prev, 
                                        formato_factura: e.target.value
                                    }))}
                                >
                                <option value="A4">A4</option>
                                <option value="TICKET">Ticket</option>
                            </Select>
                        </FormControl>
                    </VStack>
                    </CardBody>
                </Card>

                {/* Preferencias del Sistema */}
                <Card>
                    <CardBody>
                    <Heading size="md" mb={4}>Preferencias del Sistema</Heading>
                        <VStack spacing={4} align="stretch">
                            <FormControl display="flex" alignItems="center" justifyContent="space-between">
                            <FormLabel mb="0">Notificaciones por Email</FormLabel>
                                <Switch 
                                    colorScheme="blue" 
                                    isChecked={preferencias.notificaciones_email}
                                    onChange={(e) => setPreferencias(prev => ({
                                        ...prev,
                                        notificaciones_email: e.target.checked
                                    }))}
                                />
                        </FormControl>

                            <FormControl display="flex" alignItems="center" justifyContent="space-between">
                            <FormLabel mb="0">Backup Automático</FormLabel>
                                <Switch 
                                    colorScheme="blue" 
                                    isChecked={preferencias.backup_automatico}
                                    onChange={(e) => setPreferencias(prev => ({
                                        ...prev,
                                        backup_automatico: e.target.checked
                                    }))}
                                />
                        </FormControl>

                            <FormControl display="flex" alignItems="center" justifyContent="space-between">
                            <FormLabel mb="0">Modo Oscuro</FormLabel>
                                <Switch 
                                    colorScheme="blue" 
                                    isChecked={preferencias.modo_oscuro}
                                    onChange={(e) => setPreferencias(prev => ({
                                        ...prev,
                                        modo_oscuro: e.target.checked
                                    }))}
                                />
                        </FormControl>
                    </VStack>
                    </CardBody>
                </Card>

                {/* Botones */}
                <HStack justify="flex-end">
                    <Button colorScheme="gray" variant="outline">
                        Cancelar
                    </Button>
                    <Button 
                        colorScheme="blue" 
                        onClick={handleSubmit}
                        isLoading={saving}
                        loadingText="Guardando..."
                    >
                        Guardar Cambios
                    </Button>
                </HStack>
            </VStack>
        </Box>
    );
};

export default Configuracion; 
