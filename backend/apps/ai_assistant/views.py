"""
Endpoints del asistente IA. Todos los chats (Jorge, ventas, compras) pasan por
`AsistenteChat` sobre la capa `llm_client` (Vertex AI / OpenAI-compatible). El
historial vive en Conversation/Message, aislado por empresa Y usuario.

Contrato con el frontend (sin cambios de forma):
  POST /threads/                        → 201 {thread_id, conversation_id, message}
  POST /threads/<tid>/messages/ {content} → {message}
  GET  /threads/<tid>/messages/         → {messages: [{role, content, created_at}]}
  POST /threads-tools/                  → {thread_id, conversation_id, message}
  POST /threads-tools/<tid>/messages/   → {message}
  GET  /threads-tools/<tid>/messages/   → {messages}
  POST /ventas-assistant/ | /compras-assistant/            → {thread_id, conversation_id, assistant}
  POST /…-assistant/<tid>/messages/ {message}              → {response}
  GET  /…-assistant/<tid>/messages/                        → {messages}
  GET  /…-assistant/conversation/                          → {thread_id, conversation_id, assistant}

Errores: 503 si el proveedor de IA no está configurado (credenciales/permiso/modelo),
502 si el proveedor falla o no responde en LLM_TIMEOUT s, 404 si la conversación no
es del usuario. Nunca se devuelve ni se loguea el contenido de prompts o respuestas.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Conversation, Message, AIInsight
from .serializers import ConversationSerializer, MessageSerializer, AIInsightSerializer
from . import services as ai_services
from .services.chat import AsistenteChat, crear_conversacion
from .services.llm_client import LLMNoConfigurado, LLMNoDisponible
from .services.perfiles import get_perfil
from apps.core.errors import respuesta_error, error_interno


# ── Helpers ──────────────────────────────────────────────────────────────────

def _respuesta_llm(exc):
    """Traduce los errores con nombre de la capa LLM a HTTP. Devuelve None si no aplica."""
    if isinstance(exc, LLMNoConfigurado):
        return Response({'error': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    if isinstance(exc, LLMNoDisponible):
        return Response({'error': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    return None


def _conversacion_del_usuario(request, thread_id, perfil):
    """La conversación debe ser del usuario, de su empresa y del perfil del endpoint."""
    return get_object_or_404(
        Conversation, thread_id=thread_id, usuario=request.user,
        empresa=request.user.empresa, perfil=perfil.clave)


def _mensajes(conversation):
    return [{'role': m.role, 'content': m.content, 'created_at': m.created_at}
            for m in Message.objects.filter(conversation=conversation).order_by('created_at', 'id')]


def _enviar(request, thread_id, perfil, campo_entrada, campo_salida, mensaje_error):
    contenido = request.data.get(campo_entrada)
    if not contenido or not str(contenido).strip():
        return Response({'error': f'{campo_entrada} es requerido'}, status=status.HTTP_400_BAD_REQUEST)
    conversation = _conversacion_del_usuario(request, thread_id, perfil)
    try:
        texto = AsistenteChat(conversation, perfil).enviar(str(contenido))
    except (LLMNoConfigurado, LLMNoDisponible) as e:
        return _respuesta_llm(e)
    except Exception as e:  # noqa: BLE001
        return error_interno(e, mensaje_error)
    return Response({campo_salida: texto})


def _crear(request, perfil, bienvenida, extra=None, http_status=status.HTTP_200_OK):
    if not request.user.empresa_id:
        return Response({'error': 'Usuario no tiene empresa asignada'}, status=status.HTTP_400_BAD_REQUEST)
    conversation = crear_conversacion(request.user, perfil)
    Message.objects.create(conversation=conversation, role='assistant', content=bienvenida)
    cuerpo = {'thread_id': conversation.thread_id, 'conversation_id': conversation.id}
    cuerpo.update(extra or {})
    return Response(cuerpo, status=http_status)


def _bienvenida_jorge(user):
    nombre = user.get_full_name() or user.username
    empresa = user.empresa.nombre if user.empresa else 'tu empresa'
    return (f"¡Hola {nombre}! 👋\n\nSoy **Jorge**, tu analista comercial en el ERP de {empresa}.\n\n"
            "Puedo ayudarte con:\n"
            "📊 **Ventas** — tendencias, totales y métricas por período\n"
            "📈 **Clientes** — top compradores y comportamiento\n"
            "📦 **Inventario** — stock bajo, rotación y alertas\n"
            "💡 **Consultas libres** — oportunidades y proveedores\n\n"
            "Ejemplos: \"¿Cómo van las ventas este mes?\", \"¿Qué productos tienen stock bajo?\", "
            "\"¿Quiénes son mis mejores clientes?\"")


# ── CRUD de historial (router) ───────────────────────────────────────────────

class ConversationViewSet(viewsets.ModelViewSet):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer

    def get_queryset(self):
        # Aislamiento por USUARIO además de por empresa: las conversaciones con la IA
        # son privadas; dos usuarios de la misma empresa no se ven entre sí.
        return Conversation.objects.filter(
            empresa=self.request.user.empresa, usuario=self.request.user)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa, usuario=self.request.user)


class MessageViewSet(viewsets.ModelViewSet):
    """Historial plano/anidado. Solo CRUD: el chat (respuesta del modelo) va por /threads*/."""
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

    def get_queryset(self):
        qs = Message.objects.filter(
            conversation__empresa=self.request.user.empresa,
            conversation__usuario=self.request.user)
        conversation_id = self.kwargs.get('conversation_pk')
        if conversation_id is not None:
            qs = qs.filter(conversation_id=conversation_id)
        return qs

    def perform_create(self, serializer):
        # La conversación debe ser de la empresa Y del usuario (404 si no).
        conversation_id = self.kwargs.get('conversation_pk')
        conversation = get_object_or_404(
            Conversation, id=conversation_id, empresa=self.request.user.empresa,
            usuario=self.request.user)
        serializer.save(conversation=conversation)


class AIInsightViewSet(viewsets.ModelViewSet):
    queryset = AIInsight.objects.all()
    serializer_class = AIInsightSerializer

    def get_queryset(self):
        return AIInsight.objects.filter(empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)


class AIAssistantViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(
            empresa=self.request.user.empresa,
            usuario=self.request.user
        )

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        conversation = self.get_object()
        content = request.data.get('content')
        if not content:
            return Response({'error': 'El contenido del mensaje es requerido'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            texto = AsistenteChat(conversation).enviar(str(content))
        except (LLMNoConfigurado, LLMNoDisponible) as e:
            return _respuesta_llm(e)
        except Exception as e:  # noqa: BLE001
            return error_interno(e, 'Error al procesar el mensaje')
        return Response({'message': texto})

    @action(detail=True, methods=['post'])
    def upload_file(self, request, pk=None):
        conversation = self.get_object()
        file = request.FILES.get('file')
        tipo = request.data.get('tipo')  # 'compra' o 'venta'

        if not file:
            return Response({'error': 'Archivo requerido'}, status=status.HTTP_400_BAD_REQUEST)
        if not tipo or tipo not in ['compra', 'venta']:
            return Response({'error': 'Tipo de archivo inválido'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            assistant = ai_services.AIAssistantService(conversation)
            result = assistant.procesar_archivo(file, tipo)
            return Response(result)
        except Exception as e:  # noqa: BLE001
            return respuesta_error(e, 'Error al procesar el archivo')

    @action(detail=False, methods=['post'])
    def create_conversation(self, request):
        conversation = crear_conversacion(request.user, get_perfil('jorge'))
        Message.objects.create(conversation=conversation, role='assistant',
                               content=_bienvenida_jorge(request.user))
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)


# ── Chat general de Jorge (/threads/) ────────────────────────────────────────

class ThreadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            perfil = get_perfil('jorge')
            if not request.user.empresa_id:
                return Response({'error': 'Usuario no tiene empresa asignada'},
                                status=status.HTTP_400_BAD_REQUEST)
            conversation = crear_conversacion(request.user, perfil, titulo='Nueva Conversación')
            bienvenida = self._bienvenida(request.user, conversation)
            Message.objects.create(conversation=conversation, role='assistant', content=bienvenida)
            return Response({'thread_id': conversation.thread_id, 'conversation_id': conversation.id,
                             'message': bienvenida}, status=status.HTTP_201_CREATED)
        except Exception as e:  # noqa: BLE001
            return error_interno(e, 'Error al crear la conversación')

    @staticmethod
    def _bienvenida(user, conversation):
        """Bienvenida con cifras reales de la BD (sin llamar al modelo)."""
        empresa = user.empresa.nombre
        try:
            ctx = ai_services.AIAssistantService(conversation).get_sistema_context() or {}
        except Exception:  # noqa: BLE001 - la bienvenida nunca debe fallar
            ctx = {}
        vm = ctx.get('ventas_mes') or {}
        cm = ctx.get('compras_mes') or {}
        bajo = ctx.get('productos_stock_bajo_count', 0) or 0
        return (f"¡Hola! 🤖 Soy Jorge, tu asistente de {empresa}.\n\n"
                f"📊 ESTADO ACTUAL:\n"
                f"• Ventas este mes: {vm.get('cantidad', 0)} por S/ {float(vm.get('total') or 0):,.2f}\n"
                f"• Compras este mes: {cm.get('cantidad', 0)} por S/ {float(cm.get('total') or 0):,.2f}\n"
                f"• Productos con stock bajo: {bajo}\n\n"
                "🚀 ¿En qué puedo ayudarte? Ventas, inventario, clientes o cualquier consulta sobre tus datos.")


class MessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, thread_id):
        return _enviar(request, thread_id, get_perfil('jorge'), 'content', 'message',
                       'Error al procesar el mensaje')

    def get(self, request, thread_id):
        conversation = _conversacion_del_usuario(request, thread_id, get_perfil('jorge'))
        return Response({'messages': _mensajes(conversation)})


# ── Jorge con herramientas (/threads-tools/) ─────────────────────────────────

class ThreadViewWithTools(APIView):
    """Crea una conversación con Jorge (analista con herramientas de análisis)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            return _crear(request, get_perfil('jorge'), _bienvenida_jorge(request.user),
                          extra={'message': _bienvenida_jorge(request.user)})
        except Exception as e:  # noqa: BLE001
            return error_interno(e, 'Error al crear la conversación')


class MessageViewWithTools(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, thread_id):
        return _enviar(request, thread_id, get_perfil('jorge'), 'content', 'message',
                       'Error al procesar el mensaje')

    def get(self, request, thread_id):
        conversation = _conversacion_del_usuario(request, thread_id, get_perfil('jorge'))
        return Response({'messages': _mensajes(conversation)})


# ── Asistentes de módulo (ventas / compras) ──────────────────────────────────

_BIENVENIDA_VENTAS = ("🛒 ¡Hola! Soy tu asistente de ventas. Puedo:\n\n"
                      "• 🔍 Buscar clientes y productos\n• 📝 Registrar ventas\n"
                      "• 💰 Calcular totales\n\n¿En qué te ayudo?")
_BIENVENIDA_COMPRAS = ("📦 ¡Hola! Soy tu asistente de compras. Puedo:\n\n"
                       "• 🔍 Buscar proveedores, productos y almacenes\n• 📝 Registrar compras\n\n"
                       "¿En qué te ayudo?")


def _get_or_create_activa(request, perfil, bienvenida):
    if not request.user.empresa_id:
        return Response({'error': 'Usuario no tiene empresa asignada'}, status=status.HTTP_400_BAD_REQUEST)
    conversation = (Conversation.objects
                    .filter(usuario=request.user, empresa=request.user.empresa, perfil=perfil.clave)
                    .exclude(thread_id__isnull=True).exclude(thread_id='')
                    .order_by('-updated_at').first())
    if conversation is None:
        conversation = crear_conversacion(request.user, perfil)
        Message.objects.create(conversation=conversation, role='assistant', content=bienvenida)
    return Response({'thread_id': conversation.thread_id, 'conversation_id': conversation.id,
                     'assistant': perfil.clave})


class VentasAssistantView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            return _crear(request, get_perfil('ventas'), _BIENVENIDA_VENTAS, extra={'assistant': 'ventas'})
        except Exception as e:  # noqa: BLE001
            return error_interno(e, 'Error al crear la conversación de ventas')


class VentasMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, thread_id):
        return _enviar(request, thread_id, get_perfil('ventas'), 'message', 'response',
                       'Error al procesar el mensaje')

    def get(self, request, thread_id):
        conversation = _conversacion_del_usuario(request, thread_id, get_perfil('ventas'))
        return Response({'messages': _mensajes(conversation)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_or_create_ventas_conversation(request):
    try:
        return _get_or_create_activa(request, get_perfil('ventas'), _BIENVENIDA_VENTAS)
    except Exception as e:  # noqa: BLE001
        return error_interno(e, 'Error al obtener la conversación de ventas')


class ComprasAssistantView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            return _crear(request, get_perfil('compras'), _BIENVENIDA_COMPRAS, extra={'assistant': 'compras'})
        except Exception as e:  # noqa: BLE001
            return error_interno(e, 'Error al crear la conversación de compras')


class ComprasMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, thread_id):
        return _enviar(request, thread_id, get_perfil('compras'), 'message', 'response',
                       'Error al procesar el mensaje')

    def get(self, request, thread_id):
        conversation = _conversacion_del_usuario(request, thread_id, get_perfil('compras'))
        return Response({'messages': _mensajes(conversation)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_or_create_compras_conversation(request):
    try:
        return _get_or_create_activa(request, get_perfil('compras'), _BIENVENIDA_COMPRAS)
    except Exception as e:  # noqa: BLE001
        return error_interno(e, 'Error al obtener la conversación de compras')


# ── Analista comercial (Claude; fuera del alcance de la capa LLM) ────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generar_reporte_ventas(request):
    """
    Genera reporte inteligente de ventas usando Claude 3.5 Sonnet
    """
    try:
        periodo = request.data.get('periodo', 'último_mes')

        # Validar período
        periodos_validos = ['último_mes', 'último_trimestre', 'último_año']
        if periodo not in periodos_validos:
            return Response(
                {'error': f'Período no válido. Usar: {", ".join(periodos_validos)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Crear servicio de análisis comercial
        analista = ai_services.AnalistaComercialService(request.user.empresa)

        # Generar reporte
        reporte = analista.generar_reporte_ventas(periodo)

        return Response({
            'success': True,
            'reporte': reporte,
            'periodo': periodo,
            'timestamp': timezone.now()
        })

    except Exception as e:
        return error_interno(e, 'Error al generar reporte')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analizar_inventario_inteligente(request):
    """
    Análisis predictivo de inventario con alertas inteligentes
    """
    try:
        # Crear servicio de análisis comercial
        analista = ai_services.AnalistaComercialService(request.user.empresa)

        # Generar análisis
        analisis = analista.analizar_inventario_inteligente()

        return Response({
            'success': True,
            'analisis': analisis,
            'timestamp': timezone.now()
        })

    except Exception as e:
        return error_interno(e, 'Error al analizar inventario')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detectar_oportunidades_comerciales(request):
    """
    Detecta oportunidades comerciales basadas en análisis de datos
    """
    try:
        # Crear servicio de análisis comercial
        analista = ai_services.AnalistaComercialService(request.user.empresa)

        # Detectar oportunidades
        oportunidades = analista.detectar_oportunidades_comerciales()

        return Response({
            'success': True,
            'oportunidades': oportunidades,
            'timestamp': timezone.now()
        })

    except Exception as e:
        return error_interno(e, 'Error al detectar oportunidades')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def consulta_analista_libre(request):
    """
    Consulta libre al analista comercial - el usuario puede hacer cualquier pregunta
    """
    try:
        consulta = request.data.get('consulta', '')

        if not consulta:
            return Response(
                {'error': 'La consulta es requerida'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Crear servicio de análisis comercial
        analista = ai_services.AnalistaComercialService(request.user.empresa)

        # Obtener contexto empresarial completo
        contexto = analista._obtener_datos_comerciales_completos()

        prompt = f"""
        Eres un Analista Comercial Senior especializado en ERP. Tienes acceso a todos los datos de la empresa.

        CONTEXTO EMPRESARIAL:
        {contexto}

        CONSULTA DEL USUARIO:
        {consulta}

        INSTRUCCIONES:
        - Responde basándote en los datos reales de la empresa
        - Proporciona insights específicos y accionables
        - Si necesitas datos adicionales, especifica qué información sería útil
        - Mantén un tono profesional pero accesible
        - Incluye números y métricas cuando sea relevante
        """

        response = analista.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )

        respuesta = response.content[0].text

        return Response({
            'success': True,
            'respuesta': respuesta,
            'consulta': consulta,
            'timestamp': timezone.now()
        })

    except Exception as e:
        return error_interno(e, 'Error al procesar consulta')
