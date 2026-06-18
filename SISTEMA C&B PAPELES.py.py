import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, timedelta, time as time_cls 
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

# FUNCION DE HORARIOS
def hora_colombia():
    tz = pytz.timezone("America/Bogota")
    return datetime.now(tz)

def get_planta_activa() -> bool:
    """Consulta si la planta está activa en Supabase. Cache 10 segundos."""
    cache_key = '_planta_activa_cache'
    cache_ts   = '_planta_activa_ts'
    ahora      = hora_colombia().timestamp()
    if cache_key in st.session_state and ahora - st.session_state.get(cache_ts, 0) < 10:
        return st.session_state[cache_key]
    try:
        res = supabase.table("configuracion_sistema").select("valor")\
              .eq("clave", "planta_activa").single().execute()
        activa = str(res.data.get("valor", "true")).lower() == "true"
    except:
        activa = True  
    st.session_state[cache_key] = activa
    st.session_state[cache_ts]  = ahora
    return activa

def set_planta_activa(estado: bool, usuario: str = "admin"):
    """Activa o desactiva la planta globalmente. Usa upsert por si la fila no existe."""
    supabase.table("configuracion_sistema").upsert({
        "id":         1,
        "clave":      "planta_activa",
        "valor":      "true" if estado else "false",
        "updated_at": hora_colombia().isoformat(),
        "updated_by": usuario
    }).execute()
    
    st.session_state.pop('_planta_activa_cache', None)
    st.session_state.pop('_planta_activa_ts', None)

# FUNCION DE DURACION 
def calcular_duracion_laboral(inicio, fin, nombre_maquina=None, tiempo_pausa_segundos=0):
    """Calcula tiempo trabajado descontando pausas individuales y respetando estado de planta."""
    if nombre_maquina:
        if not obtener_estado_maquina(nombre_maquina):
            return "0:00:00"
    if not get_planta_activa():
        return "0:00:00"
    total = fin - inicio
    if total.total_seconds() < 0:
        return "0:00:00"
    
# Descontar pausas acumuladas 
    total_segundos = max(0, total.total_seconds() - tiempo_pausa_segundos)
    return str(timedelta(seconds=int(total_segundos)))
    
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
            area_txt  = str(h.get('area','?')).encode('latin-1','replace').decode('latin-1')
            maq_txt   = str(h.get('maquina','?')).encode('latin-1','replace').decode('latin-1')
            op_txt    = str(h.get('operario') or h.get('usuario','N/A')).encode('latin-1','replace').decode('latin-1')
            aux_txt   = str(h.get('auxiliar','N/A')).encode('latin-1','replace').decode('latin-1')
            fecha_txt = str(h.get('fecha') or h.get('fin') or h.get('inicio',''))[:19].encode('latin-1','replace').decode('latin-1')
            dur_txt   = str(h.get('duracion','0:00:00')).encode('latin-1','replace').decode('latin-1')

            pdf.cell(0, 7, f" AREA: {area_txt} | MAQUINA: {maq_txt}", ln=True, fill=True, border=1)

# FILA DE RESPONSABLES POR OP
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(65, 6, f"Operador: {op_txt}", border='LR')
            pdf.cell(65, 6, f"Auxiliar: {aux_txt}", border='R')
            pdf.cell(0, 6, f"Fecha: {fecha_txt}", border='R', ln=True)

# FILA DE TIEMPOS TOMADOS POR OP
            pdf.cell(0, 6, f"Duracion del Proceso: {dur_txt}", border='LRB', ln=True)
# DATOS TECNICOS SALIDA JHSON
            pdf.set_font("Arial", '', 8)

            datos_c = h.get('datos_cierre', {})

            if datos_c:

                pdf.set_font("Arial", 'B', 7)
                pdf.set_fill_color(230,230,230)

# ENCABEZADOS TABLA
                pdf.cell(47,6,"OBJETO",1,0,'C',True)
                pdf.cell(48,6,"DATO",1,0,'C',True)
                pdf.cell(47,6,"OBJETO",1,0,'C',True)
                pdf.cell(48,6,"DATO",1,1,'C',True)

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

                    pdf.cell(47,6,key1,1)
                    pdf.cell(48,6,str(v1),1)
                    pdf.cell(47,6,key2,1)
                    pdf.cell(48,6,str(v2),1,1)
            
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
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "1. INFORMACION DE LA ORDEN", 0, 1, fill=True)

    pdf.set_font("Arial", "B", 10); pdf.cell(20, 7, " Cliente: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(95, 7, f"{row.get('cliente','')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(20, 7, " Vendedor: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(55, 7, f"{row.get('vendedor','')}", 1, 1) 
    pdf.set_font("Arial", "B", 10); pdf.cell(20, 7, " Trabajo: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(100, 7, f"{row.get('nombre_trabajo','')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(25, 7, " Tipo Orden: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(45, 7, f"{row.get('tipo_orden','')}", 1, 1) 

#  ESPECIFICACIONES TECNICAS
    pdf.ln(4)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "2. ESPECIFICACIONES TECNICAS", 0, 1, fill=True)

    pdf.set_font("Arial", "B", 10); pdf.cell(20, 7, " Material: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(43, 7, f"{row.get('material','')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(20, 7, " Gramaje: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(43, 7, f"{row.get('gramaje_rollos','')} GRS", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(20, 7, " Core: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(44, 7, f"{row.get('core','')}", 1, 1) 
    pdf.set_font("Arial", "B", 10); pdf.cell(30, 7, " Cant. Rollos: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(33, 7, f"{row.get('cantidad_rollos','')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(30, 7, " Unid. Bolsa: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(33, 7, f"{row.get('unidades_bolsa','')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(30, 7, " Unid. Caja: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(34, 7, f"{row.get('unidades_caja','')}", 1, 1)
    pdf.set_font("Arial", "B", 10); pdf.cell(35, 7, " Ref. Comercial: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(100, 7, f"{row.get('ref_comercial','')}", 1, 0)
    trans = "SI" if row.get('transportadora_rollos') else "NO"
    pdf.set_font("Arial", "B", 10); pdf.cell(30, 7, " Transportadora: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(25, 7, f"{trans}", 1, 1) 
    pdf.set_font("Arial", "B", 10); pdf.cell(20, 8, "Impresión", 1, 0, 'C', fill=True)
    pdf.set_font("Arial", "B", 10); pdf.cell(27, 8, " Frente: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(65, 8, f"{row.get('tintas_frente_rollos', 'N/A')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(23, 8, " Respaldo: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(55, 8, f"{row.get('tintas_respaldo_rollos', 'N/A')}", 1, 1) 
    pdf.set_font("Arial", "B", 10); pdf.cell(25, 7, " Destino: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(165, 7, f"{row.get('destino_rollos','PLANTA')}", 1, 1)

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


# GENERAR PDF FORMAS        pdf.set_font("Arial", "B", 10); pdf.cell(23, 8, " Respaldo: ", 1, 0, fill=True)         pdf.set_font("Arial", "", 10);  pdf.cell(65, 8, f"{row.get('tintas_frente_rollos', 'N/A')}", 1, 0)
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

#  INFORMACION DE LA ORDEN 
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "1. INFORMACION DE LA ORDEN", 0, 1, fill=True)
    pdf.set_font("Arial", "B", 10); pdf.cell(25, 7, " Cliente: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(70, 7, f"{row.get('cliente','')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(25, 7, " Vendedor: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(70, 7, f"{row.get('vendedor','')}", 1, 1)
    pdf.set_font("Arial", "B", 10); pdf.cell(25, 7, " Trabajo: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(70, 7, f"{row.get('nombre_trabajo','')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(25, 7, " Tipo Orden: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(70, 7, f"{row.get('tipo_orden','')}", 1, 1)
    pdf.set_font("Arial", "B", 10); pdf.cell(25, 7, " OP Anterior: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(70, 7, f"{row.get('op_anterior','')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(25, 7, " Fecha: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(70, 7, f"{row.get('created_at','')[:10]}", 1, 1)

# ESPECIFICACIONES GENERALES Y ACABADOS 
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "2. ESPECIFICACIONES GENERALES Y ACABADOS", 0, 1, fill=True)
    pdf.set_font("Arial", "B", 10); pdf.cell(23, 7, " Cantidad: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(40, 7, f"{row.get('cantidad_formas','')}FORMAS", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(18, 7, " Partes: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(45, 7, f"{row.get('num_partes','')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(26, 7, " Presentación: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(38, 7, f"{row.get('presentacion','')}", 1, 1)
    pdf.set_font("Arial", "B", 10); pdf.cell(25, 7, " Numeración Del: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(70, 7, f"{row.get('num_id','NO')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(25, 7, " Numeración Al: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(70, 7, f"{row.get('num_fd','')}", 1, 1)
    pdf.set_font("Arial", "B", 10); pdf.cell(35, 7, " Código Barras: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(90, 7, f"{row.get('codigo_barras_detalle','')}", 1, 0)
    trans = "SI" if row.get('transportadora_formas') else "NO"
    pdf.set_font("Arial", "B", 10); pdf.cell(30, 7, " Transportadora: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(35, 7, f"{trans}", 1, 1)
    pdf.set_font("Arial", "B", 10); pdf.cell(25, 7, " Tipo Pegue: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(70, 7, f"{row.get('presentacion2', 'N/A')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(25, 7, " Destino: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(70, 7, f"{row.get('destino_formas','NO APLICA')}", 1, 1)


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
    pdf.cell(4,7,"P",1,0,"C",True)
    pdf.cell(15,7,"ANCHO",1,0,"C",True)
    pdf.cell(15,7,"LARGO",1,0,"C",True)
    pdf.cell(28,7,"PAPEL",1,0,"C",True)
    pdf.cell(20,7,"COLOR",1,0,"C",True)
    pdf.cell(12,7,"GR",1,0,"C",True)
    pdf.cell(50,7,"T. FRENTE",1,0,"C",True)
    pdf.cell(23,7,"T. RESP",1,0,"C",True)
    pdf.cell(23,7,"OBS",1,1,"C",True)

    pdf.set_font("Arial","",7.5)
    partes = row.get("detalles_partes_json",[])
    for p in partes:
        cell_fit(pdf,4,7,p.get("p",""))
        cell_fit(pdf,15,7,p.get("anc",""))
        cell_fit(pdf,15,7,p.get("lar",""))
        cell_fit(pdf,28,7,p.get("papel",""))
        cell_fit(pdf,20,7,p.get("color_fondo",""))
        cell_fit(pdf,12,7,p.get("gramos",""))
        cell_fit(pdf,50,7,p.get("tf",""))
        cell_fit(pdf,23,7,p.get("tr",""))
        cell_fit(pdf,23,7,p.get("obs_parte","")) 
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

# ENCABEZADO 
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
            🎨 <b>Presentación:</b> {row.get('presentacion')}<br>
            ⚠️ <b>Numeracion Desde:</b> {row.get('num_id')}<br>
            ⚠️ <b>Numeracion Hasta:</b> {row.get('num_fd')}
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
                        <span>📅 {h.get('fecha') or h.get('fin') or h.get('inicio') or 'Sin fecha'}</span>
                    </div>
                    <div class='historial-tecnico'>
                        <div>👤 <b>Operario:</b> {h.get('operario') or h.get('usuario') or 'N/A'}</div>
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
        opciones_menu = ["🖥️ Monitor", "📆 Cronograma Impresión", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "⏱️ Seguimiento Cortadoras", "📥 Colectoras", "📕 Encuadernación", "🌀 Rebobinadoras", "📦 Inventario", "📦 salida produccion P1", "📊 Reportes Admin", "🎨 Diseño y Pre-Prensa", "📦 Almacen/Despachos", "🛒 Mercado"]     
    elif rol == 'ventas':
        opciones_menu = ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación"]
    elif rol == 'jefe_log':
        opciones_menu = ["📦 salida produccion P1", "📊 Reportes Admin", "📦 Almacen/Despachos"]
    elif rol == 'patinador_log':
        opciones_menu = ["📦 Almacen/Despachos"]
    elif rol == 'aux_log':
        opciones_menu = ["📦 Almacen/Despachos"]
    elif rol == 'supervisor_imp':
        opciones_menu = ["🖥️ Monitor", "🖨️ Impresión", "📥 Colectoras", "📕 Encuadernación"]
    elif rol == 'supervisor_cor':
        opciones_menu = ["🖥️ Monitor", "✂️ Corte", "⏱️ Seguimiento Cortadoras"]
    elif rol == 'supervisor_enc':
        opciones_menu = ["🖥️ Monitor", "📕 Encuadernación"]
    elif rol == 'supervisor_reb':
        opciones_menu = ["🖥️ Monitor", "🌀 Rebobinadoras"]
    elif rol == 'patinador_roll':
        opciones_menu = ["📦 salida produccion P1"]
    elif rol == 'almacen':
        opciones_menu = ["📦 Almacen/Despachos"]
    elif rol == 'diseño':
        opciones_menu = ["🖥️ Monitor", "🎨 Diseño y Pre-Prensa", "🔍 Seguimiento"]
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

#  INTERRUPTOR GLOBAL DE PLANTA (solo admin)
    if st.session_state.get('rol','').lower() == 'admin':
        planta_on = get_planta_activa()
        col_sw1, col_sw2, col_sw3 = st.columns([1, 2, 3])
        with col_sw1:
            nuevo_estado = st.toggle(
                "🏭 PLANTA ACTIVA" if planta_on else "⏸️ PLANTA DETENIDA",
                value=planta_on,
                key="toggle_planta"
            )
            if nuevo_estado != planta_on:
                set_planta_activa(nuevo_estado, st.session_state.get('nombre_usuario','admin'))
                accion = "▶️ PLANTA ACTIVADA" if nuevo_estado else "⏸️ PLANTA DETENIDA"
                st.toast(f"{accion} — todos los contadores {'corriendo' if nuevo_estado else 'congelados'}", icon="🏭")
                time.sleep(0.5)
                st.rerun()
        with col_sw2:
            if planta_on:
                st.success("✅ Planta activa — contadores corriendo")
            else:
                st.error("⏸️ Planta detenida — contadores congelados")
                try:
                    res_cfg = supabase.table("configuracion_sistema").select("updated_at,updated_by")\
                              .eq("clave","planta_activa").single().execute().data
                    if res_cfg:
                        st.caption(f"Detenida por **{res_cfg['updated_by']}** a las {str(res_cfg['updated_at'])[:16]}")
                except:
                    pass
    else:
    
# Operarios solo ven el estado, no pueden cambiarlo
        if not get_planta_activa():
            st.error("⏸️ Planta detenida por administración — los contadores están en pausa")
    
#  TRAER ESTADOS DE MAQUINAS DE UN SOLO GOLPE 
    try:
        estados_db = supabase.table("estado_maquinas").select("maquina, estado").execute().data

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

# PASA EL ESTADO ACTUAL ALA FUNCION 
            tiempo_texto = calcular_duracion_laboral(inicio, ahora, a['maquina'], a.get('tiempo_pausa', 0))
            
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

# TARJETA  produccion
                    st.markdown(
                        f"<div class='card-produccion'>{m}<br>OP: {act[m]['op']}<br>{act[m]['nombre_trabajo']}</div>",
                        unsafe_allow_html=True
                    )
                else:

# TARJETA Libre
                    st.markdown(
                        f"<div class='card-vacia'>{m}<br>LIBRE</div>",
                        unsafe_allow_html=True
                    )

#  REFRESCO AUTOMATICO 
    try:
        from streamlit_autorefresh import st_autorefresh
        intervalo = st.select_slider(
            "🔄 Auto-refresco cada:",
            options=[15, 30, 60, 120],
            value=30,
            format_func=lambda x: f"{x} segundos"
        )
        st_autorefresh(interval=intervalo * 1000, key="monitor_refresh")
    except:
      
        col_ref = st.columns([3,1])[1]
        if col_ref.button("🔄 Actualizar ahora"):
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

# TABS DE SEGUIMIENTO: PENDIENTES / FINALIZADAS
        tab_pendientes, tab_finalizadas = st.tabs(["⏳ EN PROCESO / PENDIENTES", "✅ FINALIZADAS"])

        ordenes_pendientes = [r for r in ordenes if r.get('proxima_area', 'SIN ÁREA').upper() != "FINALIZADO"]
        ordenes_finalizadas = [r for r in ordenes if r.get('proxima_area', 'SIN ÁREA').upper() == "FINALIZADO"]

        def pintar_tarjeta_op(row):
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
                    return

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
            tipo_op = row.get('tipo_orden', '')
            if "FORMAS" in tipo_op:
                icono_tipo = "📄"
                etiqueta_tipo = "FORMAS"
                color_tipo = "#1565C0"
                borde_tipo = "#1565C0"
            elif "ROLLOS" in tipo_op:
                icono_tipo = "🌀"
                etiqueta_tipo = "ROLLOS"
                color_tipo = "#2E7D32"
                borde_tipo = "#2E7D32"
            elif "REBOBINADO" in tipo_op:
                icono_tipo = "🔄"
                etiqueta_tipo = "REBOBINADO"
                color_tipo = "#6A1B9A"
                borde_tipo = "#6A1B9A"
            else:
                icono_tipo = "📦"
                etiqueta_tipo = "OTRO"
                color_tipo = "#555"
                borde_tipo = "#555"
            
            # --- SOLUCIÓN: Eliminamos el st.markdown y usamos solo una línea de expander ---
            fecha_raw = row.get('created_at') or row.get('fecha_creacion') or ''
            try:
                fecha_fmt = datetime.fromisoformat(str(fecha_raw).replace("Z","")).strftime('%d/%m/%Y')
            except:
                fecha_fmt = ''
            titulo_unico = f"{icono_tipo} {etiqueta_tipo} | OP {op_id} | {cliente} | 💼 {vendedor} | 📅 {fecha_fmt} | {texto_estatus}"
            
            with st.expander(titulo_unico):
                # Aquí colocas los detalles de la orden usando comandos normales de Streamlit
                st.write("Detalles internos de la OP...")
                st.markdown(f"### ESTATUS DE TRABAJO: :{color_texto}[{texto_estatus}]")
                
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.write("**👤 CLIENTE:**") 
                    st.info(cliente)
                    st.write("**📅 FECHA:**")
                    st.info(row.get('created_at', '')[:10])
                    st.write("**🔙 ORDEN ANTERIOR:**")
                    st.info(row.get('op_anterior', '')[:10])
                with c2:
                    st.write("**🏗️ AREA ACTUAL:**")
                    st.info(area_destino)
                    st.write("**📦 CANTIDAD SOLICITADA:**")
                    st.info(row.get('cantidad_formas') if "FORMAS" in row.get('tipo_orden','') else row.get('cantidad_rollos','0'))
                    st.write("**📖 REFERENCIA COMERCIAL:**")
                    st.info(row.get('ref_comercial', ''))
                with c3:
                    st.write("**📝 NOMBRE DE TRABAJO:**")
                    st.info(nombre_t)
                    st.write("**⚙️ TIPO DE TRABAJO:**")
                    st.info(row.get('tipo_orden', 'N/A'))
                    st.write("**📋 OBSERVACIONES DE DISEÑO:**")
                    st.info(row.get('observaciones_diseno', 'N/A'))
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

# RECORRIDO DE TARJETAS POR PESTAÑA
        with tab_pendientes:
            if not ordenes_pendientes:
                st.info("No hay órdenes pendientes o en proceso.")
            for row in ordenes_pendientes:
                pintar_tarjeta_op(row)

        with tab_finalizadas:
            if not ordenes_finalizadas:
                st.info("No hay órdenes finalizadas.")
            for row in ordenes_finalizadas:
                pintar_tarjeta_op(row)

# MODULO DE DISEÑO
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
                st.write(f"**Tintas Frente:** {datos.get('tintas_frente_rollos')}")
                st.write(f"Tintas Respaldo: {datos.get('tintas_respaldo_rollos')}")
                st.write(f"Cantidad Solicitada: {datos.get('cantidad_rollos')}")
                st.write(f"Core: {datos.get('core')}")
            with c2:
                st.markdown("**ADICIONALES ROLLOS**")
                st.write(f"Referencia Comercial: {datos.get('ref_comercial')}")
                st.write(f"Unidades Por Bolsa: {datos.get('unidades_bolsa')}")
                st.write(f"Unidades Por Caja: {datos.get('unidades_caja')}")
                st.write(f"Repeticion : {datos.get('tipo_origen')}")
            with c3:
                st.markdown("**ADICIONALES FORMAS**")
                st.write(f"Perforaciones: {datos.get('perforaciones_detalle')}")
                st.write(f"Codigo De Barras: {datos.get('codigo_barras_detalle')}")
                st.write(f"Numeracion Inicial: {datos.get('num_id')}")
                st.write(f"Numeracion Final: {datos.get('num_fd')}")
            
            with c4:
                st.markdown("**ADICIONALES DE FORMAS**")
                st.write(f"Presentacion: {datos.get('presentacion')}")
                st.write(f"Encolada O Grapada Por: {datos.get('presentacion2', 0)}")
                st.write(f"Numero De Partes: {datos.get('num_partes', 0)}")
                st.write(f"Numero De Formas: {datos.get('cantidad_formas', 0)}")

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
                    link_arte = st.text_input("LINK DEL ARTE (DRIVE):", value=datos_op.get('link_diseno', '') or "")
                with col_inputs[1]:
                    
                    num_ticket = st.number_input("NUMERO DEL TICKET:", value=int(datos_op.get('num_ticket', 0) or 0), step=1)
                
                obs_dis = st.text_area("✍️ NOTAS PARA PRE-PRENSA:", value=datos_op.get('observaciones_diseno', '') or "")
                obs_dise = st.text_area("✍️ ESPECIFICACIONES PARA REVELAR PLANCHAS:", value=datos_op.get('observaciones_diseno2', '') or "")
                
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

    # Estados donde la OP aún no ha sido procesada por ningún área
    ESTADOS_EDITABLES = [
        "DISEÑO (AUDITORIA)", "IMPRESIÓN", "CORTE", "REBOBINADORAS",
        "ESPERA DE AUDITORIA", "ESPERA DE CORTE", "ESPERA DE IMPRESIÓN"
    ]

    tab_nueva, tab_editar = st.tabs(["➕ Nueva / Repetición", "✏️ Editar OP Existente"])

    with tab_editar:
        st.markdown("<div class='section-header'>✏️ EDITAR ORDEN DE PRODUCCIÓN</div>", unsafe_allow_html=True)
        st.caption("Solo puedes editar OPs que aún no han sido tomadas por ningún área de producción.")

        col_b1, col_b2 = st.columns([3, 1])
        op_buscar_edit = col_b1.text_input("Número de OP a editar (Ej: FRI-101):", key="op_edit_buscar")

        if col_b2.button("🔍 Buscar", key="btn_buscar_edit"):
            if op_buscar_edit:
                res_edit = supabase.table("ordenes_planeadas").select("*")\
                    .eq("op", op_buscar_edit.upper().strip()).execute()
                if res_edit.data:
                    st.session_state['op_editar_data'] = res_edit.data[0]
                else:
                    st.error("❌ No se encontró esa OP.")
                    st.session_state.pop('op_editar_data', None)
            else:
                st.warning("Ingresa el número de OP.")

        op_edit = st.session_state.get('op_editar_data')

        if op_edit:
            estado_actual = op_edit.get('proxima_area', '')
            rol_actual    = st.session_state.get('rol', '').lower()

            # Verificar si es editable
            es_editable = estado_actual in ESTADOS_EDITABLES
            es_admin    = rol_actual == 'admin'

# Mostrar estado actual
            st.markdown(f"""
            <div class='metric-box'>
              <b>📋 OP:</b> {op_edit.get('op')} &nbsp;&nbsp;
              <b>👤 Cliente:</b> {op_edit.get('cliente')} &nbsp;&nbsp;
              <b>🏷️ Tipo:</b> {op_edit.get('tipo_orden')} &nbsp;&nbsp;
              <b>📍 Estado actual:</b> <code>{estado_actual}</code>
            </div>
            """, unsafe_allow_html=True)

            if not es_editable and not es_admin:
                st.error(f"🔒 Esta OP ya fue tomada por producción ({estado_actual}) y no se puede editar.")
                st.caption("Si necesitas hacer un cambio urgente, contacta al administrador.")

            else:
                if not es_editable and es_admin:
                    st.warning("⚠️ Esta OP ya está en producción. Como admin puedes editarla igualmente.")

                st.markdown("---")
                st.markdown("**Edita los campos que necesitas corregir:**")

                with st.form("form_editar_op"):
#  DATOS GENERALES 
                    st.markdown("**📋 Datos Generales**")
                    ec1, ec2, ec3 = st.columns(3)
                    nuevo_cliente  = ec1.text_input("Cliente:", value=op_edit.get('cliente', ''))
                    nuevo_vendedor = ec2.text_input("Vendedor:", value=op_edit.get('vendedor', ''))
                    nuevo_trabajo  = ec3.text_input("Nombre del Trabajo:", value=op_edit.get('nombre_trabajo', ''))

                    tipo_op = op_edit.get('tipo_orden', '')

#  FORMAS IMPRESAS / BLANCAS 
                    if "FORMAS" in tipo_op:
                        st.markdown("**📑 Datos de Formas**")
                        ef1, ef2, ef3, ef4 = st.columns(4)
                        nueva_cant    = ef1.number_input("Cantidad Formas:", value=int(op_edit.get('cantidad_formas', 0) or 0), min_value=0)
                        nuevo_partes  = ef2.selectbox("Número de Partes:", [1,2,3,4,5,6], index=int(op_edit.get('num_partes', 1) or 1) - 1)
                        nueva_pres    = ef3.selectbox("Presentación:", PRESENTACIONES, index=PRESENTACIONES.index(op_edit['presentacion']) if op_edit.get('presentacion') in PRESENTACIONES else 0)
                        nueva_pres2   = ef4.selectbox("Encolada o Grapada:", PRESENTACIONES2, index=PRESENTACIONES2.index(op_edit['presentacion2']) if op_edit.get('presentacion2') in PRESENTACIONES2 else 0)

                        ep1, ep2, ep3, ep4 = st.columns(4)
                        t_perf_e  = ep1.selectbox("¿Perforaciones?", ["NO","SI"], index=1 if op_edit.get('perforaciones_detalle') and op_edit.get('perforaciones_detalle') != 'NO' else 0)
                        perf_det_e= ep1.text_area("Detalle Perforación:", value=op_edit.get('perforaciones_detalle','') or '') if t_perf_e == "SI" else "NO"
                        t_barr_e  = ep2.selectbox("¿Código de Barras?", ["NO","SI"], index=1 if op_edit.get('codigo_barras_detalle') and op_edit.get('codigo_barras_detalle') != 'NO' else 0)
                        barr_det_e= ep2.text_area("Detalle Barras:", value=op_edit.get('codigo_barras_detalle','') or '') if t_barr_e == "SI" else "NO"
                        t_num_e   = ep3.selectbox("¿Numeración?", ["NO","SI"], index=1 if op_edit.get('num_id') and op_edit.get('num_id') != 'NO' else 0)
                        num_id_e  = ep3.text_input("Desde:", value=op_edit.get('num_id','') or '') if t_num_e == "SI" else "NO"
                        num_fd_e  = ep3.text_input("Hasta:", value=op_edit.get('num_fd','') or '') if t_num_e == "SI" else "NO"
                        nueva_trans_f = ep4.selectbox("¿Transportadora?", ["NO","SI"], index=1 if op_edit.get('transportadora_formas') else 0)
                        nuevo_dest_f  = ep4.text_input("Ciudad destino:", value=op_edit.get('destino_formas','') or '') if nueva_trans_f == "SI" else "NO"

# Partes de la forma
                        st.markdown("**📄 Detalle de Partes**")
                        rec_partes_e = op_edit.get('detalles_partes_json') or []
                        lista_p_e = []
                        for i in range(1, nuevo_partes + 1):
                            p_data_e = rec_partes_e[i-1] if i <= len(rec_partes_e) else {}
                            st.markdown(f"*Parte {i}*")
                            d1,d2,d3,d4,d5,d6 = st.columns(6)
                            anc_e = d1.text_input(f"Ancho P{i}",  key=f"ea_{i}", value=p_data_e.get('anc',''))
                            lar_e = d2.text_input(f"Largo P{i}",  key=f"el_{i}", value=p_data_e.get('lar',''))
                            pap_e = d3.text_input(f"Papel P{i}",  key=f"ep_{i}", value=p_data_e.get('papel',''))
                            fon_e = d4.text_input(f"Fondo P{i}",  key=f"ef_{i}", value=p_data_e.get('color_fondo',''))
                            gra_e = d5.text_input(f"Gramos P{i}", key=f"eg_{i}", value=p_data_e.get('gramos',''))
                            tra_e = d6.text_input(f"Tráfico P{i}",key=f"et_{i}", value=p_data_e.get('trafico',''))
                            tf_e, tr_e, obe_e = "N/A", "N/A", ""
                            if tipo_op == "FORMAS IMPRESAS":
                                t1e,t2e,t3e = st.columns(3)
                                tf_e  = t1e.text_input(f"Tintas Frente P{i}",   key=f"etf_{i}", value=p_data_e.get('tf',''))
                                tr_e  = t2e.text_input(f"Tintas Respaldo P{i}", key=f"etr_{i}", value=p_data_e.get('tr',''))
                                obe_e = t3e.text_input(f"Obs. Especial P{i}",   key=f"eob_{i}", value=p_data_e.get('obs_parte',''))
                            lista_p_e.append({"p":i,"anc":anc_e,"lar":lar_e,"papel":pap_e,"color_fondo":fon_e,"gramos":gra_e,"tf":tf_e,"tr":tr_e,"trafico":tra_e,"obs_parte":obe_e})

                        nuevas_obs = st.text_area("Observaciones Generales:", value=op_edit.get('observaciones_formas','') or '')

#  ROLLOS IMPRESOS / BLANCOS 
                    elif tipo_op in ["ROLLOS IMPRESOS", "ROLLOS BLANCOS"]:
                        st.markdown("**🌀 Datos de Rollos**")
                        er1, er2, er3 = st.columns(3)
                        nuevo_mat   = er1.text_input("Material Base:", value=op_edit.get('material','') or '')
                        nuevo_gram  = er2.number_input("Gramaje:", value=int(op_edit.get('gramaje_rollos', 0) or 0), min_value=0)
                        nuevo_ref   = er3.text_input("Referencia Comercial:", value=op_edit.get('ref_comercial','') or '')

                        er4, er5 = st.columns(2)
                        nueva_cant_r = er4.number_input("Cantidad Rollos:", value=int(op_edit.get('cantidad_rollos', 0) or 0), min_value=0)
                        cores = ["13MM","19MM","1 PULGADA","40 MM","2 PULGADAS","3 PULGADAS"," NINGUNO"]
                        nuevo_core   = er5.selectbox("Core / Centro:", cores, index=cores.index(op_edit['core']) if op_edit.get('core') in cores else 0)

                        if tipo_op == "ROLLOS IMPRESOS":
                            ct1, ct2 = st.columns(2)
                            nuevo_tf_r = ct1.text_input("Tintas Frente:", value=op_edit.get('tintas_frente_rollos','') or '')
                            nuevo_tr_r = ct2.text_input("Tintas Respaldo:", value=op_edit.get('tintas_respaldo_rollos','') or '')
                        else:
                            nuevo_tf_r, nuevo_tr_r = "N/A", "N/A"

                        er6, er7 = st.columns(2)
                        nueva_uds_b = er6.number_input("Unidades x Bolsa:", value=int(op_edit.get('unidades_bolsa', 0) or 0), min_value=0)
                        nueva_uds_c = er7.number_input("Unidades x Caja:",  value=int(op_edit.get('unidades_caja',  0) or 0), min_value=0)

                        nueva_trans_r = st.selectbox("¿Transportadora?", ["NO","SI"], index=1 if op_edit.get('transportadora_rollos') else 0)
                        nuevo_dest_r  = st.text_input("Ciudad destino:", value=op_edit.get('destino_rollos','') or '') if nueva_trans_r == "SI" else "NO"
                        nuevas_obs    = st.text_area("Observaciones:", value=op_edit.get('observaciones_rollos','') or '')

#  REBOBINADO 
                    elif tipo_op == "REBOBINADO":
                        st.markdown("**🌀 Datos de Rebobinado**")
                        eb1, eb2, eb3 = st.columns(3)
                        nuevo_mat     = eb1.text_input("Material / Papel:", value=op_edit.get('material','') or '')
                        nuevo_gram    = eb2.number_input("Gramaje:", value=int(op_edit.get('gramaje_rollos', 0) or 0), min_value=0)
                        nuevo_ancho   = eb3.text_input("Referencia Comercial:", value=op_edit.get('ancho_base','') or '')
                        eb4, eb5 = st.columns(2)
                        nueva_cant_r  = eb4.number_input("Cantidad Rollos:", value=int(op_edit.get('cantidad_rollos', 0) or 0), min_value=0)
                        nuevo_obj     = eb5.text_input("Objetivo del Rebobinado:", value=op_edit.get('objetivo_rebobinado','') or '')
                        nuevas_obs    = st.text_area("Observaciones:", value=op_edit.get('observaciones_rollos','') or '')

                    st.markdown("---")
                    nueva_obs_gral = st.text_area("📝 Motivo del cambio (queda registrado):",
                                        placeholder="Ej: Cliente solicitó cambio de cantidad...", key="motivo_edit")
                    btn_guardar_edit = st.form_submit_button("💾 GUARDAR CAMBIOS", use_container_width=True)

                    if btn_guardar_edit:
                        if not nueva_obs_gral.strip():
                            st.error("⚠️ Debes escribir el motivo del cambio.")
                        else:
                            try:
                                update_payload = {
                                    "cliente":        nuevo_cliente,
                                    "vendedor":       nuevo_vendedor,
                                    "nombre_trabajo": nuevo_trabajo,
                                }
                                if "FORMAS" in tipo_op:
                                    update_payload.update({
                                        "cantidad_formas":       nueva_cant,
                                        "num_partes":            nuevo_partes,
                                        "presentacion":          nueva_pres,
                                        "presentacion2":         nueva_pres2,
                                        "perforaciones_detalle": perf_det_e,
                                        "codigo_barras_detalle": barr_det_e,
                                        "num_id":                num_id_e,
                                        "num_fd":                num_fd_e,
                                        "transportadora_formas": True if nueva_trans_f == "SI" else None,
                                        "destino_formas":        nuevo_dest_f if nueva_trans_f == "SI" else None,
                                        "detalles_partes_json":  lista_p_e,
                                        "observaciones_formas":  nuevas_obs,
                                    })
                                elif tipo_op in ["ROLLOS IMPRESOS", "ROLLOS BLANCOS"]:
                                    update_payload.update({
                                        "material":              nuevo_mat,
                                        "gramaje_rollos":        nuevo_gram,
                                        "ref_comercial":         nuevo_ref,
                                        "cantidad_rollos":       nueva_cant_r,
                                        "core":                  nuevo_core,
                                        "tintas_frente_rollos":  nuevo_tf_r,
                                        "tintas_respaldo_rollos":nuevo_tr_r,
                                        "unidades_bolsa":        nueva_uds_b,
                                        "unidades_caja":         nueva_uds_c,
                                        "transportadora_rollos": True if nueva_trans_r == "SI" else None,
                                        "destino_rollos":        nuevo_dest_r if nueva_trans_r == "SI" else None,
                                        "observaciones_rollos":  nuevas_obs,
                                    })
                                elif tipo_op == "REBOBINADO":
                                    update_payload.update({
                                        "material":             nuevo_mat,
                                        "gramaje_rollos":       nuevo_gram,
                                        "ancho_base":           nuevo_ancho,
                                        "cantidad_rollos":      nueva_cant_r,
                                        "objetivo_rebobinado":  nuevo_obj,
                                        "observaciones_rollos": nuevas_obs,
                                    })

                                supabase.table("ordenes_planeadas").update(update_payload)\
                                    .eq("op", op_edit['op']).execute()

                                hist = op_edit.get('historial_procesos') or []
                                hist.append({
                                    "area":    "EDICIÓN",
                                    "maquina": "—",
                                    "tipo":    "EDICIÓN",
                                    "inicio":  hora_colombia().isoformat(),
                                    "fin":     hora_colombia().isoformat(),
                                    "duracion":"0:00:00",
                                    "usuario": st.session_state.get('nombre_usuario','?'),
                                    "nota":    f"Editado: {nueva_obs_gral}"
                                })
                                supabase.table("ordenes_planeadas").update({
                                    "historial_procesos": hist
                                }).eq("op", op_edit['op']).execute()

                                st.success(f"✅ OP {op_edit['op']} actualizada correctamente.")
                                st.session_state.pop('op_editar_data', None)
                                time.sleep(1.2)
                                st.rerun()

                            except Exception as e:
                                st.error(f"Error al guardar: {e}")

    with tab_nueva:
    
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

# INTEBNTAR TRAER DAROS  DE LA  PARTE SI EXSITE REPEETICION 
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
        
        maq_sel = st.selectbox("Seleccione la Máquina", MAQUINAS["CORTE"])
        
        t1, t2 = st.tabs(["📝 Registro", "📋 Historial"])
        
        with t1:
            with st.form("f_seg_hor", clear_on_submit=True):
                ca, cb, cc = st.columns(3)
                with ca:
                    op_s = st.text_input("OP")
                    nt_s = st.text_input("Nombre Trabajo")
                    tipo_p = st.text_input("Tipo de Papel / Material")
                    turno_s = st.selectbox("Turno", ["Dia", "Mañana", "Tarde", "Noche"])
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
                                "peso_desperdicio": p_d,
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
                    
                    columnas_visibles = ["fecha", "hora_registro", "turno", "op", "nombre_trabajo", "num_cajas", "num_varillas", "peso_desperdicio", "observaciones"]
                    
# Renombrar las columnas para que se vea estetico en pantalla
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

#  CRONOGRAMA DE IMPRESIÓN ESTILO NOTION
elif menu == "📆 Cronograma Impresión":
    import streamlit.components.v1 as components
    import json

    st.markdown("<div class='title-area'>📆 CRONOGRAMA DE IMPRESIÓN</div>", unsafe_allow_html=True)
    st.caption("Arrastra las tarjetas al cronograma. Mueve o estira los bloques para ajustar. Todo se guarda solo.")

    lista_maquinas = ["ATF-22", "HR-22", "HAMILTON", "HR-17", "DIDDE 11", "MULTILYTH 1", "MULTILYTH 2"]

    qp = st.query_params
    if "crono_id" in qp:
        try:
            supabase.table("ordenes_planeadas").update({
                "fecha_inicio_cronograma": qp["crono_start"],
                "fecha_fin_cronograma":    qp["crono_end"],
                "maquina_cronograma":      qp["crono_maq"]
            }).eq("id", qp["crono_id"]).execute()
        except:
            pass
        st.query_params.clear()
        st.rerun()

    try:
        todas_las_ops = supabase.table("ordenes_planeadas").select("*").execute().data or []
    except:
        todas_las_ops = []

    # ALERTAS
    ahora_col = hora_colombia()
    alertas = []
    for op in todas_las_ops:
        if op.get("estado") == "Terminado" or op.get("proxima_area") == "FINALIZADO":
            continue
        fecha_fin_crono = op.get("fecha_fin_cronograma")
        if fecha_fin_crono:
            try:
                dt_fin_crono = datetime.fromisoformat(str(fecha_fin_crono).replace("Z","")).replace(tzinfo=pytz.utc).astimezone(pytz.timezone("America/Bogota"))
                if ahora_col > dt_fin_crono:
                    horas_retraso = int((ahora_col - dt_fin_crono).total_seconds() // 3600)
                    alertas.append(f"⏰ **OP {op.get('op')}** ({op.get('cliente','')}) — lleva **{horas_retraso}h de retraso**")
            except:
                pass
        fecha_creacion = op.get("fecha_creacion") or op.get("created_at")
        if fecha_creacion and not op.get("maquina_cronograma") and not op.get("excluir_cronograma"):
            try:
                dt_creacion = datetime.fromisoformat(str(fecha_creacion).replace("Z","")).replace(tzinfo=pytz.utc).astimezone(pytz.timezone("America/Bogota"))
                if (ahora_col - dt_creacion).days >= 3:
                    alertas.append(f"📋 **OP {op.get('op')}** — lleva **{(ahora_col - dt_creacion).days} dias sin asignar**")
            except:
                pass

    if alertas:
        with st.expander(f"🚨 {len(alertas)} ALERTA(S) — haz clic para ver", expanded=True):
            for a in alertas:
                st.warning(a)
    else:
        st.success("✅ Todo en orden")

    ops_agendadas  = [op for op in todas_las_ops if op.get("fecha_inicio_cronograma") and op.get("fecha_fin_cronograma") and op.get("maquina_cronograma")]
    ops_pendientes = [op for op in todas_las_ops if
                      not (op.get("fecha_inicio_cronograma") and op.get("maquina_cronograma"))
                      and op.get("proxima_area") != "FINALIZADO"
                      and op.get("estado") != "Terminado"
                      and not op.get("excluir_cronograma")]

    eventos_json = []
    for op in ops_agendadas:
        if op.get("proxima_area") == "FINALIZADO":
            color, etiqueta = "#4a4a4a", "FINALIZADA"
        elif op.get("estado") == "En Proceso":
            color, etiqueta = "#2563eb", "EN PROCESO"
        else:
            color, etiqueta = "#d97706", "PROGRAMADA"
        op_num    = str(op.get("op", "?")).replace('"', '').replace("'", "")
        cliente   = str(op.get("cliente", ""))[:14].replace('"', '').replace("'", "")
        titulo    = "OP " + op_num + " - " + cliente
        eventos_json.append({
            "id":              str(op["id"]),
            "resourceId":      op["maquina_cronograma"],
            "title":           titulo,
            "start":           str(op["fecha_inicio_cronograma"]),
            "end":             str(op["fecha_fin_cronograma"]),
            "backgroundColor": color,
            "borderColor":     color,
            "textColor":       "#ffffff",
            "extendedProps": {
                "cliente": cliente,
                "estado":  etiqueta,
                "db_id":   str(op["id"])
            }
        })

    pendientes_json = []
    for op in ops_pendientes:
        card_color = "#2563eb" if op.get("estado") == "En Proceso" else "#d97706"
        op_num   = str(op.get("op", "?")).replace('"', '').replace("'", "")
        cliente  = str(op.get("cliente", ""))[:14].replace('"', '').replace("'", "")
        titulo   = "OP " + op_num + " - " + cliente
        pendientes_json.append({
            "id":    str(op["id"]),
            "title": titulo,
            "color": card_color,
            "extendedProps": {"cliente": cliente, "db_id": str(op["id"])}
        })

    recursos_json  = [{"id": m, "title": m} for m in lista_maquinas]
    eventos_str    = json.dumps(eventos_json,   ensure_ascii=True)
    recursos_str   = json.dumps(recursos_json,  ensure_ascii=True)
    pendientes_str = json.dumps(pendientes_json, ensure_ascii=True)
    supa_url = str(URL)
    supa_key = str(KEY)

    html_cal = (
        "<!DOCTYPE html><html><head>"
        "<link href='https://cdn.jsdelivr.net/npm/fullcalendar-scheduler@6.1.11/index.global.min.css' rel='stylesheet'/>"
        "<script src='https://cdn.jsdelivr.net/npm/fullcalendar-scheduler@6.1.11/index.global.min.js'></script>"
        "<style>"
        "* { box-sizing: border-box; margin: 0; padding: 0; }"
        "body { background: #191919; color: #e0e0e0; font-family: Segoe UI, sans-serif; display: flex; gap: 10px; padding: 10px; }"
        "#calendar-wrap { flex: 1; min-width: 0; }"
        "#sidebar { width: 185px; flex-shrink: 0; background: #1f1f1f; border: 1px solid #2e2e2e; border-radius: 10px; padding: 10px; display: flex; flex-direction: column; gap: 6px; overflow-y: auto; max-height: 560px; }"
        "#sidebar h3 { color: #aaa; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }"
        ".tarjeta { background: #2a2a2a; border: 1px solid #3a3a3a; border-radius: 8px; padding: 8px 10px; font-size: 12px; cursor: grab; color: #e0e0e0; transition: background 0.15s; margin-bottom: 4px; }"
        ".tarjeta:hover { background: #333; }"
        ".op-num { font-weight: 700; font-size: 12px; }"
        ".cli { color: #aaa; font-size: 11px; margin-top: 2px; }"
        ".est { font-size: 10px; color: #666; margin-top: 2px; }"
        ".no-pending { color: #555; font-size: 12px; text-align: center; margin-top: 20px; }"
        ".fc .fc-toolbar { background: #191919; padding: 8px 0; border-bottom: 1px solid #2e2e2e; }"
        ".fc .fc-toolbar-title { color: #e0e0e0; font-size: 15px; font-weight: 600; }"
        ".fc .fc-button { background: #2e2e2e !important; border: 1px solid #3e3e3e !important; color: #ccc !important; border-radius: 6px !important; font-size: 12px !important; padding: 4px 10px !important; }"
        ".fc .fc-button:hover { background: #3a3a3a !important; }"
        ".fc .fc-button-active { background: #444 !important; }"
        ".fc .fc-col-header-cell { background: #1f1f1f; border-color: #2e2e2e; }"
        ".fc .fc-col-header-cell-cushion { color: #aaa; font-size: 11px; text-decoration: none; padding: 5px; }"
        ".fc-datagrid-cell { background: #1f1f1f !important; border-color: #2a2a2a !important; }"
        ".fc .fc-datagrid-cell-cushion { color: #ccc; font-size: 12px; font-weight: 600; }"
        ".fc-timeline-slot { border-color: #2a2a2a !important; }"
        ".fc-timeline-lane { border-color: #2a2a2a !important; background: #191919; }"
        ".fc-event { border-radius: 6px !important; border: none !important; padding: 3px 7px !important; font-size: 12px !important; cursor: grab !important; }"
        ".fc .fc-timeline-now-indicator-line { border-color: #ef4444; }"
        "#toast { display: none; position: fixed; bottom: 18px; left: 50%; transform: translateX(-50%); background: #22c55e; color: #fff; padding: 8px 20px; border-radius: 20px; font-size: 13px; font-weight: 600; z-index: 9999; }"
        "#btn-guardar { display: none; position: fixed; bottom: 18px; right: 18px; background: #2563eb; color: #fff; border: none; border-radius: 10px; padding: 10px 20px; font-size: 13px; font-weight: 700; cursor: pointer; z-index: 9999; }"
        "#popup-quitar { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 10000; align-items: center; justify-content: center; }"
        "#tooltip { display: none; position: fixed; background: #2a2a2a; border: 1px solid #444; color: #eee; padding: 10px 14px; border-radius: 8px; font-size: 12px; z-index: 9998; pointer-events: none; max-width: 220px; line-height: 1.7; }"
        "</style></head><body>"
        "<div id='calendar-wrap'><div id='calendar'></div></div>"
        "<div id='sidebar'><h3>Sin asignar</h3><div id='lista-pendientes'></div></div>"
        "<div id='toast'></div>"
        "<button id='btn-guardar' onclick='ejecutarGuardado()'>Guardar cambios</button>"
        "<div id='popup-quitar'><div style='background:#2a2a2a;border:1px solid #444;border-radius:12px;padding:24px;max-width:300px;text-align:center;color:#eee;'>"
        "<div style='font-size:22px;margin-bottom:8px;'>🗑</div>"
        "<div style='font-weight:700;margin-bottom:6px;'>Quitar del cronograma?</div>"
        "<div id='popup-titulo' style='color:#d97706;font-size:13px;margin-bottom:16px;'></div>"
        "<div style='display:flex;gap:10px;justify-content:center;'>"
        "<button id='btn-cancelar-quitar' style='background:#3a3a3a;color:#ccc;border:1px solid #555;border-radius:8px;padding:8px 18px;cursor:pointer;'>Cancelar</button>"
        "<button id='btn-confirmar-quitar' style='background:#ef4444;color:#fff;border:none;border-radius:8px;padding:8px 18px;cursor:pointer;font-weight:700;'>Si, quitar</button>"
        "</div></div></div>"
        "<div id='tooltip'></div>"
        "<script>"
        "var eventos    = " + eventos_str + ";"
        "var recursos   = " + recursos_str + ";"
        "var pendientes = " + pendientes_str + ";"
        "var SUPA_URL   = '" + supa_url + "';"
        "var SUPA_KEY   = '" + supa_key + "';"
        "var tooltip    = document.getElementById('tooltip');"
        "var toast      = document.getElementById('toast');"
        "var cambiosPendientes = {};"
        "function showToast(msg) { toast.textContent = msg; toast.style.display = 'block'; setTimeout(function(){ toast.style.display = 'none'; }, 2500); }"
        "function actualizarBotonGuardar() { var n = Object.keys(cambiosPendientes).length; var btn = document.getElementById('btn-guardar'); if(n>0){ btn.style.display='block'; btn.textContent='Guardar cambios ('+n+')'; } else { btn.style.display='none'; } }"
        "function guardarEnSupabase(db_id, start, end, maquina) { cambiosPendientes[db_id] = {start:start, end:end, maquina:maquina}; actualizarBotonGuardar(); }"
        "async function ejecutarGuardado() { var ids = Object.keys(cambiosPendientes); var btn = document.getElementById('btn-guardar'); btn.textContent = 'Guardando...'; btn.disabled = true; var errores = 0; for(var i=0;i<ids.length;i++){ var id=ids[i]; var cam=cambiosPendientes[id]; try { var resp = await fetch(SUPA_URL+'/rest/v1/ordenes_planeadas?id=eq.'+encodeURIComponent(id), { method:'PATCH', headers:{'Content-Type':'application/json','apikey':SUPA_KEY,'Authorization':'Bearer '+SUPA_KEY,'Prefer':'return=minimal'}, body:JSON.stringify({fecha_inicio_cronograma:cam.start,fecha_fin_cronograma:cam.end,maquina_cronograma:cam.maquina}) }); if(resp.ok){ delete cambiosPendientes[id]; } else { errores++; } } catch(e){ errores++; } } btn.disabled=false; if(errores===0){ showToast('Todo guardado!'); btn.style.display='none'; } else { showToast('Error en '+errores+' cambios'); actualizarBotonGuardar(); } }"
        "async function quitarDelCronograma(db_id, ev) { showToast('Quitando...'); try { var resp = await fetch(SUPA_URL+'/rest/v1/ordenes_planeadas?id=eq.'+encodeURIComponent(db_id), { method:'PATCH', headers:{'Content-Type':'application/json','apikey':SUPA_KEY,'Authorization':'Bearer '+SUPA_KEY,'Prefer':'return=minimal'}, body:JSON.stringify({fecha_inicio_cronograma:null,fecha_fin_cronograma:null,maquina_cronograma:null}) }); if(resp.ok){ ev.remove(); showToast('OP devuelta a pendientes'); } else { showToast('Error al quitar'); } } catch(e){ showToast('Error de conexion'); } }"
        "async function excluirOP(event, db_id) { event.stopPropagation(); var resp = await fetch(SUPA_URL+'/rest/v1/ordenes_planeadas?id=eq.'+encodeURIComponent(db_id), { method:'PATCH', headers:{'Content-Type':'application/json','apikey':SUPA_KEY,'Authorization':'Bearer '+SUPA_KEY,'Prefer':'return=minimal'}, body:JSON.stringify({excluir_cronograma:true}) }); if(resp.ok){ var t=event.target.closest('.tarjeta'); if(t) t.remove(); showToast('OP retirada de pendientes'); } }"
        "document.addEventListener('mousemove', function(e){ tooltip.style.left=(e.clientX+15)+'px'; tooltip.style.top=(e.clientY+10)+'px'; });"
        "document.addEventListener('DOMContentLoaded', function(){"
        "  var lista = document.getElementById('lista-pendientes');"
        "  if(pendientes.length === 0){ lista.innerHTML = '<div class=\"no-pending\">Todas programadas</div>'; }"
        "  else { pendientes.forEach(function(p){"
        "    var div = document.createElement('div');"
        "    div.className = 'tarjeta';"
        "    var cc = p.color || '#d97706';"
        "    div.style.borderLeft = '3px solid '+cc;"
        "    div.setAttribute('data-event', JSON.stringify({id:p.id,title:p.title,duration:'02:00',backgroundColor:cc,borderColor:cc,textColor:'#fff',extendedProps:p.extendedProps}));"
        "    div.innerHTML = '<div style=\"display:flex;justify-content:space-between;align-items:center;\"><div class=\"op-num\" style=\"color:'+cc+'\">'+p.title.split(' - ')[0]+'</div><button onclick=\"excluirOP(event,\\''+p.id+'\\')\" style=\"background:none;border:none;color:#555;cursor:pointer;font-size:13px;\">x</button></div><div class=\"cli\">'+p.extendedProps.cliente+'</div><div class=\"est\">'+(cc==='#2563eb'?'En proceso':'Sin iniciar')+'</div>';"
        "    lista.appendChild(div);"
        "  }); }"
        "  var calEl = document.getElementById('calendar');"
        "  var cal = new FullCalendar.Calendar(calEl, {"
        "    schedulerLicenseKey: 'CC-Attribution-NonCommercial-NoDerivatives',"
        "    initialView: 'resourceTimelineDay',"
        "    locale: 'es',"
        "    height: 540,"
        "    nowIndicator: true,"
        "    editable: true,"
        "    droppable: true,"
        "    eventResizableFromStart: true,"
        "    slotDuration: '01:00:00',"
        "    slotLabelFormat: {hour:'2-digit',minute:'2-digit',hour12:false},"
        "    scrollTime: '06:00:00',"
        "    resourceAreaWidth: '13%',"
        "    resourceAreaHeaderContent: 'Maquina',"
        "    headerToolbar: {left:'prev,next today',center:'title',right:'resourceTimelineDay,resourceTimelineWeek,resourceTimelineMonth'},"
        "    buttonText: {today:'Hoy',day:'Dia',week:'Semana',month:'Mes'},"
        "    views: {"
        "      resourceTimelineDay: {slotDuration:'01:00:00',slotLabelFormat:{hour:'2-digit',minute:'2-digit',hour12:false}},"
        "      resourceTimelineWeek: {slotDuration:{days:1},slotLabelFormat:{weekday:'long',day:'2-digit',month:'short'}},"
        "      resourceTimelineMonth: {slotDuration:{days:7},slotLabelFormat:{day:'2-digit',month:'short'}}"
        "    },"
        "    resources: recursos,"
        "    events: eventos,"
        "    drop: function(info){ info.draggedEl.parentNode.removeChild(info.draggedEl); },"
        "    eventReceive: function(info){"
        "      var ev=info.event; var db_id=ev.extendedProps.db_id; var maq=ev.getResources()[0]?ev.getResources()[0].id:'';"
        "      var start=ev.start?ev.start.toISOString():''; var end=ev.end?ev.end.toISOString():'';"
        "      if(!end){ var tmp=new Date(ev.start); tmp.setHours(tmp.getHours()+2); end=tmp.toISOString(); }"
        "      guardarEnSupabase(db_id,start,end,maq);"
        "    },"
        "    eventChange: function(info){"
        "      var ev=info.event; var db_id=ev.extendedProps.db_id||ev.id; var maq=ev.getResources()[0]?ev.getResources()[0].id:'';"
        "      var start=ev.start?ev.start.toISOString():''; var end=ev.end?ev.end.toISOString():'';"
        "      guardarEnSupabase(db_id,start,end,maq);"
        "    },"
        "    eventClick: function(info){"
        "      var ev=info.event; var db_id=ev.extendedProps.db_id||ev.id;"
        "      var popup=document.getElementById('popup-quitar');"
        "      document.getElementById('popup-titulo').textContent=ev.title;"
        "      popup.style.display='flex';"
        "      document.getElementById('btn-confirmar-quitar').onclick=function(){ popup.style.display='none'; quitarDelCronograma(db_id,ev); };"
        "      document.getElementById('btn-cancelar-quitar').onclick=function(){ popup.style.display='none'; };"
        "    },"
        "    eventMouseEnter: function(info){"
        "      var p=info.event.extendedProps;"
        "      var s=info.event.start?info.event.start.toLocaleString('es-CO',{hour:'2-digit',minute:'2-digit',day:'2-digit',month:'short'}):'';"
        "      var e=info.event.end?info.event.end.toLocaleString('es-CO',{hour:'2-digit',minute:'2-digit',day:'2-digit',month:'short'}):'';"
        "      tooltip.innerHTML='<b style=\"color:#fff\">'+info.event.title+'</b><br>Cliente: '+p.cliente+'<br>Estado: '+p.estado+'<br>Inicio: '+s+'<br>Fin: '+e;"
        "      tooltip.style.display='block';"
        "    },"
        "    eventMouseLeave: function(){ tooltip.style.display='none'; }"
        "  });"
        "  cal.render();"
        "  new FullCalendar.ThirdPartyDraggable(document.getElementById('lista-pendientes'),{"
        "    itemSelector: '.tarjeta',"
        "    eventData: function(el){ return JSON.parse(el.getAttribute('data-event')); }"
        "  });"
        "});"
        "</script></body></html>"
    )

    components.html(html_cal, height=620, scrolling=False)

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

# COLECTORAS
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
                    duracion = calcular_duracion_laboral(inicio, fin, r.get('maquina'), r.get('tiempo_pausa', 0))

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
                
# Captura de tiempos
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
            duracion = calcular_duracion_laboral(inicio, fin, r['maquina'], r.get('tiempo_pausa', 0))

# Preparar el nuevo historial — leer desde ordenes_planeadas, no desde trabajos_activos
            d_op_hist = supabase.table("ordenes_planeadas").select("historial_procesos").eq("op", r['op']).single().execute().data
            hist = d_op_hist.get('historial_procesos') or [] if d_op_hist else []
            
            datos_c['cantidad_parcial_entregada'] = cantidad_parcial
            if obs_parcial:
                datos_c['observacion_parcial'] = obs_parcial
                
# Recupera operario y auxiliar directamente del registro activo 'r'
            operario_actual = r.get('operario', 'Operario Planta')
            auxiliar_actual = r.get('auxiliar', '')
                
# Agrega al historial de forma segura
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

# OP avanza a siguiente area Y queda visible en area origen
                supabase.table("ordenes_planeadas").update({
                    "proxima_area": n_area_parcial,
                    "estado_parcial": f"ACTIVO EN {area_act}",
                    "historial_procesos": hist
                }).eq("op", r['op']).execute()

# Maquina queda LIBRE
                supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()

                st.success(f"✅ Parcial enviado a {n_area_parcial}. La máquina {r['maquina']} quedó libre y la OP sigue activa en {area_act}.")
                st.session_state.rep = None
                time.sleep(1.5)
                st.rerun()

            except Exception as e:
                st.error(f"Error al procesar la entrega parcial: {e}")

if st.session_state.get('rol') == 'admin':

# BLOQUE INTERRUPTORES DE MAQUINAS
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

#  BLOQUE ADMINISTRACION DE USUARIOS 
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

#  FUNCIONES DE MERCADO DE AVATARES C&B  
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


#  MÓDULO MERCADO PRINCIPAL 
if menu == "🛒 Mercado":
    usuario_actual = st.session_state.get('usuario_actual', '')
    nombre_actual  = st.session_state.get('nombre_usuario', '')
    rol_actual     = st.session_state.get('rol', '')

    st.markdown("<div class='title-area'>🪙 SISTEMA DE COINS — C&B PAPELES</div>", unsafe_allow_html=True)

    coins_usuario = mercado_obtener_coins(usuario_actual)

#  BARRA DE COINS 
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

# TABS PRINCIPALES
    if rol_actual == 'admin':
        tab_admin, tab_historial = st.tabs(
            ["⚙️ Panel Admin", "📜 Historial Monedas"]
        )
    else:
        tab_historial, = st.tabs(
            ["📜 Mi Historial"]
        )

# TAB  PANEL ADMIN
    if rol_actual == 'admin':
        with tab_admin:
            st.markdown("<div class='section-header'>⚙️ ADMINISTRACIÓN DEL MERCADO</div>", unsafe_allow_html=True)

# Asignar / quitar coins 
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

#  Ver monederos de todos
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

# TAB  HISTORIAL (ADMIN ve todo, usuario ve lo suyo)
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
