import os
import json
from openai import OpenAI
from apps.ai_assistant.models import Conversation, Message
from .ventas_executor import VentasExecutor
from ..tools.ventas_tools import VENTAS_TOOLS

class VentasAssistant:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        # Crear un assistant específico para ventas
        self.assistant_id = os.getenv('VENTAS_ASSISTANT_ID', 'asst_default_ventas')

    def create_thread(self, user):
        """Crear un nuevo thread para ventas"""
        try:
            # Crear thread en OpenAI
            thread = self.client.beta.threads.create()
            
            # Crear conversación en base de datos
            conversation = Conversation.objects.create(
                usuario=user,
                title="Nueva Conversación de Ventas",
                empresa=user.empresa,
                thread_id=thread.id
            )
            
            # Mensaje de bienvenida
            welcome_message = (
                "🛒 ¡Hola! Soy tu asistente especializado en ventas. "
                "Puedo ayudarte a:\n\n"
                "• 🔍 Buscar clientes y productos\n"
                "• 📝 Crear nuevas ventas\n"
                "• 💰 Calcular totales y stock\n\n"
                "¿En qué puedo ayudarte hoy?"
            )
            
            Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=welcome_message
            )
            
            return thread.id, conversation.id
            
        except Exception as e:
            raise

    def send_message(self, thread_id, user_message, user):
        """Enviar mensaje y procesar respuesta con tools"""
        try:
            
            # Buscar conversación
            conversation = Conversation.objects.get(thread_id=thread_id, usuario=user)
            
            # Guardar mensaje del usuario
            Message.objects.create(
                conversation=conversation,
                role='user',
                content=user_message
            )
            
            # Enviar mensaje a OpenAI
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_message
            )
            
            # Crear run con tools
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id,
                tools=VENTAS_TOOLS
            )
            
            
            # Procesar run
            final_response = self._wait_for_completion(run, thread_id, user)
            
            # Guardar respuesta del asistente
            Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=final_response
            )
            
            return final_response
            
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def _wait_for_completion(self, run, thread_id, user):
        """Esperar completion del run y manejar tool calls"""
        import time
        
        while True:
            run_status = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            
            if run_status.status == 'completed':
                # Obtener mensajes
                messages = self.client.beta.threads.messages.list(thread_id=thread_id)
                return messages.data[0].content[0].text.value
                
            elif run_status.status == 'requires_action':
                self._handle_tool_calls(run_status, thread_id, run.id, user)
                
            elif run_status.status == 'failed':
                return "❌ Error en el procesamiento de la solicitud"
                
            time.sleep(1)

    def _handle_tool_calls(self, run_status, thread_id, run_id, user):
        """Manejar las llamadas a funciones"""
        tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
        tool_outputs = []
        
        
        executor = VentasExecutor(user)
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            
            try:
                if function_name == 'crear_venta':
                    result = executor.crear_venta(**arguments)
                elif function_name == 'buscar_productos':
                    result = executor.buscar_productos(**arguments)
                elif function_name == 'buscar_clientes':
                    result = executor.buscar_clientes(**arguments)
                else:
                    result = {'success': False, 'error': f'Función {function_name} no reconocida'}
                
                
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": json.dumps(result, ensure_ascii=False)
                })
                
            except Exception as e:
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": json.dumps({'success': False, 'error': str(e)}, ensure_ascii=False)
                })
        
        # Enviar resultados a OpenAI
        self.client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run_id,
            tool_outputs=tool_outputs
        )

    def get_or_create_active_conversation(self, user):
        """Obtener conversación activa o crear una nueva"""
        try:
            # Buscar conversación activa
            conversation = Conversation.objects.filter(
                usuario=user,
                empresa=user.empresa
            ).first()
            
            if conversation and conversation.thread_id:
                return conversation.thread_id, conversation.id
            else:
                # Crear nueva conversación
                return self.create_thread(user)
                
        except Exception as e:
            return self.create_thread(user) 