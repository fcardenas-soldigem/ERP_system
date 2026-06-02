import app from './app.js';
import { config } from './config/index.js';
import { logger } from './config/logger.js';
import prisma from './prisma/client.js';

async function bootstrap() {
  try {
    await prisma.$connect();
    logger.info('✔ Conectado a PostgreSQL');

    app.listen(config.port, () => {
      logger.info(`✔ Purchase Orders Service corriendo en puerto ${config.port}`);
      logger.info(`  Entorno: ${config.nodeEnv}`);
    });
  } catch (err) {
    logger.error('Error al iniciar el servicio:', err);
    process.exit(1);
  }
}

const shutdown = async (signal) => {
  logger.info(`${signal} recibido – cerrando…`);
  await prisma.$disconnect();
  process.exit(0);
};

process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));

bootstrap();
