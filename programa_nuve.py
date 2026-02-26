import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="NUVE V7.5 - SISTEMA INTEGRAL", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES (UX/UI) ---
st.markdown("""
    <style>
    .stButton > button { height: 75px !important; border-radius: 12px; font-weight: bold; border: 2px solid #0D47A1; width: 100%; }
    .card-proceso { padding: 15px; border-radius: 12px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; margin-bottom: 10px; border-right: 1px solid #C8E6C9; border-top: 1px solid #C8E6C9; border-bottom: 1px solid #C8E6C9; }
    .card-libre { padding: 15px; border-radius: 12px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; margin-bottom: 10px; }
    .title-area { background-color: #1A237E; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

def normalizar(t):
    for k, v in {"Í":"I","Ó":"O","Á":"A","É":"E","Ú":"U"," ":"_"}.items(): t = t.upper().replace(k,v)
    return t.lower()

# --- BARRA LATERAL (NAVEGACIÓN) ---
menu = st.sidebar.radio("SISTEMA NUVE V7.5", [
    "🖥️ Monitor General", 
    "📅 Planificación (Admin)", 
    "📊 Historial KPI", 
    "🖨️ Impresión", 
    "✂️ Corte", 
    "📥 Colectoras", 
    "📕 Encuadernación"
])

# ==========================================
# 1. MONITOR GENERAL (ESTADO Y SEGUIMIENTO)
# ==========================================
if menu == "🖥️ Monitor General":
    st.title("🖥️ Tablero de Control y Seguimiento de OPs")
    
    # Visualización de Máquinas en tiempo real
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    tabs = st.tabs(list(MAQUINAS.keys()))
    
    for i, area in enumerate(MAQUINAS.keys()):
        with tabs[i]:
            cols = st.columns(4)
            for idx, m in enumerate(MAQUINAS[area]):
                with cols[idx % 4]:
                    if m in act:
                        st.markdown(f"""<div class='card-proceso'>⚙️ <b>{m}</b><br><span style='color:#1B5E20;'>{act[m]['op']}</span><br><small>{act[m]['trabajo']}</small></div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='card-libre'>⚪ <b>{m}</b><br>LIBRE</div>", unsafe_allow_html=True)

    st.divider()

    # Buscador de Expedientes de OPs
    st.subheader("📋 Consulta de Expedientes de Producción")
    res_ops = supabase.table("ordenes_planeadas").select("*").order("fecha_creacion", desc=True).execute().data
    
    if res_ops:
        df_ops = pd.DataFrame(res_ops)
        def calc_status(row):
            if row['estado'] == 'Finalizado': return "✅ COMPLETADA"
            if row['estado'] == 'En Proceso': return f"🔄 TRABAJANDO EN {row['proxima_area']}"
            return f"⏳ ESPERA DE {row['proxima_area']}"
        df_ops['Estado_Flujo'] = df_ops.apply(calc_status, axis=1)

        c_sel1, c_sel2 = st.columns([1, 2])
        op_busqueda = c_sel1.selectbox("🔍 Buscar OP para ver detalles técnicos:", ["-- SELECCIONE OP --"] + df_ops['op'].tolist())
        
        if op_busqueda != "-- SELECCIONE OP --":
            d = df_ops[df_ops['op'] == op_busqueda].iloc[0]
            with st.container(border=True):
                st.markdown(f"### 📑 Ficha Técnica: {d['op']}")
                col1, col2, col3, col4 = st.columns(4)
                col1.write(f"**Trabajo:**\n{d['trabajo']}")
                col1.write(f"**Vendedor:**\n{d['vendedor']}")
                col2.write(f"**Material:**\n{d['material']}")
                col2.write(f"**Gramaje:**\n{d['gramaje']}")
                col3.write(f"**Ancho:**\n{d['ancho']}")
                col3.write(f"**Unidades:**\n{d['unidades_solicitadas']}")
                col4.write(f"**Core:**\n{d['core']}")
                col4.write(f"**Estado:**\n{d['Estado_Flujo']}")
                
                if d['cant_tintas'] > 0:
                    st.divider()
                    st.write(f"🎨 **Configuración de Impresión:** {d['cant_tintas']} Tintas | **Colores:** {d['especificacion_tintas']} | **Lado:** {d['orientacion_impresion']}")

        st.markdown("#### Listado General de Órdenes")
        st.dataframe(df_ops[['op', 'trabajo', 'vendedor', 'Estado_Flujo']], use_container_width=True, hide_index=True)

# ==========================================
# 2. PLANIFICACIÓN (ADMIN)
# ==========================================
elif menu == "📅 Planificación (Admin)":
    st.title("📅 Registro de Órdenes de Producción")
    with st.form("form_planificacion", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        op_num = c1.text_input("Número de OP")
        trab_nom = c2.text_input("Nombre del Trabajo")
        vendedor = c3.text_input("Vendedor")
        
        f1, f2, f3 = st.columns(3)
        mat, gra, anc = f1.text_input("Material"), f2.text_input("Gramaje"), f3.text_input("Ancho")
        
        f4, f5, f6 = st.columns(3)
        unidades = f4.number_input("Unidades Solicitadas", 0)
        core_val = f5.selectbox("Core", ["3 Pulgadas", "1.5 Pulgadas", "Sin Core"])
        tipo_op = f6.radio("Tipo de Flujo", ["RI", "RB", "FRI", "FRB"], horizontal=True)
        
        # Visibilidad condicional para tintas
        cant_t, espec_t, orient_t = 0, "N/A", "N/A"
        if tipo_op in ["RI", "FRI"]:
            st.divider()
            st.subheader("🎨 Detalles de Impresión")
            i1, i2, i3 = st.columns(3)
            cant_t = i1.number_input("Cantidad Tintas", 0)
            espec_t = i2.text_input("Especificación de Colores")
            orient_t = i3.selectbox("Lado de Impresión", ["Frente", "Respaldo", "Ambos"])
            
        if st.form_submit_button("✅ CARGAR A PRODUCCIÓN"):
            if not op_num or not trab_nom:
                st.error("❌ Los campos OP y Trabajo son obligatorios.")
            else:
                # Lógica de asignación de área inicial
                if tipo_op in ["RI", "FRI"]: pArea = "IMPRESIÓN"
                elif tipo_op == "RB": pArea = "CORTE"
                else: pArea = "COLECTORAS" # FRB
                
                op_id_final = f"{tipo_op}-{op_num}".upper()
                payload = {
                    "op": op_id_final, "trabajo": trab_nom, "vendedor": vendedor, "material": mat, 
                    "gramaje": gra, "ancho": anc, "unidades_solicitadas": unidades, "core": core_val, 
                    "tipo_acabado": tipo_op, "cant_tintas": cant_t, "especificacion_tintas": espec_t, 
                    "orientacion_impresion": orient_t, "estado": "Pendiente", "proxima_area": pArea
                }
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.success(f"✅ OP {op_id_final} registrada exitosamente.")

# ==========================================
# 3. MÓDULOS OPERATIVOS (FLUJO Y CIERRE)
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}[menu]
    st.title(f"Área Operativa: {area_act}")
    
    # Cargar trabajos en curso en esta área
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    
    cols_m = st.columns(4)
    for i, m_id in enumerate(MAQUINAS[area_act]):
        estado_btn = f"{m_id} (OCUPADA)" if m_id in activos else f"{m_id} (LIBRE)"
        if cols_m[i % 4].button(estado_btn, key=f"btn_{m_id}"):
            st.session_state.m_sel = m_id

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m_actual = st.session_state.m_sel
        trabajo_actual = activos.get(m_actual)
        st.divider()
        st.subheader(f"⚙️ Máquina Seleccionada: {m_actual}")

        if not trabajo_actual:
            # Seleccionar OP para iniciar
            ops_disp = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).eq("estado", "Pendiente").execute().data
            op_seleccionada = st.selectbox("Seleccione Orden para iniciar producción:", ["--"] + [f"{o['op']} | {o['trabajo']}" for o in ops_disp])
            
            if st.button("🚀 INICIAR TURNO"):
                if op_seleccionada != "--":
                    # Rescatar datos completos de la OP
                    d_op = [o for o in ops_disp if o['op'] == op_seleccionada.split(" | ")[0]][0]
                    # Mover a Trabajos Activos heredando todo
                    payload_ini = {
                        "maquina": m_actual, "op": d_op['op'], "trabajo": d_op['trabajo'], "area": area_act,
                        "vendedor": d_op['vendedor'], "material": d_op['material'], "gramaje": d_op['gramaje'],
                        "ancho": d_op['ancho'], "unidades_solicitadas": d_op['unidades_solicitadas'],
                        "core": d_op['core'], "tipo_acabado": d_op['tipo_acabado'],
                        "cant_tintas": d_op['cant_tintas'], "especificacion_tintas": d_op['especificacion_tintas'],
                        "orientacion_impresion": d_op['orientacion_impresion'], "hora_inicio": datetime.now().strftime("%H:%M")
                    }
                    supabase.table("trabajos_activos").insert(payload_ini).execute()
                    supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d_op['op']).execute()
                    st.rerun()
        else:
            # Formulario de cierre con herencia total
            st.info(f"📋 **OP EN CURSO:** {trabajo_actual['op']} - {trabajo_actual['trabajo']}")
            with st.form("form_cierre_area"):
                st.markdown("### 🏁 Reporte de Finalización de Área")
                datos_kpi = {}
                c_k1, c_k2 = st.columns(2)
                
                if area_act == "IMPRESIÓN":
                    datos_kpi["metros_impresos"] = c_k1.number_input("Metros Impresos Reales", 0.0)
                    datos_kpi["bobinas"] = c_k2.number_input("Bobinas Utilizadas", 0)
                elif area_act == "CORTE":
                    datos_kpi["metros_finales"] = c_k1.number_input("Metros Finales de Corte", 0.0)
                    datos_kpi["total_rollos"] = c_k2.number_input("Total Rollos Obtenidos", 0)
                    datos_kpi["cant_varillas"] = st.number_input("Cantidad de Varillas", 0)
                elif area_act == "COLECTORAS":
                    datos_kpi["total_cajas"] = c_k1.number_input("Total Cajas", 0)
                    datos_kpi["total_formas"] = c_k2.number_input("Total Formas", 0)
                elif area_act == "ENCUADERNACIÓN":
                    datos_kpi["cant_final"] = c_k1.number_input("Cantidad Final Producida", 0)
                    datos_kpi["presentacion"] = c_k2.text_input("Presentación (Ej. Paquetes de 10)")

                st.divider()
                col_d1, col_d2 = st.columns(2)
                desp = col_d1.number_input("Desperdicio Total (Kg)", 0.0)
                motivo = col_d2.text_input("Motivo del Desperdicio")
                obser = st.text_area("Observaciones del turno")
                
                if st.form_submit_button("🏁 FINALIZAR Y ENVIAR A SIGUIENTE ÁREA"):
                    val_produccion = list(datos_kpi.values())[0] if area_act != "ENCUADERNACIÓN" else datos_kpi["cant_final"]
                    
                    if val_produccion <= 0:
                        st.error("❌ Debe ingresar una producción válida mayor a 0.")
                    else:
                        # Lógica de flujo (RI, RB, FRI, FRB)
                        prefijo = trabajo_actual['op'].split("-")[0]
                        siguiente = "FINALIZADO"
                        if prefijo == "RI" and area_act == "IMPRESIÓN": siguiente = "CORTE"
                        elif prefijo == "FRI" and area_act == "IMPRESIÓN": siguiente = "COLECTORAS"
                        elif (prefijo == "FRI" or prefijo == "FRB") and area_act == "COLECTORAS": siguiente = "ENCUADERNACIÓN"
                        
                        # HERENCIA DE DATOS: Construir registro de historial completo
                        historial = {
                            "op": trabajo_actual['op'], "maquina": m_actual, "trabajo": trabajo_actual['trabajo'],
                            "h_inicio": trabajo_actual['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                            "vendedor": trabajo_actual['vendedor'], "material": trabajo_actual['material'],
                            "gramaje": trabajo_actual['gramaje'], "ancho": trabajo_actual['ancho'],
                            "desp_kg": desp, "motivo_desp": motivo, "observaciones": obser
                        }
                        
                        # Agregar datos específicos de impresión si corresponde
                        if area_act == "IMPRESIÓN":
                            historial.update({
                                "cant_tintas": trabajo_actual['cant_tintas'],
                                "especificacion_tintas": trabajo_actual['especificacion_tintas'],
                                "orientacion_impresion": trabajo_actual['orientacion_impresion']
                            })
                        
                        # Agregar el KPI recién digitado
                        historial.update(datos_kpi)
                        
                        # Guardar en Base de Datos e Insertar Historial
                        supabase.table(normalizar(area_act)).insert(historial).execute()
                        
                        # Actualizar estado de OP y liberar máquina
                        n_estado = "Pendiente" if siguiente != "FINALIZADO" else "Finalizado"
                        supabase.table("ordenes_planeadas").update({"proxima_area": siguiente, "estado": n_estado}).eq("op", trabajo_actual['op']).execute()
                        supabase.table("trabajos_activos").delete().eq("id", trabajo_actual['id']).execute()
                        
                        st.success(f"✅ Área cerrada. Movido a: {siguiente}")
                        st.rerun()

# ==========================================
# 4. HISTORIAL KPI (CONSOLIDADO)
# ==========================================
elif menu == "📊 Historial KPI":
    st.title("📊 Análisis de Producción (KPI)")
    areas_list = ["impresion", "corte", "colectoras", "encuadernacion"]
    tab_n = st.tabs([a.capitalize() for a in areas_list])
    
    for i, t in enumerate(tab_n):
        with t:
            data_hist = supabase.table(areas_list[i]).select("*").order("fecha_fin", desc=True).execute().data
            if data_hist:
                st.dataframe(pd.DataFrame(data_hist), use_container_width=True)
            else:
                st.info(f"No hay registros históricos en {areas_list[i]}.")
