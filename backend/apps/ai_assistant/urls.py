from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import (
    ConversationViewSet, 
    MessageViewSet, 
    AIInsightViewSet,
    AIAssistantViewSet,
    ThreadView,
    MessageView,
    FileUploadView,
    ThreadViewWithTools,
    MessageViewWithTools,
    VentasAssistantView,
    VentasMessageView,
    get_or_create_ventas_conversation,
    ComprasAssistantView,
    ComprasMessageView,
    get_or_create_compras_conversation,
    generar_reporte_ventas,
    analizar_inventario_inteligente,
    detectar_oportunidades_comerciales,
    consulta_analista_libre
)

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet)
router.register(r'messages', MessageViewSet)
router.register(r'insights', AIInsightViewSet)
router.register(r'assistant', AIAssistantViewSet, basename='assistant')

# Rutas anidadas para mensajes
conversations_router = routers.NestedDefaultRouter(router, r'conversations', lookup='conversation')
conversations_router.register(r'messages', MessageViewSet, basename='conversation-messages')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(conversations_router.urls)),
    path('threads/', ThreadView.as_view(), name='thread-list'),
    path('threads/<str:thread_id>/messages/', MessageView.as_view(), name='message-list'),
    path('threads-tools/', ThreadViewWithTools.as_view(), name='thread-tools-list'),
    path('threads-tools/<str:thread_id>/messages/', MessageViewWithTools.as_view(), name='message-tools-list'),
    path('files/upload/', FileUploadView.as_view(), name='file-upload'),
    # Rutas del asistente de ventas especializado
    path('ventas-assistant/', VentasAssistantView.as_view(), name='ventas-assistant'),
    path('ventas-assistant/<str:thread_id>/messages/', VentasMessageView.as_view(), name='ventas-messages'),
    path('ventas-assistant/conversation/', get_or_create_ventas_conversation, name='ventas-conversation'),
    # Rutas del asistente de compras especializado
    path('compras-assistant/', ComprasAssistantView.as_view(), name='compras-assistant'),
    path('compras-assistant/<str:thread_id>/messages/', ComprasMessageView.as_view(), name='compras-messages'),
    path('compras-assistant/conversation/', get_or_create_compras_conversation, name='compras-conversation'),
    # Rutas del analista Jorge
    path('analista/reporte-ventas/', generar_reporte_ventas, name='generar-reporte-ventas'),
    path('analista/inventario/', analizar_inventario_inteligente, name='analizar-inventario'),
    path('analista/oportunidades/', detectar_oportunidades_comerciales, name='detectar-oportunidades'),
    path('analista/consulta/', consulta_analista_libre, name='consulta-analista-libre'),
] 