import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA DE PRODUCCIÓN", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 75px; font-weight: bold; border-radius: 12px; font-size: 16px; border: 2px solid #0D47A1; }
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

def calcular_horas(inicio, fin):
    if not inicio or not fin or str(fin) == "None": return 0.0
    try:
        t_ini = datetime.strptime(inicio, "%H:%M")
        t_fin = datetime.strptime(fin, "%H:%M")
        return round((t_fin - t_ini).total_seconds() / 3600, 2)
    except: return 0.0

# Función para evitar error de tablas vacías
def obtener_df(tabla):
    try:
        res = supabase.table(tabla).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- NAVEGACIÓN ---
st.sidebar.title("🏭 MENÚ PRINCIPAL")
opcion = st.sidebar.radio("Ir a:", ["🖥️ Monitor General", "📊 Consolidado Gerencial", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# ==========================================
# 1. MONITOR GENERAL
# ==========================================
if opcion == "🖥️ Monitor General":
    st.title("🖥️ Estatus en Tiempo Real")
    activos_data = supabase.table("trabajos_activos").select("*").execute().data
    paradas_data = supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data
    
    activos = {a['maquina']: a for a in activos_data} if activos_data else {}
    paradas = {p['maquina']: p for p in paradas_data} if paradas_data else {}
    
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(6)
        for idx, m in enumerate(lista):
            with cols[idx % 6]:
                if m in paradas: st.markdown(f"<div class='card-parada'>🚨 {m}</div>", unsafe_allow_html=True)
                elif m in activos: st.markdown(f"<div class='card-proceso'>⚙️ {m}<br>OP: {activos[m]['op']}</div>", unsafe_allow_html=True)
                else: st.markdown(f"<div class='card-libre'>⚪ {m}</div>", unsafe_allow_html=True)

# ==========================================
# 2. CONSOLIDADO GERENCIAL
# ==========================================
elif opcion == "📊 Consolidado Gerencial":
    st.title("📊 Panel Integral de Control Gerencial")

    # Carga segura para evitar errores
    imp = obtener_df("impresion")
    cor = obtener_df("corte")
    paradas = obtener_df("paradas_maquina")
    col = obtener_df("colectoras")
    enc = obtener_df("encuadernacion")

    # --- RESUMEN EJECUTIVO (KPIs) ---
    st.subheader("💡 Indicadores Clave de Desempeño (KPIs)")
    k1, k2, k3, k4 = st.columns(4)
    
    # Horas de Paro
    hrs_paro_total = 0.0
    if not paradas.empty and 'h_fin' in paradas.columns:
        valid_paradas = paradas.dropna(subset=['h_fin'])
        hrs_paro_total = valid_paradas.apply(lambda r: calcular_horas(str(r['h_inicio']), str(r['h_fin'])), axis=1).sum()
    
    # Valores seguros
    m_impresos = imp['metros_impresos'].sum() if not imp.empty and 'metros_impresos' in imp.columns else 0
    t_rollos = cor['total_rollos'].sum() if not cor.empty and 'total_rollos' in cor.columns else 0
    d_imp = imp['desp_kg'].sum() if not imp.empty and 'desp_kg' in imp.columns else 0
    d_cor = cor['desp_kg'].sum() if not cor.empty and 'desp_kg' in cor.columns else 0
    
    k1.metric("Tiempo Muerto", f"{hrs_paro_total:.2f} Hrs")
    k2.metric("Metraje Impreso", f"{m_impresos:,.0f} m")
    k3.metric("Total Rollos", f"{t_rollos:,.0f}")
    k4.metric("Desperdicio (I+C)", f"{d_imp + d_cor:.1f} Kg")

    t1, t2, t3, t4, t5, t6 = st.tabs(["🔗 Cruce Operativo", "🚨 Historial Paradas", "🖨️ Historial Impresión", "✂️ Historial Corte", "📥 Colectoras", "📕 Encuadernación"])

    with t1:
        st.subheader("Cruce Operativo de Producción")
        if not imp.empty and not cor.empty:
            merged = pd.merge(imp[['op', 'trabajo', 'maquina', 'h_inicio', 'h_fin', 'metros_impresos']], 
                              cor[['op', 'maquina', 'total_rollos']], on='op', how='left', suffixes=('_IMP', '_COR'))
            st.dataframe(merged, use_container_width=True)
        else: st.info("Esperando datos para realizar el cruce...")

    with t2:
        if not paradas.empty:
            paradas['hrs_paro'] = paradas.apply(lambda r: calcular_horas(str(r['h_inicio']), str(r['h_fin'])), axis=1)
            st.dataframe(paradas, use_container_width=True)
            if 'motivo' in paradas.columns:
                st.bar_chart(paradas.groupby('motivo')['hrs_paro'].sum())
        else: st.info("No hay registros de paradas.")

    with t3: st.dataframe(imp, use_container_width=True) if not imp.empty else st.info("Historial vacío.")
    with t4: st.dataframe(cor, use_container_width=True) if not cor.empty else st.info("Historial vacío.")
    with t5: st.dataframe(col, use_container_width=True) if not col.empty else st.info("Historial vacío.")
    with t6: st.dataframe(enc, use_container_width=True) if not enc.empty else st.info("Historial vacío.")

# ==========================================
# 3. JOYSTICKS DE ÁREA
# ==========================================
else:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_act = area_map[opcion]
    st.title(f"Panel de Control: {area_act}")
    
    activos_res = supabase.table("trabajos_activos").select("*").execute().data
    paradas_res = supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data
    
    activos = {a['maquina']: a for a in activos_res} if activos_res else {}
    paradas = {p['maquina']: p for p in paradas_res} if paradas_res else {}

    cols_m = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS[area_act]):
        label = m_btn
        if m_btn in paradas: label = f"🚨 {m_btn}"
        elif m_btn in activos: label = f"⚙️ {m_btn}\nOP: {activos[m_btn]['op']}"
        
        if cols_m[i % 4].button(label, key=f"btn_{m_btn}", use_container_width=True):
            st.session_state.m_sel = m_btn

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        act, par = activos.get(m), paradas.get(m)
        st.divider()

        if par:
            st.error(f"⚠️ MÁQUINA EN PARADA: {par['motivo']} desde {par['h_inicio']}")
            if st.button("REANUDAR TRABAJO"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()

        elif not act:
            with st.form("inicio_op"):
                st.subheader(f"🚀 Iniciar Operación en {m}")
                c1, c2 = st.columns(2)
                op = c1.text_input("Número de OP")
                tr = c2.text_input("Nombre del Trabajo")
                
                extra = {}
                if area_act == "IMPRESIÓN":
                    k1, k2, k3, k4 = st.columns(4)
                    extra = {"tipo_papel": k1.text_input("Tipo de Papel"), "ancho": k2.text_input("Ancho"), "gramaje": k3.text_input("Gramaje"), "medida_trabajo": k4.text_input("Medida Trabajo")}
                elif area_act == "CORTE":
                    k1, k2, k3, k4 = st.columns(4)
                    extra = {"tipo_papel": k1.text_input("Tipo de Papel"), "img_varilla": k2.number_input("Img/Varilla", 0), "medida_rollos": k3.text_input("Medida Rollos"), "unidades_caja": k4.number_input("Und/Caja", 0)}
                elif area_act == "COLECTORAS":
                    k1, k2, k3 = st.columns(3)
                    extra = {"tipo_papel": k1.text_input("Tipo de Papel"), "medida_trabajo": k2.text_input("Medida"), "unidades_caja": k3.number_input("Und/Caja", 0)}
                elif area_act == "ENCUADERNACIÓN":
                    k1, k2, k3 = st.columns(3)
                    extra = {"formas_totales": k1.number_input("Formas Totales", 0), "material": k2.text_input("Material"), "medida": k3.text_input("Medida")}

                if st.form_submit_button("EMPEZAR TURNO"):
                    if op and tr:
                        data = {"maquina": m, "op": op, "trabajo": tr, "area": area_act, "hora_inicio": datetime.now().strftime("%H:%M")}
                        data.update(extra)
                        supabase.table("trabajos_activos").insert(data).execute()
                        st.rerun()
        else:
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🚨 REGISTRAR PARADA"):
                    st.session_state.show_parada = True
            if st.session_state.get("show_parada"):
                mot_p = st.selectbox("Motivo de la parada:", ["Mecánico", "Eléctrico", "Cambio Rollo", "Limpieza", "Almuerzo", "Falta Material"])
                if st.button("Confirmar Parada"):
                    supabase.table("paradas_maquina").insert({"maquina": m, "op": act['op'], "motivo": mot_p, "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                    st.session_state.show_parada = False
                    st.rerun()

            with st.form("cierre_op"):
                st.info(f"Finalizando Trabajo: {act['op']} - {act['trabajo']}")
                res = {}
                if area_act == "IMPRESIÓN":
                    f1, f2 = st.columns(2)
                    res = {"metros_impresos": f1.number_input("Metros Impresos", 0.0), "bobinas": f2.number_input("Bobinas Usadas", 0)}
                elif area_act == "CORTE":
                    f1, f2, f3 = st.columns(3)
                    res = {"total_rollos": f1.number_input("Total Rollos", 0), "cant_varillas": f2.number_input("Cant. Varillas", 0), "unidades_caja": f3.number_input("Unidades/Caja", 0)}
                elif area_act == "COLECTORAS":
                    f1, f2 = st.columns(2)
                    res = {"total_cajas": f1.number_input("Total Cajas", 0), "total_formas": f2.number_input("Total Formas", 0)}
                elif area_act == "ENCUADERNACIÓN":
                    f1, f2 = st.columns(2)
                    res = {"cant_final": f1.number_input("Cantidad Final", 0), "presentacion": f2.text_input("Presentación")}

                dk = st.number_input("Desperdicio (Kg)", 0.0)
                mot = st.text_input("Motivo Desperdicio")
                obs = st.text_area("Observaciones")

                if st.form_submit_button("🏁 FINALIZAR Y GUARDAR"):
                    final_data = {
                        "op": act['op'], "maquina": m, "trabajo": act['trabajo'],
                        "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                        "desp_kg": safe_float(dk), "motivo_desperdicio": mot, "observaciones": obs
                    }
                    final_data.update(res)
                    
                    nom_t = normalizar(area_act)
                    cols_por_tabla = {
                        "impresion": ["tipo_papel", "ancho", "gramaje", "medida_trabajo"],
                        "corte": ["tipo_papel", "ancho", "gramaje", "img_varilla", "medida_rollos", "unidades_caja"],
                        "colectoras": ["tipo_papel", "medida_trabajo", "unidades_caja"],
                        "encuadernacion": ["formas_totales", "material", "medida"]
                    }

                    for col_name in cols_por_tabla.get(nom_t, []):
                        if col_name in act: final_data[col_name] = act[col_name]

                    try:
                        supabase.table(nom_t).insert(final_data).execute()
                        supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

