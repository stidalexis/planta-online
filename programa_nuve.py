import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA DE PRODUCCIÓN V2", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 60px; font-weight: bold; border-radius: 12px; }
    .card-parada { padding: 15px; border-radius: 10px; background-color: #FFEBEE; border-left: 8px solid #C62828; text-align: center; }
    .card-proceso { padding: 15px; border-radius: 10px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; text-align: center; }
    .card-libre { padding: 15px; border-radius: 10px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; }
    </style>
    """, unsafe_allow_html=True)

# --- MÁQUINAS (Se mantiene igual al original) ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-PP-01"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 6)]
}

# --- FUNCIONES AUXILIARES ---
def safe_float(valor):
    try: return float(str(valor).replace(',', '.'))
    except: return 0.0

# ==========================================
# NAVEGACIÓN
# ==========================================
st.sidebar.title("🏭 MENÚ PLANTA")
seleccion = st.sidebar.radio("Ir a:", ["🖥️ Monitor General", "📊 Consolidado Gerencial", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# ==========================================
# 1. MONITOR GENERAL (CON PARADAS ACTUALIZADAS)
# ==========================================
if seleccion == "🖥️ Monitor General":
    st.title("🖥️ Estatus en Tiempo Real")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
    
    for area, lista in MAQUINAS.items():
        st.subheader(area)
        cols = st.columns(6)
        for idx, m in enumerate(lista):
            with cols[idx % 6]:
                if m in paradas:
                    st.markdown(f"<div class='card-parada'>🚨 {m}<br><small>{paradas[m]['motivo']}</small></div>", unsafe_allow_html=True)
                elif m in activos:
                    st.markdown(f"<div class='card-proceso'>⚙️ {m}<br>OP: {activos[m]['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-libre'>⚪ {m}<br><small>DISPONIBLE</small></div>", unsafe_allow_html=True)

# ==========================================
# 2. CONSOLIDADO GERENCIAL (TABLERO ANALÍTICO)
# ==========================================
elif seleccion == "📊 Consolidado Gerencial":
    st.title("📊 Indicadores Críticos")
    
    df_imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
    df_cor = pd.DataFrame(supabase.table("corte").select("*").execute().data)
    
    if not df_imp.empty:
        c1, c2, c3 = st.columns(3)
        total_desp = df_imp['desp_kg'].sum() + (df_cor['desp_kg'].sum() if not df_cor.empty else 0)
        c1.metric("Merma Total (Kg)", f"{round(total_desp, 2)}")
        c2.metric("OPs Finalizadas", len(df_imp))
        
        st.subheader("Eficiencia por Máquina (Impresión)")
        st.bar_chart(df_imp, x="maquina", y="desp_kg")
    else:
        st.info("Sin datos para mostrar indicadores.")

# ==========================================
# 3. JOYSTICK DE ÁREA (CON FLUJO Y PARADAS)
# ==========================================
else:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_actual = area_map[seleccion]
    st.title(f"Joystick: {area_actual}")
    
    # Cargar estado actual
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    # Selección de Máquina
    m = st.selectbox("Seleccione Máquina:", MAQUINAS[area_actual])
    act, par = activos.get(m), paradas.get(m)

    st.divider()

    # LOGICA DE PARADAS
    if par:
        st.error(f"🚨 MÁQUINA EN PARADA: {par['motivo']} (Desde: {par['h_inicio']})")
        if st.button("✅ REANUDAR PRODUCCIÓN", use_container_width=True):
            supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
            st.rerun()
    
    # LÓGICA DE TRABAJO
    elif not act:
        with st.form("inicio_trabajo"):
            st.subheader("🚀 Iniciar Nueva OP")
            
            # FLUJO INTELIGENTE PARA CORTE
            if area_actual == "CORTE":
                ops_imp = [d['op'] for d in supabase.table("impresion").select("op").execute().data]
                op = st.selectbox("Seleccionar OP terminada en Impresión", ops_imp)
                tr = st.text_input("Trabajo (Confirmar)")
            else:
                op = st.text_input("Número de OP")
                tr = st.text_input("Nombre del Trabajo")

            # Campos específicos según área
            extra = {}
            if area_actual == "IMPRESIÓN":
                c1, c2 = st.columns(2)
                extra = {"ancho": c1.number_input("Ancho (mm)", 0.0), "gramaje": c2.number_input("Gramaje", 0.0)}
            
            if st.form_submit_button("EMPEZAR TURNO"):
                if op and tr:
                    data = {"maquina": m, "op": op, "trabajo": tr, "area": area_actual, "hora_inicio": datetime.now().strftime("%H:%M")}
                    data.update(extra)
                    supabase.table("trabajos_activos").insert(data).execute()
                    st.rerun()
    else:
        # MÁQUINA TRABAJANDO: Mostrar Cierre y Botón de Parada
        st.success(f"Trabajando OP: {act['op']} - {act['trabajo']}")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("🚨 REGISTRAR PARADA", use_container_width=True):
                motivo = st.selectbox("Motivo:", ["Mecánico", "Eléctrico", "Limpia", "Material"], key="mot")
                supabase.table("paradas_maquina").insert({"maquina": m, "op": act['op'], "motivo": motivo, "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                st.rerun()
        
        with col_c2:
            with st.expander("🏁 FINALIZAR TRABAJO"):
                with st.form("cierre"):
                    dk = st.number_input("Desperdicio (Kg)", 0.0)
                    obs = st.text_input("Observaciones")
                    
                    res = {}
                    if area_actual == "IMPRESIÓN":
                        res = {"metros_impresos": st.number_input("Metros Totales", 0.0)}
                    elif area_actual == "CORTE":
                        res = {"total_rollos": st.number_input("Total Rollos", 0)}

                    if st.form_submit_button("CERRAR OP Y GUARDAR"):
                        final_data = {
                            "op": act['op'], "maquina": m, "trabajo": act['trabajo'],
                            "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                            "desp_kg": dk, "motivo_desperdicio": obs
                        }
                        final_data.update(res)
                        
                        # Mapeo de campos técnicos
                        if area_actual == "IMPRESIÓN":
                            final_data.update({"ancho": act['ancho'], "gramaje": act['gramaje']})

                        supabase.table(area_actual.lower()).insert(final_data).execute()
                        supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                        st.rerun()
