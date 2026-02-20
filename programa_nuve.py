import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA PLANTA", page_icon="🏭")

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def guardar_datos(df_nuevo, hoja):
    try:
        # Intentamos leer la hoja para ver si tiene datos
        try:
            df_actual = conn.read(worksheet=hoja, ttl=0)
        except:
            df_actual = pd.DataFrame() # Si falla, asumimos que está vacía

        df_final = pd.concat([df_actual, df_nuevo], ignore_index=True).fillna("")
        conn.update(worksheet=hoja, data=df_final)
        st.success(f"✅ Sincronizado en {hoja}")
        st.balloons()
    except Exception as e:
        st.error(f"Error al guardar: Asegúrate de que el Excel sea 'Editor' para cualquier persona con el enlace.")

# --- LISTAS DE MÁQUINAS ---
MAQ_IMP = ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"]
MAQ_COR = ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"]
MAQ_COL = ["COL-01", "COL-02"]

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🏭 ACCESO")
    u, p = st.text_input("Usuario"), st.text_input("Password", type="password")
    if st.button("ENTRAR"):
        st.session_state.auth = True
        st.rerun()
    st.stop()

menu = st.sidebar.radio("MENÚ", ["🖨️ IMPRESIÓN", "✂️ CORTE", "📥 COLECTORAS", "📕 ENCUADERNACIÓN", "⏱️ AVANCE (GAP)", "📊 HISTORIAL"])

def selector_tactil(lista, clave):
    st.write("### Seleccione Máquina:")
    cols = st.columns(4)
    for i, m in enumerate(lista):
        if cols[i % 4].button(m, key=f"{clave}_{m}", use_container_width=True):
            st.session_state[clave] = m
    return st.session_state.get(clave)

# --- FORMULARIOS (Mismos campos completos que el anterior) ---
if menu == "🖨️ IMPRESIÓN":
    st.header("Módulo de Impresión")
    m = selector_tactil(MAQ_IMP, "m_imp")
    if m:
        with st.form("f_imp"):
            st.subheader(f"Prensa: {m}")
            c1, c2, c3 = st.columns(3)
            op, tr = c1.text_input("OP"), c2.text_input("Nombre Trabajo")
            pa, an = c3.text_input("Marca Papel"), c1.text_input("Ancho Bobina")
            gr, ti = c2.text_input("Gramaje"), c3.number_input("Cant. Tintas", 0)
            me_r, img = c1.text_input("Medida Rollo"), c2.number_input("Cant. Imágenes", 0)
            hi, hf = c3.text_input("Hora Inicio"), c1.text_input("Hora Final")
            met, roll = c2.number_input("Total Metros", 0), c3.number_input("Rollos", 0)
            p_t, des = c1.number_input("Peso Tinta", 0.0), c2.number_input("Peso Desperdicio", 0.0)
            mot = st.text_input("Motivo Desperdicio")
            obs = st.text_area("Observaciones")
            if st.form_submit_button("GUARDAR REGISTRO"):
                nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Máquina":m, "Trabajo":tr, "Papel":pa, "Ancho":an, "Gramaje":gr, "Tintas":ti, "Medida":me_r, "Imágenes":img, "H_Inicio":hi, "H_Fin":hf, "Metros":met, "Rollos":roll, "Peso_Tinta":p_t, "Desp_Kg":des, "Motivo":mot, "Obs":obs}])
                guardar_datos(nuevo, "Impresion")

# ... (Misma lógica para CORTE, COLECTORAS y ENCUADERNACIÓN) ...

elif menu == "📊 HISTORIAL":
    st.header("Consulta de Datos")
    t = st.selectbox("Seleccione Tabla:", ["Impresion", "Corte", "Colectoras", "Encuadernacion", "Seguimiento_Avance"])
    
    # IMPORTANTE: ttl=0 evita que Streamlit use datos viejos
    try:
        df = conn.read(worksheet=t, ttl=0)
        if df is not None:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("La hoja está conectada pero no tiene registros.")
    except Exception as e:
        st.error(f"No se pudo leer la pestaña '{t}'.")
        st.info("💡 Revisa que en el Excel la pestaña se llame exactamente así (sin tildes).")
