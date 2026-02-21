import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="PRODUCCIÓN 360 - PLANTA", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 70px; font-weight: bold; border-radius: 12px; font-size: 16px; border: 2px solid #0D47A1; }
    .card-proceso { padding: 15px; border-radius: 10px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; text-align: center; }
    .card-parada { padding: 15px; border-radius: 10px; background-color: #FFEBEE; border-left: 8px solid #C62828; text-align: center; }
    .card-libre { padding: 15px; border-radius: 10px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- FUNCIONES TÉCNICAS ---
def normalizar(texto):
    reemplazos = {"Í": "I", "Ó": "O", "Á": "A", "É": "E", "Ú": "U", " ": "_"}
    t = str(texto).upper()
    for k, v in reemplazos.items(): t = t.replace(k, v)
    return t.lower()

def safe_float(valor):
    if valor is None or valor == "": return 0.0
    try: return float(str(valor).replace(',', '.'))
    except: return 0.0

def calcular_horas(inicio, fin):
    try:
        if not inicio or not fin: return 0.0
        t_ini = datetime.strptime(str(inicio), "%H:%M")
        t_fin = datetime.strptime(str(fin), "%H:%M")
        diff = (t_fin - t_ini).total_seconds() / 3600
        return round(diff if diff > 0 else diff + 24, 2)
    except: return 0.0

# --- LÓGICA DE NAVEGACIÓN ---
opcion = st.sidebar.radio("MENÚ PRINCIPAL", ["🖥️ Monitor Real-Time", "📊 Consolidados Gerenciales", "🖨️ Área Impresión", "✂️ Área Corte", "📥 Área Colectoras", "📕 Área Encuadernación"])

# ==========================================
# 1. MONITOR REAL-TIME
# ==========================================
if opcion == "🖥️ Monitor Real-Time":
    st.title("🖥️ Estatus de Maquinaria")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
    
    for area, lista in MAQUINAS.items():
        st.subheader(area)
        cols = st.columns(6)
        for idx, m in enumerate(lista):
            with cols[idx % 6]:
                if m in paradas: st.markdown(f"<div class='card-parada'>🚨 {m}<br><small>{paradas[m]['motivo']}</small></div>", unsafe_allow_html=True)
                elif m in activos: st.markdown(f"<div class='card-proceso'>⚙️ {m}<br>OP: {activos[m]['op']}</div>", unsafe_allow_html=True)
                else: st.markdown(f"<div class='card-libre'>⚪ {m}</div>", unsafe_allow_html=True)

# ==========================================
# 2. CONSOLIDADO GERENCIAL (FULL)
# ==========================================
elif opcion == "📊 Consolidados Gerenciales":
    st.title("📊 Reportes de Eficiencia y Tiempos")
    
    imp_q = supabase.table("impresion").select("*").execute().data
    cor_q = supabase.table("corte").select("*").execute().data
    col_q = supabase.table("colectoras").select("*").execute().data
    enc_q = supabase.table("encuadernacion").select("*").execute().data

    t1, t2, t3, t4, t5 = st.tabs(["🏆 MAESTRO (IMP+COR)", "🖨️ IMPRESIÓN", "✂️ CORTE", "📥 COLECTORAS", "📕 ENCUADERNACIÓN"])

    with t1:
        if imp_q and cor_q:
            df_i = pd.DataFrame(imp_q)
            df_c = pd.DataFrame(cor_q)
            
            # Limpieza para el merge
            df_i_sub = df_i[['op', 'trabajo', 'maquina', 'h_inicio', 'h_fin', 'ancho', 'gramaje', 'metros_impresos', 'desp_kg']].copy()
            df_i_sub.columns = ['OP', 'TRABAJO', 'MAQ_IMP', 'INI_IMP', 'FIN_IMP', 'ANCHO', 'GRAM', 'METROS', 'DESP_IMP']
            
            df_c_sub = df_c[['op', 'maquina', 'h_inicio', 'h_fin', 'desp_kg']].copy()
            df_c_sub.columns = ['OP', 'MAQ_COR', 'INI_COR', 'FIN_COR', 'DESP_COR']
            
            # MERGE MAESTRO
            master = pd.merge(df_i_sub, df_c_sub, on='OP', how='left')
            
            # Cálculos Horarios
            master['H_IMP'] = master.apply(lambda r: calcular_horas(r['INI_IMP'], r['FIN_IMP']), axis=1)
            master['H_COR'] = master.apply(lambda r: calcular_horas(r['INI_COR'], r['FIN_COR']), axis=1)
            master['TIEMPO_TOTAL'] = master['H_IMP'] + master['H_COR']
            
            # Cálculos de Masa
            master['KG_INI'] = master.apply(lambda r: round(((safe_float(r['ANCHO'])/1000) * safe_float(r['METROS']) * safe_float(r['GRAM']))/100, 2), axis=1)
            master['MERMA_TOTAL'] = master.apply(lambda r: safe_float(r['DESP_IMP']) + safe_float(r['DESP_COR']), axis=1)
            master['EFICIENCIA'] = master.apply(lambda r: f"{round(((r['KG_INI']-r['MERMA_TOTAL'])/r['KG_INI']*100),1)}%" if r['KG_INI']>0 else "0%", axis=1)
            
            st.dataframe(master.sort_values(by='OP', ascending=False), use_container_width=True)
            
        else:
            st.info("Faltan datos en Impresión o Corte para generar el Maestro.")

    with t2: st.dataframe(pd.DataFrame(imp_q), use_container_width=True) if imp_q else st.write("Sin datos")
    with t3: st.dataframe(pd.DataFrame(cor_q), use_container_width=True) if cor_q else st.write("Sin datos")
    with t4: st.dataframe(pd.DataFrame(col_q), use_container_width=True) if col_q else st.write("Sin datos")
    with t5: st.dataframe(pd.DataFrame(enc_q), use_container_width=True) if enc_q else st.write("Sin datos")

# ==========================================
# 3. JOYSTICKS DE ÁREA
# ==========================================
else:
    area_mapping = {"🖨️ Área Impresión": "IMPRESIÓN", "✂️ Área Corte": "CORTE", "📥 Área Colectoras": "COLECTORAS", "📕 Área Encuadernación": "ENCUADERNACIÓN"}
    area_actual = area_mapping[opcion]
    st.title(f"Control: {area_actual}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    # SELECCIÓN DE MÁQUINA (GRID)
    m_cols = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS[area_actual]):
        label = m_btn
        if m_btn in paradas: label = f"🚨 {m_btn}"
        elif m_btn in activos: label = f"⚙️ {m_btn} (OP {activos[m_btn]['op']})"
        if m_cols[i % 4].button(label, key=f"btn_{m_btn}", use_container_width=True):
            st.session_state.m_sel = m_btn

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_actual]:
        m = st.session_state.m_sel
        act, par = activos.get(m), paradas.get(m)
        st.divider()

        if not act:
            with st.form("inicio_form"):
                st.subheader(f"🚀 Iniciar OP en {m}")
                c1, c2 = st.columns(2)
                op_in, tr_in = c1.text_input("N° OP"), c2.text_input("Nombre Trabajo")
                
                extra = {}
                # CAMPOS COMPLETOS SEGÚN TU ESQUEMA SQL ORIGINAL
                if area_actual == "IMPRESIÓN":
                    k1, k2, k3, k4 = st.columns(4)
                    extra = {"tipo_papel": k1.text_input("Papel"), "ancho": k2.text_input("Ancho"), "gramaje": k3.text_input("Gramaje"), "medida_trabajo": k4.text_input("Medida")}
                elif area_actual == "CORTE":
                    k1, k2, k3, k4 = st.columns(4)
                    extra = {"tipo_papel": k1.text_input("Papel"), "ancho": k2.text_input("Ancho"), "gramaje": k3.text_input("Gramaje"), "img_varilla": k4.number_input("Img/Var", 0)}
                elif area_actual == "COLECTORAS":
                    k1, k2, k3 = st.columns(3)
                    extra = {"tipo_papel": k1.text_input("Papel"), "medida_trabajo": k2.text_input("Medida"), "unidades_caja": k3.number_input("Und/Caja", 0)}
                elif area_actual == "ENCUADERNACIÓN":
                    k1, k2, k3 = st.columns(3)
                    extra = {"formas_totales": k1.number_input("Formas", 0), "material": k2.text_input("Material"), "medida": k3.text_input("Medida")}

                if st.form_submit_button("INICIAR TURNO"):
                    if op_in and tr_in:
                        data = {"maquina": m, "op": op_in, "trabajo": tr_in, "area": area_actual, "hora_inicio": datetime.now().strftime("%H:%M")}
                        data.update(extra)
                        supabase.table("trabajos_activos").insert(data).execute()
                        st.rerun()
        else:
            # LÓGICA DE PARADAS (REANUDAR / DETENER)
            if par:
                st.error(f"🛑 MÁQUINA DETENIDA POR: {par['motivo']}")
                if st.button("▶️ REANUDAR TRABAJO"):
                    supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                    st.rerun()
            else:
                c_p1, c_p2 = st.columns([3, 1])
                c_p1.success(f"TRABAJANDO: OP {act['op']} - {act['trabajo']}")
                with c_p2:
                    with st.popover("🚨 REGISTRAR PARADA"):
                        mot_p = st.selectbox("Causa", ["Mecánico", "Eléctrico", "Ajuste/Limpia", "Falta Material", "Cambio Rollo"])
                        if st.button("CONFIRMAR DETENCIÓN"):
                            supabase.table("paradas_maquina").insert({"maquina": m, "op": act['op'], "motivo": mot_p, "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                            st.rerun()

                with st.form("cierre_total"):
                    st.subheader("🏁 Reporte de Cierre de OP")
                    res = {}
                    if area_actual == "IMPRESIÓN":
                        f1, f2 = st.columns(2); res = {"metros_impresos": f1.number_input("Metros", 0.0), "bobinas": f2.number_input("Bobinas", 0)}
                    elif area_actual == "CORTE":
                        f1, f2, f3 = st.columns(3); res = {"total_rollos": f1.number_input("Rollos", 0), "cant_varillas": f2.number_input("Varillas", 0), "medida_rollos": st.text_input("Medida Rollos")}
                    elif area_actual == "COLECTORAS":
                        f1, f2 = st.columns(2); res = {"total_cajas": f1.number_input("Total Cajas", 0), "total_formas": f2.number_input("Total Formas", 0)}
                    elif area_actual == "ENCUADERNACIÓN":
                        f1, f2 = st.columns(2); res = {"cant_final": f1.number_input("Cant. Final", 0), "presentacion": st.text_input("Presentación")}

                    dk = st.number_input("Kilos Desperdicio", 0.0)
                    mot_d = st.text_input("Motivo Desperdicio")
                    obs = st.text_area("Observaciones Generales")

                    if st.form_submit_button("💾 GUARDAR Y CERRAR"):
                        final_data = {
                            "op": act['op'], "maquina": m, "trabajo": act['trabajo'],
                            "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                            "desp_kg": dk, "motivo_desperdicio": mot_d, "observaciones": obs
                        }
                        final_data.update(res)
                        
                        nom_t = normalizar(area_actual)
                        columnas_originales = {
                            "impresion": ["tipo_papel", "ancho", "gramaje", "medida_trabajo"],
                            "corte": ["tipo_papel", "ancho", "gramaje", "img_varilla"],
                            "colectoras": ["tipo_papel", "medida_trabajo", "unidades_caja"],
                            "encuadernacion": ["formas_totales", "material", "medida"]
                        }
                        
                        for col in columnas_originales.get(nom_t, []):
                            if col in act: final_data[col] = safe_float(act[col]) if col in ["ancho", "gramaje"] else act[col]

                        try:
                            supabase.table(nom_t).insert(final_data).execute()
                            supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")
