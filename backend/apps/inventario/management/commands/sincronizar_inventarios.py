"""
Comando para sincronizar productos existentes con sus inventarios correspondientes.

Uso:
    python manage.py sincronizar_inventarios
    python manage.py sincronizar_inventarios --empresa="nombre_empresa"
    python manage.py sincronizar_inventarios --dry-run  # Solo muestra qué haría
    python manage.py sincronizar_inventarios --reclasificar  # Reclasifica productos según categoría
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.inventario.models import (
    Producto, Almacen, Stock,
    InventarioMateriasPrimas, InventarioProductosTerminados
)
from apps.empresas.models import Empresa


# Categorías que indican MATERIA PRIMA
CATEGORIAS_MATERIA_PRIMA = [
    'materia prima', 'materiaprima', 'materia_prima',
    'mp', 'm.p', 'm p',
    'insumo', 'insumos',
    'material', 'materiales',
    'raw', 'raw material', 'raw materials',
]


def es_materia_prima_por_categoria(categoria_nombre):
    """Determina si un producto es materia prima basándose en su categoría"""
    if not categoria_nombre:
        return False
    return categoria_nombre.lower().strip() in CATEGORIAS_MATERIA_PRIMA


class Command(BaseCommand):
    help = 'Sincroniza productos existentes con sus inventarios separados'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa',
            type=str,
            help='Nombre de la empresa específica a sincronizar'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra qué haría sin realizar cambios'
        )
        parser.add_argument(
            '--reclasificar',
            action='store_true',
            help='Reclasifica productos según su categoría (MP vs PT)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        reclasificar = options['reclasificar']
        empresa_nombre = options.get('empresa')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('=== MODO DRY-RUN (sin cambios) ===\n'))
        
        # Obtener empresas
        if empresa_nombre:
            empresas = Empresa.objects.filter(nombre__icontains=empresa_nombre)
        else:
            empresas = Empresa.objects.all()
        
        total_mp_creados = 0
        total_pt_creados = 0
        total_stock_creados = 0
        total_reclasificados = 0
        
        for empresa in empresas:
            self.stdout.write(f'\n=== Empresa: {empresa.nombre} ===')
            
            # Obtener almacén por defecto
            almacen_default = Almacen.objects.filter(empresa=empresa).first()
            if not almacen_default:
                self.stdout.write(self.style.WARNING(f'  Sin almacén, se omite esta empresa'))
                continue
            
            # Procesar productos
            productos = Producto.objects.filter(empresa=empresa).select_related('categoria')
            self.stdout.write(f'  Total productos: {productos.count()}')
            
            for producto in productos:
                almacen = producto.almacen or almacen_default
                cat_nombre = producto.categoria.nombre if producto.categoria else ''
                
                # ============================
                # RECLASIFICAR SEGÚN CATEGORÍA
                # ============================
                if reclasificar:
                    tipo_correcto = 'RAW' if es_materia_prima_por_categoria(cat_nombre) else 'FINISHED'
                    
                    if producto.tipo_producto != tipo_correcto:
                        self.stdout.write(
                            f'  [RECLASIFICAR] {producto.sku}: {producto.tipo_producto} -> {tipo_correcto} (cat: "{cat_nombre}")'
                        )
                        if not dry_run:
                            producto.tipo_producto = tipo_correcto
                            producto.save()
                        total_reclasificados += 1
                
                # ============================
                # MATERIAS PRIMAS
                # ============================
                if producto.tipo_producto in ['RAW', 'SEMIFINISHED']:
                    existe_mp = InventarioMateriasPrimas.objects.filter(
                        empresa=empresa,
                        producto=producto,
                        almacen=almacen
                    ).exists()
                    
                    if not existe_mp:
                        self.stdout.write(
                            f'  [MP] Crear inventario para: {producto.sku} - {producto.nombre}'
                        )
                        
                        if not dry_run:
                            InventarioMateriasPrimas.objects.create(
                                empresa=empresa,
                                producto=producto,
                                almacen=almacen,
                                cantidad_disponible=producto.stock_total or 0,
                                cantidad_reservada=0,
                                costo_unitario_promedio=producto.precio_compra or 0,
                                stock_minimo=producto.stock_minimo,
                                stock_maximo=producto.stock_maximo,
                            )
                        total_mp_creados += 1
                
                # ============================
                # PRODUCTOS TERMINADOS
                # ============================
                elif producto.tipo_producto == 'FINISHED':
                    existe_pt = InventarioProductosTerminados.objects.filter(
                        empresa=empresa,
                        producto=producto,
                        almacen=almacen
                    ).exists()
                    
                    if not existe_pt:
                        self.stdout.write(
                            f'  [PT] Crear inventario para: {producto.sku} - {producto.nombre}'
                        )
                        
                        if not dry_run:
                            InventarioProductosTerminados.objects.create(
                                empresa=empresa,
                                producto=producto,
                                almacen=almacen,
                                cantidad_disponible=producto.stock_total or 0,
                                cantidad_reservada=0,
                                costo_produccion_unitario=producto.precio_compra or 0,
                                precio_venta_sugerido=producto.precio_venta or 0,
                                stock_minimo=producto.stock_minimo,
                                stock_maximo=producto.stock_maximo,
                            )
                        total_pt_creados += 1
                
                # ============================
                # STOCK (compatibilidad)
                # ============================
                existe_stock = Stock.objects.filter(
                    empresa=empresa,
                    producto=producto,
                    almacen=almacen
                ).exists()
                
                if not existe_stock:
                    self.stdout.write(
                        f'  [STOCK] Crear stock para: {producto.sku}'
                    )
                    
                    if not dry_run:
                        Stock.objects.create(
                            empresa=empresa,
                            producto=producto,
                            almacen=almacen,
                            cantidad=producto.stock_total or 0,
                        )
                    total_stock_creados += 1
        
        # Resumen
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(f'RESUMEN:'))
        if reclasificar:
            self.stdout.write(f'  Productos reclasificados: {total_reclasificados}')
        self.stdout.write(f'  Inventarios MP creados: {total_mp_creados}')
        self.stdout.write(f'  Inventarios PT creados: {total_pt_creados}')
        self.stdout.write(f'  Stocks creados: {total_stock_creados}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n(Modo dry-run: no se realizaron cambios)'))
        else:
            self.stdout.write(self.style.SUCCESS('\nSincronización completada.'))
