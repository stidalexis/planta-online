import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA DE PRODUCCIÓN NUVE", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES (CSS) ---
st.markdown("""
    <style>
    .stButton > button { height: 75px; font-weight: bold; border-radius: 12px; font-size: 16px; border: 2px solid #0D47A1; }
    .card-proceso { padding: 15px; border-radius: 10px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; text-align: center; font-weight: bold; }
    .card-parada { padding: 15px; border-radius: 10px; background-color: #FFEBEE; border-left: 8px solid #C62828; text-align: center; font-weight: bold; }
    .card-libre { padding: 15px; border-radius: 10px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- LISTADO DE MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- FUNCIONES DE UTILIDAD ---
def normalizar(texto):
    reemplazos = {"Í": "I", "Ó": "O", "Á": "A", "É": "E", "Ú": "U", " ": "_"}
    t = texto.upper()
    for k, v in reemplazos.items(): t = t.replace(k, v)
    return t.lower()

def safe_float(valor):
    if valor is None or valor == "": return 0.0
    try: return float(str(valor).replace(',', '.'))
    except: return 0.0

# --- NAVEGACIÓN LATERAL ---
st.sidebar.title("🏭 MENÚ NUVE")
opcion = st.sidebar.radio("Ir a:", ["🖥️ Monitor General", "📊 Consolidado Gerencial", "⏱️ Seguimiento Cortadoras", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# ==========================================
# 1. MONITOR GENERAL
# ==========================================
if opcion == "🖥️ Monitor General":
    st.title("🖥️ Estatus de Planta en Tiempo Real")
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
# 2. SEGUIMIENTO CORTADORAS (HORARIO)
# ==========================================
elif opcion == "⏱️ Seguimiento Cortadoras":
    st.title("⏱️ Reporte de Progreso de Cortadoras")
    with st.form("form_seg_horario"):
        c1, c2, c3 = st.columns(3)
        maq_s = c1.selectbox("Máquina", MAQUINAS["CORTE"])
        op_s = c2.text_input("Número de OP")
        tr_s = c3.text_input("Nombre del Trabajo")
        
        k1, k2, k3, k4, k5 = st.columns(5)
        med_s = k1.text_input("Medida del Rollo")
        met_s = k2.number_input("Metros por Rollo", 0.0)
        var_s = k3.number_input("Varillas producidas hasta ahora", 0)
        caj_s = k4.number_input("Cajas empacadas hasta ahora", 0)
        des_s = k5.number_input("Desp. acumulado (Kg)", 0.0)
        
        if st.form_submit_button("REGISTRAR PROGRESO"):
            h = datetime.now().hour
            t_act = "MAÑANA" if 6 <= h < 14 else "TARDE"
            payload = {
                "maquina": maq_s, "op": op_s, "trabajo": tr_s, "medida_rollo": med_s,
                "metros_rollo": met_s, "varillas_acumuladas": var_s, "cajas_acumuladas": caj_s,
                "desperidicio_acumulado": des_s, "turno": t_act
            }
            supabase.table("seguimiento_corte").insert(payload).execute()
            st.success(f"Progreso registrado para el turno {t_act}")

# ==========================================
# 3. CONSOLIDADO GERENCIAL (BLINDADO)
# ==========================================
elif opcion == "📊 Consolidado Gerencial":
    st.title("📊 Consolidado de Producción y KPIs")
    try:
        imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
        cor = pd.DataFrame(supabase.table("corte").select("*").execute().data)
        col = pd.DataFrame(supabase.table("colectoras").select("*").execute().data)
        enc = pd.DataFrame(supabase.table("encuadernacion").select("*").execute().data)
        seg = pd.DataFrame(supabase.table("seguimiento_corte").select("*").execute().data)
        
        t1, t_seg, t3, t4, t5, t6 = st.tabs(["🔗 Cruce Imp-Cor", "⏱️ Rendimiento Turnos", "🖨️ Hist. Impresión", "✂️ Hist. Corte", "📥 Colectoras", "📕 Encuadernación"])
        
        with t1:
            st.subheader("Cruce Operativo Integral por OP (Blindado)")
            if not imp.empty:
                df_i = imp[['op', 'trabajo', 'maquina', 'h_inicio', 'h_fin', 'tipo_papel', 'ancho', 'gramaje', 'medida_trabajo', 'metros_impresos', 'desp_kg', 'observaciones']].copy()
                df_i.columns = ['OP', 'TRABAJO', 'MAQ_IMP', 'INI_I', 'FIN_I', 'PAPEL_I', 'ANCHO_I', 'GRAM_I', 'MEDIDA_I', 'METROS_I', 'DESP_I', 'OBS_I']
                
                df_c = cor[['op', 'maquina', 'h_inicio', 'h_fin', 'img_varilla', 'medida_rollos', 'cant_varillas', 'unidades_caja', 'total_rollos', 'desp_kg', 'observaciones']].copy() if not cor.empty else pd.DataFrame(columns=['op'])
                if not cor.empty:
                    df_c.columns = ['OP', 'MAQ_COR', 'INI_C', 'FIN_C', 'IMG_VAR', 'MED_ROLLO', 'VARILLAS', 'UND_CAJA', 'ROLLOS_C', 'DESP_C', 'OBS_C']
                
                m = pd.merge(df_i, df_c, on='OP', how='left')
                m['💡 KPI_DESP_TOTAL_KG'] = m['DESP_I'].fillna(0) + m['DESP_C'].fillna(0)
                m['💡 KPI_ROLLOS_x_METRO'] = (m['ROLLOS_C'].fillna(0) / m['METROS_I']).replace([float('inf')], 0).round(2)
                
                st.dataframe(m, use_container_width=True)

        with t_seg:
            st.subheader("Rendimiento Máximo por Turno")
            if not seg.empty:
                res = seg.groupby(['fecha','turno','maquina','op','trabajo']).agg({'varillas_acumuladas':'max','cajas_acumuladas':'max', 'desperidicio_acumulado':'max'}).reset_index()
                st.dataframe(res, use_container_width=True)
        
        with t3: st.dataframe(imp, use_container_width=True)
        with t4: st.dataframe(cor, use_container_width=True)
        with t5: st.dataframe(col, use_container_width=True)
        with t6: st.dataframe(enc, use_container_width=True)
    except: st.info("Cargando datos de la base...")

# ==========================================
# 4. JOYSTICKS DE ÁREA (TODO EL ORIGINAL)
# ==========================================
else:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_act = area_map[opcion]
    st.title(f"Joystick Operativo: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    # MATRIZ DE BOTONES
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS[area_act]):
        if m in paradas: lbl = f"🚨 {m}"
        elif m in activos: lbl = f"⚙️ {m}\nOP: {activos[m]['op']}"
        else: lbl = f"⚪ {m}"
        if cols[i % 4].button(lbl, key=f"btn_{m}", use_container_width=True): st.session_state.m_sel = m

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        act, par = activos.get(m), paradas.get(m)

        if par:
            st.error(f"Máquina {m} en Parada")
            if st.button(f"REANUDAR TRABAJO EN {m}"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()
        elif not act:
            with st.form("form_inicio"):
                st.subheader(f"🚀 Iniciar Operación en {m}")
                c1, c2 = st.columns(2); op_i, tr_i = c1.text_input("Número de OP"), c2.text_input("Nombre del Trabajo")
                ext = {}
                if area_act == "IMPRESIÓN":
                    k1, k2, k3, k4 = st.columns(4)
                    ext = {"tipo_papel": k1.text_input("Tipo de Papel"), "ancho": k2.text_input("Ancho (pulg)"), "gramaje": k3.text_input("Gramaje"), "medida_trabajo": k4.text_input("Medida Trabajo")}
                elif area_act == "CORTE":
                    k1, k2, k3, k4, k5 = st.columns(5)
                    ext = {"tipo_papel": k1.text_input("Papel"), "ancho": k2.text_input("Ancho"), "gramaje": k3.text_input("Gramaje"), "img_varilla": k4.number_input("Imágenes por Varilla", 0), "unidades_caja": k5.number_input("Unidades por Caja", 0)}
                elif area_act == "COLECTORAS":
                    k1, k2, k3 = st.columns(3)
                    ext = {"tipo_papel": k1.text_input("Papel"), "medida_trabajo": k2.text_input("Medida"), "unidades_caja": k3.number_input("Unidades por Caja", 0)}
                elif area_act == "ENCUADERNACIÓN":
                    k1, k2, k3 = st.columns(3)
                    ext = {"formas_totales": k1.number_input("Formas Totales", 0), "material": k2.text_input("Material Usado"), "medida": k3.text_input("Medida Final")}
                
                if st.form_submit_button("COMENZAR TRABAJO"):
                    d = {"maquina": m, "op": op_i, "trabajo": tr_i, "area": area_act, "hora_inicio": datetime.now().strftime("%H:%M")}
                    d.update(ext)
                    supabase.table("trabajos_activos").insert(d).execute()
                    st.rerun()
        else:
            st.success(f"Trabajando OP: {act['op']} en {m}")
            if st.button("🚨 REGISTRAR PARADA DE MÁQUINA"):
                mot = st.text_input("Motivo de la parada")
                if mot:
                    supabase.table("paradas_maquina").insert({"maquina": m, "op": act['op'], "motivo": mot, "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                    st.rerun()

            with st.form("form_finalizar"):
                st.subheader(f"🏁 Finalizar OP: {act['op']}")
                res = {}
                if area_act == "IMPRESIÓN":
                    f1, f2 = st.columns(2); res = {"metros_impresos": f1.number_input("Metros Totales", 0.0), "bobinas": f2.number_input("Bobinas Usadas", 0)}
                elif area_act == "CORTE":
                    f1, f2, f3 = st.columns(3); res = {"total_rollos": f1.number_input("Total Rollos", 0), "cant_varillas": f2.number_input("Varillas Cortadas", 0), "medida_rollos": f3.text_input("Medida de Rollos")}
                elif area_act == "COLECTORAS":
                    f1, f2 = st.columns(2); res = {"total_cajas": f1.number_input("Cajas Totales", 0), "total_formas": f2.number_input("Formas Totales", 0)}
                elif area_act == "ENCUADERNACIÓN":
                    f1, f2 = st.columns(2); res = {"cant_final": f1.number_input("Unidades Finales", 0), "presentacion": f2.text_input("Presentación (Paquetes/Cajas)")}
                
                dk = st.number_input("Desperdicio Total (Kg)", 0.0)
                mot_d = st.text_input("Motivo del Desperdicio")
                obs = st.text_area("Observaciones Generales")
                
                if st.form_submit_button("FINALIZAR Y GUARDAR HISTORIAL"):
                    final = {
                        "op": act['op'], "maquina": m, "trabajo": act['trabajo'], 
                        "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"), 
                        "desp_kg": dk, "motivo_desperdicio": mot_d, "observaciones": obs
                    }
                    # RECUPERAR DATOS DEL INICIO (HERENCIA)
                    for k in ["tipo_papel", "ancho", "gramaje", "medida_trabajo", "img_varilla", "unidades_caja", "formas_totales", "material", "medida"]:
                        if k in act: final[k] = act[k]
                    
                    supabase.table(normalizar(area_act)).insert(final).execute()
                    supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                    st.rerun()
