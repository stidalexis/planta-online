import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V24 PRO", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 10px; font-weight: bold; width: 100%; }
    .card-produccion { background-color: #E8F5E9; border-left: 8px solid #2E7D32; padding: 15px; border-radius: 12px; text-align: center; color: #1B5E20; }
    .card-parada { background-color: #FFEBEE; border-left: 8px solid #C62828; padding: 15px; border-radius: 12px; text-align: center; color: #B71C1C; }
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px; text-align: center; color: #9E9E9E; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)] + ["COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

def normalizar_tabla(t):
    mapping = {"IMPRESIÓN": "impresion", "CORTE": "corte", "COLECTORAS": "colectoras", "ENCUADERNACIÓN": "encuadernacion"}
    return mapping.get(t, t.lower())

# --- LÓGICA DE DATOS ---
# Corregimos el filtro de nulos para evitar el APIError
try:
    trabajos_raw = supabase.table("trabajos_activos").select("*").execute().data
    activos_dict = {a['maquina']: a for a in trabajos_raw}
except:
    activos_dict = {}

try:
    # CORRECCIÓN AQUÍ: Usamos filter eq 'null' o is_ 'null' sin espacios extra
    paradas_raw = supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data
    paradas_dict = {p['maquina']: p for p in paradas_raw}
except Exception as e:
    st.error(f"Error cargando paradas: {e}")
    paradas_dict = {}

# --- NAVEGACIÓN ---
with st.sidebar:
    st.title("🏭 NUVE V24 PRO")
    menu = st.radio("MENÚ", ["🖥️ Monitor", "📊 Consolidado", "🔍 Seguimiento OP", "📅 Planificación", "⏱️ Avance Corte", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# --- 1. MONITOR ---
if menu == "🖥️ Monitor":
    st.title("Monitor de Planta")
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in paradas_dict:
                    st.markdown(f"<div class='card-parada'>🚨 {m}<br>{paradas_dict[m]['motivo']}</div>", unsafe_allow_html=True)
                elif m in activos_dict:
                    st.markdown(f"<div class='card-produccion'>⚙️ {m}<br>OP: {activos_dict[m]['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'>{m}<br>DISPONIBLE</div>", unsafe_allow_html=True)
    if st.button("🔄 Refrescar"): st.rerun()

# --- 2. CONSOLIDADO ---
elif menu == "📊 Consolidado":
    st.title("📊 Consolidado de Producción")
    op_busqueda = st.text_input("Buscar OP específica")
    
    tab1, tab2 = st.tabs(["Historial por Área", "Seguimiento de Corte"])
    
    with tab1:
        area_sel = st.selectbox("Área", list(MAQUINAS.keys()))
        tabla = normalizar_tabla(area_sel)
        query = supabase.table(tabla).select("*")
        if op_busqueda: query = query.eq("op", op_busqueda)
        data = query.execute().data
        if data: st.dataframe(pd.DataFrame(data))
        else: st.warning("No hay registros en esta área.")

    with tab2:
        query_c = supabase.table("seguimiento_corte").select("*")
        if op_busqueda: query_c = query_c.eq("op", op_busqueda)
        data_c = query_c.execute().data
        if data_c: st.dataframe(pd.DataFrame(data_c))

# --- 3. MÓDULOS DE ÁREA (JOYSTICK) ---
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.title(f"Panel {area_act}")
    
    # Grilla de selección de máquina
    cols = st.columns(4)
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols[idx % 4]:
            if m in paradas_dict:
                if st.button(f"🚨 {m}", key=f"m_{m}"): st.session_state.m_sel = m
            elif m in activos_dict:
                if st.button(f"⚙️ {m}\n{activos_dict[m]['op']}", key=f"m_{m}"): st.session_state.m_sel = m
            else:
                if st.button(f"⚪ {m}", key=f"m_{m}"): st.session_state.m_sel = m

    # Interfaz de control
    if 'm_sel' in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        st.divider()
        st.subheader(f"Control Máquina: {m}")
        
        act = activos_dict.get(m)
        par = paradas_dict.get(m)

        if par:
            st.error(f"MÁQUINA PARADA: {par['motivo']}")
            if st.button("✅ REANUDAR TRABAJO"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.success("Máquina reactivada"); time.sleep(1); st.rerun()
        
        elif not act:
            # Iniciar nuevo trabajo
            ops_pendientes = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
            if ops_pendientes:
                with st.form("inicio"):
                    op_sel = st.selectbox("OP Pendiente", [o['op'] for o in ops_pendientes])
                    if st.form_submit_button("🚀 INICIAR OP"):
                        d = next(o for o in ops_pendientes if o['op'] == op_sel)
                        supabase.table("trabajos_activos").insert({
                            "maquina": m, "area": area_act, "op": d['op'], 
                            "trabajo": d['nombre_trabajo'], "hora_inicio": datetime.now().strftime("%H:%M")
                        }).execute()
                        st.rerun()
            else: st.info("No hay OPs pendientes para esta área.")
        
        else:
            # Trabajo en curso
            st.success(f"Produciendo OP: {act['op']}")
            c1, c2 = st.columns(2)
            with c1:
                with st.expander("🛑 PARADA TÉCNICA"):
                    mot = st.selectbox("Motivo", ["Mecánico", "Eléctrico", "Ajuste", "Material"])
                    if st.button("Registrar Parada"):
                        supabase.table("paradas_maquina").insert({
                            "maquina": m, "op": act['op'], "motivo": mot, "h_inicio": datetime.now().strftime("%H:%M")
                        }).execute()
                        st.rerun()
            with c2:
                with st.expander("🏁 FINALIZAR"):
                    op_nom = st.text_input("Operador")
                    if st.button("Completar y Pasar Siguiente Área"):
                        # Lógica de Bitácora y Siguiente Área
                        d_op = supabase.table("ordenes_planeadas").select("*").eq("op", act['op']).single().execute().data
                        n_area = "FINALIZADO"
                        if area_act == "IMPRESIÓN": n_area = "CORTE" if "ROLLOS" in d_op['tipo_orden'] else "COLECTORAS"
                        elif area_act == "COLECTORAS": n_area = "ENCUADERNACIÓN"

                        h = d_op.get('historial_procesos', [])
                        h.append({"area": area_act, "maquina": m, "operario": op_nom, "fecha": datetime.now().strftime("%d/%m/%Y")})
                        
                        supabase.table("ordenes_planeadas").update({"proxima_area": n_area, "historial_procesos": h}).eq("op", act['op']).execute()
                        supabase.table(normalizar_tabla(area_act)).insert({
                            "op": act['op'], "maquina": m, "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M")
                        }).execute()
                        supabase.table("trabajos_activos").delete().eq("maquina", m).execute()
                        st.rerun()

# --- 4. PLANIFICACIÓN Y OTROS ---
elif menu == "📅 Planificación":
    st.title("Nueva Planificación")
    with st.form("plan"):
        op = st.text_input("Número OP")
        cli = st.text_input("Cliente")
        trab = st.text_input("Trabajo")
        tipo = st.selectbox("Tipo", ["ROLLOS IMPRESOS", "FORMAS IMPRESAS", "ROLLOS BLANCOS"])
        if st.form_submit_button("Planificar"):
            supabase.table("ordenes_planeadas").insert({
                "op": op, "cliente": cli, "nombre_trabajo": trab, "tipo_orden": tipo, 
                "proxima_area": "IMPRESIÓN", "historial_procesos": []
            }).execute()
            st.success("Planificado")

elif menu == "⏱️ Avance Corte":
    st.title("Seguimiento de Corte")
    with st.form("avance"):
        m_c = st.selectbox("Máquina", MAQUINAS["CORTE"])
        op_c = st.text_input("OP")
        v = st.number_input("Varillas", 0)
        c = st.number_input("Cajas", 0)
        if st.form_submit_button("Guardar"):
            supabase.table("seguimiento_corte").insert({
                "maquina": m_c, "op": op_c, "varillas_acumuladas": v, "cajas_acumuladas": c
            }).execute()
            st.success("Guardado")
