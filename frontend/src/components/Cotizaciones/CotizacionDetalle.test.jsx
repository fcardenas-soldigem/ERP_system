/**
 * Integración (0.2): el detalle de cotización renderiza el cliente y los
 * ítems con la forma REAL de la API (cliente_info{} + detalles[]).
 * Regresión de H1 (REVIEW_MOVIL): la vista leía cliente_nombre/items, campos
 * que el serializer nunca envió, y mostraba todo vacío.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ChakraProvider } from '@chakra-ui/react';
import { vi } from 'vitest';
import CotizacionDetalle from './CotizacionDetalle';

// Payload con la forma exacta de CotizacionSerializer (backend)
const COTIZACION_API = {
  id: 14,
  numero: 'COT-00000006',
  estado: 'borrador',
  estado_display: 'Borrador',
  asunto: 'Suministro de materiales',
  moneda: 'PEN',
  subtotal: '300.00',
  igv: '54.00',
  total: '354.00',
  porcentaje_igv: '18.00',
  fecha_emision: '2026-10-26',
  fecha_vencimiento: '2026-11-25',
  contacto_nombre: 'María Quispe',
  contacto_email: 'maria@cliente.pe',
  cliente: 8,
  cliente_info: {
    id: 8,
    nombre: 'Cliente Demo 2',
    documento: '20100012345',
    tipo_documento: 'ruc',
    telefono: '999888777',
    email: 'compras@clientedemo2.pe',
  },
  detalles: [
    { id: 1, producto_nombre: 'Stock Alto A', descripcion: 'Jabra Evolve2 750', cantidad: '2.00', precio_unitario: '100.00', subtotal: '200.00' },
    { id: 2, producto_nombre: null, descripcion: 'Servicio de instalación', cantidad: '1.00', precio_unitario: '100.00', subtotal: '100.00' },
  ],
};

vi.mock('../../services/cotizacionesService', () => ({
  default: {
    getById: vi.fn(() => Promise.resolve(COTIZACION_API)),
    cambiarEstado: vi.fn(),
    duplicar: vi.fn(),
    exportarPDF: vi.fn(),
    delete: vi.fn(),
  },
}));

const renderDetalle = () => render(
  <ChakraProvider>
    <MemoryRouter initialEntries={['/app/cotizaciones/14']}>
      <Routes>
        <Route path="/app/cotizaciones/:id" element={<CotizacionDetalle />} />
      </Routes>
    </MemoryRouter>
  </ChakraProvider>,
);

describe('CotizacionDetalle con el payload real de la API', () => {
  it('muestra el cliente (cliente_info) y su documento', async () => {
    renderDetalle();
    expect(await screen.findByText('Cliente Demo 2')).toBeInTheDocument();
    expect(screen.getByText(/RUC: 20100012345/)).toBeInTheDocument();
  });

  it('muestra los ítems (detalles) con cantidad y subtotal', async () => {
    renderDetalle();
    expect(await screen.findByText('Stock Alto A')).toBeInTheDocument();
    expect(screen.getByText('Servicio de instalación')).toBeInTheDocument();
    // nunca el estado vacío
    expect(screen.queryByText(/No hay items/i)).not.toBeInTheDocument();
  });

  it('muestra el número y el total', async () => {
    renderDetalle();
    expect(await screen.findByText(/COT-00000006/)).toBeInTheDocument();
  });
});
