import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V5 - TOTAL", page_icon="🏭", initial_sidebar_state="collapsed")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stButton > button { height: 85px !important; border-radius: 15px; font-weight: bold; font-size: 14px !important; border: 2px solid #0D47A1; margin-bottom: 10px; white-space: pre-wrap !important; }
    .card-proceso { padding: 12px; border-radius: 12px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; min-height: 100px; margin-bottom: 10px; font-size: 13px; }
    .card-parada { padding: 12px; border-radius: 12px; background-color: #FFEBEE; border-left: 8px solid #C62828; min-height: 100px; margin-bottom: 10px; font-size: 13px; }
    .card-libre { padding: 12px; border-radius: 12px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; color: #757575; min-height: 100px; display: flex; align-items: center; justify-content: center; margin-bottom: 10px; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin: 15px 0; font-size: 18px; }
    [data-testid="column"] { width: 100% !important; flex: 1 1 calc(50% - 10px) !important; min-width: 150px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- DATOS MAESTROS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

def normalizar(t):
    for k, v in {"Í":"I","Ó":"O","Á":"A","É":"E","Ú":"U"," ":"_"}.items(): t = t.upper().replace(k,v)
    return t.lower()

def safe_float(v):
    if v is None or v == "": return 0.0
    try: return float(str(v).replace(',', '.'))
    except: return 0.0

# --- NAVEGACIÓN ---
opcion = st.sidebar.radio("MENÚ", ["🖥️ Monitor", "📊 Consolidado", "⏱️ Seguimiento", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# ==========================================
# 1. MONITOR
# ==========================================
if opcion == "🖥️ Monitor":
    st.title("🖥️ Monitor de Planta")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
    
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(2)
        for idx, m in enumerate(lista):
            with cols[idx % 2]:
                if m in paradas: st.markdown(f"<div class='card-parada'>🚨 <b>{m}</b><br>PARADA: {paradas[m]['motivo']}<br>OP: {paradas[m]['op']}</div>", unsafe_allow_html=True)
                elif m in activos: st.markdown(f"<div class='card-proceso'>⚙️ <b>{m}</b><br>OP: {activos[m]['op']}<br>{activos[m]['trabajo']}</div>", unsafe_allow_html=True)
                else: st.markdown(f"<div class='card-libre'>⚪ {m}<br>LIBRE</div>", unsafe_allow_html=True)

# ==========================================
# 2. CONSOLIDADO (CRUCE KPI COMPLETO)
# ==========================================
elif opcion == "📊 Consolidado":
    st.title("📊 Consolidado y Cruce Operativo")
    
    # Carga masiva de datos
    imp_data = supabase.table("impresion").select("*").execute().data
    cor_data = supabase.table("corte").select("*").execute().data
    col_data = supabase.table("colectoras").select("*").execute().data
    enc_data = supabase.table("encuadernacion").select("*").execute().data
    seg_data = supabase.table("seguimiento_corte").select("*").execute().data
    
    imp_df, cor_df = pd.DataFrame(imp_data), pd.DataFrame(cor_data)
    
    t0, t1, t2, t3, t4, t5 = st.tabs(["🔗 CRUCE KPI", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación", "⏱️ Seguimiento"])
    
    with t0:
        if not imp_df.empty and not cor_df.empty:
            # Preparar Impresión
            df_i = imp_df[['op', 'trabajo', 'maquina', 'tipo_papel', 'ancho', 'gramaje', 'metros_impresos', 'desp_kg', 'fecha_fin']].copy()
            df_i.columns = ['OP', 'TRABAJO', 'MAQ_IMP', 'PAPEL', 'ANCHO', 'GR', 'MET_IMP', 'DESP_IMP', 'FECHA']
            # Preparar Corte
            df_c = cor_df[['op', 'maquina', 'total_rollos', 'cant_varillas', 'desp_kg', 'medida_rollos']].copy()
            df_c.columns = ['OP', 'MAQ_COR', 'ROLLOS', 'VARILLAS', 'DESP_COR', 'MEDIDA']
            
            # Cruce
            cruce = pd.merge(df_i, df_c, on='OP', how='inner')
            cruce['DESP_TOT'] = cruce['DESP_IMP'].fillna(0) + cruce['DESP_COR'].fillna(0)
            cruce['EFIC_%'] = ((cruce['ROLLOS'] / cruce['MET_IMP']) * 100).replace([float('inf')], 0).round(2)
            
            # Métricas
            m1, m2, m3 = st.columns(3)
            m1.metric("Metros Impresos", f"{cruce['MET_IMP'].sum():,.0f}")
            m2.metric("Rollos Totales", f"{cruce['ROLLOS'].sum():,.0f}")
            m3.metric("Desp. Acumulado (Kg)", f"{cruce['DESP_TOT'].sum():,.1f}")
            
            st.dataframe(cruce, use_container_width=True)
        else:
            st.info("Faltan datos en Impresión o Corte para generar el cruce.")

    with t1: st.dataframe(imp_df, use_container_width=True)
    with t2: st.dataframe(cor_df, use_container_width=True)
    with t3: st.dataframe(pd.DataFrame(col_data), use_container_width=True)
    with t4: st.dataframe(pd.DataFrame(enc_data), use_container_width=True)
    with t5: st.dataframe(pd.DataFrame(seg_data), use_container_width=True)

# ==========================================
# 3. SEGUIMIENTO
# ==========================================
elif opcion == "⏱️ Seguimiento":
    st.title("⏱️ Seguimiento Cortadoras")
    cols_s = st.columns(3)
    for i, m_btn in enumerate(MAQUINAS["CORTE"]):
        if cols_s[i % 3].button(m_btn, key=f"s_{m_btn}"): st.session_state.m_seg = m_btn
    if "m_seg" in st.session_state:
        m = st.session_state.m_seg
        with st.form("f_s"):
            st.subheader(f"Reporte: {m}")
            op, tr = st.text_input("OP"), st.text_input("Trabajo")
            c1, c2 = st.columns(2)
            med, met = c1.text_input("Medida"), c2.number_input("Metros/Rollo", 0.0)
            k1, k2, k3 = st.columns(3)
            v, c, d = k1.number_input("Varillas", 0), k2.number_input("Cajas", 0), k3.number_input("Desp. Kg", 0.0)
            if st.form_submit_button("REGISTRAR"):
                turno = "MAÑANA" if 6 <= datetime.now().hour < 14 else "TARDE"
                supabase.table("seguimiento_corte").insert({"maquina":m,"op":op,"trabajo":tr,"medida_rollo":med,"metros_rollo":met,"varillas_acumuladas":int(v),"cajas_acumuladas":int(c),"desperidicio_acumulado":d,"turno":turno}).execute()
                st.success("Avance guardado.")

# ==========================================
# 4. JOYSTICKS (CONTROL TOTAL)
# ==========================================
else:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_act = area_map[opcion]
    st.title(f"Joystick: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    cols_j = st.columns(2)
    for i, m in enumerate(MAQUINAS[area_act]):
        lbl = f"⚙️ {m}\nOP: {activos[m]['op']}" if m in activos else (f"🚨 {m}\nPARADA: {paradas[m]['motivo']}" if m in paradas else f"⚪ {m}\nLIBRE")
        if cols_j[i % 2].button(lbl, key=f"joy_{m}"): st.session_state.m_sel = m

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        act, par = activos.get(m), paradas.get(m)
        if par:
            if st.button("REANUDAR"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()
        elif not act:
            with st.form("ini"):
                st.subheader(f"🚀 Iniciar {m}")
                op_i, tr_i = st.text_input("OP"), st.text_input("Trabajo")
                ext = {}
                if area_act == "IMPRESIÓN":
                    c1, c2 = st.columns(2)
                    ext = {"tipo_papel": c1.text_input("Papel"), "ancho": c1.text_input("Ancho"), "gramaje": c2.text_input("Gramaje"), "medida_trabajo": c2.text_input("Medida")}
                elif area_act == "CORTE":
                    ext = {"tipo_papel": st.text_input("Papel"), "img_varilla": st.number_input("Img/Varilla", 0), "unidades_caja": st.number_input("Und/Caja", 0)}
                elif area_act == "COLECTORAS":
                    ext = {"tipo_papel": st.text_input("Papel"), "medida_trabajo": st.text_input("Medida"), "unidades_caja": st.number_input("Und/Caja", 0)}
                elif area_act == "ENCUADERNACIÓN":
                    ext = {"formas_totales": st.number_input("Formas", 0), "material": st.text_input("Material"), "medida": st.text_input("Medida")}
                if st.form_submit_button("COMENZAR"):
                    d = {"maquina":m,"op":op_i,"trabajo":tr_i,"area":area_act,"hora_inicio":datetime.now().strftime("%H:%M")}
                    d.update(ext); supabase.table("trabajos_activos").insert(d).execute(); st.rerun()
        else:
            if st.button("🛑 PARADA"):
                mot = st.selectbox("Motivo", ["Mecánico", "Eléctrico", "Limpieza", "Ajuste", "Falta Material"])
                supabase.table("paradas_maquina").insert({"maquina":m,"op":act['op'],"motivo":mot,"h_inicio":datetime.now().strftime("%H:%M")}).execute(); st.rerun()
            with st.form("fin"):
                st.subheader("🏁 Finalizar Trabajo")
                res = {}
                if area_act == "IMPRESIÓN": res = {"metros_impresos": st.number_input("Metros", 0.0), "bobinas": st.number_input("Bobinas", 0)}
                elif area_act == "CORTE": res = {"total_rollos": st.number_input("Rollos", 0), "cant_varillas": st.number_input("Varillas", 0), "medida_rollos": st.text_input("Medida Final Rollos")}
                elif area_act == "COLECTORAS": res = {"total_cajas": st.number_input("Cajas", 0), "total_formas": st.number_input("Formas", 0)}
                elif area_act == "ENCUADERNACIÓN": res = {"cant_final": st.number_input("Cantidad", 0), "presentacion": st.text_input("Presentación")}
                dk, mot_d, obs = st.number_input("Desp. Kg", 0.0), st.text_input("Motivo Desp."), st.text_area("Obs")
                if st.form_submit_button("GUARDAR"):
                    nom_t = normalizar(area_act)
                    final = {"op": act['op'], "maquina": m, "trabajo": act['trabajo'], "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"), "desp_kg": dk, "motivo_desperdicio": mot_d, "observaciones": obs}
                    cols_p = {"impresion": ["tipo_papel", "ancho", "gramaje", "medida_trabajo"], "corte": ["tipo_papel", "img_varilla", "unidades_caja"], "colectoras": ["tipo_papel", "medida_trabajo", "unidades_caja"], "encuadernacion": ["formas_totales", "material", "medida"]}
                    for col in cols_p.get(nom_t, []):
                        if col in act:
                            if col in ["ancho", "gramaje"]: final[col] = safe_float(act[col])
                            else: final[col] = act[col]
                    final.update(res)
                    try:
                        supabase.table(nom_t).insert(final).execute()
                        supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                        st.success("Guardado."); st.rerun()
                    except Exception as e: st.error(f"Error: {e}")
