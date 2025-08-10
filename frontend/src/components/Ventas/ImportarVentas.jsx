import React, { useState } from 'react';
import { ventasService } from '../../services/ventas.service';
import { ModalBody, Box, Text, Input } from '@chakra-ui/react';

const ImportarVentas = () => {
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [resultado, setResultado] = useState(null);
    const [error, setError] = useState(null);

    const handleFileChange = (event) => {
        const selectedFile = event.target.files[0];
        setFile(selectedFile);
        setError(null);
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        if (!file) {
            setError('Por favor seleccione un archivo');
            return;
        }

        setLoading(true);
        try {
            const result = await ventasService.importarExcel(file);
            setResultado(result);
            setError(null);
            event.target.reset();
            setFile(null);
        } catch (error) {
            setError(error.response?.data?.error || 'Error al importar el archivo');
            setResultado(null);
        } finally {
            setLoading(false);
        }
    };

    return (
        <ModalBody>
            <Box bg="blue.50" p={4} borderRadius="md" mb={4}>
                <Text>
                    Descargue el template de Excel, llénelo con sus ventas y súbalo para importarlas masivamente.
                </Text>
                <a href="/api/ventas/descargar_template/" target="_blank" rel="noopener noreferrer" style={{ color: "#3182ce", textDecoration: "underline" }}>
                    Descargar template
                </a>
            </Box>
            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700">
                        Seleccionar archivo Excel/CSV
                    </label>
                    <input
                        type="file"
                        accept=".xlsx,.xls,.csv"
                        onChange={handleFileChange}
                        className="mt-1 block w-full"
                        disabled={loading}
                    />
                </div>
                <button
                    type="submit"
                    disabled={!file || loading}
                    className={`px-4 py-2 rounded ${
                        !file || loading 
                            ? 'bg-gray-400'
                            : 'bg-blue-500 hover:bg-blue-600'
                    } text-white`}
                >
                    {loading ? 'Importando...' : 'Importar'}
                </button>
            </form>
            <Box mt={8}>
                <Text fontWeight="semibold" mb={2}>Formato del archivo Excel/CSV</Text>
                <Box fontSize="sm" color="gray.600" mb={2}>
                    El archivo debe contener las siguientes columnas:
                </Box>
                <ul style={{ paddingLeft: 20, fontSize: 14, color: '#4A5568' }}>
                    <li>cliente_nombre: Nombre del cliente</li>
                    <li>cliente_documento: Documento del cliente</li>
                    <li>fecha_emision: Fecha de la venta (YYYY-MM-DD)</li>
                    <li>productos: SKUs de los productos separados por comas</li>
                    <li>cantidades: Cantidades separadas por comas</li>
                    <li>precios_unitarios: Precios unitarios separados por comas</li>
                    <li>metodo_pago: Método de pago</li>
                    <li>igv_incluido: Sí/No</li>
                    <li>estado: Estado de la venta</li>
                    <li>referencia: Referencia (opcional)</li>
                </ul>
            </Box>
            {error && (
                <Box mt={4} p={3} bg="red.100" color="red.700" borderRadius="md">
                    {error}
                </Box>
            )}
            {resultado && (
                <Box mt={4} p={3} bg="green.100" color="green.700" borderRadius="md">
                    <p>{resultado.mensaje}</p>
                    {resultado.errores?.length > 0 && (
                        <Box mt={2}>
                            <Text fontWeight="bold">Errores encontrados:</Text>
                            <ul style={{ paddingLeft: 20 }}>
                                {resultado.errores.map((error, index) => (
                                    <li key={index}>{error}</li>
                                ))}
                            </ul>
                        </Box>
                    )}
                </Box>
            )}
        </ModalBody>
    );
};

export default ImportarVentas; 