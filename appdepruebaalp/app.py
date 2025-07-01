from flask import Flask, render_template, request, jsonify, send_file
import json
import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
import base64
# Imports para fuentes personalizadas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
# Imports para manejo de imágenes y PDFs
from reportlab.lib.utils import ImageReader
from PyPDF2 import PdfReader, PdfWriter
# Importar el generador de PDF separado
from pdf_generator import generar_pdf

app = Flask(__name__)

# Registrar fuentes Montserrat (asumiendo que los archivos .ttf están en la carpeta 'fonts')
try:
    montserrat_regular_path = os.path.join('fonts', 'Montserrat-Regular.ttf')
    montserrat_bold_path = os.path.join('fonts', 'Montserrat-Bold.ttf')
    pdfmetrics.registerFont(TTFont('Montserrat', montserrat_regular_path))
    pdfmetrics.registerFont(TTFont('Montserrat-Bold', montserrat_bold_path))
except Exception as e:
    print(f"Error al registrar fuentes Montserrat: {e}")
    print("Asegúrate de que los archivos Montserrat-Regular.ttf y Montserrat-Bold.ttf estén en la carpeta 'fonts'.")
    # Usar fuentes predeterminadas como fallback
    FONT_REGULAR = 'Helvetica'
    FONT_BOLD = 'Helvetica-Bold'
else:
    FONT_REGULAR = 'Montserrat'
    FONT_BOLD = 'Montserrat-Bold'

# Configuración de precios y reglas
PRECIOS = {
    'DJ': {
        'Boda': 12000,
        'Bautizo': 12000,
        'Quince años': 12000,
        'Cumpleaños': 1000  # por hora
    },
    'Sonido': {
        'Boda': {
            '150': 8000,
            '151+': 16000
        },
        'Otros': {
            '70': 4000,
            '150': 8000,
            '250': 12000,
            '350': 16000
        }
    },
    'Iluminación': {
        'Boda': {
           # '150': 4500,
            #'151+': 18000,
            '70': 4500, #6 par + 2 cabezas
            '150': 6500, #6 par + 4 cabezas
            '250': 12500, #12 par + 6 cabezas, si se pueden colgar se cuelgan
            '350': 19500 #22 par + 10 cabezas, si se pueden colgar se cuelgan
        },
        'Otros': {
            '70': 2500, #6 par o 2 cabezas
            '150': 4500, #6 par + 2 cabezas
            '250': 12500, #12 par + 6 cabezas, si se pueden colgar se cuelgan
            '350': 19500  #22 par + 10 cabezas, si se pueden colgar se cuelgan
        }
    },
    'Pista de baile': {
        '70': 6600,
        '150': 8800,
        '250': 11000,
        '350': 13200
    },
    'Planta de luz': 9000,
    'Chisperos': 350,  # precio por unidad
    'Lluvia de papeles': 3000,
    'Barra de bebidas': 8000,
    'Back pintado a mano': 4500
}

# Horas base por tipo de evento
HORAS_BASE = {
    'Cumpleaños': {
        '70': 6,
        '71+': 7
    },
    'Bautizo': {
        '70': 7,
        '71+': 8
    },
    'Quince años': {
        '70': 7,
        '71+': 8
    },
    'Boda': {
        '150': 8,
        '151+': 'ilimitado'
    }
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generar_cotizacion', methods=['POST'])
def generar_cotizacion():
    data = request.json
    
    tipo_evento = data['tipo_evento']
    num_invitados = int(data['num_invitados'])
    horas = int(data['duracion'])
    servicios = data['servicios']
    
    # Calcular horas base según el tipo de evento y número de invitados
    if tipo_evento == 'Cumpleaños':
        horas_base = HORAS_BASE['Cumpleaños']['70'] if num_invitados <= 70 else HORAS_BASE['Cumpleaños']['71+']
    elif tipo_evento == 'Bautizo' or tipo_evento == 'Quince años':
        horas_base = HORAS_BASE[tipo_evento]['70'] if num_invitados <= 70 else HORAS_BASE[tipo_evento]['71+']
    else:  # Boda
        horas_base = HORAS_BASE['Boda']['150'] if num_invitados <= 150 else HORAS_BASE['Boda']['151+']
    
    # Inicializar cotización
    cotizacion = []
    total = 0
    
    # Calcular precios de servicios seleccionados
    for servicio in servicios:
        precio = 0
        horas_extras = 0
        extra_total = 0
        if servicio == 'DJ':
            if tipo_evento in ['Boda', 'Bautizo', 'Quince años']:
                precio = PRECIOS['DJ'][tipo_evento]
            else:
                tipo_precio_dj = data.get('tipo_precio_dj', 'por_hora')
                if tipo_precio_dj == 'por_hora':
                    if horas < 6:
                        precio = 6000
                    else:
                        precio = PRECIOS['DJ']['Cumpleaños'] * horas
                else:
                    precio = 12000
                    dj_horas_base = 6 if num_invitados <= 70 else 7
                    if horas > dj_horas_base:
                        horas_extras = horas - dj_horas_base
                        precio_hora_extra_dj = PRECIOS['DJ']['Cumpleaños']
                        precio += precio_hora_extra_dj * horas_extras
        if servicio == 'Sonido':
            if tipo_evento == 'Boda':
                if num_invitados <= 150:
                    precio = PRECIOS['Sonido']['Boda']['150']
                else:
                    precio = PRECIOS['Sonido']['Boda']['151+']
            else:
                if num_invitados <= 70:
                    precio = PRECIOS['Sonido']['Otros']['70']
                elif num_invitados <= 150:
                    precio = PRECIOS['Sonido']['Otros']['150']
                elif num_invitados <= 250:
                    precio = PRECIOS['Sonido']['Otros']['250']
                elif num_invitados <= 350:
                    precio = PRECIOS['Sonido']['Otros']['350']
                else:
                    precio = "Contactar para calcular precio"
                    continue
            if horas_base != 'ilimitado' and horas > horas_base:
                horas_extras = horas - horas_base
                costo_por_hora_extra_servicio = precio / horas_base
                extra_total = costo_por_hora_extra_servicio * horas_extras
                precio += extra_total
            if isinstance(precio, (int, float)):
                precio = int((precio + 49) // 50 * 50)
        if servicio == 'Iluminación':
            if tipo_evento == 'Boda':
                if num_invitados <= 70:
                    precio = PRECIOS['Iluminación']['Boda']['70']
                elif num_invitados <= 150:
                    precio = PRECIOS['Iluminación']['Boda']['150']
                elif num_invitados <= 250:
                    precio = PRECIOS['Iluminación']['Boda']['250']
                elif num_invitados <= 350:
                    precio = PRECIOS['Iluminación']['Boda']['350']
                else:
                    precio = "Contactar para calcular precio"
                    continue
            else:
                if num_invitados <= 70:
                    precio = PRECIOS['Iluminación']['Otros']['70']
                elif num_invitados <= 150:
                    precio = PRECIOS['Iluminación']['Otros']['150']
                elif num_invitados <= 250:
                    precio = PRECIOS['Iluminación']['Otros']['250']
                elif num_invitados <= 350:
                    precio = PRECIOS['Iluminación']['Otros']['350']
                else:
                    precio = "Contactar para calcular precio"
                    continue
            if horas_base != 'ilimitado' and horas > horas_base:
                horas_extras = horas - horas_base
                costo_por_hora_extra_servicio = precio / horas_base
                extra_total = costo_por_hora_extra_servicio * horas_extras
                precio += extra_total
            if isinstance(precio, (int, float)):
                precio = int((precio + 49) // 50 * 50)
        if servicio == 'Pista de baile':
            if num_invitados <= 70:
                precio = PRECIOS['Pista de baile']['70']
            elif num_invitados <= 150:
                precio = PRECIOS['Pista de baile']['150']
            elif num_invitados <= 250:
                precio = PRECIOS['Pista de baile']['250']
            elif num_invitados <= 350:
                precio = PRECIOS['Pista de baile']['350']
            else:
                precio = "Contactar para calcular precio"
                continue
            if horas_base != 'ilimitado' and horas > horas_base:
                horas_extras = horas - horas_base
                costo_por_hora_extra_servicio = precio / horas_base
                extra_total = costo_por_hora_extra_servicio * horas_extras
                precio += extra_total
            if isinstance(precio, (int, float)):
                precio = int((precio + 49) // 50 * 50)
        if servicio == 'Planta de luz':
            if horas_base != 'ilimitado' and (horas_base + 1) > 9:
                precio = (horas_base + 1) * 1000
            else:
                precio = PRECIOS['Planta de luz']
            if isinstance(precio, (int, float)):
                precio = int((precio + 49) // 50 * 50)
        if servicio == 'Chisperos':
            cantidad = int(data.get('cantidad_chisperos', 1))
            precio = PRECIOS['Chisperos'] * cantidad
            if isinstance(precio, (int, float)):
                precio = int((precio + 49) // 50 * 50)
        if servicio == 'Lluvia de papeles':
            precio = PRECIOS['Lluvia de papeles']
            if isinstance(precio, (int, float)):
                precio = int((precio + 49) // 50 * 50)
        if precio != 0 and precio != "Contactar para calcular precio":
            cotizacion.append({
                'servicio': servicio,
                'precio': precio,
                'horas_extras': int(horas_extras) if horas_extras else 0,
                'extra_total': int(extra_total) if extra_total else 0
            })
            if isinstance(precio, (int, float)):
                total += precio
    
    # Servicios incluidos automáticamente
    servicios_automaticos = []
    
    # Para Bodas, incluir Barra de bebidas
    if tipo_evento == 'Boda':
        servicios_automaticos.append({
            'servicio': 'Barra de bebidas',
            'precio': PRECIOS['Barra de bebidas'],
            'incluido': True
        })
        total += PRECIOS['Barra de bebidas']
        
        # Si se seleccionó Sonido y DJ, incluir Cabina de DJ sin costo
        if 'Sonido' in servicios and 'DJ' in servicios:
            servicios_automaticos.append({
                'servicio': 'Cabina de DJ',
                'precio': 0,
                'incluido': True
            })
    
    # Para Bodas y Bautizos con más de 150 invitados, incluir Back pintado a mano
    if (tipo_evento == 'Boda'):
        servicios_automaticos.append({
            'servicio': 'Back pintado a mano',
            'precio': PRECIOS['Back pintado a mano'],
            'incluido': True
        })
        total += PRECIOS['Back pintado a mano']
        
    if (tipo_evento == 'Bautizo') and num_invitados >= 100:
        servicios_automaticos.append({
            'servicio': 'Back pintado a mano',
            'precio': PRECIOS['Back pintado a mano'],
            'incluido': True
        })
        total += PRECIOS['Back pintado a mano']
    
    # Agregar descuentos y viáticos si se proporcionaron
    descuentos = data.get('descuentos', [])
    viaticos = data.get('viaticos', [])
    extras = data.get('extras', [])
    
    for descuento in descuentos:
        total -= descuento['monto']
    
    for viatico in viaticos:
        total += viatico['monto']
    
    for extra in extras:
        total += extra['monto']
    
    resultado = {
        'cotizacion': cotizacion,
        'servicios_automaticos': servicios_automaticos,
        'descuentos': descuentos,
        'viaticos': viaticos,
        'extras': extras,
        'total': total
    }
    
    return jsonify(resultado)

# La función generar_pdf ha sido movida a pdf_generator.py

# La función generar_pdf_completo ha sido movida a pdf_generator.py

@app.route('/descargar_plantilla', methods=['POST'])
def descargar_plantilla():
    """
    Ruta para descargar la plantilla PDF usando las nuevas plantillas de imagen.
    """
    try:
        data = request.json
        
        # 1. Generar la cotización completa para asegurar que todos los datos están
        response = generar_cotizacion()
        if not response.is_json:
            raise Exception("La generación de cotización no devolvió un JSON válido.")
        
        full_data = response.get_json()

        # 2. Combinar con los datos originales que no están en la cotización (como personalización)
        full_data.update(data)
        # Asegurar que num_personas esté correctamente definido para el PDF
        if 'num_invitados' in data:
            full_data['num_personas'] = data['num_invitados']

        # --- Inicio: Debugging --- 
        print("----- Datos COMPLETOS para generar PDF -----") 
        print(json.dumps(full_data, indent=2))
        print("-------------------------------------------")
        # --- Fin: Debugging ---
        
        # 3. Usar la función generar_pdf con los datos completos
        return generar_pdf(full_data)
    
    except Exception as e:
        print(f"Error en descargar_plantilla: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error al generar el PDF: {str(e)}"}), 500

# La función completar_generacion_pdf ha sido movida a pdf_generator.py

if __name__ == '__main__':
    app.run(debug=True)
            