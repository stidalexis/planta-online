import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import io
from fpdf import FPDF
from datetime import datetime
import pytz

#  CONFIGURACION DE PAGINA 

st.set_page_config(layout="wide", page_title="SISTEMA C&B PAPELES V0.01 - TOTAL", page_icon="🏭")

#  CONEXION A SUPABASE 

try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("Error de conexion a Base de Datos. Revisa los Secrets.")
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
    
    /* RADIOGRAFIA: Cuadros blancos con texto en NEGRO */
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
# --- ROLES DE USUARIO ---

# --- USUARIOS ORGANIZADOS POR ROL ---
def validar_usuario_supabase(usuario_ingresado, clave_ingresada):
    try:
        # Consultamos la tabla usuarios filtrando por el nombre de usuario
        respuesta = supabase.table("usuarios")\
            .select("*")\
            .eq("usuario", usuario_ingresado)\
            .eq("clave", clave_ingresada)\
            .execute()
        
        # Si la lista de datos no está vacía, el usuario existe y la clave coincide
        if len(respuesta.data) > 0:
            return respuesta.data[0]  # Retornamos toda la info del usuario
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


# descarga excel de  historial

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
    
# --- ENCABEZADO INDUSTRIAL PDF CERTIFICADO ---
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
    
#  SECCION 1: DATOS DE VENTA PDF

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

#  SECCION 2: ESPECIFICACIONES PDF

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

#  SECCION 3: BITACORA TECNICA  

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
    pdf.cell(0, 10, f"DOCUMENTO OFICIAL C&B PAPELES  - GENERADO AUTOMATICAMENTE - {hora_colombia().strftime('%d/%m/%Y %H:%M')}", align='C')
    
    return bytes(pdf.output())

# PDF ORDEN PRODUCCION ROLLOS

from fpdf import FPDF
from datetime import datetime

def generar_op_rollos(row):
    pdf = FPDF()
    pdf.add_page()

    # 1. Lógica de color según el tipo de orden
    tipo_op = row.get('tipo_origen', '').upper()

    if "NUEVA" in tipo_op:
        r, g, b = (40, 167, 69)      # Verde
    elif "CAMBIOS" in tipo_op:
        r, g, b = (255, 165, 0)     # Naranja
    else:
        r, g, b = (13, 71, 161)     # Azul 

    # 2. ENCABEZADO CON COLOR DINÁMICO
    pdf.set_fill_color(r, g, b)
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.image("logo_cb.png", 8, 6, 55)
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 18, "ORDEN DE PRODUCCION - ROLLOS", 0, 1, "C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0,5,f"OP: {row['op']}   |   {row['tipo_origen']}",0,1,"C")
    
    # Volver a texto negro y continuar con el cuerpo
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # 1. INFORMACION GENERAL
    pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "1. INFORMACION DE LA ORDEN", 0, 1, fill=True)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(95, 7, f"Cliente: {row.get('cliente','')}", 1)
    pdf.cell(95, 7, f"Vendedor: {row.get('vendedor','')}", 1, 1)
    pdf.cell(95, 7, f"Trabajo: {row.get('nombre_trabajo','')}", 1)
    pdf.cell(95, 7, f"Tipo Orden: {row.get('tipo_orden','')}", 1, 1)

    # 2. ESPECIFICACIONES TÉCNICAS
    pdf.ln(4); pdf.set_font("Arial", "B", 11); pdf.cell(0, 8, "2. ESPECIFICACIONES TECNICAS", 0, 1, fill=True)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(63, 7, f"Material: {row.get('material','')}", 1)
    pdf.cell(63, 7, f"Gramaje: {row.get('gramaje_rollos','')}", 1)
    pdf.cell(64, 7, f"Core: {row.get('core','')}", 1, 1)

    pdf.cell(63, 7, f"Cantidad Rollos: {row.get('cantidad_rollos','')}", 1)
    pdf.cell(63, 7, f"Unidades Bolsa: {row.get('unidades_bolsa','')}", 1)
    pdf.cell(64, 7, f"Unidades Caja: {row.get('unidades_caja','')}", 1, 1)
    
    # Referencia y Transporte
    pdf.cell(95, 7, f"Referencia Comercial: {row.get('ref_comercial','')}", 1)
    trans = "SI" if row.get('transportadora_rollos') else "NO"
    pdf.cell(95, 7, f"Transportadora: {trans}", 1, 1)
    pdf.cell(25, 8, "Impresión", 1, 0, 'C')
    pdf.cell(82, 8, f" FRENTE: {row.get('tintas_frente_rollos', 'N/A')}", 1)
    pdf.cell(83, 8, f" RESPALDO: {row.get('tintas_respaldo_rollos', 'N/A')}", 1, 1)
    pdf.cell(190, 7, f"Destino: {row.get('destino_rollos','PLANTA')}", 1, 1)

    # Observaciones y Perforaciones
    pdf.ln(4); pdf.set_font("Arial", "B", 9); pdf.cell(0, 8, "3. ADICIONALES Y OBSERVACIONES", 0, 1, fill=True)
    pdf.cell(0, 7, f"Perforaciones: {row.get('perforaciones_detalle', 'NO')}", 1, 1)
    pdf.multi_cell(0, 7, f"OBSERVACIONES: {row.get('observaciones_rollos','')}", 1)

    # FIRMAS
    pdf.ln(1); pdf.set_font("Arial", "B", 7)
    pdf.cell(63, 6, "COORDINADORA", 1, 0, "C"); pdf.cell(63, 6, "ASESOR", 1, 0, "C"); pdf.cell(64, 6, "SUPERVISOR", 1, 1, "C")
    pdf.cell(63, 20, "", 1, 0); pdf.cell(63, 20, "", 1, 0); pdf.cell(64, 20, "", 1, 1)

    # ESTIBAS 
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
    pdf.cell(0, 5, f"SISTEMA C&B PAPELES  - {hora_colombia().strftime('%d/%m/%Y %H:%M')}", 0, 1, "C")

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

# GENERAR PDF FORMAS-

def generar_op_formas(row):
    pdf = FPDF()
    pdf.add_page()
    
    tipo_op = row.get('tipo_origen', '').upper()
    # --- ENCABEZADO (Mantenemos tu estilo actual) ---
    if "NUEVA" in tipo_op:
        r, g, b = (40, 167, 69)      # Verde
    elif "CAMBIOS" in tipo_op:
        r, g, b = (255, 165, 0)     # Naranja
    else:
        r, g, b = (13, 71, 161)     # Azul 

    # 2. ENCABEZADO CON COLOR DINÁMICO
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

    # 1. INFORMACIÓN DE LA ORDEN
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

    # 2. ESPECIFICACIONES GENERALES (Aquí agregamos los campos faltantes)
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

    # 3. PERFORACIONES
    pdf.ln(4)
    pdf.set_font("Arial","B",11)
    pdf.cell(0,8,"3. PERFORACIONES",0,1,fill=True)
    pdf.set_font("Arial","",10)
    pdf.multi_cell(0,7,row.get("perforaciones_detalle","SIN PERFORACIONES"), 1)

    # 4. DETALLE TECNICO POR PARTE (Mantenemos tu tabla actual)
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
        cell_fit(pdf,37,7,p.get("obs_parte","")) # Agregamos la observación específica de la parte
        pdf.ln()

    # 5. OBSERVACIONES GENERALES
    pdf.ln(5)
    pdf.set_font("Arial","B",11)
    pdf.cell(0,8,"5. OBSERVACIONES GENERALES",0,1,fill=True)
    pdf.set_font("Arial","",10)
    pdf.multi_cell(0,7,row.get("observaciones_formas",""), 1)

    # -------------------------
    # FIRMAS
    # -------------------------
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
    pdf.cell(0,10,f"SISTEMA C&B PAPELES  - {hora_colombia().strftime('%d/%m/%Y %H:%M')}",0,1,"C")
    return bytes(pdf.output())

def generar_op_rebobinado(row):
    pdf = FPDF()
    pdf.add_page()
    
    tipo_op = row.get('tipo_origen', '').upper()
    # --- ENCABEZADO ---
    if "NUEVA" in tipo_op:
        r, g, b = (40, 167, 69)      # Verde
    elif "CAMBIOS" in tipo_op:
        r, g, b = (255, 165, 0)     # Naranja
    else:
        r, g, b = (13, 71, 161)     # Azul 

    # 2. ENCABEZADO CON COLOR DINÁMICO
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

    # 1. INFORMACION GENERAL
    pdf.set_fill_color(230,230,230)
    pdf.set_font("Arial","B",11)
    pdf.cell(0,8,"1. INFORMACION GENERAL",0,1,fill=True)
    pdf.set_font("Arial","",10)

    pdf.cell(95,7,f"Cliente: {row.get('cliente','')}",1)
    pdf.cell(95,7,f"Vendedor: {row.get('vendedor','')}",1,1)
    pdf.cell(95,7,f"Trabajo: {row.get('nombre_trabajo','')}",1)
    pdf.cell(95,7,f"OP Anterior: {row.get('op_anterior','N/A')}",1,1)
    pdf.cell(190,7,f"Fecha de Creacion: {row.get('created_at','')[:10]}",1,1)

    # 2. DATOS TÉCNICOS DE ENTRADA Y OBJETIVO
    pdf.ln(4)
    pdf.set_font("Arial","B",11)
    pdf.cell(0,8,"2. DATOS TECNICOS Y OBJETIVO DEL PROCESO",0,1,fill=True)
    pdf.set_font("Arial","",10)

    # Fila 1: Material y Dimensiones
    pdf.cell(63,7,f"Material Base: {row.get('material','')}",1)
    pdf.cell(63,7,f"Gramaje: {row.get('gramaje_rollos','')}g",1)
    pdf.cell(64,7,f"Referencia Comercial: {row.get('ancho_base','')}",1,1)

    # Fila 2: Cantidades
    pdf.cell(95,7,f"Cantidad Rollos Solicitados: {row.get('cantidad_rollos','')}",1)
    pdf.cell(95,7,f"Tipo de Creacion: {row.get('tipo_creacion','NUEVA')}",1,1)

    # Fila 3: Objetivo (Campo muy importante en rebobinado)
    pdf.set_font("Arial","B",10)
    pdf.cell(190,7,"OBJETIVO PRINCIPAL DEL REBOBINADO:", "LTR", 1)
    pdf.set_font("Arial","",10)
    pdf.multi_cell(190,7, row.get('objetivo_rebobinado','No especificado'), "LRB")

    # 3. OBSERVACIONES DE PLANIFICACIÓN
    pdf.ln(5)
    pdf.set_font("Arial","B",11)
    pdf.cell(0,8,"3. OBSERVACIONES ADICIONALES",0,1,fill=True)
    pdf.set_font("Arial","",10)
    pdf.multi_cell(0,7, row.get("observaciones_rollos","Sin observaciones adicionales"), 1)

    # 4. ESPACIO PARA ANOTACIONES DE PLANTA (Opcional pero útil)
    pdf.ln(5)
    pdf.set_font("Arial","I",8)
    pdf.cell(0,5,"* Espacio reservado para el operario: verificar empalmes y diámetros finales.",0,1)

    # PIE DE PÁGINA
    pdf.ln(10)
    pdf.set_font("Arial","I",7)
    pdf.cell(0,10,f"SISTEMA C&B PAPELES  - GENERADO: {hora_colombia().strftime('%d/%m/%Y %H:%M')}",0,1,"C")

    return bytes(pdf.output())

# RADIOGRAFÍA TECNICA

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
# DISEÑO DE TARGETAS DE DENTRADA

            with st.container():
                st.markdown(f"""
                <div class='historial-card'>
                    <div class='historial-header'>
                        <span>✅ {h['area']} — {h['maquina']}</span>
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

# ESTRUCTURA DE MENÚ  GENERAL 

if 'sel_tipo' not in st.session_state: st.session_state.sel_tipo = None
if 'rep' not in st.session_state: st.session_state.rep = None
# 🔐 LOGIN PRINCIPAL (pantalla completa)
if not st.session_state.get('autenticado'):
    st.title("🔐 Acceso al Sistema C&B Palepes De Colombia")
    
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

# --- ESTRUCTURA DE MENÚ CON PERMISOS POR ROL ---
with st.sidebar:
    st.title("🏭 C&B Papeles")
    
    # Obtenemos el rol (aseguramos minúsculas para evitar errores)
    rol = st.session_state.get('rol', 'operario').lower()
    
    # 1. Definimos las opciones según el rol
    if rol == 'admin':
        opciones_menu = ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación", "🌀 Rebobinadoras", "📦 Inventario", "📦 Bodega Terminado"]
    elif rol == 'ventas':
        opciones_menu = ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación"]
    elif rol == 'supervisor_imp':
        opciones_menu = ["🖥️ Monitor", "🖨️ Impresión", "📕 Encuadernación"]
    elif rol == 'supervisor_cor':
        opciones_menu = ["🖥️ Monitor", "✂️ Corte"]
    elif rol == 'supervisor_enc':
        opciones_menu = ["🖥️ Monitor", "📕 Encuadernación"]
    elif rol == 'supervisor_reb':
        opciones_menu = ["🖥️ Monitor", "🌀 Rebobinadoras"]
    elif rol == 'patinador_roll':
        opciones_menu = ["📦 Bodega Terminado"]
    else:
        # Operarios y otros roles
        opciones_menu = ["🖥️ Monitor"]

    # 2. Creamos el radio button (Menú)
    menu = st.radio("SELECCIONE MÓDULO:", opciones_menu)
    
    st.divider()
    st.caption(f"Usuario: {st.session_state.get('usuario_actual')} | Rol: {rol}")
    
    # 3. Botón de Cerrar Sesión (Indispensable para probar roles)
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    
    st.divider()
    st.info(f"Usuario: {st.session_state.get('nombre_usuario')}\n\nRol: {rol.upper()}")
    st.caption("Conectado a Supabase Cloud")

#  MÓDULO 1: MONITOR 

if menu == "🖥️ Monitor":
    st.title("Monitor de Planta")
    
    act_data = supabase.table("trabajos_activos").select("*").execute().data

#  ALERTAS DE OP ESTANCADAS

    alertas = []

    for a in act_data:
        try:
            inicio = datetime.fromisoformat(a["hora_inicio"].replace("Z", "+00:00"))
            ahora = hora_colombia()

            horas = (ahora - inicio).total_seconds() / 3600

            if horas > 4:  # ⚠️ SE PUIEDE CAMBIA A 6 U 8 HORAS
                alertas.append(f"⚠️ OP {a['op']} en {a['maquina']} lleva {round(horas,1)}h")

        except:
            pass

    if alertas:
        st.error("🚨 ALERTAS DE PRODUCCIÓN:")
        for al in alertas:
            st.write(al)

#  TRAER NOMBRES DE  LA OP

    ops = supabase.table("ordenes_planeadas").select("op,nombre_trabajo").execute().data
    map_ops = {o['op']: o['nombre_trabajo'] for o in ops}

# UNIR TODOS LOS DATOS 

    act = {}
    for a in act_data:
        op = a['op']
        a['nombre_trabajo'] = map_ops.get(op, "SIN NOMBRE")
        act[a['maquina']] = a
        
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    st.markdown(
                        f"<div class='card-produccion'>{m}<br>OP: {act[m]['op']}<br>{act[m]['nombre_trabajo']}</div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"<div class='card-vacia'>{m}<br>LIBRE</div>",
                        unsafe_allow_html=True
                    )
    time.sleep(30); 
    st.rerun()

#  MÓDULO 2: SEGUIMIENTO 

elif menu == "🔍 Seguimiento":
    st.title("Seguimiento de Producción")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    
#  BUSCADOR 

    buscar = st.text_input("🔎 Buscar por OP, Cliente o Nombre del Trabajo")
    
    if res:
        df = pd.DataFrame(res)

# FILTRO DE BUSQUEDA

        if buscar:
            buscar = buscar.upper()
            df = df[
                df["op"].fillna("").str.upper().str.contains(buscar, na=False) |
                df["nombre_trabajo"].fillna("").str.upper().str.contains(buscar, na=False) |
                df["cliente"].fillna("").str.upper().str.contains(buscar, na=False)
            ]
        excel_file = to_excel_limpio(df, "GENERAL")

        if excel_file:
            st.download_button(
                "📥 Excel General",
                data=excel_file,
                file_name="Reporte_General_C&B PAPELES .xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        st.divider()
        h1, h2, h3, h4, h5, h6, h7 = st.columns([1,2,2,1.5,1.5,1,1.5])
        h1.write("**OP**"); h2.write("**Cliente**"); h3.write("**Trabajo**"); h4.write("**Tipo**"); h5.write("**Status**"); h6.write("**Ver**"); h7.write("**Orden**")
        for index, row in df.iterrows():

            r1, r2, r3, r4, r5, r6, r7 = st.columns([1,2,2,1.5,1.5,1,1.5])

            r1.write(row['op'])
            r2.write(row['cliente'])
            r3.write(row['nombre_trabajo'])
            r4.write(row['tipo_orden'])

            color = "#FF9800" if row['proxima_area'] != "FINALIZADO" else "#4CAF50"
            r5.markdown(f"<span style='color:{color}; font-weight:bold;'>{row['proxima_area']}</span>", unsafe_allow_html=True)

# BOTON VER DETALLE

            if r6.button("👁️", key=f"v_{row['op']}"):
                modal_detalle_op(row.to_dict())

# BOTON ORDEN PDF

            if r7.button("📄", key=f"pdf_{row['op']}"):

                tipo = row["tipo_orden"]

                if "FORMAS" in row["tipo_orden"]:
                    pdf_bytes = generar_op_formas(row.to_dict())
                elif tipo == "REBOBINADO":
                    pdf_bytes = generar_op_rebobinado(row.to_dict())
                else:
                    pdf_bytes = generar_op_rollos(row.to_dict())

                st.download_button(
                    "⬇ Descargar Orden",
                    data=pdf_bytes,
                    file_name=f"OP_{row['op']}.pdf",
                    mime="application/pdf",
                    key=f"down_{row['op']}"
                )    

#  MÓDULO 3: PLANIFICACIÓN (CON REPETICIÓN Y AUTO-LLENADO) 

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
# BOTÓN COPIAR PARTE 1 A TODAS

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
            
# SECCIÓN: DATOS GENERALES 

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

######  SECCION: ROLLOS 

                r1, r2, r3 = st.columns(3)
                mat = r1.text_input("Material Base", value=datos_rec.get('material', ""))
                gram = r2.number_input("Gramaje", 0, value=int(datos_rec.get('gramaje_rollos', 0)))
                ref_c = r3.text_input("Referencia Comercial", value=datos_rec.get('ref_comercial', ""))
                
                r4, r5, r6 = st.columns(3)
                cant_r = r4.number_input("Cantidad Rollos", 0, value=int(datos_rec.get('cantidad_rollos', 0)))
                
                cores = ["13MM", "19MM", "1 PULGADA", "40 MM", "2 PULGADAS", "3 PULGADAS"]
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
                    ruta_inicial = "IMPRESIÓN"

                elif t == "FORMAS BLANCAS":
                    ruta_inicial = "IMPRESIÓN"

                elif t == "ROLLOS IMPRESOS":
                    ruta_inicial = "IMPRESIÓN"

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

# --- MÓDULO: BODEGA PRODUCTO TERMINADO ---

elif menu == "📦 Bodega Terminado":
    st.title("📦 Inventario de Producto Terminado")
    
    tab_mov, tab_inv = st.tabs(["🔄 Movimientos (Entrada/Salida)", "📊 Inventario Actual"])
    
    with tab_mov:
        st.subheader("🔄 Gestión de Movimientos")
        
        # 1. IDENTIFICAR PERMISOS SEGÚN ROL
        rol_usuario = st.session_state.get('rol', '').lower()
        
        # Definimos quién puede hacer qué
        puede_ingresar = rol_usuario in ['admin',] 
        puede_despachar = rol_usuario in ['admin', 'ventas',]

        # 2. SELECTOR DE OPERACIÓN FILTRADO
        opciones_disponibles = []
        if puede_ingresar: opciones_disponibles.append("➕ ENTRADA (Ingreso)")
        if puede_despachar: opciones_disponibles.append("➖ SALIDA (Despacho)")

        if not opciones_disponibles:
            st.warning("⚠️ Tu rol no tiene permisos para registrar movimientos en bodega.")
        else:
            tipo_accion = st.radio("Seleccione operación:", opciones_disponibles, horizontal=True)
            
            # Consultar productos para el selector
            productos_db = supabase.table("bodega_producto_terminado").select("*").execute().data
            nombres_existentes = [p['nombre_trabajo'] for p in productos_db]

            with st.form("form_movimiento_separado"):
                col1, col2 = st.columns(2)
                
                with col1:
                    # Si es ENTRADA, permitimos crear producto nuevo. Si es SALIDA, solo elegir de la lista.
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

                # BOTÓN DINÁMICO
                # BOTÓN DINÁMICO
                texto_boton = "🚀 REGISTRAR ENTRADA" if "ENTRADA" in tipo_accion else "🚚 REGISTRAR SALIDA"
                btn_procesar = st.form_submit_button(texto_boton)

                if btn_procesar:
                    if not nom_trabajo or nom_trabajo == "":
                        st.error("Debe especificar el nombre del trabajo.")
                    else:
                        # Aquí defines la variable
                        fecha_mov = hora_colombia().isoformat()
                        
                        producto_actual = next((p for p in productos_db if p['nombre_trabajo'] == nom_trabajo), None)
                        
                        # Lógica de Suma o Resta
                        es_entrada = "ENTRADA" in tipo_accion
                        factor = 1 if es_entrada else -1

                        # VALIDACIÓN DE STOCK PARA SALIDAS
                        if not es_entrada and producto_actual:
                            if c_cajas > producto_actual['stock_cajas']:
                                st.error(f"❌ Stock insuficiente. Solo hay {producto_actual['stock_cajas']} cajas disponibles.")
                                st.stop()

                        if producto_actual:
                            # ACTUALIZAR
                            nuevo_stk_cajas = producto_actual['stock_cajas'] + (c_cajas * factor)
                            nuevo_stk_rollos = producto_actual['stock_rollos'] + (c_rollos * factor)
                            
                            supabase.table("bodega_producto_terminado").update({
                                "stock_cajas": nuevo_stk_cajas,
                                "stock_rollos": nuevo_stk_rollos,
                                "ultima_actualizacion": fecha_mov  # <--- CAMBIADO: Antes decía fecha_db
                            }).eq("id", producto_actual['id']).execute()
                        
                        elif es_entrada:
                            # INSERTAR NUEVO
                            supabase.table("bodega_producto_terminado").insert({
                                "nombre_trabajo": nom_trabajo,
                                "tipo_producto": tipo_prod,
                                "stock_cajas": c_cajas,
                                "stock_rollos": c_rollos,
                                "ultima_actualizacion": fecha_mov  # <--- CAMBIADO: Antes decía fecha_db
                            }).execute()

                            # RECOMENDACIÓN: Registra también en el historial para que no se pierda la trazabilidad
                            supabase.table("bodega_historial").insert({
                                "nombre_trabajo": nom_trabajo,
                                "tipo_movimiento": tipo_accion,
                                "cajas": c_cajas,
                                "rollos": c_rollos,
                                "fecha": fecha_mov, # <--- Usar la misma variable aquí
                                "usuario": st.session_state.get('nombre_usuario')
                            }).execute()

                        st.success(f"✅ {texto_boton} exitoso para: {nom_trabajo}")
                        time.sleep(1.2)
                        st.rerun()
                        st.success(f"✅ {texto_boton} exitoso para: {nom_trabajo}")
                        time.sleep(1.2)
                        st.rerun()
    with tab_inv:
        st.subheader("Existencias en Bodega")
        
# Traer datos actualizados
        res_bodega = supabase.table("bodega_producto_terminado").select("*").order("nombre_trabajo").execute().data
        
        if res_bodega:
            df_bodega = pd.DataFrame(res_bodega)
            
# Limpiar columnas para mostrar
            df_show = df_bodega[['nombre_trabajo', 'tipo_producto', 'stock_cajas', 'stock_rollos', 'ultima_actualizacion']]
            df_show.columns = ['TRABAJO', 'TIPO', 'CAJAS', 'ROLLOS', 'ÚLT. MOVIMIENTO']
            
# Buscador rápido dentro del inventario
            busqueda_b = st.text_input("🔍 Filtrar inventario por nombre...")
            if busqueda_b:
                df_show = df_show[df_show['TRABAJO'].str.contains(busqueda_b.upper())]
            
# Mostrar tabla con estilo
            st.dataframe(df_show, use_container_width=True, hide_index=True)
            
# Alertas de stock bajo 
            bajo_stock = df_show[df_show['CAJAS'] <= 2]
            if not bajo_stock.empty:
                st.warning(f"⚠️ Hay {len(bajo_stock)} productos con 2 o menos cajas en existencia.")
        else:
            st.info("La bodega está vacía actualmente.")

# --- NUEVO MÓDULO: GESTIÓN DE INVENTARIO ---

elif menu == "📦 Inventario":
    st.title("Gestión de Suministros (Cores y Cajas)")
    
    tab1, tab2 = st.tabs(["📥 Ingresar Stock", "📊 Ver Existencias"])
    
    with tab1:
        tipo_insumo = st.radio("¿Qué va a ingresar?", ["CORES", "CAJAS"], horizontal=True)
        tabla_db = "inventario_cores" if tipo_insumo == "CORES" else "inventario_cajas"
        col_nombre = "nombre_core" if tipo_insumo == "CORES" else "nombre_caja"
        
# Traer datos de la DB según elección
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

# --- VALIDACIÓN DE ACCESO A ÁREAS DE PRODUCCIÓN ---
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación", "🌀 Rebobinadoras"]:
    rol_actual = st.session_state.get("rol", "operario").lower()

    # Diccionario de permisos unificado (Nombres de roles en minúsculas)
    PERMISOS = {
        "admin": ["TODOS"],
        "ventas": ["TODOS"],
        "supervisor_imp": ["IMPRESIÓN", "COLECTORAS"],
        "supervisor_cor": ["CORTE"],
        "supervisor_reb": ["REBOBINADORAS"],
        "supervisor_enc": ["ENCUADERNACIÓN"]
    }

    # Extraemos el nombre del área del texto del menú (ej: "IMPRESIÓN")
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

#  BOTON PAUSAR 

 # --- NUEVA LÓGICA DE PARADAS TÉCNICAS ---
                if not tr.get("pausado"):
# Botón de Parada de Emergencia / Técnica
                    with st.popover("🚨 REGISTRAR PARADA"):
                        motivo_p = st.selectbox("Motivo de parada:", MOTIVOS_PARADA, key=f"mot_{m}")
                        if st.button("Confirmar Parada", key=f"btn_p_{m}", type="primary"):
                            supabase.table("trabajos_activos").update({
                                "pausado": True,
                                "inicio_pausa": hora_colombia().isoformat(),
                                "motivo_pausa": motivo_p # Asegúrate de tener esta columna en trabajos_activos o se guardará en metadata
                            }).eq("maquina", m).execute()
                            st.rerun()
                else:
    # Mostrar por qué está detenida
                    st.error(f"DETENIDA POR: {tr.get('motivo_pausa', 'Sin motivo')}")
                    if st.button(f"▶️ REANUDAR TRABAJO", key=f"r_{m}", type="secondary"):
                        try:
                            inicio_p = datetime.fromisoformat(tr["inicio_pausa"].replace("Z", "+00:00"))
                            ahora = hora_colombia()
                            pausa_segundos = (ahora - inicio_p).total_seconds()
            
# Guardar en la tabla histórica de tiempos muertos
                            supabase.table("tiempos_muertos").insert({
                                "maquina": m,
                                "motivo": tr.get('motivo_pausa'),
                                "inicio": tr["inicio_pausa"],
                                "fin": ahora.isoformat(),
                                "duracion_segundos": pausa_segundos
                            }).execute()

# Actualizar el registro activo para seguir trabajando
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
    
# 1. Intentar buscar cuándo terminó el último trabajo en esta máquina
                        ultimo_registro = supabase.table("tiempos_muertos").select("fin").eq("maquina", m).order("fin", desc=True).limit(1).execute()
    
                        if ultimo_registro.data:
                            fin_ultimo = datetime.fromisoformat(ultimo_registro.data[0]["fin"].replace("Z", "+00:00"))
                            ocio_segundos = (hora_colombia() - fin_ultimo).total_seconds()
        
# Guardar el tiempo que estuvo libre como "Tiempo Libre / Espera"
                            if ocio_segundos > 60: # Solo si fue más de 1 minuto
                                supabase.table("tiempos_muertos").insert({
                                    "maquina": m,
                                    "motivo": "TIEMPO LIBRE (ENTRE OPs)",
                                    "inicio": ultimo_registro.data[0]["fin"],
                                    "fin": ahora_iso,
                                    "duracion_segundos": ocio_segundos
                                }).execute()

# 2. Iniciar el trabajo normal
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
                
# Usamos dos columnas nuevas para que los selectores de inventario queden alineados
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
# Última fila de datos técnicos
                f1, f2, f3 = st.columns(3)
                datos_c['varillas_finales'] = f1.number_input("Total varillas", 0)
# Este campo es el que usara para descontar del inventario de cajas
                datos_c['cajas_totales'] = f2.number_input("Total Cajas Empacadas", 0, help="Esta cantidad se restará del inventario de la caja seleccionada arriba.")
                datos_c['desperdicio'] = f3.number_input("Total desperdicio (Kg)", 0)

            elif area_act == "COLECTORAS":
                c1, c2, c3 = st.columns(3) 
                datos_c['tipo_papel'] = c1.text_input("tipo de papel")
                datos_c['formas_colectadas'] = c2.number_input("total formas colectadas", 0)
                datos_c['partes'] = c3.number_input("total partes colectadas", 0)
                
# --- CONSUMO DE CAJAS EN COLECTORAS ---
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
                
# --- CONSUMO DE CAJAS EN ENCUADERNACIÓN ---
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

            with col_f1:
                finalizar = st.form_submit_button("🏁 FINALIZAR Y MOVER")

            with col_f2:
                parcial = st.form_submit_button("📦 ENTREGA PARCIAL")

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

# --- LÓGICA DE DESCUENTO DE INVENTARIO ---

                    if area_act == "CORTE" and 'id_tubo_inventario' in datos_c:
                        id_t = datos_c['id_tubo_inventario']
                        cant_gastar = datos_c.get('rollos_finales', 0)
                        if cant_gastar > 0:
                            stk = supabase.table("inventario_cores").select("stock_actual").eq("id", id_t).single().execute().data
                            if stk:
                                supabase.table("inventario_cores").update({"stock_actual": stk['stock_actual'] - cant_gastar}).eq("id", id_t).execute()
                                datos_c['info_inventario_tubo'] = f"Descontados {cant_gastar} tubos"

# 2. Descuento de Cajas (Aplica para CORTE, COLECTORAS y ENCUADERNACIÓN)
                    if 'id_caja_inventario' in datos_c:
                        id_cj = datos_c['id_caja_inventario']
                        cant_cj = datos_c.get('cajas_totales', 0)
                        if cant_cj > 0:
                            stk_cj = supabase.table("inventario_cajas").select("stock_actual").eq("id", id_cj).single().execute().data
                            if stk_cj:
                                nuevo_stock_caja = stk_cj['stock_actual'] - cant_cj
                                supabase.table("inventario_cajas").update({"stock_actual": nuevo_stock_caja}).eq("id", id_cj).execute()
                                datos_c['info_inventario_caja'] = f"Descontadas {cant_cj} de {datos_c.get('nombre_caja')}"

# DETENER OP  NO CUENTA TIEMPO

                    d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                    tipo = d_op['tipo_orden']
                    n_area = "FINALIZADO"

#  RUTAS 

                    if tipo == "FORMAS IMPRESAS":
                        if area_act == "IMPRESIÓN":
                            n_area = "COLECTORAS"
                        elif area_act == "COLECTORAS":
                            n_area = "ENCUADERNACIÓN"
                        elif area_act == "ENCUADERNACIÓN":
                             n_area = "FINALIZADO"

                    elif tipo == "FORMAS BLANCAS":
                        if area_act == "IMPRESIÓN":
                            n_area = "COLECTORAS"
                        elif area_act == "COLECTORAS":
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
                        "historial_procesos": hist
                   }).eq("op", r['op']).execute()

#  SOLO FINAL BORRA ACTIVO

                    supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()

                    st.session_state.rep = None
                    st.rerun()

#  ENTREGAS PARCIALES 

            if parcial:

                if not op_name:
                    st.error("Debes ingresar el operario")
                    st.stop()

                if cantidad_parcial <= 0:
                    st.error("Debes ingresar cantidad parcial")
                    st.stop()

                inicio_raw = r['hora_inicio']

                if isinstance(inicio_raw, str):
                    inicio = datetime.fromisoformat(inicio_raw.replace("Z", "+00:00"))
                else:
                    inicio = inicio_raw

                fin = hora_colombia()

                tiempo_pausa = r.get("tiempo_pausa", 0)

                fin_ajustado = fin

                from datetime import timedelta
                fin_ajustado = fin - timedelta(seconds=tiempo_pausa)

                duracion = calcular_duracion_laboral(inicio, fin_ajustado)

#  RUTAS 2
                d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                tipo = d_op['tipo_orden']
                n_area = "FINALIZADO"

                if tipo == "FORMAS IMPRESAS":
                    if area_act == "IMPRESIÓN":
                        n_area = "COLECTORAS"
                    elif area_act == "COLECTORAS":
                        n_area = "ENCUADERNACIÓN"

                elif tipo == "FORMAS BLANCAS":
                    if area_act == "IMPRESIÓN":
                        n_area = "COLECTORAS"
                    elif area_act == "COLECTORAS":
                        n_area = "ENCUADERNACIÓN"

                elif tipo == "ROLLOS IMPRESOS":
                        if area_act == "IMPRESIÓN":
                            n_area = "CORTE"

                elif tipo == "ROLLOS BLANCOS":
                        if area_act == "CORTE":
                            n_area = "FINALIZADO"

                hist = d_op.get('historial_procesos') or []

                hist.append({
                    "area": area_act,
                    "maquina": r['maquina'],
                    "operario": op_name,
                    "auxiliar": auxiliar,
                    "fecha": fin.strftime("%d/%m/%Y %H:%M"),
                    "duracion": duracion,
                    "tipo": "PARCIAL",
                    "cantidad_parcial": cantidad_parcial,
                    "observaciones": obs_parcial
                })

#  SOLO AVANZA, NO CIERRA

                # --- LÓGICA DE ENTREGA PARCIAL CORREGIDA ---

                # Definimos el flujo lógico
                n_area = area_act # Por defecto se queda en la misma para que otro (o el mismo) pueda seguir
                if tipo == "RESMA":
                    if area_act == "IMPRESIÓN":
                        n_area_siguiente = "COLECTORAS"
                    elif area_act == "COLECTORAS":
                        n_area_siguiente = "ENCUADERNACIÓN"
                    else:
                        n_area_siguiente = "FINALIZADO"

                elif tipo == "ROLLOS IMPRESOS":
                    if area_act == "IMPRESIÓN":
                        n_area_siguiente = "CORTE"
                    else:
                        n_area_siguiente = "FINALIZADO"
                else:
                    n_area_siguiente = "FINALIZADO"

                hist = d_op.get('historial_processes') or []

                hist.append({
                    "area": area_act,
                    "maquina": r['maquina'],
                    "operario": op_name,
                    "auxiliar": auxiliar,
                    "fecha": fin.strftime("%d/%m/%Y %H:%M"),
                    "duracion": duracion,
                    "tipo": "PARCIAL",
                    "cantidad_parcial": cantidad_parcial,
                    "observaciones": f"ENTREGA PARCIAL: {obs_parcial}"
                })
                
                supabase.table("ordenes_planeadas").update({
                    "proxima_area": n_area_siguiente, # Esto la manda a la siguiente fila del monitor
                    "historial_procesos": hist,
                    "estado_parcial": "ACTIVO EN ORIGEN" # Marca especial para saber que no ha terminado en el área anterior
                }).eq("op", r['op']).execute()

                st.success(f"Entrega parcial registrada. La OP ahora aparece en {n_area_siguiente} y sigue disponible aquí.")

# LIBERAR MAQUINA (Esto es vital para que la máquina quede lista para otra cosa o para seguir con la misma OP)
                supabase.table("trabajos_activos").delete().eq("id", r['id']).execute()
                
# Opcional: Registrar el fin de este tramo en tiempos muertos para medir el "Tiempo Libre"
                supabase.table("tiempos_muertos").insert({
                    "maquina": r['maquina'],
                    "motivo": "FIN TRAMO PARCIAL",
                    "inicio": fin.isoformat(),
                    "fin": fin.isoformat(),
                    "duracion_segundos": 0
                }).execute()
                
                st.rerun()

if st.session_state.get('rol') == 'admin':
    st.divider()
    with st.expander("➕ Panel de Administración de Usuarios"):
        st.info("Desde aquí se puede dar de alta nuevos operarios en la base de datos de Supabase.")
        
        # Usamos columnas para que se vea más ordenado
        c1, c2 = st.columns(2)
        with c1:
            nuevo_u = st.text_input("Usuario (Login)", key="admin_u")
            nuevo_p = st.text_input("Nueva Clave", type="password", key="admin_p")
        with c2:
            nuevo_n = st.text_input("Nombre Completo", key="admin_n")
            nuevo_r = st.selectbox("Rol", ["admin", "ventas", "supervisor_imp", "supervisor_cor", "supervisor_reb", "supervisor_enc", "patinador_roll" ], key="admin_r")
        
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

