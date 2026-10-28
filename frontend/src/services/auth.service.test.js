import { describe, expect, it } from 'vitest';
import { mensajeErrorLogin, MENSAJE_SIN_CONEXION, MENSAJE_SIN_EMPRESA } from './auth.service';

describe('mensajeErrorLogin (QW5)', () => {
  it('error de red (sin response) → mensaje de conexión, no "Credenciales inválidas"', () => {
    expect(mensajeErrorLogin(new Error('Network Error'))).toBe(MENSAJE_SIN_CONEXION);
  });
  it('401 del backend → credenciales', () => {
    expect(mensajeErrorLogin({ response: { status: 401, data: {} } })).toBe('Credenciales inválidas');
  });
  it('403 → sin empresa', () => {
    expect(mensajeErrorLogin({ response: { status: 403, data: {} } })).toBe(MENSAJE_SIN_EMPRESA);
  });
  it('500 → problema del servidor', () => {
    expect(mensajeErrorLogin({ response: { status: 500, data: {} } })).toMatch(/servidor/);
  });
  it('detalle del backend se conserva', () => {
    expect(mensajeErrorLogin({ response: { status: 400, data: { detail: 'Cuenta bloqueada' } } })).toBe('Cuenta bloqueada');
  });
});
