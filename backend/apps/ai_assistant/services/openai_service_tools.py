import openai
import json
import time
from django.conf import settings
from .analista_executor import AnalistaExecutor
from ..tools.analista_tools import ANALISTA_TOOLS

class OpenAIServiceWithTools:
    """
    Servicio OpenAI con soporte para Function Calling (Tools)
    Maneja la creación de ventas y compras a través del asistente IA
    """
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
    def create_thread(self, user):
        """Crear un nuevo thread con mensaje de bienvenida"""
        try:
            thread = self.client.beta.threads.create()
            
            # Crear conversación en la base de datos
            from ..models import Conversation
            conversation = Conversation.objects.create(
                empresa=user.empresa,
                usuario=user,
                thread_id=thread.id,
                title="Conversación con Jorge"
            )
            
            # Crear mensaje de bienvenida
            welcome_message = self._generate_welcome_message(user)
            
            # Agregar mensaje de bienvenida al thread
            self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="assistant",
                content=welcome_message
            )
            
            # Guardar mensaje en la base de datos
            from ..models import Message
            Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=welcome_message
            )
            
            return {
                'thread_id': thread.id,
                'conversation_id': conversation.id,
                'message': welcome_message
            }
            
        except Exception as e:
            raise e
    
    def _generate_welcome_message(self, user):
        """Generar mensaje de bienvenida personalizado"""
        empresa_name = user.empresa.nombre if user.empresa else "tu empresa"
        user_name = user.get_full_name() or user.username
        
        return f"""¡Hola {user_name}! 👋

Soy **Jorge**, tu analista comercial especializado en el ERP de {empresa_name}.

🔍 **¿En qué análisis puedo ayudarte hoy?**

📊 **Análisis de ventas** - Tendencias, performance y métricas
📈 **Análisis de clientes** - Top compradores y comportamiento  
📦 **Análisis de inventario** - Stock, rotación y alertas
💡 **Consultas libres** - Insights y oportunidades comerciales

**Ejemplos de consultas:**
• "¿Cómo están las ventas este mes?"
• "¿Qué productos tienen stock bajo?"
• "¿Quiénes son mis mejores clientes?"
• "¿Cuáles son las tendencias de ventas?"

¡Empecemos! 💪"""

    def send_message_with_tools(self, thread_id, content, user):
        """Enviar mensaje con soporte para function calling"""
        try:
            
            # Guardar mensaje del usuario en la base de datos
            self._save_user_message(thread_id, content, user)
            
            # Agregar mensaje del usuario al thread
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=content
            )
            
            # Crear run con tools de análisis (sin crear ventas/compras)
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=settings.OPENAI_ASSISTANT_ID,
                tools=ANALISTA_TOOLS  # 🔍 Tools solo para análisis
            )
            
            
            # Esperar completación
            run = self._wait_for_completion(thread_id, run.id)
            
            # Manejar tool calls si los hay
            if run.status == "requires_action":
                response = self._handle_tool_calls(thread_id, run, user)
            else:
                # Obtener respuesta normal
                messages = self.client.beta.threads.messages.list(thread_id=thread_id, limit=1)
                response = messages.data[0].content[0].text.value
            
            # Guardar respuesta del asistente
            self._save_assistant_message(thread_id, response, user)
            
            return response
            
        except Exception as e:
            error_msg = f"❌ Error procesando mensaje: {str(e)}"
            return error_msg
    
    def _wait_for_completion(self, thread_id, run_id, max_wait=30):
        """Esperar a que el run se complete"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            
            
            if run.status in ["completed", "requires_action", "failed", "cancelled", "expired"]:
                return run
            
            time.sleep(1)
        
        # Si se agota el tiempo, cancelar el run
        self.client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run_id)
        raise Exception("Timeout esperando respuesta del asistente")
    
    def _handle_tool_calls(self, thread_id, run, user):
        """Manejar llamadas a funciones"""
        try:
            executor = AnalistaExecutor(user)
            tool_outputs = []
            
            
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                function_name = tool_call.function.name
                arguments_str = tool_call.function.arguments
                
                
                try:
                    arguments = json.loads(arguments_str)
                except json.JSONDecodeError as e:
                    result = {
                        'success': False,
                        'error': f'Error parsing argumentos: {str(e)}'
                    }
                else:
                    # Ejecutar función
                    result = executor.execute_function(function_name, arguments)
                
                
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": json.dumps(result, ensure_ascii=False, default=str)
                })
            
            # Enviar resultados de tools
            run = self.client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )
            
            # Esperar completación final
            run = self._wait_for_completion(thread_id, run.id)
            
            if run.status == "completed":
                # Obtener respuesta final del asistente
                messages = self.client.beta.threads.messages.list(thread_id=thread_id, limit=1)
                return messages.data[0].content[0].text.value
            else:
                return f"❌ Error en la ejecución final. Status: {run.status}"
            
        except Exception as e:
            error_msg = f"❌ Error ejecutando funciones: {str(e)}"
            return error_msg
    
    def _save_user_message(self, thread_id, content, user):
        """Guardar mensaje del usuario en la base de datos"""
        try:
            from ..models import Conversation, Message
            conversation, created = Conversation.objects.get_or_create(
                thread_id=thread_id,
                usuario=user,
                defaults={
                    'title': f'Conversación {thread_id[:8]}...',
                    'empresa': user.empresa
                }
            )
            Message.objects.create(
                conversation=conversation,
                role='user',
                content=content
            )
        except Exception as e:
            pass

    def _save_assistant_message(self, thread_id, content, user):
        """Guardar mensaje del asistente en la base de datos"""
        try:
            from ..models import Conversation, Message
            conversation, created = Conversation.objects.get_or_create(
                thread_id=thread_id,
                usuario=user,
                defaults={
                    'title': f'Conversación {thread_id[:8]}...',
                    'empresa': user.empresa
                }
            )
            Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=content
            )
        except Exception as e:
            pass

    def get_thread_messages(self, thread_id):
        """Obtener mensajes de un thread"""
        try:
            messages = self.client.beta.threads.messages.list(thread_id=thread_id)
            
            formatted_messages = []
            for msg in reversed(messages.data):
                try:
                    content = msg.content[0].text.value if msg.content else ""
                    formatted_messages.append({
                        'role': msg.role,
                        'content': content,
                        'created_at': msg.created_at
                    })
                except Exception as content_error:
                    continue
            
            return formatted_messages
            
        except Exception as e:
            error_msg = str(e)
            
            # Si el thread no existe, devolver lista vacía
            if "No thread found" in error_msg or "thread_" not in thread_id:
                return []
            
            # Para otros errores, re-lanzar la excepción
            raise e 