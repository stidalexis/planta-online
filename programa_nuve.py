import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="PRODUCCIÓN PLANTA", page_icon="🏭")

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 75px; font-weight: bold; border-radius: 12px; font-size: 18px; border: 2px solid #0D47A1; }
    .card-proceso { padding: 15px; border-radius: 10px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; text-align: center; font-weight: bold; }
    .card-parada { padding: 15px; border-radius: 10px; background-color: #FFEBEE; border-left: 8px solid #C62828; text-align: center; font-weight: bold; }
    .card-libre { padding: 15px; border-radius: 10px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; }
    .title-area { background-color: #0D47A1; color: white; padding: 8px; border-radius: 5px; text-align: center; font-weight: bold; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- FUNCIONES ---
def normalizar(texto):
    reemplazos = {"Í": "I", "Ó": "O", "Á": "A", "É": "E", "Ú": "U"}
    for t, r in reemplazos.items(): texto = texto.replace(t, r)
    return texto.lower()

def safe_float(valor):
    try: return float(str(valor).replace(',', '.'))
    except: return 0.0

def calcular_duracion(inicio, fin):
    try:
        t_ini = datetime.strptime(inicio, "%H:%M")
        t_fin = datetime.strptime(fin, "%H:%M")
        diff = t_fin - t_ini
        return str(diff)
    except: return "0:00:00"

# --- NAVEGACIÓN ---
st.sidebar.title("🏭 MENÚ PRINCIPAL")
opciones = ["🖥️ Monitor en Vivo", "📊 Consolidado Gerencial", "⏱️ Seguimiento Cortadoras", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]
seleccion = st.sidebar.radio("Ir a:", opciones)

# ==========================================
# 1. MONITOR EN VIVO
# ==========================================
if seleccion == "🖥️ Monitor en Vivo":
    st.title("🖥️ Estatus de Planta en Tiempo Real")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
    
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(6)
        for idx, m in enumerate(lista):
            with cols[idx % 6]:
                if m in paradas: st.markdown(f"<div class='card-parada'>🚨 PARADA<br>{m}</div>", unsafe_allow_html=True)
                elif m in activos: st.markdown(f"<div class='card-proceso'>⚙️ {m}<br>OP: {activos[m]['op']}</div>", unsafe_allow_html=True)
                else: st.markdown(f"<div class='card-libre'>⚪ LIBRE<br>{m}</div>", unsafe_allow_html=True)

# ==========================================
# 2. CONSOLIDADO GERENCIAL
# ==========================================
elif seleccion == "📊 Consolidado Gerencial":
    st.title("📊 Análisis de Productividad")
    
    tab1, tab2, tab3 = st.tabs(["Impresión vs Corte", "Colectoras", "Encuadernación"])
    
    with tab1:
        df_imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
        df_cor = pd.DataFrame(supabase.table("corte").select("*").execute().data)
        if not df_cor.empty and not df_imp.empty:
            consolidado = pd.merge(df_cor, df_imp, on="op", how="left", suffixes=('_corte', '_imp'))
            resumen = []
            for _, fila in consolidado.iterrows():
                # Peso Teórico: (Ancho(m) * Metros * Gramaje) / 1000
                ancho = safe_float(fila.get('ancho_imp', 0))
                ancho_m = ancho / 1000 if ancho > 10 else ancho
                peso_t = (ancho_m * safe_float(fila.get('metros_impresos', 0)) * safe_float(fila.get('gramaje_imp', 0))) / 1000
                desp = safe_float(fila.get('desp_kg_imp', 0)) + safe_float(fila.get('desp_kg_corte', 0))
                
                resumen.append({
                    "OP": fila['op'], "Trabajo": fila['trabajo_corte'],
                    "Peso Salida (Kg)": round(peso_t, 2), "Desperdicio (Kg)": round(desp, 2),
                    "% Desp.": f"{round((desp/peso_t*100),1)}%" if peso_t > 0 else "0%",
                    "Tiempo Imp.": calcular_duracion(fila.get('h_inicio_imp', ''), fila.get('h_fin_imp', '')),
                    "Tiempo Corte": calcular_duracion(fila.get('h_inicio_corte', ''), fila.get('h_fin_corte', ''))
                })
            st.dataframe(pd.DataFrame(resumen), use_container_width=True)

# ==========================================
# 3. SEGUIMIENTO HORARIO CORTADORAS
# ==========================================
elif seleccion == "⏱️ Seguimiento Cortadoras":
    st.title("⏱️ Registro Horario - Corte")
    cols_s = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS["CORTE"]):
        if cols_s[i % 4].button(m_btn, key=f"seg_{m_btn}", use_container_width=True):
            st.session_state.m_seg = m_btn
    
    if "m_seg" in st.session_state:
        m_s = st.session_state.m_seg
        act_seg = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}.get(m_s, {})
        with st.form("f_seg"):
            st.subheader(f"Avance de {m_s}")
            c1, c2 = st.columns(2)
            op_s = c1.text_input("OP", value=act_seg.get('op', ""))
            tr_s = c2.text_input("Trabajo", value=act_seg.get('trabajo', ""))
            c3, c4 = st.columns(2)
            var_s = c3.number_input("Varillas producidas esta hora", 0)
            desp_s = c4.number_input("Desperdicio esta hora (Kg)", 0.0)
            if st.form_submit_button("💾 REGISTRAR HORA"):
                supabase.table("seguimiento_corte").insert({"maquina": m_s, "op": op_s, "nombre_trabajo": tr_s, "n_varillas_actual": var_s, "desperdicio_kg": desp_s}).execute()
                st.success(f"Hora registrada para {m_s}")

# ==========================================
# VISTAS DE OPERACIÓN (TODAS LAS ÁREAS)
# ==========================================
else:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_actual = area_map[seleccion]
    st.title(f"🕹️ Terminal: {area_actual}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    cols_m = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS[area_actual]):
        if cols_m[i % 4].button(m_btn, key=f"btn_{m_btn}", use_container_width=True):
            st.session_state.m_sel = m_btn

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_actual]:
        m = st.session_state.m_sel
        act, par = activos.get(m), paradas.get(m)
        
        if par:
            st.error(f"⚠️ {m} EN PARADA ({par['motivo']})")
            if st.button("▶️ REANUDAR"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()
        
        elif not act:
            with st.form("inicio"):
                st.subheader(f"🚀 Iniciar OP en {m}")
                c1, c2 = st.columns(2)
                op = c1.text_input("Orden de Producción (OP)")
                tr = c2.text_input("Nombre del Trabajo")
                extra = {}
                if area_actual == "IMPRESIÓN":
                    p1, p2, p3 = st.columns(3)
                    extra = {"tipo_papel": p1.text_input("Papel"), "ancho": p2.text_input("Ancho"), "gramaje": p3.text_input("Gramaje"), "medida_trabajo": p1.text_input("Medida")}
                elif area_actual == "CORTE":
                    p1, p2, p3 = st.columns(3)
                    extra = {"tipo_papel": p1.text_input("Papel"), "img_varilla": p2.number_input("Img/Varilla", 0), "medida_rollos": p3.text_input("Medida Rollos")}
                elif area_actual == "COLECTORAS":
                    p1, p2 = st.columns(2)
                    extra = {"tipo_papel": p1.text_input("Papel"), "unidades_caja": p2.number_input("Und/Caja", 0)}
                elif area_actual == "ENCUADERNACIÓN":
                    p1, p2 = st.columns(2)
                    extra = {"formas_totales": p1.number_input("Formas", 0), "material": p2.text_input("Material")}
                
                if st.form_submit_button("✅ EMPEZAR"):
                    if op and tr:
                        data = {"maquina": m, "op": op, "trabajo": tr, "area": area_actual, "hora_inicio": datetime.now().strftime("%H:%M")}
                        data.update(extra)
                        supabase.table("trabajos_activos").insert(data).execute()
                        st.rerun()
        else:
            with st.form("cierre"):
                st.info(f"Produciendo: {act['trabajo']} (Inició: {act['hora_inicio']})")
                res = {}
                if area_actual == "IMPRESIÓN":
                    c1, c2 = st.columns(2); res = {"metros_impresos": c1.number_input("Metros", 0), "bobinas": c2.number_input("Bobinas", 0)}
                elif area_actual == "CORTE":
                    c1, c2, c3 = st.columns(3); res = {"cant_varillas": c1.number_input("Varillas", 0), "total_rollos": c2.number_input("Total Rollos", 0), "unidades_caja": c3.number_input("Und/Caja", 0)}
                elif area_actual == "COLECTORAS":
                    c1, c2 = st.columns(2); res = {"total_cajas": c1.number_input("Total Cajas", 0), "total_formas": c2.number_input("Total Formas", 0)}
                elif area_actual == "ENCUADERNACIÓN":
                    c1, c2 = st.columns(2); res = {"cant_final": c1.number_input("Cant. Final", 0), "presentacion": c2.text_input("Presentación")}

                c3, c4 = st.columns(2)
                dk = c3.number_input("Desperdicio (Kg)", 0.0)
                mot = c4.text_input("Motivo Desp.")
                obs = st.text_area("Observaciones")
                
                if st.form_submit_button("🏁 FINALIZAR TRABAJO"):
                    final_data = {"op": act['op'], "maquina": m, "trabajo": act['trabajo'], "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"), "desp_kg": safe_float(dk), "motivo_desperdicio": mot, "observaciones": obs}
                    final_data.update(res)
                    # Mapeo de campos técnicos
                    for col in ["tipo_papel", "ancho", "gramaje", "medida_trabajo", "img_varilla", "medida_rollos", "unidades_caja", "formas_totales", "material"]:
                        if col in act: final_data[col] = safe_float(act[col]) if col in ["ancho", "gramaje"] else act[col]
                    
                    supabase.table(normalizar(area_actual)).insert(final_data).execute()
                    supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                    st.rerun()

            if st.button("🚨 PARADA TÉCNICA"):
                supabase.table("paradas_maquina").insert({"maquina": m, "op": act['op'], "motivo": "Ajuste/Mecánico", "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                st.rerun()
