import os
from io import BytesIO
from flask import send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Frame, PageTemplate, BaseDocTemplate, NextPageTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from PyPDF2 import PdfReader, PdfWriter

# Registrar fuentes Montserrat
try:
    montserrat_regular_path = os.path.join('fonts', 'Montserrat-Regular.ttf')
    montserrat_bold_path = os.path.join('fonts', 'Montserrat-Bold.ttf')
    pdfmetrics.registerFont(TTFont('Montserrat', montserrat_regular_path))
    pdfmetrics.registerFont(TTFont('Montserrat-Bold', montserrat_bold_path))
    FONT_REGULAR = 'Montserrat'
    FONT_BOLD = 'Montserrat-Bold'
except Exception as e:
    print(f"Error al registrar fuentes Montserrat: {e}")
    FONT_REGULAR = 'Helvetica'
    FONT_BOLD = 'Helvetica-Bold'

def draw_background(canvas, doc, img_path):
    page_width, page_height = letter
    try:
        img_reader = ImageReader(img_path)
        img_width, img_height = img_reader.getSize()
        scale = max(page_width / img_width, page_height / img_height)
        draw_width = img_width * scale
        draw_height = img_height * scale
        x = (page_width - draw_width) / 2
        y = (page_height - draw_height) / 2
        # Ajuste para evitar cortes: asegurar que la imagen cubra toda la página
        canvas.drawImage(img_reader, 0, 0, width=page_width, height=page_height, mask='auto')
    except Exception as e:
        print(f"Error al dibujar fondo: {e} para la imagen {img_path}")

def portada_canvas(canvas, doc, data):
    draw_background(canvas, doc, r'static\pdf_templates\Portada.jpg')
    personalizacion = data.get('personalizacion', {})
    portada_personalizacion = personalizacion.get('portada', {})
    portada_fecha = data.get('fecha', '')
    portada_lugar = data.get('lugar', '')
    portada_num_personas = data.get('num_personas', '')
    portada_tipo_evento = portada_personalizacion.get('titulo_tipo_evento', data.get('tipo_evento', ''))
    portada_nombres = data.get('nombre', '')
    canvas.saveState()
    canvas.setFillColor(colors.white)

    page_width, page_height = letter
    left_margin = 72

    # Posición para el nombre (ajuste final)
    y_nombres = 420

    # Posiciones para los detalles (ajuste final para alinear con iconos)
    x_details = 520
    y_fecha = 730
    y_lugar = 700
    y_personas = 670

    # Tipo de evento (encima del nombre)
    if portada_tipo_evento:
        canvas.setFont(FONT_BOLD, 26)
        canvas.drawString(left_margin, y_nombres + 40, portada_tipo_evento)

    # Nombres
    if portada_nombres:
        canvas.setFont(FONT_BOLD, 36)
        canvas.drawString(left_margin, y_nombres, portada_nombres)

    # Detalles alineados con iconos (a la derecha)
    canvas.setFont(FONT_REGULAR, 12)
    if portada_fecha:
        canvas.drawRightString(x_details, y_fecha, portada_fecha)
    if portada_lugar:
        canvas.drawRightString(x_details, y_lugar, portada_lugar)
    if portada_num_personas:
        canvas.drawRightString(x_details, y_personas, f"{portada_num_personas} personas")

    canvas.restoreState()
def cotizacion_canvas(canvas, doc):
    draw_background(canvas, doc, r'static\pdf_templates\Cotizacion.jpg')
def terminos_canvas(canvas, doc):
    draw_background(canvas, doc, r'static\pdf_templates\Terminos Y Condiciones.jpg')
def generar_pdf(data):
    try:
        buffer = BytesIO()
        doc = BaseDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)

        frame_full = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='full')

        portada_template = PageTemplate(id='portada', frames=[frame_full], onPage=lambda c, d: portada_canvas(c, d, data))
        cotizacion_template = PageTemplate(id='cotizacion', frames=[frame_full], onPage=cotizacion_canvas)
        terminos_template = PageTemplate(id='terminos', frames=[frame_full], onPage=terminos_canvas)

        doc.addPageTemplates([portada_template, cotizacion_template, terminos_template])

        elements = []
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='WhiteTitle', parent=styles['Title'], textColor=colors.white, fontName=FONT_BOLD, alignment=1))
        styles.add(ParagraphStyle(name='WhiteNormal', parent=styles['Normal'], textColor=colors.white, fontName=FONT_REGULAR))
        styles.add(ParagraphStyle(name='WhiteNormalRight', parent=styles['WhiteNormal'], alignment=2))
        styles.add(ParagraphStyle(name='GoldServiceTitle', parent=styles['WhiteNormal'], textColor=colors.HexColor('#FFD700'), fontName=FONT_BOLD, fontSize=18, spaceAfter=4, spaceBefore=16))
        styles.add(ParagraphStyle(name='WhiteServiceDesc', parent=styles['WhiteNormal'], fontSize=14, leftIndent=16, spaceAfter=4))
        styles.add(ParagraphStyle(name='WhitePrice', parent=styles['WhiteNormal'], fontSize=16, alignment=2))
        styles.add(ParagraphStyle(name='TermsStyle', parent=styles['WhiteNormal'], fontSize=14, leading=24, spaceAfter=12))

        # --- Portada ---
        elements.append(NextPageTemplate('cotizacion'))
        elements.append(Spacer(1, 8 * inch))
        elements.append(PageBreak())

        # --- Cotización ---
        servicios_por_tipo = {}
        for item in data.get('cotizacion', []):
            tipo = item.get('servicio', '').strip()
            if tipo:
                servicios_por_tipo.setdefault(tipo, []).append(item)
        num_personas = 0
        try:
            num_personas = int(data.get('num_personas', 0))
            print(f"[DEBUG] num_personas recibido: {data.get('num_personas', 0)} convertido a entero: {num_personas}")
        except Exception as e:
            print(f"[DEBUG] Error convirtiendo num_personas: {e}")
            num_personas = 0
        # Función para obtener descripciones según el número de personas
        # Este diccionario contiene las descripciones base para cada servicio.
        descripciones_base = {
            'DJ': ['- DJ Profesional', '- Repertorio personalizado', '- Cita de logística musical previa al evento'],
            'Pista de baile': ['- Proporcional a {rango} personas'],
            'Barra de bebidas': ['- Pintada a mano con diseño dos colores'],
            'Cabina de DJ': ['- Pintada a mano con diseño dos colores'],
            'Back pintado a mano': ['- Con diseño dos colores'],
        }

        def get_service_description(service_type, num_personas, tipo_evento=''):
            print(f"[DEBUG] get_service_description: {service_type}, num_personas={num_personas}, tipo_evento={tipo_evento}")
            if service_type in descripciones_base:
                if service_type == 'Pista de baile':
                    if num_personas <= 70: rango = 70
                    elif num_personas <= 150: rango = 150
                    elif num_personas <= 250: rango = 250
                    elif num_personas <= 350: rango = 350
                    else: rango = num_personas
                    return [desc.format(rango=rango) for desc in descripciones_base[service_type]]
                return descripciones_base[service_type]

            if service_type == 'Sonido':
                if num_personas <= 70: desc = ['- 2 Bocinas HK 115 FA']
                elif num_personas <= 150: desc = ['- 2 Bocinas HK 115 FA', '- 2 Bajos Audio Center 18"']
                else: desc = ['- 2 Bocinas HK 115 FA', '- 2 Bajos dobles Warfdale 218', '- Técnico de audio profesional']
                if tipo_evento.lower() == 'boda': desc.append('- Bocina para coctel con Bluetooth')
                return desc

            if service_type == 'Iluminación':
                if num_personas <= 70: return ['- A elegir 2 cabezas robóticas 7r o 6 parled']
                if num_personas <= 150: return ['- 2 cabezas robóticas 7r', '- 6 Parled']
                if num_personas <= 250: return ['- 6 cabezas robóticas 7r', '- 12 Parled']
                if num_personas <= 350: return ['- 10 cabezas robóticas 7r', '- 20 Parled']
                return ['- Contactar para cotización']

            return []
        table_data = []
        for tipo, items in servicios_por_tipo.items():
            total_precio_servicio = sum(item.get('precio', 0) for item in items)
            monto_text = format_currency(total_precio_servicio)
            table_data.append([Paragraph(tipo.upper(), styles['GoldServiceTitle']), Paragraph(monto_text, styles['WhitePrice'])])
            table_data.append([Spacer(1, 0.12 * inch), ''])
            desc_list = get_service_description(tipo, num_personas, data.get('tipo_evento', ''))
            for desc in desc_list:
                table_data.append([Paragraph(desc, styles['WhiteServiceDesc']), ''])
            table_data.append([Spacer(1, 0.12 * inch), ''])
            # Desglose de horas extra si aplica
            for item in items:
                horas_extras = item.get('horas_extras', 0)
                extra_total = item.get('extra_total', 0)
                if horas_extras and extra_total:
                    table_data.append([Paragraph(f"Horas extra: {horas_extras}", styles['WhiteServiceDesc']), Paragraph(format_currency(extra_total), styles['WhitePrice'])])
                    table_data.append([Spacer(1, 0.08 * inch), ''])
        def add_simple_items(items, concepto_key, monto_key, is_discount=False):
            for item in items:
                if isinstance(item, dict):
                    concepto_text = item.get(concepto_key, '')
                    monto_val = item.get(monto_key, 0)
                    monto_text = f"-{format_currency(monto_val)}" if is_discount else format_currency(monto_val)
                elif isinstance(item, str):
                    concepto_text = item
                    monto_text = ''
                else:
                    continue
                table_data.append([Paragraph(concepto_text, styles['WhiteServiceDesc']), Paragraph(monto_text, styles['WhitePrice'])])
        add_simple_items(data.get('extras', []), 'concepto', 'monto')
        add_simple_items(data.get('viaticos', []), 'concepto', 'monto')
        add_simple_items(data.get('descuentos', []), 'descripcion', 'monto', is_discount=True)
        table_data.append(['', ''])
        total_text = Paragraph('TOTAL', styles['GoldServiceTitle'])
        total_value = Paragraph(format_currency(data.get('total', 0)), styles['GoldServiceTitle'])
        table_data.append([total_text, total_value])
        cotizacion_table = Table(table_data, colWidths=[doc.width - 120, 100])
        cotizacion_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.white),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(cotizacion_table)

        # --- Términos y Condiciones ---
        personalizacion = data.get('personalizacion', {})
        if personalizacion.get('incluir_terminos', True):
            elements.append(NextPageTemplate('terminos'))
            elements.append(PageBreak())
            
            terminos_titulo = personalizacion.get('terminos_titulo', 'TÉRMINOS Y CONDICIONES')
            # Leer términos desde el archivo markdown si no hay contenido personalizado
            if not personalizacion.get('terminos_contenido'):
                try:
                    with open('docs/terminos_y_condiciones.md', 'r', encoding='utf-8') as f:
                        terminos_contenido = f.read().replace('\n', '<br/>')
                except:
                    terminos_contenido = ''
            else:
                terminos_contenido = personalizacion.get('terminos_contenido', '').replace('\n', '<br/>')
            elements.append(Paragraph(terminos_titulo, styles['WhiteTitle']))
            elements.append(Spacer(1, 0.5 * inch))
            elements.append(Paragraph(terminos_contenido, styles['TermsStyle']))

        doc.build(elements)
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name='Cotizacion.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"Error al generar el PDF: {e}")
        raise e


def format_currency(value):
    try:
        return f"${int(value):,}"
    except (ValueError, TypeError):
        return "$0"