import streamlit as st
from supabase import create_client
from datetime import datetime

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="CONTROL DE PRODUCCIÓN")

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 75px; font-weight: bold; border-radius: 15px; font-size: 20px; border: 2px solid #0D47A1; transition: 0.3s; }
    .stButton > button:hover { background-color: #1E88E5; color: white; border: 2px solid #0D47A1; }
    .card-proceso { padding: 20px; border-radius: 15px; background-color: #E8F5E9; border-left: 10px solid #2E7D32; text-align: center; }
    .card-parada { padding: 20px; border-radius: 15px; background-color: #FFEBEE; border-left: 10px solid #C62828; text-align: center; }
    .card-libre { padding: 20px; border-radius: 15px; background-color: #F5F5F5; border-left: 10px solid #9E9E9E; text-align: center; color: #757575; }
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

# --- MONITOR ---
activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

# --- INTERFAZ ---
st.sidebar.title("🏭 PLANTA PRODUCCIÓN")
area_actual = st.sidebar.radio("SELECCIONE ÁREA:", list(MAQUINAS.keys()))

st.title(f"Módulo: {area_actual}")
n_cols = 5 if area_actual == "ENCUADERNACIÓN" else 4
cols = st.columns(n_cols)

for i, m in enumerate(MAQUINAS[area_actual]):
    with cols[i % n_cols]:
        if m in paradas: st.markdown(f"<div class='card-parada'>🚨 {m}<br><b>DETENIDA</b></div>", unsafe_allow_html=True)
        elif m in activos: st.markdown(f"<div class='card-proceso'>⚙️ {m}<br><b>OP: {activos[m]['op']}</b></div>", unsafe_allow_html=True)
        else: st.markdown(f"<div class='card-libre'>⚪ {m}<br>DISPONIBLE</div>", unsafe_allow_html=True)

st.divider()

st.write("### 🔘 Seleccione Máquina:")
c_btn = st.columns(n_cols)
for i, m_btn in enumerate(MAQUINAS[area_actual]):
    if c_btn[i % n_cols].button(m_btn, key=f"btn_{m_btn}", use_container_width=True):
        st.session_state.m_sel = m_btn

if "m_sel" in st.session_state:
    m = st.session_state.m_sel
    if m in MAQUINAS[area_actual]:
        st.subheader(f"🛠️ Panel: {m}")
        act = supabase.table("trabajos_activos").select("*").eq("maquina", m).execute().data
        par = supabase.table("paradas_maquina").select("*").eq("maquina", m).is_("h_fin", "null").execute().data

        if par:
            if st.button("✅ REANUDAR MÁQUINA", use_container_width=True):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par[0]['id']).execute()
                st.rerun()

        elif not act:
            with st.form("ini_op"):
                st.write("🆕 **INICIAR TRABAJO**")
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
            datos_act = act[0]
            st.info(f"En curso: **{datos_act['trabajo']}** (OP: {datos_act['op']})")
            
            with st.form("form_cierre"):
                st.write("🏁 **FINALIZAR Y CERRAR**")
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
                    # Traemos datos del inicio
                    res.update({"tipo_papel": datos_act.get('tipo_papel'), "medida_trabajo": datos_act.get('medida_trabajo'), "unidades_caja_inicial": datos_act.get('unidades_caja')})
                elif area_actual == "ENCUADERNACIÓN":
                    c1, c2, c3 = st.columns(3)
                    res = {"cant_final": c1.number_input("Cantidad Final", 0), "presentacion": c2.text_input("Presentación"), "motivo_desperdicio": c3.text_input("Motivo de Desperdicio")}

                dk = st.number_input("Peso Desperdicio (Kg)", 0.0)
                obs = st.text_area("Observaciones")
                
                if st.form_submit_button("💾 GUARDAR TODO", use_container_width=True):
                    res.update({"op": datos_act['op'], "maquina": m, "trabajo": datos_act['trabajo'], "h_inicio": datos_act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"), "desp_kg": dk, "observaciones": obs})
                    supabase.table(normalizar(area_actual)).insert(res).execute()
                    supabase.table("trabajos_activos").delete().eq("id", datos_act['id']).execute()
                    st.rerun()

            if st.button("🚨 ACTIVAR PARADA", use_container_width=True):
                supabase.table("paradas_maquina").insert({"maquina": m, "op": datos_act['op'], "motivo": "Ajuste Técnico", "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                st.rerun()
