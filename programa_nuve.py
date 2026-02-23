import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="CONTROL DE PRODUCCIÓN MASTER", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS (TUS ESTILOS ORIGINALES) ---
st.markdown("""
    <style>
    .stButton > button { height: 75px; font-weight: bold; border-radius: 12px; font-size: 18px; border: 2px solid #0D47A1; }
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
opciones = ["🖥️ Monitor", "📊 Consolidado Gerencial", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]
seleccion = st.sidebar.radio("MENÚ DE CONTROL", opciones)

# ==========================================
# 1. MONITOR GENERAL
# ==========================================
if seleccion == "🖥️ Monitor":
    st.title("🖥️ Estatus de Maquinaria en Tiempo Real")
    # Corrección para evitar KeyError: obtenemos la data limpia
    res_activos = supabase.table("trabajos_activos").select("*").execute().data
    act_dict = {a['maquina']: a for a in res_activos} if res_activos else {}
    
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(6)
        for idx, m in enumerate(lista):
            with cols[idx % 6]:
                if m in act_dict:
                    st.markdown(f"<div class='card-proceso'>⚙️ {m}<br>OP: {act_dict[m]['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-libre'>⚪ {m}</div>", unsafe_allow_html=True)

# ==========================================
# 2. CONSOLIDADO GERENCIAL
# ==========================================
elif seleccion == "📊 Consolidado Gerencial":
    st.title("📊 Análisis de Producción e Inteligencia")
    imp_q = supabase.table("impresion").select("*").execute().data
    cor_q = supabase.table("corte").select("*").execute().data
    
    t1, t2, t3 = st.tabs(["Corte", "Impresión", "Fila Maestra por OP"])
    
    with t1:
        if cor_q: st.dataframe(pd.DataFrame(cor_q), use_container_width=True)
        else: st.info("Sin registros en Corte")
    
    with t2:
        if imp_q: st.dataframe(pd.DataFrame(imp_q), use_container_width=True)
        else: st.info("Sin registros en Impresión")
        
    with t3:
        if imp_q and cor_q:
            df_i = pd.DataFrame(imp_q)
            df_c = pd.DataFrame(cor_q)
            # Cruce de datos por OP
            df_m = pd.merge(df_c, df_i, on="op", how="inner", suffixes=('_cor', '_imp'))
            
            analisis = []
            for _, f in df_m.iterrows():
                # Fórmulas de ingeniería de papel
                anch = safe_float(f['ancho_imp'])
                anch_m = anch/1000 if anch > 10 else anch
                k_bruto = (anch_m * safe_float(f['metros_impresos']) * safe_float(f['gramaje_imp'])) / 1000
                merma = safe_float(f['desp_kg_imp']) + safe_float(f['desp_kg_cor'])
                k_neto = k_bruto - merma
                
                analisis.append({
                    "OP": f['op'], 
                    "Trabajo": f['trabajo_imp'], 
                    "Papel": f"{f.get('tipo_papel_imp', 'N/A')} {int(safe_float(f['gramaje_imp']))}g",
                    "Kilos Brutos": round(k_bruto, 2),
                    "Merma Total": round(merma, 2),
                    "Kilos Netos": round(k_neto, 2),
                    "Eficiencia": f"{round((k_neto/k_bruto*100),1) if k_bruto>0 else 0}%",
                    "Rollos": f['total_rollos'],
                    "Obs. Imp": f.get('observaciones_imp', ''),
                    "Obs. Cor": f.get('observaciones_cor', '')
                })
            st.dataframe(pd.DataFrame(analisis), use_container_width=True)
        else:
            st.warning("Se requiere completar la misma OP en Impresión y Corte para ver el cruce.")

# ==========================================
# 3. MÓDULOS DE ÁREA
# ==========================================
else:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_actual = area_map[seleccion]
    st.title(f"Joystick de Planta: {area_actual}")
    
    res_activos = supabase.table("trabajos_activos").select("*").execute().data
    act_dict = {a['maquina']: a for a in res_activos} if res_activos else {}

    # Renderizado de botones de máquinas
    m_cols = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS[area_actual]):
        if m_cols[i % 4].button(m_btn, key=f"btn_{m_btn}"):
            st.session_state.m_sel = m_btn

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_actual]:
        m = st.session_state.m_sel
        act = act_dict.get(m)
        
        if not act:
            with st.form("form_inicio"):
                st.subheader(f"🚀 Iniciar OP en {m}")
                c1, c2 = st.columns(2)
                v_op = c1.text_input("Orden de Producción (OP)")
                v_tr = c2.text_input("Nombre del Trabajo")
                
                p1, p2, p3 = st.columns(3)
                v_pa = p1.text_input("Tipo de Papel")
                v_an = p2.text_input("Ancho (mm)")
                v_gr = p3.text_input("Gramaje (g)")
                
                if st.form_submit_button("REGISTRAR INICIO"):
                    if v_op and v_tr:
                        data = {
                            "maquina": m, "op": v_op, "trabajo": v_tr, "area": area_actual,
                            "tipo_papel": v_pa, "ancho": v_an, "gramaje": v_gr,
                            "hora_inicio": datetime.now().strftime("%H:%M")
                        }
                        supabase.table("trabajos_activos").insert(data).execute()
                        st.rerun()
                    else:
                        st.error("OP y Trabajo son obligatorios.")
        else:
            with st.form("form_cierre"):
                st.success(f"📌 {m} trabajando en OP: {act['op']} ({act['trabajo']})")
                res = {}
                if area_actual == "IMPRESIÓN":
                    res["metros_impresos"] = st.number_input("Metros Totales Impresos", 0.0)
                elif area_actual == "CORTE":
                    res["total_rollos"] = st.number_input("Cantidad de Rollos Finales", 0)

                dk = st.number_input("Desperdicio / Merma (Kg)", 0.0)
                obs = st.text_area("📝 Observaciones / Motivo de desperdicio")
                
                if st.form_submit_button("🏁 FINALIZAR Y GUARDAR"):
                    final_data = {
                        "op": act['op'], "maquina": m, "trabajo": act['trabajo'],
                        "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                        "desp_kg": safe_float(dk), "observaciones": obs,
                        "tipo_papel": act['tipo_papel'], 
                        "ancho": safe_float(act['ancho']), 
                        "gramaje": safe_float(act['gramaje'])
                    }
                    final_data.update(res)
                    
                    try:
                        supabase.table(normalizar(area_actual)).insert(final_data).execute()
                        supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                        st.session_state.pop("m_sel", None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
