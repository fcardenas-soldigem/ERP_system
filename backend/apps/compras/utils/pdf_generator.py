"""
Generadores de PDF para el módulo de compras.

OrdenCompraPDFGenerator  — PDF profesional para objetos Compra (facturas recibidas).
PurchaseOrderPDFGenerator — PDF profesional para objetos OrdenCompra (OC enviadas).
"""
import logging
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image, KeepTogether,
)
from django.conf import settings
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# ─────────── paleta compartida ───────────
_PRIMARY     = colors.HexColor('#2B6CB0')   # azul usado en Compra PDF
_PRIMARY_LT  = colors.HexColor('#EBF8FF')
_DARK        = colors.HexColor('#1a1a1a')
_GRAY        = colors.HexColor('#666666')
_BORDER      = colors.HexColor('#cccccc')
_WHITE       = colors.white

# paleta OC (diseño profesional)
OC_DARK_HDR  = colors.HexColor('#1E3A5F')   # fondo barras de sección
OC_BLUE      = colors.HexColor('#2B5EA7')   # fondo header tabla + número OC
OC_ROW_ALT   = colors.HexColor('#EBF0F8')   # filas alternas

PAGE_W, PAGE_H = A4
MARGIN = 56   # ~2 cm


# ══════════════════════════════════════════════════════════════════
#  OrdenCompraPDFGenerator — para objetos Compra (facturas internas)
# ══════════════════════════════════════════════════════════════════
class OrdenCompraPDFGenerator:
    """Genera el PDF de una Compra (factura recibida del proveedor)."""

    PRIMARY = _PRIMARY
    PRIMARY_LIGHT = _PRIMARY_LT
    DARK = _DARK
    GRAY = _GRAY
    BORDER = _BORDER
    WHITE = _WHITE

    def __init__(self, compra):
        self.compra = compra
        self.empresa = compra.empresa
        self.proveedor = compra.proveedor
        self.buffer = BytesIO()
        self.styles = getSampleStyleSheet()

    def generar_pdf(self):
        doc = SimpleDocTemplate(
            self.buffer, pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=MARGIN + 10,
        )
        story = self._build_story()
        doc.build(story, onFirstPage=self._page_decor, onLaterPages=self._page_decor)
        self.buffer.seek(0)
        return self.buffer

    def _page_decor(self, canvas_obj, doc):
        canvas_obj.saveState()
        canvas_obj.setFont('Helvetica', 7)
        canvas_obj.setFillColor(self.GRAY)
        canvas_obj.drawString(MARGIN, 20, f'OC-{self.compra.numero}')
        canvas_obj.drawRightString(PAGE_W - MARGIN, 20,
                                   datetime.now().strftime('%d/%m/%Y %H:%M'))
        canvas_obj.drawCentredString(PAGE_W / 2, 20,
                                     f'Página {canvas_obj.getPageNumber()}')
        canvas_obj.restoreState()

    def _build_story(self):
        sym = 'S/' if self.compra.moneda == 'PEN' else '$'
        story = []

        story.append(self._header_section())
        story.append(Spacer(1, 6))
        story.append(self._section_bar('DATOS DEL PROVEEDOR'))
        story.append(self._proveedor_section())
        story.append(Spacer(1, 2))
        story.append(self._section_bar('DATOS DE LA COMPAÑÍA'))
        story.append(self._company_section())
        story.append(Spacer(1, 2))
        story.append(self._section_bar('CONDICIONES DE LA COMPAÑÍA'))
        story.append(self._conditions_header())
        story.append(self._items_table(sym))
        story.append(self._totals_section(sym))
        story.append(Spacer(1, 4))

        if self.compra.notas:
            story.append(self._section_bar('NOTAS / OBSERVACIONES'))
            story.append(self._notes_section())
            story.append(Spacer(1, 2))

        story.append(Spacer(1, 20))
        story.append(self._firma_section())

        return story

    def _section_bar(self, text):
        data = [[Paragraph(f'<b>{text}</b>',
                           ParagraphStyle('bar', fontName='Helvetica-Bold',
                                          fontSize=9, textColor=self.WHITE, leading=12))]]
        t = Table(data, colWidths=[PAGE_W - 2 * MARGIN])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.PRIMARY),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ]))
        return t

    def _header_section(self):
        W = PAGE_W - 2 * MARGIN
        logo_cell = self._logo_image()
        if not logo_cell:
            logo_cell = Paragraph(
                f'<b>{self.empresa.nombre}</b>',
                ParagraphStyle('en', fontSize=14, fontName='Helvetica-Bold', textColor=self.PRIMARY),
            )

        fecha_str = self.compra.fecha_emision.strftime('%d/%m/%Y')
        pag_style  = ParagraphStyle('hdr_p', fontSize=8, textColor=self.GRAY, alignment=TA_RIGHT)
        title_style = ParagraphStyle('hdr_t', fontSize=10, fontName='Helvetica-Bold',
                                     textColor=self.DARK, alignment=TA_RIGHT, spaceBefore=4)
        num_style  = ParagraphStyle('hdr_n', fontSize=16, fontName='Helvetica-Bold',
                                    textColor=self.PRIMARY, alignment=TA_RIGHT)

        right_data = [
            [Paragraph(f'Fecha de Emisión: {fecha_str}', pag_style)],
            [Paragraph('Nro Orden de Compra:', title_style)],
            [Paragraph(f'<b>OC-{self.compra.numero}</b>', num_style)],
        ]
        right_table = Table(right_data, colWidths=[W * 0.45])

        t = Table([[logo_cell, right_table]], colWidths=[W * 0.55, W * 0.45])
        t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        return t

    def _proveedor_section(self):
        W = PAGE_W - 2 * MARGIN
        half = W / 2
        p = self.proveedor

        if p:
            nombre    = p.razon_social or '—'
            ruc       = p.ruc or '—'
            direccion = p.direccion or '—'
            telefono  = p.telefono or '—'
            email     = p.email or '—'
            forma_pago = self._get_forma_pago()
        else:
            nombre = ruc = direccion = telefono = email = forma_pago = '—'

        rows = [
            [self._lv('Razón Social', nombre), self._lv('RUC', ruc)],
            [self._lv('Dirección', direccion), self._lv('Forma de Pago', forma_pago)],
            [self._lv('Contacto', telefono), self._lv('Mail', email)],
        ]
        t = Table(rows, colWidths=[half, half])
        t.setStyle(self._box_style())
        return t

    def _company_section(self):
        W = PAGE_W - 2 * MARGIN
        half = W / 2
        e = self.empresa

        rows = [
            [self._lv('Facturar a', e.nombre), self._lv('RUC', e.ruc or '—')],
            [self._lv('Dirección', e.direccion or '—'), ''],
        ]
        t = Table(rows, colWidths=[half, half])
        t.setStyle(self._box_style())
        return t

    def _conditions_header(self):
        W = PAGE_W - 2 * MARGIN
        half = W / 2
        moneda_text = 'Dólar Estadounidense' if self.compra.moneda == 'USD' else 'Sol Peruano'
        forma_pago  = self._get_forma_pago()

        rows = [[self._lv('Moneda', moneda_text), self._lv('Término de Pago', forma_pago)]]
        t = Table(rows, colWidths=[half, half])
        t.setStyle(self._box_style())
        return t

    def _items_table(self, sym):
        W = PAGE_W - 2 * MARGIN
        col_widths = [28, W - 28 - 50 - 40 - 70 - 70, 50, 40, 70, 70]
        header = ['N°', 'Descripción', 'Cantidad', 'U.M.', 'Precio Unit.', 'Importe']

        hdr_style = ParagraphStyle('thdr', fontSize=7, fontName='Helvetica-Bold',
                                   textColor=self.WHITE, alignment=TA_CENTER)
        data = [[Paragraph(h, hdr_style) for h in header]]

        for idx, d in enumerate(self.compra.detalles.all().order_by('id'), 1):
            producto = d.producto
            desc = producto.nombre if producto else 'Producto'
            if producto and producto.sku:
                desc = f'<b>{desc}</b><br/><font size="6.5" color="#666666">SKU: {producto.sku}</font>'
            else:
                desc = f'<b>{desc}</b>'
            if d.notas:
                desc += f'<br/><font size="6.5" color="#666666">{d.notas}</font>'

            qty = f'{d.cantidad:.0f}' if d.cantidad == int(d.cantidad) else f'{d.cantidad:.2f}'
            um  = (getattr(producto, 'unidad_medida', 'UND') or 'UND') if producto else 'UND'

            cs  = ParagraphStyle('cell',  fontSize=7.5, textColor=self.DARK)
            cr  = ParagraphStyle('cellr', fontSize=7.5, textColor=self.DARK, alignment=TA_RIGHT)
            cc  = ParagraphStyle('cellc', fontSize=7.5, textColor=self.DARK, alignment=TA_CENTER)
            data.append([
                Paragraph(str(idx), cc),
                Paragraph(desc, cs),
                Paragraph(qty, cc),
                Paragraph(um, cc),
                Paragraph(f'{sym} {d.precio_unitario:,.2f}', cr),
                Paragraph(f'{sym} {d.subtotal:,.2f}', cr),
            ])

        t = Table(data, colWidths=col_widths, repeatRows=1)
        cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY),
            ('TEXTCOLOR',  (0, 0), (-1, 0), self.WHITE),
            ('TOPPADDING',    (0, 0), (-1, 0), 5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
            ('TOPPADDING',    (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID',   (0, 0), (-1, -1), 0.5, self.BORDER),
        ]
        for i in range(1, len(data)):
            cmds.append(('BACKGROUND', (0, i), (-1, i),
                         self.WHITE if i % 2 == 1 else self.PRIMARY_LIGHT))
        t.setStyle(TableStyle(cmds))
        return t

    def _totals_section(self, sym):
        W = PAGE_W - 2 * MARGIN
        tot_w = 180

        s_lbl   = ParagraphStyle('tlbl',  fontSize=8, textColor=self.DARK)
        s_val   = ParagraphStyle('tval',  fontSize=8, textColor=self.DARK, alignment=TA_RIGHT)
        s_lbl_b = ParagraphStyle('tlblb', fontSize=9, fontName='Helvetica-Bold', textColor=self.DARK)
        s_val_b = ParagraphStyle('tvalb', fontSize=9, fontName='Helvetica-Bold',
                                 textColor=self.DARK, alignment=TA_RIGHT)
        s_lbl_g = ParagraphStyle('tlblg', fontSize=8, textColor=colors.HexColor('#555555'))
        s_val_g = ParagraphStyle('tvalg', fontSize=8, textColor=colors.HexColor('#555555'),
                                 alignment=TA_RIGHT)

        c = self.compra
        precios_con_igv = getattr(c, 'igv_incluido', False)

        tot_rows = [[Paragraph('Sub Total (c/IGV):' if precios_con_igv else 'Sub Total:', s_lbl),
                     Paragraph(f'{sym} {c.subtotal:,.2f}', s_val)]]

        descuento = getattr(c, 'descuento', None)
        if descuento and descuento > 0:
            tot_rows.append([Paragraph('Descuento:', s_lbl),
                             Paragraph(f'- {sym} {descuento:,.2f}', s_val)])
            tot_rows.append([Paragraph('Subtotal neto:', s_lbl_g),
                             Paragraph(f'{sym} {float(c.subtotal) - float(descuento):,.2f}', s_val_g)])

        if precios_con_igv:
            base = float(c.total) - float(c.igv) if c.total else float(c.subtotal) - float(c.igv)
            tot_rows.append([Paragraph('Base imponible:', s_lbl_g), Paragraph(f'{sym} {base:,.2f}', s_val_g)])
            tot_rows.append([Paragraph('IGV 18% (incluido):', s_lbl), Paragraph(f'{sym} {c.igv:,.2f}', s_val)])
        elif c.igv and c.igv > 0:
            tot_rows.append([Paragraph('IGV (18%):', s_lbl), Paragraph(f'{sym} {c.igv:,.2f}', s_val)])

        tot_rows.append([Paragraph('Total:', s_lbl_b), Paragraph(f'{sym} {c.total:,.2f}', s_val_b)])

        tot_t = Table(tot_rows, colWidths=[90, tot_w - 90])
        tot_t.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ('GRID',          (0, 0), (-1, -1), 0.5, self.BORDER),
            ('BACKGROUND',    (0, -1), (-1, -1), self.PRIMARY_LIGHT),
        ]))

        main = Table([['', tot_t]], colWidths=[W - tot_w, tot_w])
        main.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        return main

    def _notes_section(self):
        W = PAGE_W - 2 * MARGIN
        rows = [[Paragraph(self.compra.notas,
                           ParagraphStyle('note', fontSize=7.5, textColor=self.DARK, leading=10))]]
        t = Table(rows, colWidths=[W])
        t.setStyle(self._box_style())
        return t

    def _firma_section(self):
        W    = PAGE_W - 2 * MARGIN
        half = W / 2
        lbl  = ParagraphStyle('flbl',  fontSize=8, textColor=self.GRAY, alignment=TA_CENTER)
        name = ParagraphStyle('fname', fontSize=8, fontName='Helvetica-Bold',
                              textColor=self.DARK, alignment=TA_CENTER)
        line = ParagraphStyle('fline', fontSize=7.5, textColor=self.GRAY, alignment=TA_CENTER)

        data = [
            [Spacer(1, 40), Spacer(1, 40)],
            [Paragraph('_' * 35, line), Paragraph('_' * 35, line)],
            [Paragraph('Firma Autorizada', lbl), Paragraph('Sello Proveedor', lbl)],
            [Paragraph(self.empresa.nombre, name), ''],
        ]
        t = Table(data, colWidths=[half, half])
        t.setStyle(TableStyle([
            ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        return t

    # ── helpers ──
    def _logo_image(self, width=130, height=60):
        if self.empresa.logo:
            try:
                path = self.empresa.logo.path
                if os.path.exists(path):
                    return Image(path, width=width, height=height, kind='proportional')
            except Exception:
                pass
        return None

    def _lv(self, label, value):
        return Paragraph(
            f'<b>{label}:</b> {value or "—"}',
            ParagraphStyle('lv', fontSize=7.5, textColor=self.DARK, leading=10),
        )

    def _box_style(self):
        return TableStyle([
            ('BOX',           (0, 0), (-1, -1), 0.5, self.BORDER),
            ('INNERGRID',     (0, 0), (-1, -1), 0.5, self.BORDER),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ])

    def _get_forma_pago(self):
        if hasattr(self.compra, 'TIPO_COMPRA_CHOICES') and self.compra.tipo_compra:
            return dict(self.compra.TIPO_COMPRA_CHOICES).get(
                self.compra.tipo_compra, self.compra.tipo_compra
            )
        return '—'


# ══════════════════════════════════════════════════════════════════
#  PurchaseOrderPDFGenerator — para objetos OrdenCompra
# ══════════════════════════════════════════════════════════════════
class PurchaseOrderPDFGenerator:
    """Genera el PDF profesional de una OrdenCompra (documento enviado al proveedor)."""

    DARK_HDR = OC_DARK_HDR
    BLUE     = OC_BLUE
    ROW_ALT  = OC_ROW_ALT
    DARK     = _DARK
    GRAY     = _GRAY
    BORDER   = _BORDER
    WHITE    = _WHITE

    def __init__(self, orden, usuario=None):
        self.orden   = orden
        self.empresa = orden.empresa
        self.usuario = usuario
        self.buffer  = BytesIO()
        # Fix 3: resolver proveedor — FK primero, luego buscar por nombre
        self.proveedor = orden.proveedor
        if self.proveedor is None and orden.proveedor_nombre:
            try:
                from apps.compras.models import Proveedor
                self.proveedor = Proveedor.objects.filter(
                    empresa=orden.empresa,
                    razon_social__iexact=orden.proveedor_nombre,
                ).first()
            except Exception:
                pass

    # ── número de OC formateado ──
    def _oc_num(self):
        year = getattr(self.orden.fecha_emision, 'year', datetime.now().year)
        return f'OC-{year}-{self.orden.numero or "000001"}'

    # ── moneda y símbolo — OrdenCompra no tiene campo moneda ──
    def _moneda_texto(self):
        return 'Sol Peruano'

    def _sym(self):
        return 'S/'

    # ── nombre para la firma ──
    def _nombre_firma(self):
        # CustomUser usa nombre/apellido (no first_name/last_name de AbstractUser)
        if self.usuario:
            nombre   = getattr(self.usuario, 'nombre',   '') or ''
            apellido = getattr(self.usuario, 'apellido', '') or ''
            completo = f'{nombre} {apellido}'.strip()
            if completo:
                return completo
        return 'Fabrizio Paolo Cardenas Hernani'

    def _cargo_firma(self):
        return 'Sales Manager'

    # ── público ──
    def generar_pdf(self):
        doc = SimpleDocTemplate(
            self.buffer, pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=MARGIN + 10,
        )
        doc.build(
            self._build_story(),
            onFirstPage=self._page_decor,
            onLaterPages=self._page_decor,
        )
        self.buffer.seek(0)
        return self.buffer

    # ── footer de página (mismo patrón que CotizacionPDFGenerator) ──
    def _page_decor(self, canvas_obj, doc):
        oc = self._oc_num()
        canvas_obj.saveState()
        canvas_obj.setFont('Helvetica', 7)
        canvas_obj.setFillColor(self.GRAY)
        canvas_obj.drawString(MARGIN, 18, oc)
        canvas_obj.drawCentredString(
            PAGE_W / 2, 18,
            f'Página {canvas_obj.getPageNumber()}',
        )
        canvas_obj.drawRightString(
            PAGE_W - MARGIN, 18,
            self.orden.fecha_emision.strftime('%d/%m/%Y'),
        )
        canvas_obj.restoreState()

    # ── story principal ──
    def _build_story(self):
        sym = self._sym()
        story = []

        story.append(self._header_section())
        story.append(Spacer(1, 8))

        story.append(self._section_bar('DATOS DEL PROVEEDOR'))
        story.append(self._proveedor_section())
        story.append(Spacer(1, 2))

        story.append(self._section_bar('DATOS DE LA COMPAÑÍA'))
        story.append(self._company_section())
        story.append(Spacer(1, 2))

        story.append(self._section_bar('CONDICIONES DE LA COMPAÑÍA'))
        story.append(self._conditions_section())
        story.append(Spacer(1, 2))

        story.append(self._section_bar('DETALLE DE PRODUCTOS / SERVICIOS'))
        story.append(self._items_table(sym))
        story.append(self._totals_section(sym))
        story.append(Spacer(1, 6))

        if self.orden.fecha_entrega:
            story.append(self._section_bar('CONDICIONES DE ENTREGA'))
            story.append(self._delivery_section())
            story.append(Spacer(1, 2))

        if self.orden.notas:
            story.append(self._section_bar('OBSERVACIONES'))
            story.append(self._notes_section())
            story.append(Spacer(1, 2))

        story.append(Spacer(1, 20))
        story.append(self._firma_section())

        return story

    # ── barra de sección oscura ──
    def _section_bar(self, text):
        data = [[Paragraph(
            f'<b>{text}</b>',
            ParagraphStyle('oc_bar', fontName='Helvetica-Bold',
                           fontSize=9, textColor=self.WHITE, leading=12),
        )]]
        t = Table(data, colWidths=[PAGE_W - 2 * MARGIN])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), self.DARK_HDR),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ]))
        return t

    # ── header: logo izquierda, número OC derecha ──
    def _header_section(self):
        W    = PAGE_W - 2 * MARGIN
        oc   = self._oc_num()
        fecha_str = self.orden.fecha_emision.strftime('%d/%m/%Y')

        # columna izquierda
        logo = self._logo_image(width=140, height=65)
        if logo:
            left_content = logo
        else:
            left_content = Paragraph(
                f'<b>{self.empresa.nombre}</b>',
                ParagraphStyle('oc_en', fontSize=13, fontName='Helvetica-Bold',
                               textColor=self.BLUE),
            )

        # columna derecha
        right_data = [
            [Paragraph(
                f'Fecha de Emisión: {fecha_str}',
                ParagraphStyle('oc_d', fontSize=8, textColor=self.GRAY, alignment=TA_RIGHT),
            )],
            [Paragraph(
                'Nro Orden de Compra:',
                ParagraphStyle('oc_lbl', fontSize=9, fontName='Helvetica-Bold',
                               textColor=self.DARK, alignment=TA_RIGHT, spaceBefore=4),
            )],
            [Paragraph(
                f'<b>{oc}</b>',
                ParagraphStyle('oc_num', fontSize=17, fontName='Helvetica-Bold',
                               textColor=self.BLUE, alignment=TA_RIGHT),
            )],
        ]
        right_t = Table(right_data, colWidths=[W * 0.46])

        t = Table([[left_content, right_t]], colWidths=[W * 0.54, W * 0.46])
        t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
        return t

    # ── datos del proveedor ──
    def _proveedor_section(self):
        W    = PAGE_W - 2 * MARGIN
        half = W / 2
        p    = self.proveedor

        if p:
            nombre    = p.razon_social or '—'
            ruc       = p.ruc or '—'
            direccion = p.direccion or '—'
            contacto  = p.telefono or '—'
            email     = p.email or '—'
        else:
            nombre = self.orden.proveedor_nombre or '—'
            ruc = direccion = contacto = email = '—'

        rows = [
            [self._lv('Razón Social', nombre), self._lv('RUC', ruc)],
            [self._lv('Dirección', direccion), self._lv('Forma de Pago', '—')],
            [self._lv('Contacto', contacto), self._lv('Mail', email)],
        ]
        t = Table(rows, colWidths=[half, half])
        t.setStyle(self._box_style())
        return t

    # ── datos de la compañía ──
    def _company_section(self):
        W    = PAGE_W - 2 * MARGIN
        half = W / 2
        e    = self.empresa

        rows = [
            [self._lv('Facturar a', e.nombre), self._lv('RUC', e.ruc or '—')],
            [self._lv('Dirección', e.direccion or '—'), ''],
        ]
        t = Table(rows, colWidths=[half, half])
        t.setStyle(self._box_style())
        return t

    # ── condiciones: moneda + término de pago ──
    def _conditions_section(self):
        W    = PAGE_W - 2 * MARGIN
        half = W / 2

        rows = [[
            self._lv('Moneda', self._moneda_texto()),
            self._lv('Término de Pago', '—'),
        ]]
        t = Table(rows, colWidths=[half, half])
        t.setStyle(self._box_style())
        return t

    # ── tabla de items ──
    def _items_table(self, sym):
        W = PAGE_W - 2 * MARGIN
        desc_w = W - 28 - 50 - 40 - 75 - 75
        col_widths = [28, desc_w, 50, 40, 75, 75]
        headers = ['N°', 'Descripción', 'Cant.', 'U.M.', 'P. Unitario', 'Importe']

        hdr_s = ParagraphStyle('oc_thdr', fontSize=7.5, fontName='Helvetica-Bold',
                               textColor=self.WHITE, alignment=TA_CENTER)
        data = [[Paragraph(h, hdr_s) for h in headers]]

        # OrdenCompraDetalle restaurada con managed=False — tabla existe en BD
        detalles = list(self.orden.detalles.all().order_by('id'))

        if detalles:
            for idx, d in enumerate(detalles, 1):
                producto = getattr(d, 'producto', None)
                desc = producto.nombre if producto else 'Producto'
                if producto and getattr(producto, 'sku', None):
                    desc = (f'<b>{desc}</b>'
                            f'<br/><font size="6.5" color="#666666">SKU: {producto.sku}</font>')
                else:
                    desc = f'<b>{desc}</b>'

                qty = f'{d.cantidad:.0f}' if d.cantidad == int(d.cantidad) else f'{d.cantidad:.2f}'
                um  = (getattr(producto, 'unidad_medida', None) or 'UND') if producto else 'UND'
                precio_unit = getattr(d, 'precio_unitario', 0)
                importe     = float(d.cantidad) * float(precio_unit)

                cs = ParagraphStyle('oc_cs',  fontSize=7.5, textColor=self.DARK)
                cr = ParagraphStyle('oc_cr',  fontSize=7.5, textColor=self.DARK, alignment=TA_RIGHT)
                cc = ParagraphStyle('oc_cc',  fontSize=7.5, textColor=self.DARK, alignment=TA_CENTER)
                data.append([
                    Paragraph(str(idx), cc),
                    Paragraph(desc, cs),
                    Paragraph(qty, cc),
                    Paragraph(um, cc),
                    Paragraph(f'{sym} {float(precio_unit):,.2f}', cr),
                    Paragraph(f'{sym} {importe:,.2f}', cr),
                ])
        else:
            cs = ParagraphStyle('oc_empty', fontSize=7.5, textColor=self.GRAY, alignment=TA_CENTER)
            data.append(['', Paragraph('(sin items registrados)', cs), '', '', '', ''])

        t = Table(data, colWidths=col_widths, repeatRows=1)
        cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), self.BLUE),
            ('TEXTCOLOR',  (0, 0), (-1, 0), self.WHITE),
            ('TOPPADDING',    (0, 0), (-1, 0), 5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
            ('TOPPADDING',    (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID',   (0, 0), (-1, -1), 0.5, self.BORDER),
        ]
        for i in range(1, len(data)):
            cmds.append(('BACKGROUND', (0, i), (-1, i),
                         self.WHITE if i % 2 == 1 else self.ROW_ALT))
        t.setStyle(TableStyle(cmds))
        return t

    # ── totales ──
    def _totals_section(self, sym):
        W     = PAGE_W - 2 * MARGIN
        tot_w = 190

        s_lbl   = ParagraphStyle('oc_tl',  fontSize=8, textColor=self.DARK)
        s_val   = ParagraphStyle('oc_tv',  fontSize=8, textColor=self.DARK, alignment=TA_RIGHT)
        s_lbl_b = ParagraphStyle('oc_tlb', fontSize=9, fontName='Helvetica-Bold', textColor=self.DARK)
        s_val_b = ParagraphStyle('oc_tvb', fontSize=9, fontName='Helvetica-Bold',
                                 textColor=self.DARK, alignment=TA_RIGHT)
        s_lbl_g = ParagraphStyle('oc_tlg', fontSize=8, textColor=self.GRAY)
        s_val_g = ParagraphStyle('oc_tvg', fontSize=8, textColor=self.GRAY, alignment=TA_RIGHT)

        o = self.orden
        tot_rows = [
            [Paragraph('Sub Total:', s_lbl),   Paragraph(f'{sym} {float(o.subtotal):,.2f}', s_val)],
            [Paragraph('IGV (18%):', s_lbl_g), Paragraph(f'{sym} {float(o.igv):,.2f}', s_val_g)],
            [Paragraph('<b>TOTAL:</b>', s_lbl_b),
             Paragraph(f'<b>{sym} {float(o.total):,.2f}</b>', s_val_b)],
        ]

        tot_t = Table(tot_rows, colWidths=[100, tot_w - 100])
        tot_t.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ('GRID',          (0, 0), (-1, -1), 0.5, self.BORDER),
            ('BACKGROUND',    (0, -1), (-1, -1), self.ROW_ALT),
        ]))

        main = Table([['', tot_t]], colWidths=[W - tot_w, tot_w])
        main.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        return main

    # ── condiciones de entrega ──
    def _delivery_section(self):
        W = PAGE_W - 2 * MARGIN
        o = self.orden

        fecha_str = o.fecha_entrega.strftime('%d/%m/%Y') if o.fecha_entrega else '—'
        hoy = datetime.now().date()
        try:
            delta = (o.fecha_entrega - hoy).days
            dias  = f'{delta}' if delta >= 0 else '—'
        except Exception:
            dias = '—'

        text = (
            f'Entrega estimada en un plazo de <b>{dias}</b> días calendario '
            f'(fecha estimada: <b>{fecha_str}</b>), '
            f'sujeto a disponibilidad y tiempos de tránsito internacional.'
        )
        style = ParagraphStyle('oc_del', fontSize=7.5, textColor=self.DARK, leading=11)
        rows = [[Paragraph(text, style)]]
        t = Table(rows, colWidths=[W])
        t.setStyle(self._box_style())
        return t

    # ── observaciones ──
    def _notes_section(self):
        W = PAGE_W - 2 * MARGIN
        style = ParagraphStyle('oc_note', fontSize=7.5, textColor=self.DARK, leading=10)
        rows  = [[Paragraph(self.orden.notas, style)]]
        t = Table(rows, colWidths=[W])
        t.setStyle(self._box_style())
        return t

    # ── sección de autorizaciones ──
    def _firma_section(self):
        W    = PAGE_W - 2 * MARGIN
        half = W / 2

        nombre_firma = self._nombre_firma()
        cargo_firma  = self._cargo_firma()

        lbl_s   = ParagraphStyle('oc_fl',  fontSize=8, textColor=self.GRAY, alignment=TA_CENTER)
        name_s  = ParagraphStyle('oc_fn',  fontSize=8, fontName='Helvetica-Bold',
                                 textColor=self.DARK, alignment=TA_CENTER)
        line_s  = ParagraphStyle('oc_fli', fontSize=7.5, textColor=self.GRAY, alignment=TA_CENTER)
        cargo_s = ParagraphStyle('oc_fc',  fontSize=7.5, textColor=self.GRAY, alignment=TA_CENTER)

        # Fix 1: usar firma_elaborado (izq) y firma_aprobado (der) de la empresa
        firma_elab  = self._firma_image('firma_elaborado', width=90, height=35)
        firma_aprob = self._firma_image('firma_aprobado',  width=90, height=35)

        def _col(firma_img, label_footer):
            col = []
            col.append(firma_img if firma_img else Spacer(1, 35))
            col.append(Paragraph(nombre_firma, name_s))
            col.append(Paragraph(cargo_firma, cargo_s))
            col.append(Spacer(1, 6))
            col.append(Paragraph('_' * 38, line_s))
            col.append(Paragraph(label_footer, lbl_s))
            return col

        left_items  = _col(firma_elab,  'Preparada por')
        right_items = _col(firma_aprob, 'Aprobada por')

        def _cell(items):
            rows = [[item] for item in items]
            t = Table(rows, colWidths=[half - 20])
            t.setStyle(TableStyle([
                ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING',    (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            return t

        outer = Table([[_cell(left_items), _cell(right_items)]], colWidths=[half, half])
        outer.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
        ]))
        return outer

    # ── helpers ──
    def _logo_image(self, width=130, height=60):
        if self.empresa.logo:
            try:
                path = self.empresa.logo.path
                if os.path.exists(path):
                    return Image(path, width=width, height=height, kind='proportional')
            except Exception:
                pass
        return None

    def _firma_image(self, field_name, width=90, height=35):
        """Carga firma_elaborado o firma_aprobado de la empresa."""
        campo = getattr(self.empresa, field_name, None)
        if campo:
            try:
                path = campo.path
                if os.path.exists(path):
                    return Image(path, width=width, height=height, kind='proportional')
            except Exception:
                pass
        return None

    def _lv(self, label, value):
        return Paragraph(
            f'<b>{label}:</b> {value or "—"}',
            ParagraphStyle('oc_lv', fontSize=7.5, textColor=self.DARK, leading=10),
        )

    def _box_style(self):
        return TableStyle([
            ('BOX',           (0, 0), (-1, -1), 0.5, self.BORDER),
            ('INNERGRID',     (0, 0), (-1, -1), 0.5, self.BORDER),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ])
