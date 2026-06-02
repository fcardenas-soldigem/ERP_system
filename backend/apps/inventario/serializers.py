from rest_framework import serializers
from .models import (
    Almacen, Categoria, Producto, Stock, AjusteInventario, MovimientoInventario,
    InventarioMateriasPrimas, InventarioProductosTerminados
)
from django.db import transaction
from django.db.models import Sum
from apps.empresas.models import Empresa

class AlmacenSerializer(serializers.ModelSerializer):
    empresa = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Almacen
        fields = ['id', 'nombre', 'direccion', 'is_active', 'empresa', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class CategoriaSerializer(serializers.ModelSerializer):
    empresa = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Categoria
        fields = '__all__'

    def validate(self, data):
        request = self.context.get('request')
        if request and request.user and request.user.empresa:
            empresa = request.user.empresa
            nombre = data.get('nombre')
            if nombre:
                if Categoria.objects.filter(empresa=empresa, nombre=nombre).exists():
                    raise serializers.ValidationError(
                        {'nombre': 'Ya existe una categoría con este nombre en tu empresa'}
                    )
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.empresa:
            validated_data['empresa'] = request.user.empresa
        return super().create(validated_data)

class StockPorAlmacenSerializer(serializers.ModelSerializer):
    almacen_nombre = serializers.CharField(source='almacen.nombre')
    
    class Meta:
        model = Stock
        fields = ['almacen', 'almacen_nombre', 'cantidad']

class ProductoSerializer(serializers.ModelSerializer):
    stock = serializers.IntegerField(write_only=True, required=False, default=0)
    stock_total = serializers.SerializerMethodField()
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    almacen_nombre = serializers.CharField(source='almacen.nombre', read_only=True)
    stocks_por_almacen = StockPorAlmacenSerializer(source='stocks', many=True, read_only=True)
    alerta_stock = serializers.SerializerMethodField()
    empresa = serializers.PrimaryKeyRelatedField(read_only=True)
    tipo_producto_display = serializers.SerializerMethodField()
    es_materia_prima = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id', 'sku', 'nombre', 'descripcion',
            'stock_total', 'stock_minimo', 'stock_maximo',
            'categoria', 'categoria_nombre', 'almacen',
            'almacen_nombre', 'is_active', 'precio_compra',
            'precio_venta', 'moneda', 'margen', 'stocks_por_almacen',
            'stock', 'alerta_stock', 'empresa', 'unidad_medida',
            'tipo_producto', 'tipo_producto_display', 'es_materia_prima'
        ]
        read_only_fields = ['empresa', 'margen', 'stock_total', 'alerta_stock', 'tipo_producto_display', 'es_materia_prima']

    def get_tipo_producto_display(self, obj):
        """Retorna el nombre legible del tipo de producto"""
        tipos = {
            'RAW': 'Materia Prima',
            'SEMIFINISHED': 'Semi-Elaborado',
            'FINISHED': 'Producto Terminado',
            'SERVICE': 'Servicio'
        }
        return tipos.get(obj.tipo_producto, obj.tipo_producto)
    
    def get_es_materia_prima(self, obj):
        """Indica si el producto es materia prima o insumo"""
        return obj.tipo_producto in ['RAW', 'SEMIFINISHED']

    def get_stocks_por_almacen(self, obj):
        stocks = Stock.objects.filter(
            producto=obj,
            empresa=obj.empresa
        ).values('almacen__nombre', 'cantidad')
        return [
            {
                'almacen': stock['almacen__nombre'],
                'cantidad': stock['cantidad']
            }
            for stock in stocks
        ]

    def get_stock_total(self, obj):
        """
        Calcula el stock total sumando todos los stocks del producto
        """
        total = Stock.objects.filter(
            producto=obj,
            empresa=obj.empresa
        ).aggregate(
            total=Sum('cantidad')
        )['total'] or 0
        return total

    def get_alerta_stock(self, obj):
        """
        Determina si el producto está en alerta de stock
        """
        stock_total = self.get_stock_total(obj)
        return stock_total <= obj.stock_minimo

    def create(self, validated_data):
        from .models import InventarioMateriasPrimas, InventarioProductosTerminados
        
        request = self.context.get('request')
        stock_inicial = validated_data.pop('stock', 0)
        
        if request and request.user and request.user.empresa:
            validated_data['empresa'] = request.user.empresa
        
        # Crear el producto
        producto = Producto.objects.create(**validated_data)
        
        almacen = producto.almacen
        
        # ========================================
        # CREAR INVENTARIO SEGÚN TIPO DE PRODUCTO
        # ========================================
        if producto.tipo_producto in ['RAW', 'SEMIFINISHED']:
            # Materias primas e insumos → InventarioMateriasPrimas
            if almacen:
                inv_mp, created = InventarioMateriasPrimas.objects.get_or_create(
                    empresa=producto.empresa,
                    producto=producto,
                    almacen=almacen,
                    defaults={
                        'cantidad_disponible': stock_inicial,
                        'cantidad_reservada': 0,
                        'costo_unitario_promedio': producto.precio_compra or 0,
                        'stock_minimo': producto.stock_minimo,
                        'stock_maximo': producto.stock_maximo,
                    }
                )
                if not created and stock_inicial > 0:
                    inv_mp.cantidad_disponible += stock_inicial
                    inv_mp.save()
        elif producto.tipo_producto == 'FINISHED':
            # Productos terminados → InventarioProductosTerminados
            if almacen:
                inv_pt, created = InventarioProductosTerminados.objects.get_or_create(
                    empresa=producto.empresa,
                    producto=producto,
                    almacen=almacen,
                    defaults={
                        'cantidad_disponible': stock_inicial,
                        'cantidad_reservada': 0,
                        'costo_produccion_unitario': producto.precio_compra or 0,
                        'precio_venta_sugerido': producto.precio_venta or 0,
                        'stock_minimo': producto.stock_minimo,
                        'stock_maximo': producto.stock_maximo,
                    }
                )
                if not created and stock_inicial > 0:
                    inv_pt.cantidad_disponible += stock_inicial
                    inv_pt.save()
        # También crear en Stock para compatibilidad con otras partes del sistema
        if almacen:
            stock_obj, created = Stock.objects.get_or_create(
                producto=producto,
                almacen=almacen,
                empresa=producto.empresa,
                defaults={'cantidad': stock_inicial}
            )
            if not created and stock_inicial > 0:
                stock_obj.cantidad += stock_inicial
                stock_obj.save()
        
        return producto

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.empresa:
            validated_data['empresa'] = request.user.empresa
        return super().update(instance, validated_data)

    def validate(self, data):
        """
        Validaciones completas para productos:
        - Categoría y almacén deben pertenecer a la empresa
        - Stock mínimo no puede ser mayor al máximo
        - Materias primas: precio_venta = 0, precio_compra obligatorio
        - Productos terminados: precio_venta obligatorio y >= precio_compra
        """
        request = self.context.get('request')
        
        # Validaciones de empresa
        if request and request.user and request.user.empresa:
            if 'categoria' in data:
                categoria = data['categoria']
                if categoria.empresa != request.user.empresa:
                    raise serializers.ValidationError(
                        {'categoria': 'Esta categoría no pertenece a tu empresa'}
                    )

            if 'almacen' in data:
                almacen = data['almacen']
                if almacen.empresa != request.user.empresa:
                    raise serializers.ValidationError(
                        {'almacen': 'Este almacén no pertenece a tu empresa'}
                    )

        # Validación de stock
        if 'stock_minimo' in data and 'stock_maximo' in data:
            if data['stock_minimo'] > data['stock_maximo']:
                raise serializers.ValidationError(
                    'El stock mínimo no puede ser mayor al stock máximo'
                )
        
        # ========================================
        # VALIDACIONES DE TIPO DE PRODUCTO
        # ========================================
        tipo_producto = data.get('tipo_producto')
        if not tipo_producto and self.instance:
            tipo_producto = self.instance.tipo_producto
        if not tipo_producto:
            tipo_producto = 'FINISHED'
            
        precio_venta = data.get('precio_venta')
        precio_compra = data.get('precio_compra')
        
        # Materias primas e insumos
        if tipo_producto in ['RAW', 'SEMIFINISHED']:
            # Forzar precio_venta = 0 para materias primas
            data['precio_venta'] = 0
            
            # El precio de compra es obligatorio para materias primas
            if precio_compra is None:
                raise serializers.ValidationError({
                    'precio_compra': 'El precio de compra es obligatorio para materias primas.'
                })
            try:
                pc = float(precio_compra)
                if pc <= 0:
                    raise serializers.ValidationError({
                        'precio_compra': 'El precio de compra debe ser mayor a 0 para materias primas.'
                    })
            except (ValueError, TypeError):
                raise serializers.ValidationError({
                    'precio_compra': 'El precio de compra debe ser un número válido.'
                })
        else:
            # Productos terminados: precio_venta obligatorio y >= precio_compra
            if self.instance is None or 'precio_venta' in data:
                if precio_venta is None:
                    raise serializers.ValidationError({
                        'precio_venta': 'El precio de venta es obligatorio para productos terminados.'
                    })
                try:
                    pv = float(precio_venta)
                    if pv <= 0:
                        raise serializers.ValidationError({
                            'precio_venta': 'El precio de venta debe ser mayor a 0 para productos terminados.'
                        })
                    # Validar que precio_venta >= precio_compra solo para productos terminados
                    if precio_compra is not None:
                        pc = float(precio_compra)
                        if pv < pc:
                            raise serializers.ValidationError(
                                'El precio de venta no puede ser menor al precio de compra'
                            )
                except (ValueError, TypeError):
                    raise serializers.ValidationError({
                        'precio_venta': 'El precio de venta debe ser un número válido.'
                    })
        
        return data

class StockSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)
    almacen_nombre = serializers.CharField(source='almacen.nombre', read_only=True)
    stock_total = serializers.IntegerField(source='producto.stock_total', read_only=True)
    alerta_stock = serializers.BooleanField(source='producto.alerta_stock', read_only=True)
    estado_stock = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = [
            'id', 
            'producto', 
            'almacen', 
            'cantidad', 
            'producto_nombre',
            'producto_sku',
            'almacen_nombre',
            'stock_total',
            'alerta_stock',
            'estado_stock'
        ]

    def get_estado_stock(self, obj):
        if obj.cantidad <= 0:
            return "Sin stock"
        elif obj.cantidad <= obj.producto.stock_minimo:
            return "Stock bajo"
        return "Disponible"

    def validate(self, data):
        request = self.context.get('request')
        if request and request.user and request.user.empresa:
            empresa = request.user.empresa
            producto = data.get('producto')
            almacen = data.get('almacen')

            if producto and producto.empresa != empresa:
                raise serializers.ValidationError(
                    {'producto': 'Este producto no pertenece a tu empresa'}
                )

            if almacen and almacen.empresa != empresa:
                raise serializers.ValidationError(
                    {'almacen': 'Este almacén no pertenece a tu empresa'}
                )

            if 'cantidad' in data and data['cantidad'] < 0:
                raise serializers.ValidationError(
                    {'cantidad': 'La cantidad no puede ser negativa'}
                )

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['empresa'] = request.user.empresa
        return super().create(validated_data)

class AjusteInventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = AjusteInventario
        fields = '__all__'

class MovimientoInventarioSerializer(serializers.ModelSerializer):
    """Serializer para movimientos de inventario (Kardex)"""
    
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)
    almacen_nombre = serializers.CharField(source='almacen.nombre', read_only=True)
    tipo_movimiento_display = serializers.CharField(source='get_tipo_movimiento_display', read_only=True)
    tipo_documento_display = serializers.CharField(source='get_tipo_documento_display', read_only=True)
    
    class Meta:
        model = MovimientoInventario
        fields = [
            'id',
            'fecha',
            'tipo_movimiento',
            'tipo_movimiento_display',
            'tipo_documento',
            'tipo_documento_display',
            'numero_documento',
            'producto',
            'producto_nombre',
            'producto_sku',
            'almacen',
            'almacen_nombre',
            'cantidad_entrada',
            'cantidad_salida',
            'cantidad_saldo',
            'costo_unitario',
            'costo_total_entrada',
            'costo_total_salida',
            'costo_saldo',
            'costo_promedio',
            'observaciones',
            'created_at',
            'created_by'
        ]
        read_only_fields = [
            'cantidad_saldo',
            'costo_total_entrada',
            'costo_total_salida',
            'costo_saldo',
            'costo_promedio'
        ]

class KardexSerializer(serializers.Serializer):
    """Serializer para consultas de Kardex con filtros"""
    
    producto_id = serializers.IntegerField(required=False)
    almacen_id = serializers.IntegerField(required=False)
    fecha_inicio = serializers.DateTimeField(required=False)
    fecha_fin = serializers.DateTimeField(required=False)
    
    def validate_producto_id(self, value):
        if value and not Producto.objects.filter(id=value).exists():
            raise serializers.ValidationError("El producto especificado no existe")
        return value
    
    def validate_almacen_id(self, value):
        if value and not Almacen.objects.filter(id=value).exists():
            raise serializers.ValidationError("El almacén especificado no existe")
        return value

class KardexResumenSerializer(serializers.Serializer):
    """Serializer para resumen del Kardex"""
    
    producto = ProductoSerializer(read_only=True)
    almacen = AlmacenSerializer(read_only=True)
    stock_actual = serializers.DecimalField(max_digits=12, decimal_places=4)
    costo_total = serializers.DecimalField(max_digits=15, decimal_places=4)
    costo_promedio = serializers.DecimalField(max_digits=12, decimal_places=4)
    total_entradas = serializers.DecimalField(max_digits=12, decimal_places=4)
    total_salidas = serializers.DecimalField(max_digits=12, decimal_places=4)
    ultimo_movimiento = serializers.DateTimeField()

class MovimientoInventarioCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear movimientos de inventario"""
    
    class Meta:
        model = MovimientoInventario
        fields = [
            'producto',
            'almacen',
            'fecha',
            'tipo_movimiento',
            'tipo_documento',
            'numero_documento',
            'cantidad_entrada',
            'cantidad_salida',
            'costo_unitario',
            'observaciones'
        ]
    
    def validate(self, data):
        # Validar que solo tenga entrada o salida, no ambas
        if data.get('cantidad_entrada', 0) > 0 and data.get('cantidad_salida', 0) > 0:
            raise serializers.ValidationError("Un movimiento no puede tener entrada y salida al mismo tiempo")
        
        if data.get('cantidad_entrada', 0) == 0 and data.get('cantidad_salida', 0) == 0:
            raise serializers.ValidationError("El movimiento debe tener cantidad de entrada o salida")
        
        return data
    
    def create(self, validated_data):
        empresa = self.context['request'].user.empresa
        usuario = self.context['request'].user.username
        
        if validated_data.get('cantidad_entrada', 0) > 0:
            # Es una entrada
            return MovimientoInventario.registrar_entrada(
                empresa=empresa,
                producto=validated_data['producto'],
                almacen=validated_data['almacen'],
                cantidad=validated_data['cantidad_entrada'],
                costo_unitario=validated_data['costo_unitario'],
                tipo_documento=validated_data['tipo_documento'],
                numero_documento=validated_data.get('numero_documento', ''),
                fecha=validated_data['fecha'],
                observaciones=validated_data.get('observaciones', ''),
                usuario=usuario
            )
        else:
            # Es una salida
            return MovimientoInventario.registrar_salida(
                empresa=empresa,
                producto=validated_data['producto'],
                almacen=validated_data['almacen'],
                cantidad=validated_data['cantidad_salida'],
                tipo_documento=validated_data['tipo_documento'],
                numero_documento=validated_data.get('numero_documento', ''),
                fecha=validated_data['fecha'],
                observaciones=validated_data.get('observaciones', ''),
                usuario=usuario
            )


# =============================
# SERIALIZERS PARA INVENTARIOS SEPARADOS
# =============================

class InventarioMateriasPrimasSerializer(serializers.ModelSerializer):
    """Serializer para inventario de materias primas e insumos"""
    
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)
    producto_unidad = serializers.CharField(source='producto.unidad_medida', read_only=True)
    almacen_nombre = serializers.CharField(source='almacen.nombre', read_only=True)
    cantidad_total = serializers.DecimalField(
        max_digits=12, decimal_places=4, read_only=True
    )
    valor_inventario = serializers.DecimalField(
        max_digits=15, decimal_places=4, read_only=True
    )
    estado_stock = serializers.CharField(read_only=True)
    esta_por_vencer = serializers.BooleanField(read_only=True)
    empresa = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = InventarioMateriasPrimas
        fields = [
            'id',
            'empresa',
            'producto',
            'producto_nombre',
            'producto_sku',
            'producto_unidad',
            'almacen',
            'almacen_nombre',
            'cantidad_disponible',
            'cantidad_reservada',
            'cantidad_total',
            'costo_unitario_promedio',
            'valor_inventario',
            'ubicacion_almacen',
            'stock_minimo',
            'stock_maximo',
            'lote',
            'fecha_vencimiento',
            'estado_stock',
            'esta_por_vencer',
            'ultima_actualizacion',
            'created_at',
        ]
        read_only_fields = [
            'empresa', 'cantidad_total', 'valor_inventario', 
            'estado_stock', 'esta_por_vencer', 'ultima_actualizacion', 'created_at'
        ]
    
    def validate(self, data):
        request = self.context.get('request')
        if request and request.user and request.user.empresa:
            empresa = request.user.empresa
            
            # Validar que el producto pertenezca a la empresa
            producto = data.get('producto')
            if producto and producto.empresa != empresa:
                raise serializers.ValidationError(
                    {'producto': 'Este producto no pertenece a tu empresa'}
                )
            
            # Validar que el producto sea materia prima o semi-terminado
            if producto and producto.tipo_producto not in ['RAW', 'SEMIFINISHED']:
                raise serializers.ValidationError(
                    {'producto': 'Solo se pueden agregar materias primas o productos semi-terminados a este inventario'}
                )
            
            # Validar que el almacén pertenezca a la empresa
            almacen = data.get('almacen')
            if almacen and almacen.empresa != empresa:
                raise serializers.ValidationError(
                    {'almacen': 'Este almacén no pertenece a tu empresa'}
                )
        
        return data
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.empresa:
            validated_data['empresa'] = request.user.empresa
        return super().create(validated_data)


class InventarioMateriasPrimasCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear/actualizar inventario de materias primas"""
    
    class Meta:
        model = InventarioMateriasPrimas
        fields = [
            'producto',
            'almacen',
            'cantidad_disponible',
            'costo_unitario_promedio',
            'ubicacion_almacen',
            'stock_minimo',
            'stock_maximo',
            'lote',
            'fecha_vencimiento',
        ]
    
    def validate(self, data):
        request = self.context.get('request')
        if request and request.user and request.user.empresa:
            empresa = request.user.empresa
            
            producto = data.get('producto')
            if producto:
                if producto.empresa != empresa:
                    raise serializers.ValidationError(
                        {'producto': 'Este producto no pertenece a tu empresa'}
                    )
                if producto.tipo_producto not in ['RAW', 'SEMIFINISHED']:
                    raise serializers.ValidationError(
                        {'producto': 'Solo materias primas o productos semi-terminados permitidos'}
                    )
            
            almacen = data.get('almacen')
            if almacen and almacen.empresa != empresa:
                raise serializers.ValidationError(
                    {'almacen': 'Este almacén no pertenece a tu empresa'}
                )
        
        return data
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.empresa:
            validated_data['empresa'] = request.user.empresa
        return super().create(validated_data)


class InventarioProductosTerminadosSerializer(serializers.ModelSerializer):
    """Serializer para inventario de productos terminados"""
    
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)
    producto_unidad = serializers.CharField(source='producto.unidad_medida', read_only=True)
    almacen_nombre = serializers.CharField(source='almacen.nombre', read_only=True)
    cantidad_total = serializers.DecimalField(
        max_digits=12, decimal_places=4, read_only=True
    )
    valor_inventario = serializers.DecimalField(
        max_digits=15, decimal_places=4, read_only=True
    )
    valor_venta_potencial = serializers.DecimalField(
        max_digits=15, decimal_places=4, read_only=True
    )
    margen_utilidad = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )
    estado_stock = serializers.CharField(read_only=True)
    empresa = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = InventarioProductosTerminados
        fields = [
            'id',
            'empresa',
            'producto',
            'producto_nombre',
            'producto_sku',
            'producto_unidad',
            'almacen',
            'almacen_nombre',
            'cantidad_disponible',
            'cantidad_reservada',
            'cantidad_total',
            'costo_produccion_unitario',
            'precio_venta_sugerido',
            'valor_inventario',
            'valor_venta_potencial',
            'margen_utilidad',
            'ubicacion_almacen',
            'stock_minimo',
            'stock_maximo',
            'lote_produccion',
            'fecha_produccion',
            'fecha_vencimiento',
            'orden_produccion_id',
            'estado_stock',
            'ultima_actualizacion',
            'created_at',
        ]
        read_only_fields = [
            'empresa', 'cantidad_total', 'valor_inventario', 'valor_venta_potencial',
            'margen_utilidad', 'estado_stock', 'ultima_actualizacion', 'created_at'
        ]
    
    def validate(self, data):
        request = self.context.get('request')
        if request and request.user and request.user.empresa:
            empresa = request.user.empresa
            
            # Validar que el producto pertenezca a la empresa
            producto = data.get('producto')
            if producto and producto.empresa != empresa:
                raise serializers.ValidationError(
                    {'producto': 'Este producto no pertenece a tu empresa'}
                )
            
            # Validar que el producto sea producto terminado
            if producto and producto.tipo_producto != 'FINISHED':
                raise serializers.ValidationError(
                    {'producto': 'Solo se pueden agregar productos terminados a este inventario'}
                )
            
            # Validar que el almacén pertenezca a la empresa
            almacen = data.get('almacen')
            if almacen and almacen.empresa != empresa:
                raise serializers.ValidationError(
                    {'almacen': 'Este almacén no pertenece a tu empresa'}
                )
        
        return data
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.empresa:
            validated_data['empresa'] = request.user.empresa
        return super().create(validated_data)


class InventarioProductosTerminadosCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear/actualizar inventario de productos terminados"""
    
    class Meta:
        model = InventarioProductosTerminados
        fields = [
            'producto',
            'almacen',
            'cantidad_disponible',
            'costo_produccion_unitario',
            'precio_venta_sugerido',
            'ubicacion_almacen',
            'stock_minimo',
            'stock_maximo',
            'lote_produccion',
            'fecha_produccion',
            'fecha_vencimiento',
        ]
    
    def validate(self, data):
        request = self.context.get('request')
        if request and request.user and request.user.empresa:
            empresa = request.user.empresa
            
            producto = data.get('producto')
            if producto:
                if producto.empresa != empresa:
                    raise serializers.ValidationError(
                        {'producto': 'Este producto no pertenece a tu empresa'}
                    )
                if producto.tipo_producto != 'FINISHED':
                    raise serializers.ValidationError(
                        {'producto': 'Solo productos terminados permitidos'}
                    )
            
            almacen = data.get('almacen')
            if almacen and almacen.empresa != empresa:
                raise serializers.ValidationError(
                    {'almacen': 'Este almacén no pertenece a tu empresa'}
                )
        
        return data
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.empresa:
            validated_data['empresa'] = request.user.empresa
        return super().create(validated_data)


class EntradaCompraSerializer(serializers.Serializer):
    """Serializer para registrar entrada de compra a inventario de materias primas"""
    
    producto_id = serializers.IntegerField()
    almacen_id = serializers.IntegerField()
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=4)
    costo_unitario = serializers.DecimalField(max_digits=12, decimal_places=4)
    lote = serializers.CharField(max_length=100, required=False, allow_blank=True)
    fecha_vencimiento = serializers.DateField(required=False, allow_null=True)
    ubicacion = serializers.CharField(max_length=100, required=False, allow_blank=True)
    compra_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate(self, data):
        from .models import Producto, Almacen
        
        request = self.context.get('request')
        empresa = request.user.empresa if request else None
        
        try:
            producto = Producto.objects.get(id=data['producto_id'], empresa=empresa)
            if producto.tipo_producto not in ['RAW', 'SEMIFINISHED']:
                raise serializers.ValidationError(
                    {'producto_id': 'Solo se pueden registrar entradas de materias primas o semi-terminados'}
                )
            data['producto'] = producto
        except Producto.DoesNotExist:
            raise serializers.ValidationError(
                {'producto_id': 'Producto no encontrado'}
            )
        
        try:
            almacen = Almacen.objects.get(id=data['almacen_id'], empresa=empresa)
            data['almacen'] = almacen
        except Almacen.DoesNotExist:
            raise serializers.ValidationError(
                {'almacen_id': 'Almacén no encontrado'}
            )
        
        if data['cantidad'] <= 0:
            raise serializers.ValidationError(
                {'cantidad': 'La cantidad debe ser mayor a 0'}
            )
        
        if data['costo_unitario'] < 0:
            raise serializers.ValidationError(
                {'costo_unitario': 'El costo unitario no puede ser negativo'}
            )
        
        return data


class SalidaProduccionSerializer(serializers.Serializer):
    """Serializer para registrar salida de materias primas a producción"""
    
    producto_id = serializers.IntegerField()
    almacen_id = serializers.IntegerField()
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=4)
    orden_produccion_id = serializers.IntegerField()
    desde_reserva = serializers.BooleanField(default=True)
    
    def validate(self, data):
        from .models import Producto, Almacen, InventarioMateriasPrimas
        
        request = self.context.get('request')
        empresa = request.user.empresa if request else None
        
        try:
            producto = Producto.objects.get(id=data['producto_id'], empresa=empresa)
            data['producto'] = producto
        except Producto.DoesNotExist:
            raise serializers.ValidationError(
                {'producto_id': 'Producto no encontrado'}
            )
        
        try:
            almacen = Almacen.objects.get(id=data['almacen_id'], empresa=empresa)
            data['almacen'] = almacen
        except Almacen.DoesNotExist:
            raise serializers.ValidationError(
                {'almacen_id': 'Almacén no encontrado'}
            )
        
        # Verificar stock disponible
        try:
            inventario = InventarioMateriasPrimas.objects.get(
                empresa=empresa,
                producto=data['producto'],
                almacen=data['almacen']
            )
            
            if data['desde_reserva']:
                if inventario.cantidad_reservada < data['cantidad']:
                    raise serializers.ValidationError(
                        {'cantidad': f'Cantidad reservada insuficiente. Disponible: {inventario.cantidad_reservada}'}
                    )
            else:
                if inventario.cantidad_disponible < data['cantidad']:
                    raise serializers.ValidationError(
                        {'cantidad': f'Stock insuficiente. Disponible: {inventario.cantidad_disponible}'}
                    )
            
            data['inventario'] = inventario
            
        except InventarioMateriasPrimas.DoesNotExist:
            raise serializers.ValidationError(
                {'producto_id': 'No existe inventario para este producto en el almacén especificado'}
            )
        
        return data


class EntradaProduccionSerializer(serializers.Serializer):
    """Serializer para registrar entrada de productos terminados desde producción"""
    
    producto_id = serializers.IntegerField()
    almacen_id = serializers.IntegerField()
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=4)
    costo_produccion = serializers.DecimalField(max_digits=12, decimal_places=4)
    orden_produccion_id = serializers.IntegerField()
    lote = serializers.CharField(max_length=100, required=False, allow_blank=True)
    fecha_produccion = serializers.DateField(required=False, allow_null=True)
    fecha_vencimiento = serializers.DateField(required=False, allow_null=True)
    ubicacion = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    def validate(self, data):
        from .models import Producto, Almacen
        
        request = self.context.get('request')
        empresa = request.user.empresa if request else None
        
        try:
            producto = Producto.objects.get(id=data['producto_id'], empresa=empresa)
            if producto.tipo_producto != 'FINISHED':
                raise serializers.ValidationError(
                    {'producto_id': 'Solo se pueden registrar entradas de productos terminados'}
                )
            data['producto'] = producto
        except Producto.DoesNotExist:
            raise serializers.ValidationError(
                {'producto_id': 'Producto no encontrado'}
            )
        
        try:
            almacen = Almacen.objects.get(id=data['almacen_id'], empresa=empresa)
            data['almacen'] = almacen
        except Almacen.DoesNotExist:
            raise serializers.ValidationError(
                {'almacen_id': 'Almacén no encontrado'}
            )
        
        if data['cantidad'] <= 0:
            raise serializers.ValidationError(
                {'cantidad': 'La cantidad debe ser mayor a 0'}
            )
        
        return data


class SalidaVentaSerializer(serializers.Serializer):
    """Serializer para registrar salida de productos terminados por venta"""
    
    producto_id = serializers.IntegerField()
    almacen_id = serializers.IntegerField()
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=4)
    venta_id = serializers.IntegerField(required=False, allow_null=True)
    desde_reserva = serializers.BooleanField(default=False)
    
    def validate(self, data):
        from .models import Producto, Almacen, InventarioProductosTerminados
        
        request = self.context.get('request')
        empresa = request.user.empresa if request else None
        
        try:
            producto = Producto.objects.get(id=data['producto_id'], empresa=empresa)
            if producto.tipo_producto != 'FINISHED':
                raise serializers.ValidationError(
                    {'producto_id': 'Solo se pueden registrar salidas de productos terminados'}
                )
            data['producto'] = producto
        except Producto.DoesNotExist:
            raise serializers.ValidationError(
                {'producto_id': 'Producto no encontrado'}
            )
        
        try:
            almacen = Almacen.objects.get(id=data['almacen_id'], empresa=empresa)
            data['almacen'] = almacen
        except Almacen.DoesNotExist:
            raise serializers.ValidationError(
                {'almacen_id': 'Almacén no encontrado'}
            )
        
        # Verificar stock disponible
        try:
            inventario = InventarioProductosTerminados.objects.get(
                empresa=empresa,
                producto=data['producto'],
                almacen=data['almacen']
            )
            
            if data['desde_reserva']:
                if inventario.cantidad_reservada < data['cantidad']:
                    raise serializers.ValidationError(
                        {'cantidad': f'Cantidad reservada insuficiente. Disponible: {inventario.cantidad_reservada}'}
                    )
            else:
                if inventario.cantidad_disponible < data['cantidad']:
                    raise serializers.ValidationError(
                        {'cantidad': f'Stock insuficiente. Disponible: {inventario.cantidad_disponible}'}
                    )
            
            data['inventario'] = inventario
            
        except InventarioProductosTerminados.DoesNotExist:
            raise serializers.ValidationError(
                {'producto_id': 'No existe inventario para este producto en el almacén especificado'}
            )
        
        return data


class AlertaStockSerializer(serializers.Serializer):
    """Serializer para alertas de stock"""
    
    tipo = serializers.CharField()
    producto = serializers.CharField()
    almacen = serializers.CharField()
    cantidad_disponible = serializers.DecimalField(max_digits=12, decimal_places=4, required=False)
    stock_minimo = serializers.DecimalField(max_digits=12, decimal_places=4, required=False)
    fecha_vencimiento = serializers.DateField(required=False)
    mensaje = serializers.CharField()


class ResumenInventarioSeparadoSerializer(serializers.Serializer):
    """Serializer para resumen de inventarios separados"""
    
    # Materias Primas
    total_materias_primas = serializers.IntegerField()
    valor_total_materias_primas = serializers.DecimalField(max_digits=15, decimal_places=2)
    materias_primas_stock_bajo = serializers.IntegerField()
    materias_primas_por_vencer = serializers.IntegerField()
    
    # Productos Terminados
    total_productos_terminados = serializers.IntegerField()
    valor_total_productos_terminados = serializers.DecimalField(max_digits=15, decimal_places=2)
    productos_terminados_stock_bajo = serializers.IntegerField()
    valor_venta_potencial = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Alertas
    alertas = AlertaStockSerializer(many=True) 