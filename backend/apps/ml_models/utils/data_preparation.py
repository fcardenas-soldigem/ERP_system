"""
Utilidades para preparación de datos para modelos ML
"""
import pandas as pd
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Max, Min, Avg, F
from django.utils import timezone


def prepare_customer_data(empresa_id=None):
    """
    Prepara datos de clientes para análisis RFM
    
    Returns:
        DataFrame con columnas: cliente_id, recency, frequency, monetary
    """
    from apps.ventas.models import Venta
    from apps.core.models import Cliente
    
    # Filtrar por empresa si se proporciona
    ventas_qs = Venta.objects.all()
    if empresa_id:
        ventas_qs = ventas_qs.filter(empresa_id=empresa_id)
    
    # Calcular fecha de referencia (hoy)
    today = timezone.now().date()
    
    # Obtener datos agregados por cliente
    customer_data = ventas_qs.values('cliente_id').annotate(
        ultima_compra=Max('fecha'),
        total_compras=Count('id'),
        monto_total=Sum('total'),
        ticket_promedio=Avg('total'),
        primera_compra=Min('fecha')
    )
    
    # Convertir a DataFrame
    df = pd.DataFrame(list(customer_data))
    
    if df.empty:
        return pd.DataFrame(columns=['cliente_id', 'recency', 'frequency', 'monetary', 'avg_ticket'])
    
    # Calcular recency (días desde última compra)
    df['recency'] = df['ultima_compra'].apply(lambda x: (today - x).days)
    
    # Renombrar columnas
    df = df.rename(columns={
        'total_compras': 'frequency',
        'monto_total': 'monetary',
        'ticket_promedio': 'avg_ticket'
    })
    
    # Calcular antigüedad del cliente
    df['customer_age_days'] = df['primera_compra'].apply(lambda x: (today - x).days)
    
    return df[['cliente_id', 'recency', 'frequency', 'monetary', 'avg_ticket', 'customer_age_days']]


def prepare_product_transactions(empresa_id=None):
    """
    Prepara datos de transacciones de productos para análisis de asociación
    
    Returns:
        DataFrame con columnas: venta_id, producto_id
    """
    from apps.ventas.models import VentaDetalle
    
    # Filtrar por empresa si se proporciona
    detalles_qs = VentaDetalle.objects.select_related('venta', 'producto')
    if empresa_id:
        detalles_qs = detalles_qs.filter(venta__empresa_id=empresa_id)
    
    # Obtener transacciones
    transactions = detalles_qs.values('venta_id', 'producto_id', 'producto__nombre')
    
    df = pd.DataFrame(list(transactions))
    
    return df


def prepare_demand_data(producto_id, empresa_id=None, days_back=365):
    """
    Prepara datos históricos de ventas para predicción de demanda
    
    Args:
        producto_id: ID del producto
        empresa_id: ID de la empresa (opcional)
        days_back: Días históricos a considerar
    
    Returns:
        DataFrame con columnas: fecha, cantidad
    """
    from apps.ventas.models import VentaDetalle
    from django.db.models import Sum
    
    # Calcular fecha de inicio
    fecha_inicio = timezone.now().date() - timedelta(days=days_back)
    
    # Filtrar ventas del producto
    ventas_qs = VentaDetalle.objects.filter(
        producto_id=producto_id,
        venta__fecha__gte=fecha_inicio
    ).select_related('venta')
    
    if empresa_id:
        ventas_qs = ventas_qs.filter(venta__empresa_id=empresa_id)
    
    # Agrupar por fecha
    ventas_por_dia = ventas_qs.values('venta__fecha_emision').annotate(
        cantidad_total=Sum('cantidad')
    ).order_by('venta__fecha_emision')
    
    df = pd.DataFrame(list(ventas_por_dia))
    
    if df.empty:
        return pd.DataFrame(columns=['ds', 'y'])
    
    # Renombrar columnas para Prophet (requiere 'ds' y 'y')
    df = df.rename(columns={
        'venta__fecha': 'ds',
        'cantidad_total': 'y'
    })
    
    # Asegurar que ds sea datetime
    df['ds'] = pd.to_datetime(df['ds'])
    
    # Rellenar días sin ventas con 0
    date_range = pd.date_range(start=df['ds'].min(), end=df['ds'].max(), freq='D')
    df = df.set_index('ds').reindex(date_range, fill_value=0).reset_index()
    df.columns = ['ds', 'y']
    
    return df


def normalize_features(df, columns):
    """
    Normaliza características usando StandardScaler
    
    Args:
        df: DataFrame
        columns: Lista de columnas a normalizar
    
    Returns:
        DataFrame normalizado, scaler usado
    """
    from sklearn.preprocessing import StandardScaler
    
    scaler = StandardScaler()
    df_normalized = df.copy()
    df_normalized[columns] = scaler.fit_transform(df[columns])
    
    return df_normalized, scaler


def get_product_info(producto_id):
    """Obtiene información del producto"""
    from apps.inventario.models import Producto
    
    try:
        producto = Producto.objects.get(id=producto_id)
        return {
            'id': producto.id,
            'nombre': producto.nombre,
            'codigo': producto.codigo,
            'categoria': producto.categoria.nombre if producto.categoria else None,
            'precio': float(producto.precio_venta)
        }
    except Producto.DoesNotExist:
        return None


def get_cliente_info(cliente_id):
    """Obtiene información del cliente"""
    from apps.core.models import Cliente
    
    try:
        cliente = Cliente.objects.get(id=cliente_id)
        return {
            'id': cliente.id,
            'nombre': cliente.nombre,
            'documento': cliente.documento,
            'tipo': cliente.tipo_documento
        }
    except Cliente.DoesNotExist:
        return None

