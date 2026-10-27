import React, { useEffect, useState } from 'react';
import {
  Badge, Box, Button, Card, CardBody, Code, Heading, HStack, Link, Text, useToast,
} from '@chakra-ui/react';
import { FaTelegram } from 'react-icons/fa';
import { api } from '../../lib/api';

/**
 * A3 — Vincular Telegram: genera un código de 8 caracteres (10 min) y el
 * link t.me del bot. El backend guarda chat_id ↔ usuario al recibir
 * /start CODIGO. También permite desvincular.
 */
const VincularTelegram = () => {
  const toast = useToast();
  const [estado, setEstado] = useState({ cargando: true, vinculado: false });
  const [codigo, setCodigo] = useState(null);

  const cargar = async () => {
    try {
      const { data } = await api.get('/api/canales/telegram/vincular/');
      setEstado({ cargando: false, vinculado: data.vinculado, bot: data.bot });
    } catch {
      setEstado({ cargando: false, vinculado: false });
    }
  };

  useEffect(() => { cargar(); }, []);

  const generar = async () => {
    try {
      const { data } = await api.post('/api/canales/telegram/vincular/');
      if (data.vinculado) return cargar();
      setCodigo(data);
    } catch (e) {
      toast({ title: 'No se pudo generar el código', status: 'error', duration: 4000 });
    }
  };

  const desvincular = async () => {
    await api.delete('/api/canales/telegram/vincular/');
    setCodigo(null);
    cargar();
  };

  if (estado.cargando) return null;

  return (
    <Card>
      <CardBody>
        <HStack justify="space-between" mb={2}>
          <Heading size="md">
            <HStack><FaTelegram color="#229ED9" /><Text>Asistente por Telegram</Text></HStack>
          </Heading>
          {estado.vinculado && <Badge colorScheme="green">Vinculado</Badge>}
        </HStack>
        <Text fontSize="sm" color="gray.600" mb={3}>
          Cotiza, consulta ventas y registra cobros desde Telegram.
          El bot siempre te pide confirmar antes de crear algo.
        </Text>
        {estado.vinculado ? (
          <Button size="sm" variant="outline" colorScheme="red" onClick={desvincular}>
            Desvincular
          </Button>
        ) : codigo ? (
          <Box>
            <Text fontSize="sm" mb={2}>
              1. Abre <Link color="blue.500" href={codigo.link} isExternal>{codigo.link}</Link>
            </Text>
            <Text fontSize="sm" mb={2}>
              2. O envíale al bot: <Code>/start {codigo.codigo}</Code>
            </Text>
            <Text fontSize="xs" color="gray.500">El código vence en {codigo.expira_en_minutos} minutos.</Text>
            <Button size="sm" mt={2} variant="outline" onClick={cargar}>Ya lo vinculé</Button>
          </Box>
        ) : (
          <Button size="sm" colorScheme="blue" onClick={generar}>
            Vincular Telegram
          </Button>
        )}
      </CardBody>
    </Card>
  );
};

export default VincularTelegram;
