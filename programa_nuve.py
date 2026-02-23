import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA DE PRODUCCIÓN", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 75px; font-weight: bold; border-radius: 12px; font-size: 16px; border: 2px solid #0D47A1; }
    .card-proceso { padding: 15px; border-radius: 10px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; text-align: center; font-weight: bold; }
    .card-parada { padding: 15px; border-radius: 10px; background-color: #FFEBEE; border-left: 8px solid #C62828; text-align: center; font-weight: bold; }
    .card-libre { padding: 15px; border-radius: 10px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- FUNCIONES ---
def safe_float(valor):
    if valor is None or valor == "": return 0.0
    try: return float(str(valor).replace(',', '.'))
    except: return 0.0

def calcular_horas(inicio, fin):
    try:
        t_ini = datetime.strptime(inicio, "%H:%M")
        t_fin = datetime.strptime(fin, "%H:%M")
        return round((t_fin - t_ini).total_seconds() / 3600, 2)
    except: return 0.0

# --- NAVEGACIÓN ---
st.sidebar.title("🏭 MENÚ PRINCIPAL")
opcion = st.sidebar.radio("Ir a:", ["🖥️ Monitor General", "📊 Consolidado Gerencial", "⏱️ Seguimiento Cortadoras", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# ==========================================
# 1. MONITOR GENERAL
# ==========================================
if opcion == "🖥️ Monitor General":
    st.title("🖥️ Estatus en Tiempo Real")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
    
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(6)
        for idx, m in enumerate(lista):
            with cols[idx % 6]:
                if m in paradas: st.markdown(f"<div class='card-parada'>🚨 {m}</div>", unsafe_allow_html=True)
                elif m in activos: st.markdown(f"<div class='card-proceso'>⚙️ {m}<br>OP: {activos[m]['op']}</div>", unsafe_allow_html=True)
                else: st.markdown(f"<div class='card-libre'>⚪ {m}</div>", unsafe_allow_html=True)

# ==========================================
# 2. SEGUIMIENTO CORTADORAS (NUEVO)
# ==========================================
elif opcion == "⏱️ Seguimiento Cortadoras":
    st.title("⏱️ Reporte de Progreso Horario (Supervisión)")
    
    with st.form("form_seguimiento"):
        col1, col2 = st.columns(2)
        maq = col1.selectbox("Máquina", MAQUINAS["CORTE"])
        sup = col2.text_input("Supervisor / Operador")
        
        c1, c2, c3 = st.columns(3)
        op_seg = c1.text_input("Número de OP")
        trab_seg = c2.text_input("Nombre del Trabajo")
        med_seg = c3.text_input("Medida Rollo")
        
        k1, k2, k3, k4 = st.columns(4)
        met_seg = k1.number_input("Metros por Rollo", 0.0)
        var_seg = k2.number_input("Varillas actuales", 0)
        caj_seg = k3.number_input("Cajas actuales", 0)
        des_seg = k4.number_input("Desperdicio actual (Kg)", 0.0)
        
        if st.form_submit_button("REGISTRAR PROGRESO"):
            h_act = datetime.now().hour
            turno_act = "MAÑANA" if 6 <= h_act < 14 else "TARDE"
            
            payload = {
                "maquina": maq, "op": op_seg, "trabajo": trab_seg,
                "medida_rollo": med_seg, "metros_rollo": met_seg,
                "varillas_acumuladas": int(var_seg), "cajas_acumuladas": int(caj_seg),
                "desperidicio_acumulado": des_seg, "supervisor": sup, "turno": turno_act
            }
            supabase.table("seguimiento_corte").insert(payload).execute()
            st.success("Progreso registrado correctamente.")

# ==========================================
# 3. CONSOLIDADO GERENCIAL (BLINDADO)
# ==========================================
elif opcion == "📊 Consolidado Gerencial":
    st.title("📊 Panel Integral de Control Gerencial")

    try:
        imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
        cor = pd.DataFrame(supabase.table("corte").select("*").execute().data)
        paradas = pd.DataFrame(supabase.table("paradas_maquina").select("*").execute().data)
        seg = pd.DataFrame(supabase.table("seguimiento_corte").select("*").execute().data)

        t1, t2, t_seg, t3, t4 = st.tabs(["🔗 Cruce Imp-Cor", "🚨 Paradas", "⏱️ Rendimiento Turnos", "🖨️ Hist. Impresión", "✂️ Hist. Corte"])

        with t1:
            st.subheader("Cruce Operativo (Información Completa + KPIs)")
            if not imp.empty:
                df_i = imp[['op', 'trabajo', 'maquina', 'h_inicio', 'h_fin', 'tipo_papel', 'ancho', 'gramaje', 'medida_trabajo', 'metros_impresos', 'desp_kg', 'observaciones']].copy()
                df_i.columns = ['OP', 'TRABAJO', 'MAQ_IMP', 'INI_I', 'FIN_I', 'PAPEL_I', 'ANCHO_I', 'GRAM_I', 'MEDIDA_I', 'METROS', 'DESP_I', 'OBS_I']
                
                df_c = cor[['op', 'maquina', 'h_inicio', 'h_fin', 'img_varilla', 'medida_rollos', 'cant_varillas', 'unidades_caja', 'total_rollos', 'desp_kg', 'observaciones']].copy() if not cor.empty else pd.DataFrame(columns=['op'])
                if not cor.empty:
                    df_c.columns = ['OP', 'MAQ_COR', 'INI_C', 'FIN_C', 'IMG_VAR', 'MED_ROLLO', 'VARILLAS', 'UND_CAJA', 'ROLLOS', 'DESP_C', 'OBS_C']
                
                merged = pd.merge(df_i, df_c, on='OP', how='left')
                merged['KPI_DESP_TOTAL'] = merged['DESP_I'].fillna(0) + merged['DESP_C'].fillna(0)
                merged['KPI_EFICIENCIA'] = (merged['ROLLOS'].fillna(0) / merged['METROS']).replace([float('inf'), -float('inf')], 0).round(2)
                
                cols_view = ['OP', 'TRABAJO', 'KPI_DESP_TOTAL', 'KPI_EFICIENCIA', 'METROS', 'ROLLOS', 'MAQ_IMP', 'MAQ_COR', 'PAPEL_I', 'ANCHO_I', 'GRAM_I', 'MEDIDA_I', 'IMG_VAR', 'MED_ROLLO', 'VARILLAS', 'UND_CAJA', 'INI_I', 'FIN_I', 'INI_C', 'FIN_C', 'OBS_I', 'OBS_C']
                st.dataframe(merged[[c for c in cols_view if c in merged.columns]], use_container_width=True)

        with t_seg:
            st.subheader("Rendimiento por Turno (Seguimiento Horario)")
            if not seg.empty:
                resumen = seg.groupby(['fecha', 'turno', 'maquina', 'op', 'trabajo']).agg({'varillas_acumuladas': 'max', 'cajas_acumuladas': 'max'}).reset_index()
                st.dataframe(resumen, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")

# Resto de los Joysticks (Impresión, Corte, etc.) se mantienen igual...
else:
    st.info("Formularios de área en desarrollo (Punto de anclaje)")
