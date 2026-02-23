import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE v2.0", page_icon="🏭", initial_sidebar_state="collapsed")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS RESPONSIVOS ---
st.markdown("""
    <style>
    .stButton > button { height: 85px !important; border-radius: 15px; font-weight: bold; font-size: 14px !important; border: 2px solid #0D47A1; margin-bottom: 10px; white-space: pre-wrap !important; }
    .card-proceso { padding: 12px; border-radius: 12px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; min-height: 90px; margin-bottom: 8px; font-size: 13px; }
    .card-parada { padding: 12px; border-radius: 12px; background-color: #FFEBEE; border-left: 8px solid #C62828; min-height: 90px; margin-bottom: 8px; font-size: 13px; }
    .card-libre { padding: 12px; border-radius: 12px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; color: #757575; min-height: 90px; display: flex; align-items: center; justify-content: center; margin-bottom: 8px; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin: 15px 0; }
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
    try: return float(str(v).replace(',', '.'))
    except: return 0.0

# --- NAVEGACIÓN ---
opcion = st.sidebar.radio("MENÚ PRINCIPAL", ["🖥️ Monitor", "📊 Consolidado", "⏱️ Seguimiento", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# ==========================================
# 1. MONITOR GENERAL
# ==========================================
if opcion == "🖥️ Monitor":
    st.markdown("### 🖥️ Estatus de Planta Detallado")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
    
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(2)
        for idx, m in enumerate(lista):
            with cols[idx % 2]:
                if m in paradas:
                    st.markdown(f"<div class='card-parada'>🚨 <b>{m}</b><br>DETENIDO: {paradas[m]['motivo']}<br>OP: {paradas[m]['op']}</div>", unsafe_allow_html=True)
                elif m in activos:
                    st.markdown(f"<div class='card-proceso'>⚙️ <b>{m}</b><br>OP: {activos[m]['op']}<br>TRABAJO: {activos[m]['trabajo']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-libre'>⚪ {m}<br>LIBRE</div>", unsafe_allow_html=True)

# ==========================================
# 2. SEGUIMIENTO HORARIO (BOTONES)
# ==========================================
elif opcion == "⏱️ Seguimiento":
    st.markdown("### ⏱️ Registro de Progreso Horario")
    cols_s = st.columns(3)
    for i, m_btn in enumerate(MAQUINAS["CORTE"]):
        if cols_s[i % 3].button(m_btn, key=f"s_{m_btn}", use_container_width=True):
            st.session_state.m_seg = m_btn
            
    if "m_seg" in st.session_state:
        m = st.session_state.m_seg
        st.info(f"Reportando para: **{m}**")
        with st.form("form_seg_h"):
            op_s = st.text_input("OP")
            tr_s = st.text_input("Nombre del Trabajo")
            c1, c2 = st.columns(2)
            med_s = c1.text_input("Medida Rollo")
            met_s = c2.number_input("Metros por Rollo", 0.0)
            k1, k2, k3 = st.columns(3)
            var_s = k1.number_input("Varillas", 0)
            caj_s = k2.number_input("Cajas", 0)
            des_s = k3.number_input("Desp. Kg", 0.0)
            
            if st.form_submit_button("GUARDAR REPORTE", use_container_width=True):
                h = datetime.now().hour
                turno = "MAÑANA" if 6 <= h < 14 else "TARDE"
                payload = {"maquina": m, "op": op_s, "trabajo": tr_s, "medida_rollo": med_s, "metros_rollo": met_s, "varillas_acumuladas": int(var_s), "cajas_acumuladas": int(caj_s), "desperidicio_acumulado": des_s, "turno": turno}
                supabase.table("seguimiento_corte").insert(payload).execute()
                st.success("Progreso guardado.")

# ==========================================
# 3. CONSOLIDADO
# ==========================================
elif opcion == "📊 Consolidado":
    st.markdown("### 📊 Tablero Gerencial")
    try:
        imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
        cor = pd.DataFrame(supabase.table("corte").select("*").execute().data)
        col = pd.DataFrame(supabase.table("colectoras").select("*").execute().data)
        enc = pd.DataFrame(supabase.table("encuadernacion").select("*").execute().data)
        
        t1, t2, t3, t4 = st.tabs(["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])
        with t1: st.dataframe(imp, use_container_width=True)
        with t2: st.dataframe(cor, use_container_width=True)
        with t3: st.dataframe(col, use_container_width=True)
        with t4: st.dataframe(enc, use_container_width=True)
    except: st.info("Sincronizando con base de datos...")

# ==========================================
# 4. JOYSTICKS DE ÁREA
# ==========================================
else:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_act = area_map[opcion]
    st.markdown(f"### 🕹️ Joystick: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    cols_j = st.columns(2)
    for i, m in enumerate(MAQUINAS[area_act]):
        lbl = f"⚙️ {m}\nOP: {activos[m]['op']}" if m in activos else (f"🚨 {m}\nDETENIDO" if m in paradas else f"⚪ {m}\nLIBRE")
        if cols_j[i % 2].button(lbl, key=f"j_{m}", use_container_width=True):
            st.session_state.m_sel = m

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        act, par = activos.get(m), paradas.get(m)

        if par:
            st.error(f"Máquina {m} en Parada")
            if st.button("REANUDAR TRABAJO", use_container_width=True):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()
        elif not act:
            with st.form("ini"):
                st.subheader(f"🚀 Iniciar {m}")
                op_i, tr_i = st.text_input("Número de OP"), st.text_input("Trabajo")
                ext = {}
                if area_act == "IMPRESIÓN":
                    c1, c2 = st.columns(2)
                    ext = {"tipo_papel": c1.text_input("Papel"), "ancho": c1.text_input("Ancho"), "gramaje": c2.text_input("Gramaje"), "medida_trabajo": c2.text_input("Medida")}
                elif area_act == "CORTE":
                    ext = {"tipo_papel": st.text_input("Papel"), "img_varilla": st.number_input("Imágenes/Varilla", 0), "unidades_caja": st.number_input("Und/Caja", 0)}
                elif area_act == "COLECTORAS":
                    ext = {"tipo_papel": st.text_input("Papel"), "medida_trabajo": st.text_input("Medida"), "unidades_caja": st.number_input("Und/Caja", 0)}
                elif area_act == "ENCUADERNACIÓN":
                    ext = {"formas_totales": st.number_input("Formas", 0), "material": st.text_input("Material"), "medida": st.text_input("Medida")}
                
                if st.form_submit_button("COMENZAR", use_container_width=True):
                    d = {"maquina": m, "op": op_i, "trabajo": tr_i, "area": area_act, "hora_inicio": datetime.now().strftime("%H:%M")}
                    d.update(ext)
                    supabase.table("trabajos_activos").insert(d).execute()
                    st.rerun()
        else:
            if st.button("🚨 REGISTRAR PARADA", use_container_width=True):
                mot = st.selectbox("Motivo", ["Mecánico", "Eléctrico", "Limp.", "Ajuste", "Falta Material"])
                supabase.table("paradas_maquina").insert({"maquina":m, "op": act['op'], "motivo": mot, "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                st.rerun()
            
            with st.form("fin"):
                st.subheader(f"🏁 Finalizar {m}")
                res = {}
                if area_act == "IMPRESIÓN":
                    res = {"metros_impresos": st.number_input("Metros", 0.0), "bobinas": st.number_input("Bobinas", 0)}
                elif area_act == "CORTE":
                    res = {"total_rollos": st.number_input("Total Rollos", 0), "cant_varillas": st.number_input("Varillas", 0), "medida_rollos": st.text_input("Medida Rollos")}
                elif area_act == "COLECTORAS":
                    res = {"total_cajas": st.number_input("Total Cajas", 0), "total_formas": st.number_input("Total Formas", 0)}
                elif area_act == "ENCUADERNACIÓN":
                    res = {"cant_final": st.number_input("Unidades Finales", 0), "presentacion": st.text_input("Presentación")}
                
                dk = st.number_input("Desperdicio Kg", 0.0); mot_d = st.text_input("Motivo Desp."); obs = st.text_area("Observaciones")
                
                if st.form_submit_button("GUARDAR HISTORIAL", use_container_width=True):
                    final = {
                        "op": act['op'], "maquina": m, "trabajo": act['trabajo'], 
                        "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"), 
                        "desp_kg": dk, "motivo_desperdicio": mot_d, "observaciones": obs
                    }
                    # HERENCIA DE DATOS (Mismo nombre que en SQL)
                    campos = ["tipo_papel", "ancho", "gramaje", "medida_trabajo", "img_varilla", "unidades_caja", "formas_totales", "material", "medida"]
                    for c in campos:
                        if c in act: final[c] = act[c]
                    final.update(res)
                    
                    try:
                        supabase.table(normalizar(area_act)).insert(final).execute()
                        supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                        st.success("Guardado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
