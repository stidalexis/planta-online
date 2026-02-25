import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA PRODUCCIÓN NUVE V2", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stButton > button { height: 80px !important; border-radius: 12px; font-weight: bold; border: 2px solid #0D47A1; margin-bottom: 8px; white-space: pre-wrap !important; }
    .card-proceso { padding: 15px; border-radius: 12px; background-color: #E8F5E9; border-left: 10px solid #2E7D32; margin-bottom: 10px; font-size: 14px; }
    .card-parada { padding: 15px; border-radius: 12px; background-color: #FFEBEE; border-left: 10px solid #C62828; margin-bottom: 10px; font-size: 14px; }
    .card-libre { padding: 15px; border-radius: 12px; background-color: #F5F5F5; border-left: 10px solid #9E9E9E; color: #757575; text-align: center; margin-bottom: 10px; }
    .title-area { background-color: #1A237E; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin: 15px 0; font-size: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES ---
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
opcion = st.sidebar.radio("MENÚ PRINCIPAL", [
    "🖥️ Monitor General", 
    "📅 Planificación (Admin)", 
    "📊 Consolidado Maestro", 
    "⏱️ Seguimiento Horario", 
    "🖨️ Impresión", 
    "✂️ Corte", 
    "📥 Colectoras", 
    "📕 Encuadernación"
])

# ==========================================
# 1. PLANIFICACIÓN (ADMINISTRADOR)
# ==========================================
if opcion == "📅 Planificación (Admin)":
    st.title("📅 Carga de Órdenes de Producción")
    
    with st.form("form_plan", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        op_n = c1.text_input("Número de OP (Identificador Único)")
        tr_n = c2.text_input("Nombre del Trabajo")
        cl_n = c3.text_input("Cliente")
        
        st.subheader("Especificaciones Técnicas (Se jalarán automáticamente)")
        e1, e2, e3 = st.columns(3)
        pap_n = e1.text_input("Papel / Material")
        anc_n = e2.text_input("Ancho / Medida Base")
        gra_n = e3.text_input("Gramaje")
        
        e4, e5, e6 = st.columns(3)
        img_v = e4.number_input("Imágenes por Varilla", 0)
        und_c = e5.number_input("Unidades por Caja", 0)
        med_t = e6.text_input("Medida de Trabajo (Formato)")
        
        if st.form_submit_button("REGISTRAR OP"):
            if op_n and tr_n:
                payload = {
                    "op": op_n, "trabajo": tr_n, "cliente": cl_n, "tipo_papel": pap_n, 
                    "ancho": anc_n, "gramaje": gra_n, "img_varilla": img_v, 
                    "unidades_caja": und_c, "medida_trabajo": med_t, "estado": "Pendiente"
                }
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.success(f"✅ OP {op_n} registrada exitosamente.")
            else:
                st.error("⚠️ La OP y el Nombre del Trabajo son obligatorios.")

    st.divider()
    st.subheader("Órdenes Registradas")
    ops = supabase.table("ordenes_planeadas").select("*").order("fecha_creacion", desc=True).execute()
    if ops.data:
        st.dataframe(pd.DataFrame(ops.data), use_container_width=True)

# ==========================================
# 2. MONITOR GENERAL
# ==========================================
elif opcion == "🖥️ Monitor General":
    st.title("🖥️ Monitor de Planta en Tiempo Real")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
    
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(3)
        for idx, m in enumerate(lista):
            with cols[idx % 3]:
                if m in paradas:
                    st.markdown(f"<div class='card-parada'>🚨 <b>{m}</b><br>PARADA: {paradas[m]['motivo']}<br>OP: {paradas[m]['op']}</div>", unsafe_allow_html=True)
                elif m in activos:
                    st.markdown(f"<div class='card-proceso'>⚙️ <b>{m}</b><br>OP: {activos[m]['op']}<br>TRABAJO: {activos[m]['trabajo']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-libre'>⚪ {m}<br>LIBRE</div>", unsafe_allow_html=True)

# ==========================================
# 3. CONTROL DE ÁREAS (JOYSTICKS)
# ==========================================
elif opcion in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_act = area_map[opcion]
    st.title(f"Área Operativa: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    # Grid de máquinas
    cols_j = st.columns(2)
    for i, m in enumerate(MAQUINAS[area_act]):
        lbl = f"⚪ {m}\nLIBRE"
        if m in paradas: lbl = f"🚨 {m}\nPARADA: {paradas[m]['motivo']}"
        elif m in activos: lbl = f"⚙️ {m}\nOP: {activos[m]['op']}"
        
        if cols_j[i % 2].button(lbl, key=f"joy_{m}", use_container_width=True):
            st.session_state.m_sel = m

    # Panel de control de la máquina seleccionada
    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        act = activos.get(m)
        par = paradas.get(m)
        st.divider()
        st.subheader(f"🛠️ Panel de Control: {m}")

        if par:
            st.error(f"Máquina en Parada: {par['motivo']}")
            if st.button("▶️ REANUDAR PRODUCCIÓN"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()
        
        elif not act:
            # FLUJO DE INICIO: JALAR DE PLANEACIÓN
            with st.form("form_inicio"):
                st.info("Busque la OP cargada por Administración")
                op_busqueda = st.text_input("Escriba el número de OP")
                if st.form_submit_button("🔍 BUSCAR Y CARGAR OP"):
                    res = supabase.table("ordenes_planeadas").select("*").eq("op", op_busqueda).execute()
                    if res.data:
                        d = res.data[0]
                        inicio_data = {
                            "maquina": m, "op": d['op'], "trabajo": d['trabajo'], "area": area_act,
                            "hora_inicio": datetime.now().strftime("%H:%M"), "tipo_papel": d['tipo_papel'],
                            "ancho": d['ancho'], "gramaje": d['gramaje'], "img_varilla": d['img_varilla'],
                            "unidades_caja": d['unidades_caja'], "medida_trabajo": d['medida_trabajo']
                        }
                        supabase.table("trabajos_activos").insert(inicio_data).execute()
                        supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", op_busqueda).execute()
                        st.success(f"🚀 OP {op_busqueda} iniciada en {m}")
                        st.rerun()
                    else:
                        st.error("❌ OP no encontrada o no ha sido planeada.")
        else:
            # TRABAJO EN CURSO
            st.success(f"Trabajando OP: {act['op']} - {act['trabajo']}")
            if st.button("🛑 REGISTRAR PARADA"):
                m_parada = st.selectbox("Motivo de Parada", ["Mecánico", "Eléctrico", "Limpieza", "Ajuste", "Falta de Material"])
                supabase.table("paradas_maquina").insert({"maquina": m, "op": act['op'], "motivo": m_parada, "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                st.rerun()
            
            with st.form("form_final"):
                st.subheader("🏁 Finalizar Trabajo")
                res = {}
                if area_act == "IMPRESIÓN":
                    res = {"metros_impresos": st.number_input("Metros Impresos", 0.0), "bobinas": st.number_input("Bobinas", 0)}
                elif area_act == "CORTE":
                    res = {"total_rollos": st.number_input("Total Rollos", 0), "cant_varillas": st.number_input("Varillas", 0), "medida_rollos": st.text_input("Medida Final")}
                elif area_act == "COLECTORAS":
                    res = {"total_cajas": st.number_input("Total Cajas", 0), "total_formas": st.number_input("Total Formas", 0)}
                elif area_act == "ENCUADERNACIÓN":
                    res = {"cant_final": st.number_input("Cantidad Final", 0), "presentacion": st.text_input("Presentación")}
                
                dk = st.number_input("Desperdicio Total (Kg)", 0.0)
                obs = st.text_area("Observaciones Finales")
                
                if st.form_submit_button("💾 GUARDAR Y LIBERAR MÁQUINA"):
                    hist_data = {
                        "op": act['op'], "maquina": m, "trabajo": act['trabajo'], "h_inicio": act['hora_inicio'],
                        "h_fin": datetime.now().strftime("%H:%M"), "desp_kg": dk, "observaciones": obs,
                        "tipo_papel": act['tipo_papel'], "ancho": safe_float(act['ancho']), "gramaje": safe_float(act['gramaje'])
                    }
                    hist_data.update(res)
                    supabase.table(normalizar(area_act)).insert(hist_data).execute()
                    supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                    supabase.table("ordenes_planeadas").update({"estado": "Finalizado"}).eq("op", act['op']).execute()
                    st.success("Trabajo guardado e historial actualizado.")
                    st.rerun()

# ==========================================
# 4. CONSOLIDADO MAESTRO
# ==========================================
elif opcion == "📊 Consolidado Maestro":
    st.title("📊 Historial de Producción")
    tab1, tab2, tab3, tab4 = st.tabs(["Impresión", "Corte", "Colectoras", "Encuadernación"])
    
    with tab1:
        data = supabase.table("impresion").select("*").order("fecha_fin", desc=True).execute()
        st.dataframe(pd.DataFrame(data.data), use_container_width=True)
    with tab2:
        data = supabase.table("corte").select("*").order("fecha_fin", desc=True).execute()
        st.dataframe(pd.DataFrame(data.data), use_container_width=True)
    with tab3:
        data = supabase.table("colectoras").select("*").order("fecha_fin", desc=True).execute()
        st.dataframe(pd.DataFrame(data.data), use_container_width=True)
    with tab4:
        data = supabase.table("encuadernacion").select("*").order("fecha_fin", desc=True).execute()
        st.dataframe(pd.DataFrame(data.data), use_container_width=True)

# ==========================================
# 5. SEGUIMIENTO HORARIO
# ==========================================
elif opcion == "⏱️ Seguimiento Horario":
    st.title("⏱️ Seguimiento Cortadoras (Reporte Horario)")
    m_seg = st.selectbox("Seleccione Máquina", MAQUINAS["CORTE"])
    with st.form("form_seg"):
        c1, c2 = st.columns(2)
        op_s = c1.text_input("OP")
        tr_s = c2.text_input("Trabajo")
        med_s = c1.text_input("Medida de Rollo")
        met_s = c2.number_input("Metros por Rollo", 0.0)
        v_s = c1.number_input("Varillas Acum.", 0)
        c_s = c2.number_input("Cajas Acum.", 0)
        d_s = st.number_input("Desperdicio Acum. (Kg)", 0.0)
        
        if st.form_submit_button("GUARDAR AVANCE"):
            h = datetime.now().hour
            turno = "MAÑANA" if 6 <= h < 14 else "TARDE"
            payload = {
                "maquina": m_seg, "op": op_s, "trabajo": tr_s, "medida_rollo": med_s,
                "metros_rollo": met_s, "varillas_acumuladas": v_s, "cajas_acumuladas": c_s,
                "desperidicio_acumulado": d_s, "turno": turno
            }
            supabase.table("seguimiento_corte").insert(payload).execute()
            st.success("Reporte horario guardado correctamente.")
