import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA PLANTA", page_icon="🏭")

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def guardar_datos(df_nuevo, hoja):
    try:
        # 1. Intentar leer datos actuales
        try:
            df_actual = conn.read(worksheet=hoja, ttl=0)
        except:
            df_actual = pd.DataFrame()

        # 2. Combinar y limpiar (Evita errores de celdas vacías o formatos locos)
        df_final = pd.concat([df_actual, df_nuevo], ignore_index=True)
        # Convertimos todo a String y quitamos los 'nan' que rompen Google Sheets
        df_final = df_final.astype(str).replace('nan', '')

        # 3. Actualizar
        conn.update(worksheet=hoja, data=df_final)
        
        st.success(f"✅ Datos guardados correctamente en la pestaña: {hoja}")
        st.balloons()
    except Exception as e:
        st.error(f"Error técnico al guardar: {e}")
        st.info("Verifica que el Excel tenga permisos de 'Editor' para cualquier persona con el enlace.")

# --- LISTAS DE MÁQUINAS (Ajustadas a tu planta) ---
MAQ_IMP = ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"]
MAQ_COR = ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"]
MAQ_COL = ["COL-01", "COL-02"]

# --- LOGIN SIMPLE ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🏭 ACCESO SISTEMA PLANTA")
    col1, col2 = st.columns(2)
    with col1: u = st.text_input("Usuario")
    with col2: p = st.text_input("Password", type="password")
    if st.button("ENTRAR", use_container_width=True):
        st.session_state.auth = True
        st.rerun()
    st.stop()

# --- MENÚ Y NAVEGACIÓN ---
menu = st.sidebar.radio("ÁREAS DE TRABAJO", ["🖨️ IMPRESIÓN", "✂️ CORTE", "📥 COLECTORAS", "📕 ENCUADERNACIÓN", "⏱️ AVANCE (GAP)", "📊 HISTORIAL"])

def selector_tactil(lista, clave):
    st.write("### Seleccione Máquina:")
    cols = st.columns(4)
    for i, m in enumerate(lista):
        if cols[i % 4].button(m, key=f"{clave}_{m}", use_container_width=True):
            st.session_state[clave] = m
    return st.session_state.get(clave)

# --- FORMULARIOS ---

if menu == "🖨️ IMPRESIÓN":
    st.header("Módulo de Impresión")
    m = selector_tactil(MAQ_IMP, "m_imp")
    if m:
        with st.form("f_imp"):
            st.subheader(f"Prensa Seleccionada: {m}")
            c1, c2, c3 = st.columns(3)
            op = c1.text_input("OP")
            tr = c2.text_input("Trabajo")
            pa = c3.text_input("Marca Papel")
            an = c1.text_input("Ancho Bobina")
            gr = c2.text_input("Gramaje")
            ti = c3.number_input("Tintas", 0)
            me = c1.text_input("Medida Rollo")
            im = c2.number_input("Imágenes", 0)
            met = c3.number_input("Metros Totales", 0)
            hi = c1.text_input("Hora Inicio")
            hf = c2.text_input("Hora Fin")
            des = c3.number_input("Desp. Kg", 0.0)
            mot = st.text_input("Motivo Desperdicio")
            obs = st.text_area("Observaciones")
            if st.form_submit_button("GUARDAR EN EXCEL", use_container_width=True):
                nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Máquina":m, "Trabajo":tr, "Papel":pa, "Ancho":an, "Gramaje":gr, "Tintas":ti, "Medida":me, "Imágenes":im, "Metros":met, "H_Inicio":hi, "H_Fin":hf, "Desp_Kg":des, "Motivo":mot, "Obs":obs}])
                guardar_datos(nuevo, "Impresion")

elif menu == "✂️ CORTE":
    st.header("Módulo de Corte")
    m = selector_tactil(MAQ_COR, "m_cor")
    if m:
        with st.form("f_cor"):
            st.subheader(f"Cortadora Seleccionada: {m}")
            c1, c2, c3 = st.columns(3)
            op = c1.text_input("OP")
            tr = c2.text_input("Trabajo")
            iv = c3.number_input("Img x Varilla", 0)
            me = c1.text_input("Medida Final")
            tv = c2.number_input("Total Varillas", 0)
            rc = c3.number_input("Rollos Cortados", 0)
            uc = c1.number_input("Unid/Caja", 0)
            hi = c2.text_input("Hora Inicio")
            hf = c3.text_input("Hora Fin")
            des = c1.number_input("Desp. Kg", 0.0)
            mot = st.text_input("Motivo Desperdicio")
            if st.form_submit_button("GUARDAR CORTE", use_container_width=True):
                nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Máquina":m, "Trabajo":tr, "Img_Varilla":iv, "Medida":me, "Total_Varillas":tv, "Rollos_Cortados":rc, "Unid_Caja":uc, "H_Inicio":hi, "H_Fin":hf, "Desp_Kg":des, "Motivo":mot}])
                guardar_datos(nuevo, "Corte")

elif menu == "⏱️ AVANCE (GAP)":
    st.header("Registro de Avance por Hora")
    m = selector_tactil(MAQ_COR, "m_gap")
    if m:
        with st.form("f_gap"):
            c1, c2 = st.columns(2)
            op_h = c1.text_input("OP Actual")
            vh = c2.number_input("Varillas producidas esta hora", 0)
            if st.form_submit_button("REGISTRAR HORA"):
                nuevo = pd.DataFrame([{"Fecha":datetime.now().strftime("%d/%m/%Y"), "Hora":datetime.now().strftime("%H:%M"), "Máquina":m, "OP":op_h, "Varillas_Hora":vh}])
                guardar_datos(nuevo, "Seguimiento_Avance")

elif menu == "📊 HISTORIAL":
    st.header("Consulta de Datos en Tiempo Real")
    t = st.selectbox("Seleccione Tabla:", ["Impresion", "Corte", "Colectoras", "Encuadernacion", "Seguimiento_Avance"])
    try:
        df = conn.read(worksheet=t, ttl=0)
        st.dataframe(df, use_container_width=True)
        # Botón para forzar actualización
        if st.button("Actualizar Vista"):
            st.cache_data.clear()
            st.rerun()
    except Exception as e:
        st.error(f"No se pudo cargar la tabla. Asegúrate de que la pestaña '{t}' tenga datos.")
