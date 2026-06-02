import logging
from datetime import datetime, timedelta
from django.db.models import Sum, Avg, F, Count, Max, Min
from django.db import transaction
from django.conf import settings
from apps.ventas.models import Venta, DetalleVenta
from apps.compras.models import Compra, CompraDetalle
from apps.inventario.models import Producto, Stock, Almacen, MovimientoInventario
from apps.empresas.models import Empresa
from .models import Conversation, Message, AIInsight, AIAction
import pandas as pd
import numpy as np
from openai import OpenAI
import anthropic
import json
logger = logging.getLogger(__name__)

class AIAssistantService:
    def __init__(self, conversation):
        self.conversation = conversation
        self.empresa = conversation.empresa
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.assistant_id = settings.OPENAI_ASSISTANT_ID

    def get_user_conversation_history(self):
        """
        Obtiene el historial completo de conversaciones del usuario para análisis de patrones
        """
        try:
            # Obtener todas las conversaciones del usuario (últimas 5)
            conversations = Conversation.objects.filter(
                empresa=self.empresa,
                usuario=self.conversation.usuario
            ).order_by('-updated_at')[:5]
            
            conversation_summary = []
            total_messages = 0
            user_interests = []
            frequently_asked = []
            
            for conv in conversations:
                messages = Message.objects.filter(conversation=conv).order_by('created_at')
                if messages.exists():
                    conv_data = {
                        'date': conv.created_at.strftime('%Y-%m-%d'),
                        'title': conv.title,
                        'message_count': messages.count(),
                        'topics': []
                    }
                    
                    # Analizar temas de la conversación
                    user_messages = [msg.content.lower() for msg in messages if msg.role == 'user']
                    for msg_content in user_messages:
                        if any(word in msg_content for word in ['venta', 'ventas', 'cliente', 'factura']):
                            conv_data['topics'].append('Ventas')
                        if any(word in msg_content for word in ['inventario', 'stock', 'producto', 'almacen']):
                            conv_data['topics'].append('Inventario')
                        if any(word in msg_content for word in ['compra', 'compras', 'proveedor', 'costo']):
                            conv_data['topics'].append('Compras')
                        if any(word in msg_content for word in ['reporte', 'análisis', 'estadística', 'tendencia']):
                            conv_data['topics'].append('Reportes')
                        if any(word in msg_content for word in ['ayuda', 'cómo', 'explicar', 'mostrar']):
                            conv_data['topics'].append('Consultas')
                    
                    conv_data['topics'] = list(set(conv_data['topics']))  # Eliminar duplicados
                    conversation_summary.append(conv_data)
                    total_messages += conv_data['message_count']
                    user_interests.extend(conv_data['topics'])
                    
                    # Guardar preguntas frecuentes
                    for msg in messages:
                        if msg.role == 'user' and len(msg.content) > 10:
                            frequently_asked.append(msg.content[:100])  # Primeras 100 chars
            
            # Análisis de patrones
            from collections import Counter
            topic_frequency = Counter(user_interests)
            most_common_topics = topic_frequency.most_common(3)
            
            return {
                'total_conversations': len(conversation_summary),
                'total_messages': total_messages,
                'conversation_summary': conversation_summary,
                'user_preferences': {
                    'most_discussed_topics': [topic[0] for topic in most_common_topics],
                    'topic_frequency': dict(topic_frequency),
                    'engagement_level': 'Alto' if total_messages > 20 else 'Medio' if total_messages > 5 else 'Bajo'
                },
                'recent_questions': frequently_asked[-5:]  # Últimas 5 preguntas
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo historial de usuario: {e}")
            return {
                'total_conversations': 0,
                'total_messages': 0,
                'conversation_summary': [],
                'user_preferences': {'most_discussed_topics': [], 'engagement_level': 'Nuevo'},
                'recent_questions': []
            }

    def get_sistema_context(self):
        """
        Obtiene el contexto completo del sistema ERP para el asistente
        """
        try:
            # Datos de la empresa
            empresa_info = {
                'nombre': self.empresa.nombre,
                'ruc': self.empresa.ruc,
                'direccion': self.empresa.direccion,
                'telefono': self.empresa.telefono,
            }

            # Importar función de conversión y obtener tipo de cambio
            from apps.dashboard.views import obtener_tipo_cambio_venta, convertir_a_pen
            tipo_cambio = obtener_tipo_cambio_venta()

            # Resumen de ventas con conversión de monedas
            hoy = datetime.now().date()
            ventas_hoy_query = Venta.objects.filter(
                empresa=self.empresa,
                fecha_emision=hoy
            )
            
            # Calcular total de ventas hoy convirtiendo a PEN
            ventas_hoy_total = 0.0  
            for venta in ventas_hoy_query:
                ventas_hoy_total += convertir_a_pen(venta.total, venta.moneda, tipo_cambio)
            
            ventas_hoy = {
                'total': ventas_hoy_total,
                'cantidad': ventas_hoy_query.count()
            }

            ventas_mes_query = Venta.objects.filter(
                empresa=self.empresa,
                fecha_emision__month=datetime.now().month,
                fecha_emision__year=datetime.now().year
            )
            
            # Calcular total de ventas del mes convirtiendo a PEN
            ventas_mes_total = 0.0
            for venta in ventas_mes_query:
                ventas_mes_total += convertir_a_pen(venta.total, venta.moneda, tipo_cambio)
            
            ventas_mes = {
                'total': ventas_mes_total,
                'cantidad': ventas_mes_query.count()
            }

            # Resumen de compras con conversión de monedas
            compras_hoy_query = Compra.objects.filter(
                empresa=self.empresa,
                fecha_emision=hoy
            )
            
            # Calcular total de compras hoy convirtiendo a PEN
            compras_hoy_total = 0.0
            for compra in compras_hoy_query:
                compras_hoy_total += convertir_a_pen(compra.total, compra.moneda, tipo_cambio)
            
            compras_hoy = {
                'total': compras_hoy_total,
                'cantidad': compras_hoy_query.count()
            }

            compras_mes_query = Compra.objects.filter(
                empresa=self.empresa,
                fecha_emision__month=datetime.now().month,
                fecha_emision__year=datetime.now().year
            )
            
            # Calcular total de compras del mes convirtiendo a PEN
            compras_mes_total = 0.0
            for compra in compras_mes_query:
                compras_mes_total += convertir_a_pen(compra.total, compra.moneda, tipo_cambio)
            
            compras_mes = {
                'total': compras_mes_total,
                'cantidad': compras_mes_query.count()
            }

            # Productos con stock bajo - obtener detalles reales
            from django.db.models import F
            productos_bajo_stock_query = Producto.objects.filter(
                empresa=self.empresa,
                is_active=True,
                stock_total__lte=F('stock_minimo')
            ).values('nombre', 'sku', 'stock_total', 'stock_minimo')
            
            # Forzar evaluación de la query y convertir a lista
            productos_bajo_stock = list(productos_bajo_stock_query)
            productos_stock_bajo_count = len(productos_bajo_stock)

            # Top 5 productos más vendidos este mes - Calcular manualmente para conversión de monedas
            detalles_ventas_mes = DetalleVenta.objects.filter(
                venta__empresa=self.empresa,
                venta__fecha_emision__month=datetime.now().month,
                venta__fecha_emision__year=datetime.now().year
            ).select_related('venta', 'producto')

            # Agrupar productos y calcular totales con conversión de monedas
            productos_stats = {}
            for detalle in detalles_ventas_mes:
                producto_nombre = detalle.producto.nombre
                if producto_nombre not in productos_stats:
                    productos_stats[producto_nombre] = {
                        'total_vendido': 0,
                        'ingresos': 0.0
                    }
                
                # Sumar cantidad
                productos_stats[producto_nombre]['total_vendido'] += float(detalle.cantidad)
                
                # Convertir ingresos a PEN
                ingreso_detalle = float(detalle.cantidad) * float(detalle.precio_unitario)
                ingreso_pen = convertir_a_pen(ingreso_detalle, detalle.venta.moneda, tipo_cambio)
                productos_stats[producto_nombre]['ingresos'] += ingreso_pen

            # Convertir a lista y ordenar por cantidad vendida
            top_productos = []
            for producto_nombre, stats in productos_stats.items():
                top_productos.append({
                    'producto__nombre': producto_nombre,
                    'total_vendido': stats['total_vendido'],
                    'ingresos': stats['ingresos']
                })
            
            # Ordenar por total vendido y tomar los top 5
            top_productos = sorted(top_productos, key=lambda x: x['total_vendido'], reverse=True)[:5]

            # Últimos movimientos de inventario
            ultimos_movimientos = MovimientoInventario.objects.filter(
                producto__empresa=self.empresa
            ).select_related('producto').order_by('-fecha')[:10]

            # Obtener proveedores reales 
            from apps.compras.models import Proveedor
            ultimos_proveedores = Proveedor.objects.filter(
                empresa=self.empresa
            ).values('razon_social', 'ruc', 'telefono').order_by('-id')[:5]

            # 🧠 OBTENER HISTORIAL Y PERFIL DE USUARIO
            user_history = self.get_user_conversation_history()

            context = {
                'empresa': empresa_info,
                'ventas_hoy': ventas_hoy,
                'ventas_mes': ventas_mes,
                'compras_hoy': compras_hoy,
                'compras_mes': compras_mes,
                'productos_stock_bajo_count': productos_stock_bajo_count,
                'productos_bajo_stock': productos_bajo_stock,
                'top_productos': top_productos,
                'tipo_cambio': tipo_cambio,
                'ultimos_proveedores': list(ultimos_proveedores),
                'ultimos_movimientos': [
                    {
                        'producto': mov.producto.nombre,
                        'tipo': mov.get_tipo_movimiento_display(),
                        'cantidad_entrada': float(mov.cantidad_entrada),
                        'cantidad_salida': float(mov.cantidad_salida),
                        'cantidad_saldo': float(mov.cantidad_saldo),
                        'fecha': mov.fecha.strftime('%Y-%m-%d %H:%M'),
                        'documento': mov.numero_documento
                    } for mov in ultimos_movimientos
                ],
                'fecha_actual': datetime.now().strftime('%Y-%m-%d %H:%M'),
                # 🧠 CONTEXTO DE USUARIO INTELIGENTE
                'user_profile': user_history
            }

            return context

        except Exception as e:
            logger.error(f"Error obteniendo contexto del sistema: {e}")
            return {}

    def generate_proactive_insights(self, user_history, sistema_context):
        """
        Genera insights proactivos basados en el historial del usuario y datos actuales
        """
        try:
            insights = []
            
            # Análisis basado en temas de interés del usuario
            user_topics = user_history.get('user_preferences', {}).get('most_discussed_topics', [])
            
            if 'Ventas' in user_topics:
                ventas_mes = sistema_context.get('ventas_mes', {}).get('cantidad', 0)
                if ventas_mes > 0:
                    insights.append(f"💰 Como te interesan las ventas: Tienes {ventas_mes} ventas este mes. ¿Te gustaría analizar las tendencias?")
            
            if 'Inventario' in user_topics:
                stock_bajo = sistema_context.get('productos_stock_bajo', 0)
                if stock_bajo > 0:
                    insights.append(f"📦 Detecté que sueles preguntar sobre inventario: Tienes {stock_bajo} productos con stock bajo que requieren atención.")
            
            if 'Compras' in user_topics:
                compras_mes = sistema_context.get('compras_mes', {}).get('cantidad', 0)
                insights.append(f"🛒 Sobre compras (tu tema favorito): Llevas {compras_mes} compras este mes.")
            
            # Insights para usuarios nuevos
            if user_history.get('user_preferences', {}).get('engagement_level') == 'Nuevo':
                insights.append("🌟 Como es tu primera vez, te recomiendo explorar el dashboard de ventas y revisar tu inventario.")
            
            # Insights para usuarios experimentados
            elif user_history.get('user_preferences', {}).get('engagement_level') == 'Alto':
                insights.append("🚀 Como usuario avanzado, podrías estar interesado en análisis predictivos o tendencias de mercado.")
            
            return insights[:2]  # Máximo 2 insights proactivos
            
        except Exception as e:
            logger.error(f"Error generando insights proactivos: {e}")
            return []

    def process_message(self, content):
        """
        Procesa un mensaje del usuario con acceso completo a los datos del ERP y memoria inteligente
        """
        try:
            # Guardar el mensaje del usuario
            Message.objects.create(
                conversation=self.conversation,
                content=content,
                role='user'
            )

            # Obtener contexto del sistema CON MEMORIA INTELIGENTE
            sistema_context = self.get_sistema_context()
            user_history = sistema_context.get('user_profile', {})

            # Generar insights proactivos
            proactive_insights = self.generate_proactive_insights(user_history, sistema_context)

            # Obtener el contexto de la conversación (últimos 5 mensajes)
            context_messages = Message.objects.filter(
                conversation=self.conversation
            ).order_by('-created_at')[:5][::-1]

            # Preparar mensajes para OpenAI (prompt ya incluye memoria inteligente)
            system_prompt = f"""¡Hola! Soy Jorge 🤖, tu asistente virtual personal de {sistema_context.get('empresa', {}).get('nombre', 'tu empresa')}. ¡Estoy aquí para ayudarte con todo lo relacionado a tu ERP!

🎯 TENGO ACCESO COMPLETO Y EN TIEMPO REAL A TODOS TUS DATOS:

🏢 TU EMPRESA: {sistema_context.get('empresa', {}).get('nombre', 'N/A')} 
📄 RUC: {sistema_context.get('empresa', {}).get('ruc', 'N/A')}
📅 Fecha actual: {sistema_context.get('fecha_actual', 'N/A')}

💰 RESUMEN DE VENTAS (convertido a PEN con TC: {sistema_context.get('tipo_cambio', 3.8)}):
• Hoy: {sistema_context.get('ventas_hoy', {}).get('cantidad', 0)} ventas por S/ {sistema_context.get('ventas_hoy', {}).get('total', 0) or 0:,.2f}
• Este mes: {sistema_context.get('ventas_mes', {}).get('cantidad', 0)} ventas por S/ {sistema_context.get('ventas_mes', {}).get('total', 0) or 0:,.2f}

🛒 RESUMEN DE COMPRAS (convertido a PEN con TC: {sistema_context.get('tipo_cambio', 3.8)}):
• Hoy: {sistema_context.get('compras_hoy', {}).get('cantidad', 0)} compras por S/ {sistema_context.get('compras_hoy', {}).get('total', 0) or 0:,.2f}
• Este mes: {sistema_context.get('compras_mes', {}).get('cantidad', 0)} compras por S/ {sistema_context.get('compras_mes', {}).get('total', 0) or 0:,.2f}

⚠️ ALERTAS DE INVENTARIO:
• Productos con stock bajo: {sistema_context.get('productos_stock_bajo_count', 0)} productos

📦 PRODUCTOS CON STOCK BAJO (DATOS REALES):
{chr(10).join([f"• {prod['nombre']} (SKU: {prod['sku']}): Stock actual {prod['stock_total']} ≤ Mínimo {prod['stock_minimo']}" for prod in sistema_context.get('productos_bajo_stock', [])[:5]]) if sistema_context.get('productos_bajo_stock') else "• No hay productos con stock bajo actualmente"}

🏆 TUS PRODUCTOS ESTRELLA ESTE MES:
{chr(10).join([f"🥇 {prod['producto__nombre']}: {prod['total_vendido']} unidades vendidas (S/ {prod['ingresos']:,.2f} en ingresos)" for prod in sistema_context.get('top_productos', [])[:3]]) if sistema_context.get('top_productos') else "• No hay datos de productos vendidos este mes"}

📋 ACTIVIDAD RECIENTE EN INVENTARIO:
{chr(10).join([f"• {mov['producto']}: {mov['tipo']} - Saldo actual: {mov['cantidad_saldo']} ({mov['fecha'].split()[0]})" for mov in sistema_context.get('ultimos_movimientos', [])[:5]]) if sistema_context.get('ultimos_movimientos') else "• No hay movimientos recientes"}

🏪 TUS PROVEEDORES PRINCIPALES:
{chr(10).join([f"• {prov['razon_social']} (RUC: {prov['ruc']}) - Tel: {prov['telefono'] or 'N/A'}" for prov in sistema_context.get('ultimos_proveedores', [])[:3]]) if sistema_context.get('ultimos_proveedores') else "• No hay proveedores registrados"}

🧠 MI MEMORIA SOBRE TI (ANÁLISIS INTELIGENTE):
📊 Historial de Conversaciones: {sistema_context.get('user_profile', {}).get('total_conversations', 0)} conversaciones, {sistema_context.get('user_profile', {}).get('total_messages', 0)} mensajes
🎯 Tus Temas de Mayor Interés: {', '.join(sistema_context.get('user_profile', {}).get('user_preferences', {}).get('most_discussed_topics', ['Ninguno aún']))}
📈 Nivel de Engagement: {sistema_context.get('user_profile', {}).get('user_preferences', {}).get('engagement_level', 'Nuevo')}
🔍 Patrones Detectados: {json.dumps(sistema_context.get('user_profile', {}).get('user_preferences', {}).get('topic_frequency', {}), ensure_ascii=False) if sistema_context.get('user_profile', {}).get('user_preferences', {}).get('topic_frequency') else 'Analizando...'}

💡 CONVERSACIONES ANTERIORES RESUMEN:
{chr(10).join([f"📅 {conv['date']}: {conv['title']} ({conv['message_count']} mensajes) - Temas: {', '.join(conv['topics']) if conv['topics'] else 'General'}" for conv in sistema_context.get('user_profile', {}).get('conversation_summary', [])[:3]]) if sistema_context.get('user_profile', {}).get('conversation_summary') else "• Primera vez que conversamos - ¡Encantado de conocerte!"}

🚨 INSIGHTS PROACTIVOS PARA TI:
{chr(10).join([f"• {insight}" for insight in proactive_insights]) if proactive_insights else "• Analizando tus patrones para generar recomendaciones personalizadas..."}

🚀 ¿EN QUÉ PUEDO AYUDARTE HOY?
• Analizar tus ventas y encontrar oportunidades
• Revisar tu inventario y detectar productos con stock bajo
• Generar reportes personalizados basados en tus intereses
• Procesar archivos Excel/CSV para cargas masivas
• Darte insights sobre el rendimiento de tu negocio
• Responder cualquier pregunta específica sobre tus datos

💡 INTELIGENCIA ADAPTATIVA:
- USO MI MEMORIA para darte respuestas más personalizadas
- APRENDO de tus preguntas frecuentes para anticipar tus necesidades
- ADAPTO mis recomendaciones basándome en tus patrones de uso
- PRIORIZO información relevante según tus intereses históricos

INSTRUCCIONES ESPECIALES PARA MIS RESPUESTAS:
1. SIEMPRE considerar el historial de conversaciones para contexto
2. Si el usuario ha preguntado sobre un tema antes, hacer referencia a conversaciones anteriores
3. Personalizar recomendaciones basándose en sus temas de mayor interés
4. Si es un usuario nuevo, ser más explicativo y educativo
5. Para usuarios experimentados, ser más directo y enfocado en insights avanzados
6. Usar los patrones detectados para sugerir análisis proactivos

💱 IMPORTANTE SOBRE MONEDAS:
TODOS los valores monetarios en mis respuestas están convertidos a soles peruanos (PEN) usando el tipo de cambio oficial del día ({sistema_context.get('tipo_cambio', 3.8)}). Las ventas/compras originales pueden estar en USD o PEN, pero siempre reporto en PEN para consistencia. Cuando reportes cifras, siempre menciona que están convertidas a PEN.

🚨 INSTRUCCIONES CRÍTICAS - USA SOLO DATOS REALES:
- NUNCA inventes nombres de productos como "Producto A", "Producto B", etc.
- USA SIEMPRE los nombres reales que aparecen arriba: "HEADSET JABRA EVOLVE 20", "CAMBIO DE PANTALLAMACBOOK PRO A2338", etc.
- NUNCA inventes proveedores como "Proveedor 1", "Proveedor 2"
- USA SIEMPRE los proveedores reales con sus nombres comerciales y RUCs que aparecen arriba
- NUNCA des información genérica - USA EXCLUSIVAMENTE los datos específicos que te proporciono
- Si necesitas mencionar productos, menciona los nombres reales y sus SKUs
- Si necesitas mencionar proveedores, usa sus nombres comerciales reales

PERSONALIDAD: Sé amable, entusiasta, profesional pero cercano. Usa emojis apropiados. Siempre proporciona datos específicos y reales. NUNCA digas que no tienes acceso - SIEMPRE tengo acceso completo a todos los datos del sistema. USA TU MEMORIA para hacer referencias inteligentes a conversaciones anteriores y personalizar la experiencia. SIEMPRE explica que los valores monetarios están convertidos a soles peruanos cuando sea relevante. NUNCA INVENTES INFORMACIÓN - USA SOLO LOS DATOS REALES QUE TE PROPORCIONO."""

            messages = [{"role": "system", "content": system_prompt}]

            # Agregar mensajes del contexto (sin incluir el mensaje actual)
            for msg in context_messages[:-1]:  # Excluir el último que acabamos de crear
                role = "assistant" if msg.role == 'assistant' else "user"
                messages.append({"role": role, "content": msg.content})

            # Agregar el mensaje actual
            messages.append({"role": "user", "content": content})

            # Obtener respuesta de OpenAI
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL or "gpt-4o-mini",
                messages=messages,
                max_tokens=1200,  # Aumentado para respuestas más ricas
                temperature=0.7
            )

            # Extraer la respuesta
            ai_response = response.choices[0].message.content

            # Guardar la respuesta como mensaje
            Message.objects.create(
                conversation=self.conversation,
                content=ai_response,
                role='assistant'
            )

            return ai_response

        except Exception as e:
            logger.error(f"Error en process_message: {e}")
            # En caso de error, enviar una respuesta con datos básicos del sistema
            try:
                basic_info = self.get_basic_system_info()
                error_response = f"""¡Hola! Soy Jorge, tu asistente ERP. Aunque tuve un problema técnico, tengo acceso a tu sistema:

📊 DATOS BÁSICOS:
- Empresa: {basic_info.get('empresa_nombre', 'Tu empresa')}
- Puedo ayudarte con consultas sobre ventas, compras e inventario

¿En qué específicamente puedo ayudarte?"""
            
                Message.objects.create(
                    conversation=self.conversation,
                    content=error_response,
                    role='assistant'
                )
                
                return error_response
            except:
                error_response = "Lo siento, estoy teniendo problemas técnicos. ¿Podrías intentarlo de nuevo?"
                Message.objects.create(
                    conversation=self.conversation,
                    content=error_response,
                    role='assistant'
                )
                return error_response

    def get_basic_system_info(self):
        """Obtiene información básica del sistema para casos de error"""
        try:
            return {
                'empresa_nombre': self.empresa.nombre if self.empresa else 'Tu empresa',
                'ventas_count': Venta.objects.filter(empresa=self.empresa).count(),
                'compras_count': Compra.objects.filter(empresa=self.empresa).count(),
            }
        except:
            return {'empresa_nombre': 'Tu empresa'}

    @transaction.atomic
    def procesar_archivo(self, archivo, tipo):
        try:
            df = pd.read_excel(archivo) if archivo.name.endswith('.xlsx') else pd.read_csv(archivo)
            
            # Validar columnas requeridas
            columnas_requeridas = {
                'compra': [
                    'proveedor',  # Para crear/buscar el proveedor
                    'almacen',    # ID o nombre del almacén
                    'fecha_emision',
                    'estado',     # borrador, pendiente, pagada, anulada
                    'estado_pago', # efectivo, transferencia, cheque, tarjeta
                    'igv_incluido', # true/false
                    'producto',    # Para cada detalle
                    'cantidad',    # Para cada detalle
                    'precio_unitario', # Para cada detalle
                    'notas'       # Opcional
                ],
                'venta': [
                    'cliente',    # Para crear/buscar el cliente
                    'fecha_emision',
                    'estado',     # borrador, pendiente, pagada, anulada
                    'estado_pago', # efectivo, transferencia, cheque, tarjeta
                    'igv_incluido', # true/false
                    'producto',    # Para cada detalle
                    'cantidad',    # Para cada detalle
                    'precio_unitario', # Para cada detalle
                    'notas'       # Opcional
                ]
            }

            columnas_faltantes = [col for col in columnas_requeridas[tipo] if col not in df.columns]
            if columnas_faltantes:
                raise ValueError(f"Faltan las siguientes columnas: {', '.join(columnas_faltantes)}")

            # Crear acción para seguimiento
            accion = AIAction.objects.create(
                conversation=self.conversation,
                tipo=f'importar_{tipo}',
                datos={'total_registros': len(df)},
                status='in_progress'
            )

            registros_procesados = []
            errores = []

            for idx, row in df.iterrows():
                try:
                    if tipo == 'compra':
                        registro = self._procesar_compra(row)
                    else:
                        registro = self._procesar_venta(row)
                    registros_procesados.append(registro)
                except Exception as e:
                    errores.append({
                        'fila': idx + 2,
                        'error': str(e)
                    })

            resultado = {
                'total_registros': len(df),
                'procesados': len(registros_procesados),
                'errores': errores
            }

            accion.status = 'completed' if not errores else 'completed_with_errors'
            accion.resultado = resultado
            accion.save()

            mensaje_respuesta = (
                f"📊 Resultados de la importación:\n\n"
                f"Total registros: {len(df)}\n"
                f"Procesados exitosamente: {len(registros_procesados)}\n"
                f"Errores encontrados: {len(errores)}\n\n"
            )

            if errores:
                mensaje_respuesta += "⚠️ Se encontraron algunos errores. ¿Deseas ver el detalle?"
            else:
                mensaje_respuesta += "✅ Todos los registros fueron procesados correctamente."

            Message.objects.create(
                conversation=self.conversation,
                content=mensaje_respuesta,
                role='assistant'
            )

            return resultado

        except Exception as e:
            raise ValueError(f"Error al procesar el archivo: {str(e)}")

    def _procesar_compra(self, row):
        from apps.compras.models import Proveedor
        
        # Obtener o crear proveedor
        proveedor, _ = Proveedor.objects.get_or_create(
            empresa=self.empresa,
            nombre=row['proveedor']
        )

        # Obtener almacén
        try:
            almacen = Almacen.objects.get(
                empresa=self.empresa,
                nombre=row['almacen']
            )
        except Almacen.DoesNotExist:
            raise ValueError(f"No se encontró el almacén: {row['almacen']}")

        # Obtener o crear producto
        producto, _ = Producto.objects.get_or_create(
            empresa=self.empresa,
            nombre=row['producto']
        )

        # Crear compra
        compra = Compra.objects.create(
            empresa=self.empresa,
            almacen=almacen,
            proveedor=proveedor,
            fecha_emision=pd.to_datetime(row['fecha_emision']).date(),
            estado=row['estado'],
            estado_pago=row['estado_pago'],
            igv_incluido=row['igv_incluido'],
            notas=row.get('notas', ''),
            subtotal=float(row['cantidad'] * row['precio_unitario']),
            igv=float(row['cantidad'] * row['precio_unitario'] * 0.18),
            total=float(row['cantidad'] * row['precio_unitario'] * 1.18)
        )

        # Crear detalle de compra
        CompraDetalle.objects.create(
            compra=compra,
            producto=producto,
            cantidad=float(row['cantidad']),
            precio_unitario=float(row['precio_unitario'])
        )

        return compra.id

    def _procesar_venta(self, row):
        from apps.ventas.models import Cliente
        
        # Obtener o crear cliente
        cliente, _ = Cliente.objects.get_or_create(
            empresa=self.empresa,
            nombre=row['cliente']
        )

        # Obtener o crear producto
        producto, _ = Producto.objects.get_or_create(
            empresa=self.empresa,
            nombre=row['producto']
        )

        # Crear venta
        venta = Venta.objects.create(
            empresa=self.empresa,
            cliente=cliente,
            fecha_emision=pd.to_datetime(row['fecha_emision']).date(),
            estado=row['estado'],
            estado_pago=row['estado_pago'],
            igv_incluido=row['igv_incluido'],
            notas=row.get('notas', ''),
            subtotal=float(row['cantidad'] * row['precio_unitario']),
            igv=float(row['cantidad'] * row['precio_unitario'] * 0.18),
            total=float(row['cantidad'] * row['precio_unitario'] * 1.18)
        )

        # Crear detalle de venta
        DetalleVenta.objects.create(
            venta=venta,
            producto=producto,
            cantidad=float(row['cantidad']),
            precio_unitario=float(row['precio_unitario'])
        )

        return venta.id

class AnalistaComercialService:
    def __init__(self, empresa):
        self.empresa = empresa
        # Configurar Claude 3.5 Sonnet para análisis comercial
        self.client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
        
    def generar_reporte_ventas(self, periodo='último_mes'):
        """
        Genera análisis inteligente de ventas con insights comerciales
        """
        try:
            # Obtener datos de ventas del período
            ventas_data = self._obtener_datos_ventas(periodo)
            
            prompt = f"""
            Eres un Analista Comercial Senior especializado en ERP y análisis de ventas. 
            
            Analiza los siguientes datos de ventas y proporciona insights estratégicos:
            
            DATOS DE VENTAS ({periodo}):
            {ventas_data}
            
            INSTRUCCIONES:
            1. Analiza tendencias de ventas por período
            2. Identifica productos estrella y productos con bajo rendimiento  
            3. Evalúa performance por cliente
            4. Detecta patrones estacionales
            5. Proporciona recomendaciones estratégicas concretas
            
            FORMATO DE RESPUESTA:
            📊 RESUMEN EJECUTIVO
            📈 TENDENCIAS PRINCIPALES  
            🎯 PRODUCTOS DESTACADOS
            👥 ANÁLISIS DE CLIENTES
            ⚠️  ALERTAS COMERCIALES
            💡 RECOMENDACIONES ESTRATÉGICAS
            """
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            return f"Error al generar reporte: {str(e)}"
    
    def analizar_inventario_inteligente(self):
        """
        Análisis predictivo de inventario con alertas inteligentes
        """
        try:
            # Obtener datos de inventario y movimientos
            inventario_data = self._obtener_datos_inventario()
            
            prompt = f"""
            Como Analista de Inventario especializado en optimización, analiza estos datos:
            
            DATOS DE INVENTARIO:
            {inventario_data}
            
            PROPORCIONA:
            1. 🔴 Productos con riesgo de stockout (incluye predicción de días)
            2. 🟡 Productos con exceso de inventario 
            3. 📊 Análisis de rotación por categoría
            4. 💰 Impacto financiero del inventario actual
            5. 🎯 Recomendaciones de restock con cantidades específicas
            6. 📈 Predicciones de demanda para próximos 30 días
            
            Sé específico con números y fechas.
            """
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022", 
                max_tokens=2500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            return f"Error al analizar inventario: {str(e)}"
    
    def detectar_oportunidades_comerciales(self):
        """
        Identifica oportunidades de negocio basadas en datos históricos
        """
        try:
            # Combinar datos de ventas, compras y clientes
            datos_comerciales = self._obtener_datos_comerciales_completos()
            
            prompt = f"""
            Actúa como Consultor Estratégico Comercial. Analiza estos datos para identificar oportunidades:
            
            DATOS COMERCIALES COMPLETOS:
            {datos_comerciales}
            
            IDENTIFICA:
            1. 🎯 Oportunidades de cross-selling y up-selling
            2. 🆕 Nichos de mercado no explotados  
            3. 👥 Segmentos de clientes con potencial de crecimiento
            4. 📈 Productos con tendencia de crecimiento
            5. 💡 Estrategias de pricing optimization
            6. 🤝 Oportunidades de expansión geográfica
            
            Para cada oportunidad incluye:
            - Potencial de ingresos estimado
            - Nivel de dificultad de implementación  
            - Timeframe recomendado
            - Próximos pasos específicos
            """
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=3500, 
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            return f"Error al detectar oportunidades: {str(e)}"
    
    def _obtener_datos_ventas(self, periodo):
        """Obtiene datos de ventas del período especificado"""
        from apps.ventas.models import Venta
        from datetime import datetime, timedelta
        
        if periodo == 'último_mes':
            fecha_inicio = datetime.now() - timedelta(days=30)
        elif periodo == 'último_trimestre':
            fecha_inicio = datetime.now() - timedelta(days=90)
        else:
            fecha_inicio = datetime.now() - timedelta(days=30)
            
        ventas = Venta.objects.filter(
            empresa=self.empresa,
            fecha_emision__gte=fecha_inicio
        ).select_related('cliente').prefetch_related('detalles__producto')
        
        # Estructurar datos para análisis
        datos = {
            'total_ventas': ventas.count(),
            'ingresos_totales': sum(v.total for v in ventas),
            'ticket_promedio': sum(v.total for v in ventas) / len(ventas) if ventas else 0,
            'top_productos': {},
            'top_clientes': {},
            'ventas_por_dia': {}
        }
        
        # Análisis por productos
        for venta in ventas:
            for detalle in venta.detalles.all():
                producto = detalle.producto.nombre
                if producto not in datos['top_productos']:
                    datos['top_productos'][producto] = {
                        'cantidad': 0,
                        'ingresos': 0
                    }
                datos['top_productos'][producto]['cantidad'] += detalle.cantidad
                datos['top_productos'][producto]['ingresos'] += detalle.subtotal
        
        return datos
    
    def _obtener_datos_inventario(self):
        """Obtiene datos completos de inventario para análisis"""
        from apps.inventario.models import Producto, Stock, MovimientoInventario
        
        productos = Producto.objects.filter(empresa=self.empresa)
        datos = []
        
        for producto in productos:
            # Obtener stock actual
            stock_total = sum(s.cantidad for s in producto.stocks.all())
            
            # Obtener movimientos recientes
            movimientos_recientes = MovimientoInventario.objects.filter(
                empresa=self.empresa,
                producto=producto
            ).order_by('-fecha')[:10]
            
            datos.append({
                'producto': producto.nombre,
                'sku': producto.sku,
                'stock_actual': stock_total,
                'stock_minimo': producto.stock_minimo,
                'precio_venta': float(producto.precio_venta),
                'movimientos_recientes': [
                    {
                        'fecha': m.fecha,
                        'tipo': m.tipo_movimiento,
                        'cantidad': float(m.cantidad_entrada - m.cantidad_salida)
                    } for m in movimientos_recientes
                ]
            })
        
        return datos
    
    def _obtener_datos_comerciales_completos(self):
        """Combina todos los datos comerciales para análisis integral"""
        datos_ventas = self._obtener_datos_ventas('último_trimestre')
        datos_inventario = self._obtener_datos_inventario()
        
        from apps.compras.models import Compra
        from apps.ventas.models import Cliente
        
        # Datos de compras
        compras_recientes = Compra.objects.filter(
            empresa=self.empresa
        ).order_by('-fecha_emision')[:20]
        
        # Datos de clientes
        clientes_activos = Cliente.objects.filter(
            empresa=self.empresa,
            ventas__fecha_emision__gte=datetime.now() - timedelta(days=90)
        ).distinct()
        
        return {
            'ventas': datos_ventas,
            'inventario': datos_inventario,
            'compras_recientes': [
                {
                    'numero': c.numero,
                    'proveedor': c.proveedor.nombre,
                    'total': float(c.total),
                    'fecha': c.fecha_emision
                } for c in compras_recientes
            ],
            'clientes_activos': clientes_activos.count(),
            'empresa_info': {
                'nombre': self.empresa.nombre,
                'fecha_creacion': self.empresa.created_at
            }
        } 