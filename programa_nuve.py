import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA PLANTA TÁCTIL", page_icon="🏭")

# --- 2. ESTRUCTURA COMPLETA (TODAS LAS CASILLAS) ---
ESTRUCTURA = {
    "Impresion": ["OP", "Fecha", "Máquina", "Trabajo", "Papel", "Ancho", "Gramaje", "Tintas", "Medida_Rollo", "Imágenes", "H_Inicio", "H_Fin", "Metros", "Rollos", "Tinta_Kg", "Desp_Kg", "Motivo", "Observaciones"],
    "Corte": ["OP", "Fecha", "Máquina", "Trabajo", "Papel", "Ancho", "Gramaje", "Img_Varilla", "Medida", "Total_Varillas", "Unid_Caja", "Rollos_Cortados", "Desp_Kg", "Motivo", "Observaciones", "H_Inicio", "H_Fin"],
    "Colectoras": ["OP", "Fecha", "Máquina", "Trabajo", "Papel", "Medida_Forma", "Unid_Caja", "H_Inicio", "H_Fin", "Total_Cajas", "Total_Formas", "Desp_Kg", "Motivo", "Observaciones"],
    "Encuadernacion": ["OP", "Fecha", "Trabajo", "Cant_Formas", "Material", "Medida", "H_Inicio", "H_Fin", "Unid_Caja", "Cant_Final", "Presentacion", "Desp_Kg", "Motivo", "Observaciones"],
    "Seguimiento_Avance": ["Fecha", "Hora", "Máquina", "OP", "Varillas_Hora", "Cajas_Hora"],
    "Metas_Config": ["Maquina", "Meta"]
}

# --- 3. CONEXIÓN (SOLUCIÓN ERROR PEM) ---
def conectar_nube():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        pk = st.secrets["connections"]["gsheets"]["private_key"]
        # Limpieza profunda de caracteres de control
        clean_key = pk.replace('\\n', '\n').strip()
        
        creds_dict = {
            "type": "service_account",
            "project_id": st.secrets["connections"]["gsheets"]["project_id"],
            "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
            "private_key": clean_key,
            "client_email": st.secrets["connections"]["gsheets"]["client_email"],
            "client_id": st.secrets["connections"]["gsheets"]["client_id"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.google.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/v1/certs",
            "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"],
        }
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        gc = gspread.authorize(creds)
        return gc.open_by_url(st.secrets["connections"]["gsheets"]["spreadsheet"])
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def obtener_datos(tabla):
    sh = conectar_nube()
    if not sh: return pd.DataFrame()
    try:
        ws = sh.worksheet(tabla)
        return get_as_dataframe(ws).dropna(how='all').dropna(axis=1, how='all')
    except:
        cols = ESTRUCTURA[tabla]
        sh.add_worksheet(title=tabla, rows="1000", cols=str(len(cols)))
        return pd.DataFrame(columns=cols)

def guardar_datos(df_nuevo, tabla):
    sh = conectar_nube()
    if sh:
        ws = sh.worksheet(tabla)
        df_actual = get_as_dataframe(ws).dropna(how='all').dropna(axis=1, how='all')
        df_final = pd.concat([df_actual, df_nuevo], ignore_index=True)
        set_with_dataframe(ws, df_final)
        st.success("✅ Datos sincronizados.")

# --- 4. INTERFAZ TÁCTIL (MÁQUINAS A LA VISTA) ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🏭 ACCESO")
    u, p = st.text_input("Usuario"), st.text_input("Password", type="password")
    if st.button("ENTRAR", use_container_width=True):
        st.session_state.auth = True
        st.rerun()
    st.stop()

menu = st.sidebar.radio("ÁREA", ["🖨️ IMPRESIÓN", "✂️ CORTE", "📥 COLECTORAS", "📕 ENCUADERNACIÓN", "📊 HISTORIAL"])

# Función para selector táctil de máquinas
def selector_maquina(lista):
    st.write("**SELECCIONE MÁQUINA:**")
    cols = st.columns(len(lista))
    for i, m in enumerate(lista):
        if cols[i].button(m, use_container_width=True):
            st.session_state.maquina_sel = m
    if "maquina_sel" in st.session_state:
        st.info(f"Seleccionada: **{st.session_state.maquina_sel}**")
        return st.session_state.maquina_sel
    return None

# --- MÓDULOS ---
if menu == "🖨️ IMPRESIÓN":
    st.header("Formulario de Impresión")
    maq = selector_maquina(["HR-22", "ATF-22", "HR-17", "DID-11"])
    if maq:
        with st.form("f_imp"):
            c1, c2, c3 = st.columns(3)
            op = c1.text_input("OP")
            tr = c2.text_input("Trabajo")
            pa = c3.text_input("Papel")
            an = c1.text_input("Ancho")
            gr = c2.text_input("Gramaje")
            ti = c3.number_input("Tintas", 0)
            me = c1.text_input("Medida Rollo")
            img = c2.number_input("Imágenes", 0)
            met = c3.number_input("Metros", 0)
            hi = c1.text_input("Hora Inicio")
            hf = c2.text_input("Hora Fin")
            des = c3.number_input("Desp. Kg", 0.0)
            if st.form_submit_button("GUARDAR REGISTRO", use_container_width=True):
                nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Máquina":maq, "Trabajo":tr, "Papel":pa, "Ancho":an, "Gramaje":gr, "Tintas":ti, "Medida_Rollo":me, "Imágenes":img, "Metros":met, "H_Inicio":hi, "H_Fin":hf, "Desp_Kg":des}])
                guardar_datos(nuevo, "Impresion")

elif menu == "✂️ CORTE":
    st.header("Formulario de Corte")
    maq = selector_maquina(["COR-01", "COR-02", "COR-03", "COR-04"])
    if maq:
        with st.form("f_corte"):
            c1, c2, c3 = st.columns(3)
            op = c1.text_input("OP")
            tr = c2.text_input("Trabajo")
            iv = c3.number_input("Img x Varilla", 0)
            me = c1.text_input("Medida")
            tv = c2.number_input("Total Varillas", 0)
            rc = c3.number_input("Rollos Cortados", 0)
            des = c1.number_input("Desp. Kg", 0.0)
            if st.form_submit_button("GUARDAR CORTE", use_container_width=True):
                nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Máquina":maq, "Trabajo":tr, "Img_Varilla":iv, "Medida":me, "Total_Varillas":tv, "Rollos_Cortados":rc, "Desp_Kg":des}])
                guardar_datos(nuevo, "Corte")

elif menu == "📥 COLECTORAS":
    st.header("Formulario de Colectoras")
    maq = selector_maquina(["COL-01", "COL-02"])
    if maq:
        with st.form("f_col"):
            c1, c2 = st.columns(2)
            op = c1.text_input("OP")
            tr = c2.text_input("Trabajo")
            mf = c1.text_input("Medida Forma")
            uc = c2.number_input("Unid/Caja", 0)
            tc = c1.number_input("Total Cajas", 0)
            tf = c2.number_input("Total Formas", 0)
            if st.form_submit_button("GUARDAR COLECTORAS"):
                nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Máquina":maq, "Trabajo":tr, "Medida_Forma":mf, "Unid_Caja":uc, "Total_Cajas":tc, "Total_Formas":tf}])
                guardar_datos(nuevo, "Colectoras")

elif menu == "📕 ENCUADERNACIÓN":
    st.header("Formulario de Encuadernación")
    with st.form("f_enc"):
        c1, c2 = st.columns(2)
        op = c1.text_input("OP")
        tr = c2.text_input("Trabajo")
        cf = c1.number_input("Cant. Formas", 0)
        tm = c2.text_input("Material")
        me = c1.text_input("Medida")
        fi = c2.number_input("Cant. Final", 0)
        if st.form_submit_button("GUARDAR ENCUADERNACIÓN"):
            nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Trabajo":tr, "Cant_Formas":cf, "Tipo_Material":tm, "Medida":me, "Cant_Final":fi}])
            guardar_datos(nuevo, "Encuadernacion")

elif menu == "📊 HISTORIAL":
    st.header("Historial de Producción")
    tab = st.selectbox("Ver tabla:", list(ESTRUCTURA.keys()))
    if st.button("RECARGAR DATOS"): st.cache_data.clear()
    df = obtener_datos(tab)
    st.dataframe(df, use_container_width=True)
