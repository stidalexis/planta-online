import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V25 FULL", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES (Heredados de V25) ---
st.markdown("""
    <style>
    .stButton > button { height: 75px !important; border-radius: 12px; font-weight: bold; width: 100%; border: 2px solid #0D47A1; font-size: 14px !important; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 15px; border-radius: 12px; text-align: center; color: #1B5E20; font-weight: bold; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    .card-parada { background-color: #FFEBEE; border-left: 10px solid #C62828; padding: 15px; border-radius: 12px; text-align: center; color: #B71C1C; font-weight: bold; }
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px; text-align: center; color: #9E9E9E; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 10px; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- MAQUINARIA ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)] + ["COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

def normalizar_tabla(t):
    mapping = {"IMPRESIÓN": "impresion", "CORTE": "corte", "COLECTORAS": "colectoras", "ENCUADERNACIÓN": "encuadernacion"}
    return mapping.get(t, t.lower())

# --- ESTADO DE SESIÓN ---
if 'sel_tipo' not in st.session_state: st.session_state.sel_tipo = None
if 'm_sel' not in st.session_state: st.session_state.m_sel = None

# --- CARGA DE DATOS ---
def obtener_estado_planta():
    try:
        act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    except: act = {}
    try:
        par = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
    except: par = {}
    return act, par

activos_dict, paradas_dict = obtener_estado_planta()

# --- NAVEGACIÓN ---
with st.sidebar:
    st.title("🏭 NUVE V25 FULL")
    menu = st.radio("MENÚ PRINCIPAL", [
        "🖥️ Monitor Planta", 
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
# 1. MONITOR DE PLANTA
# ==========================================
if menu == "🖥️ Monitor Planta":
    st.title("🖥️ Monitor en Tiempo Real")
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in paradas_dict:
                    st.markdown(f"<div class='card-parada'>🚨 {m}<br>PARADA TÉCNICA</div>", unsafe_allow_html=True)
                elif m in activos_dict:
                    st.markdown(f"<div class='card-produccion'>⚙️ {m}<br>OP: {activos_dict[m]['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'>{m}<br>DISPONIBLE</div>", unsafe_allow_html=True)
    time.sleep(15); st.rerun()

# ==========================================
# 2. PLANIFICACIÓN (VISUAL V25)
# ==========================================
elif menu == "📅 Planificación":
    st.title("📅 Nueva Orden de Producción")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📑 FORMAS IMPRESAS"): st.session_state.sel_tipo = "FORMAS IMPRESAS"
    if c2.button("📄 FORMAS BLANCAS"): st.session_state.sel_tipo = "FORMAS BLANCAS"
    if c3.button("🌀 ROLLOS IMPRESOS"): st.session_state.sel_tipo = "ROLLOS IMPRESOS"
    if c4.button("⚪ ROLLOS BLANCOS"): st.session_state.sel_tipo = "ROLLOS BLANCOS"

    if st.session_state.sel_tipo:
        tipo_sel = st.session_state.sel_tipo
        st.subheader(f"Configurando: {tipo_sel}")
        with st.form("f_plan", clear_on_submit=True):
            f1, f2, f3 = st.columns(3)
            op = f1.text_input("Número de OP").upper()
            cli = f2.text_input("Cliente")
            trab = f3.text_input("Trabajo / Producto")
            
            # Campos técnicos (Heredados del pequeño)
            st.markdown("---")
            t1, t2, t3 = st.columns(3)
            papel = t1.text_input("Tipo de Papel")
            ancho = t2.text_input("Ancho (cm)")
            gram = t3.text_input("Gramaje")
            
            if st.form_submit_button("🚀 GUARDAR Y ENVIAR A PLANTA"):
                if op and cli:
                    # Lógica de ruta automática
                    ruta = "IMPRESIÓN"
                    if tipo_sel == "ROLLOS BLANCOS": ruta = "CORTE"
                    elif tipo_sel == "FORMAS BLANCAS": ruta = "COLECTORAS"
                    
                    payload = {
                        "op": op, "cliente": cli, "nombre_trabajo": trab, 
                        "tipo_orden": tipo_sel, "proxima_area": ruta, "historial_procesos": []
                    }
                    supabase.table("ordenes_planeadas").insert(payload).execute()
                    st.success(f"OP {op} planificada en {ruta}")
                    st.session_state.sel_tipo = None
                else: st.error("OP y Cliente son obligatorios")

# ==========================================
# 3. MÓDULOS DE MÁQUINAS (JOYSTICKS)
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.title(f"Joystick de Producción: {area_act}")
    
    # Grid de selección de máquina
    cols_m = st.columns(4)
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols_m[idx % 4]:
            if m in paradas_dict: label = f"🚨 {m}\n(PARADA)"
            elif m in activos_dict: label = f"⚙️ {m}\nOP: {activos_dict[m]['op']}"
            else: label = f"⚪ {m}\n(LIBRE)"
            
            if st.button(label, key=f"btn_{m}"): st.session_state.m_sel = m

    # PANEL DE CONTROL DINÁMICO
    if 'm_sel' in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        st.divider()
        st.subheader(f"🛠️ Control de Máquina: {m}")
        
        act = activos_dict.get(m)
        par = paradas_dict.get(m)

        if par:
            st.warning(f"La máquina está detenida: {par['motivo']}")
            if st.button("▶️ REANUDAR TRABAJO"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()
        
        elif not act:
            # INICIAR TRABAJO (Muestra OPs que vienen de la bitácora)
            ops_disp = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
            if ops_disp:
                with st.form("iniciar_op"):
                    sel = st.selectbox("Seleccionar OP Pendiente", [o['op'] for o in ops_disp])
                    st.info("Complete datos técnicos de inicio:")
                    c1, c2, c3 = st.columns(3)
                    p_info = c1.text_input("Papel / Material")
                    m_info = c2.text_input("Medida de Trabajo")
                    u_info = c3.text_input("Unidades x Caja")
                    
                    if st.form_submit_button("🚀 LANZAR PRODUCCIÓN"):
                        d = next(o for o in ops_disp if o['op'] == sel)
                        supabase.table("trabajos_activos").insert({
                            "maquina": m, "area": area_act, "op": d['op'], 
                            "trabajo": d['nombre_trabajo'], "hora_inicio": datetime.now().strftime("%H:%M"),
                            "tipo_papel": p_info, "medida_trabajo": m_info, "unidades_caja": u_info
                        }).execute()
                        st.rerun()
            else: st.info("No hay órdenes pendientes en Planificación para esta área.")
            
        else:
            # GESTIÓN DE TRABAJO EN CURSO
            st.success(f"PRODUCIENDO: {act['op']} | {act['trabajo']}")
            c1, c2 = st.columns(2)
            
            with c1:
                with st.expander("🛑 REPORTAR PARADA TÉCNICA"):
                    motivo = st.selectbox("Motivo de Falla", ["Mecánico", "Eléctrico", "Ajuste", "Limpieza", "Material"])
                    if st.button("Confirmar Parada"):
                        supabase.table("paradas_maquina").insert({
                            "maquina": m, "op": act['op'], "motivo": motivo, "h_inicio": datetime.now().strftime("%H:%M")
                        }).execute()
                        st.rerun()
            
            with c2:
                with st.expander("🏁 FINALIZAR Y MOVER"):
                    op_nom = st.text_input("Nombre del Operario")
                    # Datos del programa pequeño
                    res_val = st.number_input("Cantidad Final (Metros/Rollos)", 0.0)
                    dk = st.number_input("Desperdicio Total (Kg)", 0.0)
                    
                    if st.button("CERRAR PROCESO"):
                        # 1. Trazabilidad Bitácora
                        d_op = supabase.table("ordenes_planeadas").select("*").eq("op", act['op']).single().execute().data
                        
                        # Cálculo siguiente área
                        tipo = d_op['tipo_orden']
                        n_area = "FINALIZADO"
                        if area_act == "IMPRESIÓN":
                            n_area = "CORTE" if "ROLLOS" in tipo else "COLECTORAS"
                        elif area_act == "COLECTORAS":
                            n_area = "ENCUADERNACIÓN"
                        
                        # Actualizar Historial en OP
                        h = d_op.get('historial_procesos', [])
                        h.append({"area": area_act, "maquina": m, "operador": op_nom, "fecha": datetime.now().strftime("%d/%m %H:%M")})
                        
                        # 2. Insertar Histórico de Máquina
                        tab_h = normalizar_tabla(area_act)
                        hist_payload = {
                            "op": act['op'], "maquina": m, "h_inicio": act['hora_inicio'], 
                            "h_fin": datetime.now().strftime("%H:%M"), "desp_kg": dk, "operario": op_nom
                        }
                        if area_act == "IMPRESIÓN": hist_payload["metros_impresos"] = res_val
                        elif area_act == "CORTE": hist_payload["total_rollos"] = res_val
                        
                        supabase.table(tab_h).insert(hist_payload).execute()
                        
                        # 3. Actualizar OP y Borrar de Activos
                        supabase.table("ordenes_planeadas").update({"proxima_area": n_area, "historial_procesos": h}).eq("op", act['op']).execute()
                        supabase.table("trabajos_activos").delete().eq("maquina", m).execute()
                        st.session_state.m_sel = None
                        st.rerun()

# ==========================================
# 4. AVANCE HORARIO CORTE (RESCATADO DEL PEQUEÑO)
# ==========================================
elif menu == "⏱️ Avance Corte":
    st.title("⏱️ Seguimiento Horario - Cortadoras")
    with st.form("form_seg"):
        col1, col2 = st.columns(2)
        m_c = col1.selectbox("Máquina", MAQUINAS["CORTE"])
        op_c = col2.text_input("Número de OP")
        f1, f2, f3 = st.columns(3)
        v = f1.number_input("Varillas Acumuladas", 0)
        c = f2.number_input("Cajas Acumuladas", 0)
        d = f3.number_input("Desperdicio (Kg)", 0.0)
        
        if st.form_submit_button("💾 REGISTRAR AVANCE"):
            supabase.table("seguimiento_corte").insert({
                "maquina": m_c, "op": op_c, "varillas_acumuladas": v, 
                "cajas_acumuladas": c, "desperidicio_acumulado": d
            }).execute()
            st.success("Reporte horario guardado.")

# ==========================================
# 5. CONSOLIDADO Y TRAZABILIDAD
# ==========================================
elif menu == "📊 Consolidado":
    st.title("📊 Consolidado Maestro de Producción")
    area_h = st.selectbox("Seleccionar Área para ver Historial", list(MAQUINAS.keys()))
    data = supabase.table(normalizar_tabla(area_h)).select("*").order("created_at", desc=True).execute().data
    if data:
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    else:
        st.warning("No hay registros en esta tabla aún.")

elif menu == "🔍 Seguimiento OP":
    st.title("🔍 Trazabilidad de Orden (Bitácora)")
    op_ver = st.text_input("Ingrese OP para buscar (Ej: OP-1234)").upper()
    if op_ver:
        res = supabase.table("ordenes_planeadas").select("*").eq("op", op_ver).execute().data
        if res:
            d = res[0]
            st.info(f"**Cliente:** {d['cliente']} | **Trabajo:** {d['nombre_trabajo']}")
            st.success(f"📍 **Ubicación Actual:** {d['proxima_area']}")
            
            st.subheader("Historial de Procesos")
            if d['historial_procesos']:
                for paso in d['historial_procesos']:
                    st.write(f"✅ {paso['fecha']} - **{paso['area']}** ({paso['maquina']}) - Operario: {paso['operador']}")
            else:
                st.write("Esta OP no ha iniciado procesos aún.")
        else:
            st.error("OP no encontrada.")
