import logging
"""
Servicio de negocio para el módulo de producción.
Contiene toda la lógica de negocio para gestionar órdenes de producción.
Integrado con inventarios separados de materias primas y productos terminados.
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from apps.produccion.models import (
    RecetaProducto, RecetaDetalle, OrdenProduccion, ConsumoReal,
    ProductionCost, ProductionWaste, ProductionOutput, HistorialOrdenProduccion
)
from apps.inventario.models import Stock, MovimientoInventario, Producto, Almacen
from apps.inventario.models.inventario_materias_primas import InventarioMateriasPrimas
from apps.inventario.models.inventario_productos_terminados import InventarioProductosTerminados
logger = logging.getLogger(__name__)


class ProduccionService:
    """Servicio para gestionar órdenes de producción"""
    
    @staticmethod
    @transaction.atomic
    def crear_orden_produccion(
        empresa,
        receta_id,
        cantidad,
        fecha_programada,
        almacen_insumos_id,
        almacen_destino_id,
        responsable=None,
        created_by=None,
        observaciones=""
    ):
        """
        Crea una nueva orden de producción.
        
        Args:
            empresa: Instancia de Empresa
            receta_id: ID de la receta a usar
            cantidad: Cantidad a producir
            fecha_programada: Fecha programada de producción
            almacen_insumos_id: ID del almacén de donde se sacan insumos
            almacen_destino_id: ID del almacén destino del producto terminado
            responsable: Usuario responsable (opcional)
            created_by: Usuario que crea la orden
            observaciones: Observaciones (opcional)
            
        Returns:
            OrdenProduccion: La orden creada
            
        Raises:
            ValidationError: Si hay errores de validación
        """
        # Validar receta
        try:
            receta = RecetaProducto.objects.select_related('producto_terminado').get(
                id=receta_id,
                empresa=empresa,
                is_active=True
            )
        except RecetaProducto.DoesNotExist:
            raise ValidationError('Receta no encontrada o inactiva')
        
        # Validar almacenes
        try:
            almacen_insumos = Almacen.objects.get(id=almacen_insumos_id, empresa=empresa)
            almacen_destino = Almacen.objects.get(id=almacen_destino_id, empresa=empresa)
        except Almacen.DoesNotExist:
            raise ValidationError('Almacén no encontrado o no pertenece a la empresa')
        
        # Validar cantidad
        if cantidad <= 0:
            raise ValidationError('La cantidad debe ser mayor a 0')
        
        # Calcular factor de multiplicación (si se pide más de lo que produce la receta)
        factor = cantidad / receta.cantidad_producida
        
        # Validar stock disponible de insumos
        detalles = receta.detalles.select_related('insumo').all()
        insumos_faltantes = []
        
        for detalle in detalles:
            cantidad_necesaria = detalle.cantidad * factor
            
            # Obtener stock disponible en el almacén de insumos
            try:
                stock = Stock.objects.get(
                    producto=detalle.insumo,
                    almacen=almacen_insumos,
                    empresa=empresa
                )
                stock_disponible = stock.cantidad
            except Stock.DoesNotExist:
                stock_disponible = 0
            
            if stock_disponible < cantidad_necesaria:
                insumos_faltantes.append({
                    'insumo': detalle.insumo.nombre,
                    'sku': detalle.insumo.sku,
                    'necesario': cantidad_necesaria,
                    'disponible': stock_disponible,
                    'faltante': cantidad_necesaria - stock_disponible
                })
        
        if insumos_faltantes:
            mensaje = 'Stock insuficiente para los siguientes insumos:\n'
            for item in insumos_faltantes:
                mensaje += f"- {item['insumo']} (SKU: {item['sku']}): "
                mensaje += f"Necesario: {item['necesario']}, "
                mensaje += f"Disponible: {item['disponible']}, "
                mensaje += f"Faltante: {item['faltante']}\n"
            raise ValidationError(mensaje)
        
        # Crear la orden de producción
        orden = OrdenProduccion.objects.create(
            empresa=empresa,
            receta=receta,
            cantidad_planificada=cantidad,
            fecha_programada=fecha_programada,
            almacen_insumos=almacen_insumos,
            almacen_destino=almacen_destino,
            estado='pendiente',
            responsable=responsable,
            created_by=created_by,
            observaciones=observaciones
        )
        
        # Crear registros de ConsumoReal con cantidades teóricas
        for detalle in detalles:
            cantidad_teorica = detalle.cantidad * factor
            
            ConsumoReal.objects.create(
                orden_produccion=orden,
                insumo=detalle.insumo,
                cantidad_teorica=cantidad_teorica,
                cantidad_real=0,  # Se actualizará durante la ejecución
                merma=0,
                costo_unitario=detalle.insumo.precio_compra
            )
        
        # Registrar evento en historial
        HistorialOrdenProduccion.registrar_evento(
            orden=orden,
            tipo_evento='creacion',
            descripcion=f'Orden creada para producir {cantidad} unidades de {receta.producto_terminado.nombre}',
            usuario=created_by,
            datos_adicionales={
                'cantidad_planificada': float(cantidad),
                'receta': receta.nombre,
                'producto': receta.producto_terminado.nombre
            }
        )
        
        return orden
    
    @staticmethod
    @transaction.atomic
    def iniciar_orden(orden_id, usuario=None):
        """
        Inicia una orden de producción (cambia estado a En Proceso).
        DESCUENTA AUTOMÁTICAMENTE el stock de materias primas al iniciar.
        
        Args:
            orden_id: ID de la orden a iniciar
            usuario: Usuario que inicia la orden
            
        Returns:
            OrdenProduccion: La orden actualizada
            
        Raises:
            ValidationError: Si hay errores de validación
        """
        try:
            orden = OrdenProduccion.objects.select_related(
                'receta', 'almacen_insumos', 'empresa'
            ).get(id=orden_id)
        except OrdenProduccion.DoesNotExist:
            raise ValidationError('Orden de producción no encontrada')
        
        # Validar estado
        if orden.estado != 'pendiente':
            raise ValidationError(f'No se puede iniciar una orden en estado: {orden.get_estado_display()}')
        
        # Re-validar stock disponible y preparar descuentos
        consumos = orden.consumos.select_related('insumo').all()
        insumos_faltantes = []
        stocks_a_descontar = []
        
        for consumo in consumos:
            try:
                stock = Stock.objects.get(
                    producto=consumo.insumo,
                    almacen=orden.almacen_insumos,
                    empresa=orden.empresa
                )
                stock_disponible = stock.cantidad
            except Stock.DoesNotExist:
                stock_disponible = Decimal('0')
                stock = None
            
            if stock_disponible < consumo.cantidad_teorica:
                insumos_faltantes.append({
                    'insumo': consumo.insumo.nombre,
                    'sku': consumo.insumo.sku,
                    'necesario': consumo.cantidad_teorica,
                    'disponible': stock_disponible,
                    'faltante': consumo.cantidad_teorica - stock_disponible
                })
            else:
                # Guardar referencia para descontar después de validar todos
                stocks_a_descontar.append({
                    'stock': stock,
                    'consumo': consumo,
                    'cantidad': consumo.cantidad_teorica
                })
        
        if insumos_faltantes:
            mensaje = 'Stock insuficiente para iniciar la producción:\n'
            for item in insumos_faltantes:
                mensaje += f"- {item['insumo']} (SKU: {item['sku']}): "
                mensaje += f"Necesario: {item['necesario']}, "
                mensaje += f"Disponible: {item['disponible']}, "
                mensaje += f"Faltante: {item['faltante']}\n"
            raise ValidationError(mensaje)
        
        # DESCONTAR STOCK DE MATERIAS PRIMAS (de ambos sistemas)
        for item in stocks_a_descontar:
            stock = item['stock']
            consumo = item['consumo']
            cantidad_a_descontar = item['cantidad']
            insumo = consumo.insumo
            # Asegurar que costo_unitario sea Decimal
            costo_unitario = Decimal(str(consumo.costo_unitario or insumo.precio_compra or 0))
            
            # 1. Descontar del modelo Stock (legacy)
            stock.cantidad -= cantidad_a_descontar
            stock.save()
            
            # 2. Descontar del modelo InventarioMateriasPrimas (si existe)
            if insumo.tipo_producto in ['RAW', 'SEMIFINISHED']:
                try:
                    inv_mp = InventarioMateriasPrimas.objects.select_for_update().filter(
                        empresa=orden.empresa,
                        producto=insumo,
                        almacen=orden.almacen_insumos
                    ).first()
                    
                    if inv_mp:
                        # Descontar lo que se pueda (mínimo entre lo solicitado y lo disponible)
                        cantidad_real_a_descontar = min(cantidad_a_descontar, inv_mp.cantidad_disponible)
                        if cantidad_real_a_descontar > 0:
                            inv_mp.cantidad_disponible -= cantidad_real_a_descontar
                            inv_mp.save()
                            # Usar el costo del inventario de materias primas
                            if inv_mp.costo_unitario_promedio:
                                costo_unitario = Decimal(str(inv_mp.costo_unitario_promedio))
                            logger.info(f"Descontado de InventarioMP: {insumo.nombre}, cantidad: {cantidad_real_a_descontar}")
                        else:
                            logger.info(f"InventarioMP sin stock para {insumo.nombre}")
                    else:
                        logger.info(f"No existe registro en InventarioMP para {insumo.nombre}")
                except Exception as e:
                    logger.info(f"Error al descontar de InventarioMP {insumo.nombre}: {str(e)}")
            
            # 3. Actualizar consumo con cantidad real = cantidad teórica (inicial)
            consumo.cantidad_real = cantidad_a_descontar
            consumo.costo_unitario = costo_unitario
            consumo.save()
            
            # 4. Registrar movimiento de inventario (salida)
            MovimientoInventario.objects.create(
                empresa=orden.empresa,
                producto=insumo,
                almacen=orden.almacen_insumos,
                fecha=timezone.now(),
                tipo_movimiento='salida_produccion',
                tipo_documento='orden_produccion',
                tipo_inventario='materia_prima' if insumo.tipo_producto in ['RAW', 'SEMIFINISHED'] else 'general',
                numero_documento=str(orden.numero),
                cantidad_salida=cantidad_a_descontar,
                costo_unitario=costo_unitario,
                costo_total_salida=cantidad_a_descontar * costo_unitario,
                cantidad_saldo=stock.cantidad,
                orden_produccion_id=orden.id,
                observaciones=f'Consumo inicial para orden de producción {orden.numero}',
                created_by=usuario.username if usuario else ''
            )
            
            # 5. Actualizar stock total del producto
            insumo.actualizar_stock_total()
            
            logger.info(f"Descontado de Stock: {insumo.nombre}, cantidad: {cantidad_a_descontar}, stock restante: {stock.cantidad}")
        
        # Cambiar estado e iniciar
        orden.estado = 'en_proceso'
        orden.fecha_inicio = timezone.now()
        if usuario and not orden.responsable:
            orden.responsable = usuario
        orden.save()
        
        # Registrar evento en historial
        materiales_consumidos = len(stocks_a_descontar)
        HistorialOrdenProduccion.registrar_evento(
            orden=orden,
            tipo_evento='inicio',
            descripcion=f'Producción iniciada. Se descontaron {materiales_consumidos} materiales del inventario.',
            usuario=usuario,
            datos_adicionales={
                'materiales_descontados': materiales_consumidos
            }
        )
        
        return orden
    
    @staticmethod
    @transaction.atomic
    def registrar_consumo_real(orden_id, insumo_id, cantidad_real, merma=0, notas=""):
        """
        Registra el consumo real de un insumo durante la producción.
        
        Args:
            orden_id: ID de la orden de producción
            insumo_id: ID del insumo consumido
            cantidad_real: Cantidad real consumida
            merma: Cantidad de merma/desperdicio
            notas: Notas adicionales
            
        Returns:
            ConsumoReal: El registro actualizado
            
        Raises:
            ValidationError: Si hay errores de validación
        """
        try:
            consumo = ConsumoReal.objects.select_related(
                'orden_produccion', 'insumo'
            ).get(
                orden_produccion_id=orden_id,
                insumo_id=insumo_id
            )
        except ConsumoReal.DoesNotExist:
            raise ValidationError('Consumo no encontrado para esta orden e insumo')
        
        # Validar estado de la orden
        if consumo.orden_produccion.estado not in ['en_proceso', 'pendiente']:
            raise ValidationError(
                f'No se puede registrar consumo en una orden {consumo.orden_produccion.get_estado_display()}'
            )
        
        # Validar cantidades
        if cantidad_real < 0:
            raise ValidationError('La cantidad real no puede ser negativa')
        
        if merma < 0:
            raise ValidationError('La merma no puede ser negativa')
        
        # Actualizar consumo
        consumo.cantidad_real = cantidad_real
        consumo.merma = merma
        if notas:
            consumo.notas = notas
        consumo.save()
        
        return consumo
    
    @staticmethod
    @transaction.atomic
    def finalizar_orden(
        orden_id,
        cantidad_producida,
        costo_mano_obra_real=0,
        costo_indirecto_real=0,
        observaciones=""
    ):
        """
        Finaliza una orden de producción.
        - Descuenta insumos del almacén de insumos (tanto Stock como InventarioMateriasPrimas)
        - Ingresa productos terminados al almacén destino (Stock e InventarioProductosTerminados)
        - Calcula costo unitario real
        - Actualiza precio_compra del producto terminado
        - Registra movimientos de inventario con trazabilidad completa
        
        Args:
            orden_id: ID de la orden a finalizar
            cantidad_producida: Cantidad realmente producida
            costo_mano_obra_real: Costo real de mano de obra
            costo_indirecto_real: Costo real indirecto (CIF)
            observaciones: Observaciones finales
            
        Returns:
            OrdenProduccion: La orden finalizada
            
        Raises:
            ValidationError: Si hay errores de validación
        """
        try:
            orden = OrdenProduccion.objects.select_related(
                'receta__producto_terminado',
                'almacen_insumos',
                'almacen_destino',
                'empresa'
            ).prefetch_related('consumos__insumo').get(id=orden_id)
        except OrdenProduccion.DoesNotExist:
            raise ValidationError('Orden de producción no encontrada')
        
        # Validar estado
        if orden.estado != 'en_proceso':
            raise ValidationError(f'Solo se pueden finalizar órdenes en proceso. Estado actual: {orden.get_estado_display()}')
        
        # Validar cantidad producida
        if cantidad_producida <= 0:
            raise ValidationError('La cantidad producida debe ser mayor a 0')
        
        # Variables para calcular costo
        costo_insumos = Decimal('0')
        
        # 1. Calcular costo de insumos (ya fueron descontados al iniciar la producción)
        for consumo in orden.consumos.all():
            if consumo.cantidad_real > 0:
                costo_unitario_consumo = consumo.costo_unitario or consumo.insumo.precio_compra
                costo_insumos += consumo.cantidad_real * costo_unitario_consumo
        
        # 2. Calcular costo unitario real
        costo_total = costo_insumos + Decimal(str(costo_mano_obra_real)) + Decimal(str(costo_indirecto_real))
        costo_unitario_real = costo_total / Decimal(str(cantidad_producida))
        
        # 3. Ingresar productos terminados al almacén destino
        producto_terminado = orden.receta.producto_terminado
        
        # A. Actualizar Stock legacy
        try:
            stock_destino = Stock.objects.get(
                producto=producto_terminado,
                almacen=orden.almacen_destino,
                empresa=orden.empresa
            )
            stock_destino.cantidad += cantidad_producida
            stock_destino.save()
        except Stock.DoesNotExist:
            # Crear stock si no existe
            stock_destino = Stock.objects.create(
                empresa=orden.empresa,
                producto=producto_terminado,
                almacen=orden.almacen_destino,
                cantidad=cantidad_producida
            )
        
        # B. Actualizar InventarioProductosTerminados
        if producto_terminado.tipo_producto == 'FINISHED':
            try:
                # Generar número de lote basado en orden
                lote_produccion = f"OP-{orden.numero}"
                
                inventario_pt = InventarioProductosTerminados.registrar_entrada_produccion(
                    empresa=orden.empresa,
                    producto=producto_terminado,
                    almacen=orden.almacen_destino,
                    cantidad=cantidad_producida,
                    costo_produccion=costo_unitario_real,
                    lote=lote_produccion,
                    orden_produccion_id=orden.id,
                    fecha_produccion=timezone.now().date(),
                    fecha_vencimiento=None,  # Se podría calcular basado en vida útil del producto
                    ubicacion=''
                )
                
                logger.info(f"Entrada en InventarioPT: {producto_terminado.nombre}, cantidad: {cantidad_producida}, costo: {costo_unitario_real}")
                
            except Exception as e:
                logger.info(f"Error al registrar en InventarioPT: {str(e)}")
                # No fallar, ya se actualizó el stock legacy
        
        # C. Registrar movimiento de inventario (entrada)
        MovimientoInventario.objects.create(
            empresa=orden.empresa,
            producto=producto_terminado,
            almacen=orden.almacen_destino,
            fecha=timezone.now(),
            tipo_movimiento='entrada_produccion',
            tipo_documento='recepcion_produccion',
            tipo_inventario='producto_terminado',
            numero_documento=str(orden.numero),
            cantidad_entrada=cantidad_producida,
            costo_unitario=costo_unitario_real,
            costo_total_entrada=cantidad_producida * costo_unitario_real,
            cantidad_saldo=stock_destino.cantidad,
            costo_promedio=costo_unitario_real,
            orden_produccion_id=orden.id,
            observaciones=f'Producción completada - Orden {orden.numero}',
            created_by=''
        )
        
        # Actualizar stock total del producto terminado
        producto_terminado.actualizar_stock_total()
        
        # 4. Actualizar precio_compra del producto terminado (costo de producción)
        producto_terminado.precio_compra = costo_unitario_real
        producto_terminado.save(update_fields=['precio_compra'])
        
        # 5. Calcular tiempo real
        if orden.fecha_inicio:
            tiempo_transcurrido = timezone.now() - orden.fecha_inicio
            tiempo_real_minutos = int(tiempo_transcurrido.total_seconds() / 60)
        else:
            tiempo_real_minutos = 0
        
        # 6. Actualizar orden
        orden.estado = 'finalizada'
        orden.fecha_fin = timezone.now()
        orden.cantidad_producida = cantidad_producida
        orden.costo_mano_obra_real = costo_mano_obra_real
        orden.costo_indirecto_real = costo_indirecto_real
        orden.tiempo_real = tiempo_real_minutos
        if observaciones:
            orden.observaciones = observaciones
        orden.save()
        
        # 7. Crear snapshot de costeo (ProductionCost)
        costeo, created = ProductionCost.objects.get_or_create(
            orden_produccion=orden,
            defaults={
                'costo_mano_obra': costo_mano_obra_real,
                'costo_indirecto': costo_indirecto_real
            }
        )
        
        if not created:
            costeo.costo_mano_obra = costo_mano_obra_real
            costeo.costo_indirecto = costo_indirecto_real
        
        # Calcular todos los costos
        costeo.calcular_costos()
        
        # 8. Registrar evento en historial
        HistorialOrdenProduccion.registrar_evento(
            orden=orden,
            tipo_evento='finalizacion',
            descripcion=f'Orden finalizada. Se produjeron {cantidad_producida} unidades de {producto_terminado.nombre}',
            usuario=None,
            datos_adicionales={
                'cantidad_producida': float(cantidad_producida),
                'costo_unitario': float(costo_unitario_real),
                'costo_total': float(costo_total),
                'tiempo_real_minutos': tiempo_real_minutos
            }
        )
        
        return orden
    
    @staticmethod
    @transaction.atomic
    def cancelar_orden(orden_id, motivo=""):
        """
        Cancela una orden de producción.
        No afecta inventarios (solo cambia estado).
        
        Args:
            orden_id: ID de la orden a cancelar
            motivo: Motivo de cancelación
            
        Returns:
            OrdenProduccion: La orden cancelada
            
        Raises:
            ValidationError: Si hay errores de validación
        """
        try:
            orden = OrdenProduccion.objects.get(id=orden_id)
        except OrdenProduccion.DoesNotExist:
            raise ValidationError('Orden de producción no encontrada')
        
        # Validar que no esté finalizada
        if orden.estado == 'finalizada':
            raise ValidationError('No se puede cancelar una orden finalizada')
        
        if orden.estado == 'cancelada':
            raise ValidationError('La orden ya está cancelada')
        
        # Cancelar orden
        orden.estado = 'cancelada'
        if motivo:
            orden.observaciones = f"CANCELADA: {motivo}\n\n{orden.observaciones}"
        orden.save()
        
        # Registrar evento en historial
        HistorialOrdenProduccion.registrar_evento(
            orden=orden,
            tipo_evento='cancelacion',
            descripcion=f'Orden cancelada. Motivo: {motivo or "No especificado"}',
            usuario=None,
            datos_adicionales={
                'motivo': motivo or 'No especificado'
            }
        )
        
        return orden
    
    @staticmethod
    def validar_stock_receta(empresa, receta_id, cantidad, almacen_insumos_id):
        """
        Valida si hay stock suficiente para producir una cantidad de una receta.
        
        Args:
            empresa: Instancia de Empresa
            receta_id: ID de la receta
            cantidad: Cantidad a producir
            almacen_insumos_id: ID del almacén de insumos
            
        Returns:
            dict: {
                'valido': bool,
                'insumos': list de dict con info de cada insumo
            }
        """
        try:
            receta = RecetaProducto.objects.get(id=receta_id, empresa=empresa)
            almacen = Almacen.objects.get(id=almacen_insumos_id, empresa=empresa)
        except (RecetaProducto.DoesNotExist, Almacen.DoesNotExist):
            raise ValidationError('Receta o almacén no encontrado')
        
        factor = cantidad / receta.cantidad_producida
        detalles = receta.detalles.select_related('insumo').all()
        
        resultado = {
            'valido': True,
            'insumos': []
        }
        
        for detalle in detalles:
            cantidad_necesaria = detalle.cantidad * factor
            
            try:
                stock = Stock.objects.get(
                    producto=detalle.insumo,
                    almacen=almacen,
                    empresa=empresa
                )
                stock_disponible = stock.cantidad
            except Stock.DoesNotExist:
                stock_disponible = 0
            
            suficiente = stock_disponible >= cantidad_necesaria
            if not suficiente:
                resultado['valido'] = False
            
            resultado['insumos'].append({
                'insumo_id': detalle.insumo.id,
                'insumo_nombre': detalle.insumo.nombre,
                'insumo_sku': detalle.insumo.sku,
                'cantidad_necesaria': float(cantidad_necesaria),
                'stock_disponible': float(stock_disponible),
                'suficiente': suficiente,
                'faltante': float(max(0, cantidad_necesaria - stock_disponible))
            })
        
        return resultado
