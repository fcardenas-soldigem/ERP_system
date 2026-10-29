"""
Entradas de los servicios del núcleo (B5): pydantic valida ANTES de tocar BD.
La empresa nunca es un campo: la pone el servidor desde el usuario vinculado.
"""
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class BuscarCliente(BaseModel):
    query: str = Field(min_length=2, max_length=120, description='alias, parte del nombre o RUC/DNI')


class BuscarProducto(BaseModel):
    query: str = Field(min_length=2, max_length=120,
                       description='producto en texto, como lo dijo el usuario: "jabra 750", "monitor lg 24"')


class ItemCotizacion(BaseModel):
    """Un ítem TAL COMO lo dijo el vendedor: el servidor busca el producto.
    Si no está en el catálogo y trae precio, queda como línea libre."""
    descripcion: Optional[str] = Field(
        default=None, max_length=400,
        description='el producto en texto COMPLETO, tal como lo dijo el usuario, aunque sea '
                    'largo: "PEDESTAL CON INCLINACIÓN 90° TV 32 A 75 PULG / VESA 600X400MM"')
    # compatibilidad: versiones previas del prompt usaban "producto"
    producto: Optional[str] = Field(default=None, max_length=400,
                                    description='alias de descripcion; usa descripcion')
    producto_id: Optional[int] = Field(default=None, description='solo si ya conoces el id exacto')
    cantidad: Decimal = Field(
        gt=0, le=Decimal('100000'),
        description='número; convierte palabras: "una docena" = 12, "un par" = 2')
    precio_unitario: Optional[Decimal] = Field(
        default=None, ge=0, description='solo si el usuario dio precio por unidad')
    precio_incluye_igv: bool = Field(
        default=False,
        description='true si el usuario dijo que ese precio ya incluye IGV '
                    '(«incluido IGV», «inc. IGV», «con IGV»)')

    @property
    def texto(self):
        return (self.descripcion or self.producto or '').strip()

    @model_validator(mode='after')
    def _algo_que_cotizar(self):
        if not self.texto and not self.producto_id:
            raise ValueError('cada ítem necesita el producto (texto) o producto_id')
        return self


class PrepararCotizacion(BaseModel):
    cliente: Optional[str] = Field(
        default=None, max_length=200,
        description='cliente en texto, como lo dijo el usuario: nombre, alias o RUC. '
                    'Si aún no lo dijo, OMÍTELO: el borrador se crea igual y el bot lo pregunta. '
                    'NUNCA descartes los ítems por falta de cliente.')
    cliente_id: Optional[int] = Field(default=None, description='solo si ya conoces el id exacto')
    items: list[ItemCotizacion] = Field(min_length=1, max_length=50)
    asunto: Optional[str] = Field(default=None, max_length=200)
    moneda: Optional[Literal['PEN', 'USD']] = Field(
        default=None, description='SOLO si el usuario la dijo o dio precios con símbolo: '
                                  '"soles"/"lucas" → PEN; "dólares"/"$" → USD. Si no, OMÍTELA '
                                  '(el servidor la decide por el catálogo o la pregunta).')


class PrepararVenta(BaseModel):
    """«Crea/registra una venta»: mismo patrón que la cotización (líneas libres,
    IGV, cliente difuso), pero el documento es una VENTA."""
    cliente: Optional[str] = Field(
        default=None, max_length=200,
        description='cliente en texto, como lo dijo el usuario. Si aún no lo dijo, OMÍTELO.')
    cliente_id: Optional[int] = Field(default=None, description='solo si ya conoces el id exacto')
    items: list[ItemCotizacion] = Field(min_length=1, max_length=50)
    moneda: Optional[Literal['PEN', 'USD']] = Field(
        default=None, description='SOLO si el usuario la dijo o dio precios con símbolo: '
                                  '"soles"/"lucas" → PEN; "dólares"/"$" → USD. Si no, OMÍTELA '
                                  '(el servidor la decide por el catálogo o la pregunta).')
    # PROHIBIDO asumir contado: solo si el usuario lo dijo. Sin condición, el
    # borrador queda incompleto y el bot la pregunta con botones.
    condicion_pago: Optional[Literal['contado', 'credito']] = Field(
        default=None,
        description='SOLO si el usuario lo dijo: «al contado»/«ya pagó/pagaron» → contado; '
                    '«al crédito»/«a N días» → credito. Si NO lo dijo, OMÍTELO (el bot pregunta).')
    plazo_dias: Optional[int] = Field(
        default=None, ge=1, le=180,
        description='solo crédito: «a 15 días» = 15, «crédito 30» = 30. Sin plazo, omite.')
    metodo_pago: Optional[Literal['efectivo', 'transferencia', 'tarjeta', 'cheque']] = Field(
        default=None, description='SOLO si el usuario lo dijo; yape/plin = transferencia')


class ConvertirCotizacionEnVenta(BaseModel):
    """«Convierte la COT-107 en venta» / «la última cotización de Bruno hazla venta»."""
    cotizacion_numero: Optional[str] = Field(
        default=None, max_length=40, description='número de la cotización: "COT-00000107" o "107"')
    cliente_query: Optional[str] = Field(
        default=None, max_length=120,
        description='cliente en texto si no dieron número (se usa su última cotización abierta)')


class PrepararCobro(BaseModel):
    venta_numero: Optional[str] = Field(default=None, max_length=40)
    venta_id: Optional[int] = None
    cliente_query: Optional[str] = Field(default=None, max_length=120)
    monto: Optional[Decimal] = Field(default=None, gt=0)  # None → saldo completo
    # yape/plin se registran como transferencia (choices de PagoVenta)
    metodo_pago: Literal['efectivo', 'transferencia', 'tarjeta', 'cheque'] = 'transferencia'


class CambiarEstadoOperativo(BaseModel):
    venta_numero: Optional[str] = Field(default=None, max_length=40)
    venta_id: Optional[int] = None
    # «ya se entregó lo de minera andes»: el vendedor nombra al cliente, no el número
    cliente_query: Optional[str] = Field(default=None, max_length=120,
                                         description='cliente en texto si no dieron número de venta')
    nuevo_estado: Literal[
        'pendiente_compra', 'comprado', 'recibido', 'entregado',
        'esperando_oc_nr', 'facturado', 'cobrado',
    ]


class ConsultarVenta(BaseModel):
    venta_numero: Optional[str] = Field(default=None, max_length=40)
    cliente_query: Optional[str] = Field(default=None, max_length=120)


class VentasDetenidas(BaseModel):
    pass


class ResumenVentas(BaseModel):
    """«¿Cuánto voy en ventas este mes?»: cifras del período, no una venta puntual."""
    periodo: Literal['mes', 'mes_anterior'] = Field(
        default='mes', description='"este mes" → mes; "el mes pasado" → mes_anterior')
