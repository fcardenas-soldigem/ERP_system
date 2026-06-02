import { PrismaClient } from '@prisma/client';
import { logger } from '../config/logger.js';

const prisma = new PrismaClient({
  log: [
    { emit: 'event', level: 'query' },
    { emit: 'event', level: 'error' },
    { emit: 'event', level: 'warn' },
  ],
  transactionOptions: {
    timeout: 30000,
    maxWait: 30000,
  },
});

prisma.$on('error', (e) => logger.error('Prisma error: %s', e.message));
prisma.$on('warn', (e) => logger.warn('Prisma warn: %s', e.message));

export default prisma;
