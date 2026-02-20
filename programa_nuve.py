import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="SISTEMA PLANTA SUPABASE", page_icon="🏭")

# --- FUNCIONES DE BASE DE DATOS ---
def guardar_en_supabase(tabla, datos):
    try:
        supabase.table(tabla).insert(datos).execute()
        st.success(f"✅ Registro guardado en la nube exitosamente")
        st.balloons()
    except Exception as e:
        st.error(f"Error al guardar: {e}")

def obtener_datos(tabla):
    try:
        res = supabase.table(tabla).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# --- MÁQUINAS ---
MA_IMP = ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"]
MA_COR = ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"]

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🏭 ACCESO")
    u, p = st.columns(2)
    user = u.text_input("Usuario")
    pas = p.text_input("Password", type="password")
    if st.button("ENTRAR", use_container_width=True):
        st.session_state.auth = True
        st.rerun()
    st.stop()

# --- INTERFAZ ---
menu = st.sidebar.radio("MENÚ", ["🖨️ IMPRESIÓN", "✂️ CORTE", "⏱️ AVANCE (GAP)", "📊 HISTORIAL Y DESCARGA"])

def selector_tactil(lista, clave):
    st.write("### Seleccione Máquina:")
    cols = st.columns(4)
    for i, m in enumerate(lista):
        if cols[i % 4].button(m, key=f"{clave}_{m}", use_container_width=True):
            st.session_state[clave] = m
    return st.session_state.get(clave)

# --- MÓDULOS ---
if menu == "🖨️ IMPRESIÓN":
    st.header("Formulario de Impresión")
    m = selector_tactil(MA_IMP, "m_imp")
    if m:
        with st.form("f_imp"):
            st.info(f"Máquina: {m}")
            c1, c2, c3 = st.columns(3)
            op, tr, pa = c1.text_input("OP"), c2.text_input("Trabajo"), c3.text_input("Papel")
            an, gr, ti = c1.text_input("Ancho"), c2.text_input("Gramaje"), c3.number_input("Tintas", 0)
            me, im, met = c1.text_input("Medida"), c2.number_input("Imágenes", 0), c3.number_input("Metros", 0)
            hi, hf, des = c1.text_input("H. Inicio"), c2.text_input("H. Fin"), c3.number_input("Desp. Kg", 0.0)
            mot, obs = st.text_input("Motivo"), st.text_area("Obs")
            if st.form_submit_button("GUARDAR DATOS"):
                datos = {
                    "op": op, "fecha": str(datetime.now().date()), "maquina": m, "trabajo": tr, "papel": pa,
                    "ancho": an, "gramaje": gr, "tintas": ti, "medida": me, "imagenes": im,
                    "metros": met, "h_inicio": hi, "h_fin": hf, "desp_kg": des, "motivo": mot, "obs": obs
                }
                guardar_en_supabase("impresion", datos)

elif menu == "✂️ CORTE":
    st.header("Formulario de Corte")
    m = selector_tactil(MA_COR, "m_cor")
    if m:
        with st.form("f_cor"):
            st.info(f"Máquina: {m}")
            c1, c2, c3 = st.columns(3)
            op, tr, iv = c1.text_input("OP"), c2.text_input("Trabajo"), c3.number_input("Img x Varilla", 0)
            me, tv, rc = c1.text_input("Medida"), c2.number_input("Total Varillas", 0), c3.number_input("Rollos", 0)
            uc, hi, hf = c1.number_input("Unid/Caja", 0), c2.text_input("H. Inicio"), c3.text_input("H. Fin")
            des, mot = c1.number_input("Desp. Kg", 0.0), st.text_input("Motivo")
            if st.form_submit_button("GUARDAR CORTE"):
                datos = {
                    "op": op, "fecha": str(datetime.now().date()), "maquina": m, "trabajo": tr,
                    "img_varilla": iv, "medida": me, "total_varillas": tv, "rollos_cortados": rc,
                    "unid_caja": uc, "h_inicio": hi, "h_fin": hf, "desp_kg": des, "motivo": mot
                }
                guardar_en_supabase("corte", datos)

elif menu == "⏱️ AVANCE (GAP)":
    st.header("Seguimiento de Producción")
    m = selector_tactil(MA_COR, "m_gap")
    if m:
        with st.form("f_gap"):
            op_h = st.text_input("OP Actual")
            vh = st.number_input("Varillas producidas esta hora", 0)
            if st.form_submit_button("REGISTRAR AVANCE"):
                datos = {
                    "fecha": str(datetime.now().date()), "hora": datetime.now().strftime("%H:%M"),
                    "maquina": m, "op": op_h, "varillas_hora": vh
                }
                guardar_en_supabase("seguimiento_avance", datos)

elif menu == "📊 HISTORIAL Y DESCARGA":
    st.header("Descarga de Datos para tu PC")
    t = st.selectbox("Seleccione Tabla:", ["impresion", "corte", "seguimiento_avance"])
    df = obtener_datos(t)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f"📥 DESCARGAR EXCEL DE {t.upper()}",
            data=csv,
            file_name=f"{t}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv',
            use_container_width=True
        )
    else:
        st.info("No hay datos registrados todavía.")
