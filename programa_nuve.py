import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V7.5", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
# Asegúrate de tener estas credenciales en tu archivo secrets.toml o en la configuración de Streamlit Cloud
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES (UX/UI) ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    .card-proceso { padding: 15px; border-radius: 12px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; margin-bottom: 10px; }
    .card-libre { padding: 15px; border-radius: 12px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; margin-bottom: 10px; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

def normalizar(t):
    for k, v in {"Í":"I","Ó":"O","Á":"A","É":"E","Ú":"U"," ":"_"}.items(): t = t.upper().replace(k,v)
    return t.lower()

# --- BARRA LATERAL ---
menu = st.sidebar.radio("SISTEMA NUVE V7.5", [
    "🖥️ Monitor General", 
    "📅 Planificación (Ingreso OP)", 
    "📊 Historial KPI", 
    "🖨️ Impresión", 
    "✂️ Corte", 
    "📥 Colectoras", 
    "📕 Encuadernación"
])

# ==========================================
# 1. MONITOR GENERAL
# ==========================================
if menu == "🖥️ Monitor General":
    st.title("🖥️ Monitor de Producción en Tiempo Real")
    try:
        act_data = supabase.table("trabajos_activos").select("*").execute().data
        act = {a['maquina']: a for a in act_data}
    except: act = {}

    tabs = st.tabs(list(MAQUINAS.keys()))
    for i, area in enumerate(MAQUINAS.keys()):
        with tabs[i]:
            cols = st.columns(4)
            for idx, m in enumerate(MAQUINAS[area]):
                with cols[idx % 4]:
                    if m in act:
                        st.markdown(f"<div class='card-proceso'>⚙️ <b>{m}</b><br>{act[m]['op']}<br><small>{act[m]['trabajo']}</small></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='card-libre'>⚪ <b>{m}</b><br>LIBRE</div>", unsafe_allow_html=True)

# ==========================================
# 2. PLANIFICACIÓN (VENDEDORES) - FORMULARIOS DINÁMICOS
# ==========================================
elif menu == "📅 Planificación (Ingreso OP)":
    st.title("📅 Registro de Orden de Producción")
    
    tipo_op_sel = st.selectbox("SELECCIONE TIPO DE PRODUCTO:", 
                             ["-- Seleccione --", "RI (Rollo Impreso)", "RB (Rollo Blanco)", "FRI (Forma Impresa)", "FRB (Forma Blanca)"])

    if tipo_op_sel != "-- Seleccione --":
        pref = tipo_op_sel.split(" ")[0]
        es_forma = pref in ["FRI", "FRB"]
        es_impreso = pref in ["RI", "FRI"]

        with st.form("form_op_definitivo"):
            st.markdown(f"<div class='title-area'>FORMULARIO DE DATOS PARA {tipo_op_sel}</div>", unsafe_allow_html=True)
            
            # DATOS BASE
            c1, c2, c3 = st.columns(3)
            op_num = c1.text_input("NÚMERO DE OP (Solo el número)")
            vendedor = c2.text_input("VENDEDOR")
            cliente = c3.text_input("NOMBRE DEL CLIENTE")
            trabajo = st.text_input("NOMBRE DEL TRABAJO")

            st.divider()

            # VARIABLES ESPECÍFICAS
            # Inicializamos todos para evitar errores en el payload
            payload_data = {
                "core": "N/A", "unidades_bolsa": 0, "unidades_caja": 0,
                "num_desde": "N/A", "num_hasta": "N/A", "copias": "N/A",
                "fondo_copias": "N/A", "traficos_orden": "N/A", "codigo_barras": "NO",
                "perforaciones": "N/A", "presentacion": "N/A"
            }

            f1, f2, f3 = st.columns(3)
            material = f1.text_input("TIPO DE PAPEL")
            medida = f2.text_input("MEDIDA")
            cantidad = f3.number_input("CANTIDAD TOTAL", min_value=0)

            if not es_forma: # BLOQUE PARA ROLLOS (RI/RB)
                r1, r2, r3 = st.columns(3)
                payload_data["core"] = r1.selectbox("CORE", ["13MM", "19MM", "1 PULG", "2 PULG", "3 PULG", "40MM"])
                payload_data["unidades_bolsa"] = r2.number_input("UNIDADES POR BOLSA", 0)
                payload_data["unidades_caja"] = r3.number_input("UNIDADES POR CAJA", 0)
                pArea = "IMPRESIÓN" if pref == "RI" else "CORTE"
            else: # BLOQUE PARA FORMAS (FRI/FRB)
                n1, n2, n3 = st.columns(3)
                payload_data["num_desde"] = n1.text_input("NUMERACIÓN DESDE")
                payload_data["num_hasta"] = n2.text_input("NUMERACIÓN HASTA")
                payload_data["copias"] = n3.selectbox("COPIAS", ["1", "2", "3", "4", "5", "6", "7"])
                
                b1, b2, b3 = st.columns(3)
                payload_data["fondo_copias"] = b1.text_input("FONDO DE COPIAS")
                payload_data["traficos_orden"] = b2.text_input("TRÁFICOS EN ORDEN")
                payload_data["codigo_barras"] = b3.text_input("CÓDIGO DE BARRAS (TIPO O NO)")
                
                p1, p2 = st.columns(2)
                payload_data["perforaciones"] = p1.text_input("PERFORACIONES (CUALES Y DONDE)")
                payload_data["presentacion"] = p2.selectbox("PRESENTACIÓN", ["BLOCK TAPA DURA", "BLOCK NORMAL", "LICOM", "PAQUETES", "SUELTAS"])
                pArea = "IMPRESIÓN" if pref == "FRI" else "COLECTORAS"

            # BLOQUE DE IMPRESIÓN
            cant_t, espec_t, cara_i = 0, "N/A", "N/A"
            if es_impreso:
                st.subheader("🎨 Configuración de Impresión")
                i1, i2, i3 = st.columns(3)
                cant_t = i1.number_input("CANTIDAD DE TINTAS", 0)
                espec_t = i2.text_input("CUALES TINTAS")
                cara_i = i3.selectbox("CARA DE IMPRESIÓN", ["FRENTE", "RESPALDO", "AMBAS"])

            obs = st.text_area("OBSERVACIONES GENERALES")

            if st.form_submit_button("🚀 REGISTRAR E INICIAR PRODUCCIÓN"):
                if not op_num or not trabajo:
                    st.error("❌ Los campos OP y Trabajo son obligatorios.")
                else:
                    try:
                        final_payload = {
                            "op": f"{pref}-{op_num}".upper(), "nombre_cliente": cliente, "trabajo": trabajo,
                            "vendedor": vendedor, "tipo_acabado": pref, "material": material,
                            "ancho_medida": medida, "unidades_solicitadas": cantidad, "cant_tintas": cant_t,
                            "especificacion_tintas": espec_t, "orientacion_impresion": cara_i,
                            "proxima_area": pArea, "observaciones": obs, **payload_data
                        }
                        supabase.table("ordenes_planeadas").insert(final_payload).execute()
                        st.success(f"✅ OP {pref}-{op_num} guardada. El trabajo inicia en: {pArea}")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

# ==========================================
# 3. MÓDULOS OPERATIVOS (TRABAJO EN MÁQUINA)
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}[menu]
    st.title(f"Operación: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    cols_m = st.columns(4)
    
    for i, m_id in enumerate(MAQUINAS[area_act]):
        status = "🔴" if m_id in activos else "⚪"
        if cols_m[i % 4].button(f"{status} {m_id}", key=f"m_{m_id}"):
            st.session_state.maquina_actual = m_id

    if "maquina_actual" in st.session_state and st.session_state.maquina_actual in MAQUINAS[area_act]:
        m_sel = st.session_state.maquina_actual
        st.subheader(f"Gestión de Máquina: {m_sel}")

        if m_sel not in activos:
            # Seleccionar OP Pendiente para esta área
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).eq("estado", "Pendiente").execute().data
            if ops:
                op_opciones = [f"{o['op']} | {o['trabajo']}" for o in ops]
                seleccion = st.selectbox("Seleccione OP para iniciar:", ["-- Seleccione --"] + op_opciones)
                if st.button("▶️ INICIAR TRABAJO"):
                    if seleccion != "-- Seleccione --":
                        op_id = seleccion.split(" | ")[0]
                        d_op = next(item for item in ops if item["op"] == op_id)
                        supabase.table("trabajos_activos").insert({
                            "maquina": m_sel, "area": area_act, "op": d_op['op'], "trabajo": d_op['trabajo'],
                            "hora_inicio": datetime.now().strftime("%H:%M"), "vendedor": d_op['vendedor'],
                            "material": d_op['material'], "ancho_medida": d_op['ancho_medida'],
                            "unidades_solicitadas": d_op['unidades_solicitadas'], "tipo_acabado": d_op['tipo_acabado'],
                            "cant_tintas": d_op['cant_tintas'], "especificacion_tintas": d_op['especificacion_tintas']
                        }).execute()
                        supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d_op['op']).execute()
                        st.rerun()
            else:
                st.warning("No hay órdenes pendientes para esta área.")
        else:
            # Finalizar Trabajo
            t_act = activos[m_sel]
            st.info(f"TRABAJANDO: {t_act['op']} - {t_act['trabajo']}")
            with st.form("form_cierre"):
                kpi_data = {}
                if area_act == "IMPRESIÓN":
                    c1, c2 = st.columns(2)
                    kpi_data["metros_impresos"] = c1.number_input("Metros Impresos", 0.0)
                    kpi_data["bobinas"] = c2.number_input("Bobinas Utilizadas", 0)
                elif area_act == "CORTE":
                    c1, c2 = st.columns(2)
                    kpi_data["metros_finales"] = c1.number_input("Metros Finales", 0.0)
                    kpi_data["total_rollos"] = c2.number_input("Total Rollos", 0)
                elif area_act == "COLECTORAS":
                    c1, c2 = st.columns(2)
                    kpi_data["total_cajas"] = c1.number_input("Total Cajas", 0)
                    kpi_data["total_formas"] = c2.number_input("Total Formas", 0)
                elif area_act == "ENCUADERNACIÓN":
                    c1, c2 = st.columns(2)
                    kpi_data["cant_final"] = c1.number_input("Cantidad Final", 0)
                    kpi_data["presentacion"] = c2.text_input("Forma de Empaque")
                
                desp = st.number_input("Desperdicio (Kg)", 0.0)
                obs_cierre = st.text_area("Observaciones de producción")

                if st.form_submit_button("🏁 FINALIZAR ÁREA"):
                    # Lógica de Flujo
                    pref_tipo = t_act['op'].split("-")[0]
                    siguiente = "FINALIZADO"
                    if pref_tipo == "RI" and area_act == "IMPRESIÓN": siguiente = "CORTE"
                    elif pref_tipo == "FRI" and area_act == "IMPRESIÓN": siguiente = "COLECTORAS"
                    elif (pref_tipo == "FRI" or pref_tipo == "FRB") and area_act == "COLECTORAS": siguiente = "ENCUADERNACIÓN"
                    
                    hist = {
                        "op": t_act['op'], "maquina": m_sel, "trabajo": t_act['trabajo'], "vendedor": t_act['vendedor'],
                        "h_inicio": t_act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"), 
                        "desp_kg": desp, "observaciones": obs_cierre, **kpi_data
                    }
                    supabase.table(normalizar(area_act)).insert(hist).execute()
                    supabase.table("ordenes_planeadas").update({"proxima_area": siguiente, "estado": "Pendiente" if siguiente != "FINALIZADO" else "Finalizado"}).eq("op", t_act['op']).execute()
                    supabase.table("trabajos_activos").delete().eq("id", t_act['id']).execute()
                    st.rerun()

# ==========================================
# 4. HISTORIAL KPI
# ==========================================
elif menu == "📊 Historial KPI":
    st.title("📊 Análisis de KPIs")
    t1, t2, t3, t4 = st.tabs(["Impresión", "Corte", "Colectoras", "Encuadernación"])
    for i, tab in enumerate([t1, t2, t3, t4]):
        area_name = ["impresion", "corte", "colectoras", "encuadernacion"][i]
        with tab:
            data = supabase.table(area_name).select("*").order("fecha_fin", desc=True).execute().data
            if data: st.dataframe(pd.DataFrame(data), use_container_width=True)
