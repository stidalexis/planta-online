import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA PLANTA", page_icon="🏭")

# --- 2. ESTRUCTURA COMPLETA DE TABLAS ---
ESTRUCTURA = {
    "Impresion": ["OP", "Fecha", "Máquina", "Trabajo", "Papel", "Ancho", "Gramaje", "Tintas", "Metros", "Desperdicio_Kg", "Motivo", "Observaciones"],
    "Corte": ["OP", "Fecha", "Máquina", "Trabajo", "Papel", "Ancho", "Gramaje", "Img_Varilla", "Total_Varillas", "Rollos_Cortados", "Desperdicio_Kg", "Motivo", "Observaciones"],
    "Colectoras": ["OP", "Fecha", "Máquina", "Trabajo", "Medida_Forma", "Unid_Caja", "Total_Cajas", "Total_Formas", "Desperdicio_Kg", "Motivo"],
    "Encuadernacion": ["OP", "Fecha", "Trabajo", "Cant_Formas", "Material", "Medida", "Unid_Caja", "Cant_Final", "Desperdicio_Kg", "Motivo"],
    "Seguimiento_Avance": ["Fecha", "Hora", "Máquina", "OP", "Varillas_Hora", "Cajas_Hora"],
    "Metas_Config": ["Maquina", "Meta"]
}

# --- 3. CONEXIÓN CON LIMPIEZA DE LLAVE (SOLUCIÓN AL ERROR PEM) ---
def conectar_nube():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # LIMPIEZA EXTREMA DE LA LLAVE
        raw_key = st.secrets["connections"]["gsheets"]["private_key"]
        # Eliminamos espacios accidentales y arreglamos los saltos de línea
        clean_key = raw_key.strip().replace("\\n", "\n")
        
        creds_dict = {
            "type": "service_account",
            "project_id": st.secrets["connections"]["gsheets"]["project_id"],
            "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
            "private_key": clean_key,
            "client_email": st.secrets["connections"]["gsheets"]["client_email"],
            "client_id": st.secrets["connections"]["gsheets"]["client_id"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.google.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"],
        }
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        gc = gspread.authorize(creds)
        return gc.open_by_url(st.secrets["connections"]["gsheets"]["spreadsheet"])
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def obtener_o_crear_tabla(nombre_tabla):
    sh = conectar_nube()
    if not sh: return pd.DataFrame()
    try:
        ws = sh.worksheet(nombre_tabla)
        return get_as_dataframe(ws).dropna(how='all').dropna(axis=1, how='all')
    except:
        # Si la hoja no existe, se crea automáticamente con sus columnas
        cols = ESTRUCTURA[nombre_tabla]
        sh.add_worksheet(title=nombre_tabla, rows="1000", cols=str(len(cols)))
        ws = sh.worksheet(nombre_tabla)
        df_ini = pd.DataFrame(columns=cols)
        set_with_dataframe(ws, df_ini)
        st.info(f"Hoja '{nombre_tabla}' creada en el Excel.")
        return df_ini

def guardar_datos(df_nuevo, nombre_tabla):
    sh = conectar_nube()
    if sh:
        ws = sh.worksheet(nombre_tabla)
        df_actual = get_as_dataframe(ws).dropna(how='all').dropna(axis=1, how='all')
        df_final = pd.concat([df_actual, df_nuevo], ignore_index=True)
        set_with_dataframe(ws, df_final)
        st.success("✅ Datos sincronizados correctamente.")

# --- 4. LOGIN ---
USUARIOS = {
    "alexander": "admin123",
    "leonel": "0321",
    "giovanny": "1503"
}

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🏭 SISTEMA DE CONTROL DE PLANTA")
    u = st.text_input("Usuario")
    p = st.text_input("Password", type="password")
    if st.button("Entrar"):
        if u in USUARIOS and USUARIOS[u] == p:
            st.session_state.auth = True
            st.session_state.user = u
            st.rerun()
    st.stop()

# --- 5. INTERFAZ Y FORMULARIOS COMPLETOS ---
menu = st.sidebar.radio("Ir a:", ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación", "⏱️ Seguimiento Cortadoras", "📊 Historial"])

if menu == "🖨️ Impresión":
    st.header("Formulario de Impresión")
    with st.form("f_imp"):
        c1, c2, c3 = st.columns(3)
        op = c1.text_input("OP")
        maq = c2.selectbox("Máquina", ["HR-22", "ATF-22", "HR-17", "DID-11"])
        tr = c3.text_input("Trabajo")
        pa = c1.text_input("Papel")
        an = c2.text_input("Ancho")
        gr = c3.text_input("Gramaje")
        tin = c1.number_input("Tintas", 0)
        met = c2.number_input("Metros", 0)
        des = c3.number_input("Desperdicio Kg", 0.0)
        mot = st.text_input("Motivo Desperdicio")
        obs = st.text_area("Observaciones")
        if st.form_submit_button("Guardar"):
            nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Máquina":maq, "Trabajo":tr, "Papel":pa, "Ancho":an, "Gramaje":gr, "Tintas":tin, "Metros":met, "Desperdicio_Kg":des, "Motivo":mot, "Observaciones":obs}])
            guardar_datos(nuevo, "Impresion")

elif menu == "✂️ Corte":
    st.header("Formulario de Corte")
    with st.form("f_corte"):
        c1, c2, c3 = st.columns(3)
        op = c1.text_input("OP")
        maq = c2.selectbox("Máquina", ["COR-01", "COR-02", "COR-03"])
        tr = c3.text_input("Trabajo")
        pa = c1.text_input("Papel")
        iv = c2.number_input("Img x Varilla", 0)
        tv = c3.number_input("Total Varillas", 0)
        rc = c1.number_input("Rollos Cortados", 0)
        des = c2.number_input("Desperdicio Kg", 0.0)
        if st.form_submit_button("Guardar"):
            nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Máquina":maq, "Trabajo":tr, "Papel":pa, "Img_Varilla":iv, "Total_Varillas":tv, "Rollos_Cortados":rc, "Desperdicio_Kg":des}])
            guardar_datos(nuevo, "Corte")

elif menu == "⏱️ Seguimiento Cortadoras":
    st.header("Avance por Hora")
    maq = st.selectbox("Máquina", ["COR-01", "COR-02", "COR-03"])
    with st.form("f_av"):
        c1, c2 = st.columns(2)
        op_h = c1.text_input("OP")
        v_h = c2.number_input("Varillas ahora", 0)
        if st.form_submit_button("Registrar Avance"):
            nuevo = pd.DataFrame([{"Fecha":datetime.now().strftime("%d/%m/%Y"), "Hora":datetime.now().strftime("%H:%M"), "Máquina":maq, "OP":op_h, "Varillas_Hora":v_h}])
            guardar_datos(nuevo, "Seguimiento_Avance")

elif menu == "📊 Historial":
    st.header("Consulta de Registros")
    tab = st.selectbox("Ver tabla:", list(ESTRUCTURA.keys()))
    df = obtener_o_crear_tabla(tab)
    st.dataframe(df, use_container_width=True)
