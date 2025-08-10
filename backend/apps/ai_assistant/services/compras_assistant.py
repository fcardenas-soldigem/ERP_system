import os
import json
from openai import OpenAI
from apps.ai_assistant.models import Conversation, Message
from .compras_executor import ComprasExecutor
from ..tools.compras_tools import COMPRAS_TOOLS

class ComprasAssistant:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        # Usar el assistant específico para compras
        self.assistant_id = os.getenv('COMPRAS_ASSISTANT_ID', 'asst_default_compras')

    def create_thread(self, user):
        """Crear un nuevo thread para compras"""
        try:
            # Crear thread en OpenAI
            thread = self.client.beta.threads.create()
            
            # Crear conversación en base de datos
            conversation = Conversation.objects.create(
                usuario=user,
                title="Nueva Conversación de Compras",
                empresa=user.empresa,
                thread_id=thread.id
            )
            
            # Mensaje de bienvenida
            welcome_message = (
                "📦 ¡Hola! Soy tu asistente especializado en compras. "
                "Puedo ayudarte a:\n\n"
                "• 🔍 Buscar proveedores y productos\n"
                "• 📝 Crear órdenes de compra\n"
                "• 💰 Gestionar precios y cantidades\n\n"
                "¿En qué compra puedo asistirte hoy?"
            )
            
            Message.objects.create(
                conversation=conversation,
                role='assistant',
                content=welcome_message
            )
            
            return thread.id, conversation.id
            
        except Exception as e:
            print(f"❌ Error creando thread de compras: {str(e)}")
            raise

    def send_message(self, thread_id, user_message, user):
        """Enviar mensaje y procesar respuesta con tools"""
        try:
            print(f"📦 Usuario {user.username} envía (compras): {user_message}")
            
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
                tools=COMPRAS_TOOLS
            )
            
            print(f"🔄 Run de compras creado: {run.id}")
            
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
            print(f"❌ Error en ComprasAssistant: {str(e)}")
            return f"❌ Error: {str(e)}"

    def _wait_for_completion(self, run, thread_id, user):
        """Esperar completion del run y manejar tool calls"""
        import time
        
        while True:
            run_status = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            print(f"🔄 Run compras status: {run_status.status}")
            
            if run_status.status == 'completed':
                # Obtener mensajes
                messages = self.client.beta.threads.messages.list(thread_id=thread_id)
                return messages.data[0].content[0].text.value
                
            elif run_status.status == 'requires_action':
                print("🛠️ El asistente de compras requiere ejecutar funciones...")
                self._handle_tool_calls(run_status, thread_id, run.id, user)
                
            elif run_status.status == 'failed':
                return "❌ Error en el procesamiento de la solicitud de compras"
                
            time.sleep(1)

    def _handle_tool_calls(self, run_status, thread_id, run_id, user):
        """Manejar las llamadas a funciones de compras"""
        tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
        tool_outputs = []
        
        print(f"🔧 Procesando {len(tool_calls)} function calls de compras...")
        
        executor = ComprasExecutor(user)
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            print(f"📞 Llamando función de compras: {function_name}")
            print(f"📋 Argumentos: {json.dumps(arguments, indent=2, ensure_ascii=False)}")
            
            try:
                if function_name == 'crear_compra':
                    result = executor.crear_compra(**arguments)
                elif function_name == 'buscar_productos':
                    result = executor.buscar_productos(**arguments)
                elif function_name == 'buscar_proveedores':
                    result = executor.buscar_proveedores(**arguments)
                elif function_name == 'buscar_almacenes':
                    result = executor.buscar_almacenes(**arguments)
                else:
                    result = {'success': False, 'error': f'Función {function_name} no reconocida para compras'}
                
                print(f"✅ Resultado compras: {result}")
                
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": json.dumps(result, ensure_ascii=False)
                })
                
            except Exception as e:
                print(f"❌ Error ejecutando {function_name} en compras: {str(e)}")
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
        """Obtener conversación activa de compras o crear una nueva"""
        try:
            # Buscar conversación activa de compras
            conversation = Conversation.objects.filter(
                usuario=user,
                empresa=user.empresa,
                title__icontains="Compras"
            ).first()
            
            if conversation and conversation.thread_id:
                return conversation.thread_id, conversation.id
            else:
                # Crear nueva conversación
                return self.create_thread(user)
                
        except Exception as e:
            print(f"❌ Error obteniendo conversación de compras: {str(e)}")
            return self.create_thread(user) 