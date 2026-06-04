from rest_framework import serializers
from .models import (
    Compra,
    CompraDetalle,
    Proveedor,
    OrdenCompra,
    OrdenCompraDetalle,
    RecepcionCompra,
    PagoCompra,
    CompraRecurrente,
    ComprobantePago
)
from apps.inventario.models.producto import Producto
from apps.inventario.models.almacen import Almacen
from django.db import transaction
from decimal import Decimal
from datetime import timedelta

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'sku', 'descripcion', 'precio_venta',
            'precio_compra', 'stock_minimo', 'stock_maximo',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class AlmacenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Almacen
        fields = [
            'id', 'nombre', 'direccion', 'telefono',
            'encargado', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = ['id', 'razon_social', 'ruc', 'direccion', 'telefono', 'email', 'activo']

    def validate_ruc(self, value):
        if len(value) != 11:
            raise serializers.ValidationError("El RUC debe tener 11 dígitos")
        return value

    def validate_telefono(self, value):
        if value and len(value) < 7:  # Validación más flexible
            raise serializers.ValidationError("El teléfono debe tener al menos 7 dígitos")
        return value

    def validate_email(self, value):
        if value and not value:
            raise serializers.ValidationError("Ingrese un email válido")
        return value

class CompraDetalleSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)

    class Meta:
        model = CompraDetalle
        fields = [
            'id', 'compra', 'producto', 'producto_nombre', 'producto_sku',
            'cantidad', 'precio_unitario', 'subtotal', 'igv', 'total',
            'notas', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'subtotal', 'igv', 'total', 'created_at', 'updated_at']

class ComprobantePagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComprobantePago
        fields = ['id', 'archivo', 'fecha_subida', 'tipo', 'numero', 'notas']
        read_only_fields = ['fecha_subida']

class CompraSerializer(serializers.ModelSerializer):
    # comprobante = serializers.FileField(write_only=True, required=False)  # Comentamos esta línea temporalmente
    comprobante_pago = ComprobantePagoSerializer(read_only=True)
    detalles = CompraDetalleSerializer(many=True, required=False)
    proveedor_nombre = serializers.CharField(source='proveedor.razon_social', read_only=True)
    almacen_nombre = serializers.CharField(source='almacen.nombre', read_only=True)
    saldo_pendiente = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True,
        source='get_saldo_pendiente'
    )
    estado_display = serializers.SerializerMethodField()
    metodo_pago_display = serializers.SerializerMethodField()
    tipo_compra_display = serializers.SerializerMethodField()
    empresa = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = Compra
        fields = [
            'id', 'empresa', 'numero', 'proveedor', 'proveedor_nombre',
            'almacen', 'almacen_nombre', 'fecha_emision', 'fecha_vencimiento',
            'tipo_compra', 'tipo_compra_display', 'estado', 'estado_display',
            'metodo_pago', 'metodo_pago_display', 'igv_incluido',
            'subtotal', 'igv', 'total', 'moneda', 'saldo_pendiente', 'detalles',
            'created_at', 'updated_at', 'comprobante_pago'
        ]
        read_only_fields = ['id', 'numero', 'subtotal', 'igv', 'total', 'created_at', 'updated_at']

    def get_estado_display(self, obj):
        return dict(Compra.ESTADO_CHOICES).get(obj.estado, obj.estado)

    def get_metodo_pago_display(self, obj):
        return dict(Compra.METODO_PAGO_CHOICES).get(obj.metodo_pago, obj.metodo_pago)

    def get_tipo_compra_display(self, obj):
        return dict(Compra.TIPO_COMPRA_CHOICES).get(obj.tipo_compra, obj.tipo_compra)

    def validate(self, data):
        # Validar que el proveedor pertenezca a la empresa
        if 'proveedor' in data:
            proveedor = data['proveedor']
            empresa = self.context['request'].user.empresa
            if proveedor.empresa != empresa:
                raise serializers.ValidationError({
                    'proveedor': 'El proveedor no pertenece a la empresa'
                })

        # Validar que el almacén pertenezca a la empresa
        if 'almacen' in data:
            almacen = data['almacen']
            empresa = self.context['request'].user.empresa
            if almacen.empresa != empresa:
                raise serializers.ValidationError({
                    'almacen': 'El almacén no pertenece a la empresa'
                })

        # Validar fecha de vencimiento según tipo de compra
        if 'tipo_compra' in data:
            tipo_compra = data['tipo_compra']
            fecha_emision = data.get('fecha_emision')
            if tipo_compra in ['credito_30', 'credito_60'] and fecha_emision:
                dias = 30 if tipo_compra == 'credito_30' else 60
                data['fecha_vencimiento'] = fecha_emision + timedelta(days=dias)

        return data

    @transaction.atomic
    def create(self, validated_data):
        
        detalles_data = validated_data.pop('detalles', [])
        # comprobante = validated_data.pop('comprobante', None)
        
        # Asignar la empresa del usuario autenticado
        validated_data['empresa'] = self.context['request'].user.empresa
        
        # Crear la compra
        compra = Compra.objects.create(**validated_data)
        
        # Crear los detalles directamente sin usar el serializer
        for detalle_data in detalles_data:
            detalle_data['compra'] = compra  # Asignar la compra creada
            CompraDetalle.objects.create(**detalle_data)
        
        
        # Actualizar totales
        compra.actualizar_totales()
        
        # Actualizar stock del inventario (mercancía recibida)
        # Solo para compras pagadas (al contado) o que no estén en estado borrador
        if compra.estado in ['pagada', 'pendiente']:
            compra.actualizar_stock()
        
        # Si hay comprobante, crear el ComprobantePago
        # if comprobante:
        #     ComprobantePago.objects.create(
        #         compra=compra,
        #         archivo=comprobante,
        #         tipo='factura'  # Por defecto
        #     )
        
        return compra

    @transaction.atomic
    def update(self, instance, validated_data):
        detalles_data = validated_data.pop('detalles', [])
        # comprobante = validated_data.pop('comprobante', None)
        
        # Actualizar la compra
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Actualizar o crear detalles
        if detalles_data:
            instance.detalles.all().delete()
            for detalle_data in detalles_data:
                CompraDetalle.objects.create(compra=instance, **detalle_data)
            instance.actualizar_totales()
        
        # Actualizar comprobante si se proporciona uno nuevo
        # if comprobante:
        #     if hasattr(instance, 'comprobante_pago'):
        #         instance.comprobante_pago.delete()
        #     ComprobantePago.objects.create(
        #         compra=instance,
        #         archivo=comprobante,
        #         tipo='factura'  # Por defecto
        #     )
        
        return instance

class PagoCompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = PagoCompra
        fields = ['id', 'compra', 'fecha', 'monto', 'moneda', 'metodo_pago',
                 'referencia', 'comprobante', 'notas']
        read_only_fields = ['id']
    
    def validate(self, data):
        compra = data.get('compra')
        monto = data.get('monto')
        moneda_pago = data.get('moneda', 'PEN')
        
        if compra and monto:
            # Obtener tipo de cambio para conversiones
            from apps.core.services.documento_service import DocumentoService
            try:
                doc_service = DocumentoService()
                tipo_cambio_data = doc_service.obtener_tipo_cambio_venta()
                tipo_cambio = float(tipo_cambio_data.get('venta', 3.8)) if tipo_cambio_data else 3.8
            except:
                tipo_cambio = 3.8
            
            # Convertir monto a la moneda de la compra para validación
            monto_convertido = monto
            if moneda_pago != compra.moneda:
                if compra.moneda == 'USD' and moneda_pago == 'PEN':
                    # Convertir PEN a USD
                    monto_convertido = monto / tipo_cambio
                elif compra.moneda == 'PEN' and moneda_pago == 'USD':
                    # Convertir USD a PEN
                    monto_convertido = monto * tipo_cambio
            
            # Validar que no exceda el saldo pendiente
            saldo_pendiente = compra.get_saldo_pendiente()
            
            # Si es una actualización, excluir el monto del pago actual
            if self.instance:
                saldo_pendiente += self.instance.monto
            
            if monto_convertido > saldo_pendiente:
                raise serializers.ValidationError({
                    "monto": [f"El monto del pago ({monto_convertido:.2f} {compra.moneda}) excede el saldo pendiente ({saldo_pendiente:.2f} {compra.moneda})"]
                })
        
        return data

class OrdenCompraDetalleSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_sku    = serializers.CharField(source='producto.sku',    read_only=True)
    unidad_medida   = serializers.CharField(source='producto.unidad_medida', read_only=True)
    importe         = serializers.SerializerMethodField()

    class Meta:
        model  = OrdenCompraDetalle
        fields = ['id', 'producto', 'producto_nombre', 'producto_sku',
                  'unidad_medida', 'cantidad', 'precio_unitario', 'importe']

    def get_importe(self, obj):
        return float(obj.cantidad) * float(obj.precio_unitario)


class OrdenCompraSerializer(serializers.ModelSerializer):
    detalles = OrdenCompraDetalleSerializer(many=True, required=False)
    proveedor_info = serializers.SerializerMethodField()

    class Meta:
        model = OrdenCompra
        fields = [
            'id', 'numero', 'empresa', 'proveedor', 'proveedor_nombre',
            'fecha_emision', 'fecha_creacion', 'fecha_entrega',
            'subtotal', 'igv', 'total', 'estado', 'notas', 'detalles',
            'proveedor_info',
        ]
        read_only_fields = ['id', 'numero', 'empresa', 'fecha_creacion']

    def get_proveedor_info(self, obj):
        p = obj.proveedor
        if p is None and obj.proveedor_nombre:
            p = Proveedor.objects.filter(
                empresa=obj.empresa,
                razon_social__iexact=obj.proveedor_nombre,
            ).first()
        if p:
            return {'ruc': p.ruc, 'direccion': p.direccion,
                    'email': p.email, 'telefono': p.telefono}
        return None

    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles', [])
        orden = OrdenCompra.objects.create(**validated_data)
        for d in detalles_data:
            OrdenCompraDetalle.objects.create(orden=orden, **d)
        return orden

    def update(self, instance, validated_data):
        detalles_data = validated_data.pop('detalles', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if detalles_data is not None:
            instance.detalles.all().delete()
            for d in detalles_data:
                OrdenCompraDetalle.objects.create(orden=instance, **d)
        return instance

class RecepcionCompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecepcionCompra
        fields = ['id', 'orden_compra', 'fecha_recepcion', 'recibido_por',
                 'notas', 'fecha_registro', 'fecha_actualizacion']
        read_only_fields = ['id', 'fecha_registro', 'fecha_actualizacion']

class CompraRecurrenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompraRecurrente
        fields = ['id', 'empresa', 'proveedor_nombre', 'concepto', 'monto',
                 'frecuencia', 'proximo_pago', 'activo', 'notas']

