import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V28", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("Error de conexión. Verifica los Secrets de Streamlit.")
    st.stop()

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; font-size: 18px !important; width: 100%; }
    .title-area { background-color: #0D47A1; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 22px; margin-bottom: 20px; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 20px; border-radius: 15px; text-align: center; color: #1B5E20; font-weight: bold; font-size: 18px; margin-bottom: 10px; }
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 20px; border-radius: 15px; text-align: center; color: #9E9E9E; font-size: 16px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}
PRESENTACIONES = ["LIBRETAS TAPADURA", "BLOCK LICOM", "HOJAS SUELTAS", "PAQUETES", "TACOS", "CAJAS", "ROLLOS"]

# --- ESTADOS DE SESIÓN ---
if 'sel_tipo' not in st.session_state: st.session_state.sel_tipo = None
if 'detalle_op_id' not in st.session_state: st.session_state.detalle_op_id = None
if 'rep' not in st.session_state: st.session_state.rep = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🏭 NUVE V28")
    menu = st.radio("MÓDULOS", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# --- MONITOR ---
if menu == "🖥️ Monitor":
    st.title("Monitor de Planta")
    res_act = supabase.table("trabajos_activos").select("*").execute()
    act = {a['maquina']: a for a in res_act.data}
    
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    st.markdown(f"<div class='card-produccion'>{m}<br>OP: {act[m]['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'>{m}<br>LIBRE</div>", unsafe_allow_html=True)
    time.sleep(30); st.rerun()

# --- SEGUIMIENTO ---
elif menu == "🔍 Seguimiento":
    st.title("Seguimiento de Órdenes")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if res:
        df = pd.DataFrame(res)
        for _, row in df.iterrows():
            with st.expander(f"OP: {row['op']} - {row['cliente']} ({row['proxima_area']})"):
                st.write(f"**Trabajo:** {row['nombre_trabajo']}")
                if row['historial_procesos']:
                    for p in row['historial_procesos']:
                        st.info(f"📍 {p['fecha']} - {p['area']} ({p['maquina']}) - Operario: {p['operario']}")

# --- PLANIFICACIÓN ---
elif menu == "📅 Planificación":
    st.title("Nueva Orden")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📑 FORMAS IMPRESAS"): st.session_state.sel_tipo = "FORMAS IMPRESAS"
    if c2.button("📄 FORMAS BLANCAS"): st.session_state.sel_tipo = "FORMAS BLANCAS"
    if c3.button("🌀 ROLLOS IMPRESOS"): st.session_state.sel_tipo = "ROLLOS IMPRESOS"
    if c4.button("⚪ ROLLOS BLANCOS"): st.session_state.sel_tipo = "ROLLOS BLANCOS"

    if st.session_state.sel_tipo:
        t = st.session_state.sel_tipo
        with st.form("form_plan"):
            st.subheader(f"Registro: {t}")
            op_n = st.text_input("Número de OP").upper()
            cli = st.text_input("Cliente")
            trab = st.text_input("Nombre Trabajo")
            
            # Lógica simplificada para pruebas
            if "FORMAS" in t:
                cant = st.number_input("Cantidad", 0)
                ruta_init = "IMPRESIÓN" if "IMPRESAS" in t else "COLECTORAS"
            else:
                cant = st.number_input("Cantidad Rollos", 0)
                ruta_init = "IMPRESIÓN" if "IMPRESOS" in t else "CORTE"

            if st.form_submit_button("🚀 GUARDAR"):
                payload = {"op": op_n, "cliente": cli, "nombre_trabajo": trab, "tipo_orden": t, "proxima_area": ruta_init}
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.success("Orden Guardada"); time.sleep(1); st.rerun()

# --- PRODUCCIÓN ---
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.markdown(f"<div class='title-area'>PANEL: {area_act}</div>", unsafe_allow_html=True)
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    
    cols = st.columns(3)
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols[idx % 3]:
            if m in activos:
                st.markdown(f"<div class='card-produccion'>🟡 {m}<br>OP: {activos[m]['op']}</div>", unsafe_allow_html=True)
                if st.button(f"✅ FINALIZAR", key=f"f_{m}"):
                    st.session_state.rep = activos[m]
                    st.rerun()
            else:
                st.markdown(f"<div class='card-vacia'>⚪ {m}<br>LIBRE</div>", unsafe_allow_html=True)
                ops_disp = supabase.table("ordenes_planeadas").select("op").eq("proxima_area", area_act).execute().data
                if ops_disp:
                    sel_op = st.selectbox("OP", [o['op'] for o in ops_disp], key=f"sel_{m}")
                    if st.button(f"🚀 INICIAR", key=f"btn_{m}"):
                        supabase.table("trabajos_activos").insert({"maquina": m, "area": area_act, "op": sel_op, "hora_inicio": datetime.now().isoformat()}).execute()
                        st.rerun()

    if st.session_state.rep:
        r = st.session_state.rep
        with st.form("cierre"):
            st.warning(f"CIERRE TÉCNICO: {r['op']}")
            operario = st.text_input("Operario")
            desp = st.number_input("Desperdicio", 0.0)
            
            if st.form_submit_button("🏁 FINALIZAR"):
                # --- SOLUCIÓN AL ERROR DE FECHA ---
                try:
                    inicio = pd.to_datetime(r['hora_inicio']).tz_localize(None)
                    fin = datetime.now()
                    duracion = str(fin - inicio).split('.')[0]
                except:
                    duracion = "N/D"
                
                # Cargar datos actuales
                d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                
                # Definir siguiente área
                flujo = {"IMPRESIÓN": "COLECTORAS", "COLECTORAS": "ENCUADERNACIÓN", "ENCUADERNACIÓN": "FINALIZADO", "CORTE": "FINALIZADO"}
                if "ROLLOS" in d_op['tipo_orden'] and area_act == "IMPRESIÓN": n_area = "CORTE"
                else: n_area = flujo.get(area_act, "FINALIZADO")

                # Historial
                h = d_op.get('historial_procesos', []) or []
                h.append({"area": area_act, "maquina": r['maquina'], "operario": operario, "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "duracion": duracion})
                
                supabase.table("ordenes_planeadas").update({"proxima_area": n_area, "historial_processes": h}).eq("op", r['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()
                st.session_state.rep = None
                st.success("¡Hecho!"); time.sleep(1); st.rerun()
