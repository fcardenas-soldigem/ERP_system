from rest_framework import serializers
from .models import Venta, Cliente, Factura, OrdenVenta, DetalleVenta, ComprobantePago, PagoVenta
from apps.inventario.models.producto import Producto
from apps.inventario.models.stock import Stock
from django.db import transaction
from decimal import Decimal
from django.db import models
from django.utils import timezone
from .models import PagoVenta  # Asegurar que PagoVenta está importado

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ['id', 'nombre', 'documento', 'tipo_documento', 'direccion', 'telefono', 'email', 'activo', 'empresa']
        read_only_fields = ['empresa']
        extra_kwargs = {
            'direccion': {'required': False, 'allow_blank': True, 'allow_null': True},
            'telefono': {'required': False, 'allow_blank': True, 'allow_null': True},
            'email': {'required': False, 'allow_blank': True, 'allow_null': True},
        }

    def create(self, validated_data):
        # Asignar la empresa del usuario actual
        validated_data['empresa'] = self.context['request'].user.empresa
        return super().create(validated_data)

    def validate_documento(self, value):
        if not value.strip():
            raise serializers.ValidationError("El documento es requerido")
        if not value.isdigit():
            raise serializers.ValidationError("El documento debe contener solo números")
        if len(value) != 8 and len(value) != 11:
            raise serializers.ValidationError("El documento debe tener 8 dígitos (DNI) o 11 dígitos (RUC)")
        return value

    def validate_telefono(self, value):
        # Si se proporciona teléfono, validarlo
        if value and value.strip():
            if not value.isdigit():
                raise serializers.ValidationError("El teléfono debe contener solo números")
            if len(value) != 9:
                raise serializers.ValidationError("El teléfono debe tener 9 dígitos")
        return value

    def validate_nombre(self, value):
        if not value.strip():
            raise serializers.ValidationError("El nombre/razón social es requerido")
        return value

class ComprobantePagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComprobantePago
        fields = ['id', 'archivo', 'fecha_subida', 'tipo', 'numero', 'notas']
        read_only_fields = ['fecha_subida']

class DetalleVentaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)
    
    class Meta:
        model = DetalleVenta
        fields = ['venta', 'producto', 'producto_nombre', 'producto_sku',
                 'cantidad', 'precio_unitario']
        extra_kwargs = {
            'venta': {'required': False}
        }

    def validate(self, data):
        if data.get('cantidad', 0) <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor que 0")
        if data.get('precio_unitario', 0) <= 0:
            raise serializers.ValidationError("El precio unitario debe ser mayor que 0")
        return data

class VentaSerializer(serializers.ModelSerializer):
    cliente = ClienteSerializer(read_only=True)
    cliente_id = serializers.IntegerField(write_only=True, required=False)
    detalles = DetalleVentaSerializer(many=True, required=False)
    saldo_pendiente = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    dias_restantes = serializers.SerializerMethodField()
    estado_vencimiento = serializers.SerializerMethodField()
    comprobante = serializers.FileField(required=False, allow_null=True)
    comprobante_pago = ComprobantePagoSerializer(read_only=True)
    productos_stock_bajo = serializers.SerializerMethodField()
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    estado_display = serializers.SerializerMethodField()
    tipo_venta_display = serializers.SerializerMethodField()
    metodo_pago_display = serializers.SerializerMethodField()
    empresa = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = Venta
        fields = [
            'id', 'numero', 'cliente', 'cliente_id', 'fecha_emision',
            'fecha_vencimiento', 'estado', 'tipo_venta', 'metodo_pago',
            'igv_incluido', 'subtotal', 'igv', 'total', 'moneda', 'notas',
            'referencia', 'comprobante', 'detalles', 'saldo_pendiente',
            'dias_restantes', 'estado_vencimiento', 'comprobante_pago',
            'productos_stock_bajo', 'cliente_nombre', 'estado_display',
            'tipo_venta_display', 'metodo_pago_display', 'empresa'
        ]
        read_only_fields = ['id', 'numero', 'estado_display', 'tipo_venta_display', 'metodo_pago_display', 'empresa']

    ESTADO_MAP = {
        'borrador': 'Borrador',
        'pendiente': 'Pendiente',
        'pagado': 'Pagado',
        'anulado': 'Anulado'
    }

    TIPO_VENTA_MAP = {
        'contado': 'Contado',
        'credito_30': 'Crédito 30 días',
        'credito_60': 'Crédito 60 días'
    }

    METODO_PAGO_MAP = {
        'efectivo': 'Efectivo',
        'transferencia': 'Transferencia',
        'cheque': 'Cheque',
        'tarjeta': 'Tarjeta'
    }

    def get_estado_display(self, obj):
        return self.ESTADO_MAP.get(obj.estado, obj.estado)

    def get_tipo_venta_display(self, obj):
        return self.TIPO_VENTA_MAP.get(obj.tipo_venta, obj.tipo_venta)

    def get_metodo_pago_display(self, obj):
        return self.METODO_PAGO_MAP.get(obj.metodo_pago, obj.metodo_pago)

    def get_productos_stock_bajo(self, obj):
        productos_bajo_stock = []
        for detalle in obj.detalles.all():
            stock_total = detalle.producto.get_stock_total()
            if stock_total <= detalle.producto.stock_minimo:
                productos_bajo_stock.append({
                    'id': detalle.producto.id,
                    'nombre': detalle.producto.nombre,
                    'stock_actual': stock_total,
                    'stock_minimo': detalle.producto.stock_minimo
                })
        return productos_bajo_stock

    def get_dias_restantes(self, obj):
        if not obj.fecha_vencimiento:
            return None
        return (obj.fecha_vencimiento - timezone.now().date()).days

    def get_estado_vencimiento(self, obj):
        if not obj.fecha_vencimiento:
            return 'SIN FECHA DE VENCIMIENTO'
        dias_restantes = self.get_dias_restantes(obj)
        if dias_restantes < 0:
            return 'VENCIDO'
        elif dias_restantes == 0:
            return 'VENCE HOY'
        return f'{dias_restantes} DÍAS RESTANTES'

    def validate(self, data):
        print(f"DEBUG: Iniciando validación para data: {data}")
        print(f"DEBUG: initial_data: {self.initial_data}")
        print(f"DEBUG: request.user: {self.context['request'].user}")
        print(f"DEBUG: request.user.empresa: {self.context['request'].user.empresa}")
        
        if self.instance is None:  # Solo para creación
            # Validar cliente primero - buscar en data y initial_data
            cliente = data.get('cliente')
            cliente_id = data.get('cliente_id')
            
            print(f"DEBUG: Cliente recibido en data: {cliente}")
            print(f"DEBUG: Cliente_id recibido en data: {cliente_id}")
            print(f"DEBUG: Tipo de cliente: {type(cliente)}")
            print(f"DEBUG: Tipo de cliente_id: {type(cliente_id)}")
            
            # Si no viene en data, intentar obtenerlo de initial_data
            if not cliente and not cliente_id:
                cliente_from_initial = self.initial_data.get('cliente')
                cliente_id_from_initial = self.initial_data.get('cliente_id')
                
                print(f"DEBUG: Cliente desde initial_data: {cliente_from_initial}")
                print(f"DEBUG: Cliente_id desde initial_data: {cliente_id_from_initial}")
                
                # Usar el que esté disponible
                if cliente_from_initial:
                    cliente_id = cliente_from_initial
                elif cliente_id_from_initial:
                    cliente_id = cliente_id_from_initial
            
            # Si cliente_id es una lista, tomar el primer elemento
            if isinstance(cliente_id, list) and len(cliente_id) > 0:
                cliente_id = cliente_id[0]
                print(f"DEBUG: Cliente_id era una lista, tomando primer elemento: {cliente_id}")
            
            if cliente_id:
                try:
                    cliente_id = int(cliente_id)
                    cliente = Cliente.objects.get(id=cliente_id, empresa=self.context['request'].user.empresa)
                    data['cliente'] = cliente
                    print(f"DEBUG: Cliente encontrado y asignado: {cliente}")
                except (ValueError, Cliente.DoesNotExist) as e:
                    print(f"DEBUG: Error al obtener cliente: {e}")
                    raise serializers.ValidationError({
                        "cliente_id": ["Cliente no válido o no pertenece a su empresa"]
                    })
            
            if not cliente:
                print("DEBUG: Cliente no proporcionado")
                raise serializers.ValidationError({
                    "cliente_id": ["El cliente es requerido"]
                })

            print(f"DEBUG: Cliente empresa: {cliente.empresa_id}, Usuario empresa: {self.context['request'].user.empresa_id}")
            if cliente.empresa != self.context['request'].user.empresa:
                print("DEBUG: Cliente no pertenece a la empresa del usuario")
                raise serializers.ValidationError({
                    "cliente_id": ["El cliente no pertenece a su empresa"]
                })

            # Obtener y validar detalles
            detalles_data = self.initial_data.get('detalles', [])
            print(f"DEBUG: detalles_data recibidos: {detalles_data}")
            print(f"DEBUG: tipo de detalles_data: {type(detalles_data)}")
            
            if isinstance(detalles_data, str):
                try:
                    import json
                    detalles_data = json.loads(detalles_data)
                    print(f"DEBUG: detalles_data después de parse JSON: {detalles_data}")
                except json.JSONDecodeError as e:
                    print(f"DEBUG: Error al parsear JSON: {e}")
                    raise serializers.ValidationError({
                        "detalles": ["Formato de detalles inválido"]
                    })

            if not isinstance(detalles_data, list):
                print(f"DEBUG: detalles_data no es una lista: {type(detalles_data)}")
                raise serializers.ValidationError({
                    "detalles": ["Los detalles deben ser una lista"]
                })

            if not detalles_data:
                print("DEBUG: detalles_data está vacío")
                raise serializers.ValidationError({
                    "detalles": ["Debe incluir al menos un detalle en la venta"]
                })

            # Validar cada detalle
            for i, detalle in enumerate(detalles_data):
                print(f"DEBUG: Validando detalle {i}: {detalle}")
                
                if not isinstance(detalle, dict):
                    print(f"DEBUG: Detalle {i} no es un diccionario")
                    raise serializers.ValidationError({
                        "detalles": ["Cada detalle debe ser un objeto válido"]
                    })

                # Validar campos requeridos
                required_fields = ['producto', 'cantidad', 'precio_unitario']
                for field in required_fields:
                    if field not in detalle:
                        print(f"DEBUG: Falta campo {field} en detalle {i}")
                        raise serializers.ValidationError({
                            "detalles": [f"Falta el campo {field} en uno de los detalles"]
                        })

                try:
                    # Validar producto
                    producto_id = int(detalle['producto'])
                    print(f"DEBUG: Validando producto ID: {producto_id}")
                    
                    try:
                        producto = Producto.objects.get(id=producto_id)
                        print(f"DEBUG: Producto encontrado: {producto.nombre}, empresa: {producto.empresa_id}")
                        print(f"DEBUG: Empresa del usuario: {self.context['request'].user.empresa_id}")
                        
                        if producto.empresa != self.context['request'].user.empresa:
                            print(f"DEBUG: Producto no pertenece a la empresa del usuario")
                            raise serializers.ValidationError({
                                "detalles": [f"El producto {producto_id} no pertenece a su empresa"]
                            })
                    except Producto.DoesNotExist:
                        print(f"DEBUG: Producto {producto_id} no existe")
                        raise serializers.ValidationError({
                            "detalles": [f"El producto {producto_id} no existe"]
                        })

                    # Validar cantidad y precio
                    cantidad = float(detalle['cantidad'])
                    precio_unitario = float(detalle['precio_unitario'])
                    print(f"DEBUG: Cantidad: {cantidad}, Precio: {precio_unitario}")

                    if cantidad <= 0:
                        print(f"DEBUG: Cantidad inválida: {cantidad}")
                        raise serializers.ValidationError({
                            "detalles": ["La cantidad debe ser mayor que 0"]
                        })
                    if precio_unitario <= 0:
                        print(f"DEBUG: Precio inválido: {precio_unitario}")
                        raise serializers.ValidationError({
                            "detalles": ["El precio debe ser mayor que 0"]
                        })

                except (ValueError, TypeError) as e:
                    print(f"DEBUG: Error en valores numéricos: {e}")
                    raise serializers.ValidationError({
                        "detalles": [f"Error en los valores numéricos: {str(e)}"]
                    })

            # Validar tipo_venta y metodo_pago
            tipo_venta = data.get('tipo_venta')
            print(f"DEBUG: Tipo de venta: {tipo_venta}")
            
            if tipo_venta not in self.TIPO_VENTA_MAP:
                print(f"DEBUG: Tipo de venta inválido: {tipo_venta}")
                raise serializers.ValidationError({
                    "tipo_venta": ["Tipo de venta no válido"]
                })

            metodo_pago = data.get('metodo_pago')
            print(f"DEBUG: Método de pago: {metodo_pago}")
            
            if metodo_pago not in self.METODO_PAGO_MAP:
                print(f"DEBUG: Método de pago inválido: {metodo_pago}")
                raise serializers.ValidationError({
                    "metodo_pago": ["Método de pago no válido"]
                })

        print("DEBUG: Validación completada exitosamente")
        return data

    @transaction.atomic
    def create(self, validated_data):
        try:
            print(f"DEBUG CREATE: Iniciando creación de venta con validated_data: {validated_data}")
            
            # Forzar igv_incluido a booleano
            igv_incluido = validated_data.get('igv_incluido', False)
            if isinstance(igv_incluido, str):
                igv_incluido = igv_incluido.lower() in ['true', '1', 'yes', 'on', 'si', 'sí']
            validated_data['igv_incluido'] = bool(igv_incluido)
            print(f"DEBUG CREATE: igv_incluido procesado: {validated_data['igv_incluido']}")

            detalles_data = self.initial_data.get('detalles', [])
            if isinstance(detalles_data, str):
                import json
                detalles_data = json.loads(detalles_data)
            print(f"DEBUG CREATE: detalles_data: {detalles_data}")

            # Asignar la empresa del usuario actual
            validated_data['empresa'] = self.context['request'].user.empresa
            print(f"DEBUG CREATE: empresa asignada: {validated_data['empresa']}")

            # Remover cliente_id de validated_data ya que no es un campo del modelo
            cliente_id = validated_data.pop('cliente_id', None)
            print(f"DEBUG CREATE: cliente_id removido: {cliente_id}")

            # ✅ EXTRAER detalles de validated_data ANTES de crear la venta
            detalles_validated = validated_data.pop('detalles', [])
            print(f"DEBUG CREATE: detalles extraídos de validated_data: {len(detalles_validated)} items")

            # Crear la venta
            print(f"DEBUG CREATE: Creando venta con datos: {validated_data}")
            print(f"DEBUG CREATE: Datos de empresa: {validated_data['empresa']} (ID: {validated_data['empresa'].id})")
            
            # Verificar ventas existentes antes de crear
            ventas_existentes = Venta.objects.filter(empresa_id=validated_data['empresa'].id)
            print(f"DEBUG CREATE: Ventas existentes para empresa {validated_data['empresa'].id}: {list(ventas_existentes.values_list('numero', flat=True))}")
            
            venta = Venta.objects.create(**validated_data)
            print(f"DEBUG CREATE: Venta creada exitosamente: {venta.numero}")

            # Crear los detalles
            print(f"DEBUG CREATE: Creando {len(detalles_data)} detalles")
            for i, detalle_data in enumerate(detalles_data):
                print(f"DEBUG CREATE: Creando detalle {i+1}: {detalle_data}")
                DetalleVenta.objects.create(
                    venta=venta,
                    producto_id=detalle_data['producto'],
                    cantidad=detalle_data['cantidad'],
                    precio_unitario=detalle_data['precio_unitario']
                )
                print(f"DEBUG CREATE: Detalle {i+1} creado exitosamente")

            # Actualizar totales
            print(f"DEBUG CREATE: Actualizando totales de venta")
            venta.actualizar_totales()
            print(f"DEBUG CREATE: Totales actualizados - Total: {venta.total}")

            # Actualizar stock del inventario (productos entregados al cliente)
            print(f"DEBUG CREATE: Actualizando stock del inventario")
            venta.actualizar_stock()
            print(f"DEBUG CREATE: Stock actualizado correctamente")

            # Si es venta a crédito, establecer fecha de vencimiento
            if venta.tipo_venta.startswith('credito_'):
                dias = int(venta.tipo_venta.split('_')[1])
                venta.fecha_vencimiento = venta.fecha_emision + timezone.timedelta(days=dias)
                venta.save()  # Guardar fecha de vencimiento
                print(f"DEBUG CREATE: Fecha de vencimiento establecida: {venta.fecha_vencimiento}")

            print(f"DEBUG CREATE: Venta creada completamente: {venta.numero}")
            return venta

        except Exception as e:
            print(f"DEBUG CREATE ERROR: {str(e)}")
            print(f"DEBUG CREATE ERROR TYPE: {type(e)}")
            import traceback
            print(f"DEBUG CREATE TRACEBACK: {traceback.format_exc()}")
            raise serializers.ValidationError(str(e))

    @transaction.atomic
    def update(self, instance, validated_data):
        # Forzar igv_incluido a booleano
        igv_incluido = validated_data.get('igv_incluido', instance.igv_incluido)
        if isinstance(igv_incluido, str):
            igv_incluido = igv_incluido.lower() in ['true', '1', 'yes', 'on', 'si', 'sí']
        validated_data['igv_incluido'] = bool(igv_incluido)

        detalles_data = validated_data.pop('detalles', [])
        comprobante = validated_data.pop('comprobante', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        instance.detalles.all().delete()
        for detalle_data in detalles_data:
            DetalleVenta.objects.create(venta=instance, **detalle_data)
        
        if comprobante:
            if hasattr(instance, 'comprobante_pago'):
                instance.comprobante_pago.archivo = comprobante
                instance.comprobante_pago.save()
            else:
                ComprobantePago.objects.create(
                    venta=instance,
                    archivo=comprobante,
                    tipo='otro'
                )
        
        instance.actualizar_totales()
        instance.refresh_from_db()
        
        return instance

    @transaction.atomic
    def cancelar(self, instance):
        """
        Método para cancelar una venta
        """
        try:
            instance.cancelar_venta()
            return instance
        except Exception as e:
            raise serializers.ValidationError(str(e))

class FacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Factura
        fields = '__all__'

class OrdenVentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdenVenta
        fields = '__all__'
        depth = 1 

class PagoVentaSerializer(serializers.ModelSerializer):
    completar_pago = serializers.BooleanField(required=False, write_only=True)
    estado_venta = serializers.CharField(read_only=True)
    saldo_pendiente = serializers.DecimalField(read_only=True, max_digits=10, decimal_places=2)
    cliente_nombre = serializers.CharField(source='venta.cliente.nombre', read_only=True)
    venta_numero = serializers.CharField(source='venta.numero', read_only=True)
    venta_total = serializers.DecimalField(source='venta.total', read_only=True, max_digits=10, decimal_places=2)

    class Meta:
        model = PagoVenta
        fields = [
            'id', 'venta', 'venta_numero', 'cliente_nombre',
            'fecha', 'monto', 'metodo_pago',
            'referencia', 'comprobante', 'notas',
            'completar_pago', 'estado_venta', 'saldo_pendiente',
            'venta_total'
        ]
        read_only_fields = ['id', 'estado_venta', 'saldo_pendiente', 'venta_numero', 'cliente_nombre', 'venta_total']

    def validate(self, data):
        try:
            # Si es una actualización, usar la venta existente
            if self.instance:
                venta = self.instance.venta
            else:
                # Si es una creación, obtener la venta de los datos
                venta = data.get('venta')
                if not venta:
                    raise serializers.ValidationError({"venta": ["La venta es requerida"]})

            # Validar que el monto sea positivo
            monto = data.get('monto')
            if not monto or monto <= 0:
                raise serializers.ValidationError({"monto": ["El monto debe ser mayor que 0"]})

            # Validar el método de pago
            metodo_pago = data.get('metodo_pago')
            if not metodo_pago:
                raise serializers.ValidationError({"metodo_pago": ["El método de pago es requerido"]})
            if metodo_pago not in dict(PagoVenta.METODO_PAGO_CHOICES):
                raise serializers.ValidationError({"metodo_pago": ["Método de pago no válido"]})

            # No permitir crear pagos con método 'pendiente'
            if metodo_pago == 'pendiente':
                raise serializers.ValidationError({"metodo_pago": ["No se pueden crear pagos con método 'pendiente'. Use un método de pago real."]})
            
            # Calcular el saldo pendiente
            saldo_pendiente = venta.get_saldo_pendiente()

            # Si es una actualización, excluir el monto del pago actual
            if self.instance:
                saldo_pendiente += self.instance.monto

            # Validar que el monto no exceda el saldo pendiente
            if monto > saldo_pendiente:
                raise serializers.ValidationError({
                    "monto": [f"El monto del pago ({monto}) excede el saldo pendiente ({saldo_pendiente})"]
                })

            return data
        except Exception as e:
            if hasattr(e, 'detail'):
                raise e
            raise serializers.ValidationError({"non_field_errors": [str(e)]})

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['estado_venta'] = instance.venta.estado
        data['saldo_pendiente'] = float(instance.venta.get_saldo_pendiente())
        return data 