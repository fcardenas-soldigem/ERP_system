import 'dotenv/config';

export const config = Object.freeze({
  port: parseInt(process.env.PORT, 10) || 3001,
  nodeEnv: process.env.NODE_ENV || 'development',
  corsOrigin: process.env.CORS_ORIGIN || 'http://localhost:3000',
  companyLogoPath: process.env.COMPANY_LOGO_PATH || './assets/logo.png',
  igvRate: 0.18,
});
