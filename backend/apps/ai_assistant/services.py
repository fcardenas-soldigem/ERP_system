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
import json
logger = logging.getLogger(__name__)

class AIAssistantService:
    def __init__(self, conversation):
        # Solo contexto de BD y carga de archivos. El chat vive en services/chat.py.
        self.conversation = conversation
        self.empresa = conversation.empresa

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
