"""Registro central de todos los campos de archivo (FileField/ImageField).

Fuente única de verdad para los comandos de migración/auditoría de media y para
los tests. Si se añade un nuevo campo de archivo, agrégalo aquí.
"""


def file_field_specs():
    """Devuelve [(Model, 'nombre_campo'), ...] de todos los archivos subidos."""
    from apps.empresas.models import Empresa
    from apps.core.models.perfil import Perfil
    from apps.compras.models import (
        Compra, PagoCompra, ComprobantePago as ComprobantePagoCompra, RecepcionCompra,
    )
    from apps.ventas.models import (
        Venta, PagoVenta, ComprobantePago as ComprobantePagoVenta,
    )
    from apps.finanzas.models import GastoOperativo
    from apps.importador.models import ImportacionExcel

    return [
        (Empresa, 'logo'),
        (Empresa, 'firma_elaborado'),
        (Empresa, 'firma_aprobado'),
        (Perfil, 'foto'),
        (Compra, 'comprobante'),
        (PagoCompra, 'comprobante'),
        (ComprobantePagoCompra, 'archivo'),
        (RecepcionCompra, 'comprobante'),
        (Venta, 'comprobante'),
        (PagoVenta, 'comprobante'),
        (ComprobantePagoVenta, 'archivo'),
        (GastoOperativo, 'archivo_adjunto'),
        (ImportacionExcel, 'archivo'),
    ]
