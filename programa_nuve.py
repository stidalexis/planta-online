import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA DE PRODUCCIÓN NUVE", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 80px; font-weight: bold; border-radius: 12px; font-size: 16px; border: 2px solid #0D47A1; margin-bottom: 10px; }
    .card-proceso { padding: 15px; border-radius: 10px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; text-align: center; }
    .card-parada { padding: 15px; border-radius: 10px; background-color: #FFEBEE; border-left: 8px solid #C62828; text-align: center; }
    .card-libre { padding: 15px; border-radius: 10px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin: 15px 0; }
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
        cols = st.columns(3)
        for idx, m in enumerate(lista):
            with cols[idx % 3]:
                if m in paradas:
                    st.markdown(f"<div class='card-parada'>🚨 {m}<br>PARADA: {paradas[m]['motivo']}<br>OP: {paradas[m]['op']}</div>", unsafe_allow_html=True)
                elif m in activos:
                    st.markdown(f"<div class='card-proceso'>⚙️ {m}<br>OP: {activos[m]['op']}<br>{activos[m]['trabajo']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-libre'>⚪ {m}<br>LIBRE</div>", unsafe_allow_html=True)

# ==========================================
# 2. CONSOLIDADO
# ==========================================
elif opcion == "📊 Consolidado":
    st.title("📊 Consolidado de Producción")
    t1, t2, t3, t4, t5 = st.tabs(["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación", "⏱️ Seguimiento"])
    
    with t1:
        data = supabase.table("impresion").select("*").execute().data
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    with t2:
        data = supabase.table("corte").select("*").execute().data
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    with t3:
        data = supabase.table("colectoras").select("*").execute().data
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    with t4:
        data = supabase.table("encuadernacion").select("*").execute().data
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    with t5:
        data = supabase.table("seguimiento_corte").select("*").execute().data
        st.dataframe(pd.DataFrame(data), use_container_width=True)

# ==========================================
# 3. SEGUIMIENTO HORARIO
# ==========================================
elif opcion == "⏱️ Seguimiento":
    st.title("⏱️ Seguimiento Cortadoras")
    cols = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS["CORTE"]):
        if cols[i % 4].button(m_btn, key=f"btn_seg_{m_btn}"):
            st.session_state.m_seg = m_btn
            
    if "m_seg" in st.session_state:
        m = st.session_state.m_seg
        st.subheader(f"Reporte Horario: {m}")
        with st.form("f_seg_horario"):
            op = st.text_input("OP")
            tr = st.text_input("Trabajo")
            c1, c2 = st.columns(2)
            med = c1.text_input("Medida Rollo")
            met = c2.number_input("Metros/Rollo", 0.0)
            k1, k2, k3 = st.columns(3)
            var = k1.number_input("Varillas", 0)
            caj = k2.number_input("Cajas", 0)
            des = k3.number_input("Desp. Kg", 0.0)
            
            if st.form_submit_button("GUARDAR AVANCE"):
                h = datetime.now().hour
                turno = "MAÑANA" if 6 <= h < 14 else "TARDE"
                payload = {
                    "maquina": m, "op": op, "trabajo": tr, "medida_rollo": med, 
                    "metros_rollo": met, "varillas_acumuladas": int(var), 
                    "cajas_acumuladas": int(caj), "desperidicio_acumulado": des, "turno": turno
                }
                supabase.table("seguimiento_corte").insert(payload).execute()
                st.success("Avance guardado.")

# ==========================================
# 4. JOYSTICKS DE ÁREA
# ==========================================
else:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_act = area_map[opcion]
    st.title(f"Joystick: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    cols = st.columns(3)
    for i, m in enumerate(MAQUINAS[area_act]):
        if m in paradas: btn_label = f"🚨 {m}\nDETENIDO"
        elif m in activos: btn_label = f"⚙️ {m}\nOP: {activos[m]['op']}"
        else: btn_label = f"⚪ {m}\nLIBRE"
        
        if cols[i % 3].button(btn_label, key=f"joy_{m}", use_container_width=True):
            st.session_state.m_sel = m

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        act = activos.get(m)
        par = paradas.get(m)

        if par:
            st.error(f"Máquina {m} en Parada")
            if st.button("REANUDAR TRABAJO"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()
        
        elif not act:
            with st.form("form_inicio"):
                st.subheader(f"Iniciar {m}")
                op = st.text_input("OP")
                tr = st.text_input("Trabajo")
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
                
                if st.form_submit_button("COMENZAR"):
                    d = {"maquina": m, "op": op, "trabajo": tr, "area": area_act, "hora_inicio": datetime.now().strftime("%H:%M")}
                    d.update(ext)
                    supabase.table("trabajos_activos").insert(d).execute()
                    st.rerun()
        else:
            st.success(f"Trabajando OP: {act['op']}")
            if st.button("🛑 REGISTRAR PARADA"):
                motivo = st.selectbox("Motivo", ["Mecánico", "Eléctrico", "Limpieza", "Ajuste", "Falta Material"])
                supabase.table("paradas_maquina").insert({"maquina": m, "op": act['op'], "motivo": motivo, "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                st.rerun()
            
            with st.form("form_final"):
                st.subheader("Finalizar OP")
                res = {}
                if area_act == "IMPRESIÓN":
                    res = {"metros_impresos": st.number_input("Metros", 0.0), "bobinas": st.number_input("Bobinas", 0)}
                elif area_act == "CORTE":
                    res = {"total_rollos": st.number_input("Rollos", 0), "cant_varillas": st.number_input("Varillas", 0), "medida_rollos": st.text_input("Medida Rollos")}
                elif area_act == "COLECTORAS":
                    res = {"total_cajas": st.number_input("Cajas", 0), "total_formas": st.number_input("Formas", 0)}
                elif area_act == "ENCUADERNACIÓN":
                    res = {"cant_final": st.number_input("Cantidad", 0), "presentacion": st.text_input("Presentación")}
                
                dk = st.number_input("Desperdicio Kg", 0.0)
                mot = st.text_input("Motivo Desperdicio")
                obs = st.text_area("Observaciones")
                
                if st.form_submit_button("GUARDAR HISTORIAL"):
                    final_data = {
                        "op": act['op'], "maquina": m, "trabajo": act['trabajo'], 
                        "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                        "desp_kg": dk, "motivo_desperdicio": mot, "observaciones": obs
                    }
                    
                    # --- FILTRADO DE COLUMNAS PARA EVITAR PGRST204 ---
                    nom_t = normalizar(area_act)
                    cols_permitidas = {
                        "impresion": ["tipo_papel", "ancho", "gramaje", "medida_trabajo"],
                        "corte": ["tipo_papel", "img_varilla", "unidades_caja"],
                        "colectoras": ["tipo_papel", "medida_trabajo", "unidades_caja"],
                        "encuadernacion": ["formas_totales", "material", "medida"]
                    }

                    for col in cols_permitidas.get(nom_t, []):
                        if col in act and act[col] is not None:
                            if col in ["ancho", "gramaje"]: final_data[col] = safe_float(act[col])
                            else: final_data[col] = act[col]

                    final_data.update(res)
                    
                    try:
                        supabase.table(nom_t).insert(final_data).execute()
                        supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                        st.success("¡Guardado correctamente!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error crítico al guardar: {e}")
