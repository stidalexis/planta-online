import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA DE PRODUCCIÓN NUVE", page_icon="🏭", initial_sidebar_state="collapsed")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES (MÓVIL + ESCRITORIO) ---
st.markdown("""
    <style>
    .stButton > button { height: 85px !important; border-radius: 15px; font-weight: bold; font-size: 14px !important; border: 2px solid #0D47A1; margin-bottom: 10px; white-space: pre-wrap !important; }
    .card-proceso { padding: 12px; border-radius: 12px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; min-height: 100px; margin-bottom: 10px; font-size: 13px; }
    .card-parada { padding: 12px; border-radius: 12px; background-color: #FFEBEE; border-left: 8px solid #C62828; min-height: 100px; margin-bottom: 10px; font-size: 13px; }
    .card-libre { padding: 12px; border-radius: 12px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; color: #757575; min-height: 100px; display: flex; align-items: center; justify-content: center; margin-bottom: 10px; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin: 15px 0; font-size: 18px; }
    [data-testid="column"] { width: 100% !important; flex: 1 1 calc(50% - 10px) !important; min-width: 150px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- LISTADO DE MÁQUINAS ORIGINAL ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- FUNCIONES AUXILIARES ---
def normalizar(t):
    for k, v in {"Í":"I","Ó":"O","Á":"A","É":"E","Ú":"U"," ":"_"}.items(): t = t.upper().replace(k,v)
    return t.lower()

def safe_float(v):
    if v is None or v == "": return 0.0
    try: return float(str(v).replace(',', '.'))
    except: return 0.0

# --- MENÚ DE NAVEGACIÓN ---
opcion = st.sidebar.radio("MENÚ PRINCIPAL", ["🖥️ Monitor", "📊 Consolidado", "⏱️ Seguimiento", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# ==========================================
# 1. MONITOR GENERAL
# ==========================================
if opcion == "🖥️ Monitor":
    st.title("🖥️ Monitor de Planta en Tiempo Real")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
    
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(2)
        for idx, m in enumerate(lista):
            with cols[idx % 2]:
                if m in paradas:
                    st.markdown(f"<div class='card-parada'>🚨 <b>{m}</b><br>PARADA: {paradas[m]['motivo']}<br>OP: {paradas[m]['op']}</div>", unsafe_allow_html=True)
                elif m in activos:
                    st.markdown(f"<div class='card-proceso'>⚙️ <b>{m}</b><br>OP: {activos[m]['op']}<br>{activos[m]['trabajo']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-libre'>⚪ {m}<br>LIBRE</div>", unsafe_allow_html=True)

# ==========================================
# 2. CONSOLIDADO MAESTRO CON CRUCE KPI 
# ==========================================
elif opcion == "📊 Consolidado":
    st.title("📊 Consolidado Maestro de Producción")
    
    # Carga de datos de todas las tablas
    imp_df = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
    cor_df = pd.DataFrame(supabase.table("corte").select("*").execute().data)
    col_df = pd.DataFrame(supabase.table("colectoras").select("*").execute().data)
    enc_df = pd.DataFrame(supabase.table("encuadernacion").select("*").execute().data)
    seg_df = pd.DataFrame(supabase.table("seguimiento_corte").select("*").execute().data)
    
    t0, t1, t2, t3, t4, t5 = st.tabs(["🔗 Cruce Operativo KPI", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación", "⏱️ Seguimiento"])
    
    with t0:
        st.subheader("Cruce de Trazabilidad: Impresión -> Corte")
        if not imp_df.empty and not cor_df.empty:
            # Seleccionamos TODAS las columnas relevantes de Impresión
            df_i = imp_df[['op', 'trabajo', 'maquina', 'tipo_papel', 'ancho', 'gramaje', 'metros_impresos', 'desp_kg', 'fecha_fin']].copy()
            df_i.columns = ['OP', 'TRABAJO', 'MAQ_IMP', 'PAPEL', 'ANCHO', 'GR', 'METROS_IMP', 'DESP_IMP', 'FECHA']
            
            # Seleccionamos TODAS las columnas relevantes de Corte
            df_c = cor_df[['op', 'maquina', 'total_rollos', 'cant_varillas', 'desp_kg', 'medida_rollos']].copy()
            df_c.columns = ['OP', 'MAQ_COR', 'ROLLOS_FINALES', 'VARILLAS', 'DESP_COR', 'MEDIDA_CORTE']
            
            # Realizamos el Cruce por OP
            cruce = pd.merge(df_i, df_c, on='OP', how='inner')
            
            # Cálculos de la fila completa
            cruce['DESP_TOTAL_KG'] = cruce['DESP_IMP'].fillna(0) + cruce['DESP_COR'].fillna(0)
            
            # Cálculo de rendimiento: Metros aprovechados vs impresos
            # Suponiendo una relación de metros/rollos si fuera necesaria, 
            # o simplemente la relación directa para ver consistencia.
            cruce['RENDIMIENTO_%'] = ((cruce['ROLLOS_FINALES'] / cruce['METROS_IMP']) * 100).replace([float('inf')], 0).round(2)
            
            # Reordenar columnas para lectura lógica de proceso
            columnas_ordenadas = [
                'FECHA', 'OP', 'TRABAJO', 'PAPEL', 'ANCHO', 'GR', 
                'MAQ_IMP', 'METROS_IMP', 'DESP_IMP', 
                'MAQ_COR', 'ROLLOS_FINALES', 'VARILLAS', 'MEDIDA_CORTE', 'DESP_COR',
                'DESP_TOTAL_KG', 'RENDIMIENTO_%'
            ]
            
            st.dataframe(cruce[columnas_ordenadas], use_container_width=True)
            
            # Métricas rápidas arriba del cruce
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Metros Impresos", f"{cruce['METROS_IMP'].sum():,.0f} m")
            m2.metric("Total Rollos Producidos", f"{cruce['ROLLOS_FINALES'].sum():,.0f}")
            m3.metric("Desperdicio Total Accum.", f"{cruce['DESP_TOTAL_KG'].sum():,.1f} Kg")
        else:
            st.info("💡 Para ver el cruce, una OP debe haber finalizado en Impresión y en Corte.")

    with t1: st.dataframe(imp_df, use_container_width=True)
    with t2: st.dataframe(cor_df, use_container_width=True)
    with t3: st.dataframe(col_df, use_container_width=True)
    with t4: st.dataframe(enc_df, use_container_width=True)
    with t5: st.dataframe(seg_df, use_container_width=True)

# ==========================================
# 3. SEGUIMIENTO HORARIO
# ==========================================
elif opcion == "⏱️ Seguimiento de maquinas":
    st.title("⏱️ Seguimiento Cortadoras")
    cols_s = st.columns(3)
    for i, m_btn in enumerate(MAQUINAS["CORTE"]):
        if cols_s[i % 3].button(m_btn, key=f"btn_seg_{m_btn}", use_container_width=True):
            st.session_state.m_seg_act = m_btn
            
    if "m_seg_act" in st.session_state:
        m = st.session_state.m_seg_act
        with st.form("form_seg_horario"):
            st.info(f"Reportando: {m}")
            op_s = st.text_input("Número de OP")
            tr_s = st.text_input("Nombre del Trabajo")
            c1, c2 = st.columns(2)
            med_s = c1.text_input("Medida de Rollo")
            met_s = c2.number_input("Metros por Rollo", 0.0)
            k1, k2, k3 = st.columns(3)
            var_s = k1.number_input("Varillas Acumuladas", 0)
            caj_s = k2.number_input("Cajas Acumuladas", 0)
            des_s = k3.number_input("Desperdicio Kg", 0.0)
            
            if st.form_submit_button("GUARDAR AVANCE"):
                h = datetime.now().hour
                turno = "MAÑANA" if 6 <= h < 14 else "TARDE"
                payload = {"maquina": m, "op": op_s, "trabajo": tr_s, "medida_rollo": med_s, "metros_rollo": met_s, "varillas_acumuladas": int(var_s), "cajas_acumuladas": int(caj_s), "desperidicio_acumulado": des_s, "turno": turno}
                supabase.table("seguimiento_corte").insert(payload).execute()
                st.success(f"Reporte de las {datetime.now().strftime('%H:%M')} guardado.")

# ==========================================
# 4. JOYSTICKS DE ÁREA (CONTROL TOTAL)
# ==========================================
else:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_act = area_map[opcion]
    st.title(f"Area: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    cols_j = st.columns(2)
    for i, m in enumerate(MAQUINAS[area_act]):
        if m in paradas: lbl = f"🚨 {m}\nPARADA: {paradas[m]['motivo']}"
        elif m in activos: lbl = f"⚙️ {m}\nOP: {activos[m]['op']}"
        else: lbl = f"⚪ {m}\nLIBRE"
        
        if cols_j[i % 2].button(lbl, key=f"joy_{m}", use_container_width=True):
            st.session_state.m_sel = m

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        act = activos.get(m)
        par = paradas.get(m)

        if par:
            st.error(f"Máquina {m} DETENIDA")
            if st.button("REANUDAR TRABAJO", use_container_width=True):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()
        
        elif not act:
            with st.form("form_inicio"):
                st.subheader(f"🚀 Iniciar {m}")
                op_i = st.text_input("Número de OP")
                tr_i = st.text_input("Nombre del Trabajo")
                ext = {}
                if area_act == "IMPRESIÓN":
                    c1, c2 = st.columns(2)
                    ext = {"tipo_papel": c1.text_input("Papel"), "ancho": c1.text_input("Ancho"), "gramaje": c2.text_input("Gramaje"), "medida_trabajo": c2.text_input("Medida")}
                elif area_act == "CORTE":
                    c1, c2 = st.columns(2)
                    ext = {"tipo_papel": c1.text_input("Papel"), "img_varilla": c1.number_input("Img/Varilla", 0), "unidades_caja": c2.number_input("Und/Caja", 0)}
                elif area_act == "COLECTORAS":
                    c1, c2 = st.columns(2)
                    ext = {"tipo_papel": c1.text_input("Papel"), "medida_trabajo": c1.text_input("Medida"), "unidades_caja": c2.number_input("Und/Caja", 0)}
                elif area_act == "ENCUADERNACIÓN":
                    c1, c2 = st.columns(2)
                    ext = {"formas_totales": c1.number_input("Formas", 0), "material": c1.text_input("Material"), "medida": c2.text_input("Medida")}
                
                if st.form_submit_button("COMENZAR TURNO", use_container_width=True):
                    datos = {"maquina": m, "op": op_i, "trabajo": tr_i, "area": area_act, "hora_inicio": datetime.now().strftime("%H:%M")}
                    datos.update(ext)
                    supabase.table("trabajos_activos").insert(datos).execute()
                    st.rerun()
        else:
            st.success(f"Trabajando OP: {act['op']}")
            if st.button("🛑 REGISTRAR PARADA", use_container_width=True):
                mot = st.selectbox("Motivo", ["Mecánico", "Eléctrico", "Limpieza", "Ajuste", "Falta de Material"])
                supabase.table("paradas_maquina").insert({"maquina": m, "op": act['op'], "motivo": mot, "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                st.rerun()
            
            with st.form("form_final"):
                st.subheader("🏁 Finalizar Trabajo")
                res = {}
                if area_act == "IMPRESIÓN":
                    res = {"metros_impresos": st.number_input("Total Metros", 0.0), "bobinas": st.number_input("Total Bobinas", 0)}
                elif area_act == "CORTE":
                    res = {"total_rollos": st.number_input("Total Rollos", 0), "cant_varillas": st.number_input("Varillas", 0), "medida_rollos": st.text_input("Medida Final Rollos")}
                elif area_act == "COLECTORAS":
                    res = {"total_cajas": st.number_input("Total Cajas", 0), "total_formas": st.number_input("Total Formas", 0)}
                elif area_act == "ENCUADERNACIÓN":
                    res = {"cant_final": st.number_input("Cantidad Final", 0), "presentacion": st.text_input("Presentación")}
                
                dk = st.number_input("Desperdicio Total (Kg)", 0.0)
                mot_d = st.text_input("Motivo Desp.")
                obs = st.text_area("Observaciones")
                
                if st.form_submit_button("GUARDAR HISTORIAL", use_container_width=True):
                    nom_t = normalizar(area_act)
                    final_data = {"op": act['op'], "maquina": m, "trabajo": act['trabajo'], "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"), "desp_kg": dk, "motivo_desperdicio": mot_d, "observaciones": obs}
                    
                    # FILTRADO DE COLUMNAS PARA EVITAR PGRST204
                    cols_permitidas = {
                        "impresion": ["tipo_papel", "ancho", "gramaje", "medida_trabajo"],
                        "corte": ["tipo_papel", "img_varilla", "unidades_caja"],
                        "colectoras": ["tipo_papel", "medida_trabajo", "unidades_caja"],
                        "encuadernacion": ["formas_totales", "material", "medida"]
                    }
                    for col in cols_permitidas.get(nom_t, []):
                        if col in act:
                            if col in ["ancho", "gramaje"]: final_data[col] = safe_float(act[col])
                            else: final_data[col] = act[col]
                    
                    final_data.update(res)
                    try:
                        supabase.table(nom_t).insert(final_data).execute()
                        supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                        st.success("Guardado exitoso.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
