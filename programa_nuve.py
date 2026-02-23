import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    layout="wide", 
    page_title="SISTEMA NUVE MÓVIL", 
    page_icon="🏭",
    initial_sidebar_state="collapsed" # Colapsado para dar más espacio en móvil
)

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES (OPT. MÓVIL) ---
st.markdown("""
    <style>
    /* Optimización de botones para dedos (Touch Friendly) */
    .stButton > button {
        height: 85px !important;
        font-weight: bold;
        border-radius: 15px;
        font-size: 14px !important; /* Texto un poco más pequeño para que quepa */
        border: 2px solid #0D47A1;
        margin-bottom: 10px;
        white-space: pre-wrap !important; /* Permite saltos de línea en el nombre */
    }
    
    /* Cards responsivas */
    .card-proceso, .card-parada, .card-libre {
        padding: 10px;
        border-radius: 12px;
        text-align: center;
        font-weight: bold;
        font-size: 13px;
        margin-bottom: 5px;
    }
    .card-proceso { background-color: #E8F5E9; border-left: 6px solid #2E7D32; }
    .card-parada { background-color: #FFEBEE; border-left: 6px solid #C62828; }
    .card-libre { background-color: #F5F5F5; border-left: 6px solid #9E9E9E; color: #757575; }
    
    /* Títulos de área compactos */
    .title-area {
        background-color: #0D47A1;
        color: white;
        padding: 8px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        font-size: 16px;
        margin-top: 15px;
        margin-bottom: 10px;
    }

    /* Ajuste de contenedores para móvil */
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 calc(50% - 10px) !important; /* Fuerza 2 columnas en pantallas pequeñas */
        min-width: 150px !important;
    }
    
    /* Forzar tablas con scroll horizontal */
    .stDataFrame {
        width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LISTADO DE MÁQUINAS ---
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
opcion = st.sidebar.radio("MENÚ:", ["🖥️ Monitor", "📊 Consolidado", "⏱️ Seguimiento", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# ==========================================
# 1. MONITOR GENERAL (Responsivo)
# ==========================================
if opcion == "🖥️ Monitor":
    st.markdown("### 🖥️ Estatus Planta")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
    
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(2) # En móvil se verá en 2 columnas gracias al CSS superior
        for idx, m in enumerate(lista):
            with cols[idx % 2]:
                if m in paradas: st.markdown(f"<div class='card-parada'>🚨 {m}</div>", unsafe_allow_html=True)
                elif m in activos: st.markdown(f"<div class='card-proceso'>⚙️ {m}<br>OP:{activos[m]['op']}</div>", unsafe_allow_html=True)
                else: st.markdown(f"<div class='card-libre'>⚪ {m}</div>", unsafe_allow_html=True)

# ==========================================
# 2. SEGUIMIENTO CORTADORAS (Formulario Compacto)
# ==========================================
elif opcion == "⏱️ Seguimiento":
    st.markdown("### ⏱️ Progreso Cortadoras")
    with st.form("form_seg"):
        maq_s = st.selectbox("Máquina", MAQUINAS["CORTE"])
        op_s = st.text_input("Número de OP")
        tr_s = st.text_input("Nombre del Trabajo")
        med_s = st.text_input("Medida Rollo")
        met_s = st.number_input("Metros/Rollo", 0.0)
        var_s = st.number_input("Varillas Actuales", 0)
        caj_s = st.number_input("Cajas Actuales", 0)
        des_s = st.number_input("Desp. Kg", 0.0)
        
        if st.form_submit_button("REGISTRAR PROGRESO", use_container_width=True):
            h = datetime.now().hour
            t_act = "MAÑANA" if 6 <= h < 14 else "TARDE"
            payload = {"maquina": maq_s, "op": op_s, "trabajo": tr_s, "medida_rollo": med_s, "metros_rollo": met_s, "varillas_acumuladas": var_s, "cajas_acumuladas": caj_s, "desperidicio_acumulado": des_s, "turno": t_act}
            supabase.table("seguimiento_corte").insert(payload).execute()
            st.success(f"Guardado en turno {t_act}")

# ==========================================
# 3. CONSOLIDADO GERENCIAL (Tablas con Scroll)
# ==========================================
elif opcion == "📊 Consolidado":
    st.markdown("### 📊 Reporte Gerencial")
    try:
        imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
        cor = pd.DataFrame(supabase.table("corte").select("*").execute().data)
        seg = pd.DataFrame(supabase.table("seguimiento_corte").select("*").execute().data)
        
        tabs = st.tabs(["🔗 Cruce", "⏱️ Turnos", "🖨️ Imp", "✂️ Cor"])
        
        with tabs[0]:
            if not imp.empty:
                df_i = imp[['op', 'trabajo', 'maquina', 'h_inicio', 'h_fin', 'tipo_papel', 'ancho', 'gramaje', 'medida_trabajo', 'metros_impresos', 'desp_kg']].copy()
                df_i.columns = ['OP', 'TRABAJO', 'MAQ_IMP', 'INI_I', 'FIN_I', 'PAPEL', 'ANCHO', 'GRAM', 'MEDIDA', 'METROS', 'DESP_I']
                df_c = cor[['op', 'maquina', 'total_rollos', 'desp_kg']].copy() if not cor.empty else pd.DataFrame(columns=['op'])
                if not cor.empty: df_c.columns = ['OP', 'MAQ_COR', 'ROLLOS', 'DESP_C']
                
                m = pd.merge(df_i, df_c, on='OP', how='left')
                m['KPI_DESP'] = m['DESP_I'].fillna(0) + m['DESP_C'].fillna(0)
                m['KPI_EFIC'] = (m['ROLLOS'].fillna(0) / m['METROS']).replace([float('inf')], 0).round(2)
                st.dataframe(m, use_container_width=False) # Permite scroll lateral natural

        with tabs[1]:
            if not seg.empty:
                res = seg.groupby(['fecha','turno','maquina','op']).agg({'varillas_acumuladas':'max','cajas_acumuladas':'max'}).reset_index()
                st.dataframe(res)
    except: st.info("Esperando sincronización de datos...")

# ==========================================
# 4. JOYSTICKS DE ÁREA (Formulario Adaptativo)
# ==========================================
else:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_act = area_map[opcion]
    st.markdown(f"### 🕹️ {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    # Botones en 2 columnas para móvil
    cols_j = st.columns(2)
    for i, m in enumerate(MAQUINAS[area_act]):
        lbl = f"⚙️ {m}\nOP: {activos[m]['op']}" if m in activos else (f"🚨 {m}" if m in paradas else f"⚪ {m}")
        if cols_j[i % 2].button(lbl, key=f"joy_{m}", use_container_width=True): 
            st.session_state.m_sel = m

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        act = activos.get(m)
        par = paradas.get(m)

        if par:
            st.error(f"Máquina {m} Parada")
            if st.button(f"REANUDAR", use_container_width=True):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()
        elif not act:
            with st.form("ini_mob"):
                st.subheader(f"Iniciar {m}")
                op_i = st.text_input("OP")
                tr_i = st.text_input("Trabajo")
                ext = {}
                if area_act == "IMPRESIÓN":
                    ext = {"tipo_papel": st.text_input("Papel"), "ancho": st.text_input("Ancho"), "gramaje": st.text_input("Gramaje"), "medida_trabajo": st.text_input("Medida")}
                elif area_act == "CORTE":
                    ext = {"tipo_papel": st.text_input("Papel"), "img_varilla": st.number_input("Img/Varilla", 0), "unidades_caja": st.number_input("Und/Caja", 0)}
                elif area_act == "COLECTORAS":
                    ext = {"tipo_papel": st.text_input("Papel"), "unidades_caja": st.number_input("Und/Caja", 0)}
                elif area_act == "ENCUADERNACIÓN":
                    ext = {"material": st.text_input("Material"), "medida": st.text_input("Medida")}
                
                if st.form_submit_button("COMENZAR", use_container_width=True):
                    d = {"maquina": m, "op": op_i, "trabajo": tr_i, "area": area_act, "hora_inicio": datetime.now().strftime("%H:%M")}
                    d.update(ext)
                    supabase.table("trabajos_activos").insert(d).execute()
                    st.rerun()
        else:
            st.success(f"OP: {act['op']} en curso")
            if st.button("🛑 PARADA", use_container_width=True):
                mot = st.text_input("Motivo")
                if mot:
                    supabase.table("paradas_maquina").insert({"maquina": m, "op": act['op'], "motivo": mot, "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                    st.rerun()

            with st.form("fin_mob"):
                st.subheader("Finalizar")
                res = {}
                if area_act == "IMPRESIÓN":
                    res = {"metros_impresos": st.number_input("Metros", 0.0), "bobinas": st.number_input("Bobinas", 0)}
                elif area_act == "CORTE":
                    res = {"total_rollos": st.number_input("Rollos", 0), "cant_varillas": st.number_input("Varillas", 0), "medida_rollos": st.text_input("Medida")}
                elif area_act == "COLECTORAS":
                    res = {"total_cajas": st.number_input("Cajas", 0), "total_formas": st.number_input("Formas", 0)}
                elif area_act == "ENCUADERNACIÓN":
                    res = {"cant_final": st.number_input("Cantidad", 0), "presentacion": st.text_input("Presentación")}
                
                dk = st.number_input("Desp. Kg", 0.0)
                mot_d = st.text_input("Motivo Desp.")
                obs = st.text_area("Observaciones")
                
                if st.form_submit_button("GUARDAR", use_container_width=True):
                    final = {"op": act['op'], "maquina": m, "trabajo": act['trabajo'], "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"), "desp_kg": dk, "motivo_desperdicio": mot_d, "observaciones": obs}
                    # Arrastrar datos del inicio
                    for k in ["tipo_papel", "ancho", "gramaje", "medida_trabajo", "img_varilla", "unidades_caja", "material", "medida"]:
                        if k in act: final[k] = act[k]
                    
                    supabase.table(normalizar(area_act)).insert(final).execute()
                    supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                    st.rerun()
