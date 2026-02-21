import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="CONTROL DE PRODUCCIÓN", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS (IGUALES A TU ARCHIVO) ---
st.markdown("""
    <style>
    .stButton > button { height: 75px; font-weight: bold; border-radius: 12px; font-size: 18px; border: 2px solid #0D47A1; }
    .card-proceso { padding: 15px; border-radius: 10px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; text-align: center; font-weight: bold; }
    .card-parada { padding: 15px; border-radius: 10px; background-color: #FFEBEE; border-left: 8px solid #C62828; text-align: center; color: #B71C1C; font-weight: bold; }
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
st.sidebar.title("🏭 MENÚ PLANTA")
opciones = ["🖥️ Monitor", "📊 Consolidado Gerencial", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]
seleccion = st.sidebar.radio("Ir a:", opciones)

# ==========================================
# 1. MONITOR (CORREGIDO)
# ==========================================
if seleccion == "🖥️ Monitor":
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
# 2. CONSOLIDADO GERENCIAL (PEDIDO)
# ==========================================
elif seleccion == "📊 Consolidado Gerencial":
    st.title("📊 Análisis de Inteligencia por OP")
    df_imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
    df_cor = pd.DataFrame(supabase.table("corte").select("*").execute().data)
    
    if not df_imp.empty and not df_cor.empty:
        df_join = pd.merge(df_cor, df_imp, on="op", how="inner", suffixes=('_cor', '_imp'))
        analisis = []
        for _, fila in df_join.iterrows():
            ancho_m = safe_float(fila['ancho_imp']) / 1000 if safe_float(fila['ancho_imp']) > 10 else safe_float(fila['ancho_imp'])
            k_bruto = (ancho_m * safe_float(fila['metros_impresos']) * safe_float(fila['gramaje_imp'])) / 1000
            merma = safe_float(fila['desp_kg_imp']) + safe_float(fila['desp_kg_cor'])
            k_neto = k_bruto - merma
            analisis.append({
                "OP": fila['op'], "Trabajo": fila['trabajo_imp'], "Papel": f"{fila['tipo_papel_imp']} {int(safe_float(fila['gramaje_imp']))}g",
                "K. Bruto": round(k_bruto,2), "Merma": round(merma,2), "K. Neto": round(k_neto,2),
                "Eficiencia": f"{round((k_neto/k_bruto*100),1) if k_bruto>0 else 0}%",
                "Obs. Imp": fila['observaciones_imp'], "Obs. Corte": fila['observaciones_cor']
            })
        st.dataframe(pd.DataFrame(analisis), use_container_width=True)
    else: st.info("Datos insuficientes para el cruce.")

# ==========================================
# 3. MÓDULOS DE ÁREA (TU LÓGICA ORIGINAL)
# ==========================================
else:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_actual = area_map[seleccion]
    st.title(f"Joystick: {area_actual}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}

    cols_m = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS[area_actual]):
        if cols_m[i % 4].button(m_btn, key=f"btn_{m_btn}"):
            st.session_state.m_sel = m_btn

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_actual]:
        m = st.session_state.m_sel
        act = activos.get(m)
        
        if not act:
            with st.form("inicio"):
                st.subheader(f"🚀 Iniciar en {m}")
                c1, c2 = st.columns(2)
                op, tr = c1.text_input("OP"), c2.text_input("Trabajo")
                p1, p2, p3 = st.columns(3)
                pa, an, gr = p1.text_input("Papel"), p2.text_input("Ancho"), p3.text_input("Gramaje")
                if st.form_submit_button("EMPEZAR"):
                    data = {"maquina": m, "op": op, "trabajo": tr, "area": area_actual, "tipo_papel": pa, "ancho": an, "gramaje": gr, "hora_inicio": datetime.now().strftime("%H:%M")}
                    supabase.table("trabajos_activos").insert(data).execute()
                    st.rerun()
        else:
            with st.form("cierre"):
                st.info(f"Produciendo OP: {act['op']}")
                res = {}
                if area_actual == "IMPRESIÓN":
                    res["metros_impresos"] = st.number_input("Metros", 0.0)
                elif area_actual == "CORTE":
                    res["total_rollos"] = st.number_input("Rollos", 0)

                dk = st.number_input("Desperdicio (Kg)", 0.0)
                obs = st.text_area("📝 Observaciones") # ESTO ES LO QUE PEDISTE
                
                if st.form_submit_button("🏁 FINALIZAR"):
                    final_data = {
                        "op": act['op'], "maquina": m, "trabajo": act['trabajo'],
                        "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                        "desp_kg": safe_float(dk), "observaciones": obs,
                        "tipo_papel": act['tipo_papel'], "ancho": safe_float(act['ancho']), "gramaje": safe_float(act['gramaje'])
                    }
                    final_data.update(res)
                    supabase.table(normalizar(area_actual)).insert(final_data).execute()
                    supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                    st.rerun()
