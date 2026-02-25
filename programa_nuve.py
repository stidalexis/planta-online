import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V3.1", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
# Asegúrate de tener estas credenciales en .streamlit/secrets.toml
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stButton > button { height: 90px !important; border-radius: 15px; font-weight: bold; border: 2px solid #0D47A1; width: 100%; white-space: pre-wrap !important; font-size: 16px; }
    .card-proceso { padding: 15px; border-radius: 12px; background-color: #E8F5E9; border-left: 10px solid #2E7D32; margin-bottom: 10px; font-size: 14px; }
    .card-libre { padding: 15px; border-radius: 12px; background-color: #F5F5F5; border-left: 10px solid #9E9E9E; text-align: center; color: #757575; margin-bottom: 10px; }
    .title-area { background-color: #1A237E; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 25px; font-size: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES DE MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- FUNCIONES AUXILIARES ---
def normalizar(t):
    for k, v in {"Í":"I","Ó":"O","Á":"A","É":"E","Ú":"U"," ":"_"}.items(): t = t.upper().replace(k,v)
    return t.lower()

# --- MENÚ PRINCIPAL ---
opcion = st.sidebar.radio("SISTEMA NUVE", [
    "🖥️ Monitor General", 
    "📅 Planificación (Admin)", 
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
    
    with st.form("form_planificacion", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        op_numero = col1.text_input("Número de Orden (Solo el número)")
        trabajo_nombre = col2.text_input("Nombre del Trabajo / Cliente")
        vendedor_nom = col3.text_input("Vendedor Asignado")
        
        st.subheader("Ficha Técnica")
        f1, f2, f3 = st.columns(3)
        mat_tipo = f1.text_input("Material / Sustrato")
        gramaje_val = f2.text_input("Gramaje")
        ancho_val = f3.text_input("Ancho / Medida Base")
        
        f4, f5, f6 = st.columns(3)
        unidades_s = f4.number_input("Unidades Solicitadas", min_value=0, step=1)
        core_t = f5.selectbox("Core", ["3 Pulgadas", "1.5 Pulgadas", "Sin Core", "Otro"])
        tipo_p = f6.radio("Tipo de Trabajo (Prefijo)", ["RI (Rollo Impreso)", "RB (Rollo Blanco)", "FR (Formas)"], horizontal=True)
        
        # Lógica Condicional para Tintas
        c_tintas = 0
        e_tintas = "N/A"
        orient = "N/A"
        
        if "RI" in tipo_p or "FR" in tipo_p:
            st.divider()
            st.subheader("Detalles de Impresión")
            i1, i2, i3 = st.columns(3)
            c_tintas = i1.number_input("Cantidad de Tintas", 0, 10)
            e_tintas = i2.text_input("Colores Específicos (Ej: Rojo, Negro)")
            orient = i3.selectbox("Orientación de Impresión", ["Solo Frente", "Solo Respaldo", "Frente y Respaldo"])
        
        if st.form_submit_button("✅ REGISTRAR Y CARGAR ORDEN"):
            if op_numero and trabajo_nombre:
                # Construir el prefijo
                p_f = "RI-" if "RI" in tipo_p else "RB-" if "RB" in tipo_p else "FR-"
                op_final_id = f"{p_f}{op_numero}".strip().upper()
                
                payload = {
                    "op": op_final_id,
                    "trabajo": trabajo_nombre,
                    "vendedor": vendedor_nom,
                    "material": mat_tipo,
                    "gramaje": gramaje_val,
                    "ancho": ancho_val,
                    "unidades_solicitadas": int(unidades_s),
                    "core": core_t,
                    "tipo_acabado": tipo_p,
                    "cant_tintas": int(c_tintas),
                    "especificacion_tintas": e_tintas,
                    "orientacion_impresion": orient,
                    "estado": "Pendiente"
                }
                
                try:
                    supabase.table("ordenes_planeadas").insert(payload).execute()
                    st.success(f"Orden {op_final_id} cargada exitosamente.")
                except Exception as e:
                    st.error(f"Error: La OP {op_final_id} ya existe o hay un problema de conexión.")
            else:
                st.warning("El Número de OP y el Nombre del Trabajo son obligatorios.")

    st.divider()
    st.subheader("Órdenes en Espera")
    pendientes = supabase.table("ordenes_planeadas").select("*").eq("estado", "Pendiente").execute()
    if pendientes.data:
        st.dataframe(pd.DataFrame(pendientes.data), use_container_width=True)

# ==========================================
# 2. MONITOR GENERAL
# ==========================================
elif opcion == "🖥️ Monitor General":
    st.title("🖥️ Estado de Producción en Tiempo Real")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    
    for area, maquinas_area in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols_m = st.columns(4)
        for idx, m_nombre in enumerate(maquinas_area):
            with cols_m[idx % 4]:
                if m_nombre in activos:
                    info = activos[m_nombre]
                    st.markdown(f"""
                        <div class='card-proceso'>
                            <b>⚙️ {m_nombre}</b><br>
                            OP: {info['op']}<br>
                            {info['trabajo']}<br>
                            <small>{info['vendedor']}</small>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-libre'>⚪ {m_nombre}<br>DISPONIBLE</div>", unsafe_allow_html=True)

# ==========================================
# 3. MÓDULOS DE ÁREA (BOTONES + DESPLEGABLE)
# ==========================================
elif opcion in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_actual = area_map[opcion]
    st.title(f"Área de {area_actual}")
    
    # Obtener estados actuales
    activos_area = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_actual).execute().data}
    
    # 1. MOSTRAR MÁQUINAS COMO BOTONES
    st.subheader("Seleccione su Máquina:")
    columnas_botones = st.columns(4)
    for i, m_id in enumerate(MAQUINAS[area_actual]):
        label_m = f"⚙️ {m_id}\n(EN USO)" if m_id in activos_area else f"⚪ {m_id}\n(LIBRE)"
        if columnas_botones[i % 4].button(label_m, key=f"btn_{m_id}"):
            st.session_state.maquina_seleccionada = m_id

    # 2. INTERFAZ DE OPERACIÓN SI HAY MÁQUINA SELECCIONADA
    if "maquina_seleccionada" in st.session_state and st.session_state.maquina_seleccionada in MAQUINAS[area_actual]:
        m_sel = st.session_state.maquina_seleccionada
        trabajo_en_curso = activos_area.get(m_sel)
        
        st.divider()
        st.subheader(f"🛠️ Panel de Control - Máquina: {m_sel}")

        if not trabajo_en_curso:
            # FLUJO DE INICIO: BUSCAR ORDENES DISPONIBLES EN DESPLEGABLE
            res_disponibles = supabase.table("ordenes_planeadas").select("op, trabajo").eq("estado", "Pendiente").execute()
            lista_desplegable = [f"{o['op']} | {o['trabajo']}" for o in res_disponibles.data]
            
            if lista_desplegable:
                op_para_iniciar = st.selectbox("📋 Seleccione la Orden que va a trabajar:", ["-- Seleccione --"] + lista_desplegable)
                
                if st.button("🚀 INICIAR TRABAJO"):
                    if op_para_iniciar != "-- Seleccione --":
                        id_op = op_para_iniciar.split(" | ")[0]
                        datos_op = supabase.table("ordenes_planeadas").select("*").eq("op", id_op).execute().data[0]
                        
                        inicio_payload = {
                            "maquina": m_sel, "op": datos_op['op'], "trabajo": datos_op['trabajo'], "area": area_actual,
                            "vendedor": datos_op['vendedor'], "material": datos_op['material'], 
                            "gramaje": datos_op['gramaje'], "ancho": datos_op['ancho'],
                            "unidades_solicitadas": datos_op['unidades_solicitadas'], "core": datos_op['core'],
                            "tipo_acabado": datos_op['tipo_acabado'], "cant_tintas": datos_op['cant_tintas'],
                            "especificacion_tintas": datos_op['especificacion_tintas'],
                            "orientacion_impresion": datos_op['orientacion_impresion'],
                            "hora_inicio": datetime.now().strftime("%H:%M")
                        }
                        
                        supabase.table("trabajos_activos").insert(inicio_payload).execute()
                        supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", id_op).execute()
                        st.success(f"Trabajo {id_op} iniciado en {m_sel}"); st.rerun()
            else:
                st.warning("No hay órdenes pendientes en Planificación. El administrador debe cargar una orden primero.")
        
        else:
            # FLUJO DE FINALIZACIÓN: MOSTRAR DATOS HEREDADOS
            st.success(f"📌 TRABAJANDO: {trabajo_en_curso['op']} - {trabajo_en_curso['trabajo']}")
            
            # Mostrar Info de Tintas solo si aplica
            if trabajo_en_curso['cant_tintas'] > 0:
                st.info(f"🎨 **TINTAS:** {trabajo_en_curso['cant_tintas']} Colores ({trabajo_en_curso['especificacion_tintas']}) | **LADO:** {trabajo_en_curso['orientacion_impresion']}")
            
            with st.form("form_reporte_final"):
                st.subheader("🏁 Reporte de Finalización")
                reporte_data = {}
                col_i, col_d = st.columns(2)
                
                if area_actual == "IMPRESIÓN":
                    reporte_data["metros_impresos"] = col_i.number_input("Metros Totales", 0.0)
                    reporte_data["bobinas"] = col_d.number_input("Bobinas", 0)
                elif area_actual == "CORTE":
                    reporte_data["total_rollos"] = col_i.number_input("Total Rollos", 0)
                    reporte_data["cant_varillas"] = col_d.number_input("Total Varillas", 0)
                elif area_actual == "COLECTORAS":
                    reporte_data["total_cajas"] = col_i.number_input("Cajas", 0)
                    reporte_data["total_formas"] = col_d.number_input("Formas", 0)
                elif area_actual == "ENCUADERNACIÓN":
                    reporte_data["cant_final"] = col_i.number_input("Cantidad Final", 0)
                    reporte_data["presentacion"] = col_d.text_input("Presentación (Ej: Paquetes)")

                desp_kg = st.number_input("Desperdicio Total (Kg)", 0.0)
                notas = st.text_area("Observaciones del turno")
                
                if st.form_submit_button("🏁 GUARDAR REPORTE Y FINALIZAR"):
                    historial_final = {
                        "op": trabajo_en_curso['op'], "maquina": m_sel, "trabajo": trabajo_en_curso['trabajo'],
                        "h_inicio": trabajo_en_curso['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                        "vendedor": trabajo_en_curso['vendedor'], "material": trabajo_en_curso['material'],
                        "desp_kg": desp_kg, "observaciones": notas
                    }
                    historial_final.update(reporte_data)
                    
                    # Insertar en la tabla de historial correspondiente
                    supabase.table(normalizar(area_actual)).insert(historial_final).execute()
                    # Borrar de activos y marcar como finalizado en planeación
                    supabase.table("trabajos_activos").delete().eq("id", trabajo_en_curso['id']).execute()
                    supabase.table("ordenes_planeadas").update({"estado": "Finalizado"}).eq("op", trabajo_en_curso['op']).execute()
                    
                    st.success("¡Datos guardados! Máquina liberada."); st.rerun()
