import React from 'react';
import {
  Box, Flex, Text, VStack, HStack, Button, Icon, Tooltip,
} from '@chakra-ui/react';
import { FiAlertTriangle, FiCheckCircle, FiAlertOctagon, FiExternalLink } from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';

const CONFIG = {
  vigente: {
    bg: '#f0fdf5', border: '#22c55e', text: '#166534',
    muted: '#15803d', icon: FiCheckCircle, iconColor: '#22c55e',
    label: 'Al día',
  },
  proximo: {
    bg: '#fffbeb', border: '#f59e0b', text: '#92400e',
    muted: '#b45309', icon: FiAlertTriangle, iconColor: '#f59e0b',
    label: 'Próximo a vencer',
  },
  vencido: {
    bg: '#fff1f2', border: '#ef4444', text: '#991b1b',
    muted: '#b91c1c', icon: FiAlertOctagon, iconColor: '#ef4444',
    label: 'Vencido',
  },
};

const fmt = (n) =>
  'S/ ' + Number(n).toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const IGVCard = ({ obligaciones }) => {
  const navigate = useNavigate();

  if (!obligaciones) return null;

  const { igv_ventas, igv_compras, igv_por_pagar, dias_para_vencer, estado, periodo } = obligaciones;
  const cfg = CONFIG[estado] ?? CONFIG.vigente;

  const countdownText =
    dias_para_vencer <= 0
      ? 'Vencido'
      : `Vence en ${dias_para_vencer} día${dias_para_vencer === 1 ? '' : 's'}`;

  return (
    <Box
      bg={cfg.bg}
      border="2px solid"
      borderColor={cfg.border}
      borderRadius="xl"
      p={5}
    >
      <Flex align="flex-start" justify="space-between" wrap="wrap" gap={4}>

        {/* ── Izquierda: ícono + título + desglose ── */}
        <HStack spacing={3} align="flex-start">
          <Icon as={cfg.icon} color={cfg.iconColor} boxSize="22px" mt="2px" flexShrink={0} />
          <VStack align="flex-start" spacing={1}>
            <HStack spacing={2} align="center">
              <Text fontWeight="bold" color={cfg.text} fontSize="sm">
                IGV por pagar · SUNAT
              </Text>
              <Tooltip
                label="Diferencia entre el IGV que cobraste a tus clientes y el IGV que pagaste a tus proveedores. Esto es lo que le debes a SUNAT."
                placement="top"
                hasArrow
                maxW="260px"
                fontSize="xs"
              >
                <Text
                  as="span"
                  fontSize="xs"
                  color={cfg.muted}
                  cursor="help"
                  borderBottom="1px dotted"
                  borderColor={cfg.muted}
                  lineHeight="1"
                >
                  ¿Qué es?
                </Text>
              </Tooltip>
            </HStack>

            <Text fontSize="2xl" fontWeight="extrabold" color={cfg.text} lineHeight="1.1">
              {fmt(igv_por_pagar)}
            </Text>

            <Text fontSize="xs" color={cfg.muted}>
              Período: {periodo}
            </Text>

            <HStack spacing={4} pt={1} flexWrap="wrap">
              <VStack spacing={0} align="flex-start">
                <Text fontSize="xs" color={cfg.muted} opacity={0.8}>IGV cobrado</Text>
                <Text fontSize="sm" fontWeight="semibold" color={cfg.text}>{fmt(igv_ventas)}</Text>
              </VStack>
              <Text color={cfg.muted} fontSize="sm">−</Text>
              <VStack spacing={0} align="flex-start">
                <Text fontSize="xs" color={cfg.muted} opacity={0.8}>IGV pagado (crédito fiscal)</Text>
                <Text fontSize="sm" fontWeight="semibold" color={cfg.text}>{fmt(igv_compras)}</Text>
              </VStack>
            </HStack>
          </VStack>
        </HStack>

        {/* ── Derecha: countdown + botón ── */}
        <VStack align="flex-end" spacing={3} minW="140px">
          <VStack spacing={0} align="flex-end">
            <Text fontSize="xs" color={cfg.muted} opacity={0.8}>Vencimiento SUNAT</Text>
            <Text fontSize="md" fontWeight="bold" color={cfg.text}>
              {countdownText}
            </Text>
            <Text fontSize="xs" color={cfg.muted}>{cfg.label}</Text>
          </VStack>

          <Button
            size="sm"
            variant="outline"
            borderColor={cfg.border}
            color={cfg.text}
            _hover={{ bg: cfg.border, color: 'white' }}
            rightIcon={<Icon as={FiExternalLink} />}
            onClick={() => navigate('/app/dashboard')}
            fontSize="xs"
          >
            Ver detalle
          </Button>
        </VStack>

      </Flex>
    </Box>
  );
};

export default IGVCard;
