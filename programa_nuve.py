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

MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- MODALES ---
@st.dialog("Detalles de la Orden", width="large")
def mostrar_detalle_op(row):
    st.markdown(f"### 📄 Orden: {row['op']}")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"👤 **Cliente:** {row.get('nombre_cliente')}")
        st.write(f"🛠️ **Trabajo:** {row.get('trabajo')}")
    with col2:
        st.write(f"📏 **Medida:** {row.get('ancho_medida')}")
        st.write(f"🎨 **Tintas:** {row.get('cant_tintas')}")
    with col3:
        st.write(f"⚙️ **Área:** {row.get('proxima_area')}")
    if row.get('url_arte'):
        st.link_button("📂 VER ARTE", row['url_arte'], use_container_width=True)

@st.dialog("REPORTE TÉCNICO", width="large")
def modal_reporte_impresion(t, m_s, tipo="FINAL"):
    with st.form("f_reporte"):
        c1, c2 = st.columns(2)
        metros = c1.number_input("Metros Impresos", 0)
        operario = c2.text_input("Operario")
        if st.form_submit_button("GUARDAR"):
            data = {"op": t['op'], "maquina": m_s, "metros": metros, "operario": operario, "tipo_entrega": tipo}
            supabase.table("impresion").insert(data).execute()
            if tipo == "FINAL":
                sig = "CORTE" if t.get('tipo_acabado') == "RI" else "COLECTORAS"
                supabase.table("ordenes_planeadas").update({"proxima_area": sig, "estado": "Terminado"}).eq("op", t['op']).execute()
            supabase.table("trabajos_activos").delete().eq("maquina", m_s).execute()
            st.rerun()

@st.dialog("🚨 PARADA")
def modal_parada(t, m_s):
    motivo = st.selectbox("Motivo:", ["MECÁNICO", "ELÉCTRICO", "MATERIAL", "AJUSTE"])
    if st.button("CONFIRMAR"):
        supabase.table("trabajos_activos").update({"estado_maquina": "PARADA", "h_parada": datetime.now().strftime("%H:%M")}).eq("maquina", m_s).execute()
        st.rerun()

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("SISTEMA NUVE V10.2", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

if menu == "🖥️ Monitor":
    st.title("🏭 Monitor de Planta")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    d = act[m]
                    clase = "card-produccion" if d['estado_maquina'] == 'PRODUCIENDO' else "card-parada"
                    st.markdown(f"<div class='{clase}'><b>{m}</b><br>{d['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'>{m}<br>LIBRE</div>", unsafe_allow_html=True)
    time.sleep(20); st.rerun()

elif menu == "🔍 Seguimiento":
    st.title("🔍 Seguimiento")
    data = supabase.table("ordenes_planeadas").select("*").execute().data
    if data: st.table(pd.DataFrame(data)[['op', 'nombre_cliente', 'trabajo', 'proxima_area', 'estado']])

elif menu == "📅 Planificación":
    st.title("📅 Nueva Orden de Producción")
    
    st.markdown("### 1. Seleccione Tipo de Producto")
    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    
    # Manejo de selección con botones
    if col_b1.button("RI (Rollo Impreso)"): st.session_state.tipo_sel = "RI"
    if col_b2.button("RB (Rollo Blanco)"): st.session_state.tipo_sel = "RB"
    if col_b3.button("FRI (Forma Impresa)"): st.session_state.tipo_sel = "FRI"
    if col_b4.button("FRB (Forma Blanca)"): st.session_state.tipo_sel = "FRB"

    if "tipo_sel" in st.session_state:
        pref = st.session_state.tipo_sel
        st.info(f"Configurando: **{pref}**")
        
        with st.form("form_op", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            op_n = c1.text_input("Número de OP")
            cli = c2.text_input("Cliente")
            tra = c3.text_input("Trabajo")
            
            f1, f2, f3 = st.columns(3)
            mat = f1.text_input("Material")
            med = f2.text_input("Medida")
            can = f3.number_input("Cantidad", 0)
            
            pArea = "IMPRESIÓN" if "I" in pref else ("CORTE" if pref == "RB" else "COLECTORAS")
            
            if st.form_submit_button("🚀 REGISTRAR"):
                new_data = {
                    "op": f"{pref}-{op_n}".upper(),
                    "nombre_cliente": cli,
                    "trabajo": tra,
                    "tipo_acabado": pref,
                    "material": mat,
                    "ancho_medida": med,
                    "unidades_solicitadas": int(can),
                    "proxima_area": pArea,
                    "estado": "Pendiente"
                }
                try:
                    supabase.table("ordenes_planeadas").insert(new_data).execute()
                    st.success("✅ ¡Orden Guardada!")
                    del st.session_state.tipo_sel
                except Exception as e:
                    st.error(f"Error: {e}")

elif menu == "🖨️ Impresión":
    st.title("🖨️ Operaciones de Impresión")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", "IMPRESIÓN").execute().data}
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS["IMPRESIÓN"]):
        btn_label = f"🟢 {m}" if m in act else f"⚪ {m}"
        if cols[i%4].button(btn_label, key=m): st.session_state.m_sel = m
    
    if "m_sel" in st.session_state:
        ms = st.session_state.m_sel
        if ms not in act:
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", "IMPRESIÓN").execute().data
            if ops:
                sel_op = st.selectbox("Seleccione OP", [o['op'] for o in ops])
                if st.button(f"INICIAR {ms}"):
                    d = next(o for o in ops if o['op'] == sel_op)
                    supabase.table("trabajos_activos").insert({"maquina": ms, "area": "IMPRESIÓN", "op": d['op'], "trabajo": d['trabajo'], "estado_maquina": "PRODUCIENDO"}).execute()
                    st.rerun()
        else:
            t = act[ms]
            st.write(f"### Máquina {ms} trabajando en {t['op']}")
            c1, c2 = st.columns(2)
            if c1.button("🚨 PARADA"): modal_parada(t, ms)
            if c2.button("🏁 FINALIZAR"): modal_reporte_impresion(t, ms)

elif menu in ["✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    a_nom = menu.split(" ")[1].upper()
    st.title(a_nom)
    act_a = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", a_nom).execute().data}
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS[a_nom]):
        if cols[i%4].button(f"{'🔴' if m in act_a else '⚪'} {m}", key=m):
            if m in act_a:
                sig = "ENCUADERNACIÓN" if a_nom != "ENCUADERNACIÓN" else "DESPACHO"
                supabase.table("ordenes_planeadas").update({"proxima_area": sig}).eq("op", act_a[m]['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", m).execute()
                st.rerun()
            else:
                ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", a_nom).execute().data
                if ops:
                    o = ops[0] # Lógica simple: toma la primera disponible
                    supabase.table("trabajos_activos").insert({"maquina": m, "area": a_nom, "op": o['op'], "trabajo": o['trabajo']}).execute()
                    st.rerun()
