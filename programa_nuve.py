import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V24 PRO", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 10px; font-weight: bold; width: 100%; border: 1px solid #0D47A1; }
    .card-produccion { background-color: #E8F5E9; border-left: 8px solid #2E7D32; padding: 15px; border-radius: 12px; text-align: center; color: #1B5E20; }
    .card-parada { background-color: #FFEBEE; border-left: 8px solid #C62828; padding: 15px; border-radius: 12px; text-align: center; color: #B71C1C; }
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px; text-align: center; color: #9E9E9E; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE MAQUINARIA ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)] + ["COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- FUNCIONES DE SOPORTE ---
def normalizar_tabla(t):
    mapping = {"IMPRESIÓN": "impresion", "CORTE": "corte", "COLECTORAS": "colectoras", "ENCUADERNACIÓN": "encuadernacion"}
    return mapping.get(t, t.lower())

# --- ESTADO DE SESIÓN ---
if 'sel_tipo' not in st.session_state: st.session_state.sel_tipo = None
if 'm_sel' not in st.session_state: st.session_state.m_sel = None
if 'detalle_op_id' not in st.session_state: st.session_state.detalle_op_id = None

# --- SIDEBAR NAVEGACIÓN ---
with st.sidebar:
    st.title("🏭 NUVE V24 PRO")
    menu = st.radio("MENÚ", [
        "🖥️ Monitor", 
        "📊 Consolidado", 
        "🔍 Seguimiento OP", 
        "📅 Planificación", 
        "⏱️ Avance Corte", 
        "🖨️ Impresión", 
        "✂️ Corte", 
        "📥 Colectoras", 
        "📕 Encuadernación"
    ])

# ==========================================
# 1. MONITOR GENERAL (CON PARADAS)
# ==========================================
if menu == "🖥️ Monitor":
    st.title("🖥️ Monitor de Planta en Tiempo Real")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
    
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in paradas:
                    st.markdown(f"<div class='card-parada'>🚨 {m}<br>PARADA: {paradas[m]['motivo']}</div>", unsafe_allow_html=True)
                elif m in act:
                    st.markdown(f"<div class='card-produccion'>⚙️ {m}<br>OP: {act[m]['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'>{m}<br>LIBRE</div>", unsafe_allow_html=True)
    time.sleep(30); st.rerun()

# ==========================================
# 2. CONSOLIDADO MAESTRO (KPIs)
# ==========================================
elif menu == "📊 Consolidado":
    st.title("📊 Consolidado y Trazabilidad")
    t1, t2, t3 = st.tabs(["🔗 Cruce Impresión-Corte", "📝 Registros Históricos", "🚨 Bitácora de Paradas"])
    
    with t1:
        st.subheader("Eficiencia de Material (Metros vs Rollos)")
        imp_df = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
        cor_df = pd.DataFrame(supabase.table("corte").select("*").execute().data)
        if not imp_df.empty and not cor_df.empty:
            cruce = pd.merge(imp_df, cor_df, on='op', how='inner', suffixes=('_imp', '_cor'))
            st.dataframe(cruce, use_container_width=True)
        else: st.info("Se requieren datos en ambas áreas para generar el cruce.")

    with t2:
        area_sel = st.selectbox("Seleccionar Área para Ver Historial", list(MAQUINAS.keys()))
        data_h = supabase.table(normalizar_tabla(area_sel)).select("*").order("created_at", desc=True).execute().data
        if data_h: st.dataframe(pd.DataFrame(data_h), use_container_width=True)

    with t3:
        par_data = supabase.table("paradas_maquina").select("*").order("created_at", desc=True).execute().data
        if par_data: st.dataframe(pd.DataFrame(par_data), use_container_width=True)

# ==========================================
# 3. SEGUIMIENTO INDIVIDUAL DE OP
# ==========================================
elif menu == "🔍 Seguimiento OP":
    st.title("🔍 Seguimiento de Orden de Producción")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if res:
        df = pd.DataFrame(res)
        st.dataframe(df[['op', 'cliente', 'nombre_trabajo', 'proxima_area']], use_container_width=True)
        
        sel_op_ver = st.selectbox("Ver detalle de OP", df['op'].unique())
        if st.button("Ver Bitácora"):
            d = df[df['op'] == sel_op_ver].iloc[0]
            st.info(f"Estado Actual: {d['proxima_area']}")
            if d['historial_procesos']:
                for p in d['historial_procesos']:
                    st.success(f"✅ {p['fecha']} - {p['area']} ({p['maquina']}) - Operario: {p['operario']}")

# ==========================================
# 4. PLANIFICACIÓN (V24)
# ==========================================
elif menu == "📅 Planificación":
    st.title("📅 Nueva Orden de Producción")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📑 FORMAS IMPRESAS"): st.session_state.sel_tipo = "FORMAS IMPRESAS"
    if c2.button("📄 FORMAS BLANCAS"): st.session_state.sel_tipo = "FORMAS BLANCAS"
    if c3.button("🌀 ROLLOS IMPRESOS"): st.session_state.sel_tipo = "ROLLOS IMPRESOS"
    if c4.button("⚪ ROLLOS BLANCOS"): st.session_state.sel_tipo = "ROLLOS BLANCOS"

    if st.session_state.sel_tipo:
        t = st.session_state.sel_tipo
        with st.form("form_plan", clear_on_submit=True):
            st.subheader(f"Configurando: {t}")
            f1, f2, f3 = st.columns(3)
            op_n = f1.text_input("Número de OP").upper()
            cli = f2.text_input("Cliente")
            trab = f3.text_input("Nombre Trabajo")
            
            obs = st.text_area("Observaciones Generales")
            
            if st.form_submit_button("🚀 GUARDAR Y PLANIFICAR"):
                # Lógica de ruta automática
                ruta = "IMPRESIÓN"
                if t == "ROLLOS BLANCOS": ruta = "CORTE"
                elif t == "FORMAS BLANCAS": ruta = "COLECTORAS"
                
                payload = {
                    "op": op_n, "cliente": cli, "nombre_trabajo": trab, 
                    "tipo_orden": t, "proxima_area": ruta, "historial_procesos": []
                }
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.success(f"OP {op_n} enviada a {ruta}")
                time.sleep(1); st.rerun()

# ==========================================
# 5. AVANCE HORARIO CORTE
# ==========================================
elif menu == "⏱️ Avance Corte":
    st.title("⏱️ Reporte de Avance Cortadoras")
    m_corte = st.selectbox("Seleccionar Cortadora", MAQUINAS["CORTE"])
    with st.form("form_seg_horario"):
        op_s = st.text_input("Número de OP")
        c1, c2, c3 = st.columns(3)
        var_s = c1.number_input("Varillas Acumuladas", 0)
        caj_s = c2.number_input("Cajas Acumuladas", 0)
        des_s = c3.number_input("Desperdicio Kg", 0.0)
        
        if st.form_submit_button("💾 GUARDAR AVANCE"):
            payload = {
                "maquina": m_corte, "op": op_s, 
                "varillas_acumuladas": int(var_s), "cajas_acumuladas": int(caj_s), 
                "desperidicio_acumulado": des_s
            }
            supabase.table("seguimiento_corte").insert(payload).execute()
            st.success("Avance registrado correctamente.")

# ==========================================
# 6. JOYSTICKS DE PRODUCCIÓN (ÁREAS)
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.title(f"Módulo de {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    # Grilla de Máquinas
    cols_j = st.columns(4)
    for i, m in enumerate(MAQUINAS[area_act]):
        with cols_j[i % 4]:
            if m in paradas: label = f"🚨 {m}\nDETENIDA"
            elif m in activos: label = f"⚙️ {m}\nOP: {activos[m]['op']}"
            else: label = f"⚪ {m}\nLIBRE"
            
            if st.button(label, key=f"joy_{m}"):
                st.session_state.m_sel = m

    # Panel de Acción (Joystick)
    if st.session_state.m_sel and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        st.divider()
        st.subheader(f"Panel de Control: {m}")
        
        act = activos.get(m)
        par = paradas.get(m)

        if par:
            st.error(f"Máquina en Parada: {par['motivo']}")
            if st.button("▶️ REANUDAR TRABAJO"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()
        
        elif not act:
            # INICIAR TRABAJO (Solo OPs planificadas para esta área)
            ops_disp = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
            if ops_disp:
                with st.form("form_inicio"):
                    sel_op = st.selectbox("Seleccionar OP para Iniciar", [o['op'] for o in ops_disp])
                    # Campos técnicos adicionales
                    papel = st.text_input("Papel / Material")
                    if st.form_submit_button("🚀 INICIAR TURNO"):
                        d = next(o for o in ops_disp if o['op'] == sel_op)
                        supabase.table("trabajos_activos").insert({
                            "maquina": m, "area": area_act, "op": d['op'], 
                            "trabajo": d['nombre_trabajo'], "hora_inicio": datetime.now().strftime("%H:%M"),
                            "tipo_papel": papel
                        }).execute()
                        st.rerun()
            else: st.info("No hay órdenes pendientes para esta área en Planificación.")

        else:
            # GESTIÓN DE TRABAJO ACTIVO
            st.success(f"Trabajando OP: {act['op']} - {act['trabajo']}")
            c1, c2 = st.columns(2)
            
            with c1:
                with st.expander("🛑 REPORTAR PARADA TÉCNICA"):
                    mot = st.selectbox("Motivo", ["Mecánico", "Eléctrico", "Ajuste", "Limpieza", "Falta Material"])
                    if st.button("Confirmar Parada"):
                        supabase.table("paradas_maquina").insert({
                            "maquina": m, "op": act['op'], "motivo": mot, "h_inicio": datetime.now().strftime("%H:%M")
                        }).execute()
                        st.rerun()
            
            with c2:
                with st.expander("🏁 FINALIZAR PROCESO"):
                    operario = st.text_input("Nombre del Operario")
                    # Datos específicos según área para el historial
                    res_val = 0.0
                    if area_act == "IMPRESIÓN": res_val = st.number_input("Metros Impresos", 0.0)
                    elif area_act == "CORTE": res_val = st.number_input("Total Rollos", 0)
                    
                    dk = st.number_input("Desperdicio Final (Kg)", 0.0)
                    
                    if st.button("GUARDAR Y ENVIAR A SIGUENTE ÁREA"):
                        # 1. Calcular Siguiente Área
                        d_op = supabase.table("ordenes_planeadas").select("*").eq("op", act['op']).single().execute().data
                        tipo = d_op['tipo_orden']
                        n_area = "FINALIZADO"
                        if "ROLLOS" in tipo and area_act == "IMPRESIÓN": n_area = "CORTE"
                        elif "FORMAS" in tipo:
                            if area_act == "IMPRESIÓN": n_area = "COLECTORAS"
                            elif area_act == "COLECTORAS": n_area = "ENCUADERNACIÓN"
                        
                        # 2. Actualizar Bitácora
                        h = d_op.get('historial_procesos', [])
                        h.append({
                            "area": area_act, "maquina": m, "operario": operario, 
                            "fecha": datetime.now().strftime("%d/%m/%Y %H:%M")
                        })
                        supabase.table("ordenes_planeadas").update({"proxima_area": n_area, "historial_procesos": h}).eq("op", act['op']).execute()
                        
                        # 3. Guardar en Histórico de Producción
                        hist_data = {
                            "op": act['op'], "maquina": m, "trabajo": act['trabajo'],
                            "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                            "desp_kg": dk
                        }
                        if area_act == "IMPRESIÓN": hist_data["metros_impresos"] = res_val
                        elif area_act == "CORTE": hist_data["total_rollos"] = res_val
                        
                        supabase.table(normalizar_tabla(area_act)).insert(hist_data).execute()
                        
                        # 4. Limpiar Activos
                        supabase.table("trabajos_activos").delete().eq("maquina", m).execute()
                        st.session_state.m_sel = None
                        st.rerun()
