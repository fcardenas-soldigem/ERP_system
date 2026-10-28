"""
Modelos del canal de mensajería (Bloque 1).

Principio (FASE2_SPEC §1 y B6): la IA solo PREPARA borradores; la persona
confirma. Nada se crea en el ERP sin un toque explícito en "Confirmar".
"""
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.empresas.models import Empresa


def _codigo_vinculacion():
    # 8 caracteres legibles (sin 0/O/1/I): se tipea en el teléfono
    alfabeto = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(alfabeto) for _ in range(8))


class VinculacionTelegram(models.Model):
    """chat_id de Telegram ↔ usuario del ERP (uno a uno, A3).

    El bot es uno solo para todas las empresas: la empresa sale SIEMPRE del
    usuario vinculado, nunca del mensaje.
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vinculacion_telegram',
    )
    chat_id = models.BigIntegerField(null=True, blank=True, unique=True)
    # código pendiente de canje (10 min); al canjearse se limpia
    codigo = models.CharField(max_length=8, default=_codigo_vinculacion, db_index=True)
    codigo_expira = models.DateTimeField()
    vinculado_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Vinculación de Telegram'
        verbose_name_plural = 'Vinculaciones de Telegram'

    VIGENCIA_CODIGO = timedelta(minutes=10)

    @property
    def vinculado(self):
        return self.chat_id is not None

    @property
    def codigo_vigente(self):
        return not self.vinculado and timezone.now() < self.codigo_expira

    def regenerar_codigo(self):
        self.codigo = _codigo_vinculacion()
        self.codigo_expira = timezone.now() + self.VIGENCIA_CODIGO
        self.save(update_fields=['codigo', 'codigo_expira'])

    def __str__(self):
        estado = f'chat {self.chat_id}' if self.vinculado else 'pendiente'
        return f'{self.usuario} · {estado}'


class UpdateProcesado(models.Model):
    """Idempotencia del webhook (A2): un update de Telegram se procesa una vez."""

    canal = models.CharField(max_length=20, default='telegram')
    update_id = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['canal', 'update_id'], name='uniq_update_por_canal'),
        ]


class BorradorAgente(models.Model):
    """Documento preparado por la IA a la espera de confirmación humana (B6)."""

    TIPOS = [
        ('cotizacion', 'Cotización'),
        ('venta', 'Venta'),
        ('conversion_venta', 'Conversión de cotización a venta'),
        ('cobro', 'Cobro'),
        ('estado_operativo', 'Cambio de estado operativo'),
    ]
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('confirmado', 'Confirmado'),
        ('cancelado', 'Cancelado'),
        ('expirado', 'Expirado'),
        # un borrador nuevo del mismo chat lo desplaza: solo hay UNO pendiente
        ('reemplazado', 'Reemplazado'),
    ]
    VIGENCIA = timedelta(minutes=30)

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='borradores_agente')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='borradores_agente')
    tipo = models.CharField(max_length=20, choices=TIPOS)
    payload = models.JSONField(default=dict)
    estado = models.CharField(max_length=12, choices=ESTADOS, default='pendiente', db_index=True)
    canal = models.CharField(max_length=20, default='telegram')
    id_externo = models.CharField(max_length=64, blank=True, help_text='chat_id u otro id del canal')
    # al confirmar: a qué documento real dio origen
    documento_id = models.IntegerField(null=True, blank=True)
    documento_numero = models.CharField(max_length=40, blank=True)
    # id del mensaje de Telegram que muestra ESTE borrador (sus botones): al
    # reemplazarlo se desactivan, y un callback que llegue desde otro mensaje
    # se detecta como desactualizado (evidencia de prod 2026-10-28)
    mensaje_bot_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resuelto_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Borrador del agente'
        verbose_name_plural = 'Borradores del agente'

    @property
    def expirado(self):
        return self.estado == 'pendiente' and timezone.now() > self.created_at + self.VIGENCIA

    def marcar(self, estado):
        self.estado = estado
        self.resuelto_at = timezone.now()
        self.save(update_fields=['estado', 'resuelto_at'])

    def __str__(self):
        return f'{self.get_tipo_display()} · {self.estado} · {self.usuario}'


class MensajeConversacion(models.Model):
    """Memoria corta del chat (fix V2 punto 3): el agente recibe los últimos N
    mensajes para que «Cliente Uhman» complete el borrador en vez de perderse.
    Solo texto plano acotado; nada de payloads ni datos del ERP."""

    ROLES = [('user', 'Usuario'), ('assistant', 'Bot')]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='mensajes_canal')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='mensajes_canal')
    canal = models.CharField(max_length=20, default='telegram')
    id_externo = models.CharField(max_length=64, help_text='chat_id u otro id del canal')
    rol = models.CharField(max_length=10, choices=ROLES)
    texto = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['usuario', 'id_externo', '-created_at'])]
        verbose_name = 'Mensaje de conversación'
        verbose_name_plural = 'Mensajes de conversación'

    def __str__(self):
        return f'{self.rol} · {self.id_externo} · {self.texto[:40]}'
