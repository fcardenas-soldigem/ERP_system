import React, { useState } from 'react';
import {
  Box, VStack, HStack, Text, Badge, Icon, Switch, FormLabel,
  Table, Thead, Tbody, Tr, Th, Td, TableContainer, Select,
  Grid, GridItem, FormControl, Input, Collapse,
  Accordion, AccordionItem, AccordionButton, AccordionPanel, AccordionIcon,
  useColorModeValue,
} from '@chakra-ui/react';
import {
  FiCheckCircle, FiAlertTriangle, FiAlertCircle, FiChevronDown,
} from 'react-icons/fi';

const FIELD_OPTIONS = [
  { value: '',                  label: '— ignorar —' },
  { value: 'id_fila',           label: 'ID / Código (clave cruce)' },
  { value: 'producto_nombre',   label: 'Nombre de producto' },
  { value: 'id_producto',       label: 'ID Producto (cruce)' },
  { value: 'cantidad',          label: 'Cantidad' },
  { value: 'proveedor_nombre',  label: 'Nombre proveedor' },
  { value: 'id_proveedor',      label: 'ID Proveedor (cruce)' },
  { value: 'proveedor_ruc',     label: 'RUC proveedor' },
  { value: 'cliente_nombre',    label: 'Nombre cliente' },
  { value: 'precio_compra',     label: 'Precio compra (sin IGV)' },
  { value: 'precio_final_compra', label: 'Precio compra (con IGV)' },
  { value: 'precio_venta',      label: 'Precio venta (sin IGV)' },
  { value: 'precio_final_venta', label: 'Precio venta (con IGV)' },
  { value: 'igv_compra',        label: 'IGV compra' },
  { value: 'igv_venta',         label: 'IGV venta' },
  { value: 'estado',            label: 'Estado (PAGADA/PENDIENTE/PARCIAL)' },
  { value: 'marca',             label: 'Marca' },
  { value: 'categoria_nombre',  label: 'Categoría' },
  { value: 'fecha_compra',      label: 'Fecha compra' },
  { value: 'fecha_entrega',     label: 'Fecha entrega/venta' },
  { value: 'encargado',         label: 'Encargado/Vendedor' },
  { value: 'direccion',         label: 'Dirección' },
  { value: 'telefono',          label: 'Teléfono' },
  { value: 'email',             label: 'Email' },
  { value: 'utilidad',          label: 'Utilidad (ignorar en import)' },
];

/**
 * Determina el estado de cobertura de una hoja según su tipo.
 * Devuelve 'ok' | 'warning' | 'error'.
 *
 * Reglas por entidad (basadas en campos obligatorios reales del sistema):
 *  - proveedores: basta con que haya columna de nombre de proveedor
 *  - productos:   necesita nombre de producto
 *  - compras:     necesita producto + almacen (default) + fecha (default o columna)
 *  - ventas:      necesita producto + cliente (default o columna) + fecha (default o columna)
 *  - standard:    necesita producto + almacen + cliente + fecha
 */
function getCoverageStatus(hoja, mapeo, defaults) {
  const mapped = new Set(Object.values(mapeo).filter(Boolean));
  const tipo = hoja.tipo_hoja;

  const hasProd     = mapped.has('producto_nombre') || mapped.has('id_producto');
  const hasFechaC   = mapped.has('fecha_compra');
  const hasFechaV   = mapped.has('fecha_entrega');
  const hasCliente  = mapped.has('cliente_nombre') || mapped.has('id_cliente');
  const hasProv     = mapped.has('proveedor_nombre') || mapped.has('id_proveedor');

  if (tipo === 'proveedores') {
    const hasNombre = mapped.has('proveedor_nombre') || mapped.has('producto_nombre');
    return hasNombre ? 'ok' : 'error';
  }

  if (tipo === 'productos') {
    // almacen y categoria tienen fallback automático, no son blocking
    return hasProd ? 'ok' : 'error';
  }

  if (tipo === 'compras') {
    if (!hasProd) return 'error';
    const almacenOk = !!defaults?.almacen_id;   // obligatorio para compra
    const fechaOk   = hasFechaC || !!defaults?.fecha;
    if (!almacenOk || !fechaOk) return 'warning';
    return 'ok';
  }

  if (tipo === 'ventas') {
    if (!hasProd) return 'error';
    const clienteOk = hasCliente || !!defaults?.cliente_id;  // obligatorio para venta
    const fechaOk   = hasFechaV || !!defaults?.fecha;
    if (!clienteOk || !fechaOk) return 'warning';
    return 'ok';
  }

  // standard: compra + venta en la misma fila
  if (!hasProd) return 'error';
  const almacenOk = !!defaults?.almacen_id;
  const clienteOk = hasCliente || !!defaults?.cliente_id;
  if (!almacenOk || !clienteOk) return 'warning';
  return 'ok';
}

function StatusBadge({ hoja, mapeo, defaults }) {
  const status   = getCoverageStatus(hoja, mapeo, defaults);
  const warnings = hoja.warnings || [];

  if (status === 'error') {
    return (
      <Badge colorScheme="red" variant="subtle" px={2} py={1} borderRadius="md">
        <HStack spacing={1}>
          <Icon as={FiAlertCircle} boxSize={3} />
          <Text>Problemas detectados</Text>
        </HStack>
      </Badge>
    );
  }
  if (status === 'warning' || warnings.length > 0) {
    return (
      <Badge colorScheme="yellow" variant="subtle" px={2} py={1} borderRadius="md">
        <HStack spacing={1}>
          <Icon as={FiAlertTriangle} boxSize={3} />
          <Text>Requiere configuración</Text>
        </HStack>
      </Badge>
    );
  }
  return (
    <Badge colorScheme="green" variant="subtle" px={2} py={1} borderRadius="md">
      <HStack spacing={1}>
        <Icon as={FiCheckCircle} boxSize={3} />
        <Text>Listo para importar</Text>
      </HStack>
    </Badge>
  );
}

/**
 * Construye la lista de campos faltantes a mostrar según el tipo de entidad.
 * Devuelve un array de { key, label, type, required }.
 * Solo muestra campos que el usuario PUEDE/DEBE configurar como default.
 */
function getMissingFields(hoja, mapeo, defaults) {
  const mapped  = new Set(Object.values(mapeo).filter(Boolean));
  const tipo    = hoja.tipo_hoja;
  const fields  = [];

  if (tipo === 'proveedores') {
    // Proveedores no necesitan fecha, almacén, cliente ni categoría.
    // Sus campos vienen del Excel (nombre, RUC). Nada que pedir aquí.
    return [];
  }

  if (tipo === 'productos') {
    // Productos necesitan almacén (para crear Stock) y opcionalmente categoría.
    fields.push({ key: 'almacen_id',   label: 'Almacén por defecto',   type: 'almacen',   required: false });
    fields.push({ key: 'categoria_id', label: 'Categoría por defecto', type: 'categoria', required: false });
    return fields;
  }

  if (tipo === 'compras') {
    // Compra requiere almacén. Fecha si no hay columna fecha_compra.
    fields.push({ key: 'almacen_id', label: 'Almacén', type: 'almacen', required: !defaults?.almacen_id });
    if (!mapped.has('fecha_compra')) {
      fields.push({ key: 'fecha', label: 'Fecha por defecto', type: 'fecha', required: !defaults?.fecha });
    }
    return fields;
  }

  if (tipo === 'ventas') {
    // Venta requiere cliente. Fecha si no hay columna fecha_entrega.
    const hasClienteCol = mapped.has('cliente_nombre') || mapped.has('id_cliente');
    if (!hasClienteCol) {
      fields.push({ key: 'cliente_id', label: 'Cliente por defecto', type: 'cliente', required: !defaults?.cliente_id });
    }
    if (!mapped.has('fecha_entrega')) {
      fields.push({ key: 'fecha', label: 'Fecha por defecto', type: 'fecha', required: !defaults?.fecha });
    }
    return fields;
  }

  // standard: compra + venta combinadas
  fields.push({ key: 'almacen_id',   label: 'Almacén',               type: 'almacen',   required: !defaults?.almacen_id });
  const hasClienteCol = mapped.has('cliente_nombre') || mapped.has('id_cliente');
  if (!hasClienteCol) {
    fields.push({ key: 'cliente_id', label: 'Cliente por defecto',   type: 'cliente',   required: !defaults?.cliente_id });
  }
  if (!mapped.has('fecha_compra') && !mapped.has('fecha_entrega')) {
    fields.push({ key: 'fecha',      label: 'Fecha por defecto',     type: 'fecha',     required: !defaults?.fecha });
  }
  fields.push({ key: 'categoria_id', label: 'Categoría por defecto', type: 'categoria', required: false });
  return fields;
}

export default function HojaPreview({ hoja, mapeo, defaults, onMapeoChange, onDefaultsChange, onToggle, incluir, ctx }) {
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const headBg      = useColorModeValue('gray.50', 'gray.750');
  const cellColor   = useColorModeValue('gray.600', 'gray.300');
  const subText     = useColorModeValue('gray.500', 'gray.400');
  const reqColor    = useColorModeValue('red.500', 'red.300');

  const missingFields = getMissingFields(hoja, mapeo, defaults);
  const hasMissingRequired = missingFields.some(f => f.required);

  return (
    <Box
      border="1px solid"
      borderColor={borderColor}
      borderRadius="xl"
      overflow="hidden"
      opacity={incluir ? 1 : 0.5}
    >
      {/* Header */}
      <HStack
        justify="space-between"
        px={5}
        py={4}
        bg={headBg}
        borderBottom="1px solid"
        borderColor={borderColor}
      >
        <HStack spacing={3}>
          <VStack align="start" spacing={0}>
            <HStack spacing={2}>
              <Text fontWeight="semibold" fontSize="sm">{hoja.nombre}</Text>
              <Badge colorScheme="gray" variant="outline" fontSize="10px">
                {hoja.tipo_hoja}
              </Badge>
            </HStack>
            <Text fontSize="xs" color={subText}>
              {hoja.total_filas} filas · {hoja.columnas.length} columnas
            </Text>
          </VStack>
          <StatusBadge hoja={hoja} mapeo={mapeo} defaults={defaults} />
        </HStack>
        <HStack spacing={3}>
          <FormLabel htmlFor={`toggle-${hoja.nombre}`} mb={0} fontSize="xs" color={subText}>
            Importar
          </FormLabel>
          <Switch
            id={`toggle-${hoja.nombre}`}
            isChecked={incluir}
            onChange={(e) => onToggle(e.target.checked)}
            colorScheme="blue"
            size="sm"
          />
        </HStack>
      </HStack>

      {incluir && (
        <Box px={5} py={4}>
          <Accordion allowToggle defaultIndex={[0]}>
            {/* Preview tabla */}
            <AccordionItem border="none">
              <AccordionButton px={0} py={2} _hover={{ bg: 'transparent' }}>
                <Text flex={1} textAlign="left" fontSize="xs" fontWeight="semibold" color={subText} letterSpacing="wider" textTransform="uppercase">
                  Preview datos
                </Text>
                <AccordionIcon boxSize={4} />
              </AccordionButton>
              <AccordionPanel px={0} pb={3}>
                <TableContainer borderRadius="lg" border="1px solid" borderColor={borderColor}>
                  <Table size="sm" variant="simple">
                    <Thead>
                      <Tr>
                        {hoja.columnas.slice(0, 6).map(col => (
                          <Th key={col} fontSize="10px" py={2} maxW="120px">
                            <Text isTruncated>{col}</Text>
                          </Th>
                        ))}
                        {hoja.columnas.length > 6 && <Th fontSize="10px">+{hoja.columnas.length - 6}</Th>}
                      </Tr>
                    </Thead>
                    <Tbody>
                      {(hoja.preview_filas || []).slice(0, 4).map((row, ri) => (
                        <Tr key={ri}>
                          {hoja.columnas.slice(0, 6).map(col => (
                            <Td key={col} fontSize="11px" color={cellColor} maxW="120px" py={1.5}>
                              {/* Backend ya envía RUC como "20390342048" (sin .0). NaT como null. */}
                              <Text isTruncated>{row[col] ?? '—'}</Text>
                            </Td>
                          ))}
                          {hoja.columnas.length > 6 && <Td />}
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </TableContainer>
              </AccordionPanel>
            </AccordionItem>

            {/* Mapeo de columnas */}
            <AccordionItem border="none">
              <AccordionButton px={0} py={2} _hover={{ bg: 'transparent' }}>
                <Text flex={1} textAlign="left" fontSize="xs" fontWeight="semibold" color={subText} letterSpacing="wider" textTransform="uppercase">
                  Mapeo de columnas
                </Text>
                <AccordionIcon boxSize={4} />
              </AccordionButton>
              <AccordionPanel px={0} pb={3}>
                <Grid templateColumns="repeat(2, 1fr)" gap={2}>
                  {hoja.columnas.map(col => (
                    <GridItem key={col}>
                      <FormControl>
                        <FormLabel fontSize="10px" color={subText} mb={1} isTruncated title={col}>
                          {col}
                        </FormLabel>
                        <Select
                          size="xs"
                          borderRadius="md"
                          value={mapeo[col] || ''}
                          onChange={(e) => onMapeoChange(col, e.target.value || null)}
                          fontSize="12px"
                        >
                          {FIELD_OPTIONS.map(opt => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                          ))}
                        </Select>
                      </FormControl>
                    </GridItem>
                  ))}
                </Grid>
              </AccordionPanel>
            </AccordionItem>

            {/* Campos faltantes — solo los relevantes por tipo de entidad */}
            {missingFields.length > 0 && (
              <AccordionItem border="none">
                <AccordionButton px={0} py={2} _hover={{ bg: 'transparent' }}>
                  <HStack flex={1} spacing={2}>
                    <Icon
                      as={hasMissingRequired ? FiAlertTriangle : FiChevronDown}
                      boxSize={3}
                      color={hasMissingRequired ? 'yellow.500' : subText}
                    />
                    <Text textAlign="left" fontSize="xs" fontWeight="semibold" color={subText} letterSpacing="wider" textTransform="uppercase">
                      {hasMissingRequired ? 'Completar datos requeridos' : 'Configuración opcional'}
                    </Text>
                  </HStack>
                  <AccordionIcon boxSize={4} />
                </AccordionButton>
                <AccordionPanel px={0} pb={3}>
                  <Grid templateColumns="repeat(2, 1fr)" gap={3}>

                    {missingFields.map(field => (
                      <GridItem key={field.key}>
                        <FormControl isRequired={field.required}>
                          <FormLabel fontSize="xs" color={field.required ? reqColor : subText} mb={1}>
                            {field.label}{field.required ? ' *' : ''}
                          </FormLabel>

                          {field.type === 'fecha' && (
                            <Input
                              type="date"
                              size="sm"
                              borderRadius="md"
                              borderColor={field.required && !defaults?.[field.key] ? 'red.300' : undefined}
                              value={defaults?.[field.key] || ''}
                              onChange={(e) => onDefaultsChange(field.key, e.target.value)}
                            />
                          )}

                          {field.type === 'almacen' && (
                            <Select
                              size="sm"
                              borderRadius="md"
                              placeholder="Seleccionar almacén..."
                              borderColor={field.required && !defaults?.[field.key] ? 'red.300' : undefined}
                              value={defaults?.[field.key] || ''}
                              onChange={(e) => onDefaultsChange(field.key, e.target.value)}
                            >
                              {(ctx?.almacenes || []).map(a => (
                                <option key={a.id} value={a.id}>{a.nombre}</option>
                              ))}
                            </Select>
                          )}

                          {field.type === 'cliente' && (
                            <Select
                              size="sm"
                              borderRadius="md"
                              placeholder="Seleccionar cliente..."
                              borderColor={field.required && !defaults?.[field.key] ? 'red.300' : undefined}
                              value={defaults?.[field.key] || ''}
                              onChange={(e) => onDefaultsChange(field.key, e.target.value)}
                            >
                              {(ctx?.clientes || []).map(c => (
                                <option key={c.id} value={c.id}>
                                  {c.nombre} ({c.documento})
                                </option>
                              ))}
                            </Select>
                          )}

                          {field.type === 'categoria' && (
                            <Select
                              size="sm"
                              borderRadius="md"
                              placeholder="Seleccionar categoría..."
                              value={defaults?.[field.key] || ''}
                              onChange={(e) => onDefaultsChange(field.key, e.target.value)}
                            >
                              {(ctx?.categorias || []).map(c => (
                                <option key={c.id} value={c.id}>{c.nombre}</option>
                              ))}
                            </Select>
                          )}

                        </FormControl>
                      </GridItem>
                    ))}

                  </Grid>
                </AccordionPanel>
              </AccordionItem>
            )}
          </Accordion>

          {/* Resumen estimado */}
          {hoja.estimado && (
            <HStack
              spacing={4}
              mt={3}
              pt={3}
              borderTop="1px solid"
              borderColor={borderColor}
              flexWrap="wrap"
            >
              {hoja.estimado.compras > 0 && (
                <Text fontSize="11px" color={subText}>
                  <Text as="span" fontWeight="semibold" color="blue.500">{hoja.estimado.compras}</Text> compras
                </Text>
              )}
              {hoja.estimado.ventas > 0 && (
                <Text fontSize="11px" color={subText}>
                  <Text as="span" fontWeight="semibold" color="green.500">{hoja.estimado.ventas}</Text> ventas
                </Text>
              )}
              {hoja.estimado.proveedores_nuevos > 0 && (
                <Text fontSize="11px" color={subText}>
                  <Text as="span" fontWeight="semibold" color="orange.500">{hoja.estimado.proveedores_nuevos}</Text> proveedores nuevos
                </Text>
              )}
              {hoja.estimado.productos_nuevos > 0 && (
                <Text fontSize="11px" color={subText}>
                  <Text as="span" fontWeight="semibold" color="purple.500">{hoja.estimado.productos_nuevos}</Text> productos nuevos
                </Text>
              )}
            </HStack>
          )}

          {/* Warnings del backend */}
          {(hoja.warnings || []).length > 0 && (
            <VStack align="start" spacing={1} mt={2}>
              {hoja.warnings.map((w, i) => (
                <HStack key={i} spacing={1}>
                  <Icon as={FiAlertTriangle} boxSize={3} color="yellow.500" />
                  <Text fontSize="11px" color="yellow.600">{w}</Text>
                </HStack>
              ))}
            </VStack>
          )}
        </Box>
      )}
    </Box>
  );
}
