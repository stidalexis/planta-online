import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, timedelta  
import time
import io
from fpdf import FPDF
import pytz

#  CONFIGURACION DE PAGINA 

st.set_page_config(layout="wide", page_title="SISTEMA C&B PAPELES V0.01 - TOTAL", page_icon="🏭")

#  CONEXION A SUPABASE 

try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("Error de conexion a Base de Datos. Revisar los Secrets.")
    st.stop()
    
#  ESTILOS CSS (DISEÑO INDUSTRIAL Y TACTIL)

st.markdown("""
    <style>
    .stButton > button { height: 70px !important; border-radius: 15px; font-weight: bold; font-size: 20px !important; width: 100%; }
    .title-area { background-color: #0D47A1; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 22px; margin-bottom: 20px; }
    
    /* MONITOR: Cartas con fondo vibrante y texto en NEGRO absoluto */
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 20px; border-radius: 15px; text-align: center; color: #000000 !important; font-weight: bold; font-size: 18px; margin-bottom: 10px; }
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 20px; border-radius: 15px; text-align: center; color: #000000 !important; font-size: 16px; margin-bottom: 10px; }
    
    .section-header { background-color: #F0F2F6; padding: 10px; border-radius: 8px; font-weight: bold; color: #0D47A1; margin-top: 15px; margin-bottom: 10px; border-left: 6px solid #0D47A1; }
    
    /* RADIOGRAFÍA: Cuadros blancos con texto en NEGRO */
    .metric-box { background-color: #ffffff; border: 1px solid #e0e0e0; padding: 12px; border-radius: 8px; margin-bottom: 5px; color: #000000 !important; line-height: 1.6; }
    .metric-box b { color: #000000 !important; }

    /* ESTILO PROFESIONAL PARA HISTORIAL EN PANTALLA */
    .historial-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        border-left: 5px solid #0D47A1;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .historial-header {
        display: flex;
        justify-content: space-between;
        font-weight: bold;
        color: #0D47A1;
        border-bottom: 1px solid #dee2e6;
        padding-bottom: 5px;
        margin-bottom: 10px;
    }
    .historial-tecnico {
        font-size: 0.9em;
        color: #333;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

#  CONSTANTES 

MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 15)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)],
    "REBOBINADORAS": ["REB-01", "REB-02", "REB-03"],
}
PRESENTACIONES = ["BLOCK", "LIBRETA LICOM", "HOJAS SUELTAS", "PAQUETES", "TACOS", "CAJAS", "FAJILLAS", "FORMA CONTINUA"]
PRESENTACIONES2 = ["POR CABEZA", "IZQUIERDA", "DERECHA", "PATA", "N/A", ]
MOTIVOS_PARADA = ["Mantenimiento", "Falta de Material", "falta operario", "Limpieza", "Falla Electrica", "desayuno/desdcanso",]

#  USUARIOS ORGANIZADOS POR ROL 
def validar_usuario_supabase(usuario_ingresado, clave_ingresada):
    try:
# CONSULTA EN TABLA DE USUARIOS FILTRADAS POR EL NOMBRE DE USUSRIO
        respuesta = supabase.table("usuarios")\
            .select("*")\
            .eq("usuario", usuario_ingresado)\
            .eq("clave", clave_ingresada)\
            .execute()
        
# SI LA LISTA ESTA VASIA EL USUARIO NO EXISTE NO DEJA INGRESAR

        if len(respuesta.data) > 0:
            return respuesta.data[0] 
        else:
            return None
    except Exception as e:
        st.error(f"Error al conectar con la tabla de usuarios: {e}")
        return None

#  FUNCIONES AUXILIARES 


def cell_fit(pdf, w, h, text, border=1):

    text = str(text)

    while pdf.get_string_width(text) > (w - 2):
        text = text[:-1]

    pdf.cell(w, h, text, border)

def hora_colombia():
    tz = pytz.timezone("America/Bogota")
    return datetime.now(tz)

# FUNCION DE HORARIOS

def calcular_duracion_laboral(inicio, fin, nombre_maquina=None):
    jornada_inicio = 6
    jornada_fin = 22
    actual = inicio
    total = timedelta()

    esta_on = True
    if nombre_maquina:
        esta_on = obtener_estado_maquina(nombre_maquina)

# SI LA MAQUINA ESTA APAGANA NO CUENTA NADA

    if not esta_on:
        return "0:00:00"

    while actual.date() <= fin.date():
        dia_inicio = actual.replace(hour=jornada_inicio, minute=0, second=0, tzinfo=actual.tzinfo)
        dia_fin = actual.replace(hour=jornada_fin, minute=0, second=0, tzinfo=actual.tzinfo)

        if actual.date() == inicio.date():
            dia_inicio = max(inicio, dia_inicio)

        if actual.date() == fin.date():
            dia_fin = min(fin, dia_fin)

        if dia_inicio < dia_fin:
            total += (dia_fin - dia_inicio)

        actual = (actual + timedelta(days=1)).replace(hour=0, minute=0, second=0, tzinfo=actual.tzinfo)

    return str(total).split('.')[0]
    
#  PDF DE CERTIFICADO 

def generar_pdf_op(row):
    pdf = FPDF()
    pdf.add_page()
    
# ENCABEZADO INDUSTRIAL PDF CERTIFICADO 

    pdf.set_fill_color(13, 71, 161)
    pdf.rect(0, 0, 210, 40, 'F')

# LOGO CYB PAPELES

    pdf.image("logo_cb.png", 2, 2, 60)
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 20, f" CERTIFICADO DE PRODUCCION - OP: {row['op']}", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"TRABAJO: {row['nombre_trabajo']}", ln=True, align='C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(0.5)
    
#  SECCION DATOS DE VENTA PDF

    pdf.set_font("Arial", 'B', 11)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 8, " 1. INFORMACION GENERAL Y ORIGEN", ln=True, fill=True)
    pdf.set_font("Arial", '', 10)
    
    c1 = 100
    pdf.cell(c1, 7, f"Cliente: {row.get('cliente')}", border='B')
    pdf.cell(0, 7, f"Vendedor: {row.get('vendedor')}", border='B', ln=True)
    pdf.cell(c1, 7, f"Tipo de Orden: {row.get('tipo_orden')}", border='B')
    pdf.cell(0, 7, f"Fecha Creacion: {row.get('created_at', '')[:10]}", border='B', ln=True)
    pdf.ln(5)

#  SECCION ESPECIFICACIONES PDF

    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, " 2. ESPECIFICACIONES TECNICAS", ln=True, fill=True)
    pdf.set_font("Arial", '', 10)

    if "FORMAS" in row.get('tipo_orden', ''):
        pdf.cell(c1, 7, f"Cantidad: {row.get('cantidad_formas')}", border='B')
        pdf.cell(0, 7, f"Partes: {row.get('num_partes')}", border='B', ln=True)
        pdf.cell(c1, 7, f"Presentacion: {row.get('presentacion')}", border='B')
        pdf.cell(0, 7, f"Destino: {row.get('destino_formas', 'N/A')}", border='B', ln=True)
    else:
        pdf.cell(c1, 7, f"Material: {row.get('material')}", border='B')
        pdf.cell(0, 7, f"Gramaje: {row.get('gramaje_rollos')}g", border='B', ln=True)
        pdf.cell(c1, 7, f"Cantidad: {row.get('cantidad_rollos')}", border='B')
        pdf.cell(0, 7, f"Core: {row.get('core')}", border='B', ln=True)

    pdf.ln(5)

#  SECCION BITACORA TECNICA  

    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, " 3. TRAZABILIDAD Y REGISTROS DE PLANTA", ln=True, fill=True)
    
    historial = row.get('historial_procesos', [])
    if not historial:
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 10, "Pendiente de procesamiento.", ln=True)
    else:
        for h in historial:
            pdf.ln(2)

# FILA DE TITULO DE AREA

            pdf.set_font("Arial", 'B', 10)
            pdf.set_fill_color(240, 245, 255)
            pdf.cell(0, 7, f" AREA: {h['area']} | MAQUINA: {h['maquina']}", ln=True, fill=True, border=1)
            
# FILA DE RESPONSABLES POR OP

            pdf.set_font("Arial", 'B', 9)
            pdf.cell(65, 6, f"Operador: {h['operario']}", border='LR')
            pdf.cell(65, 6, f"Auxiliar: {h.get('auxiliar', 'N/A')}", border='R')
            pdf.cell(0, 6, f"Fecha: {h['fecha']}", border='R', ln=True)
            
# FILA DE TIEMPOS TOMADOS POR OP

            pdf.cell(130, 6, f"Duracion del Proceso: {h['duracion']}", border='LRB')
            pdf.cell(0, 6, "", border='RB', ln=True)

# DATOS TECNICOS SALIDA JHSON

            pdf.set_font("Arial", '', 8)

            datos_c = h.get('datos_cierre', {})

            if datos_c:

                pdf.set_font("Arial", 'B', 7)
                pdf.set_fill_color(230,230,230)

# ENCABEZADOS TABLA

                pdf.cell(45,6,"OBJETO",1,0,'C',True)
                pdf.cell(45,6,"DATO",1,0,'C',True)
                pdf.cell(45,6,"OBJETO",1,0,'C',True)
                pdf.cell(45,6,"DATO",1,1,'C',True)

                pdf.set_font("Arial",'',8)

                items = list(datos_c.items())

                for i in range(0,len(items),2):

                    k1,v1 = items[i]
                    key1 = k1.replace("_"," ").upper()

                    if i+1 < len(items):
                        k2,v2 = items[i+1]
                        key2 = k2.replace("_"," ").upper()
                    else:
                        key2=""
                        v2=""

                    pdf.cell(45,6,key1,1)
                    pdf.cell(45,6,str(v1),1)
                    pdf.cell(45,6,key2,1)
                    pdf.cell(45,6,str(v2),1,1)
            
# BLOQUE OBSERVACIONES

            if h.get('observaciones'):
                pdf.set_font("Arial", 'I', 8)
                pdf.multi_cell(0, 5, f"OBSERVACIONES: {h['observaciones']}", border=1)
            else:
                pdf.cell(0, 1, "", ln=True, border='T')
            pdf.ln(2)

    pdf.ln(10)
    pdf.set_font("Arial", 'I', 7)
    pdf.cell(0, 10, f"DOCUMENTO OFICIAL C&B PAPELES - GENERADO AUTOMATICAMENTE - {hora_colombia().strftime('%d/%m/%Y %H:%M')}", align='C')
    
    return bytes(pdf.output())

def generar_op_rollos(row):
    pdf = FPDF()
    pdf.add_page()

# LOGICA DE COLOR SEGUN ORDEN 

    tipo_op = row.get('tipo_origen', '').upper()

    if "NUEVA" in tipo_op:
        r, g, b = (40, 167, 69)      # VERDE
    elif "CAMBIOS" in tipo_op:
        r, g, b = (255, 0, 0)     # ROJO
    else:
        r, g, b = (13, 71, 161)     # AZUL

#  ENCABEZADO CON COLOR DINAMICO

    pdf.set_fill_color(r, g, b)
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.image("logo_cb.png", 2, 2, 60)
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 18, "ORDEN DE PRODUCCION - ROLLOS", 0, 1, "C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0,5,f"OP: {row['op']}   |   {row['tipo_origen']}",0,1,"C")
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

# INFORMACION GENERAL

    pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "1. INFORMACION DE LA ORDEN", 0, 1, fill=True)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(95, 7, f"Cliente: {row.get('cliente','')}", 1)
    pdf.cell(95, 7, f"Vendedor: {row.get('vendedor','')}", 1, 1)
    pdf.cell(95, 7, f"Trabajo: {row.get('nombre_trabajo','')}", 1)
    pdf.cell(95, 7, f"Tipo Orden: {row.get('tipo_orden','')}", 1, 1)

# ESPECIFICACIONES TECNICAS

    pdf.ln(4); pdf.set_font("Arial", "B", 11); 
    pdf.cell(0, 8, "2. ESPECIFICACIONES TECNICAS", 0, 1, fill=True)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(63, 7, f"Material: {row.get('material','')}", 1)
    pdf.cell(63, 7, f"Gramaje: {row.get('gramaje_rollos','')}", 1)
    pdf.cell(64, 7, f"Core: {row.get('core','')}", 1, 1)

    pdf.cell(63, 7, f"Cantidad Rollos: {row.get('cantidad_rollos','')}", 1)
    pdf.cell(63, 7, f"Unidades Bolsa: {row.get('unidades_bolsa','')}", 1)
    pdf.cell(64, 7, f"Unidades Caja: {row.get('unidades_caja','')}", 1, 1)
    
# REFERENCIAS Y TRANSPORTES 

    pdf.cell(95, 7, f"Referencia Comercial: {row.get('ref_comercial','')}", 1)
    trans = "SI" if row.get('transportadora_rollos') else "NO"
    pdf.cell(95, 7, f"Transportadora: {trans}", 1, 1)
    pdf.cell(25, 8, "Impresión", 1, 0, 'C')
    pdf.cell(82, 8, f" Frente: {row.get('tintas_frente_rollos', 'N/A')}", 1)
    pdf.cell(83, 8, f" Respaldo: {row.get('tintas_respaldo_rollos', 'N/A')}", 1, 1)
    pdf.cell(190, 7, f"Destino: {row.get('destino_rollos','PLANTA')}", 1, 1)

# OBSERFVACIONES Y PERFORACIONES 

    pdf.ln(4); pdf.set_font("Arial", "B", 11); 
    pdf.cell(0, 8, "3. ADICIONALES Y OBSERVACIONES", 0, 1, fill=True)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, f"Perforaciones: {row.get('perforaciones_detalle', 'NO')}", 1, 1)
    pdf.set_text_color(255, 0, 0)
    pdf.multi_cell(0, 7, f"Observaciones: {row.get('observaciones_rollos','')}", 1)

# FIRMAS O SELLOS
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4); pdf.set_font("Arial", "B", 11); 
    pdf.cell(0, 8, "4. FIRMAS", 0, 1, fill=True)
    pdf.ln(1); pdf.set_font("Arial", "B", 6)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(63, 6, "COORDINADORA COMERCIAL", 1, 0, "C", fill=True) 
    pdf.cell(63, 6, "ASESOR", 1, 0, "C", fill=True) 
    pdf.cell(64, 6, "SUPERVISOR DE PRODUCCION", 1, 1, "C", fill=True)
    pdf.cell(63, 20, "", 1, 0); pdf.cell(63, 20, "", 1, 0); pdf.cell(64, 20, "", 1, 1)

# DATOS DE ESTIBAS 

    pdf.set_font("Arial", "", 11)
    y_est = pdf.get_y() + 2
    pdf.set_xy(10, y_est)
    pdf.set_fill_color(210, 210, 210); pdf.set_font("Arial", 'B', 11)
    pdf.cell(190, 5, "5 .REPORTE DE CAJAS POR ESTIBAS (PRODUCCIÓN)", 1, 1, 'C', True)
    
    
    w_e = 190 / 3
    pdf.set_font("Arial", '', 8)
    for i in range(4): 
        pdf.cell(w_e, 7, f" ESTIBA {i*3+1} | Cant:_________H:___________", 1, 0)
        pdf.cell(w_e, 7, f" ESTIBA {i*3+2} | Cant:_________H:___________", 1, 0)
        pdf.cell(w_e, 7, f" ESTIBA {i*3+3} | Cant:_________H:___________", 1, 1)

# OBSERVACIONES FINALIZADO

    pdf.set_font("Arial", "B", 8)
    pdf.cell(130, 8, "OBSERVACIONES FINALIZADO", 1, 0, "C"); pdf.cell(60, 8, "RECIBE", 1, 1, "C")
    pdf.set_font("Arial", "", 7)
    for _ in range(2):
        pdf.cell(130, 6, "", 1, 0); pdf.cell(60, 6, "", 1, 1)

# PIE

    pdf.set_font("Arial", "I", 6)
    pdf.cell(0, 5, f"SISTEMA C&B PAPELES - {hora_colombia().strftime('%d/%m/%Y %H:%M')}", 0, 1, "C")

    return bytes(pdf.output())


# GENERAR PDF FORMAS

def generar_op_formas(row):
    pdf = FPDF()
    pdf.add_page()
    
    tipo_op = row.get('tipo_origen', '').upper()

# ENCABEZADO DINAMICO

    if "NUEVA" in tipo_op:
        r, g, b = (40, 167, 69)      # VERDE
    elif "CAMBIOS" in tipo_op:
        r, g, b = (255, 0, 0)     # ROJO
    else:
        r, g, b = (13, 71, 161)     # AZUL

# ENCABEZADO CON COLOR DINAMICO

    pdf.set_fill_color(r, g, b)
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.image("logo_cb.png", 2, 2, 60)

    pdf.set_text_color(255,255,255)
    pdf.set_font("Arial","B",16)
    pdf.cell(0,18,"ORDEN DE PRODUCCION - FORMAS",0,1,"C")
    pdf.set_font("Arial","B",12)
    pdf.cell(0,5,f"OP: {row['op']}   |   {row['tipo_origen']}",0,1,"C")
    pdf.set_text_color(0,0,0)
    pdf.ln(4)

# INFORMACION DE LA ORDEN

    pdf.set_fill_color(230,230,230)
    pdf.set_font("Arial","B",11)
    pdf.cell(0,8,"1. INFORMACION DE LA ORDEN",0,1,fill=True)
    pdf.set_font("Arial","B",10)
    pdf.cell(95,7,f"Cliente: {row.get('cliente','')}",1)
    pdf.cell(95,7,f"Vendedor: {row.get('vendedor','')}",1,1)
    pdf.cell(95,7,f"Trabajo: {row.get('nombre_trabajo','')}",1)
    pdf.cell(95,7,f"Tipo Orden: {row.get('tipo_orden','')}",1,1)
    pdf.cell(95,7,f"OP Anterior: {row.get('op_anterior','')}",1)
    pdf.cell(95,7,f"Fecha: {row.get('created_at','')[:10]}",1,1)

# ESPECIFICACIONES GENERALES 

    pdf.ln(4)
    pdf.set_font("Arial","B",11)
    pdf.cell(0,8,"2. ESPECIFICACIONES GENERALES Y ACABADOS",0,1,fill=True)
    pdf.set_font("Arial","B",10)
    
    pdf.cell(63,7,f"Cantidad: {row.get('cantidad_formas','')}",1)
    pdf.cell(63,7,f"Partes: {row.get('num_partes','')}",1)
    pdf.cell(64,7,f"Presentacion: {row.get('presentacion','')}",1,1)
    
    pdf.cell(65,7,f"Tipo Pegue: {row.get('presentacion2', 'N/A')}",1) 
    pdf.cell(125,7,f"Numeracion: DEL-  {row.get('num_id','NO')} AL-  {row.get('num_fd','')}",1,1)
    
    pdf.cell(125,7,f"Codigo Barras: {row.get('codigo_barras_detalle','')}",1)
    trans = "SI" if row.get('transportadora_formas') else "NO"
    pdf.cell(65,7,f"Transportadora: {trans}",1,1)
    pdf.cell(190,7,f"Destino: {row.get('destino_formas','NO APLICA')}",1,1)

# PERFORACIONES

    pdf.ln(4)
    pdf.set_font("Arial","B",11)
    pdf.cell(0,8,"3. PERFORACIONES",0,1,fill=True)
    pdf.set_font("Arial","",10)
    pdf.multi_cell(0,7,row.get("perforaciones_detalle","SIN PERFORACIONES"), 1)

# DETALLE TECNICO POR PARTE

    pdf.ln(4)
    pdf.set_font("Arial","B",11)
    pdf.cell(0,8,"4. DETALLE TECNICO POR PARTE",0,1,fill=True)
    pdf.set_font("Arial","B",8)
    pdf.set_fill_color(200,200,200)
    pdf.cell(8,7,"P",1,0,"C",True)
    pdf.cell(15,7,"ANCHO",1,0,"C",True)
    pdf.cell(15,7,"LARGO",1,0,"C",True)
    pdf.cell(32,7,"PAPEL",1,0,"C",True)
    pdf.cell(25,7,"COLOR",1,0,"C",True)
    pdf.cell(12,7,"GR",1,0,"C",True)
    pdf.cell(23,7,"T. FRENTE",1,0,"C",True)
    pdf.cell(23,7,"T. RESP",1,0,"C",True)
    pdf.cell(37,7,"OBS. PARTE",1,1,"C",True)

    pdf.set_font("Arial","",8)
    partes = row.get("detalles_partes_json",[])
    for p in partes:
        cell_fit(pdf,8,7,p.get("p",""))
        cell_fit(pdf,15,7,p.get("anc",""))
        cell_fit(pdf,15,7,p.get("lar",""))
        cell_fit(pdf,32,7,p.get("papel",""))
        cell_fit(pdf,25,7,p.get("color_fondo",""))
        cell_fit(pdf,12,7,p.get("gramos",""))
        cell_fit(pdf,23,7,p.get("tf",""))
        cell_fit(pdf,23,7,p.get("tr",""))
        cell_fit(pdf,37,7,p.get("obs_parte","")) 
        pdf.ln()

# OBSERVACIONES GENERALES

    pdf.ln(5)
    pdf.set_font("Arial","B",11)
    pdf.set_text_color(255, 0, 0)
    pdf.cell(0,8,"5. OBSERVACIONES GENERALES",0,1,fill=True)
    pdf.set_font("Arial","",10)
    pdf.multi_cell(0,7,row.get("observaciones_formas",""), 1)

# FIRMAS

    pdf.ln(1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4); pdf.set_font("Arial", "B", 11); 
    pdf.cell(0, 8, "4. FIRMAS", 0, 1, fill=True)
    pdf.ln(1); pdf.set_font("Arial", "B", 6)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(63, 6, "COORDINADORA COMERCIAL", 1, 0, "C", fill=True) 
    pdf.cell(63, 6, "ASESOR", 1, 0, "C", fill=True) 
    pdf.cell(64, 6, "SUPERVISOR DE PRODUCCION", 1, 1, "C", fill=True)
    pdf.cell(63, 20, "", 1, 0); pdf.cell(63, 20, "", 1, 0); pdf.cell(64, 20, "", 1, 1)

    pdf.set_font("Arial","B",8)
    pdf.cell(130,8,"OBSERVACIONES",1,0,"C")
    pdf.cell(60,8,"RECIBE",1,1,"C")

    pdf.set_font("Arial", "B", 8)
    pdf.cell(130, 8, "OBSERVACIONES FINALIZADO", 1, 0, "C"); pdf.cell(60, 8, "RECIBE", 1, 1, "C")
    pdf.set_font("Arial", "", 7)
    for _ in range(2):
        pdf.cell(130, 6, "", 1, 0); pdf.cell(60, 6, "", 1, 1)

# PIE

    pdf.set_font("Arial", "I", 6)
    pdf.cell(0, 5, f"SISTEMA C&B PAPELES - {hora_colombia().strftime('%d/%m/%Y %H:%M')}", 0, 1, "C")

    return bytes(pdf.output())

def generar_op_rebobinado(row):
    pdf = FPDF()
    pdf.add_page()
    
    tipo_op = row.get('tipo_origen', '').upper()
    # --- ENCABEZADO ---
    if "NUEVA" in tipo_op:
        r, g, b = (40, 167, 69)      # VERDE
    elif "CAMBIOS" in tipo_op:
        r, g, b = (255, 0, 0)     # ROJO
    else:
        r, g, b = (13, 71, 161)     # AZUL

#  ENCABEZADO CON COLOR DINAMICO

    pdf.set_fill_color(r, g, b)
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.image("logo_cb.png", 2, 2, 60)

    pdf.set_text_color(255,255,255)
    pdf.set_font("Arial","B",16)
    pdf.cell(0,18,"ORDEN DE PRODUCCION - REBOBINADO",0,1,"C")
    pdf.set_font("Arial","B",12)
    pdf.cell(0,5,f"OP: {row['op']}   |   {row['tipo_origen']}",0,1,"C")
    pdf.set_text_color(0,0,0)
    pdf.ln(4)

# INFORMACION GENERAL

    pdf.set_fill_color(230,230,230)
    pdf.set_font("Arial","B",11)
    pdf.cell(0,8,"1. INFORMACION GENERAL",0,1,fill=True)
    pdf.set_font("Arial","",10)

    pdf.cell(95,7,f"Cliente: {row.get('cliente','')}",1)
    pdf.cell(95,7,f"Vendedor: {row.get('vendedor','')}",1,1)
    pdf.cell(95,7,f"Trabajo: {row.get('nombre_trabajo','')}",1)
    pdf.cell(95,7,f"OP Anterior: {row.get('op_anterior','N/A')}",1,1)
    pdf.cell(190,7,f"Fecha de Creacion: {row.get('created_at','')[:10]}",1,1)

# DATOS TECNICOS DE ENTRADA Y OBJETIVO

    pdf.ln(4)
    pdf.set_font("Arial","B",11)
    pdf.cell(0,8,"2. DATOS TECNICOS Y OBJETIVO DEL PROCESO",0,1,fill=True)
    pdf.set_font("Arial","",10)

#  MATERIAL Y DIMENCIONES

    pdf.cell(63,7,f"Material Base: {row.get('material','')}",1)
    pdf.cell(63,7,f"Gramaje: {row.get('gramaje_rollos','')}g",1)
    pdf.cell(64,7,f"Referencia Comercial: {row.get('ancho_base','')}",1,1)

# CANTIDADES
    pdf.cell(95,7,f"Cantidad Rollos Solicitados: {row.get('cantidad_rollos','')}",1)
    pdf.cell(95,7,f"Tipo de Creacion: {row.get('tipo_creacion','NUEVA')}",1,1)

# OBJETIVO DE REBOBINADO (IMPRESION O PARA QUE )

    pdf.set_font("Arial","B",10)
    pdf.cell(190,7,"OBJETIVO PRINCIPAL DEL REBOBINADO:", "LTR", 1)
    pdf.set_font("Arial","",10)
    pdf.multi_cell(190,7, row.get('objetivo_rebobinado','No especificado'), "LRB")

# OBSERVACIONES DE PLANIFICACION

    pdf.ln(5)
    pdf.set_font("Arial","B",11)
    pdf.cell(0,8,"3. OBSERVACIONES ADICIONALES",0,1,fill=True)
    pdf.set_font("Arial","",10)
    pdf.multi_cell(0,7, row.get("observaciones_rollos","Sin observaciones adicionales"), 1)

# ESPACIO PARA ANOTACIONES DE PLANTA 

    pdf.ln(5)
    pdf.set_font("Arial","I",8)
    pdf.cell(0,5,"* Espacio reservado para el operario: verificar empalmes y diámetros finales.",0,1)

# PIE DE PAGINA

    pdf.ln(10)
    pdf.set_font("Arial","I",7)
    pdf.cell(0,10,f"SISTEMA C&B PAPELES - GENERADO: {hora_colombia().strftime('%d/%m/%Y %H:%M')}",0,1,"C")

    return bytes(pdf.output())

# RADIOGRAFIA TECNICA

@st.dialog("📋 RADIOGRAFÍA TÉCNICA DE LA ORDEN", width="large")
def modal_detalle_op(row):
    st.markdown(f"### OP: {row['op']} — {row['nombre_trabajo']}")
    st.write(f"🏭 **Estado en Planta:** `{row['proxima_area']}`")
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div class='section-header'>👤 DATOS GENERALES</div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class='metric-box'>
        👤 <b>Cliente:</b> {row.get('cliente')}<br>
        💼 <b>Vendedor:</b> {row.get('vendedor')}<br>
        📝 <b>Nombre trabajo:</b> {row.get('nombre_trabajo')}<br>
        📑 <b>referencia:</b> {row.get('ref_comercial')}<br>
        🔙 <b>orden anterior:</b> {row.get('op_anterior')}<br>
        📅 <b>Fecha:</b> {row.get('created_at', '')[:10]}
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='section-header'>📐 ESPECIFICACIONES</div>", unsafe_allow_html=True)
        if "FORMAS" in row['tipo_orden']:
            st.markdown(f"""
            <div class='metric-box'>
            📦 <b>Cantidad:</b> {row.get('cantidad_formas')}<br>
            📑 <b>Partes:</b> {row.get('num_partes')}<br>
            🎨 <b>Presentación:</b> {row.get('presentacion')}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='metric-box'>
            📄 <b>Material:</b> {row.get('material')}<br>
            📏 <b>Gramaje:</b> {row.get('gramaje_rollos')}<br>
            📦 <b>unidades por caja:</b> {row.get('unidades_caja')}<br>
            🛍️ <b>unidades por bolsa:</b> {row.get('unidades_bolsa')}<br>
            📦 <b>Cantidad:</b> {row.get('cantidad_rollos')}
            </div>
            """, unsafe_allow_html=True)

    with col3:
        st.markdown("<div class='section-header'>⚙️ EXTRAS</div>", unsafe_allow_html=True)
        if "FORMAS" in row['tipo_orden']:
            st.markdown(f"""
            <div class='metric-box'>
            ✂️ <b>Perforación:</b> {row.get('perforaciones_detalle')}<br>
            🚚 <b>Transporte:</b> {row.get('transportadora_formas', 'NO')}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='metric-box'>
            🎨 <b>Tintas F:</b> {row.get('tintas_frente_rollos')}<br>
            🎨 <b>Tintas R:</b> {row.get('tintas_respaldo_rollos')}<br>
            🌀 <b>Core:</b> {row.get('core')}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div class='section-header'>📜 BITÁCORA DE PRODUCCIÓN PROFESIONAL</div>", unsafe_allow_html=True)
    hist = row.get('historial_procesos', [])
    if not hist:
        st.info("No hay registros de producción todavía.")
    else:
        for h in hist:

# DISENO DE TARGETAS DE DENTRADA

            with st.container():
                st.markdown(f"""
                <div class='historial-card'>
                    <div class='historial-header'>
                        <span>✅ {h['area']} — {h['maquina']}{' 🔄 ENTREGA PARCIAL' if h.get('tipo') == 'PARCIAL' else ''}</span>
                        <span>📅 {h['fecha']}</span>
                    </div>
                    <div class='historial-tecnico'>
                        <div>👤 <b>Operario:</b> {h['operario']}</div>
                        <div>👥 <b>Auxiliar:</b> {h.get('auxiliar', 'N/A')}</div>
                        <div>⏱️ <b>Tiempo Proceso:</b> {h['duracion']}</div>
                        <div>📝 <b>Obs:</b> {h.get('observaciones', 'Sin observaciones')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
# VER DATOS DE CIERRE EN TABLA LIMPOA Y NO JHSON

                if h.get('datos_cierre'):
                    with st.expander("📊 Ver Datos Técnicos de Salida"):
                        df_datos = pd.DataFrame(list(h['datos_cierre'].items()), columns=['Parámetro', 'Valor'])
                        df_datos['Parámetro'] = df_datos['Parámetro'].str.replace('_', ' ').str.upper()
                        st.table(df_datos)

    st.divider()
    pdf_bytes = generar_pdf_op(row)
    st.download_button(label="🖨️ Descargar Certificado de Producción (PDF)", data=pdf_bytes, file_name=f"CERTIFICADO_{row['op']}.pdf", mime="application/pdf", use_container_width=True)

# ESTRUCTURA DE MENU  GENERAL 

if 'sel_tipo' not in st.session_state: st.session_state.sel_tipo = None
if 'rep' not in st.session_state: st.session_state.rep = None

# LOGIN PRINCIPAL  LOGUIN

if not st.session_state.get('autenticado'):
    st.title("🔐 Acceso al Sistema C&B PAPELES DE COLOMBIA S.A.S")
    
    with st.form("login_form"):
        user = st.text_input("Usuario")
        pw = st.text_input("Contraseña", type="password")
        boton_login = st.form_submit_button("Ingresar")
        
        if boton_login:
            datos_usuario = validar_usuario_supabase(user, pw)
            
            if datos_usuario:
                st.session_state['autenticado'] = True
                st.session_state['usuario_actual'] = datos_usuario['usuario']
                st.session_state['nombre_usuario'] = datos_usuario['nombre']
                st.session_state['rol'] = datos_usuario['rol']
                st.success(f"Bienvenido {datos_usuario['nombre']}")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
    st.stop() 

# ESTRUCTURA DE MENU CON PERMISOS POR ROL

with st.sidebar:
    st.title("🏭 C&B PAPELES DE COLOMBIA S.A.S")
    
    rol = st.session_state.get('rol', 'operario').lower()
    
# DEFINICION DE PERMISOS SEGUN ROL

    if rol == 'admin':
        opciones_menu = ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "⏱️ Seguimiento Cortadoras", "📥 Colectoras", "📕 Encuadernación", "🌀 Rebobinadoras", "📦 Inventario", "📦 salida produccion P1", "📊 Reportes Admin", "🎨 Diseño y Pre-Prensa", "📦 Almacen/Despachos", "🛒 Mercado"]     
    elif rol == 'ventas':
        opciones_menu = ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🛒 Mercado"]
    elif rol == 'jefe_log':
        opciones_menu = ["📦 salida produccion P1", "📊 Reportes Admin", "📦 Almacen/Despachos", "🛒 Mercado"]
    elif rol == 'patinador_log':
        opciones_menu = ["📦 Almacen/Despachos", "🛒 Mercado"]
    elif rol == 'aux_log':
        opciones_menu = ["📦 Almacen/Despachos", "🛒 Mercado"]
    elif rol == 'supervisor_imp':
        opciones_menu = ["🖥️ Monitor", "🖨️ Impresión", "📥 Colectoras", "📕 Encuadernación", "🛒 Mercado"]
    elif rol == 'supervisor_cor':
        opciones_menu = ["🖥️ Monitor", "✂️ Corte", "⏱️ Seguimiento Cortadoras", "🛒 Mercado"]
    elif rol == 'supervisor_enc':
        opciones_menu = ["🖥️ Monitor", "📕 Encuadernación", "🛒 Mercado"]
    elif rol == 'supervisor_reb':
        opciones_menu = ["🖥️ Monitor", "🌀 Rebobinadoras", "🛒 Mercado"]
    elif rol == 'patinador_roll':
        opciones_menu = ["📦 salida produccion P1", "🛒 Mercado"]
    elif rol == 'almacen':
        opciones_menu = ["📦 Almacen/Despachos", "🛒 Mercado"]
    elif rol == 'diseño':
        opciones_menu = ["🖥️ Monitor", "🎨 Diseño y Pre-Prensa", "🔍 Seguimiento", "🛒 Mercado"]
    else:

# OPERARIOS Y OTROS ROLES SI LOS DEJA DENTRAR

        opciones_menu = ["🖥️ Monitor"]

    menu = st.radio("SELECCIONE MÓDULO:", opciones_menu)
    
    st.divider()
    st.caption(f"Usuario: {st.session_state.get('usuario_actual')} | Rol: {rol}")
    
# BOTON DE CERRAR SESION

    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    
    st.divider()
    st.info(f"Usuario: {st.session_state.get('nombre_usuario')}\n\nRol: {rol.upper()}")
    st.caption("Conectado a Supabase Cloud")

#  FUNCION PARA GESTION DE MAQUINAS   

def obtener_estado_maquina(nombre_maquina):
    try:
        res = supabase.table("estado_maquinas").select("estado").eq("maquina", nombre_maquina).execute()
        if res.data:
            return res.data[0]['estado']
        return True  # Si no existe en la tabla, asumimos que esta ON
    except:
        return True

def cambiar_estado_maquina(nombre_maquina, nuevo_estado):
    try:
        supabase.table("estado_maquinas").upsert({
            "maquina": nombre_maquina,
            "estado": nuevo_estado,
            "ultima_modificacion": hora_colombia().isoformat()
        }).execute()
    except Exception as e:
        st.error(f"Error al cambiar estado: {e}")
# MODULO MONITOR 

if menu == "🖥️ Monitor":
    st.markdown("<div class='title-area'>🖥️ MONITOR DE PRODUCCIÓN EN TIEMPO REAL</div>", unsafe_allow_html=True)
    
#  OPTIMIZACION: TRAER ESTADOS DE MAQUINAS DE UN SOLO GOLPE 
    try:
        estados_db = supabase.table("estado_maquinas").select("maquina, estado").execute().data

# Diccionario rápido: {'MAQ1': True, 'MAQ2': False}

        diccionario_estados = {item['maquina']: item['estado'] for item in estados_db}
    except Exception as e:
        st.error(f"Error al cargar estados: {e}")
        diccionario_estados = {}

# Traer datos de trabajos activos

    act_data = supabase.table("trabajos_activos").select("*").execute().data

# ALERTAS DE OP ESTANCADAS (Filtrando por ON/OFF)

    alertas = []
    for a in act_data:
        try:

# USA EL DICCIONARIO PARA NO BUSCAR EN LA SUPABASE

            if not diccionario_estados.get(a['maquina'], True):
                continue 
            
            inicio = datetime.fromisoformat(a["hora_inicio"].replace("Z", "+00:00"))

# PASAMOS EL ESTADO ACTUAL ALA FUNCION 

            tiempo_texto = calcular_duracion_laboral(inicio, ahora, a['maquina'])
            
            h, m, s = map(int, tiempo_texto.split(':'))
            horas_laborales = h + m/60 + s/3600

            if horas_laborales > 4:  
                alertas.append(f"🚨 OP {a['op']} en {a['maquina']} lleva {round(horas_laborales,1)}h de trabajo activo")
        except Exception as e:
            print(f"Error en alerta: {e}")

    if alertas:
        st.error("🚨 ALERTAS DE PRODUCCIÓN:")
        for al in alertas:
            st.warning(al)

# PREPARAR DATOS DE OPERACIONES 

    ops = supabase.table("ordenes_planeadas").select("op,nombre_trabajo").execute().data
    map_ops = {o['op']: o['nombre_trabajo'] for o in ops}

    act = {}
    for a in act_data:
        op = a['op']
        a['nombre_trabajo'] = map_ops.get(op, "SIN NOMBRE")
        act[a['maquina']] = a
        
#  DIBUJAR INTERFAZ (Con logica de colores) 

    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:

# Verificar si la maquina esta encendida en el diccionario

                esta_encendida = diccionario_estados.get(m, True)

                if not esta_encendida:

# TARJETA GRIS: Maquina apagada (Mantenimiento/etc)

                    st.markdown(
                        f"""<div style='background-color: #424242; color: #9E9E9E; padding: 20px; 
                        border-radius: 15px; text-align: center; border: 2px solid #212121;'>
                        <span style='font-size: 18px; font-weight: bold;'>{m}</span><br>
                        <span style='font-size: 14px;'>🚫 FUERA DE SERVICIO</span>
                        </div>""", 
                        unsafe_allow_html=True
                    )
                elif m in act:

# TARJETA AZUL/VIBRANTE: En produccion

                    st.markdown(
                        f"<div class='card-produccion'>{m}<br>OP: {act[m]['op']}<br>{act[m]['nombre_trabajo']}</div>",
                        unsafe_allow_html=True
                    )
                else:

# TARJETA VERDE: Libre

                    st.markdown(
                        f"<div class='card-vacia'>{m}<br>LIBRE</div>",
                        unsafe_allow_html=True
                    )

#  REFRESCO AUTOMATICO 

    time.sleep(30)
    st.rerun()

# MODULO SEGUIMIENTO

elif menu == "🔍 Seguimiento":
    st.title("🔍 Seguimiento de Órdenes en Tiempo Real")
    
# TRAER TRABAJOS Y ORDENES ACTIVAS 

    try:
        ordenes_res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute()
        activos_res = supabase.table("trabajos_activos").select("op, maquina").execute()
        
        ordenes = ordenes_res.data
        activos = activos_res.data
        
# DICCIONARIO DE OP EN MAQUINAS 

        op_en_maquina = {str(a['op']): a['maquina'] for a in activos}
    except Exception as e:
        st.error(f"Error al conectar con las tablas: {e}")
        ordenes = []

    if not ordenes:
        st.warning("No hay órdenes registradas.")
    else:
        busqueda = st.text_input("🔍 Filtrar por OP, Cliente, Trabajo o Vendedor:", "")
        
        for row in ordenes:
            op_id = str(row['op'])
            area_destino = row.get('proxima_area', 'SIN ÁREA').upper()
            cliente = row.get('cliente', 'N/A')
            nombre_t = row.get('nombre_trabajo', 'SIN NOMBRE')
            vendedor = row.get('vendedor', 'N/A')
            lugar = row.get('tipo_origen', 'N/A')
           

# LOGICA DE FILTRADO

            if busqueda:
                b = busqueda.lower()
                
                if (b not in op_id.lower() and 
                    b not in cliente.lower() and 
                    b not in nombre_t.lower() and
                    b not in lugar.lower() and  
                    b not in area_destino.lower() and 
                    b not in vendedor.lower()):
                    continue


# LOGICA DE ESTATUS MEJORADA

            if area_destino == "FINALIZADO":
                
                texto_estatus = "🔵 ORDEN FINALIZADA (BODEGA / DESPACHOS)"
                color_texto = "blue"
            elif op_id in op_en_maquina:
                
                maquina_nombre = op_en_maquina[op_id]
                texto_estatus = f"🟢 EN {area_destino} (PROCESANDO EN: {maquina_nombre})"
                color_texto = "green"
            else:
               
                texto_estatus = f"⏳ EN ESPERA DE {area_destino}"
                color_texto = "orange"

#  DISEÑO DE TARJETA 

            with st.expander(f"📦 OP: {op_id} | {cliente} | {texto_estatus} | {vendedor}"):
                st.markdown(f"### ESTATUS DE TRABAJO: :{color_texto}[{texto_estatus}]")
                
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.write("**👤 CLIENTE:**")
                    st.write(cliente)
                    st.write("**📅 FECHA:**")
                    st.write(row.get('created_at', '')[:10])
                    st.write("**🔙 ORDEN ANTERIOR:**")
                    st.write(row.get('op_anterior', '')[:10])
                with c2:
                    st.write("**🏗️ AREA ACTUAL:**")
                    st.info(area_destino)
                    st.write("**📦 CANTIDAD SOLICITADA:**")
                    st.write(row.get('cantidad_formas') if "FORMAS" in row.get('tipo_orden','') else row.get('cantidad_rollos','0'))
                    st.write("**📖 REFERENCIA COMERCIAL:**")
                    st.write(row.get('ref_comercial', ''))
                with c3:
                    st.write("**📝 NOMBRE DE TRABAJO:**")
                    st.write(nombre_t)
                    st.write("**⚙️ TIPO DE TRABAJO:**")
                    st.write(row.get('tipo_orden', 'N/A'))
                    st.write("**📋 OBSERVACIONES DE DISEÑO:**")
                    st.write(row.get('observaciones_diseno', 'N/A'))
                with c4:
                    st.write("**🛠️ ACCIONES Y ENLACES:**")

# BOTON DE READIOGRAFIA

                    if st.button(f"📋 VER RADIOGRAFIA OP {op_id}", key=f"btn_seg_{op_id}", use_container_width=True):
                        modal_detalle_op(row)

 # MOSTRAR      

                    link_arte = row.get('link_diseno')
                    link_ticket = row.get('link_ticket')

                    if link_arte:
                        st.link_button("🎨 VER ARTE", link_arte, use_container_width=True)
                    
                    if link_ticket:
                        st.link_button("🎫 VER TICKET", link_ticket, use_container_width=True)
                    
                    if not link_arte and not link_ticket:
                        st.caption("Sin links adjuntos")

                st.divider()

#  BOTONES DE DESCARGA ORDEN EN PDF

                if st.session_state.get('rol') in ['admin', 'ventas', 'diseño']:
                    try:
                        tipo = row.get('tipo_orden', '')
                        if "FORMAS" in tipo:
                            pdf_data = generar_op_formas(row)
                        elif "ROLLOS" in tipo:
                            pdf_data = generar_op_rollos(row)
                        else:
                            pdf_data = generar_op_rebobinado(row)
                            
                        st.download_button(
                            label=f"📥 Descargar PDF Orden {op_id}",
                            data=pdf_data,
                            file_name=f"OP_{op_id}.pdf",
                            mime="application/pdf",
                            key=f"dl_pdf_{op_id}",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"No se pudo generar el PDF: {e}")

elif menu == "🎨 Diseño y Pre-Prensa":
    st.title("🎨 Módulo de Diseño y Pre-Prensa")

    def radiografia_completa_op(datos):
        st.markdown("### 📋 RADIOGRAFIA COMPLETA DE CREACION")
        
        with st.expander("🏢 INFORMACION COMERCIAL", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            c1.write(f"**OP #:**\n{datos.get('op')}")
            c1.write(f"**OP ANTERIOR:**\n{datos.get('op_anterior')}")
            c2.write(f"**CLIENTE:**\n{datos.get('cliente')}")
            c2.write(f"**VENDEDOR:**\n{datos.get('vendedor')}")
            c3.write(f"**FECHA DE CREACION:**\n{datos.get('created_at', '')[:19]}")
            c3.write(f"**NOMBRE DEL TRABAJO:**\n{datos.get('nombre_trabajo')}")
            c4.write(f"**MATERIAL BASE:**\n{datos.get('material')}")
            c4.write(f"**GRAMAJE:**\n{datos.get('gramaje_rollos')}")

        with st.expander("⚙️ ESPECIFICACIONES TECNICAS", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown("**ADICIONALES ROLLOS**")
                st.write(f"TINTAS FRENTE: {datos.get('tintas_frente_rollos')}")
                st.write(f"TINTAS RESPALDO: {datos.get('tintas_respaldo_rollos')}")
                st.write(f"CANTIDAD SOLICITADA: {datos.get('cantidad_rollos')}")
                st.write(f"CORE: {datos.get('core')}")
            with c2:
                st.markdown("**ADICIONALES ROLLOS**")
                st.write(f"REFERENCIA COMERCIAL: {datos.get('ref_comercial')}")
                st.write(f"UNIDADES POR BOLSA: {datos.get('unidades_bolsa')}")
                st.write(f"UNIDADES POR CAJA: {datos.get('unidades_caja')}")
                st.write(f"REPETICION : {datos.get('tipo_origen')}")
            with c3:
                st.markdown("**ADICIONALES FORMAS**")
                st.write(f"PERFORACIONES: {datos.get('perforaciones_detalle')}")
                st.write(f"CODIGO DE BARRAS: {datos.get('codigo_barras_detalle')}")
                st.write(f"NUMERACION INICIAL: {datos.get('num_id')}")
                st.write(f"NUMERACION FINAL: {datos.get('num_fd')}")
            
            with c4:
                st.markdown("**ADICIONAlES DE FORMAS**")
                st.write(f"PRESENTACION: {datos.get('presentacion')}")
                st.write(f"ENCOLADA O GRAPADA POR: {datos.get('presentacion2', 0)}")
                st.write(f"NUMERO DE PARTES: {datos.get('num_partes', 0)}")

        c_obs1, c_obs2 = st.columns(2)
        with c_obs1:
            st.info(f"**📝 OBSERVACIONES DE ROLLOS:**\n{datos.get('observaciones_rollos', 'Sin observaciones')}")
            st.info(f"**📝 OBSERVACIONES DE FORMAS:**\n{datos.get('observaciones_formas', 'Sin observaciones')}")
            st.info(f"**📝 OBSERVACIONES DE AUDITORIA 1:**\n{datos.get('observaciones_diseno', 'Sin observaciones')}")
        with c_obs2:
            if datos.get('detalles_partes_json'):
                st.write("**📑 Estructura de Partes (Papel/Tintas):**")
                st.table(datos_op.get('detalles_partes_json'))
            else:
                st.write("**Tipo de Producto:** ROLLOS IMPRESOS")


#  DEFINICION DE VENTANAS

    tab1, tab2, tab3 = st.tabs(["📋 1. AUDITORIA TECNICA", "🎞️ 2. PRE-PRENSA", "⚡ 3. REVISION FINAL PLANCHA"])

#  AUDITORIA

    with tab1:
        st.subheader("🕵️ Revisión de Diseño")
        op_pendientes = supabase.table("ordenes_planeadas").select("*").ilike("proxima_area", "DISEÑO%").execute().data
        
        if op_pendientes:
            op_sel = st.selectbox("Seleccione OP:", [f"{o['op']} - {o['nombre_trabajo']} - {o['tipo_origen']}" for o in op_pendientes], key="aud_v5")
            op_id = op_sel.split(" - ")[0]
            datos_op = next((o for o in op_pendientes if str(o['op']) == str(op_id)), None)

            if datos_op:
                radiografia_completa_op(datos_op)
                st.divider()
                
                col_inputs = st.columns(2)
                with col_inputs[0]:
                    link_arte = st.text_input("Link del Arte (Drive):", value=datos_op.get('link_diseno', '') or "")
                with col_inputs[1]:
                    
                    num_ticket = st.number_input("Número de Ticket:", value=int(datos_op.get('num_ticket', 0) or 0), step=1)
                
                obs_dis = st.text_area("✍️ Notas para Pre-Prensa:", value=datos_op.get('observaciones_diseno', '') or "")
                obs_dise = st.text_area("✍️ ESPESIFICACIONE SPARA REVELAR PLANCHAS:", value=datos_op.get('observaciones_diseno2', '') or "")
                
                if st.button("✅ ENVIAR A PRE-PRENSA", use_container_width=True):
                    if link_arte and num_ticket > 0:
                        update_data = {
                            "link_diseno": link_arte, 
                            "num_ticket": num_ticket, 
                            "observaciones_diseno": obs_dis,
                            "observaciones_diseno2": obs_dise,  
                            "proxima_area": "PRE-PRENSA"
                        }
                        supabase.table("ordenes_planeadas").update(update_data).eq("op", op_id).execute()
                        st.success("Enviado a Pre-Prensa."); time.sleep(1); st.rerun()
                    else:
                        st.error("El link del ARTE y el NÚMERO DE TICKET son obligatorios.")

# PRE-PRENSA

    with tab2:
        st.subheader("🎞️ Procesamiento de Archivos")
        op_pre = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", "PRE-PRENSA").execute().data

        if op_pre:
            op_sel_2 = st.selectbox("Seleccione OP:", [f"{o['op']} - {o['nombre_trabajo']} - {o['tipo_origen']}" for o in op_pre], key="pre_v5")
            op_id_2 = op_sel_2.split(" - ")[0]
            datos_op_2 = next((o for o in op_pre if str(o['op']) == str(op_id_2)), None)

            if datos_op_2:
               
                c1, c2 = st.columns(2)
                c1.link_button("🎨 ABRIR ARTE", datos_op_2.get('link_diseno', '#'), use_container_width=True)
                c2.metric("🎫 TICKET ASIGNADO", datos_op_2.get('num_ticket', 0))

                radiografia_completa_op(datos_op_2)
                
                if st.button("🚀 ENVIAR A REVISIÓN FINAL", use_container_width=True):
                    supabase.table("ordenes_planeadas").update({"proxima_area": "REVISION_FINAL"}).eq("op", op_id_2).execute()
                    st.success("Enviado a Revisión Final."); time.sleep(1); st.rerun()

# REVISION FINAL CON PLANCHA 

    with tab3:
        st.subheader("⚡ Control de Planchas y Salida")
        op_final = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", "REVISION_FINAL").execute().data

        if op_final:
            op_sel_3 = st.selectbox("Seleccione OP:", [f"{o['op']} - {o['nombre_trabajo']} - {o['tipo_origen']}" for o in op_final], key="final_v5")
            op_id_3 = op_sel_3.split(" - ")[0]
            datos_op_3 = next((o for o in op_final if str(o['op']) == str(op_id_3)), None)

            if datos_op_3:
                st.warning(f"**Ticket:** {datos_op_3.get('num_ticket')} | **DATOS DE PLANCHAS A REVELAR:** {datos_op_3.get('observaciones_diseno2')}")
                
# Aqui agregar campos especificos de planchas  ########################################################################33
                num_plancha = st.text_input("ESPESIFIQUE LAS PLANCHAS REVELADAS:")
                
                radiografia_completa_op(datos_op_3)

                if st.button("🏁 FINALIZAR Y ENVIAR A IMPRESIÓN", use_container_width=True):

# Actualizamos a IMPRESION para que pase a la planta

                    supabase.table("ordenes_planeadas").update({"proxima_area": "IMPRESIÓN"}).eq("op", op_id_3).execute()
                    st.success("Orden enviada a planta exitosamente."); time.sleep(1); st.rerun()
        else:
            st.info("No hay órdenes pendientes para revisión de plancha.")
            
# MODULO PLANIFICACION 

elif menu == "📅 Planificación":
    st.title("Planificación de Órdenes 🌐")
    
#  SELECTOR OTIGEN DE OP

    st.markdown("<div class='section-header'>📂 ORIGEN DE LA INFORMACIÓN</div>", unsafe_allow_html=True)
    origen = st.radio("¿Cómo desea ingresar la orden?", 
                      ["Nueva (Desde cero)", "Repetición Exacta", "Repetición con Cambios"], 
                      horizontal=True)
    
# VARIABLE PARA ALMACENAR DATOS RECUPERADOS

    datos_rec = {}
    
    if "Repetición" in origen:
        col_busq1, col_busq2 = st.columns([3, 1])
        op_a_buscar = col_busq1.text_input("Ingrese el número de OP Anterior para buscar (Ej: FRI-100):")
        if col_busq2.button("🔍 Buscar y Cargar"):
            if op_a_buscar:
                try:
                    res_busq = supabase.table("ordenes_planeadas").select("*").eq("op", op_a_buscar.upper()).execute()
                    if res_busq.data:
                        datos_rec = res_busq.data[0]
                        st.success(f"✅ Datos de '{datos_rec['nombre_trabajo']}' cargados correctamente.")
                    else:
                        st.error("No se encontró la OP. Verifique el prefijo y número.")
                except Exception as e:
                    st.error(f"Error en la base de datos: {e}")
            else:
                st.warning("Por favor ingrese un número de OP.")

    st.divider()

# SELECTOR DE TIPO DE PRODUCTO

    c1, c2, c3, c4, c5 = st.columns(5)
    if c1.button("📑 FORMAS IMPRESAS"): st.session_state.sel_tipo = "FORMAS IMPRESAS"
    if c2.button("📄 FORMAS BLANCAS"): st.session_state.sel_tipo = "FORMAS BLANCAS"
    if c3.button("🌀 ROLLOS IMPRESOS"): st.session_state.sel_tipo = "ROLLOS IMPRESOS"
    if c4.button("⚪ ROLLOS BLANCOS"): st.session_state.sel_tipo = "ROLLOS BLANCOS"
    if c5.button("🌀 REBOBINADO"):st.session_state.sel_tipo = "REBOBINADO"

    if st.session_state.sel_tipo:
        t = st.session_state.sel_tipo
        prefijo = {"FORMAS IMPRESAS": "FRI-", "FORMAS BLANCAS": "FRB-", "ROLLOS IMPRESOS": "RI-", "ROLLOS BLANCOS": "RB-", "REBOBINADO": "RR-"}.get(t, "")
        p1, p2, p3, p4 = st.columns(4)

#  PERFORACIONES TODOS

        t_perf = p1.selectbox("¿Tiene Perforaciones?", ["NO","SI"], key="perf_select")

        if t_perf == "SI":
            perf_d = p1.text_area("Detalle Perforación", key="perf_det")
        else:
            perf_d = "NO"

 #  SOLO PARA FORMAS   

        if "FORMAS" in t:


            if "partes_sel" not in st.session_state:
                val_partes = int(datos_rec.get('num_partes', 1))
                st.session_state.partes_sel = val_partes if 1 <= val_partes <= 6 else 1

            g1, g2, g3, g4 = st.columns(4)

            cant_f = g1.number_input(
                "Cantidad Formas",
                0,
                value=int(datos_rec.get('cantidad_formas', 0))
            )

            st.session_state.partes_sel = g2.selectbox(
                "Número de Partes",
                [1,2,3,4,5,6],
                index=st.session_state.partes_sel - 1
            )

            partes = st.session_state.partes_sel

            idx_pres = PRESENTACIONES.index(datos_rec['presentacion']) if datos_rec.get('presentacion') in PRESENTACIONES else 0
            pres = g3.selectbox("Presentación", PRESENTACIONES, index=idx_pres)

            pres_peg = g4.selectbox("Encolada o Grapada", PRESENTACIONES2)

            t_barr = p2.selectbox("¿Tiene Código de Barras?", ["NO","SI"], key="barr_select")

            if t_barr == "SI":
                barr_d = p2.text_area("Detalle Barras", key="barr_det")
            else:
                barr_d = "NO"


            t_num = p3.selectbox("¿Tiene Numeración?", ["NO","SI"], key="num_select")

            if t_num == "SI":
                num_id = p3.text_input("Desde", key="num_desde")
                num_fd = p3.text_input("Hasta", key="num_hasta")
            else:
                num_id = "NO"
                num_fd = "NO"
        else:
            barr_d = "NO"
            num_id = "NO"
            num_fd = "NO"

#  TRANSPORTADORA (TODOS) 

        t_trans_f = p4.selectbox("¿Transportadora?", ["NO","SI"], key="trans_select")

        if t_trans_f == "SI":
            dest_f = p4.text_area("Ciudad destino", key="dest_trans")
        else:
            dest_f = "NO"
        partes = st.session_state.get("partes_sel", 1)

# BOTON COPIAR PARTE 1 A TODAS

        if "FORMAS" in t and partes > 1:
            if st.button("📋 Copiar Parte 1 a todas las partes"):

                for i in range(2, partes + 1):

                    st.session_state[f"a_{i}"] = st.session_state.get("a_1", "")
                    st.session_state[f"l_{i}"] = st.session_state.get("l_1", "")
                    st.session_state[f"p_{i}"] = st.session_state.get("p_1", "")
                    st.session_state[f"f_{i}"] = st.session_state.get("f_1", "")
                    st.session_state[f"g_{i}"] = st.session_state.get("g_1", "")
                    st.session_state[f"t_{i}"] = st.session_state.get("t_1", "")

                    st.session_state[f"tf_{i}"] = st.session_state.get("tf_1", "")
                    st.session_state[f"tr_{i}"] = st.session_state.get("tr_1", "")
                    st.session_state[f"obe_{i}"] = st.session_state.get("obe_1", "")

                st.success("Partes copiadas correctamente")
                st.rerun()
                

        with st.form("form_plan", clear_on_submit=True):
            st.subheader(f"Nueva Orden: {t} (Prefijo: {prefijo})")
            
# SECCION: DATOS GENERALES 

            f1, f2, f3 = st.columns(3)
            op_input = f1.text_input("Número de Nueva OP (Solo número) *")
            
# SI ES REPETICION SUGERIR LA OP ANTERIOR BUSCADA

            val_op_ant = datos_rec.get('op', "") if "Repetición" in origen else ""
            op_a = f2.text_input("OP Anterior", value=val_op_ant)
            
            cli = f3.text_input("Cliente *", value=datos_rec.get('cliente', ""))
            
            f4, f5 = st.columns(2)
            vend = f4.text_input("Vendedor", value=datos_rec.get('vendedor', ""))
            trab = f5.text_input("Nombre del Trabajo", value=datos_rec.get('nombre_trabajo', ""))

            if "FORMAS" in t:
                lista_p = []
                rec_partes = datos_rec.get('detalles_partes_json', [])

                for i in range(1, partes + 1):

# INTEBNTAR TRAER DAROS  DE LA  PARTE SI EXSITE REPEETICION ( NO TODOS )

                    p_data = rec_partes[i-1] if i <= len(rec_partes) else {}
                    
                    st.markdown(f"**PARTE {i}**")
                    d1, d2, d3, d4, d5, d6 = st.columns(6)
                    anc = d1.text_input(f"Ancho P{i}", key=f"a_{i}", value=p_data.get('anc', ""))
                    lar = d2.text_input(f"Largo P{i}", key=f"l_{i}", value=p_data.get('lar', ""))
                    pap = d3.text_input(f"Papel P{i}", key=f"p_{i}", value=p_data.get('papel', ""))
                    fon = d4.text_input(f"Color Fondo P{i}", key=f"f_{i}", value=p_data.get('color_fondo', "")) 
                    gra = d5.text_input(f"Gramos P{i}", key=f"g_{i}", value=p_data.get('gramos', ""))
                    tra = d6.text_input(f"Tráfico P{i}", key=f"t_{i}", value=p_data.get('trafico', ""))
                    
                    tf, tr = "N/A", "N/A"
                    obe = ""
                    if t == "FORMAS IMPRESAS":
                        t1, t2, t3 = st.columns(3)
                        tf = t1.text_input(f"Tintas Frente P{i}", key=f"tf_{i}", value=p_data.get('tf', ""))
                        tr = t2.text_input(f"Tintas Respaldo P{i}", key=f"tr_{i}", value=p_data.get('tr', ""))
                        obe = t3.text_input(f"Obs. Especial P{i}", key=f"obe_{i}", value=p_data.get('obs_parte',""))
                    
                    lista_p.append({
                        "p": i,
                        "anc": anc,
                        "lar": lar,
                        "papel": pap,
                        "color_fondo": fon,
                        "gramos": gra,
                        "tf": tf,
                        "tr": tr,
                        "trafico": tra,
                        "obs_parte": obe
                    })
                
                obs = st.text_area("Observaciones Generales Formas", value=datos_rec.get('observaciones_formas', ""))
            elif t == "REBOBINADO":

                r1, r2, r3 = st.columns(3)

                mat = r1.text_input("Material / Papel")
                gram = r2.number_input("Gramaje", 0)
                ancho = r3.text_input("Referencia Comercial",)

                r4, r5 = st.columns(2)

                cant_r = r4.number_input("Cantidad Rollos Solicitada", 0)
                objetivo = r5.text_input("Objetivo del Rebobinado")

                obs = st.text_area("Observaciones Rebobinado")
                
            else: 

#  SECCION: ROLLOS 

                r1, r2, r3 = st.columns(3)
                mat = r1.text_input("Material Base", value=datos_rec.get('material', ""))
                gram = r2.number_input("Gramaje", 0, value=int(datos_rec.get('gramaje_rollos', 0)))
                ref_c = r3.text_input("Referencia Comercial", value=datos_rec.get('ref_comercial', ""))
                
                r4, r5, r6 = st.columns(3)
                cant_r = r4.number_input("Cantidad Rollos", 0, value=int(datos_rec.get('cantidad_rollos', 0)))
                
                cores = ["13MM", "19MM", "1 PULGADA", "40 MM", "2 PULGADAS", "3 PULGADAS", " NINGUNO"]
                idx_core = cores.index(datos_rec['core']) if datos_rec.get('core') in cores else 0
                core = r5.selectbox("Core / Centro", cores, index=idx_core)
                                
                tf_r, tr_r = "N/A", "N/A"
                if t == "ROLLOS IMPRESOS":
                    ct1, ct2 = st.columns(2)
                    tf_r = ct1.text_input("Tintas Frente", value=datos_rec.get('tintas_frente_rollos', ""))
                    tr_r = ct2.text_input("Tintas Respaldo", value=datos_rec.get('tintas_respaldo_rollos', ""))
                
                r7, r8 = st.columns(2)
                ub = r7.number_input("Unidades x Bolsa", 0, value=int(datos_rec.get('unidades_bolsa', 0)))
                uc = r8.number_input("Unidades x Caja", 0, value=int(datos_rec.get('unidades_caja', 0)))
                obs = st.text_area("Observaciones Generales Rollos", value=datos_rec.get('observaciones_rollos', ""))

#  ERROR SI TIENE CAMPOS SIN LLENAR 

            if st.form_submit_button("🚀 GUARDAR PLANIFICACIÓN"):

                campos_faltantes = []

                if not op_input:
                    campos_faltantes.append("Número OP")

                if not cli:
                    campos_faltantes.append("Cliente")

                if not vend:
                    campos_faltantes.append("Vendedor")

                if not trab:
                    campos_faltantes.append("Nombre del Trabajo")

                if campos_faltantes:
                    st.error("Faltan campos obligatorios: " + ", ".join(campos_faltantes))
                    st.stop()

                op_final = f"{prefijo}{op_input.upper()}"

#  VALIDAR OP DUPLICADA

                existe_op = supabase.table("ordenes_planeadas") \
                   .select("op") \
                   .eq("op", op_final) \
                   .execute()

                if existe_op.data:
                    st.error(f"❌ La OP {op_final} ya existe. No se puede duplicar.")
                    st.stop()

                
# DEFINIR AREA INICIAL SEGUN TIPO

                if t == "FORMAS IMPRESAS":
                    ruta_inicial = "DISEÑO (AUDITORIA)"

                elif t == "FORMAS BLANCAS":
                    ruta_inicial = "IMPRESIÓN"

                elif t == "ROLLOS IMPRESOS":
                    ruta_inicial = "DISEÑO (AUDITORIA)"

                elif t == "ROLLOS BLANCOS":
                    ruta_inicial = "CORTE"
                    
                elif t == "REBOBINADO":
                    ruta_inicial = "REBOBINADORAS"  

                payload = {
                    "op": op_final,
                    "op_anterior": op_a,
                    "cliente": cli,
                    "vendedor": vend,
                    "nombre_trabajo": trab,
                    "tipo_orden": t,
                    "tipo_origen": origen,
                    "proxima_area": ruta_inicial,
                    "historial_procesos": []
                }

                if "FORMAS" in t:
                    payload.update({
                        "cantidad_formas": int(cant_f),
                        "num_partes": partes,
                        "perforaciones_detalle": perf_d,
                        "codigo_barras_detalle": barr_d,
                        "num_id": num_id,    
                        "num_fd": num_fd, 
                        "tipo_origen": origen,   
                        "presentacion2": pres_peg, 
                        "transportadora_formas": True if t_trans_f == "SI" else None,
                        "destino_formas": dest_f if t_trans_f == "SI" else None,
                        "detalles_partes_json": lista_p,
                        "presentacion": pres,
                        "observaciones_formas": obs
                    })

                elif t == "REBOBINADO":
                    payload.update({
                        "material": mat,
                        "gramaje_rollos": gram,
                        "ancho_base": ancho,
                        "tipo_origen": origen,
                        "cantidad_rollos": int(cant_r),
                        "objetivo_rebobinado": objetivo,
                        "observaciones_rollos": obs
                })

                else:
                    payload.update({
                        "material": mat,
                        "gramaje_rollos": gram,
                        "cantidad_rollos": int(cant_r),
                        "core": core,
                        "tintas_frente_rollos": tf_r,
                        "tintas_respaldo_rollos": tr_r,
                        "unidades_bolsa": int(ub),
                        "unidades_caja": int(uc),
                        "observaciones_rollos": obs,
                        "ref_comercial": ref_c,
                        "transportadora_rollos": True if t_trans_f == "SI" else None,
                        "destino_rollos": dest_f if t_trans_f == "SI" else None,
                    })

                supabase.table("ordenes_planeadas").insert(payload).execute()

                st.success(f"Orden {op_final} registrada.")
                st.session_state.sel_tipo = None

                time.sleep(1.5)
                st.rerun()

# MODULO: BODEGA PRODUCTO TERMINADO 

elif menu == "📦 salida produccion P1":
    st.title("📦 Inventario de Producto Terminado")
    
    tab_mov, tab_inv = st.tabs(["🔄 Movimientos (Entrada/Salida)", "📊 Inventario Actual"])
    
    with tab_mov:
        st.subheader("🔄 Gestión de Movimientos")
        
# IDENTIFICAR PERMISOS SEGUN ROL

        rol_usuario = st.session_state.get('rol', '').lower()
        
# DEFINE QUIN PUEDE HACER QUE DENTRO DEL MODULO 

        puede_ingresar = rol_usuario in ['admin', 'patinador_roll' ] 
        puede_despachar = rol_usuario in ['admin', 'ventas']

#  SELECTOR DE OPERACION FILTRADO

        opciones_disponibles = []
        if puede_ingresar: opciones_disponibles.append("➕ ENTRADA (Ingreso)")
        if puede_despachar: opciones_disponibles.append("➖ SALIDA (Despacho)")

        if not opciones_disponibles:
            st.warning("⚠️ Tu rol no tiene permisos para registrar movimientos en bodega.")
        else:
            tipo_accion = st.radio("Seleccione operación:", opciones_disponibles, horizontal=True)
            
            productos_db = supabase.table("bodega_producto_terminado").select("*").execute().data
            nombres_existentes = sorted([p['nombre_trabajo'] for p in productos_db])

            with st.form("form_movimiento_separado"):
                col1, col2 = st.columns(2)
                
                with col1:

#  SI ES INGRESO SEJA CREAR SI ES SALIDA SOLO SELECCIONA DE LO YA EXISTENTE

                    if "ENTRADA" in tipo_accion:
                        nuevo_o_existente = st.checkbox("¿Es un producto nuevo en bodega?")
                        if nuevo_o_existente:
                            nom_trabajo = st.text_input("Nombre del Trabajo (NUEVO)").upper()
                        else:
                            nom_trabajo = st.selectbox("Seleccione Trabajo Existente:", [""] + nombres_existentes)
                    else:
                        st.info("ℹ️ Solo puede dar salida a productos que ya están en el inventario.")
                        nom_trabajo = st.selectbox("Seleccione Trabajo para Despacho:", [""] + nombres_existentes)
                    
                    tipo_prod = st.selectbox("Tipo de Producto:", ["BLANCO", "IMPRESO", "REBOBINADO"])
                
                with col2:
                    c_cajas = st.number_input("Cantidad de Cajas", min_value=0, step=1)
                    c_rollos = st.number_input("Cantidad de Rollos", min_value=0, step=1)
                    notas = st.text_input("Observaciones (Ej: Factura # o Cliente)")

# BOTON DINAMICO DE REGISTRO A INGRESOS

                texto_boton = "🚀 REGISTRAR ENTRADA" if "ENTRADA" in tipo_accion else "🚚 REGISTRAR SALIDA"
                btn_procesar = st.form_submit_button(texto_boton)

                if btn_procesar:
                    if not nom_trabajo or nom_trabajo == "":
                        st.error("Debe especificar el nombre del trabajo.")
                    elif c_cajas == 0 and c_rollos == 0:
                        st.warning("Ingrese una cantidad válida de cajas o rollos.")
                    else:
                        fecha_mov = hora_colombia().isoformat()
                        producto_actual = next((p for p in productos_db if p['nombre_trabajo'] == nom_trabajo), None)
                        
# LOGICA DE SUMA Y RESTA

                        es_entrada = "ENTRADA" in tipo_accion
                        factor = 1 if es_entrada else -1

# VALIDACION DE STOCK PARA SALIDAS

                        if not es_entrada:
                            if not producto_actual:
                                st.error("El producto no existe en inventario.")
                                st.stop()
                            if c_cajas > producto_actual.get('stock_cajas', 0):
                                st.error(f"❌ Stock insuficiente. Solo hay {producto_actual['stock_cajas']} cajas disponibles.")
                                st.stop()

# ACTUALIZAR O INSERTAR EN BODEGA ACTUAL

                        try:
                            if producto_actual:

# ACTUALIZAR EXISTENTE

                                nuevo_stk_cajas = producto_actual['stock_cajas'] + (c_cajas * factor)
                                nuevo_stk_rollos = producto_actual['stock_rollos'] + (c_rollos * factor)
                                
                                supabase.table("bodega_producto_terminado").update({
                                    "stock_cajas": nuevo_stk_cajas,
                                    "stock_rollos": nuevo_stk_rollos,
                                    "ultima_actualizacion": fecha_mov,
                                    "observaciones": notas  
                                }).eq("id", producto_actual['id']).execute()
                            
                            elif es_entrada:

# INSERTAR NUEVO (Solo si es entrada)

                                supabase.table("bodega_producto_terminado").insert({
                                    "nombre_trabajo": nom_trabajo,
                                    "tipo_producto": tipo_prod,
                                    "stock_cajas": c_cajas,
                                    "stock_rollos": c_rollos,
                                    "ultima_actualizacion": fecha_mov,
                                    "observaciones": notas
                                }).execute()

#  REGISTRAR SIEMPRE EN HISTORIAL 

                            supabase.table("bodega_historial").insert({
                                "nombre_trabajo": nom_trabajo,
                                "tipo_movimiento": "ENTRADA" if es_entrada else "SALIDA",
                                "cajas": c_cajas,
                                "rollos": c_rollos,
                                "fecha": fecha_mov,
                                "usuario": st.session_state.get('nombre_usuario', 'Sistema'),
                                "observaciones": notas
                            }).execute()

                            st.success(f"✅ {texto_boton} exitoso para: {nom_trabajo}")
                            time.sleep(1.2)
                            st.rerun()
                        
                        except Exception as e:
                            st.error(f"Error al procesar en base de datos: {e}")

# PESTAÑA DE INVENTARIO ACTUAL

    with tab_inv:
        st.subheader("📊 Existencias en Bodega")
        
        res_bodega = supabase.table("bodega_producto_terminado").select("*").order("nombre_trabajo").execute().data
        
        if res_bodega:
            df_bodega = pd.DataFrame(res_bodega)
            
            cols_esperadas = ['nombre_trabajo', 'tipo_producto', 'stock_cajas', 'stock_rollos', 'ultima_actualizacion', 'observaciones']
            cols_finales = [c for c in cols_esperadas if c in df_bodega.columns]
            
            df_show = df_bodega[cols_finales].copy()
            
# RENOMBRAR COLUMBAS PARA VISUALIZACION 

            nombres_columnas = {
                'nombre_trabajo': 'TRABAJO',
                'tipo_producto': 'TIPO',
                'stock_cajas': 'CAJAS',
                'stock_rollos': 'ROLLOS',
                'ultima_actualizacion': 'ÚLT. MOVIMIENTO',
                'observaciones': 'OBSERVACIONES'
            }
            df_show.rename(columns=nombres_columnas, inplace=True)
            
# BUSCADOR RAPIDO

            busqueda_b = st.text_input("🔍 Filtrar inventario por nombre...")
            if busqueda_b:
                df_show = df_show[df_show['TRABAJO'].str.contains(busqueda_b.upper(), na=False)]
            
# MOSTRAR TABLAS 

            st.dataframe(df_show, use_container_width=True, hide_index=True)
            
# ALERTAS D ESTOCK BAJO 

            if 'CAJAS' in df_show.columns:
                bajo_stock = df_show[df_show['CAJAS'] <= 2]
                if not bajo_stock.empty:
                    st.warning(f"⚠️ Hay {len(bajo_stock)} productos con stock crítico (2 o menos cajas).")
        else:
            st.info("La bodega está vacía actualmente.")

# MODULO: REPORTES 

elif menu == "📊 Reportes Admin":
        st.title("📊 Panel de Control y Reportes")
        
        tab_historial, tab_muertos, tab_paradas = st.tabs([
            "📦 Historial de Bodega", 
            "⏳ Disponibilidad (Máquina Libre)", 
            "🛑 Reporte de Paradas (Fallas)"
        ])
        
        with tab_historial:
            st.subheader("Historial de Movimientos de Bodega")
            res_h = supabase.table("bodega_historial").select("*").order("fecha", desc=True).execute().data
            if res_h:
                df_h = pd.DataFrame(res_h)
                st.dataframe(df_h, use_container_width=True, hide_index=True)
            else:
                st.info("Sin registros en bodega.")

        with tab_muertos:
            st.subheader("⏳ Tiempo de Máquina Libre (Sin Órdenes)")

#  TOMA DE TIEMPOS DE MAQUIA LIBRE ENTRE UN AOP Y OTRA 

            res_m = supabase.table("tiempos_muertos").select("*").order("fecha", desc=True).execute().data
            if res_m:
                df_m = pd.DataFrame(res_m)
                if 'duracion_min' in df_m.columns:
                    total_libre = df_m['duracion_min'].sum()
                    st.metric("Total Tiempo Libre (Ocioso)", f"{total_libre} min")
                st.dataframe(df_m, use_container_width=True, hide_index=True)
            else:
                st.info("No hay registros de tiempo libre.")

        with tab_paradas:
            st.subheader("🛑 Reporte de Fallas y Paradas Técnicas")

# AQUI S EMUESTRA PORQUE LA MAQUINA SE DERUBO 

            res_p = supabase.table("paradas_maquina").select("*").order("fecha", desc=True).execute().data
            if res_p:
                df_p = pd.DataFrame(res_p)

                if 'duracion_min' in df_p.columns:
                    total_parada = df_p['duracion_min'].sum()
                    st.metric("Total Tiempo Perdido por Fallas", f"{total_parada} min", delta_color="inverse")
                
                st.dataframe(df_p, use_container_width=True, hide_index=True)
            else:
                st.info("No hay reportes de fallas técnicos.")


elif menu == "📦 Almacen/Despachos":
    st.title("📦 Inventario de Productos Almacen")
    
    tab_mov, tab_inv = st.tabs(["🔄 Movimientos (Entrada/Salida)", "📊 Inventario Actual"])
    
    with tab_mov:
        st.subheader("🔄 Gestión de Movimientos")
        
# IDENTIFICAR PERMISOS SEGUN ROL

        rol_usuario = st.session_state.get('rol', '').lower()
        
# DEFINE QUIN PUEDE HACER QUE DENTRO DEL MODULO 

        puede_ingresar = rol_usuario in ['admin', 'jefe_log', 'patinador_log' ] 
        puede_despachar = rol_usuario in ['admin', 'jefe_log', 'patinador_log', 'aux_log']

#  SELECTOR DE OPERACION FILTRADO

        opciones_disponibles = []
        if puede_ingresar: opciones_disponibles.append("➕ ENTRADA DE MERCANCIA (Ingreso)")
        if puede_despachar: opciones_disponibles.append("➖ SALIDA DE MERCANCIA (Despacho)")

        if not opciones_disponibles:
            st.warning("⚠️ Tu rol no tiene permisos para registrar movimientos en bodega.")
        else:
            tipo_accion = st.radio("Seleccione operación:", opciones_disponibles, horizontal=True)
            
            productos_db = supabase.table("almacen_producto_terminado").select("*").execute().data
            nombres_existentes = sorted([p['nombre_trabajo'] for p in productos_db])

            with st.form("form_movimiento_separado"):
                col1, col2 = st.columns(2)
                
                with col1:
#  SI ES INGRESO SEJA CREAR SI ES SALIDA SOLO SELECCIONA DE LO YA EXISTENTE

                    if "ENTRADA" in tipo_accion:
                        nuevo_o_existente = st.checkbox("¿Es un producto nuevo en bodega?")
                        if nuevo_o_existente:
                            nom_trabajo = st.text_input("Nombre del Trabajo (NUEVO)").upper()
                        else:
                            nom_trabajo = st.selectbox("Seleccione Trabajo Existente:", [""] + nombres_existentes)
                    else:
                        st.info("ℹ️ Solo puede dar salida a productos que ya están en el inventario.")
                        nom_trabajo = st.selectbox("Seleccione Trabajo para Despacho:", [""] + nombres_existentes)
                    
                    tipo_prod = st.selectbox("Tipo de Producto:", ["BLANCO", "IMPRESO", "REBOBINADO", "ADHESIVO"])
                
                with col2:
                    c_cajas = st.number_input("Cantidad de Cajas", min_value=0, step=1)
                    c_rollos = st.number_input("Cantidad de Rollos", min_value=0, step=1)
                    notas = st.text_input("Observaciones (Ej: Factura # o Cliente)")

# BOTON DINAMICO DE REGISTRO A INGRESOS

                texto_boton = "🚀 REGISTRAR ENTRADA" if "ENTRADA" in tipo_accion else "🚚 REGISTRAR SALIDA"
                btn_procesar = st.form_submit_button(texto_boton)

                if btn_procesar:
                    if not nom_trabajo or nom_trabajo == "":
                        st.error("Debe especificar el nombre del trabajo.")
                    elif c_cajas == 0 and c_rollos == 0:
                        st.warning("Ingrese una cantidad válida de cajas o rollos.")
                    else:
                        fecha_mov = hora_colombia().isoformat()
                        producto_actual = next((p for p in productos_db if p['nombre_trabajo'] == nom_trabajo), None)
                        
# LOGICA DE SUMA Y RESTA

                        es_entrada = "ENTRADA" in tipo_accion
                        factor = 1 if es_entrada else -1

# VALIDACION DE STOCK PARA SALIDAS

                        if not es_entrada:
                            if not producto_actual:
                                st.error("El producto no existe en inventario.")
                                st.stop()
                            if c_cajas > producto_actual.get('stock_cajas', 0):
                                st.error(f"❌ Stock insuficiente. Solo hay {producto_actual['stock_cajas']} cajas disponibles.")
                                st.stop()

# ACTUALIZAR O INSERTAR EN BODEGA ACTUAL

                        try:
                            if producto_actual:

# ACTUALIZAR EXISTENTE

                                nuevo_stk_cajas = producto_actual['stock_cajas'] + (c_cajas * factor)
                                nuevo_stk_rollos = producto_actual['stock_rollos'] + (c_rollos * factor)
                                
                                supabase.table("almacen_producto_terminado").update({
                                    "stock_cajas": nuevo_stk_cajas,
                                    "stock_rollos": nuevo_stk_rollos,
                                    "ultima_actualizacion": fecha_mov,
                                    "observaciones": notas  
                                }).eq("id", producto_actual['id']).execute()
                            
                            elif es_entrada:

# INSERTAR NUEVO (Solo si es entrada)

                                supabase.table("almacen_producto_terminado").insert({
                                    "nombre_trabajo": nom_trabajo,
                                    "tipo_producto": tipo_prod,
                                    "stock_cajas": c_cajas,
                                    "stock_rollos": c_rollos,
                                    "ultima_actualizacion": fecha_mov,
                                    "observaciones": notas
                                }).execute()

#  REGISTRAR SIEMPRE EN HISTORIAL 

                            supabase.table("bodega_historial").insert({
                                "nombre_trabajo": nom_trabajo,
                                "tipo_movimiento": "ENTRADA" if es_entrada else "SALIDA",
                                "cajas": c_cajas,
                                "rollos": c_rollos,
                                "fecha": fecha_mov,
                                "usuario": st.session_state.get('nombre_usuario', 'Sistema'),
                                "observaciones": notas
                            }).execute()

                            st.success(f"✅ {texto_boton} exitoso para: {nom_trabajo}")
                            time.sleep(1.2)
                            st.rerun()
                        
                        except Exception as e:
                            st.error(f"Error al procesar en base de datos: {e}")

# PESTAÑA DE INVENTARIO ACTUAL

    with tab_inv:
        st.subheader("📊 Existencias en Bodega")
        
        res_bodega = supabase.table("almacen_producto_terminado").select("*").order("nombre_trabajo").execute().data
        
        if res_bodega:
            df_bodega = pd.DataFrame(res_bodega)
            
            cols_esperadas = ['nombre_trabajo', 'tipo_producto', 'stock_cajas', 'stock_rollos', 'ultima_actualizacion', 'observaciones']
            cols_finales = [c for c in cols_esperadas if c in df_bodega.columns]
            
            df_show = df_bodega[cols_finales].copy()
            
# RENOMBRAR COLUMBAS PARA VISUALIZACION 

            nombres_columnas = {
                'nombre_trabajo': 'TRABAJO',
                'tipo_producto': 'TIPO',
                'stock_cajas': 'CAJAS',
                'stock_rollos': 'ROLLOS',
                'ultima_actualizacion': 'ÚLT. MOVIMIENTO',
                'observaciones': 'OBSERVACIONES'
            }
            df_show.rename(columns=nombres_columnas, inplace=True)
            
# BUSCADOR RAPIDO

            busqueda_b = st.text_input("🔍 Filtrar inventario por nombre...")
            if busqueda_b:
                df_show = df_show[df_show['TRABAJO'].str.contains(busqueda_b.upper(), na=False)]
            
# MOSTRAR TABLAS 

            st.dataframe(df_show, use_container_width=True, hide_index=True)
            
# ALERTAS D ESTOCK BAJO 

            if 'CAJAS' in df_show.columns:
                bajo_stock = df_show[df_show['CAJAS'] <= 2]
                if not bajo_stock.empty:
                    st.warning(f"⚠️ Hay {len(bajo_stock)} productos con stock crítico (2 o menos cajas).")
        else:
            st.info("La bodega está vacía actualmente.")

elif menu == "⏱️ Seguimiento Cortadoras":
        st.header("⏱️ Seguimiento Horario de Cortadoras")
        
        # Usamos las máquinas de corte configuradas en tus CONSTANTES
        maq_sel = st.selectbox("Seleccione la Máquina", MAQUINAS["CORTE"])
        
        t1, t2 = st.tabs(["📝 Registro", "📋 Historial"])
        
        with t1:
            with st.form("f_seg_hor", clear_on_submit=True):
                ca, cb, cc = st.columns(3)
                with ca:
                    op_s = st.text_input("OP")
                    nt_s = st.text_input("Nombre Trabajo")
                    tipo_p = st.text_input("Tipo de Papel / Material")
                    turno_s = st.selectbox("Turno", ["Mañana", "Tarde", "Noche"])
                with cb:
                    m_r = st.number_input("Metros de Rollo", min_value=0, value=0)
                    med_r = st.text_input("Medida de Rollo")
                    u_c = st.number_input("Unid/Caja", min_value=0, value=0)
                    n_c = st.number_input("Número Cajas", min_value=0, value=0)
                with cc:
                    n_v = st.number_input("Varillas", min_value=0, value=0)
                    p_d = st.number_input("Desp. KG", min_value=0.0, value=0.0, step=0.1)
                    mot_d = st.text_input("Motivo Desp.")
                    obs = st.text_area("Observaciones")
                
                # Campos de cierre de turno opcionales
                st.markdown("---")
                st.markdown("##### 📦 Datos de Cierre de Turno (Opcional)")
                col_x, col_y = st.columns(2)
                with col_x: 
                    c_t = st.number_input("TOTAL CAJAS TURNO", min_value=0, value=0)
                with col_y: 
                    v_t = st.number_input("TOTAL VARILLAS TURNO", min_value=0, value=0)
                
                if st.form_submit_button("🚀 Guardar Avance"):
                    if not op_s:
                        st.error("⚠️ El número de OP es obligatorio para registrar el avance.")
                    else:
                        try:
                            datos_insertar = {
                                "fecha": hora_colombia().strftime("%Y-%m-%d"), 
                                "hora_registro": hora_colombia().strftime("%H:%M:%S"),
                                "turno": turno_s, 
                                "maquina": maq_sel, 
                                "op": str(op_s), 
                                "nombre_trabajo": nt_s,
                                "tipo_papel": tipo_p, 
                                "metros_rollo": m_r, 
                                "medida_rollo": med_r,
                                "unidades_por_caja": u_c, 
                                "num_varillas": n_v, 
                                "num_cajas": n_c,
                                "peso_desperdicio": p_d, # CORREGIDO AQUÍ
                                "motivo_desperdicio_seg": mot_d, 
                                "observaciones": obs,
                                "total_cajas_empacadas": c_t, 
                                "total_varillas_sacadas": v_t
                            }
                            
                            supabase.table("seguimiento_cortadoras").insert(datos_insertar).execute()
                            st.success(f"🎉 Avance de la máquina {maq_sel} guardado exitosamente en la nube.")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar en Supabase: {e}")
                            
        with t2:
            st.markdown(f"### Historial Reciente - {maq_sel}")
            try:
                query = supabase.table("seguimiento_cortadoras").select("*").eq("maquina", maq_sel)
                respuesta = query.order("id", desc=True).execute()
                
                if respuesta.data:
                    df_h = pd.DataFrame(respuesta.data)
                    
                    # CORREGIDO: 'peso_desperdicio' con D
                    columnas_visibles = ["fecha", "hora_registro", "turno", "op", "nombre_trabajo", "num_cajas", "num_varillas", "peso_desperdicio", "observaciones"]
                    
                    # Renombrar las columnas para que se vea estético en pantalla
                    df_mostrar = df_h[columnas_visibles].rename(columns={
                        "fecha": "Fecha",
                        "hora_registro": "Hora",
                        "turno": "Turno",
                        "op": "OP",
                        "nombre_trabajo": "Trabajo",
                        "num_cajas": "Cajas",
                        "num_varillas": "Varillas",
                        "peso_desperdicio": "Desp. (KG)",
                        "observaciones": "Observaciones"
                    })
                    
                    st.dataframe(df_mostrar, use_container_width=True)
                else:
                    st.info("No hay registros previos para esta máquina.")
            except Exception as e:
                st.error(f"Error al cargar el historial: {e}")

# MODULO DE INVENTARIO CORES Y CAJAS

elif menu == "📦 Inventario":
    st.title("Gestión de Suministros (Cores y Cajas)")
    
    tab1, tab2 = st.tabs(["📥 Ingresar Stock", "📊 Ver Existencias"])
    
    with tab1:
        tipo_insumo = st.radio("¿Qué va a ingresar?", ["CORES", "CAJAS"], horizontal=True)
        tabla_db = "inventario_cores" if tipo_insumo == "CORES" else "inventario_cajas"
        col_nombre = "nombre_core" if tipo_insumo == "CORES" else "nombre_caja"
        
# TRAER DATOS DE LA TABLA SEGUN SELECCION 

        items_db = supabase.table(tabla_db).select("*").execute().data
        opciones = {item[col_nombre]: item['id'] for item in items_db}
        
        with st.form("entrada_suministros"):
            sel_item = st.selectbox(f"Seleccione {tipo_insumo[:-1]}", list(opciones.keys()))
            cant_n = st.number_input("Cantidad que ingresa (unidades)", min_value=1, step=1)
            
            if st.form_submit_button("Actualizar Stock Dentrada"):
                id_sel = opciones[sel_item]
                actual = next(i for i in items_db if i["id"] == id_sel)["stock_actual"]
                supabase.table(tabla_db).update({"stock_actual": actual + cant_n}).eq("id", id_sel).execute()
                st.success(f"Stock de {sel_item} actualizado a {actual + cant_n}")
                time.sleep(1)
                st.rerun()

        with st.form("salida_suministros"):
            sel_item = st.selectbox(f"Seleccione {tipo_insumo[:-1]}", list(opciones.keys()))
            cant_n = st.number_input("Cantidad que ingresa (unidades)", min_value=1, step=1)
            
            if st.form_submit_button("Actualizar Stock Salida"):
                id_sel = opciones[sel_item]
                actual = next(i for i in items_db if i["id"] == id_sel)["stock_actual"]
                supabase.table(tabla_db).update({"stock_actual": actual - cant_n}).eq("id", id_sel).execute()
                st.success(f"Stock de {sel_item} actualizado a {actual - cant_n}")
                time.sleep(1)
                st.rerun()

    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Cores")
            st.dataframe(pd.DataFrame(supabase.table("inventario_cores").select("*").execute().data), use_container_width=True)
        with c2:
            st.subheader("Cajas")
            st.dataframe(pd.DataFrame(supabase.table("inventario_cajas").select("*").execute().data), use_container_width=True)

#  VALIDACION DE ACCESO A AREAS DE PRODUCCION 

elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación", "🌀 Rebobinadoras"]:
    rol_actual = st.session_state.get("rol", "operario").lower()

# DICCIONARIO DE PERMISOS UNIFICADO

    PERMISOS = {
        "admin": ["TODOS"],
        "ventas": ["TODOS"],
        "supervisor_imp": ["IMPRESIÓN", "COLECTORAS"],
        "supervisor_cor": ["CORTE"],
        "supervisor_reb": ["REBOBINADORAS"],
        "supervisor_enc": ["ENCUADERNACIÓN"]
    }
#

    area_act = menu.split(" ")[1].upper()
    
    permisos_del_usuario = PERMISOS.get(rol_actual, [])

    if "TODOS" not in permisos_del_usuario and area_act not in permisos_del_usuario:
        st.error(f"⛔ El rol '{rol_actual}' no tiene permiso para el área {area_act}")
        st.stop()

    st.markdown(f"<div class='title-area'>PANEL DE PRODUCCIÓN: {area_act}</div>", unsafe_allow_html=True)
    
    activos_data = supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data
    activos = {a['maquina']: a for a in activos_data}
    
    cols = st.columns(3)
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols[idx % 3]:
            if m in activos:
                tr = activos[m]

                st.markdown(f"<div class='card-produccion'>🟡 EN PROCESO<br>{m}<br>OP: {tr['op']}</div>", unsafe_allow_html=True)

 # LOGICA DE PARADAS TECNICAS 

                if not tr.get("pausado"):

# BOTON DE PARADA 

                    with st.popover("🚨 REGISTRAR PARADA"):
                        motivo_p = st.selectbox("Motivo de parada:", MOTIVOS_PARADA, key=f"mot_{m}")
                        if st.button("Confirmar Parada", key=f"btn_p_{m}", type="primary"):
                            supabase.table("trabajos_activos").update({
                                "pausado": True,
                                "inicio_pausa": hora_colombia().isoformat(),
                                "motivo_pausa": motivo_p 
                            }).eq("maquina", m).execute()
                            st.rerun()
                else:

# MOSTRAR PORQUE ESTA DETENIDA LA AMQUINA 

                    st.error(f"DETENIDA POR: {tr.get('motivo_pausa', 'Sin motivo')}")
                    if st.button(f"▶️ REANUDAR TRABAJO", key=f"r_{m}", type="secondary"):
                        try:
                            inicio_p = datetime.fromisoformat(tr["inicio_pausa"].replace("Z", "+00:00"))
                            ahora = hora_colombia()
                            pausa_segundos = (ahora - inicio_p).total_seconds()
            
# GUARDAR ENH LA TABLA DE TIEMPOS MUERTOS

                            supabase.table("paradas_maquina").insert({
                                "maquina": m,
                                "motivo": tr.get('motivo_pausa'),
                                "inicio": tr["inicio_pausa"],
                                "fin": ahora.isoformat(),
                                "duracion_segundos": pausa_segundos
                            }).execute()

# ACTUALIZAR EL REGISTRO DE ACTIVOS PARA IR TRABAJANO

                            nuevo_tiempo_acumulado = tr.get("tiempo_pausa", 0) + pausa_segundos
                            supabase.table("trabajos_activos").update({
                                "pausado": False,
                                "tiempo_pausa": nuevo_tiempo_acumulado,
                                "inicio_pausa": None,
                                "motivo_pausa": None
                            }).eq("maquina", m).execute()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

#  BOTON FINALIZAR SIEMPRE VERLO

                if st.button(f"✅ FINALIZAR TRABAJO", key=f"f_{m}"):
                    st.session_state.rep = tr
                    st.rerun()
            else:
                st.markdown(f"<div class='card-vacia'>⚪ DISPONIBLE<br>{m}</div>", unsafe_allow_html=True)
                ops_p = supabase.table("ordenes_planeadas").select("*").or_(f"proxima_area.eq.{area_act},estado_parcial.eq.ACTIVO EN {area_act}").execute().data
                if ops_p:
                    op_dict = {f"{o['op']} - {o['nombre_trabajo']}": o['op'] for o in ops_p}

                    sel_op_label = st.selectbox("Seleccionar OP", list(op_dict.keys()), key=f"s_{m}")
                    sel_op = op_dict[sel_op_label]
                    
                    if st.button(f"🚀 INICIAR {m}", key=f"str_{m}"):
                        ahora_iso = hora_colombia().isoformat()
    
# INTENTAR BUSCAR HORA DE CUANDO TERMINO EL ULTIMO TRABAJO  

                        ultimo_registro = supabase.table("tiempos_muertos").select("fin").eq("maquina", m).order("fin", desc=True).limit(1).execute()
    
                        if ultimo_registro.data:
                            fin_ultimo = datetime.fromisoformat(ultimo_registro.data[0]["fin"].replace("Z", "+00:00"))
                            ocio_segundos = (hora_colombia() - fin_ultimo).total_seconds()
        
# GUARDA TIEMPO Q8UE NESTUBNO LIBRE O SIN TRABAJO 

                            if ocio_segundos > 360: # Solo si fue mas de 3 minuto
                                supabase.table("tiempos_muertos").insert({
                                    "maquina": m,
                                    "motivo": "TIEMPO LIBRE (ENTRE OPs)",
                                    "inicio": ultimo_registro.data[0]["fin"],
                                    "fin": ahora_iso,
                                    "duracion_segundos": ocio_segundos
                                }).execute()

# INICIAR TRABAJO NORMAL

                        supabase.table("trabajos_activos").insert({
                            "maquina": m,
                            "area": area_act,
                            "op": sel_op,
                            "hora_inicio": ahora_iso,
                            "pausado": False,
                            "tiempo_pausa": 0,
                            "inicio_pausa": None
                        }).execute()
                        st.rerun()

    if st.session_state.rep and st.session_state.rep["area"] == area_act:
        r = st.session_state.rep
        st.divider()
        with st.form("cierre_tecnico_completo"):
            st.warning(f"### REGISTRO DE CIERRE: OP {r['op']}")
            op_name = st.text_input("Nombre del Operario *")
            auxiliar = st.text_input("Auxiliar")
            datos_c = {}
            
            if area_act == "IMPRESIÓN":
                c1, c2, c3 = st.columns(3)
                datos_c['marca_papel_i'] = c1.text_input("marca de papel",)
                datos_c['medida_papel'] = c2.number_input("medida de papel", 0)
                datos_c['metros_impresos'] = c3.number_input("Metros", 0)
                datos_c['imagenes_impresas'] = c1.number_input("n° imagenes ", 0)
                datos_c['desperdicio_kg'] = c2.number_input("Desperdicio Kg", 0)
                datos_c['planchas'] = c3.number_input("planchas gastadas", 0)

            elif area_act == "CORTE":
                c1, c2, c3 = st.columns(3)
                datos_c['tipo_papel'] = c1.text_input("Tipo de papel")
                datos_c['marca_papel_c'] = c2.text_input("Marca de papel")
                datos_c['ancho_bobina'] = c3.number_input("Ancho de bobina", 0)
                
                datos_c['imagenes_corte'] = c1.number_input("Imágenes/Bobina", 0)
                datos_c['gramos_bobinas'] = c2.number_input("Gramaje de bobina", 0)
                datos_c['rollos_finales'] = c3.number_input("Total Rollos cortados", 0)

                st.markdown("---")

# CNSUMO DE CAJAS Y CORES
                
                col_inv1, col_inv2 = st.columns(2)
                
                with col_inv1:
                    st.subheader("🌀 CONSUMO DE CORES")
                    cores_res = supabase.table("inventario_cores").select("id, nombre_core").execute().data
                    dict_cores = {c['nombre_core']: c['id'] for c in cores_res}
                    tubo_usado = st.selectbox("¿Qué TUBO/CORE utilizó?", ["Seleccione..."] + list(dict_cores.keys()))
                    if tubo_usado != "Seleccione...":
                        datos_c['id_tubo_inventario'] = dict_cores[tubo_usado]
                        datos_c['nombre_tubo'] = tubo_usado
                
                with col_inv2:
                    st.subheader("📦 CONSUMO DE CAJAS")
                    cajas_res = supabase.table("inventario_cajas").select("id, nombre_caja").execute().data
                    dict_cajas = {c['nombre_caja']: c['id'] for c in cajas_res}
                    caja_usada = st.selectbox("¿Qué CAJA utilizó?", ["Seleccione..."] + list(dict_cajas.keys()))
                    if caja_usada != "Seleccione...":
                        datos_c['id_caja_inventario'] = dict_cajas[caja_usada]
                        datos_c['nombre_caja'] = caja_usada

                st.markdown("---")

                # CALCULOS AUTOMATICOS
                rollos = datos_c.get('rollos_finales', 0)
                imagenes = datos_c.get('imagenes_corte', 0)

                # Recuperar unidades_caja de la OP activa
                op_data_corte = supabase.table("ordenes_planeadas").select("unidades_caja").eq("op", r['op']).single().execute().data
                uds_caja_op = int(op_data_corte.get('unidades_caja', 0)) if op_data_corte else 0

                varillas_auto = int(rollos / imagenes) if imagenes > 0 else 0
                cajas_auto    = int(rollos / uds_caja_op) if uds_caja_op > 0 else 0

                datos_c['varillas_finales'] = varillas_auto
                datos_c['cajas_totales']    = cajas_auto

                # Mostrar resultados calculados para que el operario los vea
                col_r1, col_r2 = st.columns(2)
                col_r1.info(f"🔩 **Varillas calculadas:** {varillas_auto}  \n_(Rollos {rollos} ÷ Imágenes/Bobina {imagenes})_")
                col_r2.info(f"📦 **Cajas calculadas:** {cajas_auto}  \n_(Rollos {rollos} ÷ Uds/Caja OP: {uds_caja_op})_")

                f3 = st.columns(1)[0]
                datos_c['desperdicio'] = f3.number_input("Total desperdicio (Kg)", 0)
## COLECTORAS

            elif area_act == "COLECTORAS":
                c1, c2, c3 = st.columns(3) 
                datos_c['tipo_papel'] = c1.text_input("tipo de papel")
                datos_c['formas_colectadas'] = c2.number_input("total formas colectadas", 0)
                datos_c['partes'] = c3.number_input("total partes colectadas", 0)
                
                st.markdown("---")
                datos_c['destino_final'] = st.radio(
                    "¿Cuál es el siguiente paso?",
                    ["Enviar a Encuadernación", "Finalizar en Colectora"],
                    index=0
                )
# CONSUMO DE CAJAS EN COLECTORAS
                st.markdown("---")
                col_inv_col = st.columns(2)
                with col_inv_col[0]:
                    st.subheader("📦 CONSUMO DE CAJAS")
                    cajas_res = supabase.table("inventario_cajas").select("id, nombre_caja").execute().data
                    dict_cajas = {c['nombre_caja']: c['id'] for c in cajas_res}
                    caja_usada = st.selectbox("¿Qué CAJA utilizó?", ["Seleccione..."] + list(dict_cajas.keys()), key="inv_col")
                    if caja_usada != "Seleccione...":
                        datos_c['id_caja_inventario'] = dict_cajas[caja_usada]
                        datos_c['nombre_caja'] = caja_usada
                
                with col_inv_col[1]:
                    datos_c['cajas_totales'] = st.number_input("Total Cajas Empacadas", 0, key="cant_col")
                st.markdown("---")
                
                datos_c['formas_dañadas'] = c2.number_input("formas dañadas", 0)
                datos_c['tipo_pegado'] = c3.text_input("que tipo de pegue lleva")

            elif area_act == "ENCUADERNACIÓN":
                c1, c2, c3 = st.columns(3)
                datos_c['tipo_presentacion'] = c1.text_input("presentacion final")
                datos_c['unidades_caja'] = c2.number_input("cantidad por caja", 0)
                
#  CONSUMO DE CAJAS EN ENCUADERNACION
                st.markdown("---")
                col_inv_enc = st.columns(2)
                with col_inv_enc[0]:
                    st.subheader("📦 CONSUMO DE CAJAS")
                    cajas_res = supabase.table("inventario_cajas").select("id, nombre_caja").execute().data
                    dict_cajas = {c['nombre_caja']: c['id'] for c in cajas_res}
                    caja_usada = st.selectbox("¿Qué CAJA utilizó?", ["Seleccione..."] + list(dict_cajas.keys()), key="inv_enc")
                    if caja_usada != "Seleccione...":
                        datos_c['id_caja_inventario'] = dict_cajas[caja_usada]
                        datos_c['nombre_caja'] = caja_usada
                
                with col_inv_enc[1]:
                    datos_c['cajas_totales'] = st.number_input("Total Cajas Empacadas", 0, key="cant_enc")
                st.markdown("---")

                datos_c['tipo_pegado'] = c1.text_input("lugar de pegado")
                datos_c['desperdicio'] = c2.number_input("peso desperdicio", 0)
                datos_c['total_formas'] = c3.number_input("total formas procesadas", 0)

            elif area_act == "REBOBINADORAS":
                c1, c2, c3 = st.columns(3)
                datos_c['tipo_papel'] = c1.text_input("Tipo de papel")
                datos_c['ancho_entrada'] = c2.number_input("Gramaje", 0)
                datos_c['ancho_salida'] = c3.number_input("Ancho salida (si es un corte ponga las medidas)", 0)
                datos_c['metros_procesados'] = c1.number_input("Metros procesados", 0)
                datos_c['rollos_finales'] = c2.number_input("Rollos finales", 0)
                datos_c['empalmes'] = c3.number_input("Empalmes(defina un total o promedio)", 0)
                datos_c['desperdicio_kg'] = c1.number_input("Desperdicio Kg", 0)
                 
            obs_prod = st.text_area("Observaciones de producción / saldos ")

#  ENTREGA PARCIAL

            st.markdown("### 📦 ENTREGA PARCIAL (OPCIONAL)")
            cantidad_parcial = st.number_input("Cantidad parcial producida", 0)
            obs_parcial = st.text_input("Observación parcial")

            col_f1, col_f2 = st.columns(2)
            finalizar = col_f1.form_submit_button("🏁 FINALIZAR Y MOVER")
            parcial = col_f2.form_submit_button("📦 ENTREGA PARCIAL")

            if finalizar:
                if op_name:
                    inicio = datetime.fromisoformat(r['hora_inicio'].replace("Z", "+00:00")) if isinstance(r['hora_inicio'], str) else r['hora_inicio']
                    fin = hora_colombia()
                    duracion = calcular_duracion_laboral(inicio, fin)

                    # RUTAS DINÁMICAS
                    d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                    tipo = d_op['tipo_orden']
                    n_area = "FINALIZADO"

                    if tipo in ["FORMAS IMPRESAS", "FORMAS BLANCAS"]:
                        if area_act == "IMPRESIÓN":
                            n_area = "COLECTORAS"
                        elif area_act == "COLECTORAS":
                            # AQUÍ SE USA LA NUEVA LÓGICA
                            if datos_c.get('destino_final') == "Finalizar en Colectora":
                                n_area = "FINALIZADO"
                            else:
                                n_area = "ENCUADERNACIÓN"
                        elif area_act == "ENCUADERNACIÓN":
                            n_area = "FINALIZADO"
#  FINALIZAR TRABAJO ( LOGICA)

            if finalizar:

                if op_name:

                    inicio_raw = r['hora_inicio']

#  CONVERTIR A DATATIME (TODOS LOS MISMOS DATOS )

                    if isinstance(inicio_raw, str):
                        inicio = datetime.fromisoformat(inicio_raw.replace("Z", "+00:00"))
                    else:
                        inicio = inicio_raw

#  NORMALIZAR A ZONA HORARIA COLOMBIA

                    tz = pytz.timezone("America/Bogota")

                    if inicio.tzinfo is None:
                        inicio = tz.localize(inicio)
                    else:
                        inicio = inicio.astimezone(tz)

#  HORA ACTUAL CONSISTENTE

                    fin = hora_colombia()

#  CALCULAR DURACION

                    duracion = calcular_duracion_laboral(inicio, fin)

#  LOGICA DE DESCUENTO DE INVENTARIO

                    if area_act == "CORTE" and 'id_tubo_inventario' in datos_c:
                        id_t = datos_c['id_tubo_inventario']
                        cant_gastar = datos_c.get('rollos_finales', 0)
                        if cant_gastar > 0:
                            stk = supabase.table("inventario_cores").select("stock_actual").eq("id", id_t).single().execute().data
                            if stk:
                                supabase.table("inventario_cores").update({"stock_actual": stk['stock_actual'] - cant_gastar}).eq("id", id_t).execute()
                                datos_c['info_inventario_tubo'] = f"Descontados {cant_gastar} tubos"

# DESCUENTO DE CAJAS GENERAL 

                    if 'id_caja_inventario' in datos_c:
                        id_cj = datos_c['id_caja_inventario']
                        cant_cj = datos_c.get('cajas_totales', 0)
                        if cant_cj > 0:
                            stk_cj = supabase.table("inventario_cajas").select("stock_actual").eq("id", id_cj).single().execute().data
                            if stk_cj:
                                nuevo_stock_caja = stk_cj['stock_actual'] - cant_cj
                                supabase.table("inventario_cajas").update({"stock_actual": nuevo_stock_caja}).eq("id", id_cj).execute()
                                datos_c['info_inventario_caja'] = f"Descontadas {cant_cj} de {datos_c.get('nombre_caja')}"

# DETENER OP  NO CUENTA TIEMPO DE LA OP PERO SI DE PARADA

                    d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                    tipo = d_op['tipo_orden']
                    n_area = "FINALIZADO"

#  RUTAS 

                    if tipo in ["FORMAS IMPRESAS", "FORMAS BLANCAS"]:
                        if area_act == "IMPRESIÓN":
                            n_area = "COLECTORAS"
                        elif area_act == "COLECTORAS":
                            if datos_c.get('destino_final') == "Finalizar en Colectora":
                                n_area = "FINALIZADO"
                            else:
                                n_area = "ENCUADERNACIÓN"
                        elif area_act == "ENCUADERNACIÓN":
                            n_area = "FINALIZADO"

                    elif tipo == "ROLLOS IMPRESOS":
                        if area_act == "IMPRESIÓN":
                            n_area = "CORTE"
                        elif area_act == "CORTE":
                            n_area = "FINALIZADO"

                    elif tipo == "ROLLOS BLANCOS":
                        if area_act == "CORTE":
                            n_area = "FINALIZADO"

                    elif tipo == "REBOBINADO":
                        if area_act == "REBOBINADORAS":
                            n_area = "FINALIZADO"

                    hist = d_op.get('historial_procesos') or []
                    hist.append({
                        "area": area_act,
                        "maquina": r['maquina'],
                        "operario": op_name,
                        "auxiliar": auxiliar,
                        "fecha": fin.strftime("%d/%m/%Y %H:%M"),
                        "duracion": duracion,
                        "tipo": "FINAL",
                        "datos_cierre": datos_c,
                        "observaciones": obs_prod
                    })

                    supabase.table("ordenes_planeadas").update({
                        "proxima_area": n_area,
                        "historial_procesos": hist,
                        "estado_parcial": None
                    }).eq("op", r['op']).execute()

                    supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()
                    st.session_state.rep = None
                    st.rerun()

#  ENTREGAS PARCIALES 
        if parcial:
            # 1. Validaciones de la cantidad
            if cantidad_parcial <= 0:
                st.error("❌ Error: La cantidad parcial debe ser mayor a 0.")
                st.stop()
                
# Captura de tiempos (Tu logica nativa de conversion)

            inicio_raw = r['hora_inicio']
            if isinstance(inicio_raw, str):
                inicio = datetime.fromisoformat(inicio_raw.replace("Z", "+00:00"))
            else:
                inicio = inicio_raw
                
            tz = pytz.timezone("America/Bogota")
            if inicio.tzinfo is None:
                inicio = tz.localize(inicio)
            else:
                inicio = inicio.astimezone(tz)
                
            fin = hora_colombia()
            duracion = calcular_duracion_laboral(inicio, fin, r['maquina'])
            
# Preparar el nuevo historial

            # Preparar el nuevo historial — leer desde ordenes_planeadas, no desde trabajos_activos

            d_op_hist = supabase.table("ordenes_planeadas").select("historial_procesos").eq("op", r['op']).single().execute().data
            hist = d_op_hist.get('historial_procesos') or [] if d_op_hist else []
            
            datos_c['cantidad_parcial_entregada'] = cantidad_parcial
            if obs_parcial:
                datos_c['observacion_parcial'] = obs_parcial
                
# Recuperamos operario y auxiliar directamente del registro activo 'r'

            operario_actual = r.get('operario', 'Operario Planta')
            auxiliar_actual = r.get('auxiliar', '')
                
# Agregamos al historial de forma segura

            hist.append({
                "area": area_act,
                "maquina": r['maquina'],
                "operario": operario_actual,
                "auxiliar": auxiliar_actual,
                "fecha": fin.strftime("%d/%m/%Y %H:%M"),
                "duracion": duracion,
                "tipo": "PARCIAL",
                "datos_cierre": datos_c,
                "observaciones": obs_parcial if obs_parcial else f"Entrega parcial de {cantidad_parcial} unidades."
            })
            
#  CAMBIO CLAVE SIMULTANEO 

            # Calcular siguiente area leyendo la OP directo (no depende de n_area del finalizar)
            d_op_p = supabase.table("ordenes_planeadas").select("tipo_orden").eq("op", r['op']).single().execute().data
            tipo_p = d_op_p['tipo_orden'] if d_op_p else ""

            n_area_parcial = "FINALIZADO"
            if tipo_p in ["FORMAS IMPRESAS", "FORMAS BLANCAS"]:
                if area_act == "IMPRESIÓN":
                    n_area_parcial = "COLECTORAS"
                elif area_act == "COLECTORAS":
                    n_area_parcial = "ENCUADERNACIÓN"
            elif tipo_p == "ROLLOS IMPRESOS":
                if area_act == "IMPRESIÓN":
                    n_area_parcial = "CORTE"
                elif area_act == "CORTE":
                    n_area_parcial = "FINALIZADO"
            elif tipo_p == "ROLLOS BLANCOS":
                if area_act == "CORTE":
                    n_area_parcial = "FINALIZADO"
            elif tipo_p == "REBOBINADO":
                if area_act == "REBOBINADORAS":
                    n_area_parcial = "FINALIZADO"

            try:
                # 1. OP avanza a siguiente area Y queda visible en area origen
                supabase.table("ordenes_planeadas").update({
                    "proxima_area": n_area_parcial,
                    "estado_parcial": f"ACTIVO EN {area_act}",
                    "historial_procesos": hist
                }).eq("op", r['op']).execute()

                # 2. Maquina queda LIBRE
                supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()

                st.success(f"✅ Parcial enviado a {n_area_parcial}. La máquina {r['maquina']} quedó libre y la OP sigue activa en {area_act}.")
                st.session_state.rep = None
                time.sleep(1.5)
                st.rerun()

            except Exception as e:
                st.error(f"Error al procesar la entrega parcial: {e}")

if st.session_state.get('rol') == 'admin':

#  BLOQUE INTERRUPTORES DE MAQUINAS

    with st.expander("⚙️ INTERRUPTORES DE MÁQUINAS (ON/OFF)"):
        st.warning("Si apagas una máquina, el sistema no contará tiempos laborados para ella.")
        
        for area, lista_maquinas in MAQUINAS.items():
            st.subheader(f"Área: {area}")
            cols = st.columns(4) 
            for i, maq in enumerate(lista_maquinas):
                col_idx = i % 4
                with cols[col_idx]:
                    estado_actual = obtener_estado_maquina(maq)

# El interruptor (toggle)

                    nuevo_st = st.toggle(f"{maq}", value=estado_actual, key=f"switch_{maq}")
                    
                    if nuevo_st != estado_actual:
                        cambiar_estado_maquina(maq, nuevo_st)
                        st.toast(f"Máquina {maq} {'ACTIVADA' if nuevo_st else 'DESACTIVADA'}")
                        time.sleep(0.5) 
                        st.rerun() 

    st.divider()

#  BLOQUE 2: ADMINISTRACION DE USUARIOS 

    with st.expander("➕ Panel de Administración de Usuarios"):
        st.info("Desde aquí se puede dar de alta nuevos operarios en la base de datos de Supabase.")
        
        c1, c2 = st.columns(2)
        with c1:
            nuevo_u = st.text_input("Usuario (Login)", key="admin_u")
            nuevo_p = st.text_input("Nueva Clave", type="password", key="admin_p")
        with c2:
            nuevo_n = st.text_input("Nombre Completo", key="admin_n")
            nuevo_r = st.selectbox("Rol", ["admin", "ventas", "supervisor_imp", "supervisor_cor", "supervisor_reb", "supervisor_enc",'diseño', "patinador_roll", "almacen", "jefe_log", "patinador_log",'aux_log' ], key="admin_r")
        
        if st.button("🚀 Crear Usuario en Sistema"):
            if nuevo_u and nuevo_p and nuevo_n:
                try:
                    supabase.table("usuarios").insert({
                        "usuario": nuevo_u, 
                        "clave": nuevo_p, 
                        "nombre": nuevo_n, 
                        "rol": nuevo_r
                    }).execute()
                    st.success(f"Usuario {nuevo_u} creado exitosamente.")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al insertar: {e}")
            else:
                st.warning("Por favor, completa todos los campos.")


# ══════════════════════════════════════════════════════════════
#   MÓDULO: 🛒 MERCADO DE AVATARES C&B PAPELES
# ══════════════════════════════════════════════════════════════

# ── FUNCIONES DE MERCADO ──────────────────────────────────────

def mercado_obtener_coins(usuario):
    """Retorna los coins actuales de un usuario."""
    try:
        res = supabase.table("monedas_usuarios").select("coins").eq("usuario", usuario).execute()
        if res.data:
            return res.data[0]['coins']
        # Si no existe, crea registro con 0 coins
        supabase.table("monedas_usuarios").upsert({"usuario": usuario, "coins": 0}, on_conflict="usuario").execute()
        return 0
    except:
        return 0

def mercado_ajustar_coins(usuario, cantidad, motivo, admin_who):
    """Suma o resta coins a un usuario y registra el movimiento."""
    try:
        coins_actuales = mercado_obtener_coins(usuario)
        nuevos_coins = max(0, coins_actuales + cantidad)
        supabase.table("monedas_usuarios").upsert({"usuario": usuario, "coins": nuevos_coins}, on_conflict="usuario").execute()
        # Registrar movimiento en historial
        supabase.table("monedas_historial").insert({
            "usuario": usuario,
            "cantidad": cantidad,
            "motivo": motivo,
            "admin": admin_who,
            "fecha": hora_colombia().isoformat()
        }).execute()
        return nuevos_coins
    except Exception as e:
        st.error(f"Error al ajustar coins: {e}")
        return None

def mercado_obtener_items_tienda():
    """Retorna todos los items disponibles en la tienda."""
    try:
        res = supabase.table("items_mercado").select("*").eq("activo", True).order("precio").execute()
        return res.data or []
    except:
        return []

def mercado_obtener_items_usuario(usuario):
    """Retorna los items que posee un usuario."""
    try:
        res = supabase.table("inventario_avatar").select("*").eq("usuario", usuario).execute()
        return res.data or []
    except:
        return []

def mercado_comprar_item(usuario, item_id, item_nombre, precio):
    """Procesa la compra de un item."""
    try:
        coins_actuales = mercado_obtener_coins(usuario)
        if coins_actuales < precio:
            return False, "No tienes suficientes coins 💸"
        
        # Verificar si ya lo tiene
        tiene = supabase.table("inventario_avatar").select("id").eq("usuario", usuario).eq("item_id", item_id).execute()
        if tiene.data:
            return False, "Ya tienes este item ✋"
        
        # Descontar coins
        nuevos_coins = coins_actuales - precio
        supabase.table("monedas_usuarios").upsert({"usuario": usuario, "coins": nuevos_coins}, on_conflict="usuario").execute()
        
        # Agregar al inventario del avatar
        supabase.table("inventario_avatar").insert({
            "usuario": usuario,
            "item_id": item_id,
            "item_nombre": item_nombre,
            "equipado": False,
            "fecha_compra": hora_colombia().isoformat()
        }).execute()
        
        # Registrar en historial
        supabase.table("monedas_historial").insert({
            "usuario": usuario,
            "cantidad": -precio,
            "motivo": f"Compra en tienda: {item_nombre}",
            "admin": "SISTEMA",
            "fecha": hora_colombia().isoformat()
        }).execute()
        
        return True, f"¡{item_nombre} comprado exitosamente! 🎉"
    except Exception as e:
        return False, f"Error en la compra: {e}"

def mercado_equipar_item(usuario, inv_id, categoria):
    """Equipa un item (desequipa el anterior de la misma categoría)."""
    try:
        # Obtener todos los items del usuario de esa categoría
        items_cat = supabase.table("inventario_avatar")\
            .select("id")\
            .eq("usuario", usuario)\
            .eq("equipado", True)\
            .execute()
        
        # Desequipar los de la misma categoría
        for it in (items_cat.data or []):
            # Verificar si es de la misma categoría
            det = supabase.table("items_mercado").select("categoria").eq("id", 
                supabase.table("inventario_avatar").select("item_id").eq("id", it['id']).execute().data[0]['item_id']
            ).execute()
            if det.data and det.data[0].get('categoria') == categoria:
                supabase.table("inventario_avatar").update({"equipado": False}).eq("id", it['id']).execute()
        
        # Equipar el nuevo
        supabase.table("inventario_avatar").update({"equipado": True}).eq("id", inv_id).execute()
        return True
    except Exception as e:
        return False

# ── RENDERIZADOR DE AVATAR SVG ────────────────────────────────

def render_avatar_avaturn(nombre_usuario="", glb_url="", subdomain="demo"):
    """
    Renderiza el avatar de Avaturn.
    - Si glb_url está vacío: muestra el editor de Avaturn para crear/editar avatar.
    - Si glb_url tiene valor: muestra el avatar 3D ya creado con Three.js + GLTFLoader.
    subdomain: el subdominio que creaste en developer.avaturn.me (ej: 'cbpapeles')
    """
    # ── Vista del avatar ya guardado ───────────────────────────────────────────
    if glb_url:
        return f"""
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<div style="text-align:center;">
  <canvas id="avaturn_canvas" style="border-radius:14px;border:1px solid #e0e0e0;width:280px;height:380px;display:inline-block;cursor:grab;"></canvas>
  <div style="font-weight:bold;color:#0D47A1;margin-top:6px;font-family:sans-serif;">{nombre_usuario}</div>
  <div id="av_status" style="font-size:12px;color:#888;font-family:sans-serif;">Cargando avatar...</div>
</div>
<script>
(function(){{
  const canvas = document.getElementById('avaturn_canvas');
  if(!canvas || !window.THREE) return;
  const renderer = new THREE.WebGLRenderer({{canvas, antialias:true, alpha:true}});
  renderer.setSize(280, 380);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(38, 280/380, 0.1, 100);
  camera.position.set(0, 1.4, 2.8);
  camera.lookAt(0, 1.0, 0);
  // Iluminación de calidad
  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const dirLight = new THREE.DirectionalLight(0xfff5e0, 1.2);
  dirLight.position.set(2, 5, 3);
  dirLight.castShadow = true;
  scene.add(dirLight);
  const fillLight = new THREE.DirectionalLight(0xd0e8ff, 0.4);
  fillLight.position.set(-3, 2, -2);
  scene.add(fillLight);
  const rimLight = new THREE.DirectionalLight(0xffffff, 0.3);
  rimLight.position.set(0, 3, -4);
  scene.add(rimLight);
  // Suelo con sombra
  const floor = new THREE.Mesh(
    new THREE.CircleGeometry(1.2, 48),
    new THREE.MeshStandardMaterial({{color:0xf0f0f0, roughness:0.8}})
  );
  floor.rotation.x = -Math.PI/2;
  floor.receiveShadow = true;
  scene.add(floor);
  // Drag / orbit simple
  let isDragging=false, prevX=0, rotY=0.15;
  canvas.addEventListener('mousedown', e=>{{isDragging=true; prevX=e.clientX;}});
  canvas.addEventListener('touchstart', e=>{{isDragging=true; prevX=e.touches[0].clientX;}});
  window.addEventListener('mouseup', ()=>isDragging=false);
  window.addEventListener('touchend', ()=>isDragging=false);
  canvas.addEventListener('mousemove', e=>{{
    if(!isDragging) return;
    rotY += (e.clientX - prevX) * 0.012;
    prevX = e.clientX;
  }});
  canvas.addEventListener('touchmove', e=>{{
    if(!isDragging) return;
    rotY += (e.touches[0].clientX - prevX) * 0.012;
    prevX = e.touches[0].clientX;
  }});
  let avatarMesh = null;
  // Cargar GLB de Avaturn
  const loader = new THREE.GLTFLoader();
  loader.load(
    '{glb_url}',
    function(gltf) {{
      avatarMesh = gltf.scene;
      // Centrar y escalar el modelo
      const box = new THREE.Box3().setFromObject(avatarMesh);
      const center = box.getCenter(new THREE.Vector3());
      const size = box.getSize(new THREE.Vector3());
      const scale = 1.8 / size.y;
      avatarMesh.scale.setScalar(scale);
      avatarMesh.position.x = -center.x * scale;
      avatarMesh.position.y = -box.min.y * scale;
      avatarMesh.position.z = -center.z * scale;
      // Sombras
      avatarMesh.traverse(child => {{
        if(child.isMesh) {{
          child.castShadow = true;
          child.receiveShadow = true;
        }}
      }});
      scene.add(avatarMesh);
      document.getElementById('av_status').textContent = 'Arrastra para rotar 360°';
    }},
    undefined,
    function(err) {{
      document.getElementById('av_status').textContent = 'Error cargando avatar';
      console.error(err);
    }}
  );
  // Animación flotante suave
  let t = 0;
  (function animate() {{
    requestAnimationFrame(animate);
    t += 0.016;
    if(!isDragging && avatarMesh) avatarMesh.rotation.y += 0.005;
    if(avatarMesh) avatarMesh.rotation.y = rotY + Math.sin(t*0.3)*0.0;
    if(!isDragging) rotY += 0.005;
    if(avatarMesh) avatarMesh.rotation.y = rotY;
    renderer.render(scene, camera);
  }})();
}})();
</script>
"""

    # ── Editor de Avaturn (crear/editar avatar) ────────────────────────────────
    else:
        return f"""
<style>
  #avaturn_wrapper {{ width:100%; height:520px; border-radius:14px; overflow:hidden;
                      border:1px solid #e0e0e0; position:relative; }}
  #avaturn_frame   {{ width:100%; height:100%; border:none; display:block; }}
  #avaturn_info    {{ text-align:center; font-size:12px; color:#888;
                      font-family:sans-serif; margin-top:6px; }}
</style>
<div id="avaturn_wrapper">
  <iframe id="avaturn_frame"
    src="https://{subdomain}.avaturn.dev"
    allow="camera *; microphone *; clipboard-write">
  </iframe>
</div>
<div id="avaturn_info">Crea tu avatar con selfie — cuando termines haz clic en "Done" para guardar</div>
<script>
(function(){{
  window.addEventListener('message', function(event) {{
    try {{
      const json = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
      // Avaturn envía el GLB URL cuando el usuario hace clic en "Done"
      if(json && json.source === 'avaturn' && json.eventName === 'v1.avatar.exported') {{
        const glbUrl = json.data.url;
        document.getElementById('avaturn_info').textContent = 'Avatar guardado. URL: ' + glbUrl;
        // Enviar al padre (Streamlit) via postMessage para guardarlo en Supabase
        window.parent.postMessage({{type:'AVATURN_GLB', url: glbUrl, usuario: '{nombre_usuario}'}}, '*');
      }}
    }} catch(e) {{}}
  }});
}})();
</script>
"""

# ── MÓDULO MERCADO PRINCIPAL ──────────────────────────────────
# ── MÓDULO MERCADO PRINCIPAL ──────────────────────────────────
# ── MÓDULO MERCADO PRINCIPAL ──────────────────────────────────

if menu == "🛒 Mercado":
    usuario_actual = st.session_state.get('usuario_actual', '')
    nombre_actual  = st.session_state.get('nombre_usuario', '')
    rol_actual     = st.session_state.get('rol', '')

    st.markdown("<div class='title-area'>🛒 MERCADO DE AVATARES — C&B PAPELES</div>", unsafe_allow_html=True)

    coins_usuario = mercado_obtener_coins(usuario_actual)

    # ── BARRA DE COINS ──────────────────────────────────────
    st.markdown(f"""
    <div style="background: linear-gradient(135deg,#1565C0,#0D47A1); border-radius:16px; 
                padding:18px 28px; display:flex; align-items:center; gap:16px; margin-bottom:20px;">
        <span style="font-size:2.5rem;">🪙</span>
        <div>
            <div style="color:#FFD700; font-size:1.8rem; font-weight:900; line-height:1;">{coins_usuario}</div>
            <div style="color:#90CAF9; font-size:0.9rem;">Coins disponibles — {nombre_actual}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── TABS PRINCIPALES ────────────────────────────────────
    if rol_actual == 'admin':
        tab_tienda, tab_avatar, tab_admin, tab_historial = st.tabs(
            ["🛍️ Tienda", "👤 Mi Avatar", "⚙️ Panel Admin", "📜 Historial Monedas"]
        )
    else:
        tab_tienda, tab_avatar, tab_historial = st.tabs(
            ["🛍️ Tienda", "👤 Mi Avatar", "📜 Mi Historial"]
        )

    # ════════════════════════════════════════════════════════
    # TAB 1 — TIENDA
    # ════════════════════════════════════════════════════════
    with tab_tienda:
        st.markdown("<div class='section-header'>🛍️ ARTÍCULOS DISPONIBLES</div>", unsafe_allow_html=True)

        items_tienda = mercado_obtener_items_tienda()
        items_poseidos = {it['item_id'] for it in mercado_obtener_items_usuario(usuario_actual)}

        if not items_tienda:
            st.info("La tienda está vacía. El admin puede agregar items desde el Panel Admin.")
        else:
            # Agrupar por categoría
            categorias = {}
            for item in items_tienda:
                cat = item.get('categoria', 'General')
                categorias.setdefault(cat, []).append(item)

            for cat, items_cat in categorias.items():
                emoji_cat = {"sombrero": "🎩", "camisa": "👕", "cabello": "💇", "insignia": "🏅", "accesorio": "🎀"}.get(cat.lower(), "🎁")
                st.markdown(f"#### {emoji_cat} {cat.upper()}")
                cols = st.columns(min(len(items_cat), 4))

                for i, item in enumerate(items_cat):
                    with cols[i % 4]:
                        ya_tiene = item['id'] in items_poseidos
                        puede_comprar = coins_usuario >= item['precio'] and not ya_tiene

                        color_borde = "#4CAF50" if ya_tiene else ("#1565C0" if puede_comprar else "#9E9E9E")
                        estado_txt  = "✅ Ya tienes" if ya_tiene else (f"🪙 {item['precio']}" if puede_comprar else f"🔒 {item['precio']} (sin fondos)")

                        # Miniatura de color si aplica
                        color_swatch = ""
                        if item.get('color_hex'):
                            color_swatch = f"<div style='width:32px;height:32px;border-radius:50%;background:{item['color_hex']};border:2px solid #fff;display:inline-block;vertical-align:middle;margin-right:8px;'></div>"

                        st.markdown(f"""
                        <div style="border:2px solid {color_borde}; border-radius:14px; padding:14px; text-align:center;
                                    background:#fff; margin-bottom:8px; min-height:140px;">
                            <div style="font-size:2.2rem;">{item.get('emoji','🎁')}</div>
                            {color_swatch}
                            <div style="font-weight:bold; color:#0D47A1; margin:6px 0 2px;">{item['nombre']}</div>
                            <div style="font-size:0.8rem; color:#666; margin-bottom:8px;">{item.get('descripcion','')}</div>
                            <div style="font-weight:bold; color:{'#388E3C' if ya_tiene else '#E65100'};">{estado_txt}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        if not ya_tiene:
                            btn_label = f"Comprar" if puede_comprar else "Sin coins"
                            if st.button(btn_label, key=f"buy_{item['id']}", disabled=not puede_comprar, use_container_width=True):
                                ok, msg = mercado_comprar_item(usuario_actual, item['id'], item['nombre'], item['precio'])
                                if ok:
                                    st.success(msg)
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(msg)

    # ════════════════════════════════════════════════════════
    # TAB 2 — MI AVATAR
    # ════════════════════════════════════════════════════════
    with tab_avatar:
        st.markdown("<div class='section-header'>👤 MI AVATAR</div>", unsafe_allow_html=True)

        inventario = mercado_obtener_items_usuario(usuario_actual)

        col_av, col_inv = st.columns([1, 2])

        with col_av:
            st.markdown("**Vista Previa**")
            # Obtener items equipados con su info de la tienda
            items_equipados_full = []
            for inv_item in inventario:
                if inv_item.get('equipado'):
                    detalle = supabase.table("items_mercado").select("*").eq("id", inv_item['item_id']).execute().data
                    if detalle:
                        d = detalle[0]
                        d['categoria'] = d.get('categoria', '')
                        items_equipados_full.append(d)

            import streamlit.components.v1 as components

            # ── Subdominio Avaturn — cámbialo por el tuyo de developer.avaturn.me ──
            AVATURN_SUBDOMAIN = "cbpapeles" 

            # Obtener GLB guardado de este usuario (si ya creó su avatar)
            glb_guardado = ""
            try:
                res_glb = supabase.table("monedas_usuarios").select("avatar_glb_url").eq("usuario", usuario_actual).execute()
                if res_glb.data and res_glb.data[0].get("avatar_glb_url"):
                    glb_guardado = res_glb.data[0]["avatar_glb_url"]
            except:
                pass

            # Botón para re-crear el avatar aunque ya tenga uno
            col_av_btn1, col_av_btn2 = st.columns(2)
            with col_av_btn1:
                if st.button("✏️ Crear / Editar Avatar", key="btn_editar_av", use_container_width=True):
                    st.session_state['editando_avatar'] = True
            with col_av_btn2:
                if glb_guardado and st.button("👁️ Ver mi Avatar", key="btn_ver_av", use_container_width=True):
                    st.session_state['editando_avatar'] = False

            editando = st.session_state.get('editando_avatar', not bool(glb_guardado))

            if editando:
                # Mostrar editor de Avaturn (iframe con selfie)
                html_avaturn = render_avatar_avaturn(
                    nombre_usuario=nombre_actual,
                    glb_url="",
                    subdomain=AVATURN_SUBDOMAIN
                )
                components.html(html_avaturn, height=600, scrolling=False)
                st.info("💡 Cuando termines en el editor y hagas clic en **Done**, copia la URL del GLB y pégala aquí:")
                glb_input = st.text_input("URL del GLB de tu avatar (la recibirás al terminar en Avaturn):", key="glb_input_manual")
                if st.button("💾 Guardar mi avatar", key="btn_save_glb") and glb_input.strip():
                    try:
                        supabase.table("monedas_usuarios").upsert(
                            {"usuario": usuario_actual, "avatar_glb_url": glb_input.strip()},
                            on_conflict="usuario"
                        ).execute()
                        st.success("✅ Avatar guardado correctamente.")
                        st.session_state['editando_avatar'] = False
                        import time; time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error guardando avatar: {e}")
            else:
                # Mostrar avatar 3D ya guardado
                if glb_guardado:
                    html_av = render_avatar_avaturn(
                        nombre_usuario=nombre_actual,
                        glb_url=glb_guardado,
                        subdomain=AVATURN_SUBDOMAIN
                    )
                    components.html(html_av, height=430, scrolling=False)
                else:
                    st.info("Aún no tienes avatar. Haz clic en **Crear / Editar Avatar** para empezar.")

        with col_inv:
            st.markdown("**Mi Inventario — selecciona qué equipar**")
            if not inventario:
                st.info("Aún no tienes items. Ve a la tienda y compra algo 🛍️")
            else:
                # Agrupar por categoría
                inv_cats = {}
                for it in inventario:
                    det = supabase.table("items_mercado").select("*").eq("id", it['item_id']).execute().data
                    cat = det[0]['categoria'] if det else 'General'
                    inv_cats.setdefault(cat, []).append((it, det[0] if det else {}))

                for cat, items_list in inv_cats.items():
                    st.markdown(f"**{cat.upper()}**")
                    for inv_it, det_it in items_list:
                        equipado_now = inv_it.get('equipado', False)
                        col_i, col_b = st.columns([3, 1])
                        with col_i:
                            color_swatch = f"<span style='display:inline-block;width:16px;height:16px;border-radius:50%;background:{det_it.get('color_hex','#ccc')};border:1px solid #999;vertical-align:middle;margin-right:6px;'></span>" if det_it.get('color_hex') else ""
                            st.markdown(f"{det_it.get('emoji','🎁')} {color_swatch} **{det_it.get('nombre','')}** {'✅ Equipado' if equipado_now else ''}", unsafe_allow_html=True)
                        with col_b:
                            if not equipado_now:
                                if st.button("Equipar", key=f"eq_{inv_it['id']}", use_container_width=True):
                                    mercado_equipar_item(usuario_actual, inv_it['id'], cat)
                                    st.rerun()
                            else:
                                if st.button("Quitar", key=f"rm_{inv_it['id']}", use_container_width=True):
                                    supabase.table("inventario_avatar").update({"equipado": False}).eq("id", inv_it['id']).execute()
                                    st.rerun()

    # ════════════════════════════════════════════════════════
    # TAB 3 — PANEL ADMIN
    # ════════════════════════════════════════════════════════
    if rol_actual == 'admin':
        with tab_admin:
            st.markdown("<div class='section-header'>⚙️ ADMINISTRACIÓN DEL MERCADO</div>", unsafe_allow_html=True)

            # ── Asignar / quitar coins ───────────────────────
            with st.expander("🪙 Asignar o Quitar Coins a Trabajadores", expanded=True):
                st.info("Puedes dar coins como recompensa por buen desempeño, o descontarlos si es necesario.")
                
                try:
                    todos_usuarios = supabase.table("usuarios").select("usuario, nombre, rol").execute().data or []
                except:
                    todos_usuarios = []

                opciones_u = {f"{u['nombre']} ({u['usuario']}) — {u['rol']}": u['usuario'] for u in todos_usuarios}

                c1, c2, c3 = st.columns(3)
                with c1:
                    sel_u = st.selectbox("Seleccionar Trabajador", list(opciones_u.keys()), key="admin_sel_user")
                with c2:
                    cantidad_coins = st.number_input("Cantidad de Coins (+/-)", min_value=-9999, max_value=9999, value=10, step=5, key="admin_coins_amt")
                with c3:
                    motivo_coins = st.text_input("Motivo / Descripción", placeholder="Ej: Cumplimiento meta semana", key="admin_coins_mot")

                if sel_u:
                    u_key = opciones_u[sel_u]
                    coins_act = mercado_obtener_coins(u_key)
                    st.caption(f"Coins actuales de {sel_u.split('(')[0].strip()}: **{coins_act} 🪙**")

                if st.button("✅ Confirmar Asignación de Coins", use_container_width=True, key="btn_assign_coins"):
                    if not motivo_coins.strip():
                        st.warning("Por favor escribe un motivo antes de asignar coins.")
                    else:
                        u_key = opciones_u[sel_u]
                        nuevos = mercado_ajustar_coins(u_key, cantidad_coins, motivo_coins, st.session_state.get('usuario_actual'))
                        if nuevos is not None:
                            accion = "asignaron" if cantidad_coins > 0 else "descontaron"
                            st.success(f"✅ Se {accion} {abs(cantidad_coins)} coins a {sel_u.split('(')[0].strip()}. Saldo nuevo: {nuevos} 🪙")
                            time.sleep(1)
                            st.rerun()

            # ── Ver monederos de todos ───────────────────────
            with st.expander("💰 Ver Coins de Todos los Trabajadores"):
                try:
                    monederos = supabase.table("monedas_usuarios").select("*").order("coins", desc=True).execute().data or []
                    if monederos:
                        df_coins = pd.DataFrame(monederos)
                        # Cruzar con nombres
                        nombres_map = {u['usuario']: u['nombre'] for u in todos_usuarios}
                        df_coins['nombre'] = df_coins['usuario'].map(nombres_map).fillna("Desconocido")
                        df_coins = df_coins[['nombre', 'usuario', 'coins']].rename(columns={
                            'nombre': 'Nombre', 'usuario': 'Usuario', 'coins': '🪙 Coins'
                        })
                        st.dataframe(df_coins, use_container_width=True, hide_index=True)
                    else:
                        st.info("Ningún trabajador tiene coins todavía.")
                except Exception as e:
                    st.error(f"Error: {e}")

            # ── Gestión de items de la tienda ────────────────
            with st.expander("🎁 Gestionar Items de la Tienda"):
                st.markdown("**Agregar nuevo item:**")
                ic1, ic2, ic3 = st.columns(3)
                with ic1:
                    item_nombre = st.text_input("Nombre del item", key="it_nom")
                    item_emoji  = st.text_input("Emoji", value="🎁", key="it_em")
                    item_cat    = st.selectbox("Categoría", ["sombrero", "camisa", "cabello", "insignia", "accesorio"], key="it_cat")
                with ic2:
                    item_precio = st.number_input("Precio en Coins", min_value=1, value=50, key="it_prec")
                    item_color  = st.color_picker("Color (si aplica)", value="#1565C0", key="it_col")
                    item_label  = st.text_input("Etiqueta corta (para insignia)", key="it_lbl", placeholder="Ej: TOP 1")
                with ic3:
                    item_desc   = st.text_area("Descripción", key="it_desc", height=80)
                    item_svg    = st.text_input("Tipo de forma (corona/gorra/casco)", key="it_svg", placeholder="corona")

                if st.button("➕ Agregar Item a la Tienda", use_container_width=True, key="btn_add_item"):
                    if item_nombre.strip():
                        try:
                            supabase.table("items_mercado").insert({
                                "nombre": item_nombre,
                                "emoji": item_emoji,
                                "categoria": item_cat,
                                "precio": item_precio,
                                "color_hex": item_color,
                                "label": item_label,
                                "descripcion": item_desc,
                                "svg_data": item_svg,
                                "activo": True
                            }).execute()
                            st.success(f"✅ Item '{item_nombre}' agregado a la tienda.")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.warning("El nombre del item no puede estar vacío.")

                st.markdown("**Items actuales en tienda:**")
                try:
                    todos_items = supabase.table("items_mercado").select("*").order("categoria").execute().data or []
                    if todos_items:
                        df_items = pd.DataFrame(todos_items)[['nombre', 'categoria', 'emoji', 'precio', 'activo']]
                        df_items.columns = ['Nombre', 'Categoría', 'Emoji', '🪙 Precio', 'Activo']
                        st.dataframe(df_items, use_container_width=True, hide_index=True)
                except Exception as e:
                    st.error(f"Error: {e}")

        # ════════════════════════════════════════════════════
        # TAB 4 — HISTORIAL (ADMIN ve todo, usuario ve lo suyo)
        # ════════════════════════════════════════════════════
        with tab_historial:
            st.markdown("<div class='section-header'>📜 HISTORIAL DE MOVIMIENTOS DE COINS</div>", unsafe_allow_html=True)
            try:
                if rol_actual == 'admin':
                    hist_data = supabase.table("monedas_historial").select("*").order("fecha", desc=True).limit(200).execute().data or []
                else:
                    hist_data = supabase.table("monedas_historial").select("*").eq("usuario", usuario_actual).order("fecha", desc=True).limit(100).execute().data or []

                if hist_data:
                    df_hist = pd.DataFrame(hist_data)
                    df_hist['Tipo'] = df_hist['cantidad'].apply(lambda x: "➕ Ingreso" if x > 0 else "➖ Gasto")
                    cols_show = ['fecha', 'usuario', 'cantidad', 'Tipo', 'motivo', 'admin'] if rol_actual == 'admin' else ['fecha', 'cantidad', 'Tipo', 'motivo']
                    col_names = {
                        'fecha': 'Fecha', 'usuario': 'Usuario', 'cantidad': '🪙 Coins',
                        'motivo': 'Descripción', 'admin': 'Asignado por'
                    }
                    df_show = df_hist[[c for c in cols_show if c in df_hist.columns]].rename(columns=col_names)
                    st.dataframe(df_show, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay movimientos registrados aún.")
            except Exception as e:
                st.error(f"Error al cargar historial: {e}")
    else:
        # Tab historial para no-admin
        with tab_historial:
            st.markdown("<div class='section-header'>📜 MI HISTORIAL DE COINS</div>", unsafe_allow_html=True)
            try:
                hist_data = supabase.table("monedas_historial").select("*").eq("usuario", usuario_actual).order("fecha", desc=True).limit(100).execute().data or []
                if hist_data:
                    df_hist = pd.DataFrame(hist_data)
                    df_hist['Tipo'] = df_hist['cantidad'].apply(lambda x: "➕ Ingreso" if x > 0 else "➖ Gasto")
                    df_show = df_hist[['fecha', 'cantidad', 'Tipo', 'motivo']].rename(columns={
                        'fecha': 'Fecha', 'cantidad': '🪙 Coins', 'motivo': 'Descripción'
                    })
                    st.dataframe(df_show, use_container_width=True, hide_index=True)
                else:
                    st.info("Aún no tienes movimientos de coins.")
            except Exception as e:
                st.error(f"Error: {e}")

