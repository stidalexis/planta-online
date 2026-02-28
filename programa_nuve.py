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
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; width: 100%; display: block; }
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
# FUNCIONES AUXILIARES Y MODALES
# ==========================================

@st.dialog("Detalles de la Orden", width="large")
def mostrar_detalle_op(row):
    st.write("### 📄 Orden: " + str(row['op']))
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Cliente:** " + str(row.get('nombre_cliente')))
        st.write("**Trabajo:** " + str(row.get('trabajo')))
        st.write("**Vendedor:** " + str(row.get('vendedor')))
    with c2:
        st.write("**Medida:** " + str(row.get('ancho_medida')))
        st.write("**Cantidad:** " + str(row.get('unidades_solicitadas')))
        st.write("**Estado:** " + str(row.get('estado')))
    
    if row.get('url_arte'):
        st.markdown("---")
        st.link_button("📂 VER ARTE (PDF/IMAGEN)", row['url_arte'], use_container_width=True)

# ==========================================
# NAVEGACIÓN
# ==========================================
menu = st.sidebar.radio("SISTEMA NUVE", ["🖥️ Monitor General", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión"])

# 1. MONITOR GENERAL (REESCRITO PARA EVITAR ERROR DE SINTAXIS)
if menu == "🖥️ Monitor General":
    st.title("🏭 Estado Actual de Planta")
    
    # Obtener datos de trabajos activos
    try:
        res = supabase.table("trabajos_activos").select("*").execute()
        act = {a['maquina']: a for a in res.data}
    except:
        act = {}

    for area, maquinas in MAQUINAS.items():
        # LÍNEA 143: Usamos format() en lugar de f-string para máxima compatibilidad
        html_titulo = '<div class="title-area">{}</div>'.format(area)
        st.markdown(html_titulo, unsafe_allow_html=True)
        
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    d = act[m]
                    est = d.get('estado_maquina', 'PRODUCIENDO')
                    clase = "card-produccion" if est == 'PRODUCIENDO' else "card-parada"
                    # Usamos concatenación simple para evitar el error de f-string
                    card_html = '<div class="' + clase + '"><b>' + m + '</b><br>' + str(d['op']) + '</div>'
                    st.markdown(card_html, unsafe_allow_html=True)
                else:
                    card_vacia = '<div class="card-vacia"><b>' + m + '</b><br>LIBRE</div>'
                    st.markdown(card_vacia, unsafe_allow_html=True)
    
    time.sleep(15)
    st.rerun()

# 2. SEGUIMIENTO
elif menu == "🔍 Seguimiento":
    st.title("🔍 Seguimiento de Producción")
    res = supabase.table("ordenes_planeadas").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[["op", "nombre_cliente", "trabajo", "proxima_area", "estado"]], use_container_width=True)
        for idx, r in df.iterrows():
            if st.button("Ver Detalle " + str(r['op']), key="btn_" + str(r['op'])):
                mostrar_detalle_op(r)

# 3. PLANIFICACIÓN
elif menu == "📅 Planificación":
    st.title("📅 Nueva Orden")
    
    # Subida de arte con persistencia en session_state
    archivo = st.file_uploader("Cargar Arte", type=["pdf", "png", "jpg"])
    if archivo:
        if st.button("1. SUBIR ARCHIVO"):
            with st.spinner("Subiendo..."):
                path = "artes/" + str(int(time.time())) + "_" + archivo.name
                supabase.storage.from_("artes").upload(path, archivo.getvalue())
                st.session_state.url_temp = supabase.storage.from_("artes").get_public_url(path)
                st.success("Archivo subido correctamente.")

    with st.form("f_alta_op"):
        op_id = st.text_input("Número de OP (Ej: 1234)")
        cli = st.text_input("Cliente")
        trab = st.text_input("Trabajo")
        area = st.selectbox("Área de Inicio", ["IMPRESIÓN", "CORTE", "COLECTORAS"])
        
        if st.form_submit_button("2. REGISTRAR ORDEN"):
            if op_id and cli:
                url = st.session_state.get('url_temp', None)
                payload = {
                    "op": op_id, "nombre_cliente": cli, "trabajo": trab, 
                    "proxima_area": area, "url_arte": url, "estado": "Pendiente"
                }
                supabase.table("ordenes_planeadas").insert(payload).execute()
                if 'url_temp' in st.session_state: del st.session_state['url_temp']
                st.success("Orden Registrada.")
                st.rerun()

# 4. IMPRESIÓN
elif menu == "🖨️ Impresión":
    st.title("🖨️ Área de Impresión")
    m_sel = st.selectbox("Máquina", MAQUINAS["IMPRESIÓN"])
    
    res_ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", "IMPRESIÓN").execute()
    if res_ops.data:
        op_list = [o['op'] for o in res_ops.data]
        op_sel = st.selectbox("Seleccionar OP", op_list)
        if st.button("▶️ INICIAR TRABAJO"):
            d = next(o for o in res_ops.data if o['op'] == op_sel)
            supabase.table("trabajos_activos").insert({
                "maquina": m_sel, "op": d['op'], "trabajo": d['trabajo'], "area": "IMPRESIÓN"
            }).execute()
            st.rerun()
