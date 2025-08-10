import os
from django.db import models
from django.conf import settings
from apps.empresas.models import Empresa
from django.contrib.auth import get_user_model

User = get_user_model()

class Conversation(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    thread_id = models.CharField(max_length=255, null=True, blank=True)
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