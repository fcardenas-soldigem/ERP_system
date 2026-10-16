import os
from django.db import models
from django.conf import settings
from apps.empresas.models import Empresa
from django.contrib.auth import get_user_model

User = get_user_model()

class Conversation(models.Model):
    PERFIL_CHOICES = [
        ('jorge', 'Jorge (analista)'),
        ('ventas', 'Asistente de ventas'),
        ('compras', 'Asistente de compras'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    # Antes: id del thread de OpenAI. Ahora: identificador opaco nuestro (conv_<uuid>);
    # el historial vive en Message. Se conserva el nombre por el contrato del frontend.
    thread_id = models.CharField(max_length=255, null=True, blank=True)
    # Qué asistente (system prompt + tools) atiende esta conversación.
    perfil = models.CharField(max_length=10, choices=PERFIL_CHOICES, default='jorge')
    title = models.CharField(max_length=255, default="Nueva Conversación")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

class Message(models.Model):
    ROLE_CHOICES = [
        ('user', 'Usuario'),
        ('assistant', 'Asistente'),
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

class AIInsight(models.Model):
    TIPO_CHOICES = [
        ('compra', 'Compra'),
        ('venta', 'Venta'),
        ('inventario', 'Inventario'),
    ]
    
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    contenido = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

class AIAction(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'En Progreso'),
        ('completed', 'Completado'),
        ('completed_with_errors', 'Completado con Errores'),
        ('failed', 'Fallido')
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=50)
    datos = models.JSONField(default=dict)
    resultado = models.JSONField(default=dict, null=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='in_progress')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at'] 

class UsoLLM(models.Model):
    """Tokens consumidos por empresa, día y modelo (sin contenido de prompts)."""
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='uso_llm')
    fecha = models.DateField()
    modelo = models.CharField(max_length=80)
    tokens_entrada = models.BigIntegerField(default=0)
    tokens_salida = models.BigIntegerField(default=0)
    llamadas = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'fecha', 'modelo'], name='uso_llm_empresa_fecha_modelo'),
        ]
        ordering = ['-fecha']

    @classmethod
    def registrar(cls, empresa, modelo, tokens_entrada, tokens_salida):
        from .services.chat import registrar_uso
        registrar_uso(empresa, modelo, tokens_entrada, tokens_salida)

    def __str__(self):
        return f'{self.empresa_id} {self.fecha} {self.modelo}: {self.tokens_entrada}/{self.tokens_salida}'
