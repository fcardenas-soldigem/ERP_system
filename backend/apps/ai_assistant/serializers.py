from rest_framework import serializers
from .models import Conversation, Message, AIInsight, AIAction

class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ['id', 'empresa', 'usuario', 'thread_id', 'title', 'created_at', 'updated_at']
        read_only_fields = ['empresa', 'usuario']

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'conversation', 'content', 'role', 'created_at']
        read_only_fields = ['conversation']

class AIInsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIInsight
        fields = ['id', 'empresa', 'tipo', 'contenido', 'created_at', 'is_active']
        read_only_fields = ['empresa']

class AIActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAction
        fields = ['id', 'conversation', 'tipo', 'datos', 'resultado', 'status', 'created_at', 'updated_at']
        read_only_fields = ['conversation'] 