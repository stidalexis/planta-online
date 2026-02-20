import streamlit as st
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN DE CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="SISTEMA INTEGRAL DE PRODUCCIÓN", page_icon="🏭")

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stButton > button { height: 75px; font-weight: bold; border-radius: 15px; font-size: 20px; border: 2px solid #0D47A1; transition: 0.3s; }
    .stButton > button:hover { background-color: #1E88E5; color: white; border: 2px solid #0D47A1; }
    .card-proceso { padding: 15px; border-radius: 10px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; text-align: center; margin-bottom: 10px; }
    .card-parada { padding: 15px; border-radius: 10px; background-color: #FFEBEE; border-left: 8px solid #C62828; text-align: center; margin-bottom: 10px; }
    .card-libre { padding: 15px; border-radius: 10px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; margin-bottom: 10px; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin-top: 25px; font-size: 18px; }
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

# --- CARGA DE DATOS ---
try:
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
except:
    activos, paradas = {}, {}

# --- NAVEGACIÓN ---
st.sidebar.title("🏭 PLANTA")
opciones = ["🖥️ Monitor General", "⏱️ Seguimiento Cortadoras", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]
seleccion = st.sidebar.radio("Ir a:", opciones)

# ==========================================
# 1. MONITOR GENERAL
# ==========================================
if seleccion == "🖥️ Monitor General":
    st.title("🖥️ Estado Global de Planta")
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols_mon = st.columns(6)
        for idx, m_mon in enumerate(lista):
            with cols_mon[idx % 6]:
                if m_mon in paradas: st.markdown(f"<div class='card-parada'>🚨 {m_mon}</div>", unsafe_allow_html=True)
                elif m_mon in activos: st.markdown(f"<div class='card-proceso'>⚙️ {m_mon}<br>OP: {activos[m_mon]['op']}</div>", unsafe_allow_html=True)
                else: st.markdown(f"<div class='card-libre'>⚪ {m_mon}</div>", unsafe_allow_html=True)

# ==========================================
# 2. SEGUIMIENTO HORARIO CORTADORAS (ESTILO TÁCTIL)
# ==========================================
elif seleccion == "⏱️ Seguimiento Cortadoras":
    st.title("⏱️ Seguimiento Horario de Rendimiento")
    st.info("Seleccione una máquina para registrar el avance de esta hora.")
    
    n_cols = 4
    cols_s = st.columns(n_cols)
    for i, m_btn in enumerate(MAQUINAS["CORTE"]):
        # Color especial si la máquina ya está activa en producción
        label = f"⚙️ {m_btn}" if m_btn in activos else m_btn
        if cols_s[i % n_cols].button(label, key=f"seg_{m_btn}", use_container_width=True):
            st.session_state.m_seg = m_btn

    if "m_seg" in st.session_state:
        m_s = st.session_state.m_seg
        st.subheader(f"📋 Registro Horario: {m_s}")
        
        # Intentar auto-rellenar datos si la máquina tiene una OP activa
        datos_previa = activos.get(m_s, {})
        
        with st.form("form_seg_tactil"):
            c1, c2, c3 = st.columns(3)
            op_f = c1.text_input("Número de OP", value=datos_previa.get('op', ""))
            tr_f = c2.text_input("Nombre del Trabajo", value=datos_previa.get('trabajo', ""))
            pa_f = c3.text_input("Tipo de Papel", value=datos_previa.get('tipo_papel', ""))
            
            c4, c5, c6 = st.columns(3)
            gr_f = c4.text_input("Gramaje", value=datos_previa.get('gramaje', ""))
            me_f = c5.text_input("Medida de Rollos", value=datos_previa.get('medida_rollos', ""))
            var_f = c6.number_input("Número Varillas Actual", 0)
            
            c7, c8, c9 = st.columns(3)
            caj_f = c7.number_input("Número de Cajas", 0)
            uni_f = c8.number_input("Unidades por Caja", value=datos_previa.get('unidades_caja', 0))
            pes_f = c9.number_input("Peso Aprox Rollo (Unidad)", 0.0)
            
            c10, c11 = st.columns(2)
            des_f = c10.number_input("Desperdicio de esta hora (Kg)", 0.0)
            mot_f = c11.text_input("Motivo Desperdicio")
            
            if st.form_submit_button("💾 GUARDAR REGISTRO HORARIO", use_container_width=True):
                data_seg = {
                    "maquina": m_s, "op": op_f, "nombre_trabajo": tr_f, "tipo_papel": pa_f,
                    "gramaje": gr_f, "medida_rollos": me_f, "n_varillas_actual": var_f,
                    "n_cajas": caj_f, "unidades_por_caja": uni_f, "peso_aprox_rollo": pes_f,
                    "desperdicio_kg": des_f, "motivo_desperdicio": mot_f
                }
                supabase.table("seguimiento_corte").insert(data_seg).execute()
                st.success(f"✅ Registro de {m_s} guardado.")
                # No hacemos rerun forzoso para que el usuario vea el mensaje de éxito

# ==========================================
# 3. MÓDULOS OPERATIVOS (TRABAJO NORMAL)
# ==========================================
else:
    mapa_areas = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_actual = mapa_areas[seleccion]
    st.title(f"Módulo: {area_actual}")

    n_cols = 5 if area_actual == "ENCUADERNACIÓN" else 4
    cols_v = st.columns(n_cols)
    for i, m_btn in enumerate(MAQUINAS[area_actual]):
        if cols_v[i % n_cols].button(m_btn, key=f"btn_{m_btn}", use_container_width=True):
            st.session_state.m_sel = m_btn

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_actual]:
        m = st.session_state.m_sel
        st.subheader(f"🛠️ Control: {m}")
        act, par = activos.get(m), paradas.get(m)

        if par:
            st.error("🚨 Máquina detenida.")
            if st.button("✅ REANUDAR TRABAJO", use_container_width=True):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()
        
        elif not act:
            with st.form("ini_op"):
                st.write("🆕 **INICIAR NUEVA OP**")
                c1, c2 = st.columns(2)
                op, tr = c1.text_input("Número de OP"), c2.text_input("Trabajo")
                extra = {}
                if area_actual == "IMPRESIÓN":
                    p1, p2, p3 = st.columns(3)
                    extra = {"tipo_papel": p1.text_input("Tipo Papel"), "ancho": p2.text_input("Ancho"), "gramaje": p3.text_input("Gramaje"), "medida_trabajo": p1.text_input("Medida")}
                elif area_actual == "CORTE":
                    p1, p2, p3 = st.columns(3)
                    extra = {"tipo_papel": p1.text_input("Papel"), "ancho": p2.text_input("Ancho"), "gramaje": p3.text_input("Gramaje"), "img_varilla": p1.number_input("Imágenes*Varilla", 0), "medida_rollos": p2.text_input("Medida Rollos")}
                elif area_actual == "COLECTORAS":
                    p1, p2 = st.columns(2)
                    extra = {"tipo_papel": p1.text_input("Tipo Papel"), "medida_trabajo": p2.text_input("Medida"), "unidades_caja": p1.number_input("Unidades*Caja", 0)}
                elif area_actual == "ENCUADERNACIÓN":
                    p1, p2 = st.columns(2)
                    extra = {"formas_totales": p1.number_input("Formas Totales", 0), "material": p2.text_input("Material"), "medida": p1.text_input("Medida")}
                
                if st.form_submit_button("▶️ INICIAR PRODUCCIÓN", use_container_width=True):
                    if op and tr:
                        data = {"maquina": m, "op": op, "trabajo": tr, "area": area_actual, "hora_inicio": datetime.now().strftime("%H:%M")}
                        data.update(extra)
                        supabase.table("trabajos_activos").insert(data).execute()
                        st.rerun()
        else:
            st.info(f"🟢 Produciendo: {act['trabajo']} (OP: {act['op']})")
            with st.form("cierre"):
                st.write("🏁 **CERRAR TRABAJO**")
                res = {}
                if area_actual == "IMPRESIÓN":
                    c1, c2 = st.columns(2); res = {"metros_impresos": c1.number_input("Metros", 0), "bobinas": c2.number_input("Bobinas", 0), "motivo_desperdicio": c1.text_input("Motivo Desp.")}
                elif area_actual == "CORTE":
                    c1, c2, c3 = st.columns(3); res = {"cant_varillas": c1.number_input("Varillas", 0), "unidades_caja": c2.number_input("Unidades/Caja", 0), "total_rollos": c3.number_input("Total Rollos", 0), "motivo_desperdicio": c1
