import streamlit as st
from supabase import create_client
from datetime import datetime

# --- CONEXIÓN ---
# Asegúrate de tener SUPABASE_URL y SUPABASE_KEY en tus Secrets de Streamlit
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="SISTEMA INTEGRAL DE PRODUCCIÓN")

# --- ESTILOS DE ALTO IMPACTO ---
st.markdown("""
    <style>
    .stButton > button { height: 75px; font-weight: bold; border-radius: 15px; font-size: 20px; border: 2px solid #0D47A1; transition: 0.3s; }
    .stButton > button:hover { background-color: #1E88E5; color: white; border: 2px solid #0D47A1; }
    .card-proceso { padding: 15px; border-radius: 10px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; text-align: center; margin-bottom: 10px; }
    .card-parada { padding: 15px; border-radius: 10px; background-color: #FFEBEE; border-left: 8px solid #C62828; text-align: center; margin-bottom: 10px; }
    .card-libre { padding: 15px; border-radius: 10px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; margin-bottom: 10px; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin-top: 25px; margin-bottom: 10px; font-size: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

def normalizar(texto):
    reemplazos = {"Í": "I", "Ó": "O", "Á": "A", "É": "E", "Ú": "U"}
    for t, r in reemplazos.items():
        texto = texto.replace(t, r)
    return texto.lower()

# --- CARGA DE DATOS EN TIEMPO REAL ---
try:
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
except Exception as e:
    st.error(f"Error de conexión: {e}")
    activos, paradas = {}, {}

# --- SIDEBAR (MENÚ DE NAVEGACIÓN) ---
st.sidebar.title("🏭 PLANTA PRODUCCIÓN")
opciones = ["🖥️ Monitor General", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]
seleccion = st.sidebar.radio("IR A:", opciones)

# ==========================================
# VISTA 1: MONITOR GENERAL EN TIEMPO REAL
# ==========================================
if seleccion == "🖥️ Monitor General":
    st.title("🖥️ Estado Global de Planta")
    
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols_mon = st.columns(6)
        for idx, m_mon in enumerate(lista):
            with cols_mon[idx % 6]:
                if m_mon in paradas:
                    st.markdown(f"<div class='card-parada'>🚨 {m_mon}<br><small>PARADA</small></div>", unsafe_allow_html=True)
                elif m_mon in activos:
                    st.markdown(f"<div class='card-proceso'>⚙️ {m_mon}<br><b>OP: {activos[m_mon]['op']}</b></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-libre'>⚪ {m_mon}<br><small>LIBRE</small></div>", unsafe_allow_html=True)

# ==========================================
# VISTA 2: MÓDULOS OPERATIVOS
# ==========================================
else:
    # Mapeo de selección a nombre de área técnica
    mapa_areas = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_actual = mapa_areas[seleccion]
    
    st.title(f"Módulo: {area_actual}")

    # Visualización de estado local (el área actual)
    n_cols = 5 if area_actual == "ENCUADERNACIÓN" else 4
    cols_v = st.columns(n_cols)
    for i, m_v in enumerate(MAQUINAS[area_actual]):
        with cols_v[i % n_cols]:
            if m_v in paradas: st.markdown(f"<div class='card-parada'>🚨 {m_v}</div>", unsafe_allow_html=True)
            elif m_v in activos: st.markdown(f"<div class='card-proceso'>⚙️ {m_v}<br>OP: {activos[m_v]['op']}</div>", unsafe_allow_html=True)
            else: st.markdown(f"<div class='card-libre'>⚪ {m_v}</div>", unsafe_allow_html=True)

    st.divider()

    # Gestión de botones táctiles
    st.write("### 🔘 Seleccione Máquina para Operar:")
    c_btn = st.columns(n_cols)
    for i, m_btn in enumerate(MAQUINAS[area_actual]):
        if c_btn[i % n_cols].button(m_btn, key=f"btn_{m_btn}", use_container_width=True):
            st.session_state.m_sel = m_btn

    # Panel de Control de la máquina seleccionada
    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_actual]:
        m = st.session_state.m_sel
        st.subheader(f"🛠️ Gestión: {m}")
        
        act = activos.get(m)
        par = paradas.get(m)

        if par:
            st.error("🚨 Máquina en Parada Técnica")
            if st.button("✅ REANUDAR PRODUCCIÓN", use_container_width=True):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()

        elif not act:
            with st.form("ini_op"):
                st.write("🆕 **INICIAR NUEVA ORDEN DE PRODUCCIÓN**")
                c1, c2 = st.columns(2)
                op, tr = c1.text_input("Número de OP"), c2.text_input("Nombre del Trabajo")
                
                extra = {}
                if area_actual == "IMPRESIÓN":
                    p1, p2, p3 = st.columns(3)
                    extra = {"tipo_papel": p1.text_input("Tipo de Papel"), "ancho": p2.text_input("Ancho"), "gramaje": p3.text_input("Gramaje"), "medida_trabajo": p1.text_input("Medida Trabajo")}
                elif area_actual == "CORTE":
                    p1, p2, p3 = st.columns(3)
                    extra = {"tipo_papel": p1.text_input("Tipo de Papel"), "ancho": p2.text_input("Ancho"), "gramaje": p3.text_input("Gramaje"), "img_varilla": p1.number_input("Imágenes*Varilla", 0), "medida_rollos": p2.text_input("Medida Rollos")}
                elif area_actual == "COLECTORAS":
                    p1, p2 = st.columns(2)
                    extra = {"tipo_papel": p1.text_input("Tipo Papel"), "medida_trabajo": p2.text_input("Medida de Trabajo"), "unidades_caja": p1.number_input("Unidades*Caja", 0)}
                elif area_actual == "ENCUADERNACIÓN":
                    p1, p2 = st.columns(2)
                    extra = {"formas_totales": p1.number_input("Formas Totales", 0), "material": p2.text_input("Material"), "medida": p1.text_input("Medida")}
                
                if st.form_submit_button("▶️ REGISTRAR INICIO", use_container_width=True):
                    if op and tr:
                        data = {"maquina": m, "op": op, "trabajo": tr, "area": area_actual, "hora_inicio": datetime.now().strftime("%H:%M")}
                        data.update(extra)
                        supabase.table("trabajos_activos").insert(data).execute()
                        st.rerun()

        else:
            st.info(f"🟢 **EN CURSO:** {act['trabajo']} (OP: {act['op']})")
            with st.form("form_cierre"):
                st.write("🏁 **FINALIZAR TRABAJO**")
                res = {}
                if area_actual == "IMPRESIÓN":
                    c1, c2, c3 = st.columns(3)
                    res = {"metros_impresos": c1.number_input("Metros Impresos", 0), "bobinas": c2.number_input("Bobinas", 0), "motivo_desperdicio": c3.text_input("Motivo Desperdicio")}
                elif area_actual == "CORTE":
                    c1, c2, c3 = st.columns(3)
                    res = {"cant_varillas": c1.number_input("Cant. Varillas", 0), "unidades_caja": c2.number_input("Unidades*Caja", 0), "total_rollos": c3.number_input("Total Rollos", 0), "motivo_desperdicio": c1.text_input("Motivo Desperdicio")}
                elif area_actual == "COLECTORAS":
                    c1, c2 = st.columns(2)
                    res = {"total_cajas": c1.number_input("Cantidad de Cajas", 0), "total_formas": c2.number_input("Total Formas", 0), "motivo_desperdicio": c1.text_input("Motivo de Desperdicio")}
                    res.update({"tipo_papel": act.get('tipo_papel'), "medida_trabajo": act.get('medida_trabajo'), "unidades_caja_inicial": act.get('unidades_caja')})
                elif area_actual == "ENCUADERNACIÓN":
                    c1, c2, c3 = st.columns(3)
                    res = {"cant_final": c1.number_input("Cantidad Final", 0), "presentacion": c2.text_input("Presentación"), "motivo_desperdicio": c3.text_input("Motivo de Desperdicio")}

                dk = st.number_input("Peso Desperdicio (Kg)", 0.0)
                obs = st.text_area("Observaciones")
                
                if st.form_submit_button("💾 GUARDAR PRODUCCIÓN", use_container_width=True):
                    res.update({"op": act['op'], "maquina": m, "trabajo": act['trabajo'], "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"), "desp_kg": dk, "observaciones": obs})
                    supabase.table(normalizar(area_actual)).insert(res).execute()
                    supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                    st.rerun()

            if st.button("🚨 REPORTAR PARADA", use_container_width=True):
                supabase.table("paradas_maquina").insert({"maquina": m, "op": act['op'], "motivo": "Ajuste/Incidencia", "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                st.rerun()
