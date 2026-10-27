"""
Entradas de los servicios del núcleo (B5): pydantic valida ANTES de tocar BD.
La empresa nunca es un campo: la pone el servidor desde el usuario vinculado.
"""
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class BuscarCliente(BaseModel):
    query: str = Field(min_length=2, max_length=120, description='alias, parte del nombre o RUC/DNI')


class BuscarProducto(BaseModel):
    query: str = Field(min_length=2, max_length=120, description='nombre aproximado o SKU, p. ej. "jabra 750"')


class ItemCotizacion(BaseModel):
    producto_id: Optional[int] = None
    descripcion: Optional[str] = Field(default=None, max_length=500)
    cantidad: Decimal = Field(gt=0, le=Decimal('100000'))
    precio_unitario: Optional[Decimal] = Field(default=None, ge=0)

    @field_validator('descripcion')
    @classmethod
    def _algo_que_cotizar(cls, v, info):
        if not v and not info.data.get('producto_id'):
            raise ValueError('cada ítem necesita producto_id o descripción')
        return v


class PrepararCotizacion(BaseModel):
    cliente_id: Optional[int] = None
    cliente_query: Optional[str] = Field(default=None, max_length=120)
    items: list[ItemCotizacion] = Field(min_length=1, max_length=50)
    asunto: Optional[str] = Field(default=None, max_length=200)
    moneda: Literal['PEN', 'USD'] = 'PEN'


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
