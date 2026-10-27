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
    query: str = Field(min_length=2, max_length=120, description='nombre aproximado o SKU, p. ej. "jabra 750"')


class ItemCotizacion(BaseModel):
    """Un ítem TAL COMO lo dijo el vendedor: el servidor busca el producto."""
    producto: Optional[str] = Field(
        default=None, max_length=200,
        description='producto en texto, como lo dijo el usuario: "jabra 750", "mouse inalambrico"')
    producto_id: Optional[int] = Field(default=None, description='solo si ya conoces el id exacto')
    cantidad: Decimal = Field(
        gt=0, le=Decimal('100000'),
        description='número; convierte palabras: "una docena" = 12, "un par" = 2')
    precio_unitario: Optional[Decimal] = Field(
        default=None, ge=0, description='solo si el usuario dio precio por unidad')

    @model_validator(mode='after')
    def _algo_que_cotizar(self):
        if not (self.producto or '').strip() and not self.producto_id:
            raise ValueError('cada ítem necesita el producto (texto) o producto_id')
        return self


class PrepararCotizacion(BaseModel):
    cliente: Optional[str] = Field(
        default=None, max_length=200,
        description='cliente en texto, como lo dijo el usuario: nombre, alias o RUC')
    cliente_id: Optional[int] = Field(default=None, description='solo si ya conoces el id exacto')
    items: list[ItemCotizacion] = Field(min_length=1, max_length=50)
    asunto: Optional[str] = Field(default=None, max_length=200)
    moneda: Literal['PEN', 'USD'] = Field(
        default='PEN', description='"soles"/"lucas" → PEN; "dólares" → USD')

    @model_validator(mode='after')
    def _con_cliente(self):
        if not (self.cliente or '').strip() and not self.cliente_id:
            raise ValueError('falta el cliente')
        return self


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
    nuevo_estado: Literal[
        'pendiente_compra', 'comprado', 'recibido', 'entregado',
        'esperando_oc_nr', 'facturado', 'cobrado',
    ]


class ConsultarVenta(BaseModel):
    venta_numero: Optional[str] = Field(default=None, max_length=40)
    cliente_query: Optional[str] = Field(default=None, max_length=120)


class ConsultarStock(BaseModel):
    query: str = Field(min_length=2, max_length=120)


class VentasDetenidas(BaseModel):
    pass
