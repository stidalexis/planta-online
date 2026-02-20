import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA PLANTA TÁCTIL", page_icon="🏭")

# --- CONEXIÓN DIRECTA (SIN LLAVES JSON) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(hoja):
    try:
        return conn.read(worksheet=hoja, ttl=0)
    except:
        return pd.DataFrame()

def guardar_datos(df_nuevo, hoja):
    df_actual = cargar_datos(hoja)
    df_final = pd.concat([df_actual, df_nuevo], ignore_index=True)
    conn.update(worksheet=hoja, data=df_final)
    st.success(f"✅ Sincronizado en {hoja}")

# --- INTERFAZ TÁCTIL ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🏭 ACCESO")
    u, p = st.text_input("Usuario"), st.text_input("Password", type="password")
    if st.button("ENTRAR", use_container_width=True):
        st.session_state.auth = True
        st.rerun()
    st.stop()

menu = st.sidebar.radio("ÁREA", ["🖨️ IMPRESIÓN", "✂️ CORTE", "📥 COLECTORAS", "📕 ENCUADERNACIÓN", "📊 HISTORIAL"])

# Función para selector táctil
def selector_maquina(lista):
    st.write("**SELECCIONE MÁQUINA:**")
    cols = st.columns(len(lista))
    for i, m in enumerate(lista):
        if cols[i].button(m, key=m, use_container_width=True):
            st.session_state.maquina_sel = m
    return st.session_state.get("maquina_sel")

# --- MÓDULOS ---
if menu == "🖨️ IMPRESIÓN":
    st.header("Formulario de Impresión")
    maq = selector_maquina(["HR-22", "ATF-22", "HR-17", "DID-11"])
    if maq:
        with st.form("f_imp"):
            c1, c2, c3 = st.columns(3)
            op, tr, pa = c1.text_input("OP"), c2.text_input("Trabajo"), c3.text_input("Papel")
            an, gr, ti = c1.text_input("Ancho"), c2.text_input("Gramaje"), c3.number_input("Tintas", 0)
            me, img, met = c1.text_input("Medida Rollo"), c2.number_input("Imágenes", 0), c3.number_input("Metros", 0)
            if st.form_submit_button("GUARDAR REGISTRO", use_container_width=True):
                nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Máquina":maq, "Trabajo":tr, "Papel":pa, "Ancho":an, "Gramaje":gr, "Tintas":ti, "Medida_Rollo":me, "Imágenes":img, "Metros":met}])
                guardar_datos(nuevo, "Impresion")

elif menu == "✂️ CORTE":
    st.header("Formulario de Corte")
    maq = selector_maquina(["COR-01", "COR-02", "COR-03", "COR-04"])
    if maq:
        with st.form("f_corte"):
            c1, c2, c3 = st.columns(3)
            op, tr, iv = c1.text_input("OP"), c2.text_input("Trabajo"), c3.number_input("Img x Varilla", 0)
            me, tv, rc = c1.text_input("Medida"), c2.number_input("Total Varillas", 0), c3.number_input("Rollos Cortados", 0)
            if st.form_submit_button("GUARDAR CORTE", use_container_width=True):
                nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Máquina":maq, "Trabajo":tr, "Img_Varilla":iv, "Medida":me, "Total_Varillas":tv, "Rollos_Cortados":rc}])
                guardar_datos(nuevo, "Corte")

elif menu == "📥 COLECTORAS":
    st.header("Formulario de Colectoras")
    maq = selector_maquina(["COL-01", "COL-02"])
    if maq:
        with st.form("f_col"):
            op, tr = st.columns(2)[0].text_input("OP"), st.columns(2)[1].text_input("Trabajo")
            uc, tc = st.columns(2)[0].number_input("Unid/Caja", 0), st.columns(2)[1].number_input("Total Cajas", 0)
            if st.form_submit_button("GUARDAR COLECTORAS"):
                nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Máquina":maq, "Trabajo":tr, "Unid_Caja":uc, "Total_Cajas":tc}])
                guardar_datos(nuevo, "Colectoras")

elif menu == "📊 HISTORIAL":
    st.header("Historial")
    tab = st.selectbox("Hoja:", ["Impresion", "Corte", "Colectoras"])
    df = cargar_datos(tab)
    st.dataframe(df, use_container_width=True)
