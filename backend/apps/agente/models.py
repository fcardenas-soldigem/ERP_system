"""
Modelos del agente MCP (Fase 2, base de solo lectura).

- ApiToken: credencial larga, revocable, por empresa, para el MCP remoto. Se guarda
  SOLO el hash (sha256) y un prefijo visible; el token en claro se muestra una vez.
- AgenteAccionLog: auditoría de cada llamada a una herramienta del MCP.
"""
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.empresas.models import Empresa

TOKEN_PREFIX = 'sgm_'
DEFAULT_EXPIRY_DAYS = 90


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


class ApiToken(models.Model):
    """Token de API por empresa para el servidor MCP del ERP."""

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='api_tokens')
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='api_tokens_creados',
    )
    nombre = models.CharField(max_length=120, help_text='Etiqueta legible, p. ej. "Agente intake diario".')
    token_prefix = models.CharField(max_length=16, help_text='Prefijo visible del token (sgm_ab12…).')
    token_hash = models.CharField(max_length=64, unique=True, help_text='sha256 del token; el token en claro no se guarda.')
    scopes = models.CharField(max_length=64, default='mcp:read', help_text='Alcance. Inicial: mcp:read (solo lectura).')
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Token de API'
        verbose_name_plural = 'Tokens de API'
        indexes = [models.Index(fields=['token_hash'])]

    def __str__(self):
        return f'{self.nombre} ({self.token_prefix}…) · {self.empresa_id}'

    @classmethod
    def generar(cls, empresa, nombre, creado_por=None, dias=DEFAULT_EXPIRY_DAYS, scopes='mcp:read'):
        """Crea un token nuevo. Devuelve (instancia, token_en_claro). El claro NO se persiste."""
        raw = TOKEN_PREFIX + secrets.token_urlsafe(32)  # >= 32 bytes de entropía
        obj = cls.objects.create(
            empresa=empresa,
            nombre=nombre,
            creado_por=creado_por,
            token_prefix=raw[:12],                 # 'sgm_' + 8 chars
            token_hash=_hash_token(raw),
            scopes=scopes,
            expires_at=timezone.now() + timedelta(days=dias) if dias else None,
        )
        return obj, raw

    @property
    def activo(self) -> bool:
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at <= timezone.now():
            return False
        return True

    @property
    def estado(self) -> str:
        if self.revoked_at is not None:
            return 'revocado'
        if self.expires_at is not None and self.expires_at <= timezone.now():
            return 'expirado'
        return 'activo'

    def revocar(self):
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=['revoked_at'])


class AgenteAccionLog(models.Model):
    """Auditoría: una fila por cada llamada a una herramienta del MCP."""

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='agente_logs')
    token = models.ForeignKey(ApiToken, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs')
    herramienta = models.CharField(max_length=64)
    argumentos = models.JSONField(default=dict, blank=True, help_text='Entrada saneada (sin datos sensibles).')
    resultado_resumen = models.CharField(max_length=300, blank=True)
    ok = models.BooleanField(default=True)
    duracion_ms = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Log de acción del agente'
        verbose_name_plural = 'Logs de acciones del agente'

    def __str__(self):
        return f'{self.herramienta} · empresa {self.empresa_id} · {"ok" if self.ok else "error"}'
