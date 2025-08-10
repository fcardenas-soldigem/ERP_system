from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from apps.ventas.models import Venta, Cliente
from apps.compras.models import Compra, Proveedor
from apps.inventario.models import Producto

class AdminExecutor:
    def __init__(self, user):
        self.user = user
        self.empresa = user.empresa

    def execute_function(self, function_name, arguments):
        """Ejecutar función de administración"""
        if function_name == 'dirigir_agente':
            return self.dirigir_agente(**arguments)
        elif function_name == 'resumen_ejecutivo':
            return self.resumen_ejecutivo(**arguments)
        elif function_name == 'consulta_general':
            return self.consulta_general(**arguments)
        else:
            return {
                'success': False,
                'error': f'Función {function_name} no reconocida para administrador'
            }

    def dirigir_agente(self, **kwargs):
        """Dirigir al usuario hacia el agente apropiado"""
        try:
            agente_recomendado = kwargs.get('agente_recomendado')
            razon = kwargs.get('razon')
            mensaje_usuario = kwargs.get('mensaje_usuario')

            # URLs de los agentes
            agentes_info = {
                'jorge': {
                    'nombre': 'Jorge - Analista Comercial',
                    'descripcion': 'Especialista en análisis, reportes y tendencias comerciales',
                    'icono': '📊',
                    'url': '/dashboard', # Jorge está en el AIAssistantSimple global
                    'color': 'blue'
                },
                'ventas': {
                    'nombre': 'Asistente de Ventas',
                    'descripcion': 'Crear ventas, buscar clientes y productos',
                    'icono': '🛒',
                    'url': '/ventas', # Chatbar integrado en módulo ventas
                    'color': 'blue'
                },
                'compras': {
                    'nombre': 'Asistente de Compras',
                    'descripcion': 'Crear órdenes de compra, buscar proveedores',
                    'icono': '📦',
                    'url': '/compras', # Chatbar integrado en módulo compras
                    'color': 'green'
                }
            }

            agente_info = agentes_info.get(agente_recomendado, agentes_info['jorge'])

            return {
                'success': True,
                'agente_recomendado': agente_recomendado,
                'agente_info': agente_info,
                'razon': razon,
                'mensaje_original': mensaje_usuario,
                'recomendacion': f"""
🎯 **Recomendación de Agente**

{agente_info['icono']} **{agente_info['nombre']}**
📋 {agente_info['descripcion']}

**¿Por qué este agente?**
{razon}

**¿Cómo acceder?**
• Ve al módulo correspondiente en tu ERP
• Busca el botón flotante del asistente
• Haz tu consulta específica allí

¡Te ayudará de manera más especializada!
""",
                'mensaje': f'Recomiendo contactar a {agente_info["nombre"]} para tu consulta'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error dirigiendo agente: {str(e)}'
            }

    def resumen_ejecutivo(self, **kwargs):
        """Generar resumen ejecutivo del negocio"""
        try:
            tipo_resumen = kwargs.get('tipo_resumen', 'general')
            periodo = kwargs.get('periodo', 'mes')

            # Definir período
            ahora = timezone.now()
            if periodo == 'semana':
                fecha_inicio = ahora - timedelta(days=7)
                periodo_texto = "esta semana"
            elif periodo == 'mes':
                fecha_inicio = ahora - timedelta(days=30)
                periodo_texto = "este mes"
            elif periodo == 'trimestre':
                fecha_inicio = ahora - timedelta(days=90)
                periodo_texto = "este trimestre"
            else:
                fecha_inicio = ahora - timedelta(days=30)
                periodo_texto = "este mes"

            # Métricas de ventas
            ventas_metricas = Venta.objects.filter(
                empresa=self.empresa,
                fecha_emision__gte=fecha_inicio
            ).aggregate(
                total_ventas=Count('id'),
                monto_ventas=Sum('total'),
                promedio_venta=Avg('total')
            )

            # Métricas de compras
            compras_metricas = Compra.objects.filter(
                empresa=self.empresa,
                fecha_orden__gte=fecha_inicio
            ).aggregate(
                total_compras=Count('id'),
                monto_compras=Sum('total')
            )

            # Métricas de inventario
            total_productos = Producto.objects.filter(empresa=self.empresa).count()
            productos_bajo_stock = 0
            valor_inventario = 0
            
            for producto in Producto.objects.filter(empresa=self.empresa):
                stock = producto.get_stock()
                if stock < 10:
                    productos_bajo_stock += 1
                if producto.precio_venta:
                    valor_inventario += stock * producto.precio_venta

            # Clientes y proveedores
            total_clientes = Cliente.objects.filter(empresa=self.empresa).count()
            total_proveedores = Proveedor.objects.filter(empresa=self.empresa).count()

            resumen_completo = f"""
🏢 **RESUMEN EJECUTIVO - {self.empresa.nombre}**
📅 *Período: {periodo_texto}*

## 💰 VENTAS
• **Volumen**: {ventas_metricas['total_ventas'] or 0} ventas
• **Facturación**: S/ {ventas_metricas['monto_ventas'] or 0:,.2f}
• **Ticket promedio**: S/ {ventas_metricas['promedio_venta'] or 0:,.2f}

## 📦 COMPRAS  
• **Órdenes**: {compras_metricas['total_compras'] or 0} compras
• **Inversión**: S/ {compras_metricas['monto_compras'] or 0:,.2f}

## 📊 INVENTARIO
• **Productos**: {total_productos} SKUs
• **Valor estimado**: S/ {valor_inventario:,.2f}
• **Alertas**: {productos_bajo_stock} productos con stock bajo

## 👥 RELACIONES COMERCIALES
• **Clientes**: {total_clientes} registrados
• **Proveedores**: {total_proveedores} registrados

---
**💡 Recomendación**: {"Excelente performance" if (ventas_metricas['total_ventas'] or 0) > 10 else "Considera revisar estrategias de ventas"}
"""

            return {
                'success': True,
                'tipo_resumen': tipo_resumen,
                'periodo': periodo,
                'metricas': {
                    'ventas': ventas_metricas,
                    'compras': compras_metricas,
                    'inventario': {
                        'total_productos': total_productos,
                        'productos_bajo_stock': productos_bajo_stock,
                        'valor_inventario': valor_inventario
                    },
                    'relaciones': {
                        'total_clientes': total_clientes,
                        'total_proveedores': total_proveedores
                    }
                },
                'resumen_texto': resumen_completo,
                'mensaje': f'Resumen ejecutivo generado para {periodo_texto}'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error generando resumen: {str(e)}'
            }

    def consulta_general(self, **kwargs):
        """Responder consultas generales del sistema"""
        try:
            consulta = kwargs.get('consulta', '').lower()
            requiere_datos = kwargs.get('requiere_datos', False)

            # Respuestas según tipo de consulta
            if any(palabra in consulta for palabra in ['ayuda', 'help', 'asistencia', 'cómo']):
                respuesta = """
🆘 **CENTRO DE AYUDA ERP**

**Agentes Disponibles:**
📊 **Jorge** - Análisis y reportes comerciales
🛒 **Asistente de Ventas** - Crear ventas y buscar clientes
📦 **Asistente de Compras** - Órdenes de compra y proveedores

**¿Cómo usar los agentes?**
1. Ve al módulo correspondiente
2. Busca el botón flotante del asistente
3. Haz tu consulta en lenguaje natural

**Consultas frecuentes:**
• "Crear venta para cliente X"
• "¿Cómo van las ventas?"
• "Necesito comprar productos"
• "¿Qué productos tienen stock bajo?"
"""

            elif any(palabra in consulta for palabra in ['agentes', 'asistentes', 'bots']):
                respuesta = """
🤖 **EQUIPO DE AGENTES INTELIGENTES**

**🔍 Jorge - Analista Comercial**
• Análisis de ventas, clientes e inventario
• Reportes y tendencias
• Insights comerciales

**🛒 Asistente de Ventas**
• Crear ventas rápidamente
• Buscar clientes y productos
• Calcular totales automáticamente

**📦 Asistente de Compras**
• Crear órdenes de compra
• Buscar proveedores
• Gestionar inventario de entrada

¡Cada uno especializado en su área!
"""

            elif any(palabra in consulta for palabra in ['módulos', 'funciones', 'características']):
                respuesta = """
🏗️ **MÓDULOS DEL SISTEMA ERP**

**📊 Dashboard**
• Métricas generales
• Jorge - Analista comercial

**💰 Ventas**
• Gestión de clientes
• Facturación
• Asistente de ventas integrado

**📦 Compras**
• Gestión de proveedores
• Órdenes de compra
• Asistente de compras integrado

**📋 Inventario**
• Control de stock
• Productos y categorías
• Movimientos automáticos

**🏢 Empresas**
• Configuración multi-empresa
• Usuarios y permisos
"""

            else:
                respuesta = f"""
❓ **Consulta Recibida**: {kwargs.get('consulta')}

Como administrador de agentes, te recomiendo:

1. **Para análisis**: Contacta a Jorge
2. **Para ventas**: Usa el asistente de ventas
3. **Para compras**: Usa el asistente de compras

¿Puedes ser más específico sobre qué necesitas?
"""

            return {
                'success': True,
                'consulta_original': kwargs.get('consulta'),
                'requiere_datos': requiere_datos,
                'respuesta': respuesta.strip(),
                'mensaje': 'Consulta general procesada exitosamente'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error procesando consulta: {str(e)}'
            } 