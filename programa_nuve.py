import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="SISTEMA PLANTA MODULAR")

# --- ESTILO TÁCTIL PERSONALIZADO (CSS) ---
st.markdown("""
    <style>
    div.stButton > button {
        height: 80px;
        font-size: 20px;
        font-weight: bold;
        border-radius: 10px;
        border: 2px solid #4CAF50;
    }
    div.stButton > button:hover {
        background-color: #4CAF50;
        color: white;
    }
    .card {
        padding: 20px;
        border-radius: 15px;
        background-color: #f0f2f6;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.update({"auth": False, "rol": None})
if not st.session_state.auth:
    st.title("🏭 ACCESO A LA EMPRESA")
    usuarios = {"admin": "admin2026", "impresion": "imp2026", "colectoras": "col2026", "corte1": "c1p", "corte2": "c2p", "encuadernacion": "enc2026"}
    u = st.text_input("Usuario").lower().strip()
    p = st.text_input("Contraseña", type="password")
    if st.button("ENTRAR"):
        if u in usuarios and usuarios[u] == p:
            st.session_state.auth, st.session_state.rol = True, u
            st.rerun()
    st.stop()

# --- COMPONENTES TÁCTILES ---
def grid_maquinas(lista, clave_session):
    st.subheader("Seleccione Máquina:")
    cols = st.columns(4)
    for i, m in enumerate(lista):
        if cols[i % 4].button(m, key=f"btn_{clave_session}_{m}", use_container_width=True):
            st.session_state[clave_session] = m
    return st.session_state.get(clave_session)

# --- MÓDULO INDEPENDIENTE: IMPRESIÓN ---
def modulo_impresion():
    st.title("🖨️ ÁREA DE IMPRESIÓN")
    maquinas = ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"]
    m = grid_maquinas(maquinas, "m_imp")
    
    if m:
        st.info(f"Máquina seleccionada: **{m}**")
        col1, col2 = st.columns(2)
        
        # INICIO (POST-MORTEM O REAL TIME)
        with col1:
            with st.form("form_ini_imp"):
                st.subheader("1. Iniciar OP")
                op = st.text_input("OP")
                tr = st.text_input("Trabajo")
                if st.form_submit_button("REGISTRAR INICIO"):
                    supabase.table("trabajos_activos").insert({"maquina":m, "op":op, "trabajo":tr, "area":"impresion"}).execute()
                    st.success("OP Iniciada")

        # CIERRE
        with col2:
            st.subheader("2. Finalizar y Datos Técnicos")
            activos = supabase.table("trabajos_activos").select("*").eq("maquina", m).execute().data
            if activos:
                act = activos[0]
                with st.form("form_fin_imp"):
                    st.write(f"OP Activa: {act['op']}")
                    c1, c2 = st.columns(2)
                    papel = c1.text_input("Papel")
                    ancho = c2.text_input("Ancho")
                    gramaje = c1.text_input("Gramaje")
                    tintas = c2.number_input("Tintas", 0)
                    metros = c1.number_input("Metros Finales", 0)
                    desp = c2.number_input("Desperdicio Kg", 0.0)
                    if st.form_submit_button("FINALIZAR TRABAJO"):
                        data_final = {"op":act['op'], "maquina":m, "trabajo":act['trabajo'], "papel":papel, "ancho":ancho, "gramaje":gramaje, "tintas":tintas, "metros":metros, "desp_kg":desp, "h_inicio":act['hora_inicio'], "h_fin":datetime.now().strftime("%H:%M")}
                        supabase.table("impresion").insert(data_final).execute()
                        supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                        st.rerun()
            else:
                st.warning("No hay OP activa en esta máquina.")

# --- MÓDULO INDEPENDIENTE: CORTE ---
def modulo_corte(usuario_corte):
    st.title(f"✂️ ÁREA DE CORTE ({usuario_corte.upper()})")
    maqs = ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07"] if usuario_corte == "corte1" else ["COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"]
    m = grid_maquinas(maqs, f"m_{usuario_corte}")
    
    if m:
        st.info(f"Máquina seleccionada: **{m}**")
        col1, col2 = st.columns(2)
        with col1:
            with st.form("ini_corte"):
                st.subheader("Iniciar Corte")
                op = st.text_input("OP")
                tr = st.text_input("Trabajo")
                if st.form_submit_button("INICIAR"):
                    supabase.table("trabajos_activos").insert({"maquina":m, "op":op, "trabajo":tr, "area":usuario_corte}).execute()
        
        with col2:
            st.subheader("Finalizar Corte")
            act = supabase.table("trabajos_activos").select("*").eq("maquina", m).execute().data
            if act:
                with st.form("fin_corte"):
                    iv = st.number_input("Img x Varilla", 0)
                    tv = st.number_input("Total Varillas", 0)
                    rc = st.number_input("Rollos Cortados", 0)
                    dk = st.number_input("Desperdicio Kg", 0.0)
                    if st.form_submit_button("GUARDAR Y CERRAR"):
                        supabase.table("corte").insert({"op":act[0]['op'], "maquina":m, "img_varilla":iv, "total_varillas":tv, "rollos_cortados":rc, "desp_kg":dk}).execute()
                        supabase.table("trabajos_activos").delete().eq("id", act[0]['id']).execute()
                        st.rerun()

# --- MÓDULO INDEPENDIENTE: PARADAS ---
def modulo_paradas():
    st.subheader("⚠️ REGISTRO DE PARADA DE MÁQUINA")
    with st.expander("Abrir panel de paradas"):
        maq = st.text_input("Máquina que se detiene")
        motivo = st.selectbox("Motivo", ["Mantenimiento", "Falla Eléctrica", "Cambio Formato", "Ajuste", "Limpieza"])
        if st.button("REGISTRAR PARADA"):
            supabase.table("paradas_maquina").insert({"maquina":maq, "motivo":motivo}).execute()
            st.warning(f"Parada registrada en {maq}")

# --- ESTRUCTURA DE LA EMPRESA (NAVEGACIÓN) ---
rol = st.session_state.rol
st.sidebar.title(f"Usuario: {rol.upper()}")

if rol == "admin":
    menu = st.sidebar.radio("IR A:", ["IMPRESIÓN", "CORTE 1", "CORTE 2", "COLECTORAS", "ENCUADERNACIÓN", "ADMINISTRACIÓN"])
    if menu == "IMPRESIÓN": modulo_impresion()
    elif menu == "CORTE 1": modulo_corte("corte1")
    elif menu == "CORTE 2": modulo_corte("corte2")
    # ... agregar el resto de módulos ...
    elif menu == "ADMINISTRACIÓN":
        st.title("Reportes Generales")
        t = st.selectbox("Tabla", ["impresion", "corte", "paradas_maquina"])
        df = pd.DataFrame(supabase.table(t).select("*").execute().data)
        st.dataframe(df)

elif rol == "impresion": modulo_impresion()
elif rol == "corte1": modulo_corte("corte1")
elif rol == "corte2": modulo_corte("corte2")

# Mostrar paradas siempre abajo para los operarios
if rol != "admin":
    st.divider()
    modulo_paradas()
