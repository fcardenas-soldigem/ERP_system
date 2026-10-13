import React from 'react';
import {
  Table, Thead, Tbody, Tr, Th, Td, TableContainer,
} from '@chakra-ui/react';
import EmptyState from './EmptyState';

/**
 * DataTable — wrapper de Table con las reglas del sistema:
 * densidad compacta (size sm del theme), header gris, hover de fila,
 * montos SIEMPRE a la derecha (isNumeric) y tabular-nums (global en td).
 *
 * columns: [{ key, header, isNumeric?, render?(row) }]
 * rows: array de objetos. onRowClick opcional (cursor + hover ya en theme).
 * empty: props para EmptyState cuando no hay filas.
 */
const DataTable = ({ columns, rows = [], onRowClick, empty, ...rest }) => {
  if (!rows.length && empty) return <EmptyState {...empty} />;
  return (
    <TableContainer {...rest}>
      <Table variant="simple">
        <Thead>
          <Tr>
            {columns.map((c) => (
              <Th key={c.key} isNumeric={c.isNumeric}>{c.header}</Th>
            ))}
          </Tr>
        </Thead>
        <Tbody>
          {rows.map((row, i) => (
            <Tr
              key={row.id ?? i}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              cursor={onRowClick ? 'pointer' : undefined}
            >
              {columns.map((c) => (
                <Td key={c.key} isNumeric={c.isNumeric}>
                  {c.render ? c.render(row) : row[c.key]}
                </Td>
              ))}
            </Tr>
          ))}
        </Tbody>
      </Table>
    </TableContainer>
  );
};

export default DataTable;
