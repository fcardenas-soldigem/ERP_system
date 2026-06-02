import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import morgan from 'morgan';
import { config } from './config/index.js';
import { errorHandler } from './common/middleware/error-handler.js';
import { purchaseOrderRoutes } from './modules/purchase-orders/purchase-order.routes.js';

const app = express();

// ── Security & compression ──
app.use(helmet({ crossOriginResourcePolicy: { policy: 'cross-origin' } }));
app.use(compression());
app.use(cors({
  origin: ['http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:5173', 'http://127.0.0.1:5173'],
  credentials: true,
}));

// ── Body parsing ──
app.use(express.json({ limit: '5mb' }));
app.use(express.urlencoded({ extended: true }));

// ── HTTP logging ──
app.use(morgan('short'));

// ── Health check ──
app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'purchase-orders', timestamp: new Date() });
});

// ── Routes ──
app.use('/api/purchase-orders', purchaseOrderRoutes);

// ── 404 ──
app.use((_req, res) => {
  res.status(404).json({ success: false, message: 'Ruta no encontrada' });
});

// ── Centralized error handler (must be last) ──
app.use(errorHandler);

export default app;
