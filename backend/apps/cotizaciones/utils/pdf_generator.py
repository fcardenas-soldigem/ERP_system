"""
Generador de PDF corporativo para cotizaciones — estilo OC (azul, barras, firmas).
Utiliza ReportLab para generar un PDF con layout tipo orden de compra bancaria.
"""
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm, mm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image, KeepTogether,
)
from reportlab.pdfgen import canvas
from django.conf import settings
import os
from datetime import datetime


PRIMARY = colors.HexColor('#2B6CB0')
PRIMARY_LIGHT = colors.HexColor('#EBF8FF')
DARK = colors.HexColor('#1a1a1a')
GRAY = colors.HexColor('#666666')
BORDER = colors.HexColor('#cccccc')
WHITE = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 36


class CotizacionPDFGenerator:
    
    def __init__(self, cotizacion):
        self.cotizacion = cotizacion
        self.empresa = cotizacion.empresa
        self.cliente = cotizacion.cliente
        self.buffer = BytesIO()
        self.styles = getSampleStyleSheet()

    # ───────── public ─────────
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
    
    # ───────── page decoration ─────────
    def _page_decor(self, canvas_obj, doc):
        canvas_obj.saveState()
        canvas_obj.setFont('Helvetica', 7)
        canvas_obj.setFillColor(GRAY)
        canvas_obj.drawString(MARGIN, 20, f'{self.cotizacion.numero}')
        canvas_obj.drawRightString(PAGE_W - MARGIN, 20,
                                   datetime.now().strftime('%d/%m/%Y %H:%M'))
        canvas_obj.drawCentredString(PAGE_W / 2, 20,
                                     f'Página {canvas_obj.getPageNumber()}')
        canvas_obj.restoreState()

    # ───────── story builder ─────────
    def _build_story(self):
        sym = 'S/' if self.cotizacion.moneda == 'PEN' else '$'
        story = []

        story.append(self._header_section())
        story.append(Spacer(1, 6))
        story.append(self._section_bar('DATOS DEL CLIENTE'))
        story.append(self._client_section())
        story.append(Spacer(1, 2))
        story.append(self._section_bar('DATOS DE LA COMPAÑÍA'))
        story.append(self._company_section())
        story.append(Spacer(1, 2))
        story.append(self._section_bar('CONDICIONES COMERCIALES'))
        story.append(self._conditions_section())
        story.append(Spacer(1, 2))
        story.append(self._section_bar('DETALLE DE PRODUCTOS / SERVICIOS'))
        story.append(self._items_table(sym))
        story.append(self._totals_section(sym))
        story.append(Spacer(1, 4))

        if self.cotizacion.tiempo_entrega or self.cotizacion.lugar_entrega:
            story.append(self._section_bar('ENTREGA'))
            story.append(self._delivery_section())
            story.append(Spacer(1, 2))

        if self.cotizacion.notas:
            story.append(self._section_bar('NOTAS / OBSERVACIONES'))
            story.append(self._notes_section())
            story.append(Spacer(1, 2))

        if self.cotizacion.terminos_condiciones:
            story.append(self._section_bar('TÉRMINOS Y CONDICIONES'))
            story.append(self._terms_section())
            story.append(Spacer(1, 2))

        story.append(Spacer(1, 20))
        story.append(self._closing_section())

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

    # ───────── header (logo + nro) ─────────
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

        right_data = [
            [Paragraph(f'Fecha: {self.cotizacion.fecha_emision.strftime("%d/%m/%Y")}',
                        ParagraphStyle('hdr', fontSize=8, textColor=GRAY,
                                       alignment=TA_RIGHT))],
            [Paragraph('Nro Cotización:',
                        ParagraphStyle('hdr2', fontSize=10, fontName='Helvetica-Bold',
                                       textColor=DARK, alignment=TA_RIGHT,
                                       spaceBefore=4))],
            [Paragraph(f'<b>{self.cotizacion.numero}</b>',
                        ParagraphStyle('hdr3', fontSize=16, fontName='Helvetica-Bold',
                                       textColor=PRIMARY, alignment=TA_RIGHT))],
        ]
        right_table = Table(right_data, colWidths=[W * 0.45])

        data = [[logo_cell, right_table]]
        t = Table(data, colWidths=[W * 0.55, W * 0.45])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        return t

    # ───────── client info ─────────
    def _client_section(self):
        W = PAGE_W - 2 * MARGIN
        half = W / 2
        c = self.cliente
        cot = self.cotizacion

        contacto = cot.contacto_nombre or c.telefono or '—'
        email    = cot.contacto_email or c.email or '—'

        rows = [
            [self._lv('Razón Social', c.nombre), self._lv('RUC / Doc.', c.documento)],
            [self._lv('Dirección', c.direccion or '—'), self._lv('Contacto', contacto)],
            [self._lv('Email', email), ''],
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
            [self._lv('Empresa', e.nombre), self._lv('RUC', e.ruc or '—')],
            [self._lv('Dirección', e.direccion or '—'), ''],
        ]
        t = Table(rows, colWidths=[half, half])
        t.setStyle(self._box_style())
        return t

    # ───────── conditions ─────────
    def _conditions_section(self):
        W = PAGE_W - 2 * MARGIN
        cot = self.cotizacion
        moneda_text = 'Dólar Estadounidense' if cot.moneda == 'USD' else 'Sol Peruano'

        rows = [
            [self._lv('Moneda', moneda_text),
             self._lv('Forma de Pago', cot.forma_pago or '—'),
             self._lv('Validez', cot.validez_oferta or '—')],
        ]
        if cot.pago_facturas:
            rows.append([self._lv('Pago Facturas', cot.pago_facturas),
                         self._lv('Válido Hasta', cot.fecha_vencimiento.strftime('%d/%m/%Y') if cot.fecha_vencimiento else '—'),
                         ''])
        t = Table(rows, colWidths=[W / 3] * 3)
        t.setStyle(self._box_style())
        return t

    # ───────── items table ─────────
    def _items_table(self, sym):
        W = PAGE_W - 2 * MARGIN

        col_widths = [28, W - 28 - 55 - 65 - 75, 55, 65, 75]
        header = ['N°', 'Descripción', 'Cant.', 'P. Unit.', 'Importe']

        hdr_style = ParagraphStyle('thdr', fontSize=7, fontName='Helvetica-Bold',
                                   textColor=WHITE, alignment=TA_CENTER)
        header_row = [Paragraph(h, hdr_style) for h in header]

        data = [header_row]
        for idx, d in enumerate(self.cotizacion.detalles.all().order_by('orden'), 1):
            desc = d.descripcion
            if d.codigo:
                desc = f'[{d.codigo}] {desc}'

            qty = f'{d.cantidad:.0f}' if d.cantidad == int(d.cantidad) else f'{d.cantidad:.2f}'

            cell_style = ParagraphStyle('cell', fontSize=7.5, fontName='Helvetica',
                                        textColor=DARK)
            cell_right = ParagraphStyle('cellr', fontSize=7.5, fontName='Helvetica',
                                        textColor=DARK, alignment=TA_RIGHT)

            data.append([
                Paragraph(str(idx), ParagraphStyle('cc', fontSize=7.5, alignment=TA_CENTER,
                                                    textColor=DARK)),
                Paragraph(desc, cell_style),
                Paragraph(qty, ParagraphStyle('ccc', fontSize=7.5, alignment=TA_CENTER,
                                               textColor=DARK)),
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

        obs_cell = ''

        s_lbl = ParagraphStyle('tlbl', fontSize=8, fontName='Helvetica', textColor=DARK)
        s_val = ParagraphStyle('tval', fontSize=8, fontName='Helvetica', textColor=DARK,
                                alignment=TA_RIGHT)
        s_lbl_b = ParagraphStyle('tlblb', fontSize=9, fontName='Helvetica-Bold',
                                  textColor=DARK)
        s_val_b = ParagraphStyle('tvalb', fontSize=9, fontName='Helvetica-Bold',
                                  textColor=DARK, alignment=TA_RIGHT)

        cot = self.cotizacion
        precios_con_igv = getattr(cot, 'precios_incluyen_igv', False)

        lbl_subtotal = 'Sub Total (c/IGV):' if precios_con_igv else 'Sub Total:'
        tot_rows = [
            [Paragraph(lbl_subtotal, s_lbl), Paragraph(f'{sym} {cot.subtotal:,.2f}', s_val)],
        ]

        s_lbl_g = ParagraphStyle('tlblg', fontSize=8, fontName='Helvetica',
                                  textColor=colors.HexColor('#555555'))
        s_val_g = ParagraphStyle('tvalg', fontSize=8, fontName='Helvetica',
                                  textColor=colors.HexColor('#555555'), alignment=TA_RIGHT)

        if cot.descuento and cot.descuento > 0:
            tot_rows.append([
                Paragraph('Descuento:', s_lbl),
                Paragraph(f'- {sym} {cot.descuento:,.2f}', s_val)
            ])
            subtotal_neto = float(cot.subtotal) - float(cot.descuento)
            tot_rows.append([
                Paragraph('Subtotal neto:', s_lbl_g),
                Paragraph(f'{sym} {subtotal_neto:,.2f}', s_val_g)
            ])

        if precios_con_igv:
            # Precios ya incluyen IGV → mostrar base imponible + IGV incluido
            base_imp = float(cot.total) - float(cot.igv) if cot.total else float(cot.subtotal) - float(cot.igv)
            tot_rows.append([
                Paragraph('Base imponible:', s_lbl_g),
                Paragraph(f'{sym} {base_imp:,.2f}', s_val_g)
            ])
            tot_rows.append([
                Paragraph(f'IGV {cot.porcentaje_igv:.0f}% (incluido):', s_lbl),
                Paragraph(f'{sym} {cot.igv:,.2f}', s_val)
            ])
        else:
            tot_rows.append([
                Paragraph(f'IGV ({cot.porcentaje_igv:.0f}%):', s_lbl),
                Paragraph(f'{sym} {cot.igv:,.2f}', s_val)
            ])

        tot_rows.append([
            Paragraph('Total:', s_lbl_b),
            Paragraph(f'{sym} {cot.total:,.2f}', s_val_b)
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

        main = Table([[obs_cell, tot_table]], colWidths=[obs_w, tot_w])
        main.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        return main

    # ───────── delivery ─────────
    def _delivery_section(self):
        W = PAGE_W - 2 * MARGIN
        cot = self.cotizacion
        rows = []
        if cot.tiempo_entrega:
            rows.append([self._lv('Tiempo de Entrega', cot.tiempo_entrega)])
        if cot.lugar_entrega:
            rows.append([self._lv('Lugar de Entrega', cot.lugar_entrega)])
        t = Table(rows, colWidths=[W])
        t.setStyle(self._box_style())
        return t

    # ───────── notes ─────────
    def _notes_section(self):
        W = PAGE_W - 2 * MARGIN
        style = ParagraphStyle('note', fontSize=7.5, textColor=DARK, leading=10)
        rows = [[Paragraph(self.cotizacion.notas, style)]]
        t = Table(rows, colWidths=[W])
        t.setStyle(self._box_style())
        return t

    # ───────── terms ─────────
    def _terms_section(self):
        W = PAGE_W - 2 * MARGIN
        style = ParagraphStyle('term', fontSize=7.5, textColor=DARK, leading=10)
        rows = [[Paragraph(self.cotizacion.terminos_condiciones, style)]]
        t = Table(rows, colWidths=[W])
        t.setStyle(self._box_style())
        return t

    # ───────── closing note ─────────
    def _closing_section(self):
        W = PAGE_W - 2 * MARGIN
        validez = self.cotizacion.validez_oferta or '30 días'
        vencimiento = ''
        if self.cotizacion.fecha_vencimiento:
            vencimiento = f' (válida hasta el {self.cotizacion.fecha_vencimiento.strftime("%d/%m/%Y")})'

        note_style = ParagraphStyle('closing', fontSize=8, textColor=GRAY,
                                     alignment=TA_CENTER, leading=12)
        name_style = ParagraphStyle('closingname', fontSize=9, fontName='Helvetica-Bold',
                                     textColor=DARK, alignment=TA_CENTER)

        data = [
            [Paragraph(
                f'Esta cotización tiene una validez de <b>{validez}</b>{vencimiento}.',
                note_style
            )],
            [Paragraph(self.empresa.nombre, name_style)],
        ]
        t = Table(data, colWidths=[W])
        t.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
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
