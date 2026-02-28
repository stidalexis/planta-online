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
# MODALES
# ==========================================

@st.dialog("Detalles de la Orden", width="large")
def mostrar_detalle_op(row):
    st.write(f"### 📄 Orden: {row['op']}")
    st.divider()
    c1, c2 = st.columns(2)
    c1.write(f"👤 Cliente: {row.get('nombre_cliente')}")
    c1.write(f"🛠️ Trabajo: {row.get('trabajo')}")
    c2.write(f"📏 Medida: {row.get('ancho_medida')}")
    c2.write(f"📦 Cantidad: {row.get('unidades_solicitadas')}")
    if row.get('url_arte'):
        st.link_button("📂 VER ARTE (PDF/IMG)", row['url_arte'], use_container_width=True)

@st.dialog("REPORTE DE PRODUCCIÓN")
def modal_reporte(t, m_s, tipo):
    with st.form("f_rep"):
        opero = st.text_input("Operario")
        metros = st.number_input("Metros", 0)
        if st.form_submit_button("GUARDAR"):
            if opero:
                supabase.table("trabajos_activos").delete().eq("maquina", m_s).execute()
                st.rerun()

# ==========================================
# NAVEGACIÓN
# ==========================================
menu = st.sidebar.radio("SISTEMA NUVE", ["🖥️ Monitor General", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión"])

# 1. MONITOR GENERAL (CORRECCIÓN CRÍTICA LÍNEA 143)
if menu == "🖥️ Monitor General":
    st.title("🏭 Estado de Planta")
    try:
        act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    except:
        act = {}

    for area, maquinas in MAQUINAS.items():
        # LÍNEA 143: SE CAMBIÓ LA SINTAXIS PARA EVITAR EL ERROR DE PYTHON
        st.markdown(f'<div class="title-area">{area}</div>', unsafe_allow_html=True)
        
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    d = act[m]
                    st.markdown(f'<div class="card-produccion"><b>{m}</b><br>{d["op"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="card-vacia"><b>{m}</b><br>LIBRE</div>', unsafe_allow_html=True)
    
    time.sleep(15)
    st.rerun()

# 2. SEGUIMIENTO
elif menu == "🔍 Seguimiento":
    st.title("🔍 Seguimiento")
    data = supabase.table("ordenes_planeadas").select("*").execute().data
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df[["op", "nombre_cliente", "trabajo", "proxima_area", "estado"]])
        for idx, r in df.iterrows():
            if st.button(f"Ver Detalle {r['op']}", key=f"btn_{r['op']}"):
                mostrar_detalle_op(r)

# 3. PLANIFICACIÓN (CARGA SIN BLOQUEO)
elif menu == "📅 Planificación":
    st.title("📅 Nueva Orden de Producción")
    
    # PASO 1: CARGAR ARTE
    archivo = st.file_uploader("Subir Arte (Opcional)", type=["pdf", "png", "jpg"])
    url_guardada = st.session_state.get('url_temp', None)
    
    if archivo and not url_guardada:
        if st.button("⬆️ SUBIR ARCHIVO"):
            with st.spinner("Subiendo..."):
                nombre_archivo = f"artes/{int(time.time())}_{archivo.name}"
                supabase.storage.from_("artes").upload(nombre_archivo, archivo.getvalue())
                url_guardada = supabase.storage.from_("artes").get_public_url(nombre_archivo)
                st.session_state.url_temp = url_guardada
                st.success("Archivo listo.")

    # PASO 2: FORMULARIO
    with st.form("registro_op"):
        op_id = st.text_input("Número de OP")
        cliente = st.text_input("Cliente")
        trabajo = st.text_input("Descripción del Trabajo")
        area_ini = st.selectbox("Inicia en:", ["IMPRESIÓN", "CORTE", "COLECTORAS"])
        
        if st.form_submit_button("🚀 REGISTRAR TODO"):
            if op_id and cliente:
                payload = {
                    "op": op_id, 
                    "nombre_cliente": cliente, 
                    "trabajo": trabajo, 
                    "proxima_area": area_ini,
                    "url_arte": st.session_state.get('url_temp', None)
                }
                supabase.table("ordenes_planeadas").insert(payload).execute()
                if 'url_temp' in st.session_state: del st.session_state['url_temp']
                st.success("¡Registrado!")
                st.rerun()

# 4. IMPRESIÓN
elif menu == "🖨️ Impresión":
    st.title("🖨️ Área de Impresión")
    # Mostrar máquinas y permitir iniciar trabajos
    msel = st.selectbox("Seleccione Máquina", MAQUINAS["IMPRESIÓN"])
    ops_pendientes = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", "IMPRESIÓN").execute().data
    
    if ops_pendientes:
        op_sel = st.selectbox("OP a procesar", [o['op'] for o in ops_pendientes])
        if st.button("▶️ INICIAR"):
            d_op = next(o for o in ops_pendientes if o['op'] == op_sel)
            supabase.table("trabajos_activos").insert({
                "maquina": msel, "op": d_op['op'], "trabajo": d_op['trabajo'], "area": "IMPRESIÓN"
            }).execute()
            st.rerun()
