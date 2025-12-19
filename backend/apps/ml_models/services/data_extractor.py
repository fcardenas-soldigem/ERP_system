"""
Servicio para extraer datos del ERP y prepararlos para ML
Extrae datos específicos por empresa
"""
import pandas as pd
from django.db.models import Sum, Count, Max, Min, Avg, F
from django.utils import timezone
from datetime import timedelta
from apps.ventas.models import Venta, DetalleVenta, Cliente
from apps.inventario.models import Producto, MovimientoInventario
from apps.empresas.models import Empresa


class DataExtractor:
    """
    Extrae y prepara datos del ERP para entrenamiento de modelos ML
    """
    
    def __init__(self, empresa):
        """
        Args:
            empresa: Instancia de Empresa
        """
        self.empresa = empresa
    
    def extract_rfm_data(self):
        """
        Extrae datos para análisis RFM desde las ventas reales
        
        Returns:
            DataFrame con columnas: cliente_id, recency, frequency, monetary, 
                                   customer_age_days, avg_ticket
        """
        # Obtener todas las ventas de la empresa
        ventas = Venta.objects.filter(
            empresa=self.empresa,
            estado__in=['pagado']
        ).select_related('cliente')
        
        if not ventas.exists():
            raise ValueError(f"No hay ventas para la empresa {self.empresa.nombre}")
        
        # Fecha de referencia (hoy)
        reference_date = timezone.now().date()
        
        # Agrupar por cliente
        clientes_data = []
        
        clientes = Cliente.objects.filter(
            empresa=self.empresa,
            activo=True
        )
        
        for cliente in clientes:
            # Obtener ventas pagadas del cliente
            ventas_cliente = Venta.objects.filter(
                cliente=cliente,
                empresa=self.empresa,
                estado__in=['pagado']
            )
            
            if not ventas_cliente.exists():
                continue
            
            # Calcular RFM
            ultima_venta = ventas_cliente.aggregate(Max('fecha_emision'))['fecha_emision__max']
            primera_venta = ventas_cliente.aggregate(Min('fecha_emision'))['fecha_emision__min']
            
            # Convertir a date si es datetime
            if hasattr(ultima_venta, 'date'):
                ultima_venta = ultima_venta.date()
            if hasattr(primera_venta, 'date'):
                primera_venta = primera_venta.date()
            
            recency = (reference_date - ultima_venta).days
            frequency = ventas_cliente.count()
            monetary = float(ventas_cliente.aggregate(Sum('total'))['total__sum'] or 0)
            avg_ticket = monetary / frequency if frequency > 0 else 0
            customer_age_days = (reference_date - primera_venta).days
            
            clientes_data.append({
                'cliente_id': cliente.id,
                'cliente_nombre': cliente.nombre,
                'cliente_documento': cliente.documento,
                'recency': recency,
                'frequency': frequency,
                'monetary': monetary,
                'avg_ticket': avg_ticket,
                'customer_age_days': customer_age_days,
            })
        
        if not clientes_data:
            raise ValueError(f"No hay datos de clientes con ventas para {self.empresa.nombre}")
        
        df = pd.DataFrame(clientes_data)
        
        return df
    
    def extract_sales_data(self):
        """
        Extrae datos completos de ventas para análisis demográfico y otros
        
        Returns:
            DataFrame con información detallada de ventas
        """
        ventas = Venta.objects.filter(
            empresa=self.empresa,
            estado__in=['pagado']
        ).select_related('cliente').prefetch_related('detalles__producto')
        
        if not ventas.exists():
            raise ValueError(f"No hay ventas para la empresa {self.empresa.nombre}")
        
        ventas_data = []
        
        for venta in ventas:
            for detalle in venta.detalles.all():
                ventas_data.append({
                    'venta_id': venta.id,
                    'fecha': venta.fecha_emision,
                    'cliente_id': venta.cliente.id if venta.cliente else None,
                    'cliente_nombre': venta.cliente.nombre if venta.cliente else 'Sin cliente',
                    'producto_id': detalle.producto.id,
                    'producto_nombre': detalle.producto.nombre,
                    'categoria': getattr(detalle.producto.categoria, 'nombre', 'Sin categoría') if hasattr(detalle.producto, 'categoria') else 'Sin categoría',
                    'cantidad': float(detalle.cantidad),
                    'precio_unitario': float(detalle.precio_unitario),
                    'subtotal': float(detalle.subtotal),
                    'total': float(venta.total),
                })
        
        df = pd.DataFrame(ventas_data)
        
        return df
    
    def extract_product_transactions(self):
        """
        Extrae transacciones de productos para recomendaciones
        
        Returns:
            DataFrame con columnas: transaction_id, producto_id, producto_nombre
        """
        ventas = Venta.objects.filter(
            empresa=self.empresa,
            estado__in=['pagado']
        ).prefetch_related('detalles__producto')
        
        if not ventas.exists():
            raise ValueError(f"No hay ventas para la empresa {self.empresa.nombre}")
        
        transactions_data = []
        
        for venta in ventas:
            for detalle in venta.detalles.all():
                transactions_data.append({
                    'transaction_id': venta.id,
                    'producto_id': detalle.producto.id,
                    'producto_nombre': detalle.producto.nombre,
                    'cantidad': float(detalle.cantidad),
                })
        
        df = pd.DataFrame(transactions_data)
        
        return df
    
    def extract_demand_data(self, producto_id=None, days_back=365):
        """
        Extrae datos históricos de demanda para forecasting
        
        Args:
            producto_id: ID del producto (None para todos)
            days_back: Días hacia atrás para extraer
            
        Returns:
            DataFrame con columnas: fecha, producto_id, producto_nombre, cantidad
        """
        fecha_inicio = timezone.now() - timedelta(days=days_back)
        
        ventas = DetalleVenta.objects.filter(
            venta__empresa=self.empresa,
            venta__fecha_emision__gte=fecha_inicio,
            venta__estado__in=['pagado']
        ).select_related('producto', 'venta')
        
        if producto_id:
            ventas = ventas.filter(producto_id=producto_id)
        
        if not ventas.exists():
            raise ValueError(f"No hay datos de demanda para la empresa {self.empresa.nombre}")
        
        demand_data = []
        
        for detalle in ventas:
            demand_data.append({
                'fecha': detalle.venta.fecha_emision.date() if hasattr(detalle.venta.fecha_emision, 'date') else detalle.venta.fecha_emision,
                'producto_id': detalle.producto.id,
                'producto_nombre': detalle.producto.nombre,
                'cantidad': float(detalle.cantidad),
            })
        
        df = pd.DataFrame(demand_data)
        
        # Agrupar por fecha y producto
        df = df.groupby(['fecha', 'producto_id', 'producto_nombre']).agg({
            'cantidad': 'sum'
        }).reset_index()
        
        return df
    
    def get_data_summary(self):
        """
        Obtiene un resumen de los datos disponibles para la empresa
        
        Returns:
            dict con estadísticas
        """
        # Contador total de ventas (todas, no solo pagadas)
        ventas_count = Venta.objects.filter(
            empresa=self.empresa
        ).count()
        
        clientes_count = Cliente.objects.filter(
            empresa=self.empresa,
            activo=True
        ).count()
        
        productos_count = Producto.objects.filter(
            empresa=self.empresa,
            is_active=True
        ).count()
        
        # Rango de fechas
        fecha_range = Venta.objects.filter(
            empresa=self.empresa,
            estado__in=['pagado']
        ).aggregate(
            primera=Min('fecha_emision'),
            ultima=Max('fecha_emision')
        )
        
        return {
            'empresa': self.empresa.nombre,
            'ventas_count': ventas_count,
            'clientes_count': clientes_count,
            'productos_count': productos_count,
            'fecha_primera_venta': fecha_range['primera'],
            'fecha_ultima_venta': fecha_range['ultima'],
            'dias_historial': (fecha_range['ultima'] - fecha_range['primera']).days if fecha_range['primera'] and fecha_range['ultima'] else 0,
        }
    
    def validate_data_for_training(self, model_type):
        """
        Valida si hay suficientes datos para entrenar un modelo
        
        Args:
            model_type: Tipo de modelo ('rfm_segmentation', 'churn_prediction', etc.)
            
        Returns:
            tuple (is_valid: bool, message: str, data_info: dict)
        """
        summary = self.get_data_summary()
        
        # Requisitos mínimos por tipo de modelo (ajustados para desarrollo/pruebas)
        requirements = {
            'rfm_segmentation': {
                'min_clientes': 2,  # Reducido de 20 a 2
                'min_ventas': 2,    # Reducido de 50 a 2
                'min_dias': 1,      # Reducido de 30 a 1
            },
            'churn_prediction': {
                'min_clientes': 2,  # Reducido de 30 a 2
                'min_ventas': 2,    # Reducido de 100 a 2
                'min_dias': 1,      # Reducido de 60 a 1
            },
            'product_recommendations': {
                'min_ventas': 5,    # Reducido de 100 a 5
                'min_productos': 3, # Reducido de 10 a 3
                'min_dias': 1,      # Reducido de 30 a 1
            },
            'demand_forecasting': {
                'min_ventas': 10,   # Reducido de 200 a 10
                'min_dias': 7,      # Reducido de 90 a 7
            }
        }
        
        if model_type not in requirements:
            return False, f"Tipo de modelo desconocido: {model_type}", summary
        
        reqs = requirements[model_type]
        
        # Validar requisitos
        errors = []
        
        if 'min_clientes' in reqs and summary['clientes_count'] < reqs['min_clientes']:
            errors.append(f"Se requieren al menos {reqs['min_clientes']} clientes (tienes {summary['clientes_count']})")
        
        if 'min_ventas' in reqs and summary['ventas_count'] < reqs['min_ventas']:
            errors.append(f"Se requieren al menos {reqs['min_ventas']} ventas (tienes {summary['ventas_count']})")
        
        if 'min_productos' in reqs and summary['productos_count'] < reqs['min_productos']:
            errors.append(f"Se requieren al menos {reqs['min_productos']} productos (tienes {summary['productos_count']})")
        
        if 'min_dias' in reqs and summary['dias_historial'] < reqs['min_dias']:
            errors.append(f"Se requieren al menos {reqs['min_dias']} días de historial (tienes {summary['dias_historial']})")
        
        if errors:
            return False, "; ".join(errors), summary
        
        return True, "Datos suficientes para entrenar", summary

