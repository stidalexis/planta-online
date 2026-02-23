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

# --- ESTILOS (TU DISEÑO ORIGINAL v6) ---
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
seleccion = st.sidebar.radio("Ir a:", opciones)

# ==========================================
# 1. MONITOR
# ==========================================
if seleccion == "🖥️ Monitor":
    st.title("🖥️ Estatus General")
    act_data = supabase.table("trabajos_activos").select("*").execute().data
    act_dict = {a['maquina']: a for a in act_data} if act_data else {}
    
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(6)
        for i, m in enumerate(lista):
            with cols[i % 6]:
                if m in act_dict:
                    st.markdown(f"<div class='card-proceso'>⚙️ {m}<br>OP: {act_dict[m]['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-libre'>⚪ {m}</div>", unsafe_allow_html=True)

# ==========================================
# 2. CONSOLIDADO GERENCIAL (TODAS LAS VENTANAS)
# ==========================================
elif seleccion == "📊 Consolidado Gerencial":
    st.title("📊 Consolidado de Producción")
    
    # Consultas de todas las áreas
    imp = supabase.table("impresion").select("*").execute().data
    cor = supabase.table("corte").select("*").execute().data
    col = supabase.table("colectoras").select("*").execute().data
    enc = supabase.table("encuadernacion").select("*").execute().data
    par = supabase.table("paradas_maquina").select("*").execute().data

    tabs = st.tabs(["Fila Maestra (OP)", "Corte", "Impresión", "Colectoras", "Encuadernación", "Paradas"])
    
    with tabs[0]: # Fila Maestra con tu cálculo solicitado
        if imp and cor:
            df_i, df_c = pd.DataFrame(imp), pd.DataFrame(cor)
            df_m = pd.merge(df_c, df_i, on="op", how="inner", suffixes=('_cor', '_imp'))
            analisis = []
            for _, f in df_m.iterrows():
                anch = safe_float(f['ancho_imp'])
                anch_m = anch/1000 if anch > 10 else anch
                k_bruto = (anch_m * safe_float(f['metros_impresos']) * safe_float(f['gramaje_imp'])) / 1000
                merma = safe_float(f['desp_kg_imp']) + safe_float(f['desp_kg_cor'])
                k_neto = k_bruto - merma
                analisis.append({
                    "OP": f['op'], "Trabajo": f['trabajo_imp'], "K. Bruto": round(k_bruto,2),
                    "Merma": round(merma,2), "K. Neto": round(k_neto,2),
                    "Eficiencia": f"{round((k_neto/k_bruto*100),1) if k_bruto>0 else 0}%",
                    "Obs. Imp": f.get('observaciones_imp',''), "Obs. Cor": f.get('observaciones_cor','')
                })
            st.dataframe(pd.DataFrame(analisis), use_container_width=True)
        else: st.info("Datos insuficientes para el cruce de OP.")

    with tabs[1]: st.dataframe(pd.DataFrame(cor), use_container_width=True) if cor else st.write("Sin datos")
    with tabs[2]: st.dataframe(pd.DataFrame(imp), use_container_width=True) if imp else st.write("Sin datos")
    with tabs[3]: st.dataframe(pd.DataFrame(col), use_container_width=True) if col else st.write("Sin datos")
    with tabs[4]: st.dataframe(pd.DataFrame(enc), use_container_width=True) if enc else st.write("Sin datos")
    with tabs[5]: st.dataframe(pd.DataFrame(par), use_container_width=True) if par else st.write("Sin datos")

# ==========================================
# 3. MÓDULOS OPERATIVOS (BOTONERA TÁCTIL)
# ==========================================
else:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_actual = area_map[seleccion]
    st.title(f"Joystick: {area_actual}")
    
    act_data = supabase.table("trabajos_activos").select("*").execute().data
    act_dict = {a['maquina']: a for a in act_data} if act_data else {}

    # Botonera táctil original
    m_cols = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS[area_actual]):
        if m_cols[i % 4].button(m_btn, key=f"btn_{m_btn}"):
            st.session_state.m_sel = m_btn

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_actual]:
        m = st.session_state.m_sel
        act = act_dict.get(m)
        
        if not act:
            with st.form("ini"):
                st.subheader(f"🚀 Iniciar {m}")
                c1, c2 = st.columns(2)
                v_op, v_tr = c1.text_input("OP"), c2.text_input("Trabajo")
                p1, p2, p3 = st.columns(3)
                v_pa, v_an, v_gr = p1.text_input("Papel"), p2.text_input("Ancho"), p3.text_input("Gramaje")
                if st.form_submit_button("EMPEZAR"):
                    if v_op:
                        supabase.table("trabajos_activos").insert({
                            "maquina":m, "op":v_op, "trabajo":v_tr, "area":area_actual,
                            "tipo_papel":v_pa, "ancho":v_an, "gramaje":v_gr, "hora_inicio":datetime.now().strftime("%H:%M")
                        }).execute()
                        st.rerun()
        else:
            with st.form("fin"):
                st.success(f"📌 {m} - OP: {act['op']}")
                if area_actual == "IMPRESIÓN": prod = st.number_input("Metros", 0.0)
                elif area_actual == "CORTE": prod = st.number_input("Rollos", 0)
                else: prod = st.number_input("Cantidad", 0)

                dk = st.number_input("Desperdicio (Kg)", 0.0)
                obs = st.text_area("📝 Observaciones")
                
                if st.form_submit_button("🏁 FINALIZAR"):
                    final = {
                        "op": act['op'], "maquina": m, "trabajo": act['trabajo'],
                        "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                        "desp_kg": safe_float(dk), "observaciones": obs,
                        "tipo_papel": act.get('tipo_papel',''), "ancho": safe_float(act.get('ancho',0)), "gramaje": safe_float(act.get('gramaje',0))
                    }
                    if area_actual == "IMPRESIÓN": final["metros_impresos"] = prod
                    elif area_actual == "CORTE": final["total_rollos"] = int(prod)
                    
                    supabase.table(normalizar(area_actual)).insert(final).execute()
                    supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                    st.rerun()
