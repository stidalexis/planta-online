import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V24 PRO", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stButton > button { height: 70px !important; border-radius: 12px; font-weight: bold; width: 100%; border: 2px solid #0D47A1; }
    .card-produccion { background-color: #E8F5E9; border-left: 10px solid #2E7D32; padding: 20px; border-radius: 15px; text-align: center; color: #1B5E20; }
    .card-parada { background-color: #FFEBEE; border-left: 10px solid #C62828; padding: 20px; border-radius: 15px; text-align: center; color: #B71C1C; }
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 20px; border-radius: 15px; text-align: center; color: #9E9E9E; }
    .title-area { background-color: #0D47A1; color: white; padding: 12px; border-radius: 10px; text-align: center; font-weight: bold; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE MAQUINARIA ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)] + ["COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

def normalizar_tabla(t):
    mapping = {"IMPRESIÓN": "impresion", "CORTE": "corte", "COLECTORAS": "colectoras", "ENCUADERNACIÓN": "encuadernacion"}
    return mapping.get(t, t.lower())

# --- CARGA DE DATOS CENTRALIZADA ---
def get_status():
    try:
        activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    except: activos = {}
    
    try:
        # Buscamos paradas donde h_fin sea nulo (parada activa)
        paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
    except: paradas = {}
    
    return activos, paradas

activos_dict, paradas_dict = get_status()

# --- NAVEGACIÓN ---
with st.sidebar:
    st.title("🏭 NUVE PRO V24")
    menu = st.radio("MENÚ", [
        "🖥️ Monitor", 
        "📅 Planificación", 
        "📊 Consolidado", 
        "🔍 Seguimiento OP",
        "⏱️ Avance Corte", 
        "🖨️ Impresión", 
        "✂️ Corte", 
        "📥 Colectoras", 
        "📕 Encuadernación"
    ])

# ==========================================
# 1. MONITOR EN TIEMPO REAL
# ==========================================
if menu == "🖥️ Monitor":
    st.title("🖥️ Monitor de Planta")
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in paradas_dict:
                    st.markdown(f"<div class='card-parada'>🚨 {m}<br>PARADA: {paradas_dict[m]['motivo']}</div>", unsafe_allow_html=True)
                elif m in activos_dict:
                    st.markdown(f"<div class='card-produccion'>⚙️ {m}<br>OP: {activos_dict[m]['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'>{m}<br>LIBRE</div>", unsafe_allow_html=True)
    if st.button("🔄 Actualizar"): st.rerun()

# ==========================================
# 2. PLANIFICACIÓN (NUEVAS ORDENES)
# ==========================================
elif menu == "📅 Planificación":
    st.title("📅 Nueva Planificación de Producción")
    with st.form("form_plan", clear_on_submit=True):
        f1, f2 = st.columns(2)
        op_num = f1.text_input("Número de OP (Ej: OP-5000)").upper()
        cliente = f2.text_input("Cliente")
        trabajo = st.text_input("Nombre del Trabajo")
        tipo = st.selectbox("Tipo de Producto", ["ROLLOS IMPRESOS", "ROLLOS BLANCOS", "FORMAS IMPRESAS", "FORMAS BLANCAS"])
        
        if st.form_submit_button("✅ GUARDAR Y PLANIFICAR"):
            if op_num and cliente:
                # Lógica de ruta
                ruta = "IMPRESIÓN"
                if tipo == "ROLLOS BLANCOS": ruta = "CORTE"
                elif tipo == "FORMAS BLANCAS": ruta = "COLECTORAS"
                
                supabase.table("ordenes_planeadas").insert({
                    "op": op_num, "cliente": cliente, "nombre_trabajo": trabajo, 
                    "tipo_orden": tipo, "proxima_area": ruta, "historial_procesos": []
                }).execute()
                st.success(f"OP {op_num} registrada. Próximo paso: {ruta}")
            else:
                st.error("Faltan datos obligatorios.")

# ==========================================
# 3. JOYSTICKS DE ÁREA (CONTROL TOTAL)
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.title(f"Joystick de Control: {area_act}")
    
    # Grilla de Máquinas
    m_cols = st.columns(4)
    for idx, m in enumerate(MAQUINAS[area_act]):
        with m_cols[idx % 4]:
            if m in paradas_dict: btn_label = f"🚨 {m}\n(DETENIDA)"
            elif m in activos_dict: btn_label = f"⚙️ {m}\nOP: {activos_dict[m]['op']}"
            else: btn_label = f"⚪ {m}\n(LIBRE)"
            
            if st.button(btn_label, key=f"joy_{m}"):
                st.session_state.m_sel = m

    # Panel de Acción Inferior
    if 'm_sel' in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        st.divider()
        st.subheader(f"🛠️ Panel de Acción: {m}")
        
        act = activos_dict.get(m)
        par = paradas_dict.get(m)

        if par:
            st.warning(f"La máquina está parada por: {par['motivo']}")
            if st.button("▶️ REANUDAR PRODUCCIÓN"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()
        
        elif not act:
            # MOSTRAR OPS PENDIENTES PARA ESTA ÁREA
            ops_p = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
            if ops_p:
                with st.form("inicio_m"):
                    op_s = st.selectbox("Seleccionar OP para empezar", [o['op'] for o in ops_p])
                    extra_info = st.text_input("Detalles / Papel")
                    if st.form_submit_button("🚀 INICIAR TRABAJO"):
                        d = next(o for o in ops_p if o['op'] == op_s)
                        supabase.table("trabajos_activos").insert({
                            "maquina": m, "area": area_act, "op": d['op'], 
                            "trabajo": d['nombre_trabajo'], "hora_inicio": datetime.now().strftime("%H:%M"),
                            "tipo_papel": extra_info
                        }).execute()
                        st.rerun()
            else:
                st.info("No hay OPs planificadas para esta área.")
        
        else:
            # TRABAJO EN CURSO
            st.success(f"PRODUCIENDO: {act['op']} - {act['trabajo']}")
            c1, c2 = st.columns(2)
            with c1:
                with st.expander("🛑 REPORTAR FALLA / PARADA"):
                    motivo = st.selectbox("Motivo", ["Mecánico", "Eléctrico", "Ajuste", "Material", "Personal"])
                    if st.button("Confirmar Parada"):
                        supabase.table("paradas_maquina").insert({
                            "maquina": m, "op": act['op'], "motivo": motivo, "h_inicio": datetime.now().strftime("%H:%M")
                        }).execute()
                        st.rerun()
            with c2:
                with st.expander("🏁 FINALIZAR TAREA"):
                    operador = st.text_input("Nombre Operador")
                    dato_u = st.number_input("Metros/Rollos finales", 0.0)
                    dk = st.number_input("Desperdicio (Kg)", 0.0)
                    
                    if st.button("GUARDAR Y PASAR SIGUIENTE ÁREA"):
                        # 1. Trazabilidad
                        d_op = supabase.table("ordenes_planeadas").select("*").eq("op", act['op']).single().execute().data
                        
                        # Determinar siguiente paso
                        n_area = "FINALIZADO"
                        if area_act == "IMPRESIÓN":
                            n_area = "CORTE" if "ROLLOS" in d_op['tipo_orden'] else "COLECTORAS"
                        elif area_act == "COLECTORAS":
                            n_area = "ENCUADERNACIÓN"
                        
                        h = d_op.get('historial_procesos', [])
                        h.append({"area": area_act, "maquina": m, "operador": operador, "fecha": datetime.now().strftime("%d/%m %H:%M")})
                        
                        # Actualizar OP y Histórico
                        supabase.table("ordenes_planeadas").update({"proxima_area": n_area, "historial_procesos": h}).eq("op", act['op']).execute()
                        
                        hist_tab = normalizar_tabla(area_act)
                        supabase.table(hist_tab).insert({
                            "op": act['op'], "maquina": m, "h_inicio": act['hora_inicio'], 
                            "h_fin": datetime.now().strftime("%H:%M"), "desp_kg": dk
                        }).execute()
                        
                        # Borrar activo
                        supabase.table("trabajos_activos").delete().eq("maquina", m).execute()
                        st.rerun()

# ==========================================
# 4. AVANCE HORARIO CORTE
# ==========================================
elif menu == "⏱️ Avance Corte":
    st.title("⏱️ Reporte Horario de Producción - Corte")
    with st.form("f_corte"):
        m_c = st.selectbox("Cortadora", MAQUINAS["CORTE"])
        op_c = st.text_input("Número de OP")
        v = st.number_input("Varillas Acumuladas", 0)
        c = st.number_input("Cajas Acumuladas", 0)
        d = st.number_input("Desperdicio Kg", 0.0)
        if st.form_submit_button("💾 Guardar Avance"):
            supabase.table("seguimiento_corte").insert({
                "maquina": m_c, "op": op_c, "varillas_acumuladas": v, 
                "cajas_acumuladas": c, "desperidicio_acumulado": d
            }).execute()
            st.success("Registrado.")

# ==========================================
# 5. CONSOLIDADO Y KPIs
# ==========================================
elif menu == "📊 Consolidado":
    st.title("📊 Consolidado Maestro")
    area_h = st.selectbox("Ver Histórico de:", list(MAQUINAS.keys()))
    data_h = supabase.table(normalizar_tabla(area_h)).select("*").execute().data
    if data_h:
        st.dataframe(pd.DataFrame(data_h), use_container_width=True)
    else:
        st.info("No hay datos históricos en esta área.")
