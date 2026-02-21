import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="SISTEMA DE PRODUCCIÓN", page_icon="🏭")

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 75px; font-weight: bold; border-radius: 15px; font-size: 20px; border: 2px solid #0D47A1; transition: 0.3s; }
    .card-proceso { padding: 15px; border-radius: 10px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; text-align: center; }
    .card-parada { padding: 15px; border-radius: 10px; background-color: #FFEBEE; border-left: 8px solid #C62828; text-align: center; }
    .card-libre { padding: 15px; border-radius: 10px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin-top: 25px; font-size: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

def calcular_duracion(inicio, fin):
    try:
        fmt = "%H:%M"
        t_ini = datetime.strptime(inicio, fmt)
        t_fin = datetime.strptime(fin, fmt)
        diff = t_fin - t_ini
        return str(diff)
    except: return "0:00:00"

# --- NAVEGACIÓN ---
st.sidebar.title("⚙️ PANEL DE CONTROL")
opciones = ["🖥️ Monitor General", "📊 Consolidado Total", "⏱️ Seguimiento Cortadoras", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]
seleccion = st.sidebar.radio("Ir a:", opciones)

# ==========================================
# 1. CONSOLIDADO TOTAL (NUEVA PESTAÑA)
# ==========================================
if seleccion == "📊 Consolidado Total":
    st.title("📊 Consolidado de Producción")
    
    # Carga de datos de todas las tablas
    df_imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
    df_cor = pd.DataFrame(supabase.table("corte").select("*").execute().data)
    df_col = pd.DataFrame(supabase.table("colectoras").select("*").execute().data)
    df_enc = pd.DataFrame(supabase.table("encuadernacion").select("*").execute().data)

    st.subheader("🚀 Unificado: Impresión vs Corte")
    
    if not df_cor.empty:
        # Unificamos por OP
        consolidado = pd.merge(df_cor, df_imp, on="op", how="left", suffixes=('_corte', '_imp'))
        
        # Cálculos de Tiempo y Diferencias
        resumen = []
        for _, fila in consolidado.iterrows():
            t_imp = calcular_duracion(fila.get('h_inicio_imp', ''), fila.get('h_fin_imp', '')) if pd.notnull(fila.get('h_inicio_imp')) else "N/A"
            t_cor = calcular_duracion(fila.get('h_inicio_corte', ''), fila.get('h_fin_corte', ''))
            
            # Lógica de Rollo Blanco
            tipo = "Impreso" if pd.notnull(fila.get('h_inicio_imp')) else "Rollo Blanco"
            
            # Cantidades
            esperado = fila.get('bobinas', 0) if pd.notnull(fila.get('bobinas')) else 0
            salieron = fila.get('total_rollos', 0)
            dif = salieron - esperado if tipo == "Impreso" else salieron
            
            resumen.append({
                "OP": fila['op'],
                "Trabajo": fila['trabajo_corte'],
                "Tipo": tipo,
                "T. Impresión": t_imp,
                "T. Corte": t_cor,
                "Rollos Impresos": esperado,
                "Rollos Corte": salieron,
                "Diferencia": dif,
                "Desp. Total (Kg)": (fila.get('desp_kg_imp', 0) or 0) + (fila.get('desp_kg_corte', 0) or 0)
            })
        
        st.table(pd.DataFrame(resumen))
    else:
        st.warning("No hay datos de Corte para consolidar.")

    # Tablas individuales para las otras áreas
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📥 Colectoras")
        st.dataframe(df_col) if not df_col.empty else st.write("Sin datos")
    with c2:
        st.subheader("📕 Encuadernación")
        st.dataframe(df_enc) if not df_enc.empty else st.write("Sin datos")

# ==========================================
# 2. MONITOR GENERAL
# ==========================================
elif seleccion == "🖥️ Monitor General":
    st.title("🖥️ Monitor en Tiempo Real")
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
# 3. SEGUIMIENTO CORTADORAS
# ==========================================
elif seleccion == "⏱️ Seguimiento Cortadoras":
    st.title("⏱️ Seguimiento Horario")
    cols_s = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS["CORTE"]):
        if cols_s[i % 4].button(m_btn, key=f"seg_{m_btn}", use_container_width=True):
            st.session_state.m_seg = m_btn
    
    if "m_seg" in st.session_state:
        with st.form("seg_h"):
            st.subheader(f"Registro: {st.session_state.m_seg}")
            c1, c2, c3 = st.columns(3)
            op_f = c1.text_input("OP")
            var_f = c2.number_input("Varillas", 0)
            des_f = c3.number_input("Desp. Hora (Kg)", 0.0)
            if st.form_submit_button("Guardar"):
                supabase.table("seguimiento_corte").insert({"maquina": st.session_state.m_seg, "op": op_f, "n_varillas_actual": var_f, "desperdicio_kg": des_f}).execute()
                st.success("Guardado")

# ==========================================
# 4. MÓDULOS OPERATIVOS (RESTO DEL CÓDIGO)
# ==========================================
else:
    mapa_areas = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_actual = mapa_areas[seleccion]
    st.title(f"Módulo: {area_actual}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    n_cols = 5 if area_actual == "ENCUADERNACIÓN" else 4
    cols_v = st.columns(n_cols)
    for i, m_btn in enumerate(MAQUINAS[area_actual]):
        if cols_v[i % n_cols].button(m_btn, key=f"btn_{m_btn}", use_container_width=True):
            st.session_state.m_sel = m_btn

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_actual]:
        m = st.session_state.m_sel
        act, par = activos.get(m), paradas.get(m)
        
        if par:
            st.error("🚨 Parada técnica.")
            if st.button("REANUDAR"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()
        elif not act:
            with st.form("ini"):
                op = st.text_input("OP")
                tr = st.text_input("Trabajo")
                if st.form_submit_button("INICIAR"):
                    supabase.table("trabajos_activos").insert({"maquina": m, "op": op, "trabajo": tr, "area": area_actual, "hora_inicio": datetime.now().strftime("%H:%M")}).execute()
                    st.rerun()
        else:
            with st.form("fin"):
                st.info(f"Trabajando OP: {act['op']}")
                if area_actual == "CORTE":
                    rollos = st.number_input("Total Rollos", 0)
                else:
                    cant = st.number_input("Cantidad", 0)
                dk = st.number_input("Desp. (Kg)", 0.0)
                if st.form_submit_button("FINALIZAR"):
                    # Aquí la lógica de guardado que ya teníamos
                    res = {"op": act['op'], "maquina": m, "trabajo": act['trabajo'], "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"), "desp_kg": dk}
                    if area_actual == "CORTE": res["total_rollos"] = rollos
                    supabase.table(area_actual.lower()).insert(res).execute()
                    supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                    st.rerun()
