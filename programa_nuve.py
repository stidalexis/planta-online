import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="PLANTA INTEGRAL ONLINE", page_icon="🏭")

# --- FUNCIONES DE BASE DE DATOS ---
def guardar(tabla, datos):
    try:
        supabase.table(tabla).insert(datos).execute()
        st.success("✅ Registro guardado exitosamente en la nube.")
        st.balloons()
    except Exception as e:
        st.error(f"Error al guardar: {e}")

def leer(tabla):
    try:
        res = supabase.table(tabla).select("*").order("id", desc=True).execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# --- AUTENTICACIÓN Y ROLES ---
if "auth" not in st.session_state:
    st.session_state.update({"auth": False, "rol": None})

if not st.session_state.auth:
    st.title("🏭 ACCESO SISTEMA DE PRODUCCIÓN")
    usuarios = {
        "administrador": "admin2026",
        "impresion": "imp2026",
        "colectoras": "col2026",
        "corte1": "c1p",
        "corte2": "c2p",
        "encuadernacion": "enc2026"
    }
    u = st.text_input("Usuario").lower().strip()
    p = st.text_input("Contraseña", type="password")
    if st.button("INGRESAR", use_container_width=True):
        if u in usuarios and usuarios[u] == p:
            st.session_state.auth, st.session_state.rol = True, u
            st.rerun()
        else:
            st.error("Credenciales inválidas")
    st.stop()

# --- MENÚ SEGMENTADO ---
rol = st.session_state.rol
opc_map = {
    "administrador": ["🖨️ IMPRESIÓN", "✂️ CORTE", "📥 COLECTORAS", "📕 ENCUADERNACIÓN", "⏱️ METAS (GAP)", "📊 REPORTES"],
    "impresion": ["🖨️ IMPRESIÓN"],
    "colectoras": ["📥 COLECTORAS"],
    "corte1": ["✂️ CORTE", "⏱️ METAS (GAP)"],
    "corte2": ["✂️ CORTE", "⏱️ METAS (GAP)"],
    "encuadernacion": ["📕 ENCUADERNACIÓN"]
}
opciones = opc_map.get(rol, [])

st.sidebar.title(f"Usuario: {rol.upper()}")
menu = st.sidebar.radio("Navegación", opciones)
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()

# --- LISTAS DE MÁQUINAS ---
MA_IMP = ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"]
MA_COR = ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"]
MA_COL = ["COL-01", "COL-02"]

def selector_maquina(lista, clave):
    st.write("### Seleccione Máquina:")
    cols = st.columns(4)
    for i, m in enumerate(lista):
        if cols[i % 4].button(m, key=f"{clave}_{m}", use_container_width=True):
            st.session_state[clave] = m
    return st.session_state.get(clave)

# --- MÓDULOS ---
if menu == "🖨️ IMPRESIÓN":
    st.header("Módulo de Impresión")
    m = selector_maquina(MA_IMP, "m_imp")
    if m:
        with st.form("f_imp"):
            st.subheader(f"Prensa: {m}")
            c1, c2, c3 = st.columns(3)
            op, tr, pa = c1.text_input("OP"), c2.text_input("Trabajo"), c3.text_input("Papel")
            an, gr, ti = c1.text_input("Ancho"), c2.text_input("Gramaje"), c3.number_input("Tintas", 0)
            me, im, mt = c1.text_input("Medida"), c2.number_input("Imágenes", 0), c3.number_input("Metros Totales", 0)
            hi, hf, d_k = c1.text_input("H. Inicio"), c2.text_input("H. Fin"), c3.number_input("Desp. Kg", 0.0)
            mot, obs = st.text_input("Motivo Desp."), st.text_area("Observaciones")
            if st.form_submit_button("GUARDAR REGISTRO"):
                guardar("impresion", {"op":op,"maquina":m,"trabajo":tr,"papel":pa,"ancho":an,"gramaje":gr,"tintas":ti,"medida":me,"imagenes":im,"metros":mt,"h_inicio":hi,"h_fin":hf,"desp_kg":d_k,"motivo":mot,"obs":obs})

elif menu == "✂️ CORTE":
    st.header(f"Módulo de Corte ({rol.upper()})")
    m = selector_maquina(MA_COR, "m_cor")
    if m:
        with st.form("f_cor"):
            st.subheader(f"Cortadora: {m}")
            c1, c2, c3 = st.columns(3)
            op, tr, iv = c1.text_input("OP"), c2.text_input("Trabajo"), c3.number_input("Img x Varilla", 0)
            me, tv, rc = c1.text_input("Medida"), c2.number_input("Total Varillas", 0), c3.number_input("Rollos Cortados", 0)
            uc, hi, hf = c1.number_input("Unid/Caja", 0), c2.text_input("H. Inicio"), c3.text_input("H. Fin")
            dk, mo = c1.number_input("Desp. Kg", 0.0), st.text_input("Motivo")
            if st.form_submit_button("GUARDAR CORTE"):
                guardar("corte", {"op":op,"maquina":m,"trabajo":tr,"img_varilla":iv,"medida":me,"total_varillas":tv,"rollos_cortados":rc,"unid_caja":uc,"h_inicio":hi,"h_fin":hf,"desp_kg":dk,"motivo":mo, "obs": f"Reg por {rol}"})

elif menu == "📥 COLECTORAS":
    st.header("Módulo Colectoras")
    m = selector_maquina(MA_COL, "m_col")
    if m:
        with st.form("f_col"):
            c1, c2, c3 = st.columns(3)
            op, tr, pa = c1.text_input("OP"), c2.text_input("Trabajo"), c3.text_input("Papel")
            mf, uc = c1.text_input("Medida Forma"), c2.number_input("Unid/Caja", 0)
            hi, hf = c1.text_input("H. Inicio"), c2.text_input("H. Fin")
            tc, tf = c1.number_input("Total Cajas", 0), c2.number_input("Total Formas", 0)
            dk, mo = c3.number_input("Desp. Kg", 0.0), st.text_input("Motivo")
            if st.form_submit_button("GUARDAR COLECTORA"):
                guardar("colectoras", {"op":op,"maquina":m,"trabajo":tr,"papel":pa,"medida_forma":mf,"unid_caja":uc,"h_inicio":hi,"h_fin":hf,"total_cajas":tc,"total_formas":tf,"desp_kg":dk,"motivo":mo})

elif menu == "📕 ENCUADERNACIÓN":
    st.header("Módulo Encuadernación")
    with st.form("f_enc"):
        c1, c2, c3 = st.columns(3)
        op, tr, cf = c1.text_input("OP"), c2.text_input("Trabajo"), c3.number_input("Cant. Formas", 0)
        tm, me, hi = c1.text_input("Material"), c2.text_input("Medida"), c3.text_input("H. Inicio")
        hf, uc, fi = c1.text_input("H. Fin"), c2.number_input("Unid/Caja", 0), c3.number_input("Cant. Final", 0)
        tp, dk, mo = c1.text_input("Presentación"), c2.number_input("Desp. Kg", 0.0), c3.text_input("Motivo")
        if st.form_submit_button("GUARDAR ENCUADERNACIÓN"):
            guardar("encuadernacion", {"op":op,"trabajo":tr,"cant_formas":cf,"material":tm,"medida":me,"h_inicio":hi,"h_fin":hf,"unid_caja":uc,"cant_final":fi,"presentacion":tp,"desp_kg":dk,"motivo":mo})

elif menu == "⏱️ METAS (GAP)":
    st.header("Registro de Avance por Hora")
    m = selector_maquina(MA_COR, "m_gap")
    if m:
        with st.form("f_gap"):
            c1, c2 = st.columns(2)
            op_h = c1.text_input("OP Actual")
            vh = c2.number_input("Varillas producidas en esta hora", 0)
            if st.form_submit_button("🚀 REGISTRAR PRODUCCIÓN"):
                guardar("seguimiento_avance", {"hora":datetime.now().strftime("%H:%M"),"maquina":m,"op":op_h,"varillas_hora":vh})

elif menu == "📊 REPORTES":
    st.header("Centro de Datos - Administrador")
    t = st.selectbox("Seleccione Tabla:", ["impresion", "corte", "colectoras", "encuadernacion", "seguimiento_avance"])
    df = leer(t)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 DESCARGAR CSV PARA EXCEL", data=csv, file_name=f"{t}.csv", mime='text/csv', use_container_width=True)
    else:
        st.info("Sin registros.")
