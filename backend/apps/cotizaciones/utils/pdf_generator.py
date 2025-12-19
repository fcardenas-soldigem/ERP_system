"""
Generador de PDF profesional y elegante para cotizaciones
"""
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image, PageBreak, Frame, PageTemplate
)
from reportlab.pdfgen import canvas
from django.conf import settings
import os
from datetime import datetime


class CotizacionPDFGenerator:
    """
    Generador de PDF profesional para cotizaciones
    """
    
    # Colores corporativos elegantes
    COLOR_PRIMARY = colors.HexColor('#2C3E50')      # Azul oscuro elegante
    COLOR_SECONDARY = colors.HexColor('#3498DB')    # Azul corporativo
    COLOR_ACCENT = colors.HexColor('#E74C3C')       # Rojo para destacar
    COLOR_SUCCESS = colors.HexColor('#27AE60')      # Verde para totales
    COLOR_LIGHT_GRAY = colors.HexColor('#ECF0F1')  # Gris claro para fondos
    COLOR_DARK_GRAY = colors.HexColor('#7F8C8D')   # Gris oscuro para texto secundario
    COLOR_WHITE = colors.white
    
    def __init__(self, cotizacion):
        self.cotizacion = cotizacion
        self.buffer = BytesIO()
        self.width, self.height = A4
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """
        Configurar estilos personalizados para el PDF
        """
        # Estilo para título principal
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.COLOR_PRIMARY,
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Estilo para subtítulos
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.COLOR_PRIMARY,
            spaceAfter=8,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
        
        # Estilo para texto normal
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.COLOR_PRIMARY,
            alignment=TA_JUSTIFY,
            spaceAfter=6
        ))
        
        # Estilo para información destacada
        self.styles.add(ParagraphStyle(
            name='Highlight',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=self.COLOR_SECONDARY,
            fontName='Helvetica-Bold',
            spaceAfter=4
        ))
        
        # Estilo para notas y observaciones
        self.styles.add(ParagraphStyle(
            name='Notes',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=self.COLOR_DARK_GRAY,
            alignment=TA_JUSTIFY,
            leftIndent=10,
            rightIndent=10
        ))
    
    def _draw_header(self, canvas, doc):
        """
        Dibujar encabezado profesional en cada página
        """
        canvas.saveState()
        
        # Línea superior decorativa
        canvas.setStrokeColor(self.COLOR_SECONDARY)
        canvas.setLineWidth(3)
        canvas.line(30, self.height - 30, self.width - 30, self.height - 30)
        
        # Logo de la empresa (si existe)
        empresa = self.cotizacion.empresa
        if empresa.logo:
            try:
                logo_path = os.path.join(settings.MEDIA_ROOT, str(empresa.logo))
                if os.path.exists(logo_path):
                    img = Image(logo_path, width=2*inch, height=1*inch, kind='proportional')
                    img.drawOn(canvas, 40, self.height - 120)
            except Exception as e:
                print(f"Error cargando logo: {e}")
        
        # Información de la empresa (lado derecho)
        canvas.setFont('Helvetica-Bold', 12)
        canvas.setFillColor(self.COLOR_PRIMARY)
        canvas.drawRightString(self.width - 40, self.height - 50, empresa.nombre)
        
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(self.COLOR_DARK_GRAY)
        y_pos = self.height - 65
        
        if empresa.ruc:
            canvas.drawRightString(self.width - 40, y_pos, f"RUC: {empresa.ruc}")
            y_pos -= 12
        
        if empresa.direccion:
            canvas.drawRightString(self.width - 40, y_pos, empresa.direccion)
            y_pos -= 12
        
        if empresa.telefono:
            canvas.drawRightString(self.width - 40, y_pos, f"Tel: {empresa.telefono}")
            y_pos -= 12
        
        if empresa.email:
            canvas.drawRightString(self.width - 40, y_pos, empresa.email)
        
        canvas.restoreState()
    
    def _draw_footer(self, canvas, doc):
        """
        Dibujar pie de página elegante
        """
        canvas.saveState()
        
        # Línea inferior decorativa
        canvas.setStrokeColor(self.COLOR_LIGHT_GRAY)
        canvas.setLineWidth(1)
        canvas.line(30, 50, self.width - 30, 50)
        
        # Texto del pie de página
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(self.COLOR_DARK_GRAY)
        
        footer_text = f"Cotización {self.cotizacion.numero} | Página {doc.page}"
        canvas.drawCentredString(self.width / 2, 35, footer_text)
        
        # Fecha de generación
        fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M")
        canvas.drawRightString(self.width - 40, 35, f"Generado: {fecha_generacion}")
        
        canvas.restoreState()
    
    def generar_pdf(self):
        """
        Generar el PDF completo de la cotización
        """
        # Crear documento
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=140,
            bottomMargin=70
        )
        
        # Contenido del documento
        story = []
        
        # Título de la cotización
        story.append(Spacer(1, 0.3*inch))
        titulo = Paragraph(
            f"<b>COTIZACIÓN</b><br/>{self.cotizacion.numero}",
            self.styles['CustomTitle']
        )
        story.append(titulo)
        story.append(Spacer(1, 0.2*inch))
        
        # Información del cliente y fechas
        story.extend(self._crear_seccion_cliente())
        story.append(Spacer(1, 0.2*inch))
        
        # Asunto
        if self.cotizacion.asunto:
            asunto = Paragraph(
                f"<b>Asunto:</b> {self.cotizacion.asunto}",
                self.styles['Highlight']
            )
            story.append(asunto)
            story.append(Spacer(1, 0.1*inch))
        
        # Descripción
        if self.cotizacion.descripcion:
            descripcion = Paragraph(
                self.cotizacion.descripcion,
                self.styles['CustomBody']
            )
            story.append(descripcion)
            story.append(Spacer(1, 0.2*inch))
        
        # Tabla de productos/servicios
        story.extend(self._crear_tabla_productos())
        story.append(Spacer(1, 0.2*inch))
        
        # Tabla de totales
        story.extend(self._crear_tabla_totales())
        story.append(Spacer(1, 0.3*inch))
        
        # Condiciones comerciales
        story.extend(self._crear_condiciones_comerciales())
        
        # Notas y términos
        if self.cotizacion.notas or self.cotizacion.terminos_condiciones:
            story.append(Spacer(1, 0.2*inch))
            story.extend(self._crear_notas_terminos())
        
        # Firma
        story.append(Spacer(1, 0.5*inch))
        story.extend(self._crear_seccion_firma())
        
        # Construir PDF
        doc.build(
            story,
            onFirstPage=self._draw_header,
            onLaterPages=self._draw_header,
            canvasmaker=lambda *args, **kwargs: self._custom_canvas(*args, **kwargs)
        )
        
        self.buffer.seek(0)
        return self.buffer
    
    def _custom_canvas(self, *args, **kwargs):
        """
        Canvas personalizado con pie de página
        """
        c = canvas.Canvas(*args, **kwargs)
        original_showPage = c.showPage
        
        def custom_showPage():
            self._draw_footer(c, args[0] if args else None)
            original_showPage()
        
        c.showPage = custom_showPage
        return c
    
    def _crear_seccion_cliente(self):
        """
        Crear sección con información del cliente y fechas
        """
        elements = []
        cliente = self.cotizacion.cliente
        
        # Datos en dos columnas
        data = [
            ['CLIENTE', 'FECHAS'],
            [
                Paragraph(f"<b>{cliente.nombre}</b>", self.styles['CustomBody']),
                Paragraph(
                    f"<b>Emisión:</b> {self.cotizacion.fecha_emision.strftime('%d/%m/%Y')}",
                    self.styles['CustomBody']
                )
            ],
            [
                Paragraph(
                    f"<b>{cliente.get_tipo_documento_display()}:</b> {cliente.documento}",
                    self.styles['CustomBody']
                ),
                Paragraph(
                    f"<b>Vencimiento:</b> {self.cotizacion.fecha_vencimiento.strftime('%d/%m/%Y')}",
                    self.styles['CustomBody']
                )
            ],
        ]
        
        if cliente.direccion:
            data.append([
                Paragraph(f"<b>Dirección:</b> {cliente.direccion}", self.styles['CustomBody']),
                Paragraph(f"<b>Validez:</b> {self.cotizacion.validez_oferta}", self.styles['CustomBody'])
            ])
        
        if cliente.telefono or cliente.email:
            contacto = []
            if cliente.telefono:
                contacto.append(f"Tel: {cliente.telefono}")
            if cliente.email:
                contacto.append(f"Email: {cliente.email}")
            data.append([
                Paragraph(" | ".join(contacto), self.styles['CustomBody']),
                ''
            ])
        
        table = Table(data, colWidths=[3.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            # Encabezados
            ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.COLOR_WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            
            # Contenido
            ('BACKGROUND', (0, 1), (-1, -1), self.COLOR_WHITE),
            ('TEXTCOLOR', (0, 1), (-1, -1), self.COLOR_PRIMARY),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            
            # Bordes
            ('BOX', (0, 0), (-1, -1), 1, self.COLOR_LIGHT_GRAY),
            ('LINEBELOW', (0, 0), (-1, 0), 2, self.COLOR_SECONDARY),
            ('GRID', (0, 1), (-1, -1), 0.5, self.COLOR_LIGHT_GRAY),
        ]))
        
        elements.append(table)
        return elements
    
    def _crear_tabla_productos(self):
        """
        Crear tabla elegante de productos/servicios
        """
        elements = []
        
        # Encabezado
        heading = Paragraph("<b>DETALLE DE PRODUCTOS/SERVICIOS</b>", self.styles['CustomHeading'])
        elements.append(heading)
        elements.append(Spacer(1, 0.1*inch))
        
        # Datos de la tabla
        data = [
            ['#', 'Código', 'Descripción', 'Cant.', 'P. Unit.', 'Subtotal']
        ]
        
        simbolo_moneda = 'S/' if self.cotizacion.moneda == 'PEN' else '$'
        
        for idx, detalle in enumerate(self.cotizacion.detalles.all(), 1):
            data.append([
                str(idx),
                detalle.codigo or '-',
                Paragraph(detalle.descripcion, self.styles['CustomBody']),
                f"{detalle.cantidad:.2f}",
                f"{simbolo_moneda} {detalle.precio_unitario:.2f}",
                f"{simbolo_moneda} {detalle.subtotal:.2f}"
            ])
        
        # Crear tabla
        table = Table(
            data,
            colWidths=[0.4*inch, 1*inch, 3*inch, 0.7*inch, 1*inch, 1.1*inch]
        )
        
        table.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.COLOR_WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Contenido
            ('BACKGROUND', (0, 1), (-1, -1), self.COLOR_WHITE),
            ('TEXTCOLOR', (0, 1), (-1, -1), self.COLOR_PRIMARY),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Número
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Código
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),    # Descripción
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Cantidad
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),  # Precios
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            
            # Bordes
            ('BOX', (0, 0), (-1, -1), 1.5, self.COLOR_PRIMARY),
            ('LINEBELOW', (0, 0), (-1, 0), 2, self.COLOR_SECONDARY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [self.COLOR_WHITE, self.COLOR_LIGHT_GRAY]),
            ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_LIGHT_GRAY),
        ]))
        
        elements.append(table)
        return elements
    
    def _crear_tabla_totales(self):
        """
        Crear tabla de totales elegante
        """
        elements = []
        simbolo_moneda = 'S/' if self.cotizacion.moneda == 'PEN' else '$'
        
        data = []
        
        # Subtotal
        data.append([
            Paragraph('<b>Subtotal:</b>', self.styles['CustomBody']),
            Paragraph(f'<b>{simbolo_moneda} {self.cotizacion.subtotal:.2f}</b>', self.styles['CustomBody'])
        ])
        
        # Descuento (si aplica)
        if self.cotizacion.descuento > 0:
            data.append([
                Paragraph('<b>Descuento:</b>', self.styles['CustomBody']),
                Paragraph(
                    f'<b>- {simbolo_moneda} {self.cotizacion.descuento:.2f}</b>',
                    self.styles['CustomBody']
                )
            ])
        
        # IGV (si aplica)
        if self.cotizacion.incluye_igv:
            data.append([
                Paragraph(f'<b>IGV ({self.cotizacion.porcentaje_igv}%):</b>', self.styles['CustomBody']),
                Paragraph(f'<b>{simbolo_moneda} {self.cotizacion.igv:.2f}</b>', self.styles['CustomBody'])
            ])
        
        # Total
        data.append([
            Paragraph('<b>TOTAL:</b>', self.styles['Highlight']),
            Paragraph(
                f'<b>{simbolo_moneda} {self.cotizacion.total:.2f}</b>',
                self.styles['Highlight']
            )
        ])
        
        table = Table(data, colWidths=[4.5*inch, 1.7*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            
            # Destacar total
            ('BACKGROUND', (0, -1), (-1, -1), self.COLOR_SUCCESS),
            ('TEXTCOLOR', (0, -1), (-1, -1), self.COLOR_WHITE),
            ('FONTSIZE', (0, -1), (-1, -1), 13),
            
            # Bordes
            ('BOX', (0, 0), (-1, -1), 1, self.COLOR_LIGHT_GRAY),
            ('LINEABOVE', (0, -1), (-1, -1), 2, self.COLOR_SUCCESS),
        ]))
        
        elements.append(table)
        return elements
    
    def _crear_condiciones_comerciales(self):
        """
        Crear sección de condiciones comerciales (Condiciones de Compra)
        """
        elements = []
        
        heading = Paragraph("<b>CONDICIONES DE COMPRA</b>", self.styles['CustomHeading'])
        elements.append(heading)
        elements.append(Spacer(1, 0.1*inch))
        
        data = []
        
        if self.cotizacion.forma_pago:
            data.append([
                Paragraph('<b>Forma de Pago:</b>', self.styles['CustomBody']),
                Paragraph(self.cotizacion.forma_pago, self.styles['CustomBody'])
            ])
        
        if self.cotizacion.pago_facturas:
            data.append([
                Paragraph('<b>Pago de Facturas:</b>', self.styles['CustomBody']),
                Paragraph(self.cotizacion.pago_facturas, self.styles['CustomBody'])
            ])
        
        if self.cotizacion.fecha_vencimiento:
            fecha_entrega = self.cotizacion.fecha_vencimiento.strftime('%d/%m/%Y')
            data.append([
                Paragraph('<b>Fecha de Entrega:</b>', self.styles['CustomBody']),
                Paragraph(fecha_entrega, self.styles['CustomBody'])
            ])
        
        if self.cotizacion.lugar_entrega:
            data.append([
                Paragraph('<b>Lugar de Entrega:</b>', self.styles['CustomBody']),
                Paragraph(self.cotizacion.lugar_entrega, self.styles['CustomBody'])
            ])
        
        if data:
            table = Table(data, colWidths=[2*inch, 4.2*inch])
            table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, self.COLOR_LIGHT_GRAY),
            ]))
            elements.append(table)
        
        return elements
    
    def _crear_notas_terminos(self):
        """
        Crear sección de notas y términos
        """
        elements = []
        
        if self.cotizacion.notas:
            heading = Paragraph("<b>NOTAS:</b>", self.styles['CustomHeading'])
            elements.append(heading)
            notas = Paragraph(self.cotizacion.notas, self.styles['Notes'])
            elements.append(notas)
            elements.append(Spacer(1, 0.1*inch))
        
        if self.cotizacion.terminos_condiciones:
            heading = Paragraph("<b>TÉRMINOS Y CONDICIONES:</b>", self.styles['CustomHeading'])
            elements.append(heading)
            terminos = Paragraph(self.cotizacion.terminos_condiciones, self.styles['Notes'])
            elements.append(terminos)
        
        return elements
    
    def _crear_seccion_firma(self):
        """
        Crear sección de firma
        """
        elements = []
        
        # Línea para firma
        data = [
            ['', ''],
            ['_' * 40, '_' * 40],
            [
                Paragraph('<b>Firma y Sello</b>', self.styles['CustomBody']),
                Paragraph('<b>Fecha</b>', self.styles['CustomBody'])
            ]
        ]
        
        table = Table(data, colWidths=[3*inch, 3*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('TOPPADDING', (0, 0), (-1, -1), 20),
        ]))
        
        elements.append(table)
        return elements

