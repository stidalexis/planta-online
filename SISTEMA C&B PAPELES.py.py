import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
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
    st.error("Error de conexión a Base de Datos. Revisa los Secrets.")
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
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)],
    "REBOBINADORAS": ["REB-01", "REB-02", "REB-03"],
}
PRESENTACIONES = ["BLOCK", "LIBRETA LICOM", "HOJAS SUELTAS", "PAQUETES", "TACOS", "CAJAS", "FAJILLAS", "FORMA CONTINUA"]
PRESENTACIONES2 = ["POR CABEZA", "IZQUIERDA", "DERECHA", "PATA", ]
MOTIVOS_PARADA = ["Mantenimiento Mecánico", "Falta de Material", "Cambio de Referencia", "Limpieza", "Falla Eléctrica", "Almuerzo/Cena","Ajuste de Registro"]

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

from datetime import timedelta
import io
import pandas as pd

def hora_colombia():
    tz = pytz.timezone("America/Bogota")
    return datetime.now(tz)

# FUNCION DE HORARIOS

def calcular_duracion_laboral(inicio, fin):

    jornada_inicio = 6
    jornada_fin = 22

    actual = inicio
    total = timedelta()

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


# DESCARGA EL EXCEL DE EL HISTORIAL

def to_excel_limpio(df_input, tipo=None):

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:

        if tipo == "GENERAL":
            df_f = df_input[df_input['tipo_orden'].str.contains("FORMAS", na=False)].dropna(axis=1, how='all')
            df_r = df_input[df_input['tipo_orden'].str.contains("ROLLOS", na=False)].dropna(axis=1, how='all')

            if not df_f.empty:
                df_f.to_excel(writer, index=False, sheet_name='FORMAS')

            if not df_r.empty:
                df_r.to_excel(writer, index=False, sheet_name='ROLLOS')

        else:
            df_unit = df_input.dropna(axis=1, how='all')

            if 'id' in df_unit.columns:
                df_unit = df_unit.drop(columns=['id'])

            df_unit.to_excel(writer, index=False, sheet_name='DETALLE_OP')

    return output.getvalue()
    
#  PDF DE CERTIFICADO 

def generar_pdf_op(row):
    pdf = FPDF()
    pdf.add_page()
    
# ENCABEZADO INDUSTRIAL PDF CERTIFICADO 

    pdf.set_fill_color(13, 71, 161)
    pdf.rect(0, 0, 210, 40, 'F')

# LOGO CYB PAPELES

    pdf.image("logo_cb.png", 7, 5, 60)
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 20, f" CERTIFICADO DE PRODUCCION - OP: {row['op']}", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"TRABAJO: {row['nombre_trabajo']}", ln=True, align='C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(0.5)
    
#  SECCION DATOS DE VENTA PDF

    pdf.set_font("Arial", 'B', 10)
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

# PDF ORDEN PRODUCCION ROLLOS

from fpdf import FPDF
from datetime import datetime

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
    pdf.image("logo_cb.png", 8, 6, 55)
    
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

    pdf.ln(4); pdf.set_font("Arial", "B", 11); pdf.cell(0, 8, "2. ESPECIFICACIONES TECNICAS", 0, 1, fill=True)
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
    pdf.cell(82, 8, f" FRENTE: {row.get('tintas_frente_rollos', 'N/A')}", 1)
    pdf.cell(83, 8, f" RESPALDO: {row.get('tintas_respaldo_rollos', 'N/A')}", 1, 1)
    pdf.cell(190, 7, f"Destino: {row.get('destino_rollos','PLANTA')}", 1, 1)

# OBSERFVACIONES Y PERFORACIONES 

    pdf.ln(4); pdf.set_font("Arial", "B", 9); pdf.cell(0, 8, "3. ADICIONALES Y OBSERVACIONES", 0, 1, fill=True)
    pdf.cell(0, 7, f"Perforaciones: {row.get('perforaciones_detalle', 'NO')}", 1, 1)
    pdf.multi_cell(0, 7, f"OBSERVACIONES: {row.get('observaciones_rollos','')}", 1)

# FIRMAS O SELLOS 

    pdf.ln(1); pdf.set_font("Arial", "B", 7)
    pdf.cell(63, 6, "COORDINADORA", 1, 0, "C"); pdf.cell(63, 6, "ASESOR", 1, 0, "C"); pdf.cell(64, 6, "SUPERVISOR", 1, 1, "C")
    pdf.cell(63, 20, "", 1, 0); pdf.cell(63, 20, "", 1, 0); pdf.cell(64, 20, "", 1, 1)

# DATOS DE ESTIBAS 

    pdf.set_font("Arial", "", 6)
    y_est = pdf.get_y() + 2
    pdf.set_xy(10, y_est)
    pdf.set_fill_color(210, 210, 210); pdf.set_font("Arial", 'B', 9)
    pdf.cell(190, 5, "REPORTE DE CAJAS POR ESTIBAS (PRODUCCIÓN)", 1, 1, 'C', True)
    
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

# PDF ORDEN PRODUCCION FORMAS

from fpdf import FPDF
from datetime import datetime

# FUNCION PARA AJUSTAR TEXTO

def cell_fit(pdf, w, h, text, border=1):

    text = str(text)

    while pdf.get_string_width(text) > (w - 2):
        text = text[:-1]

    pdf.cell(w, h, text, border)

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
    pdf.image("logo_cb.png", 8, 6, 55)

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
    pdf.set_font("Arial","",10)
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
    pdf.cell(0,8,"5. OBSERVACIONES GENERALES",0,1,fill=True)
    pdf.set_font("Arial","",10)
    pdf.multi_cell(0,7,row.get("observaciones_formas",""), 1)

# FIRMAS

    pdf.ln(1)
    pdf.set_font("Arial","B",7)

    pdf.cell(63,6,"COORDINADORA",1,0,"C")
    pdf.cell(63,6,"ASESOR",1,0,"C")
    pdf.cell(64,6,"SUPERVISOR",1,1,"C")

    pdf.cell(63,20,"",1,0)
    pdf.cell(63,20,"",1,0)
    pdf.cell(64,20,"",1,1)

    pdf.set_font("Arial","B",8)
    pdf.cell(130,8,"OBSERVACIONES",1,0,"C")
    pdf.cell(60,8,"RECIBE",1,1,"C")

    pdf.set_font("Arial","",7)

    for _ in range(2):
        pdf.cell(130,6,"",1,0)
        pdf.cell(60,6,"",1,1)


    pdf.ln(10)
    pdf.set_font("Arial","I",7)
    pdf.cell(0,10,f"SISTEMA C&B PAPELES - {hora_colombia().strftime('%d/%m/%Y %H:%M')}",0,1,"C")
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
    pdf.image("logo_cb.png", 8, 6, 55)

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
    pdf.cell(0,8,"3. OBSERVACIONES ADICIONAL
