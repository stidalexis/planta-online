import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA PLANTA INTEGRAL", page_icon="🏭")

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def guardar_datos(df_nuevo, hoja):
    try:
        df_actual = conn.read(worksheet=hoja, ttl=0)
        df_final = pd.concat([df_actual, df_nuevo], ignore_index=True).fillna("")
        conn.update(worksheet=hoja, data=df_final)
        st.success(f"✅ Sincronizado en {hoja}")
        st.balloons()
    except Exception as e:
        st.error(f"Error: Verifica que la pestaña '{hoja}' exista en el Excel y que seas 'Editor'.")

# --- LISTADOS DE MÁQUINAS ---
MAQ_IMP = ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"]
MAQ_COR = ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"]
MAQ_COL = ["COL-01", "COL-02"]

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🏭 ACCESO")
    u, p = st.text_input("Usuario"), st.text_input("Password", type="password")
    if st.button("ENTRAR", use_container_width=True):
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

# --- FORMULARIOS ---

if menu == "🖨️ IMPRESIÓN":
    st.header("Módulo de Impresión")
    m = selector_tactil(MAQ_IMP, "m_imp")
    if m:
        with st.form("f_imp"):
            st.subheader(f"Prensa: {m}")
            c1, c2, c3 = st.columns(3)
            op, fecha_f = c1.text_input("OP"), c2.text_input("Fecha Fin (DD/MM/YY)")
            tr, pa = c3.text_input("Nombre Trabajo"), c1.text_input("Marca Papel")
            an, gr = c2.text_input("Ancho Bobina"), c3.text_input("Gramaje")
            ti, me_r = c1.number_input("Cant. Tintas", 0), c2.text_input("Medida Rollo")
            img, hi = c3.number_input("Cant. Imágenes", 0), c1.text_input("Hora Inicio")
            hf, met = c2.text_input("Hora Final"), c3.number_input("Total Metros", 0)
            roll, p_t = c1.number_input("Rollos a Sacar", 0), c2.number_input("Peso Tinta", 0.0)
            des, mot = c3.number_input("Peso Desperdicio", 0.0), st.text_input("Motivo Desperdicio")
            obs = st.text_area("Observaciones")
            if st.form_submit_button("GUARDAR REGISTRO"):
                nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Máquina":m, "Trabajo":tr, "Papel":pa, "Ancho":an, "Gramaje":gr, "Tintas":ti, "Medida":me_r, "Imágenes":img, "H_Inicio":hi, "H_Fin":hf, "Metros":met, "Rollos":roll, "Peso_Tinta":p_t, "Desp_Kg":des, "Motivo":mot, "Obs":obs}])
                guardar_datos(nuevo, "Impresion")

elif menu == "✂️ CORTE":
    st.header("Módulo de Corte")
    m = selector_tactil(MAQ_COR, "m_cor")
    if m:
        with st.form("f_cor"):
            st.subheader(f"Cortadora: {m}")
            c1, c2, c3 = st.columns(3)
            op, fecha_f = c1.text_input("OP"), c2.text_input("Fecha Fin")
            tr, pa = c3.text_input("Nombre Trabajo"), c1.text_input("Marca Papel")
            an, gr = c2.text_input("Ancho Bobina"), c3.text_input("Gramaje")
            iv, me = c1.number_input("Imágenes x Varilla", 0), c2.text_input("Medida Rollo")
            tv, uc = c3.number_input("Total Varillas", 0), c1.number_input("Unid. por Caja", 0)
            rc, des = c2.number_input("Total Rollos Cortados", 0), c3.number_input("Peso Desperdicio", 0.0)
            mot, hi = st.text_input("Motivo Desperdicio"), c1.text_input("Hora Inicio")
            hf = c2.text_input("Hora Final")
            obs = st.text_area("Observaciones")
            if st.form_submit_button("GUARDAR CORTE"):
                nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Máquina":m, "Trabajo":tr, "Papel":pa, "Ancho":an, "Gramaje":gr, "Img_Varilla":iv, "Medida":me, "Total_Varillas":tv, "Unid_Caja":uc, "Rollos_Cortados":rc, "Desp_Kg":des, "Motivo":mot, "H_Inicio":hi, "H_Fin":hf, "Obs":obs}])
                guardar_datos(nuevo, "Corte")

elif menu == "📥 COLECTORAS":
    st.header("Módulo de Colectoras")
    m = selector_tactil(MAQ_COL, "m_col")
    if m:
        with st.form("f_col"):
            c1, c2, c3 = st.columns(3)
            op, fecha_f = c1.text_input("OP"), c2.text_input("Fecha Fin")
            tr, pa = c3.text_input("Nombre Trabajo"), c1.text_input("Marca Papel")
            mf, uc = c2.text_input("Medida Forma"), c3.number_input("Unid/Caja", 0)
            hi, hf = c1.text_input("Hora Inicio"), c2.text_input("Hora Final")
            tc, tf = c3.number_input("Total Cajas", 0), c1.number_input("Total Formas", 0)
            des, mot = c2.number_input("Peso Desperdicio", 0.0), c3.text_input("Motivo Desperdicio")
            obs = st.text_area("Observaciones")
            if st.form_submit_button("GUARDAR COLECTORAS"):
                nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Máquina":m, "Trabajo":tr, "Medida_Forma":mf, "Unid_Caja":uc, "H_Inicio":hi, "H_Fin":hf, "Total_Cajas":tc, "Total_Formas":tf, "Desp_Kg":des, "Motivo":mot, "Obs":obs}])
                guardar_datos(nuevo, "Colectoras")

elif menu == "📕 ENCUADERNACIÓN":
    st.header("Módulo de Encuadernación")
    with st.form("f_enc"):
        c1, c2, c3 = st.columns(3)
        op, tr = c1.text_input("OP"), c2.text_input("Nombre Trabajo")
        cf, tm = c3.number_input("Cant. Formas", 0), c1.text_input("Tipo Material")
        me, hi = c2.text_input("Medida Forma"), c3.text_input("Hora Inicio")
        hf, uc = c1.text_input("Hora Final"), c2.number_input("Unid. Caja", 0)
        fi, tp = c3.number_input("Cant. Final", 0), c1.text_input("Tipo Presentación")
        des, mot = c2.number_input("Peso Desperdicio", 0.0), c3.text_input("Motivo Desperdicio")
        obs = st.text_area("Observaciones")
        if st.form_submit_button("GUARDAR ENCUADERNACIÓN"):
            nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Trabajo":tr, "Cant_Formas":cf, "Material":tm, "Medida":me, "H_Inicio":hi, "H_Fin":hf, "Unid_Caja":uc, "Cant_Final":fi, "Presentacion":tp, "Desp_Kg":des, "Motivo":mot, "Obs":obs}])
            guardar_datos(nuevo, "Encuadernacion")

elif menu == "⏱️ AVANCE (GAP)":
    st.header("Seguimiento de Metas")
    m = selector_tactil(MAQ_COR, "m_gap")
    if m:
        with st.form("f_gap"):
            c1, c2 = st.columns(2)
            op_h = c1.text_input("OP Actual")
            vh = c2.number_input("Varillas en esta hora", 0)
            if st.form_submit_button("REGISTRAR HORA"):
                nuevo = pd.DataFrame([{"Fecha":datetime.now().strftime("%d/%m/%Y"), "Hora":datetime.now().strftime("%H:%M"), "Máquina":m, "OP":op_h, "Varillas_Hora":vh}])
                guardar_datos(nuevo, "Seguimiento_Avance")

elif menu == "📊 HISTORIAL":
    st.header("Consulta")
    t = st.selectbox("Tabla", ["Impresion", "Corte", "Colectoras", "Encuadernacion", "Seguimiento_Avance"])
    df = conn.read(worksheet=t, ttl=0)
    st.dataframe(df, use_container_width=True)
