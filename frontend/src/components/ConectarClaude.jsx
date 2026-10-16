import React, { useEffect, useState } from 'react';
import {
  Box, Card, CardBody, Heading, Text, VStack, HStack, Button, Input,
  FormControl, FormLabel, Table, Thead, Tbody, Tr, Th, Td, Badge, Code,
  useToast, Alert, AlertIcon, Divider, Spinner, Tooltip,
} from '@chakra-ui/react';
import { FaRobot, FaCopy, FaPlus, FaBan } from 'react-icons/fa';
import { agenteService } from '../services/agente.service';

const ESTADO_COLOR = { activo: 'green', revocado: 'red', expirado: 'gray' };
// En dev el backend corre en :8000; en prod reemplazar por la URL pública del ERP.
const MCP_URL = `${window.location.protocol}//${window.location.hostname}:8000/api/mcp/`;

export default function ConectarClaude() {
  const toast = useToast();
  const [tokens, setTokens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [nombre, setNombre] = useState('');
  const [dias, setDias] = useState(90);
  const [creating, setCreating] = useState(false);
  const [nuevoToken, setNuevoToken] = useState(null); // {token, nombre} mostrado una vez

  const cargar = async () => {
    setLoading(true);
    try {
      setTokens(await agenteService.listTokens());
    } catch (e) {
      toast({ title: 'No se pudieron cargar los tokens', status: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { cargar(); }, []);

  const copiar = (txt) => {
    navigator.clipboard?.writeText(txt);
    toast({ title: 'Copiado', status: 'success', duration: 1200 });
  };

  const crear = async () => {
    setCreating(true);
    try {
      const data = await agenteService.createToken({ nombre: nombre || 'Token MCP', dias });
      setNuevoToken({ token: data.token, nombre: data.nombre });
      setNombre('');
      await cargar();
    } catch (e) {
      toast({ title: 'No se pudo crear el token', status: 'error' });
    } finally {
      setCreating(false);
    }
  };

  const revocar = async (t) => {
    if (!window.confirm(`¿Revocar el token "${t.nombre}"? Claude dejará de poder conectarse con él.`)) return;
    try {
      await agenteService.revokeToken(t.id);
      toast({ title: 'Token revocado', status: 'success' });
      await cargar();
    } catch (e) {
      toast({ title: 'No se pudo revocar', status: 'error' });
    }
  };

  const comando = (token) =>
    `claude mcp add --transport http erp-soldigem ${MCP_URL} --header "Authorization: Bearer ${token}"`;

  return (
    <Card>
      <CardBody>
        <HStack mb={2}>
          <FaRobot />
          <Heading size="md">Conectar Claude</Heading>
        </HStack>
        <Text color="gray.600" fontSize="sm" mb={4}>
          Crea un token para conectar el agente de Claude al ERP (solo lectura). El agente
          <b> propone</b>; tú confirmas en el ERP. El token se muestra una sola vez.
        </Text>

        {/* Crear */}
        <HStack align="flex-end" spacing={3} mb={4}>
          <FormControl maxW="320px">
            <FormLabel fontSize="sm">Nombre del token</FormLabel>
            <Input size="sm" placeholder="Agente intake diario" value={nombre}
                   onChange={(e) => setNombre(e.target.value)} />
          </FormControl>
          <FormControl maxW="120px">
            <FormLabel fontSize="sm">Días</FormLabel>
            <Input size="sm" type="number" min={1} value={dias}
                   onChange={(e) => setDias(Number(e.target.value) || 90)} />
          </FormControl>
          <Button size="sm" colorScheme="blue" leftIcon={<FaPlus />} onClick={crear} isLoading={creating}>
            Crear token
          </Button>
        </HStack>

        {/* Token recién creado: se muestra UNA vez */}
        {nuevoToken && (
          <Alert status="success" variant="subtle" flexDirection="column" alignItems="flex-start" mb={4} borderRadius="md">
            <HStack><AlertIcon /><Text fontWeight="bold">Copia este token ahora. No se volverá a mostrar.</Text></HStack>
            <HStack mt={2} w="100%">
              <Code p={2} flex="1" overflowX="auto">{nuevoToken.token}</Code>
              <Tooltip label="Copiar token"><Button size="sm" leftIcon={<FaCopy />} onClick={() => copiar(nuevoToken.token)}>Copiar</Button></Tooltip>
            </HStack>
            <Text mt={3} fontSize="sm" fontWeight="semibold">Conéctalo desde Claude Code:</Text>
            <HStack mt={1} w="100%">
              <Code p={2} flex="1" overflowX="auto" whiteSpace="pre">{comando(nuevoToken.token)}</Code>
              <Button size="sm" leftIcon={<FaCopy />} onClick={() => copiar(comando(nuevoToken.token))}>Copiar</Button>
            </HStack>
          </Alert>
        )}

        <Divider mb={3} />

        {/* Instrucciones */}
        <Box bg="gray.50" p={3} borderRadius="md" mb={4} fontSize="sm">
          <Text fontWeight="semibold" mb={1}>Cómo conectar</Text>
          <Text>1. Crea un token arriba y cópialo.</Text>
          <Text>2. En Claude Code / Cowork, agrega el servidor MCP:</Text>
          <Code display="block" p={2} my={1} whiteSpace="pre" overflowX="auto">{comando('TU_TOKEN')}</Code>
          <Text>3. El agente podrá usar: buscar_cliente, historial_precios_item, ventas_esperando_oc_nr y listar_propuestas_pendientes.</Text>
        </Box>

        {/* Listado */}
        {loading ? <Spinner /> : (
          <Table size="sm" variant="simple">
            <Thead>
              <Tr><Th>Nombre</Th><Th>Prefijo</Th><Th>Estado</Th><Th>Último uso</Th><Th>Expira</Th><Th></Th></Tr>
            </Thead>
            <Tbody>
              {tokens.length === 0 && (
                <Tr><Td colSpan={6}><Text color="gray.500">Aún no hay tokens.</Text></Td></Tr>
              )}
              {tokens.map((t) => (
                <Tr key={t.id}>
                  <Td>{t.nombre}</Td>
                  <Td><Code>{t.token_prefix}…</Code></Td>
                  <Td><Badge colorScheme={ESTADO_COLOR[t.estado] || 'gray'}>{t.estado}</Badge></Td>
                  <Td>{t.last_used_at ? new Date(t.last_used_at).toLocaleString() : '—'}</Td>
                  <Td>{t.expires_at ? new Date(t.expires_at).toLocaleDateString() : '—'}</Td>
                  <Td>
                    {t.estado === 'activo' && (
                      <Button size="xs" colorScheme="red" variant="outline" leftIcon={<FaBan />} onClick={() => revocar(t)}>
                        Revocar
                      </Button>
                    )}
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </CardBody>
    </Card>
  );
}
