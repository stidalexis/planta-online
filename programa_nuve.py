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

# --- FUNCIONES AUXILIARES ---
def normalizar(texto):
    reemplazos = {"Í": "I", "Ó": "O", "Á": "A", "É": "E", "Ú": "U", " ": "_"}
    t = texto.upper()
    for k, v in reemplazos.items(): t = t.replace(k, v)
    return t.lower()

def safe_float(valor):
    if valor is None or valor == "": return 0.0
    try: return float(str(valor).replace(',', '.'))
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
# 2. SEGUIMIENTO CORTADORAS (PROGRESO HORARIO)
# ==========================================
elif opcion == "⏱️ Seguimiento Cortadoras":
    st.title("⏱️ Seguimiento de Rendimiento por Máquina")
    with st.form("form_seg"):
        c1, c2, c3 = st.columns(3)
        maq_s = c1.selectbox("Máquina", MAQUINAS["CORTE"])
        op_s = c2.text_input("Número de OP")
        tr_s = c3.text_input("Nombre del Trabajo")
        
        k1, k2, k3, k4, k5 = st.columns(5)
        med_s = k1.text_input("Medida Rollo")
        met_s = k2.number_input("Metros Rollo", 0.0)
        var_s = k3.number_input("Varillas actuales", 0)
        caj_s = k4.number_input("Cajas actuales", 0)
        des_s = k5.number_input("Desp. acumulado (Kg)", 0.0)
        
        if st.form_submit_button("REGISTRAR PROGRESO"):
            h = datetime.now().hour
            t_act = "MAÑANA" if 6 <= h < 14 else "TARDE"
            payload = {
                "maquina": maq_s, "op": op_s, "trabajo": tr_s, "medida_rollo": med_s,
                "metros_rollo": met_s, "varillas_acumuladas": var_s, "cajas_acumuladas": caj_s,
                "desperidicio_acumulado": des_s, "turno": t_act
            }
            supabase.table("seguimiento_corte").insert(payload).execute()
            st.success(f"Reporte guardado en turno {t_act}")

# ==========================================
# 3. CONSOLIDADO GERENCIAL (BLINDADO)
# ==========================================
elif opcion == "📊 Consolidado Gerencial":
    st.title("📊 Panel Integral de Control Gerencial")
    try:
        imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
        cor = pd.DataFrame(supabase.table("corte").select("*").execute().data)
        col = pd.DataFrame(supabase.table("colectoras").select("*").execute().data)
        enc = pd.DataFrame(supabase.table("encuadernacion").select("*").execute().data)
        seg = pd.DataFrame(supabase.table("seguimiento_corte").select("*").execute().data)

        t1, t_seg, t3, t4, t5, t6 = st.tabs(["🔗 Cruce Imp-Cor", "⏱️ Rendimiento Turnos", "🖨️ Hist. Impresión", "✂️ Hist. Corte", "📥 Colectoras", "📕 Encuadernación"])

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
                
                cols_v = ['OP', 'TRABAJO', 'KPI_DESP_TOTAL', 'KPI_EFICIENCIA', 'METROS', 'ROLLOS', 'MAQ_IMP', 'MAQ_COR', 'PAPEL_I', 'ANCHO_I', 'GRAM_I', 'MEDIDA_I', 'IMG_VAR', 'MED_ROLLO', 'VARILLAS', 'UND_CAJA', 'INI_I', 'FIN_I', 'INI_C', 'FIN_C']
                st.dataframe(merged[[c for c in cols_v if c in merged.columns]], use_container_width=True)

        with t_seg:
            st.subheader("Rendimiento por Turno (Cierre Automático)")
            if not seg.empty:
                res = seg.groupby(['fecha', 'turno', 'maquina', 'op', 'trabajo']).agg({'varillas_acumuladas': 'max', 'cajas_acumuladas': 'max', 'desperidicio_acumulado': 'max'}).reset_index()
                st.dataframe(res, use_container_width=True)

        with t3: st.dataframe(imp, use_container_width=True)
        with t4: st.dataframe(cor, use_container_width=True)
        with t5: st.dataframe(col, use_container_width=True)
        with t6: st.dataframe(enc, use_container_width=True)

    except Exception as e:
        st.error(f"Error de carga: {e}")

# ==========================================
# 4. JOYSTICKS DE ÁREA (UNIFICADO)
# ==========================================
else:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_act = area_map[opcion]
    st.title(f"Operación: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    # SELECCIÓN DE MÁQUINA
    cols_m = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS[area_act]):
        lbl = m_btn
        if m_btn in paradas: lbl = f"🚨 {m_btn}"
        elif m_btn in activos: lbl = f"⚙️ {m_btn}\nOP: {activos[m_btn]['op']}"
        if cols_m[i % 4].button(lbl, key=f"j_{m_btn}", use_container_width=True):
            st.session_state.m_sel = m_btn

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        act, par = activos.get(m), paradas.get(m)

        if par:
            if st.button("REANUDAR"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()
        elif not act:
            with st.form("ini"):
                st.subheader(f"🚀 Iniciar en {m}")
                c1, c2 = st.columns(2)
                op_i, tr_i = c1.text_input("OP"), c2.text_input("Trabajo")
                ext = {}
                if area_act == "IMPRESIÓN":
                    k1, k2, k3 = st.columns(3); ext = {"tipo_papel": k1.text_input("Papel"), "ancho": k2.text_input("Ancho"), "gramaje": k3.text_input("Gramaje")}
                elif area_act == "CORTE":
                    k1, k2 = st.columns(2); ext = {"tipo_papel": k1.text_input("Papel"), "img_varilla": k2.number_input("Img/Varilla", 0)}
                elif area_act == "COLECTORAS":
                    k1, k2 = st.columns(2); ext = {"tipo_papel": k1.text_input("Papel"), "unidades_caja": k2.number_input("Und/Caja", 0)}
                elif area_act == "ENCUADERNACIÓN":
                    k1, k2 = st.columns(2); ext = {"material": k1.text_input("Material"), "medida": k2.text_input("Medida")}
                
                if st.form_submit_button("INICIAR"):
                    data = {"maquina": m, "op": op_i, "trabajo": tr_i, "area": area_act, "hora_inicio": datetime.now().strftime("%H:%M")}
                    data.update(ext)
                    supabase.table("trabajos_activos").insert(data).execute()
                    st.rerun()
        else:
            if st.button("🚨 PARADA"):
                mot = st.selectbox("Motivo", ["Mecánico", "Eléctrico", "Cambio Material", "Limpieza"])
                supabase.table("paradas_maquina").insert({"maquina": m, "op": act['op'], "motivo": mot, "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                st.rerun()

            with st.form("fin"):
                st.subheader(f"🏁 Finalizar OP: {act['op']}")
                res = {}
                if area_act == "IMPRESIÓN":
                    f1, f2 = st.columns(2); res = {"metros_impresos": f1.number_input("Metros", 0.0), "bobinas": f2.number_input("Bobinas", 0)}
                elif area_act == "CORTE":
                    f1, f2 = st.columns(2); res = {"total_rollos": f1.number_input("Rollos", 0), "cant_varillas": f2.number_input("Varillas", 0)}
                elif area_act == "COLECTORAS":
                    f1, f2 = st.columns(2); res = {"total_cajas": f1.number_input("Cajas", 0), "total_formas": f2.number_input("Formas", 0)}
                elif area_act == "ENCUADERNACIÓN":
                    f1, f2 = st.columns(2); res = {"cant_final": f1.number_input("Cantidad Final", 0), "presentacion": f2.text_input("Presentación")}
                
                dk = st.number_input("Desp. Kg", 0.0)
                obs = st.text_input("Observaciones")
                
                if st.form_submit_button("FINALIZAR"):
                    final_data = {"op": act['op'], "maquina": m, "trabajo": act['trabajo'], "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"), "desp_kg": dk, "observaciones": obs}
                    final_data.update(res)
                    supabase.table(normalizar(area_act)).insert(final_data).execute()
                    supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                    st.rerun()
