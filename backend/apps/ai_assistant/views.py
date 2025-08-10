from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Conversation, Message, AIInsight
from .serializers import ConversationSerializer, MessageSerializer, AIInsightSerializer
from . import services as ai_services
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from openai import OpenAI
from django.conf import settings
import json
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone

def get_openai_client():
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return client
    except Exception as e:
        print(f"Error al crear cliente OpenAI: {str(e)}")
        raise

class ConversationViewSet(viewsets.ModelViewSet):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(empresa=self.request.user.empresa)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa, usuario=self.request.user)

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

    def get_queryset(self):
        conversation_id = self.kwargs.get('conversation_pk')
        return Message.objects.filter(conversation_id=conversation_id)

    def perform_create(self, serializer):
        conversation_id = self.kwargs.get('conversation_pk')
        conversation = Conversation.objects.get(id=conversation_id)
        serializer.save(conversation=conversation)

        try:
            # Crear una instancia del cliente de OpenAI
            client = get_openai_client()

            # Obtener el contexto de la conversación
            messages = Message.objects.filter(conversation=conversation).order_by('created_at')
            conversation_history = [
                {"role": "system", "content": "Eres un asistente de IA especializado en ayudar con tareas de ERP."}
            ]
            
            for msg in messages:
                role = "assistant" if msg.is_from_assistant else "user"
                conversation_history.append({"role": role, "content": msg.content})

            # Generar respuesta
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=conversation_history,
                temperature=0.7,
                max_tokens=1000
            )

            # Guardar la respuesta del asistente
            assistant_message = response.choices[0].message.content
            Message.objects.create(
                conversation=conversation,
                content=assistant_message,
                is_from_assistant=True
            )

        except Exception as e:
            print(f"Error en MessageViewSet: {str(e)}")  # Para debugging
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def upload(self, request, conversation_pk=None):
        try:
            file = request.FILES['file']
            tipo = request.data.get('tipo')

            # Crear una instancia del cliente de OpenAI
            client = get_openai_client()

            # Leer el contenido del archivo
            file_content = file.read().decode('utf-8')

            # Preparar el prompt según el tipo de archivo
            if tipo == 'compra':
                prompt = f"Analiza el siguiente archivo de compra y proporciona insights relevantes:\n\n{file_content}"
            else:
                prompt = f"Analiza el siguiente archivo de venta y proporciona insights relevantes:\n\n{file_content}"

            # Generar análisis
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Eres un asistente de IA especializado en análisis de documentos de ERP."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            # Guardar el mensaje con el análisis
            conversation = Conversation.objects.get(id=conversation_pk)
            Message.objects.create(
                conversation=conversation,
                content=response.choices[0].message.content,
                is_from_assistant=True
            )

            return Response({"message": "Archivo analizado exitosamente"})

        except Exception as e:
            print(f"Error al analizar archivo: {str(e)}")  # Para debugging
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
            return Response(
                {'error': 'El contenido del mensaje es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Crear mensaje del usuario
        Message.objects.create(
            conversation=conversation,
            content=content,
            tipo='text',
            is_from_assistant=False
        )

        # Procesar con el asistente
        assistant = ai_services.AIAssistantService(conversation)
        response = assistant.process_message(content)

        return Response({'message': 'Mensaje enviado correctamente'})

    @action(detail=True, methods=['post'])
    def upload_file(self, request, pk=None):
        conversation = self.get_object()
        file = request.FILES.get('file')
        tipo = request.data.get('tipo')  # 'compra' o 'venta'

        if not file:
            return Response(
                {'error': 'Archivo requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not tipo or tipo not in ['compra', 'venta']:
            return Response(
                {'error': 'Tipo de archivo inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            assistant = ai_services.AIAssistantService(conversation)
            result = assistant.procesar_archivo(file, tipo)
            return Response(result)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def create_conversation(self, request):
        conversation = Conversation.objects.create(
            empresa=request.user.empresa,
            usuario=request.user
        )
        
        # Mensaje de bienvenida
        Message.objects.create(
            conversation=conversation,
            content="¡Hola! Soy Jorge, tu asistente virtual. ¿En qué puedo ayudarte hoy?",
            tipo='text',
            is_from_assistant=True
        )
        
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)

class ThreadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            print("Iniciando creación de conversación...")
            client = get_openai_client()
            
            # Crear un nuevo thread para cada conversación
            thread = client.beta.threads.create()
            thread_id = thread.id
            
            # Crear la conversación en la base de datos
            conversation = Conversation.objects.create(
                usuario=request.user,
                empresa=request.user.empresa,
                thread_id=thread_id,
                title="Nueva Conversación"
            )
            
            # ✨ USAR AIAssistantService para obtener mensaje personalizado
            try:
                assistant = ai_services.AIAssistantService(conversation)
                sistema_context = assistant.get_sistema_context()
                user_history = sistema_context.get('user_profile', {})
            except Exception as e:
                print(f"Error obteniendo contexto del sistema: {e}")
                # Fallback a información básica
                sistema_context = {
                    'empresa': {'nombre': request.user.empresa.nombre},
                    'ventas_mes': {'cantidad': 0, 'total': 0},
                    'compras_mes': {'cantidad': 0, 'total': 0},
                    'productos_stock_bajo_count': 0
                }
                user_history = {}
            
            # Crear mensaje de bienvenida personalizado con datos reales y memoria
            if user_history.get('total_conversations', 0) > 0:
                # Usuario recurrente - mensaje personalizado
                welcome_message = f"""¡Hola de nuevo! 🤖 Soy Jorge, tu asistente virtual personal de {sistema_context.get('empresa', {}).get('nombre', 'tu empresa')}.

🧠 TE RECUERDO PERFECTAMENTE:
• Hemos tenido {user_history.get('total_conversations', 0)} conversaciones anteriores
• Tus temas favoritos: {', '.join(user_history.get('user_preferences', {}).get('most_discussed_topics', ['Explorando el sistema']))}
• Nivel de experiencia: {user_history.get('user_preferences', {}).get('engagement_level', 'Intermedio')}

📊 ESTADO ACTUAL DE TU NEGOCIO:
• Ventas este mes: {sistema_context.get('ventas_mes', {}).get('cantidad', 0)} ventas por S/ {sistema_context.get('ventas_mes', {}).get('total', 0) or 0:,.2f}
• Compras este mes: {sistema_context.get('compras_mes', {}).get('cantidad', 0)} compras por S/ {sistema_context.get('compras_mes', {}).get('total', 0) or 0:,.2f}
• Productos con stock bajo: {sistema_context.get('productos_stock_bajo_count', 0)} productos

🚀 Basándome en nuestras conversaciones anteriores, ¿te gustaría que revisemos tus {', '.join(user_history.get('user_preferences', {}).get('most_discussed_topics', ['datos'])[:2])} o prefieres explorar algo nuevo?

¡Tengo acceso completo a todos tus datos en tiempo real y recuerdo todo lo que hemos hablado!"""
            else:
                # Usuario nuevo - mensaje de bienvenida estándar
                welcome_message = f"""¡Hola! 🤖 Soy Jorge, tu asistente virtual personal de {sistema_context.get('empresa', {}).get('nombre', 'tu empresa')}.

🌟 ¡ES TU PRIMERA VEZ! Encantado de conocerte.

📊 ESTADO ACTUAL DE TU NEGOCIO:
• Ventas este mes: {sistema_context.get('ventas_mes', {}).get('cantidad', 0)} ventas por S/ {sistema_context.get('ventas_mes', {}).get('total', 0) or 0:,.2f}
• Compras este mes: {sistema_context.get('compras_mes', {}).get('cantidad', 0)} compras por S/ {sistema_context.get('compras_mes', {}).get('total', 0) or 0:,.2f}
• Productos con stock bajo: {sistema_context.get('productos_stock_bajo_count', 0)} productos

🚀 ¿En qué puedo ayudarte hoy? Te recomiendo empezar explorando:
• Análisis de ventas y tendencias
• Estado del inventario
• Reportes personalizados  
• Cualquier consulta específica de tu ERP

💡 A partir de ahora, recordaré nuestras conversaciones para darte un servicio cada vez más personalizado."""
            
            # Guardar el mensaje en la base de datos
            Message.objects.create(
                conversation=conversation,
                content=welcome_message,
                role='assistant'
            )
            
            return Response({
                'thread_id': thread_id,
                'conversation_id': conversation.id,
                'message': welcome_message
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"Error al crear conversación: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, thread_id):
        try:
            content = request.data.get('content')
            if not content:
                return Response({'error': 'El contenido del mensaje es requerido'}, 
                              status=status.HTTP_400_BAD_REQUEST)

            # Obtener conversación
            conversation = Conversation.objects.get(thread_id=thread_id, usuario=request.user)
            
            # ✨ USAR AIAssistantService con acceso completo a datos
            assistant = ai_services.AIAssistantService(conversation)
            response = assistant.process_message(content)
            
            return Response({
                'message': response
            }, status=status.HTTP_200_OK)
            
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversación no encontrada'}, 
                          status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error al procesar mensaje: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, thread_id):
        try:
            # Crear una instancia del cliente de OpenAI
            client = get_openai_client()
            
            # Obtener los mensajes del thread
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            return Response({
                'messages': [
                    {
                        'role': msg.role,
                        'content': msg.content[0].text.value
                    }
                    for msg in messages.data
                ]
            })
        except Exception as e:
            print(f"Error al obtener mensajes: {str(e)}")  # Para debugging
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class FileUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            if 'file' not in request.FILES:
                return Response(
                    {'error': 'No file provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            file = request.FILES['file']
            client = get_openai_client()
            
            # Crear un archivo en OpenAI
            with file.open('rb') as f:
                response = client.files.create(
                    file=f,
                    purpose='assistants'
                )

            return Response({
                'file_id': response.id
            })

        except Exception as e:
            print(f"Error al subir archivo: {str(e)}")  # Para debugging
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
        return Response(
            {'error': f'Error al generar reporte: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

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
        return Response(
            {'error': f'Error al analizar inventario: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

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
        return Response(
            {'error': f'Error al detectar oportunidades: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

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
        return Response(
            {'error': f'Error al procesar consulta: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class ThreadViewWithTools(APIView):
    """
    Vista para manejar threads con Function Calling habilitado
    Permite crear ventas y compras a través del asistente Jorge
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Crear un nuevo thread con herramientas habilitadas"""
        try:
            from .services.openai_service_tools import OpenAIServiceWithTools
            
            # Verificar que el usuario tenga empresa
            if not request.user.empresa:
                return Response(
                    {'error': 'Usuario no tiene empresa asignada'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Crear servicio con tools
            openai_service = OpenAIServiceWithTools()
            
            # Crear thread
            result = openai_service.create_thread(request.user)
            
            return Response({
                'thread_id': result['thread_id'],
                'conversation_id': result['conversation_id'], 
                'message': result['message']
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error creating thread: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MessageViewWithTools(APIView):
    """
    Vista para enviar mensajes con Function Calling habilitado
    Permite ejecutar funciones como crear_venta y crear_compra
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, thread_id):
        """Enviar mensaje con soporte para tools"""
        try:
            from .services.openai_service_tools import OpenAIServiceWithTools
            
            content = request.data.get('content')
            if not content:
                return Response(
                    {'error': 'Content is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verificar que el usuario tenga empresa
            if not request.user.empresa:
                return Response(
                    {'error': 'Usuario no tiene empresa asignada'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            print(f"🗣️ Usuario {request.user.username} envía: {content}")
            
            # Crear servicio con tools
            openai_service = OpenAIServiceWithTools()
            
            # Enviar mensaje con tools habilitadas
            response = openai_service.send_message_with_tools(
                thread_id=thread_id,
                content=content,
                user=request.user
            )
            
            return Response({'message': response})
            
        except Exception as e:
            print(f"❌ Error en MessageViewWithTools: {str(e)}")
            return Response(
                {'error': f'Error processing message: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request, thread_id):
        """Obtener mensajes del thread"""
        try:
            from .services.openai_service_tools import OpenAIServiceWithTools
            
            openai_service = OpenAIServiceWithTools()
            messages = openai_service.get_thread_messages(thread_id)
            
            return Response({'messages': messages})
            
        except Exception as e:
            return Response(
                {'error': f'Error retrieving messages: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VentasAssistantView(APIView):
    """
    Vista específica para el asistente de ventas integrado en el módulo
    Maneja solo operaciones relacionadas con ventas
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Crear un nuevo thread para el asistente de ventas"""
        try:
            from .services.ventas_assistant import VentasAssistant
            
            assistant = VentasAssistant()
            thread_id, conversation_id = assistant.create_thread(request.user)
            
            return Response({
                'thread_id': thread_id,
                'conversation_id': conversation_id,
                'assistant': 'ventas'
            })
            
        except Exception as e:
            print(f"❌ Error en VentasAssistantView: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VentasMessageView(APIView):
    """
    Vista para enviar mensajes al asistente de ventas
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, thread_id):
        """Enviar mensaje al asistente de ventas"""
        try:
            from .services.ventas_assistant import VentasAssistant
            
            message = request.data.get('message')
            if not message:
                return Response(
                    {'error': 'Mensaje requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            assistant = VentasAssistant()
            response = assistant.send_message(thread_id, message, request.user)
            
            return Response({'response': response})
            
        except Exception as e:
            print(f"❌ Error en VentasMessageView: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request, thread_id):
        """Obtener mensajes del thread de ventas"""
        try:
            conversation = get_object_or_404(
                Conversation, 
                thread_id=thread_id, 
                usuario=request.user
            )
            
            messages = Message.objects.filter(
                conversation=conversation
            ).order_by('created_at')
            
            messages_data = []
            for message in messages:
                messages_data.append({
                    'role': message.role,
                    'content': message.content,
                    'created_at': message.created_at
                })
            
            return Response({'messages': messages_data})
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_or_create_ventas_conversation(request):
    """Obtener conversación activa de ventas o crear una nueva"""
    try:
        from .services.ventas_assistant import VentasAssistant
        
        assistant = VentasAssistant()
        thread_id, conversation_id = assistant.get_or_create_active_conversation(request.user)
        
        return Response({
            'thread_id': thread_id,
            'conversation_id': conversation_id,
            'assistant': 'ventas'
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class ComprasAssistantView(APIView):
    """
    Vista específica para el asistente de compras integrado en el módulo
    Maneja solo operaciones relacionadas con compras
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Crear un nuevo thread para el asistente de compras"""
        try:
            from .services.compras_assistant import ComprasAssistant
            
            assistant = ComprasAssistant()
            thread_id, conversation_id = assistant.create_thread(request.user)
            
            return Response({
                'thread_id': thread_id,
                'conversation_id': conversation_id,
                'assistant': 'compras'
            })
            
        except Exception as e:
            print(f"❌ Error en ComprasAssistantView: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ComprasMessageView(APIView):
    """
    Vista para enviar mensajes al asistente de compras
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, thread_id):
        """Enviar mensaje al asistente de compras"""
        try:
            from .services.compras_assistant import ComprasAssistant
            
            message = request.data.get('message')
            if not message:
                return Response(
                    {'error': 'Mensaje requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            assistant = ComprasAssistant()
            response = assistant.send_message(thread_id, message, request.user)
            
            return Response({'response': response})
            
        except Exception as e:
            print(f"❌ Error en ComprasMessageView: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request, thread_id):
        """Obtener mensajes del thread de compras"""
        try:
            conversation = get_object_or_404(
                Conversation, 
                thread_id=thread_id, 
                usuario=request.user
            )
            
            messages = Message.objects.filter(
                conversation=conversation
            ).order_by('created_at')
            
            messages_data = []
            for message in messages:
                messages_data.append({
                    'role': message.role,
                    'content': message.content,
                    'created_at': message.created_at
                })
            
            return Response({'messages': messages_data})
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_or_create_compras_conversation(request):
    """Obtener conversación activa de compras o crear una nueva"""
    try:
        from .services.compras_assistant import ComprasAssistant
        
        assistant = ComprasAssistant()
        thread_id, conversation_id = assistant.get_or_create_active_conversation(request.user)
        
        return Response({
            'thread_id': thread_id,
            'conversation_id': conversation_id,
            'assistant': 'compras'
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 