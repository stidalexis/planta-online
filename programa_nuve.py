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
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px; text-align: center; color: #9E9E9E; margin-bottom:10px;}
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; width: 100%; display: block; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": ["LINEA-01", "LINEA-02", "LINEA-03", "LINEA-04", "LINEA-05"]
}

# ==========================================
# FUNCIONES Y DIÁLOGOS
# ==========================================

@st.dialog("Detalles de la Orden")
def mostrar_detalle(row):
    st.subheader("Orden: " + str(row['op']))
    st.write("**Cliente:** " + str(row['nombre_cliente']))
    st.write("**Trabajo:** " + str(row['trabajo']))
    if row.get('url_arte'):
        st.link_button("📂 VER ARTE", row['url_arte'], use_container_width=True)

# ==========================================
# INTERFAZ PRINCIPAL
# ==========================================
menu = st.sidebar.radio("SISTEMA NUVE", ["🖥️ Monitor General", "🔍 Seguimiento", "📅 Planificación", "🖨️ Operaciones"])

# 1. MONITOR GENERAL
if menu == "🖥️ Monitor General":
    st.title("🏭 Monitor de Planta Online")
    
    try:
        res = supabase.table("trabajos_activos").select("*").execute()
        act = {a['maquina']: a for a in res.data}
    except:
        act = {}

    for area, maquinas in MAQUINAS.items():
        # Solución definitiva al error de sintaxis:
        st.markdown('<div class="title-area">' + area + '</div>', unsafe_allow_html=True)
        
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    d = act[m]
                    clase = "card-produccion" if d.get('estado') != 'PARADA' else "card-parada"
                    st.markdown('<div class="' + clase + '"><b>' + m + '</b><br>' + str(d['op']) + '</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="card-vacia"><b>' + m + '</b><br>LIBRE</div>', unsafe_allow_html=True)
    
    time.sleep(20)
    st.rerun()

# 2. SEGUIMIENTO
elif menu == "🔍 Seguimiento":
    st.title("🔍 Seguimiento de Órdenes")
    try:
        res = supabase.table("ordenes_planeadas").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.dataframe(df[["op", "nombre_cliente", "trabajo", "proxima_area", "estado"]], use_container_width=True)
            sel_op = st.selectbox("Seleccione OP para ver detalle:", df['op'].tolist())
            if st.button("Ver Detalle"):
                fila = df[df['op'] == sel_op].iloc[0]
                mostrar_detalle(fila)
    except Exception as e:
        st.error("Error al conectar: " + str(e))

# 3. PLANIFICACIÓN
elif menu == "📅 Planificación":
    st.title("📅 Registro de Nueva Orden")
    
    # Manejo de Arte
    archivo = st.file_uploader("Subir Arte (PDF/JPG)", type=["pdf", "png", "jpg"])
    if archivo:
        if st.button("1. SUBIR ARTE AL SERVIDOR"):
            with st.spinner("Subiendo..."):
                path = "artes/" + str(int(time.time())) + "_" + archivo.name
                supabase.storage.from_("artes").upload(path, archivo.getvalue())
                st.session_state.url_temp = supabase.storage.from_("artes").get_public_url(path)
                st.success("Archivo cargado con éxito.")

    with st.form("form_registro"):
        c1, c2 = st.columns(2)
        op_id = c1.text_input("Número de OP")
        cliente = c2.text_input("Cliente")
        trabajo = st.text_input("Descripción del Trabajo")
        area_inicio = st.selectbox("Área de Inicio", ["IMPRESIÓN", "CORTE", "COLECTORAS"])
        
        if st.form_submit_button("2. REGISTRAR ORDEN"):
            if op_id and cliente:
                url_final = st.session_state.get('url_temp', None)
                data_insert = {
                    "op": op_id.upper(),
                    "nombre_cliente": cliente,
                    "trabajo": trabajo,
                    "proxima_area": area_inicio,
                    "estado": "Pendiente",
                    "url_arte": url_final
                }
                try:
                    supabase.table("ordenes_planeadas").insert(data_insert).execute()
                    st.success("¡Orden guardada en Supabase!")
                    if 'url_temp' in st.session_state: del st.session_state['url_temp']
                    st.rerun()
                except Exception as e:
                    st.error("Error de Inserción: " + str(e))
            else:
                st.warning("Complete OP y Cliente.")

# 4. OPERACIONES
elif menu == "🖨️ Operaciones":
    st.title("⚙️ Panel de Operación")
    area_op = st.selectbox("Seleccione su Área", list(MAQUINAS.keys()))
    maq_op = st.selectbox("Seleccione Máquina", MAQUINAS[area_op])
    
    # Obtener OPs para esa área
    res_ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_op).execute()
    if res_ops.data:
        op_list = [o['op'] for o in res_ops.data]
        op_sel = st.selectbox("OP para iniciar", op_list)
        
        if st.button("▶️ INICIAR TRABAJO"):
            d_op = next(o for o in res_ops.data if o['op'] == op_sel)
            ins = {"maquina": maq_op, "op": d_op['op'], "trabajo": d_op['trabajo'], "area": area_op, "estado": "PRODUCIENDO"}
            supabase.table("trabajos_activos").insert(ins).execute()
            st.success("Trabajo iniciado en " + maq_op)
            st.rerun()

    if st.button("🏁 FINALIZAR TRABAJO ACTUAL"):
        supabase.table("trabajos_activos").delete().eq("maquina", maq_op).execute()
        st.warning("Máquina liberada.")
        st.rerun()
