import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import io
from fpdf import FPDF
import pytz

# --- CONFIGURACION DE PAGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V0.01 - TOTAL", page_icon="🏭")

# --- CONEXION A SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("Error de conexión a Base de Datos. Revisa los Secrets.")
    st.stop()

def hora_colombia():
    return datetime.now(pytz.timezone('America/Bogota'))

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stButton > button { height: 70px !important; border-radius: 15px; font-weight: bold; font-size: 20px !important; width: 100%; }
    .title-area { background-color: #0D47A1; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 22px; margin-bottom: 20px; }
    .card-maquina { background-color: #f8f9fa; padding: 20px; border-radius: 15px; border-left: 10px solid #0D47A1; margin-bottom: 20px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); }
    </style>
""", unsafe_allow_html=True)

# --- 1. DEFINICIÓN DE ROLES Y PERMISOS ---
ACCESO_ROLES = {
    "VENDEDOR": ["🚀 Monitor General", "📋 Seguimiento", "📅 Planificación"],
    "SUP_CORTE": ["📊 Monitor Corte", "✂️ Área de Corte"],
    "SUP_IMPRESION": ["🚀 Monitor General", "🖨️ Área de Impresión", "🌀 Colectoras", "📚 Encuadernación"],
    "SUP_REBOBINADORA": ["📊 Monitor Rebobinadoras", "🔄 Rebobinadoras"],
    "SUP_ENCUADERNACION": ["📊 Monitor Encuadernación", "📚 Encuadernación"],
    "ADMIN": ["🚀 Monitor General", "📋 Seguimiento", "📅 Planificación", "🖨️ Área de Impresión", "✂️ Área de Corte", "🌀 Colectoras", "📚 Encuadernación", "🔄 Rebobinadoras", "📊 Control Supervisor (Hora a Hora)"]
}

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.perfil = None

# --- 2. PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    st.markdown("<div class='title-area'>🔐 ACCESO SISTEMA NUVE</div>", unsafe_allow_html=True)
    c1, _ = st.columns([1, 1])
    with c1:
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR"):
            creds = {
                "admin": ("admin77", "ADMIN"),
                "ventas": ("v123", "VENDEDOR"),
                "corte": ("c123", "SUP_CORTE"),
                "impresion": ("i123", "SUP_IMPRESION"),
                "rebobina": ("r123", "SUP_REBOBINADORA"),
                "encuaderna": ("e123", "SUP_ENCUADERNACION")
            }
            if u in creds and p == creds[u][0]:
                st.session_state.perfil = creds[u][1]
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    st.stop()

# --- 3. BARRA LATERAL ---
with st.sidebar:
    st.title(f"👤 {st.session_state.perfil}")
    opciones = ACCESO_ROLES.get(st.session_state.perfil, [])
    pagina = st.radio("Ir a:", opciones)
    st.divider()
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

# --- 4. CONTENIDO SEGÚN LA PÁGINA SELECCIONADA ---

if pagina == "🚀 Monitor General":
    st.markdown("<div class='title-area'>🚀 MONITOR GENERAL DE PRODUCCIÓN</div>", unsafe_allow_html=True)
    # --- TU CODIGO ORIGINAL DEL MONITOR ---
    areas = ["PLANIFICACIÓN", "IMPRESIÓN", "CORTE", "COLECTORAS", "ENCUADERNACIÓN", "REBOBINADORAS", "FINALIZADO"]
    cols = st.columns(len(areas))

    for i, area in enumerate(areas):
        with cols[i]:
            st.markdown(f"<div class='title-area' style='font-size:14px; padding:10px;'>{area}</div>", unsafe_allow_html=True)
            
            # Consultar OPs
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area).execute().data
            
            # Consultar si hay algo activo en esa área
            activos = supabase.table("trabajos_activos").select("op,maquina").eq("area", area).execute().data
            op_activa = activos[0]['op'] if activos else None
            maq_activa = activos[0]['maquina'] if activos else ""

            if ops:
                for o in ops:
                    es_esta = (str(o['op']) == str(op_activa))
                    color = "#FFEB3B" if es_esta else "#FFFFFF"
                    borde = "5px solid #F44336" if es_esta else "1px solid #ddd"
                    texto_estado = f"⚠️ EN: {maq_activa}" if es_esta else "⏳ ESPERA"
                    
                    st.markdown(f"""
                        <div style="background-color:{color}; padding:10px; border-radius:10px; border:{borde}; margin-bottom:10px; color:black;">
                            <b style="font-size:16px;">OP: {o['op']}</b><br>
                            <span style="font-size:13px;">{o['trabajo']}</span><br>
                            <hr style="margin:5px 0;">
                            <center><b style="font-size:12px;">{texto_estado}</b></center>
                        </div>
                    """, unsafe_allow_html=True)
                    
elif pagina == "🖨️ Área de Impresión":
    st.markdown("<div class='title-area'>🖨️ ÁREA DE IMPRESIÓN</div>", unsafe_allow_html=True)
    # Aquí va tu bloque de máquinas de Impresión
    # [HEIDELBERG, ROLAND, KBA, KOMORI]
    st.info("Selecciona una máquina para trabajar.")

elif pagina == "✂️ Área de Corte":
    st.markdown("<div class='title-area'>✂️ ÁREA DE CORTE</div>", unsafe_allow_html=True)
    # Aquí va tu bloque de máquinas de Corte
    st.info("Gestión de Guillotinas y Troqueladoras.")

elif pagina == "📊 Control Supervisor (Hora a Hora)":
    st.markdown("<div class='title-area'>📊 REGISTRO DE PRODUCCIÓN HORA A HORA</div>", unsafe_allow_html=True)
    # Aquí es donde pondremos el nuevo formulario que querías
    st.write("Formulario de rendimiento horario para el administrador.")
