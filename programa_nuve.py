import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import io
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V10.2", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 15px; border-radius: 12px; text-align: center; color: #1B5E20; box-shadow: 0px 0px 15px rgba(0,230,118,0.5); margin-bottom:10px;}
    .card-parada { background-color: #FF5252; border: 2px solid #D32F2F; padding: 15px; border-radius: 12px; text-align: center; color: white; box-shadow: 0px 0px 15px rgba(255,82,82,0.5); margin-bottom:10px;}
    .card-turno { background-color: #FFD740; border: 2px solid #FFA000; padding: 15px; border-radius: 12px; text-align: center; color: #5D4037; margin-bottom:10px;}
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px; text-align: center; color: #9E9E9E; margin-bottom:10px;}
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# ==========================================
# MODALES
# ==========================================

@st.dialog("Detalles de la Orden de Producción", width="large")
def mostrar_detalle_op(row):
    st.markdown(f"### 📄 Orden: {row['op']}")
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**DATOS GENERALES**")
        st.write(f"👤 **Cliente:** {row.get('nombre_cliente')}")
        st.write(f"💼 **Vendedor:** {row.get('vendedor')}")
        st.write(f"🛠️ **Trabajo:** {row.get('trabajo')}")
    with col2:
        st.markdown("**ESPECIFICACIONES**")
        st.write(f"📄 **Material:** {row.get('material')}")
        st.write(f"📏 **Medida:** {row.get('ancho_medida')}")
        st.write(f"📦 **Cantidad:** {row.get('unidades_solicitadas')}")
    with col3:
        st.markdown("**PROCESO TÉCNICO**")
        st.write(f"⚙️ **Core:** {row.get('core')}")
        st.write(f"🔢 **Numeración:** {row.get('num_desde')} - {row.get('num_hasta')}")
    
    if row.get('url_arte'):
        st.markdown("---")
        st.link_button("📂 ABRIR ARTE / PDF", row['url_arte'], use_container_width=True)

@st.dialog("REPORTE TÉCNICO", width="large")
def modal_reporte_impresion(t, m_s, tipo="FINAL"):
    st.subheader(f"Reporte {tipo}: {t['op']}")
    with st.form("f_rep"):
        operario = st.text_input("Nombre del Operario")
        if st.form_submit_button("💾 GUARDAR"):
            if operario:
                # Lógica simplificada para el ejemplo
                supabase.table("trabajos_activos").delete().eq("maquina", m_s).execute()
                st.rerun()
            else:
                st.error("Falta operario")

# ==========================================
# NAVEGACIÓN
# ==========================================
menu = st.sidebar.radio("MENÚ", ["🖥️ Monitor General", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión"])

# 1. MONITOR GENERAL (AQUÍ ESTABA EL ERROR)
if menu == "🖥️ Monitor General":
    st.title("🏭 Monitor de Planta")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    
    for area, maquinas in MAQUINAS.items():
        # LÍNEA 143 CORREGIDA CON TRIPLE COMILLA
        st.markdown(f"""<div class='title-area'>{area}</div>""", unsafe_allow_html=True)
        
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    d = act[m]
                    st.markdown(f"""<div class='card-produccion'><b>{m}</b><br>{d['op']}</div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div class='card-vacia'><b>{m}</b><br>LIBRE</div>""", unsafe_allow_html=True)
    time.sleep(15)
    st.rerun()

# 2. SEGUIMIENTO
elif menu == "🔍 Seguimiento":
    st.title("🔍 Seguimiento")
    ops = supabase.table("ordenes_planeadas").select("*").execute().data
    if ops:
        for fila in ops:
            c1, c2, c3 = st.columns([1, 2, 1])
            c1.write(fila['op'])
            c2.write(fila['trabajo'])
            if c3.button("Ver", key=fila['op']):
                mostrar_detalle_op(fila)

# 3. PLANIFICACIÓN (CORRECCIÓN CARGA BLOQUEADA)
elif menu == "📅 Planificación":
    st.title("📅 Nueva Orden")
    
    # Subida fuera del form para evitar bloqueos
    archivo = st.file_uploader("Subir Arte PDF", type=["pdf", "png", "jpg"])
    if archivo:
        if st.button("1. SUBIR ARCHIVO AL SERVIDOR"):
            with st.spinner("Subiendo..."):
                path = f"artes/{int(time.time())}_{archivo.name}"
                supabase.storage.from_("artes").upload(path, archivo.getvalue())
                st.session_state.url_temp = supabase.storage.from_("artes").get_public_url(path)
                st.success("Archivo subido con éxito.")

    with st.form("f_alta"):
        op_n = st.text_input("Número de OP")
        cliente = st.text_input("Cliente")
        trabajo = st.text_input("Trabajo")
        if st.form_submit_button("2. REGISTRAR TODO"):
            url = st.session_state.get('url_temp', None)
            data = {"op": op_n, "nombre_cliente": cliente, "trabajo": trabajo, "url_arte": url, "proxima_area": "IMPRESIÓN"}
            supabase.table("ordenes_planeadas").insert(data).execute()
            st.success("Registrado.")
            st.rerun()

# 4. IMPRESIÓN
elif menu == "🖨️ Impresión":
    st.title("🖨️ Impresión")
    # Lógica de impresión similar a versiones previas...
    st.info("Seleccione una máquina para iniciar.")
