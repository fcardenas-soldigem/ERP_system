from rest_framework import serializers
from .models import Almacen, Categoria, Producto, Stock, AjusteInventario, MovimientoInventario
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

    class Meta:
        model = Producto
        fields = [
            'id', 'sku', 'nombre', 'descripcion',
            'stock_total', 'stock_minimo', 'stock_maximo',
            'categoria', 'categoria_nombre', 'almacen',
            'almacen_nombre', 'is_active', 'precio_compra',
            'precio_venta', 'moneda', 'margen', 'stocks_por_almacen',
            'stock', 'alerta_stock', 'empresa'
        ]
        read_only_fields = ['empresa', 'margen', 'stock_total', 'alerta_stock']

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
        request = self.context.get('request')
        stock_inicial = validated_data.pop('stock', 0)
        almacen_id = validated_data.get('almacen')
        
        if request and request.user and request.user.empresa:
            validated_data['empresa'] = request.user.empresa
        
        # Crear el producto primero
        print(f"[DEBUG] validated_data antes de crear producto: {validated_data}")
        producto = Producto.objects.create(**validated_data)
        print(f"[DEBUG] Producto creado: id={producto.id}, sku={producto.sku}, almacen={producto.almacen}, empresa={producto.empresa}")
        
        # Obtener el almacén asociado
        almacen = producto.almacen
        
        # Crear o actualizar el registro de stock inicial si se proporcionó y hay almacén
        if stock_inicial > 0 and almacen:
            stock_obj, created = Stock.objects.get_or_create(
                producto=producto,
                almacen=almacen,
                empresa=producto.empresa,
                defaults={'cantidad': 0}
            )
            stock_obj.cantidad += stock_inicial
            stock_obj.save()
            print(f"[DEBUG] {'Creado' if created else 'Actualizado'} stock: producto={producto.sku}, almacen={almacen.nombre}, cantidad={stock_obj.cantidad}, empresa={producto.empresa}")
        else:
            print(f"[DEBUG] No se creó/actualizó stock inicial para producto={producto.sku} (stock_inicial={stock_inicial}, almacen={almacen})")
        
        # Mostrar todos los stocks del producto
        stocks = Stock.objects.filter(producto=producto)
        print(f"[DEBUG] Stocks creados/actualizados para producto {producto.sku}: {[{'almacen': s.almacen.nombre, 'cantidad': s.cantidad, 'empresa': s.empresa.nombre if s.empresa else None} for s in stocks]}")
        
        return producto

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.empresa:
            validated_data['empresa'] = request.user.empresa
        return super().update(instance, validated_data)

    def validate(self, data):
        request = self.context.get('request')
        if request and request.user and request.user.empresa:
            # Validar que la categoría pertenezca a la empresa del usuario
            if 'categoria' in data:
                categoria = data['categoria']
                if categoria.empresa != request.user.empresa:
                    raise serializers.ValidationError(
                        {'categoria': 'Esta categoría no pertenece a tu empresa'}
                    )

            # Validar que el almacén pertenezca a la empresa del usuario
            if 'almacen' in data:
                almacen = data['almacen']
                if almacen.empresa != request.user.empresa:
                    raise serializers.ValidationError(
                        {'almacen': 'Este almacén no pertenece a tu empresa'}
                    )

        if 'stock_minimo' in data and 'stock_maximo' in data:
            if data['stock_minimo'] > data['stock_maximo']:
                raise serializers.ValidationError(
                    'El stock mínimo no puede ser mayor al stock máximo'
                )
        
        if 'precio_compra' in data and 'precio_venta' in data:
            if data['precio_venta'] < data['precio_compra']:
                raise serializers.ValidationError(
                    'El precio de venta no puede ser menor al precio de compra'
                )
        
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