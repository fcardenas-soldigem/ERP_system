from io import BytesIO
import os
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, KeepTogether,
)

# ── Palette ──────────────────────────────────────────────────────────────────
NAVY       = colors.HexColor('#1B2A4A')
BLUE       = colors.HexColor('#2563EB')
BLUE_LIGHT = colors.HexColor('#EFF6FF')
GRAY_50    = colors.HexColor('#F9FAFB')
GRAY_200   = colors.HexColor('#E5E7EB')
GRAY_300   = colors.HexColor('#D1D5DB')
GRAY_500   = colors.HexColor('#6B7280')
GRAY_700   = colors.HexColor('#374151')
GRAY_900   = colors.HexColor('#111827')
WHITE      = colors.white

PAGE_W, PAGE_H = A4
MARGIN    = 1.6 * cm
CONTENT_W = PAGE_W - 2 * MARGIN

MOTIVO_LABELS = {
    'ingreso_reparacion': 'Ingreso por Reparación',
    'devolucion_cliente': 'Devolución a Cliente',
    'traslado_tecnico':   'Traslado Técnico',
    'otro':               'Otro',
}


# ── Styles ───────────────────────────────────────────────────────────────────
def _s(name, size=8, bold=False, color=GRAY_900, align=TA_LEFT, leading=None, space_after=0):
    return ParagraphStyle(
        name,
        fontName='Helvetica-Bold' if bold else 'Helvetica',
        fontSize=size,
        textColor=color,
        alignment=align,
        leading=leading or size + 3,
        spaceAfter=space_after,
    )


# ── Main class ───────────────────────────────────────────────────────────────
class GuiaRemisionPDF:

    def __init__(self, guia):
        self.guia    = guia
        self.empresa = guia.empresa
        self.buffer  = BytesIO()

    def generar(self):
        doc = SimpleDocTemplate(
            self.buffer, pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=MARGIN + 12,
        )
        doc.build(self._story(), onFirstPage=self._footer, onLaterPages=self._footer)
        self.buffer.seek(0)
        return self.buffer

    @staticmethod
    def nombre_archivo(guia):
        cliente = re.sub(r'[^\w\s-]', '', guia.nombre_destinatario).strip()
        cliente = re.sub(r'\s+', '_', cliente)[:30]
        fecha   = guia.fecha_emision.strftime('%Y%m%d')
        return f"{guia.numero}_{cliente}_{fecha}.pdf"

    # ── Footer ───────────────────────────────────────────────────────────────
    def _footer(self, canvas, doc):
        canvas.saveState()
        y = 14
        canvas.setStrokeColor(GRAY_200)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, y + 10, PAGE_W - MARGIN, y + 10)

        canvas.setFont('Helvetica', 6)
        canvas.setFillColor(GRAY_500)
        canvas.drawString(MARGIN, y, self.guia.numero)

        now = datetime.now().strftime('%d/%m/%Y %H:%M')
        canvas.drawCentredString(
            PAGE_W / 2, y,
            f'Documento de control interno  ·  {self.empresa.nombre}  ·  {now}',
        )
        canvas.drawRightString(PAGE_W - MARGIN, y, f'Pág. {canvas.getPageNumber()}')
        canvas.restoreState()

    # ── Story ────────────────────────────────────────────────────────────────
    def _story(self):
        g = self.guia
        story = []
        story.append(self._header())
        story.append(Spacer(1, 10))
        story.append(self._info_block())
        story.append(Spacer(1, 10))
        seccion = 'PRODUCTOS A TRANSPORTAR' if g.tipo == 'venta' else 'EQUIPOS A TRANSPORTAR'
        story.append(self._section_title(seccion))
        story.append(Spacer(1, 2))
        equipos = self._tabla_equipos()
        if isinstance(equipos, list):
            story.extend(equipos)
        else:
            story.append(equipos)
        story.append(Spacer(1, 16))

        if g.observaciones:
            story.append(self._observaciones())
            story.append(Spacer(1, 16))

        story.append(self._firmas())
        return story

    # ── Header ───────────────────────────────────────────────────────────────
    def _header(self):
        e = self.empresa
        left_w  = CONTENT_W * 0.55
        right_w = CONTENT_W * 0.45

        logo_cell = None
        if e.logo:
            try:
                path = e.logo.path
                if os.path.exists(path):
                    logo_cell = Image(path, width=120, height=2.6 * cm, kind='proportional')
            except Exception:
                pass
        if logo_cell is None:
            logo_cell = Paragraph(
                f'<b>{e.nombre}</b>',
                _s('emp', size=14, bold=True, color=NAVY),
            )

        left_data = [
            [logo_cell],
            [Paragraph(f'RUC: {e.ruc or "—"}', _s('ruc', size=7.5, color=GRAY_500))],
            [Paragraph(e.direccion or '', _s('dir', size=7, color=GRAY_500))],
        ]
        left = Table(left_data, colWidths=[left_w])
        left.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ]))

        fecha = self.guia.fecha_emision.strftime('%d/%m/%Y')
        right_data = [
            [Paragraph('<b>GUÍA DE REMISIÓN</b>', _s('t1', size=10, bold=True, color=WHITE, align=TA_CENTER))],
            [Spacer(1, 4)],
            [Paragraph(f'<b>{self.guia.numero}</b>', _s('t2', size=18, bold=True, color=WHITE, align=TA_CENTER))],
            [Spacer(1, 4)],
            [Paragraph(f'Fecha: {fecha}', _s('t3', size=8, color=colors.HexColor('#CBD5E1'), align=TA_CENTER))],
        ]
        right = Table(right_data, colWidths=[right_w - 4])
        right.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), NAVY),
            ('TOPPADDING',    (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
            ('TOPPADDING',    (0, 1), (-1, -2), 0),
            ('BOTTOMPADDING', (0, 1), (-1, -2), 0),
            ('LEFTPADDING',   (0, 0), (-1, -1), 10),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        outer = Table([[left, right]], colWidths=[left_w, right_w])
        outer.setStyle(TableStyle([
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ]))
        return outer

    # ── Section title ────────────────────────────────────────────────────────
    def _section_title(self, text):
        t = Table(
            [[Paragraph(f'<b>{text}</b>', _s('sec', size=8, bold=True, color=NAVY))]],
            colWidths=[CONTENT_W],
        )
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), BLUE_LIGHT),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING',   (0, 0), (-1, -1), 8),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
            ('LINEBELOW',     (0, 0), (-1, -1), 1.5, BLUE),
        ]))
        return t

    # ── Info block (dates + destinatario + addresses in one card) ────────────
    def _info_block(self):
        g = self.guia
        motivo = MOTIVO_LABELS.get(g.motivo, g.motivo)

        if g.cliente and g.cliente.nombre:
            nombre = g.cliente.nombre
        else:
            nombre = g.nombre_destinatario

        half  = CONTENT_W / 2
        third = CONTENT_W / 3
        elements = []

        # Row 1: dates + motivo
        r1 = Table(
            [[self._field_cell('FECHA DE EMISIÓN', g.fecha_emision.strftime('%d/%m/%Y')),
              self._field_cell('FECHA DE TRASLADO', g.fecha_traslado.strftime('%d/%m/%Y')),
              self._field_cell('MOTIVO', motivo)]],
            colWidths=[third, third, third],
        )
        r1.setStyle(self._info_row_style(bottom_line=True))
        elements.append(r1)

        # Row 2: destinatario + RUC
        r2 = Table(
            [[self._field_cell('DESTINATARIO', nombre),
              self._field_cell('RUC / DNI', g.ruc_destinatario or '—')]],
            colWidths=[half, half],
        )
        r2.setStyle(self._info_row_style(bottom_line=True))
        elements.append(r2)

        # Row 3: addresses
        r3 = Table(
            [[self._field_cell('PUNTO DE PARTIDA', g.direccion_origen or '—'),
              self._field_cell('PUNTO DE LLEGADA', g.direccion_destino or '—')]],
            colWidths=[half, half],
        )
        r3.setStyle(self._info_row_style(bottom_line=False))
        elements.append(r3)

        # Wrap in a bordered card
        card = Table([[e] for e in elements], colWidths=[CONTENT_W])
        card.setStyle(TableStyle([
            ('BOX',           (0, 0), (-1, -1), 0.5, GRAY_300),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ]))
        return card

    def _info_row_style(self, bottom_line=True):
        cmds = [
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING',   (0, 0), (-1, -1), 10),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND',    (0, 0), (-1, -1), WHITE),
        ]
        if bottom_line:
            cmds.append(('LINEBELOW', (0, 0), (-1, -1), 0.5, GRAY_200))
        return TableStyle(cmds)

    def _field_cell(self, label, value):
        p = Paragraph(
            f'<font size="6" color="#6B7280">{label}</font><br/>'
            f'<font size="8">{value or "—"}</font>',
            _s(f'fc_{label}', size=8, color=GRAY_900, leading=12),
        )
        return p

    # ── Equipment table ──────────────────────────────────────────────────────
    def _tabla_equipos(self):
        # Column widths must sum exactly to CONTENT_W
        col_n   = 0.8 * cm    # N°
        col_s   = 3.4 * cm    # Serie
        col_m   = 4.0 * cm    # Modelo
        col_b   = 2.0 * cm    # Marca
        col_f   = CONTENT_W - col_n - col_s - col_m - col_b - 1.2 * cm  # Falla (dynamic)
        col_c   = 1.2 * cm    # Cant
        col_w   = [col_n, col_s, col_m, col_b, col_f, col_c]

        hdr_s = _s('th', size=7, bold=True, color=WHITE, align=TA_CENTER)
        col_f_label = 'DESCRIPCIÓN' if self.guia.tipo == 'venta' else 'FALLA / ESTADO'
        headers = ['N°', 'N° SERIE', 'MODELO', 'MARCA', col_f_label, 'CANT.']
        header_row = [Paragraph(h, hdr_s) for h in headers]

        cell_c = _s('tcc', size=7.5, align=TA_CENTER)
        cell_l = _s('tcl', size=7.5)

        data = [header_row]
        total = 0
        for item in self.guia.items.order_by('numero_item'):
            total += item.cantidad
            data.append([
                Paragraph(str(item.numero_item), cell_c),
                Paragraph(item.serie or '—', _s('ser', size=7, color=GRAY_700)),
                Paragraph(item.modelo or '—', cell_l),
                Paragraph(item.marca or '—', cell_l),
                Paragraph(item.estado_ingreso or item.descripcion or '—', cell_l),
                Paragraph(str(item.cantidad), cell_c),
            ])

        style_cmds = [
            ('BACKGROUND',    (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR',     (0, 0), (-1, 0), WHITE),
            ('TOPPADDING',    (0, 0), (-1, 0), 5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
            ('TOPPADDING',    (0, 1), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
            ('LEFTPADDING',   (0, 0), (-1, -1), 5),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX',           (0, 0), (-1, -1), 0.5, GRAY_300),
            ('LINEBELOW',     (0, 0), (-1, 0), 1, BLUE),
        ]
        for i in range(1, len(data)):
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), WHITE if i % 2 == 1 else GRAY_50))
            style_cmds.append(('LINEBELOW', (0, i), (-1, i), 0.25, GRAY_200))

        t = Table(data, colWidths=col_w, repeatRows=1)
        t.setStyle(TableStyle(style_cmds))

        # Total row
        unidad = 'producto' if self.guia.tipo == 'venta' else 'equipo'
        total_p = Paragraph(
            f'<b>Total: {total} {unidad}{"s" if total != 1 else ""}</b>',
            _s('tot', size=8, bold=True, color=NAVY, align=TA_RIGHT),
        )
        total_row = Table([[total_p]], colWidths=[CONTENT_W])
        total_row.setStyle(TableStyle([
            ('TOPPADDING',  (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))

        if len(data) <= 15:
            return KeepTogether([t, total_row])
        return [t, total_row]

    # ── Observaciones ────────────────────────────────────────────────────────
    def _observaciones(self):
        label = Paragraph('<b>OBSERVACIONES</b>', _s('olbl', size=7, bold=True, color=NAVY))
        text  = Paragraph(self.guia.observaciones, _s('otxt', size=8, color=GRAY_700, leading=12))
        t = Table([[label], [text]], colWidths=[CONTENT_W])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (0, 0), BLUE_LIGHT),
            ('BACKGROUND',    (0, 1), (-1, -1), WHITE),
            ('BOX',           (0, 0), (-1, -1), 0.5, GRAY_300),
            ('LINEBELOW',     (0, 0), (0, 0), 0.5, GRAY_200),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING',   (0, 0), (-1, -1), 10),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
        ]))
        return t

    # ── Firmas ───────────────────────────────────────────────────────────────
    def _firmas(self):
        half = (CONTENT_W - 1.5 * cm) / 2
        t = Table(
            [[self._firma_box('ENTREGADO POR', half), self._firma_box('RECIBIDO POR', half)]],
            colWidths=[half, half],
            hAlign='CENTER',
        )
        t.setStyle(TableStyle([
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        return t

    def _firma_box(self, titulo, width):
        title_s = _s('ft', size=8, bold=True, color=NAVY, align=TA_CENTER)
        line_s  = _s('fl', size=7.5, color=GRAY_500, align=TA_CENTER)
        field_s = _s('ff', size=7.5, color=GRAY_700)

        data = [
            [Paragraph(f'<b>{titulo}</b>', title_s)],
            [Spacer(1, 24)],
            [Paragraph('_' * 40, line_s)],
            [Spacer(1, 6)],
            [Paragraph('Nombre: ________________________', field_s)],
            [Paragraph('DNI:       ________________________', field_s)],
            [Paragraph('Fecha:    ________________________', field_s)],
        ]
        t = Table(data, colWidths=[width - 8])
        t.setStyle(TableStyle([
            ('BOX',           (0, 0), (-1, -1), 0.5, GRAY_300),
            ('BACKGROUND',    (0, 0), (0, 0), BLUE_LIGHT),
            ('TOPPADDING',    (0, 0), (0, 0), 6),
            ('BOTTOMPADDING', (0, 0), (0, 0), 6),
            ('TOPPADDING',    (0, 1), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
            ('LEFTPADDING',   (0, 0), (-1, -1), 10),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
        ]))
        return t

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _lv(self, label, value):
        return Paragraph(
            f'<b>{label}:</b> {value or "—"}',
            _s('lv', size=7.5, color=GRAY_900, leading=11),
        )


def generar_pdf_guia(guia):
    return GuiaRemisionPDF(guia).generar()
