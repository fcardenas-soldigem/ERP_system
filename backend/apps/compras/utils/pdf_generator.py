"""
Generador de PDF para Órdenes de Compra — estilo con barras azules y secciones.
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

PRIMARY = colors.HexColor('#2B6CB0')
PRIMARY_LIGHT = colors.HexColor('#EBF8FF')
DARK = colors.HexColor('#1a1a1a')
GRAY = colors.HexColor('#666666')
BORDER = colors.HexColor('#cccccc')
WHITE = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 36


class OrdenCompraPDFGenerator:

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
        canvas_obj.setFillColor(GRAY)
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

    # ───────── reusable bar ─────────
    def _section_bar(self, text):
        data = [[Paragraph(f'<b>{text}</b>',
                           ParagraphStyle('bar', fontName='Helvetica-Bold',
                                          fontSize=9, textColor=WHITE,
                                          leading=12))]]
        t = Table(data, colWidths=[PAGE_W - 2 * MARGIN])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), PRIMARY),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ]))
        return t

    # ───────── header (logo + nro OC) ─────────
    def _header_section(self):
        W = PAGE_W - 2 * MARGIN
        logo_cell = ''
        if self.empresa.logo:
            try:
                logo_path = self.empresa.logo.path
                if os.path.exists(logo_path):
                    logo_cell = Image(logo_path, width=130, height=60, kind='proportional')
            except Exception:
                pass

        fecha_str = self.compra.fecha_emision.strftime('%d/%m/%Y')
        pag_style = ParagraphStyle('hdr_p', fontSize=8, textColor=GRAY, alignment=TA_RIGHT)
        title_style = ParagraphStyle('hdr_t', fontSize=10, fontName='Helvetica-Bold',
                                     textColor=DARK, alignment=TA_RIGHT, spaceBefore=4)
        num_style = ParagraphStyle('hdr_n', fontSize=16, fontName='Helvetica-Bold',
                                   textColor=PRIMARY, alignment=TA_RIGHT)

        right_data = [
            [Paragraph(f'Página 1 de 1', pag_style)],
            [Paragraph(f'Fecha de Emisión: {fecha_str}', pag_style)],
            [Paragraph('Nro Orden de Compra:', title_style)],
            [Paragraph(f'<b>OC-{self.compra.numero}</b>', num_style)],
        ]
        right_table = Table(right_data, colWidths=[W * 0.45])

        data = [[logo_cell, right_table]]
        t = Table(data, colWidths=[W * 0.55, W * 0.45])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        return t

    # ───────── proveedor info ─────────
    def _proveedor_section(self):
        W = PAGE_W - 2 * MARGIN
        half = W / 2
        p = self.proveedor

        if p:
            nombre = p.razon_social or '—'
            ruc = p.ruc or '—'
            direccion = p.direccion or '—'
            telefono = p.telefono or '—'
            email = p.email or '—'
            forma_pago = self._get_forma_pago()
        else:
            nombre = ruc = direccion = telefono = email = '—'
            forma_pago = '—'

        rows = [
            [self._lv('Razón Social', nombre), self._lv('RUC', ruc)],
            [self._lv('Dirección', direccion), self._lv('Forma de Pago', forma_pago)],
            [self._lv('Contacto', telefono), self._lv('Mail', email)],
        ]
        t = Table(rows, colWidths=[half, half])
        t.setStyle(self._box_style())
        return t

    # ───────── company info ─────────
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

    # ───────── conditions header (moneda + término de pago) ─────────
    def _conditions_header(self):
        W = PAGE_W - 2 * MARGIN
        half = W / 2
        moneda_text = 'Dólar Estadounidense' if self.compra.moneda == 'USD' else 'Sol Peruano'
        forma_pago = self._get_forma_pago()

        rows = [
            [self._lv('Moneda', moneda_text),
             self._lv('Término de Pago', forma_pago)],
        ]
        t = Table(rows, colWidths=[half, half])
        t.setStyle(self._box_style())
        return t

    # ───────── items table ─────────
    def _items_table(self, sym):
        W = PAGE_W - 2 * MARGIN

        col_widths = [28, W - 28 - 50 - 40 - 70 - 70, 50, 40, 70, 70]
        header = ['N°', 'Descripción', 'Cantidad', 'U.M.', 'Precio Unit.', 'Importe']

        hdr_style = ParagraphStyle('thdr', fontSize=7, fontName='Helvetica-Bold',
                                   textColor=WHITE, alignment=TA_CENTER)
        header_row = [Paragraph(h, hdr_style) for h in header]

        data = [header_row]
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
            um = (getattr(producto, 'unidad_medida', 'UND') or 'UND') if producto else 'UND'

            cell_style = ParagraphStyle('cell', fontSize=7.5, fontName='Helvetica',
                                        textColor=DARK)
            cell_right = ParagraphStyle('cellr', fontSize=7.5, fontName='Helvetica',
                                        textColor=DARK, alignment=TA_RIGHT)
            cell_center = ParagraphStyle('cellc', fontSize=7.5, fontName='Helvetica',
                                         textColor=DARK, alignment=TA_CENTER)

            data.append([
                Paragraph(str(idx), cell_center),
                Paragraph(desc, cell_style),
                Paragraph(qty, cell_center),
                Paragraph(um, cell_center),
                Paragraph(f'{sym} {d.precio_unitario:,.2f}', cell_right),
                Paragraph(f'{sym} {d.subtotal:,.2f}', cell_right),
            ])

        t = Table(data, colWidths=col_widths, repeatRows=1)
        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('TOPPADDING', (0, 0), (-1, 0), 5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ]
        for i in range(1, len(data)):
            bg = WHITE if i % 2 == 1 else PRIMARY_LIGHT
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg))

        t.setStyle(TableStyle(style_cmds))
        return t

    # ───────── totals ─────────
    def _totals_section(self, sym):
        W = PAGE_W - 2 * MARGIN
        obs_w = W - 180
        tot_w = 180

        s_lbl = ParagraphStyle('tlbl', fontSize=8, fontName='Helvetica', textColor=DARK)
        s_val = ParagraphStyle('tval', fontSize=8, fontName='Helvetica', textColor=DARK,
                               alignment=TA_RIGHT)
        s_lbl_b = ParagraphStyle('tlblb', fontSize=9, fontName='Helvetica-Bold',
                                 textColor=DARK)
        s_val_b = ParagraphStyle('tvalb', fontSize=9, fontName='Helvetica-Bold',
                                 textColor=DARK, alignment=TA_RIGHT)
        s_lbl_g = ParagraphStyle('tlblg', fontSize=8, fontName='Helvetica',
                                 textColor=colors.HexColor('#555555'))
        s_val_g = ParagraphStyle('tvalg', fontSize=8, fontName='Helvetica',
                                 textColor=colors.HexColor('#555555'), alignment=TA_RIGHT)

        c = self.compra
        precios_con_igv = getattr(c, 'igv_incluido', False)

        lbl_subtotal = 'Sub Total (c/IGV):' if precios_con_igv else 'Sub Total:'
        tot_rows = [
            [Paragraph(lbl_subtotal, s_lbl), Paragraph(f'{sym} {c.subtotal:,.2f}', s_val)],
        ]

        descuento = getattr(c, 'descuento', None)
        if descuento and descuento > 0:
            tot_rows.append([
                Paragraph('Descuento:', s_lbl),
                Paragraph(f'- {sym} {descuento:,.2f}', s_val)
            ])
            subtotal_neto = float(c.subtotal) - float(descuento)
            tot_rows.append([
                Paragraph('Subtotal neto:', s_lbl_g),
                Paragraph(f'{sym} {subtotal_neto:,.2f}', s_val_g)
            ])

        if precios_con_igv:
            base_imp = float(c.total) - float(c.igv) if c.total else float(c.subtotal) - float(c.igv)
            tot_rows.append([
                Paragraph('Base imponible:', s_lbl_g),
                Paragraph(f'{sym} {base_imp:,.2f}', s_val_g)
            ])
            tot_rows.append([
                Paragraph('IGV 18% (incluido):', s_lbl),
                Paragraph(f'{sym} {c.igv:,.2f}', s_val)
            ])
        else:
            if c.igv and c.igv > 0:
                tot_rows.append([
                    Paragraph('IGV (18%):', s_lbl),
                    Paragraph(f'{sym} {c.igv:,.2f}', s_val)
                ])

        tot_rows.append([
            Paragraph('Total:', s_lbl_b),
            Paragraph(f'{sym} {c.total:,.2f}', s_val_b)
        ])

        tot_table = Table(tot_rows, colWidths=[90, tot_w - 90])
        tot_style = [
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
            ('BACKGROUND', (0, -1), (-1, -1), PRIMARY_LIGHT),
        ]
        tot_table.setStyle(TableStyle(tot_style))

        main = Table([['', tot_table]], colWidths=[obs_w, tot_w])
        main.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        return main

    # ───────── notes ─────────
    def _notes_section(self):
        W = PAGE_W - 2 * MARGIN
        style = ParagraphStyle('note', fontSize=7.5, textColor=DARK, leading=10)
        rows = [[Paragraph(self.compra.notas, style)]]
        t = Table(rows, colWidths=[W])
        t.setStyle(self._box_style())
        return t

    # ───────── firma ─────────
    def _firma_section(self):
        W = PAGE_W - 2 * MARGIN
        half = W / 2

        lbl_style = ParagraphStyle('flbl', fontSize=8, textColor=GRAY, alignment=TA_CENTER)
        name_style = ParagraphStyle('fname', fontSize=8, fontName='Helvetica-Bold',
                                    textColor=DARK, alignment=TA_CENTER)
        line_style = ParagraphStyle('fline', fontSize=7.5, textColor=GRAY, alignment=TA_CENTER)

        data = [
            [Spacer(1, 40), Spacer(1, 40)],
            [Paragraph('_' * 35, line_style), Paragraph('_' * 35, line_style)],
            [Paragraph('Firma Autorizada', lbl_style), Paragraph('Sello Proveedor', lbl_style)],
            [Paragraph(self.empresa.nombre, name_style), ''],
        ]
        t = Table(data, colWidths=[half, half])
        t.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        return t

    # ───────── helpers ─────────
    def _lv(self, label, value):
        style = ParagraphStyle('lv', fontSize=7.5, textColor=DARK, leading=10)
        return Paragraph(f'<b>{label}:</b> {value or "—"}', style)

    def _box_style(self):
        return TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])

    def _get_forma_pago(self):
        if hasattr(self.compra, 'TIPO_COMPRA_CHOICES') and self.compra.tipo_compra:
            return dict(self.compra.TIPO_COMPRA_CHOICES).get(
                self.compra.tipo_compra, self.compra.tipo_compra
            )
        return '—'
