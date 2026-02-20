import streamlit as st
from supabase import create_client
from datetime import datetime

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="CONTROL DE PRODUCCIÓN")

# --- ESTILOS DE ALTO IMPACTO ---
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

# --- INTERFAZ PRINCIPAL ---
st.sidebar.title("🏭 PLANTA PRODUCCIÓN")
area_actual = st.sidebar.radio("SELECCIONE ÁREA:", list(MAQUINAS.keys()))

st.title(f"Módulo de Operación: {area_actual}")

# --- MONITOR EN TIEMPO REAL ---
activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

n_cols = 5 if area_actual == "ENCUADERNACIÓN" else 4
cols = st.columns(n_cols)

for i, m in enumerate(MAQUINAS[area_actual]):
    with cols[i % n_cols]:
        if m in paradas:
            st.markdown(f"<div class='card-parada'>🚨 {m}<br><b>DETENIDA</b></div>", unsafe_allow_html=True)
        elif m in activos:
            st.markdown(f"<div class='card-proceso'>⚙️ {m}<br><b>OP: {activos[m]['op']}</b></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='card-libre'>⚪ {m}<br>DISPONIBLE</div>", unsafe_allow_html=True)

st.divider()

# --- GESTIÓN TÁCTIL ---
st.write("### 🔘 Seleccione Máquina para gestionar:")
c_btn = st.columns(n_cols)
for i, m_btn in enumerate(MAQUINAS[area_actual]):
    if c_btn[i % n_cols].button(m_btn, key=f"btn_{m_btn}", use_container_width=True):
        st.session_state.m_sel = m_btn

if "m_sel" in st.session_state:
    m = st.session_state.m_sel
    if m in MAQUINAS[area_actual]:
        st.subheader(f"🛠️ Panel de Control: {m}")
        
        act = supabase.table("trabajos_activos").select("*").eq("maquina", m).execute().data
        par = supabase.table("paradas_maquina").select("*").eq("maquina", m).is_("h_fin", "null").execute().data

        if par:
            st.error(f"🚨 Máquina en Parada Técnica")
            if st.button("✅ FINALIZAR PARADA Y REANUDAR", use_container_width=True):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par[0]['id']).execute()
                st.rerun()

        elif not act:
            with st.form("ini_op"):
                st.write("🆕 **ABRIR NUEVA ORDEN DE PRODUCCIÓN**")
                c1, c2 = st.columns(2)
                op = c1.text_input("Número de OP")
                tr = c2.text_input("Nombre del Trabajo")
                if st.form_submit_button("▶️ INICIAR PRODUCCIÓN", use_container_width=True):
                    if op and tr:
                        supabase.table("trabajos_activos").insert({"maquina": m, "op": op, "trabajo": tr, "area": area_actual, "hora_inicio": datetime.now().strftime("%H:%M")}).execute()
                        st.rerun()

        else:
            datos_act = act[0]
            st.info(f"Produciendo: **{datos_act['trabajo']}** (OP: {datos_act['op']}) | Inicio: {datos_act['hora_inicio']}")
            
            c_par, c_fin = st.columns([1, 2])
            
            with c_par:
                st.warning("⚠️ Registrar Incidencia")
                motivo = st.selectbox("Motivo:", ["Mantenimiento", "Falla Eléctrica", "Ajuste", "Limpieza", "Almuerzo"])
                if st.button("🚨 ACTIVAR PARADA"):
                    supabase.table("paradas_maquina").insert({"maquina": m, "op": datos_act['op'], "motivo": motivo, "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                    st.rerun()

            with c_fin:
                st.success("🏁 Finalizar Trabajo")
                with st.form("form_cierre"):
                    res = {}
                    if area_actual == "IMPRESIÓN":
                        c1, c2, c3 = st.columns(3)
                        res = {"papel": c1.text_input("Papel"), "ancho": c2.text_input("Ancho"), "gramaje": c3.text_input("Gramaje"), "tintas": c1.number_input("Tintas", 0), "metros": c2.number_input("Metros", 0), "medida": c3.text_input("Medida")}
                    elif area_actual == "CORTE":
                        c1, c2 = st.columns(2)
                        res = {"img_varilla": c1.number_input("Img x Varilla", 0), "medida": c2.text_input("Medida"), "total_varillas": c1.number_input("Total Varillas", 0), "rollos_cortados": c2.number_input("Rollos", 0)}
                    elif area_actual == "COLECTORAS":
                        c1, c2 = st.columns(2)
                        res = {"papel": c1.text_input("Papel"), "medida_forma": c2.text_input("Medida Forma"), "total_cajas": c1.number_input("Total Cajas", 0), "total_formas": c2.number_input("Total Formas", 0)}
                    elif area_actual == "ENCUADERNACIÓN":
                        c1, c2 = st.columns(2)
                        res = {"cant_formas": c1.number_input("Cant. Formas", 0), "material": c2.text_input("Material"), "cant_final": c1.number_input("Cant. Final", 0)}

                    dk = st.number_input("Desperdicio Total (Kg)", 0.0)
                    
                    if st.form_submit_button("💾 GUARDAR PRODUCCIÓN Y LIBERAR MÁQUINA", use_container_width=True):
                        res.update({
                            "op": datos_act['op'], "maquina": m, "trabajo": datos_act['trabajo'],
                            "h_inicio": datos_act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                            "desp_kg": dk
                        })
                        try:
                            supabase.table(normalizar(area_actual)).insert(res).execute()
                            supabase.table("trabajos_activos").delete().eq("id", datos_act['id']).execute()
                            st.success("✅ Datos guardados correctamente")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error en base de datos: {e}")
