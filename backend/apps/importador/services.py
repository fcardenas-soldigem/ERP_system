"""
Importador Excel — Services
Soporta dos formatos:
  • "standard"    → cada fila tiene compra+venta combinadas (formato anterior)
  • "referenced"  → hojas separadas por entidad con IDs cruzados
                    (PROVEEDORES, PRODUCTOS, COMPRAS, VENTAS, PROYECTOS)
"""
import hashlib
import logging
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import numpy as np
import pandas as pd
from django.db import transaction
from django.utils import timezone

from apps.compras.models import Proveedor, Compra, CompraDetalle
from apps.inventario.models.almacen import Almacen
from apps.inventario.models.categoria import Categoria
from apps.inventario.models.movimiento_inventario import MovimientoInventario
from apps.inventario.models.producto import Producto
from apps.inventario.models.stock import Stock
from apps.ventas.models import Cliente, Venta, DetalleVenta

logger = logging.getLogger(__name__)

# ─── Alias table ──────────────────────────────────────────────────────────────

COLUMN_ALIASES = {
    # ── Columnas con guion bajo del formato Excel estructurado ─────────────────
    # COMPRAS sheet
    'precio_unit_sin_igv':   'precio_compra',         # precio unitario sin IGV → precio_compra (base)
    'precio_unit_con_igv':   'precio_final_compra',   # precio unitario con IGV → fallback (/1.18)
    'subtotal_sin_igv':      None,                    # ignorar — se recalcula vía actualizar_totales
    'igv_unit':              None,                    # ignorar
    'igv_total':             None,                    # ignorar
    'total_con_igv':         None,                    # ignorar — es total de fila, no precio unitario
    # PRODUCTOS sheet
    'precio_compra':         'precio_compra',
    'precio_venta':          'precio_venta',

    # Identificadores cruzados
    'id':              'id_fila',
    'id proveedor':    'id_proveedor',
    'id_proveedor':    'id_proveedor',
    'cod proveedor':   'id_proveedor',
    'codigo proveedor':'id_proveedor',
    'id producto':     'id_producto',
    'id_producto':     'id_producto',
    'cod producto':    'id_producto',
    'codigo producto': 'id_producto',
    'id cliente':      'id_cliente',
    'id_cliente':      'id_cliente',

    # Producto
    'producto':        'producto_nombre',
    'productos':       'producto_nombre',
    'descripcion':     'producto_nombre',
    'item':            'producto_nombre',
    'articulo':        'producto_nombre',
    'nombre producto': 'producto_nombre',
    'nombre':          'producto_nombre',
    'detalle':         'producto_nombre',

    # Cantidad
    'cantidad':        'cantidad',
    'cant':            'cantidad',
    'qty':             'cantidad',
    'unidades':        'cantidad',
    'cant vendida':    'cantidad',

    # Proveedor
    'proveedor':       'proveedor_nombre',
    'proveedores':     'proveedor_nombre',
    'razon social':    'proveedor_nombre',
    'nombre proveedor':'proveedor_nombre',
    'empresa':         'proveedor_nombre',

    # RUC
    'ruc':                  'proveedor_ruc',
    'ruc proveedor':        'proveedor_ruc',
    'ruc del proveedor':    'proveedor_ruc',
    'ruc/dni':              'proveedor_ruc',
    'numero ruc':           'proveedor_ruc',
    'n ruc':                'proveedor_ruc',

    # Cliente
    'cliente':         'cliente_nombre',
    'clientes':        'cliente_nombre',
    'nombre cliente':  'cliente_nombre',
    'comprador':       'cliente_nombre',

    # Precio compra (sin IGV)
    'precio de compra':      'precio_compra',
    'precio compra':         'precio_compra',
    'pc':                    'precio_compra',
    'p compra':              'precio_compra',
    'costo unitario':        'precio_compra',
    'costo':                 'precio_compra',
    'costo unit':            'precio_compra',
    'valor compra':          'precio_compra',
    'precio unit compra':    'precio_compra',
    'precio unitario compra':'precio_compra',
    'valor unitario':        'precio_compra',
    'precio unit':           'precio_compra',
    'p.u. compra':           'precio_compra',
    'p.u compra':            'precio_compra',
    'precio s/ igv':         'precio_compra',
    'monto':                 'precio_compra',
    'precio c/igv':          'precio_final_compra',
    'precio con igv':        'precio_final_compra',
    'precio s/igv':          'precio_compra',
    'precio sin igv':        'precio_compra',
    'p.u':                   'precio_compra',
    'pu':                    'precio_compra',
    'unit price':            'precio_compra',
    'unit cost':             'precio_compra',
    'cost':                  'precio_compra',

    # Precio final compra (con IGV)
    'precio final - c':      'precio_final_compra',
    'precio final-c':        'precio_final_compra',
    'precio final c':        'precio_final_compra',
    'pf':                    'precio_final_compra',
    'total compra':          'precio_final_compra',
    'precio total compra':   'precio_final_compra',
    'importe compra':        'precio_final_compra',
    'total c/igv':           'precio_final_compra',

    # IGV compra
    'igv-c':      'igv_compra',
    'igv c':      'igv_compra',
    'igv compra': 'igv_compra',

    # Precio venta (sin IGV)
    'precio de venta':       'precio_venta',
    'precio venta':          'precio_venta',
    'pv':                    'precio_venta',
    'p venta':               'precio_venta',
    'valor venta':           'precio_venta',
    'precio unit venta':     'precio_venta',
    'precio unitario venta': 'precio_venta',
    'precio unitario':       'precio_venta',
    'p.u. venta':            'precio_venta',
    'p.u venta':             'precio_venta',
    'venta unitario':        'precio_venta',
    'precio':                'precio_venta',

    # Precio final venta (con IGV)
    'precio final - v':    'precio_final_venta',
    'precio final-v':      'precio_final_venta',
    'precio final v':      'precio_final_venta',
    'pfv':                 'precio_final_venta',
    'total venta':         'precio_final_venta',
    'importe venta':       'precio_final_venta',
    'precio final':        'precio_final_venta',
    'total c/igv venta':   'precio_final_venta',
    'importe':             'precio_final_venta',
    'total':               'precio_final_venta',

    # Moneda
    'moneda':    'moneda',
    'divisa':    'moneda',
    'currency':  'moneda',

    # IGV venta
    'igv-v':      'igv_venta',
    'igv v':      'igv_venta',
    'igv venta':  'igv_venta',
    'igv':        'igv_venta',

    # Utilidad
    'utilidad':  'utilidad',
    'ganancia':  'utilidad',
    'margen':    'porcentaje_margen',

    # Estado
    'estado':       'estado',
    'estado pago':  'estado',
    'condicion':    'estado',
    'situacion':    'estado',

    # Marca / Categoría
    'marca':      'marca',
    'brand':      'marca',
    'fabricante': 'marca',
    'categoria':  'categoria_nombre',
    'rubro':      'categoria_nombre',
    'tipo':       'tipo_venta',

    # Encargado
    'encargado':   'encargado',
    'responsable': 'encargado',
    'vendedor':    'encargado',
    'asesor':      'encargado',

    # Fechas
    'fecha de compra':   'fecha_compra',
    'fecha compra':      'fecha_compra',
    'fecha':             'fecha_compra',
    'fecha de ingreso':  'fecha_compra',
    'fecha de entrega':  'fecha_entrega',
    'fecha entrega':     'fecha_entrega',
    'fecha de venta':    'fecha_entrega',
    'fecha despacho':    'fecha_entrega',
    'fecha factura':     'fecha_compra',

    # Dirección / Teléfono (para hojas de Proveedores/Clientes)
    'direccion':  'direccion',
    'telefono':   'telefono',
    'email':      'email',
    'correo':     'email',

    # Columnas a ignorar
    'mes facturacion':    None,
    'mes de facturacion': None,
    '%':                  None,
    'porcentaje':         None,
    'utilidad %':         None,
}

IGNORAR_PREFIXES = ('unnamed',)

# Nombres de hoja que indican formato "referenced"
HOJA_TIPO = {
    'proveedores': 'proveedores',
    'proveedor':   'proveedores',
    'productos':   'productos',
    'producto':    'productos',
    'inventario':  'productos',
    'compras':     'compras',
    'compra':      'compras',
    'ventas':      'ventas',
    'venta':       'ventas',
    'proyectos':   'proyectos',
    'proyecto':    'proyectos',
    'servicios':   'proyectos',
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _norm(text: str) -> str:
    """Normaliza: minúsculas, sin tildes, sin emoji, sin espacios extra."""
    text = str(text).lower().strip()
    text = unicodedata.normalize('NFD', text)
    # Quita combining marks (tildes) Y caracteres no ASCII (emojis, símbolos)
    text = ''.join(
        c for c in text
        if unicodedata.category(c) != 'Mn' and ord(c) < 0x10000
        and (c.isalnum() or c in (' ', '_', '-', '.', '/'))
    )
    return ' '.join(text.split())


def _detect_tipo_hoja(sheet_name: str) -> str:
    """Detecta el tipo de hoja usando substring matching (tolera emojis y prefijos)."""
    normed = _norm(sheet_name)
    # Búsqueda exacta primero
    if normed in HOJA_TIPO:
        return HOJA_TIPO[normed]
    # Búsqueda por substring (p.ej. "📦 proveedores" → "proveedores" está contenido)
    for key, tipo in HOJA_TIPO.items():
        if key in normed:
            return tipo
    return 'standard'


def _detect_mapping(columns: list) -> dict:
    mapping = {}
    for col in columns:
        norm = _norm(col)
        if any(norm.startswith(p) for p in IGNORAR_PREFIXES):
            mapping[col] = None
            continue
        mapped = COLUMN_ALIASES.get(norm)
        if mapped is None:
            for alias, target in COLUMN_ALIASES.items():
                if alias and (alias in norm or norm in alias):
                    mapped = target
                    break
        mapping[col] = mapped
    return mapping


def _field_to_col(mapping: dict) -> dict:
    """Inverts mapping dict: field → first matching column."""
    result = {}
    for col, field in mapping.items():
        if field and field not in result:
            result[field] = col
    return result


def _clean_numeric(raw: str) -> str:
    """Strips currency symbols, whitespace, and normalizes thousands/decimal separators."""
    import re
    s = str(raw).strip()
    s = re.sub(r'[Ss]/\.?\s*', '', s)   # S/, S/., s/
    s = s.replace('$', '').replace('€', '').strip()

    # Detect thousands separator vs decimal:
    # "1,500.00" → comma is thousands  |  "1.500,00" → dot is thousands
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            # European: 1.500,00
            s = s.replace('.', '').replace(',', '.')
        else:
            # American: 1,500.00
            s = s.replace(',', '')
    elif ',' in s and '.' not in s:
        parts = s.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = s.replace(',', '.')
        else:
            s = s.replace(',', '')
    return s


def _safe_decimal(val, default=None) -> Decimal | None:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return default
    try:
        cleaned = _clean_numeric(val)
        if not cleaned or cleaned.lower() in ('nan', 'none', ''):
            return default
        return Decimal(cleaned).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError):
        return default


def _format_cell(val) -> str | None:
    """Formats a cell value for preview. Converts Excel float-integers to clean strings."""
    if val is None:
        return None
    if val is pd.NaT:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(val, float) and np.isnan(val):
        return None
    # Excel stores RUC/DNI as floats: 20390342048.0 → "20390342048"
    if isinstance(val, float) and val == int(val):
        return str(int(val))
    return str(val).strip() or None


def _safe_date(val, default=None) -> date | None:
    if val is None:
        return default
    # Pandas NaT check (NaTType no soporta .date())
    if val is pd.NaT:
        return default
    try:
        if pd.isna(val):
            return default
    except (TypeError, ValueError):
        pass
    if isinstance(val, float) and np.isnan(val):
        return default
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    # str "NaT" / "nan" / "none" → default
    as_str = str(val).strip().lower()
    if as_str in ('nat', 'nan', 'none', ''):
        return default
    try:
        result = pd.to_datetime(val, dayfirst=False)
        if result is pd.NaT or (hasattr(result, 'isnull') and result.isnull()):
            return default
        return result.date()
    except Exception:
        return default


def _map_estado(val: str) -> str:
    norm = _norm(str(val or ''))
    if norm in ('pagada', 'pagado', 'paid', 'completado', 'completada', 'cancelado', 'cancelada'):
        return 'pagada'
    if norm in ('parcial', 'partial', 'parcialmente pagado'):
        return 'parcial'
    return 'pendiente'


def _read_sheet(file_path: str, sheet_name: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=0, engine='openpyxl')
    except Exception:
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=0, engine='xlrd')
    return df.dropna(how='all').reset_index(drop=True)


def _synthetic_ruc(empresa_id: int, nombre: str) -> str:
    h = hashlib.md5(f"{empresa_id}:{nombre}".encode()).hexdigest()
    return ('9' + h[:10])[:11]


# ─── ExcelParserService ────────────────────────────────────────────────────────

class ExcelParserService:
    """Lee el archivo y devuelve la estructura de hojas con detección de columnas."""

    def parse(self, file_path: str) -> dict:
        try:
            xl = pd.ExcelFile(file_path, engine='openpyxl')
        except Exception:
            xl = pd.ExcelFile(file_path, engine='xlrd')

        hojas = []
        for sheet_name in xl.sheet_names:
            df = _read_sheet(file_path, sheet_name)
            columns = [str(c) for c in df.columns.tolist()]
            mapping = _detect_mapping(columns)
            ftoc = _field_to_col(mapping)

            # Preview 5 filas
            preview_filas = []
            for _, row in df.head(5).iterrows():
                preview_filas.append({
                    c: _format_cell(v)
                    for c, v in zip(columns, row.values)
                })

            # Tipo de hoja — usa substring matching para tolerar emojis y prefijos
            tipo_hoja = _detect_tipo_hoja(sheet_name)

            # Fila válidas
            prod_col = ftoc.get('producto_nombre')
            if prod_col and prod_col in df.columns:
                mask = df[prod_col].notna() & (df[prod_col].astype(str).str.strip().ne('')) \
                       & (df[prod_col].astype(str).str.strip().ne('nan'))
                total_filas = int(mask.sum())
            else:
                total_filas = len(df)

            # Warnings
            warnings = self._build_warnings(mapping, tipo_hoja)

            hojas.append({
                'nombre':          sheet_name,
                'tipo_hoja':       tipo_hoja,
                'columnas':        columns,
                'mapeo_detectado': mapping,
                'preview_filas':   preview_filas,
                'total_filas':     total_filas,
                'warnings':        warnings,
            })

        return {'hojas': hojas}

    def _build_warnings(self, mapping: dict, tipo_hoja: str) -> list:
        mapped = {v for v in mapping.values() if v}
        warnings = []

        if tipo_hoja == 'proveedores':
            if 'proveedor_nombre' not in mapped and 'producto_nombre' not in mapped:
                warnings.append('Sin columna de nombre de proveedor')

        elif tipo_hoja == 'productos':
            if 'producto_nombre' not in mapped:
                warnings.append('Sin columna de nombre — hoja no se puede importar')
            if 'precio_compra' not in mapped and 'precio_final_compra' not in mapped:
                warnings.append('Sin precio de compra — se usará 0 (actualizable después)')
            if 'precio_venta' not in mapped and 'precio_final_venta' not in mapped:
                warnings.append('Sin precio de venta — se usará mínimo para productos terminados')

        elif tipo_hoja == 'compras':
            if 'producto_nombre' not in mapped and 'id_producto' not in mapped:
                warnings.append('Sin columna de producto — hoja no se puede importar')
            if 'fecha_compra' not in mapped:
                warnings.append('Sin columna de fecha — configura fecha por defecto')
            if 'proveedor_nombre' not in mapped and 'id_proveedor' not in mapped:
                warnings.append('Sin proveedor — se asignará "Proveedor Genérico"')
            if 'precio_compra' not in mapped and 'precio_final_compra' not in mapped:
                warnings.append('Sin precio de compra detectado')

        elif tipo_hoja == 'ventas':
            if 'producto_nombre' not in mapped and 'id_producto' not in mapped:
                warnings.append('Sin columna de producto — hoja no se puede importar')
            if 'fecha_entrega' not in mapped:
                warnings.append('Sin columna de fecha — configura fecha por defecto')
            if 'precio_venta' not in mapped and 'precio_final_venta' not in mapped:
                warnings.append('Sin precio de venta detectado')

        elif tipo_hoja == 'standard':
            if 'producto_nombre' not in mapped and 'id_producto' not in mapped:
                warnings.append('Sin columna de producto — hoja podría no ser importable')
            if 'fecha_compra' not in mapped and 'fecha_entrega' not in mapped:
                warnings.append('Sin columna de fecha — se usará la fecha por defecto')
            if 'proveedor_nombre' not in mapped and 'id_proveedor' not in mapped:
                warnings.append('Sin columna de proveedor')
            if 'precio_compra' not in mapped and 'precio_final_compra' not in mapped:
                warnings.append('Sin precio de compra detectado')
            if 'precio_venta' not in mapped and 'precio_final_venta' not in mapped:
                warnings.append('Sin precio de venta detectado')

        return warnings


# ─── PreviewService ────────────────────────────────────────────────────────────

class PreviewService:
    """Extiende el parser con conteos estimados por empresa."""

    def get_preview(self, file_path: str, empresa) -> dict:
        parser = ExcelParserService()
        result = parser.parse(file_path)
        for hoja in result['hojas']:
            hoja['estimado'] = self._estimate(file_path, hoja, empresa)
        return result

    def _estimate(self, file_path: str, hoja_info: dict, empresa) -> dict:
        try:
            df = _read_sheet(file_path, hoja_info['nombre'])
        except Exception:
            return {}

        ftoc = _field_to_col(hoja_info['mapeo_detectado'])
        tipo = hoja_info['tipo_hoja']

        prod_col = ftoc.get('producto_nombre')
        prov_col = ftoc.get('proveedor_nombre')

        total_valid = hoja_info['total_filas']

        prov_nuevos = 0
        if prov_col and prov_col in df.columns:
            nombres = df[prov_col].dropna().astype(str).str.strip().unique()
            existing = set(
                Proveedor.objects.filter(empresa=empresa, razon_social__in=nombres)
                .values_list('razon_social', flat=True)
            )
            prov_nuevos = sum(1 for n in nombres if n and n not in existing)

        prod_nuevos = 0
        if prod_col and prod_col in df.columns:
            nombres = df[prod_col].dropna().astype(str).str.strip().unique()
            existing = set(
                Producto.objects.filter(empresa=empresa, nombre__in=nombres)
                .values_list('nombre', flat=True)
            )
            prod_nuevos = sum(1 for n in nombres if n and n not in existing)

        return {
            'compras':            total_valid if tipo in ('standard', 'compras') else 0,
            'ventas':             total_valid if tipo in ('standard', 'ventas', 'proyectos') else 0,
            'proveedores_nuevos': prov_nuevos,
            'productos_nuevos':   prod_nuevos,
        }


# ─── ImportService ─────────────────────────────────────────────────────────────

class ImportService:
    """Orquesta la importación completa de un ImportacionExcel."""

    def __init__(self, importacion, usuario):
        self.importacion = importacion
        self.empresa = importacion.empresa
        self.usuario = usuario
        self.errores: list[dict] = []
        self.stats = dict(
            proveedores_creados=0,
            productos_creados=0,
            compras_creadas=0,
            ventas_creadas=0,
        )
        # Lookups para formato "referenced"
        self._prov_lookup: dict = {}    # excel_id/nombre → Proveedor
        self._prod_lookup: dict = {}    # excel_id/nombre → Producto

    # ── Public entry point ─────────────────────────────────────────────────────

    def run(self, hojas_config: list, modo_parcial: bool = False):
        """
        hojas_config: list of {
            nombre_hoja, tipo_hoja, incluir, mapeo_columnas,
            defaults: { fecha, cliente_id, almacen_id, categoria_id }
        }
        """
        self.importacion.estado = 'importando'
        self.importacion.save(update_fields=['estado'])

        file_path = self.importacion.archivo.path
        formato = self._detect_formato(hojas_config)

        total_filas = 0
        importadas  = 0

        try:
            if formato == 'referenced':
                total_filas, importadas = self._run_referenced(file_path, hojas_config, modo_parcial)
            else:
                total_filas, importadas = self._run_standard(file_path, hojas_config, modo_parcial)
        except Exception as exc:
            logger.error("Import fatal: %s", exc, exc_info=True)
            self.importacion.estado = 'error'
            self.importacion.errores_json = [{'fila': 0, 'hoja': '—', 'error': str(exc)}]
            self.importacion.save()
            raise

        self.importacion.total_filas      = total_filas
        self.importacion.filas_importadas = importadas
        self.importacion.filas_con_error  = total_filas - importadas
        self.importacion.errores_json     = self.errores
        self.importacion.proveedores_creados = self.stats['proveedores_creados']
        self.importacion.productos_creados   = self.stats['productos_creados']
        self.importacion.compras_creadas     = self.stats['compras_creadas']
        self.importacion.ventas_creadas      = self.stats['ventas_creadas']
        self.importacion.estado = 'parcial' if self.errores else 'completado'
        self.importacion.save()

    # ── Formato detection ──────────────────────────────────────────────────────

    def _detect_formato(self, hojas_config: list) -> str:
        tipos = {hc.get('tipo_hoja', 'standard') for hc in hojas_config if hc.get('incluir', True)}
        referenced_tipos = {'proveedores', 'productos', 'compras', 'ventas', 'proyectos'}
        if tipos & referenced_tipos:
            return 'referenced'
        return 'standard'

    # ── Standard format (compra+venta en misma fila) ───────────────────────────

    def _run_standard(self, file_path, hojas_config, modo_parcial):
        total = importadas = 0
        for hoja_cfg in hojas_config:
            if not hoja_cfg.get('incluir', True):
                continue
            t, i = self._import_hoja_standard(file_path, hoja_cfg, modo_parcial)
            total += t
            importadas += i
        return total, importadas

    def _import_hoja_standard(self, file_path, hoja_cfg, modo_parcial):
        df = _read_sheet(file_path, hoja_cfg['nombre_hoja'])
        mapping = hoja_cfg.get('mapeo_columnas', {})
        defaults = hoja_cfg.get('defaults', {})
        ftoc = _field_to_col(mapping)
        prod_col = ftoc.get('producto_nombre')
        if not prod_col:
            return 0, 0

        total = importadas = 0
        for idx, row in df.iterrows():
            val = row.get(prod_col)
            if val is None or str(val).strip() in ('', 'nan', 'None'):
                continue
            total += 1
            if modo_parcial:
                try:
                    with transaction.atomic():
                        self._import_standard_row(row, ftoc, defaults, idx + 2, hoja_cfg['nombre_hoja'])
                    importadas += 1
                except Exception as exc:
                    self.errores.append({
                        'hoja': hoja_cfg['nombre_hoja'], 'fila': idx + 2,
                        'producto': str(val)[:60], 'error': str(exc)[:300],
                    })
            else:
                self._import_standard_row(row, ftoc, defaults, idx + 2, hoja_cfg['nombre_hoja'])
                importadas += 1

        return total, importadas

    # ── Referenced format (hojas separadas) ───────────────────────────────────

    def _run_referenced(self, file_path, hojas_config, modo_parcial):
        cfg_by_tipo = {hc['tipo_hoja']: hc for hc in hojas_config if hc.get('incluir', True)}

        # Paso 1: Proveedores
        if 'proveedores' in cfg_by_tipo:
            self._load_proveedores(file_path, cfg_by_tipo['proveedores'])

        # Paso 2: Productos
        if 'productos' in cfg_by_tipo:
            self._load_productos(file_path, cfg_by_tipo['productos'])

        total = importadas = 0

        # Paso 3: Compras
        if 'compras' in cfg_by_tipo:
            t, i = self._import_hoja_compras(file_path, cfg_by_tipo['compras'], modo_parcial)
            total += t; importadas += i

        # Paso 4: Ventas
        if 'ventas' in cfg_by_tipo:
            t, i = self._import_hoja_ventas(file_path, cfg_by_tipo['ventas'], modo_parcial)
            total += t; importadas += i

        # Paso 5: Proyectos (como ventas de servicio)
        if 'proyectos' in cfg_by_tipo:
            t, i = self._import_hoja_proyectos(file_path, cfg_by_tipo['proyectos'], modo_parcial)
            total += t; importadas += i

        return total, importadas

    def _load_proveedores(self, file_path, hoja_cfg):
        df = _read_sheet(file_path, hoja_cfg['nombre_hoja'])
        mapping = hoja_cfg.get('mapeo_columnas', {})
        defaults = hoja_cfg.get('defaults', {})
        ftoc = _field_to_col(mapping)

        # Acepta tanto 'id_proveedor' (ID_PROVEEDOR) como 'id_fila' (ID genérico)
        id_col   = ftoc.get('id_proveedor') or ftoc.get('id_fila')
        nom_col  = ftoc.get('proveedor_nombre') or ftoc.get('producto_nombre')
        ruc_col  = ftoc.get('proveedor_ruc')
        dir_col  = ftoc.get('direccion')
        tel_col  = ftoc.get('telefono')
        email_col= ftoc.get('email')

        for idx, row in df.iterrows():
            nombre = self._get_val(row, nom_col)
            if not nombre:
                continue
            ruc = self._get_val(row, ruc_col)
            proveedor, created = self._get_or_create_proveedor(nombre, ruc)
            if created:
                self.stats['proveedores_creados'] += 1
                # Enriquecer con datos adicionales si existen
                updates = {}
                if dir_col:
                    updates['direccion'] = self._get_val(row, dir_col) or ''
                if tel_col:
                    updates['telefono'] = str(self._get_val(row, tel_col) or '')[:15]
                if email_col:
                    val = self._get_val(row, email_col) or ''
                    if '@' in str(val):
                        updates['email'] = str(val)[:100]
                if updates:
                    Proveedor.objects.filter(pk=proveedor.pk).update(**updates)

            # Guardar en lookup por ID y por nombre
            id_val = self._get_val(row, id_col)
            if id_val:
                self._prov_lookup[str(id_val).strip()] = proveedor
            self._prov_lookup[_norm(nombre)] = proveedor

    def _load_productos(self, file_path, hoja_cfg):
        df = _read_sheet(file_path, hoja_cfg['nombre_hoja'])
        mapping = hoja_cfg.get('mapeo_columnas', {})
        defaults = hoja_cfg.get('defaults', {})
        ftoc = _field_to_col(mapping)

        # Acepta tanto 'id_producto' (ID_PRODUCTO) como 'id_fila' (ID genérico)
        id_col   = ftoc.get('id_producto') or ftoc.get('id_fila')
        nom_col  = ftoc.get('producto_nombre')
        marca_col= ftoc.get('marca')
        cat_col  = ftoc.get('categoria_nombre')
        pc_col   = ftoc.get('precio_compra') or ftoc.get('precio_final_compra')
        pv_col   = ftoc.get('precio_venta') or ftoc.get('precio_final_venta')

        almacen   = self._get_almacen(defaults.get('almacen_id'))
        categoria = self._get_categoria(defaults.get('categoria_id'))

        for idx, row in df.iterrows():
            nombre = self._get_val(row, nom_col)
            if not nombre:
                continue
            marca = self._get_val(row, marca_col)
            precio_compra = _safe_decimal(self._get_val(row, pc_col), Decimal('0'))
            precio_venta  = _safe_decimal(self._get_val(row, pv_col), Decimal('0'))

            # Usar categoría de fila si disponible
            cat_nombre = self._get_val(row, cat_col)
            if cat_nombre:
                cat_obj = Categoria.objects.filter(
                    empresa=self.empresa, nombre__iexact=str(cat_nombre)[:100]
                ).first()
                if not cat_obj:
                    cat_obj, _ = Categoria.objects.get_or_create(
                        empresa=self.empresa, nombre=str(cat_nombre)[:100],
                        defaults={'descripcion': ''}
                    )
                categoria = cat_obj

            producto, created = self._get_or_create_producto(
                nombre, marca, categoria, almacen, precio_compra, precio_venta
            )
            if created:
                self.stats['productos_creados'] += 1

            id_val = self._get_val(row, id_col)
            if id_val:
                self._prod_lookup[str(id_val).strip()] = producto
            self._prod_lookup[_norm(nombre)] = producto

    def _import_hoja_compras(self, file_path, hoja_cfg, modo_parcial):
        df = _read_sheet(file_path, hoja_cfg['nombre_hoja'])
        mapping = hoja_cfg.get('mapeo_columnas', {})
        defaults = hoja_cfg.get('defaults', {})
        ftoc = _field_to_col(mapping)

        prod_id_col = ftoc.get('id_producto')
        prod_nom_col= ftoc.get('producto_nombre')
        pivot_col   = prod_id_col or prod_nom_col
        if not pivot_col:
            return 0, 0

        total = importadas = 0
        for idx, row in df.iterrows():
            pivot = self._get_val(row, pivot_col)
            if not pivot:
                continue
            total += 1
            if modo_parcial:
                try:
                    with transaction.atomic():
                        self._import_compra_row(row, ftoc, defaults, idx + 2, hoja_cfg['nombre_hoja'])
                    importadas += 1
                except Exception as exc:
                    self.errores.append({
                        'hoja': hoja_cfg['nombre_hoja'], 'fila': idx + 2,
                        'producto': str(pivot)[:60], 'error': str(exc)[:300],
                    })
            else:
                self._import_compra_row(row, ftoc, defaults, idx + 2, hoja_cfg['nombre_hoja'])
                importadas += 1

        return total, importadas

    def _import_hoja_ventas(self, file_path, hoja_cfg, modo_parcial):
        df = _read_sheet(file_path, hoja_cfg['nombre_hoja'])
        mapping = hoja_cfg.get('mapeo_columnas', {})
        defaults = hoja_cfg.get('defaults', {})
        ftoc = _field_to_col(mapping)

        prod_id_col  = ftoc.get('id_producto')
        prod_nom_col = ftoc.get('producto_nombre')
        pivot_col    = prod_id_col or prod_nom_col
        if not pivot_col:
            return 0, 0

        total = importadas = 0
        for idx, row in df.iterrows():
            pivot = self._get_val(row, pivot_col)
            if not pivot:
                continue
            total += 1
            if modo_parcial:
                try:
                    with transaction.atomic():
                        self._import_venta_row(row, ftoc, defaults, idx + 2, hoja_cfg['nombre_hoja'])
                    importadas += 1
                except Exception as exc:
                    self.errores.append({
                        'hoja': hoja_cfg['nombre_hoja'], 'fila': idx + 2,
                        'producto': str(pivot)[:60], 'error': str(exc)[:300],
                    })
            else:
                self._import_venta_row(row, ftoc, defaults, idx + 2, hoja_cfg['nombre_hoja'])
                importadas += 1

        return total, importadas

    def _import_hoja_proyectos(self, file_path, hoja_cfg, modo_parcial):
        """Proyectos → ventas de tipo servicio (sin afectar inventario)."""
        df = _read_sheet(file_path, hoja_cfg['nombre_hoja'])
        mapping = hoja_cfg.get('mapeo_columnas', {})
        defaults = hoja_cfg.get('defaults', {})
        ftoc = _field_to_col(mapping)

        nom_col = ftoc.get('producto_nombre')
        if not nom_col:
            return 0, 0

        total = importadas = 0
        for idx, row in df.iterrows():
            nombre = self._get_val(row, nom_col)
            if not nombre:
                continue
            total += 1
            if modo_parcial:
                try:
                    with transaction.atomic():
                        self._import_proyecto_row(row, ftoc, defaults, idx + 2)
                    importadas += 1
                except Exception as exc:
                    self.errores.append({
                        'hoja': hoja_cfg['nombre_hoja'], 'fila': idx + 2,
                        'producto': str(nombre)[:60], 'error': str(exc)[:300],
                    })
            else:
                self._import_proyecto_row(row, ftoc, defaults, idx + 2)
                importadas += 1

        return total, importadas

    # ── Row importers ──────────────────────────────────────────────────────────

    def _resolve_moneda(self, row, ftoc) -> str:
        val = self._get_val(row, ftoc.get('moneda'))
        if val:
            v = str(val).strip().upper()
            if v in ('USD', 'DOLLAR', 'DOLLARS', '$'):
                return 'USD'
        return 'PEN'  # Default PEN — ERP peruano

    def _import_standard_row(self, row, ftoc, defaults, fila_num, nombre_hoja):
        """Fila con compra+venta combinadas."""
        prod_nombre = str(self._get_val(row, ftoc.get('producto_nombre')) or '').strip()
        if not prod_nombre or prod_nombre.lower() in ('nan', 'none', ''):
            return

        cantidad = _safe_decimal(self._get_val(row, ftoc.get('cantidad')), Decimal('1'))
        if not cantidad or cantidad <= 0:
            raise ValueError(f"Cantidad inválida en fila {fila_num}")

        prov_nombre = str(self._get_val(row, ftoc.get('proveedor_nombre')) or 'Proveedor Genérico').strip()
        prov_ruc    = self._get_val(row, ftoc.get('proveedor_ruc'))
        marca       = str(self._get_val(row, ftoc.get('marca')) or '').strip() or None
        estado_str  = self._get_val(row, ftoc.get('estado'))
        moneda      = self._resolve_moneda(row, ftoc)

        precio_compra = self._resolve_precio_compra(row, ftoc)
        precio_venta  = self._resolve_precio_venta(row, ftoc)

        fecha_default = self._parse_date_default(defaults.get('fecha'))
        fecha_compra  = _safe_date(self._get_val(row, ftoc.get('fecha_compra')), fecha_default)
        fecha_entrega = _safe_date(self._get_val(row, ftoc.get('fecha_entrega')), fecha_compra)

        almacen  = self._get_almacen(defaults.get('almacen_id'))
        categoria= self._get_categoria(defaults.get('categoria_id'))

        # Row value takes priority over wizard default
        cliente = None
        cliente_nom_row = str(self._get_val(row, ftoc.get('cliente_nombre')) or '').strip()
        if cliente_nom_row:
            cliente = self._get_or_create_cliente(cliente_nom_row)
        if not cliente:
            cliente = self._get_cliente(defaults.get('cliente_id'))

        self._validate_defaults(almacen, cliente, fecha_compra, fila_num)

        estado_importado = _map_estado(estado_str)

        proveedor, pnew = self._get_or_create_proveedor(prov_nombre, prov_ruc)
        if pnew:
            self.stats['proveedores_creados'] += 1

        producto, prnew = self._get_or_create_producto(
            prod_nombre, marca, categoria, almacen, precio_compra, precio_venta, moneda=moneda
        )
        if prnew:
            self.stats['productos_creados'] += 1

        # Compra
        self._create_compra(
            proveedor, producto, almacen, cantidad,
            precio_compra, fecha_compra, estado_importado, moneda=moneda
        )

        # Venta
        self._create_venta(
            cliente, producto, almacen, cantidad,
            precio_venta, fecha_entrega or fecha_compra, estado_importado,
            notas='Importado desde Excel', moneda=moneda
        )

    def _import_compra_row(self, row, ftoc, defaults, fila_num, nombre_hoja):
        prod_id  = str(self._get_val(row, ftoc.get('id_producto')) or '').strip()
        prod_nom = str(self._get_val(row, ftoc.get('producto_nombre')) or '').strip()
        prov_id  = str(self._get_val(row, ftoc.get('id_proveedor')) or '').strip()
        prov_nom = str(self._get_val(row, ftoc.get('proveedor_nombre')) or '').strip()

        producto   = self._resolve_prod(prod_id, prod_nom, ftoc, row, defaults)
        proveedor  = self._resolve_prov(prov_id, prov_nom, ftoc, row, defaults)

        cantidad      = _safe_decimal(self._get_val(row, ftoc.get('cantidad')), Decimal('1'))
        precio_compra = self._resolve_precio_compra(row, ftoc)
        estado_str    = self._get_val(row, ftoc.get('estado'))
        moneda        = self._resolve_moneda(row, ftoc)
        fecha_default = self._parse_date_default(defaults.get('fecha'))
        fecha_compra  = _safe_date(self._get_val(row, ftoc.get('fecha_compra')), fecha_default)
        almacen       = self._get_almacen(defaults.get('almacen_id'))

        if not almacen:
            raise ValueError(f"Sin almacén disponible — configura uno por defecto (fila {fila_num})")
        if not fecha_compra:
            raise ValueError(f"Sin fecha — configura una fecha por defecto (fila {fila_num})")

        if not proveedor:
            proveedor, pnew = self._get_or_create_proveedor('Proveedor Genérico', None)
            if pnew:
                self.stats['proveedores_creados'] += 1
        if not producto:
            raise ValueError(f"Producto no encontrado (fila {fila_num})")

        self._create_compra(
            proveedor, producto, almacen, cantidad or Decimal('1'),
            precio_compra, fecha_compra, _map_estado(estado_str), moneda=moneda
        )

    def _import_venta_row(self, row, ftoc, defaults, fila_num, nombre_hoja):
        prod_id  = str(self._get_val(row, ftoc.get('id_producto')) or '').strip()
        prod_nom = str(self._get_val(row, ftoc.get('producto_nombre')) or '').strip()

        producto = self._resolve_prod(prod_id, prod_nom, ftoc, row, defaults)

        # Row value takes priority over wizard default
        cliente = None
        cliente_nom = str(self._get_val(row, ftoc.get('cliente_nombre')) or '').strip()
        if cliente_nom:
            cliente = self._get_or_create_cliente(cliente_nom)
        if not cliente:
            cliente = self._get_cliente(defaults.get('cliente_id'))

        cantidad     = _safe_decimal(self._get_val(row, ftoc.get('cantidad')), Decimal('1'))
        precio_venta = self._resolve_precio_venta(row, ftoc)
        estado_str   = self._get_val(row, ftoc.get('estado'))
        moneda       = self._resolve_moneda(row, ftoc)
        fecha_default= self._parse_date_default(defaults.get('fecha'))
        fecha_entrega= _safe_date(self._get_val(row, ftoc.get('fecha_entrega')), fecha_default)
        almacen      = self._get_almacen(defaults.get('almacen_id'))

        if not cliente:
            raise ValueError(
                f"Sin cliente disponible — añade columna 'cliente' en el Excel "
                f"o configura un cliente por defecto en el paso 2 (fila {fila_num})"
            )
        if not producto:
            raise ValueError(f"Producto no encontrado (fila {fila_num})")
        if not fecha_entrega:
            raise ValueError(f"Sin fecha disponible (fila {fila_num})")

        self._create_venta(
            cliente, producto, almacen, cantidad or Decimal('1'),
            precio_venta, fecha_entrega, _map_estado(estado_str),
            notas='Importado desde Excel', moneda=moneda
        )

    def _import_proyecto_row(self, row, ftoc, defaults, fila_num):
        nombre    = str(self._get_val(row, ftoc.get('producto_nombre')) or '').strip()
        cliente   = self._get_cliente(defaults.get('cliente_id'))
        almacen   = self._get_almacen(defaults.get('almacen_id'))
        categoria = self._get_categoria(defaults.get('categoria_id'))

        if not nombre:
            return
        if not cliente:
            raise ValueError(f"Sin cliente disponible (fila {fila_num})")

        cantidad     = _safe_decimal(self._get_val(row, ftoc.get('cantidad')), Decimal('1'))
        precio_venta = self._resolve_precio_venta(row, ftoc)
        estado_str   = self._get_val(row, ftoc.get('estado'))
        fecha_default= self._parse_date_default(defaults.get('fecha'))
        fecha         = _safe_date(self._get_val(row, ftoc.get('fecha_compra'))
                                   or self._get_val(row, ftoc.get('fecha_entrega')), fecha_default)

        producto, pnew = self._get_or_create_producto(
            nombre, None, categoria, almacen,
            Decimal('0'), precio_venta or Decimal('0'),
            tipo_producto='FINISHED',
        )
        if pnew:
            self.stats['productos_creados'] += 1

        self._create_venta(
            cliente, producto, almacen, cantidad or Decimal('1'),
            precio_venta, fecha or date.today(), _map_estado(estado_str),
            notas=f'Proyecto — importado desde Excel'
        )

    # ── Entity creators ────────────────────────────────────────────────────────

    def _create_compra(self, proveedor, producto, almacen, cantidad,
                       precio_compra, fecha, estado_importado, *, moneda='PEN'):
        tipo_compra = 'contado' if estado_importado == 'pagada' else 'credito_30'
        metodo_pago = 'efectivo' if tipo_compra == 'contado' else 'pendiente'

        # ── Precio: resolver ANTES de crear la compra ──────────────────────────
        # Fallback en cascada: columna Excel → precio_compra del producto → 0.01 mínimo.
        # No se lanza excepción aquí: si el precio falta, se usa el del producto.
        # Esto evita que filas sin precio en el Excel bloqueen toda la importación.
        if not precio_compra or precio_compra <= 0:
            precio_compra = (
                producto.precio_compra
                if producto.precio_compra and producto.precio_compra > 0
                else Decimal('0.01')
            )
            logger.info(
                "Compra '%s': precio no encontrado en Excel, usando precio del producto: %s",
                producto.nombre, precio_compra
            )

        compra = Compra(
            empresa=self.empresa,
            proveedor=proveedor,
            almacen=almacen,
            fecha_emision=fecha,
            tipo_compra=tipo_compra,
            metodo_pago=metodo_pago,
            moneda=moneda,
            igv_incluido=False,  # precio_compra es SIN IGV; actualizar_totales suma +18%
            notas='Importado desde Excel',
            subtotal=Decimal('0'),
            igv=Decimal('0'),
            total=Decimal('0'),
        )
        compra.save()
        logger.info("Compra creada: %s — proveedor=%s producto=%s cant=%s precio=%s",
                    compra.numero, proveedor.razon_social, producto.nombre, cantidad, precio_compra)

        detalle = CompraDetalle(
            compra=compra,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=precio_compra,
        )
        # CompraDetalle.save() llama compra.actualizar_totales() vía model hook
        detalle.save()
        self.stats['compras_creadas'] += 1

        # Actualizar inventario si la compra quedó pagada (igual que CompraSerializer.create())
        # Maneja RAW/SEMIFINISHED con InventarioMateriasPrimas correctamente
        compra.refresh_from_db()  # Rereads estado (Compra.save() puede haberlo cambiado)
        if compra.estado == 'pagada':
            logger.info("Compra %s pagada — actualizando stock", compra.numero)
            compra.actualizar_stock()

    def _create_venta(self, cliente, producto, almacen, cantidad,
                      precio_venta, fecha, estado_importado, notas='', *, moneda='PEN'):
        venta = Venta(
            empresa=self.empresa,
            cliente=cliente,
            fecha_emision=fecha,
            tipo_venta='contado',
            igv_incluido=True,
            estado='pagado',
            metodo_pago='efectivo',
            moneda=moneda,
            notas=notas,
            subtotal=Decimal('0'),
            igv=Decimal('0'),
            total=Decimal('0'),
        )
        venta.save()

        # If no price found in row, fall back to the product's stored sale price
        if not precio_venta or precio_venta <= 0:
            precio_venta = producto.precio_venta or Decimal('0')

        detalle = DetalleVenta(
            venta=venta,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=precio_venta,
        )
        # DetalleVenta.save() already calls venta.actualizar_totales() via model hook
        detalle.save()
        self.stats['ventas_creadas'] += 1

    # ── Stock helpers ──────────────────────────────────────────────────────────

    def _stock_entrada(self, producto, almacen, cantidad, costo, numero_doc):
        stock, _ = Stock.objects.get_or_create(
            producto=producto, almacen=almacen, empresa=self.empresa,
            defaults={'cantidad': Decimal('0')},
        )
        anterior = stock.cantidad
        stock.cantidad += cantidad
        stock.save()
        producto.actualizar_stock_total()

        try:
            MovimientoInventario.objects.create(
                empresa=self.empresa,
                producto=producto,
                almacen=almacen,
                fecha=timezone.now(),
                tipo_movimiento='entrada_compra',
                tipo_documento='compra',
                tipo_inventario='general',
                numero_documento=numero_doc,
                cantidad_entrada=cantidad,
                cantidad_saldo=stock.cantidad,
                costo_unitario=costo,
                costo_total_entrada=cantidad * costo,
                inventario_anterior=float(anterior),
                inventario_actual=float(stock.cantidad),
                observaciones='Importación Excel',
                created_by='importador',
            )
        except Exception as exc:
            logger.warning("MovimientoInventario entrada: %s", exc)

    def _stock_salida(self, producto, almacen, cantidad, precio, numero_doc):
        stock, _ = Stock.objects.get_or_create(
            producto=producto, almacen=almacen, empresa=self.empresa,
            defaults={'cantidad': Decimal('0')},
        )
        anterior = stock.cantidad
        stock.cantidad = max(Decimal('0'), stock.cantidad - cantidad)
        stock.save()
        producto.actualizar_stock_total()

        try:
            MovimientoInventario.objects.create(
                empresa=self.empresa,
                producto=producto,
                almacen=almacen,
                fecha=timezone.now(),
                tipo_movimiento='salida_venta',
                tipo_documento='venta',
                tipo_inventario='general',
                numero_documento=numero_doc,
                cantidad_salida=cantidad,
                cantidad_saldo=stock.cantidad,
                costo_unitario=precio,
                costo_total_salida=cantidad * precio,
                inventario_anterior=float(anterior),
                inventario_actual=float(stock.cantidad),
                observaciones='Importación Excel',
                created_by='importador',
            )
        except Exception as exc:
            logger.warning("MovimientoInventario salida: %s", exc)

    # ── get_or_create helpers ──────────────────────────────────────────────────

    def _get_or_create_cliente(self, nombre: str) -> 'Cliente':
        """Busca o crea un cliente por nombre. Genera DNI sintético si no tiene documento real."""
        nombre = str(nombre).strip()[:200] or 'Cliente Genérico'
        existing = Cliente.objects.filter(
            empresa=self.empresa,
            nombre__iexact=nombre,
        ).first()
        if existing:
            return existing
        # Documento sintético de 8 dígitos (DNI) para garantizar unicidad
        syn_doc = ('9' + hashlib.md5(f"{self.empresa.id}:{nombre}".encode()).hexdigest()[:7])[:8]
        cliente, _ = Cliente.objects.get_or_create(
            empresa=self.empresa,
            documento=syn_doc,
            defaults={
                'nombre': nombre,
                'tipo_documento': 'dni',
                'activo': True,
            }
        )
        return cliente

    def _get_or_create_proveedor(self, nombre, ruc=None):
        nombre = str(nombre).strip()[:200] or 'Proveedor Genérico'

        if ruc:
            ruc_clean = str(ruc).strip().replace(' ', '').replace('-', '')
            # Handle Excel float-formatted integers: "20390342048.0" → "20390342048"
            if '.' in ruc_clean:
                try:
                    ruc_clean = str(int(float(ruc_clean)))
                except (ValueError, OverflowError):
                    pass
            if ruc_clean and ruc_clean.lower() not in ('nan', 'none', ''):
                ruc_clean = ruc_clean[:11]
                try:
                    return Proveedor.objects.get_or_create(
                        empresa=self.empresa,
                        ruc=ruc_clean,
                        defaults={'razon_social': nombre, 'telefono': ''},
                    )
                except Exception:
                    pass

        existing = Proveedor.objects.filter(
            empresa=self.empresa,
            razon_social__iexact=nombre,
        ).first()
        if existing:
            return existing, False

        syn_ruc = _synthetic_ruc(self.empresa.id, nombre)
        return Proveedor.objects.get_or_create(
            empresa=self.empresa,
            ruc=syn_ruc,
            defaults={'razon_social': nombre, 'telefono': ''},
        )

    def _get_or_create_producto(self, nombre, marca, categoria, almacen,
                                 precio_compra, precio_venta, tipo_producto='FINISHED',
                                 moneda='PEN'):
        nombre = str(nombre).strip()[:200]
        marca  = str(marca or '').strip()[:100]

        qs = Producto.objects.filter(empresa=self.empresa, nombre__iexact=nombre)
        if marca:
            qs = qs.filter(marca__iexact=marca)
        existing = qs.first()
        if existing:
            return existing, False

        # SKU único basado en nombre
        base = (nombre[:12].upper().replace(' ', '-').replace('/', '-')
                .replace('\\', '-').replace('.', ''))
        sku = base
        counter = 1
        while Producto.objects.filter(empresa=self.empresa, sku=sku).exists():
            sku = f"{base[:10]}-{counter}"
            counter += 1

        # Enforce pricing rules matching ProductoSerializer validation:
        # FINISHED: precio_venta must be > 0
        if tipo_producto == 'FINISHED' and (not precio_venta or precio_venta <= 0):
            precio_venta = precio_compra if precio_compra and precio_compra > 0 else Decimal('0.01')
        # RAW/SEMIFINISHED: precio_venta must be 0 (forced by serializer)
        elif tipo_producto in ('RAW', 'SEMIFINISHED'):
            precio_venta = Decimal('0')

        producto = Producto.objects.create(
            empresa=self.empresa,
            sku=sku,
            nombre=nombre,
            marca=marca,
            tipo_producto=tipo_producto,
            categoria=categoria,
            almacen=almacen,
            precio_compra=precio_compra or Decimal('0'),
            precio_venta=precio_venta,
            moneda=moneda,
            stock_total=Decimal('0'),
            stock_minimo=Decimal('5'),
            stock_maximo=Decimal('100'),
        )
        return producto, True

    # ── Lookup resolvers ───────────────────────────────────────────────────────

    def _resolve_prod(self, prod_id, prod_nom, ftoc, row, defaults):
        if prod_id and prod_id in self._prod_lookup:
            return self._prod_lookup[prod_id]
        if prod_nom and _norm(prod_nom) in self._prod_lookup:
            return self._prod_lookup[_norm(prod_nom)]
        # Intenta crear en caliente
        if prod_nom:
            almacen   = self._get_almacen(defaults.get('almacen_id'))
            categoria = self._get_categoria(defaults.get('categoria_id'))
            pc = self._resolve_precio_compra(row, ftoc)
            pv = self._resolve_precio_venta(row, ftoc)
            prod, created = self._get_or_create_producto(
                prod_nom, None, categoria, almacen, pc, pv
            )
            if created:
                self.stats['productos_creados'] += 1
            self._prod_lookup[_norm(prod_nom)] = prod
            if prod_id:
                self._prod_lookup[prod_id] = prod
            return prod
        return None

    def _resolve_prov(self, prov_id, prov_nom, ftoc, row, defaults):
        if prov_id and prov_id in self._prov_lookup:
            return self._prov_lookup[prov_id]
        if prov_nom and _norm(prov_nom) in self._prov_lookup:
            return self._prov_lookup[_norm(prov_nom)]
        if prov_nom:
            ruc = self._get_val(row, ftoc.get('proveedor_ruc'))
            prov, created = self._get_or_create_proveedor(prov_nom, ruc)
            if created:
                self.stats['proveedores_creados'] += 1
            self._prov_lookup[_norm(prov_nom)] = prov
            if prov_id:
                self._prov_lookup[prov_id] = prov
            return prov
        return None

    # ── Price resolvers ────────────────────────────────────────────────────────

    def _resolve_precio_compra(self, row, ftoc) -> Decimal:
        pc  = _safe_decimal(self._get_val(row, ftoc.get('precio_compra')))
        pfc = _safe_decimal(self._get_val(row, ftoc.get('precio_final_compra')))
        if pc and pc > 0:
            return pc
        if pfc and pfc > 0:
            return (pfc / Decimal('1.18')).quantize(Decimal('0.01'))
        return Decimal('0')

    def _resolve_precio_venta(self, row, ftoc) -> Decimal:
        pv  = _safe_decimal(self._get_val(row, ftoc.get('precio_venta')))
        pfv = _safe_decimal(self._get_val(row, ftoc.get('precio_final_venta')))
        if pv and pv > 0:
            return pv
        if pfv and pfv > 0:
            return (pfv / Decimal('1.18')).quantize(Decimal('0.01'))
        return Decimal('0')

    # ── Default getters ────────────────────────────────────────────────────────

    def _get_almacen(self, almacen_id) -> Almacen | None:
        if almacen_id:
            a = Almacen.objects.filter(pk=almacen_id, empresa=self.empresa).first()
            if a:
                return a
        return Almacen.objects.filter(empresa=self.empresa, is_active=True).first()

    def _get_categoria(self, categoria_id) -> Categoria | None:
        if categoria_id:
            c = Categoria.objects.filter(pk=categoria_id, empresa=self.empresa).first()
            if c:
                return c
        return Categoria.objects.filter(empresa=self.empresa).first()

    def _get_cliente(self, cliente_id) -> Cliente | None:
        if cliente_id:
            c = Cliente.objects.filter(pk=cliente_id, empresa=self.empresa).first()
            if c:
                return c
        return Cliente.objects.filter(empresa=self.empresa, activo=True).first()

    def _parse_date_default(self, val) -> date:
        if not val:
            return date.today()
        try:
            return pd.to_datetime(str(val)).date()
        except Exception:
            return date.today()

    def _validate_defaults(self, almacen, cliente, fecha, fila_num):
        if not almacen:
            raise ValueError(f"Sin almacén disponible (fila {fila_num}) — configura uno en el paso 2")
        if not cliente:
            raise ValueError(f"Sin cliente disponible (fila {fila_num}) — configura uno en el paso 2")
        if not fecha:
            raise ValueError(f"Sin fecha (fila {fila_num}) — configura una fecha por defecto")

    def _get_val(self, row, col):
        if not col:
            return None
        val = row.get(col)
        if val is None:
            return None
        # pandas NaT
        if val is pd.NaT:
            return None
        try:
            if pd.isna(val):
                return None
        except (TypeError, ValueError):
            pass
        if isinstance(val, float) and np.isnan(val):
            return None
        s = str(val).strip()
        return None if s.lower() in ('nan', 'none', '', 'nat') else s
