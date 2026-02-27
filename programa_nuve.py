import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V7.5", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
# Asegúrate de tener estas llaves en .streamlit/secrets.toml
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES (UX/UI) ---
st.markdown("""
    <style>
    .stButton > button { height: 45px !important; border-radius: 8px; font-weight: bold; width: 100%; }
    .card-proceso { 
        padding: 15px; border-radius: 12px; background-color: #E8F5E9; 
        border-left: 8px solid #2E7D32; margin-bottom: 10px; 
    }
    .card-libre { 
        padding: 15px; border-radius: 12px; background-color: #F5F5F5; 
        border-left: 8px solid #9E9E9E; text-align: center; color: #757575; 
        margin-bottom: 10px; 
    }
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

# ==========================================
# FUNCIÓN: VENTANA EMERGENTE (MODAL DETALLE)
# ==========================================
@st.dialog("Detalles de la Orden de Producción", width="large")
def mostrar_detalle_op(row):
    st.markdown(f"### 📄 Orden: {row['op']}")
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**DATOS DEL CLIENTE**")
        st.write(f"👤 **Cliente:** {row.get('nombre_cliente', 'N/A')}")
        st.write(f"💼 **Vendedor:** {row.get('vendedor', 'N/A')}")
        st.write(f"🛠️ **Trabajo:** {row.get('trabajo', 'N/A')}")
    
    with col2:
        st.markdown("**ESPECIFICACIONES**")
        st.write(f"📄 **Material:** {row.get('material', 'N/A')}")
        st.write(f"📏 **Medida:** {row.get('ancho_medida', 'N/A')}")
        st.write(f"📦 **Cantidad:** {row.get('unidades_solicitadas', 0)}")
    
    with col3:
        st.markdown("**PROCESO**")
        st.write(f"🎨 **Tintas:** {row.get('cant_tintas', 0)}")
        st.write(f"📍 **Área Actual:** {row.get('proxima_area', 'N/A')}")
        st.write(f"📑 **Tipo:** {row.get('tipo_acabado', 'N/A')}")

    st.info(f"📝 **Observaciones:** {row.get('observaciones', 'Sin observaciones')}")
    
    st.divider()
    
    # --- GENERADOR DE EXCEL ---
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Convertimos la fila (Series) a DataFrame para exportar
        df_temp = pd.DataFrame([row])
        df_temp.to_excel(writer, index=False, sheet_name='Ficha_Tecnica')
    
    st.download_button(
        label="📥 DESCARGAR ESTA OP EN EXCEL",
        data=output.getvalue(),
        file_name=f"OP_{row['op']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

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
    st.title("🖥️ Tablero de Control de Planta")
    
    try:
        act_data = supabase.table("trabajos_activos").select("*").execute().data
        act = {a['maquina']: a for a in act_data}
        # Traer OPs que no estén finalizadas
        ops_pendientes = supabase.table("ordenes_planeadas").select("*").neq("estado", "Finalizado").execute().data
    except:
        act, ops_pendientes = {}, []

    st.subheader("Estado de Máquinas")
    tabs = st.tabs(list(MAQUINAS.keys()))
    for i, area in enumerate(MAQUINAS.keys()):
        with tabs[i]:
            cols = st.columns(4)
            for idx, m in enumerate(MAQUINAS[area]):
                with cols[idx % 4]:
                    if m in act:
                        d = act[m]
                        st.markdown(f"<div class='card-proceso'><b>⚙️ {m}</b><br><small>{d['op']}</small></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='card-libre'>⚪ <b>{m}</b><br><small>LIBRE</small></div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("📋 Órdenes en Cola / Pendientes")
    
    if ops_pendientes:
        df_p = pd.DataFrame(ops_pendientes)
        # Selector de área para no saturar la vista
        filtro_area = st.selectbox("Filtrar cola por área:", ["TODAS"] + list(MAQUINAS.keys()))
        cola_final = df_p if filtro_area == "TODAS" else df_p[df_p['proxima_area'] == filtro_area]
        
        # Cabecera de tabla manual
        c1, c2, c3, c4, c5 = st.columns([1, 2, 1, 1, 1])
        c1.write("**OP**")
        c2.write("**TRABAJO**")
        c3.write("**ÁREA**")
        c4.write("**ESTADO**")
        c5.write("**ACCIÓN**")
        
        for _, fila in cola_final.iterrows():
            with st.container():
                r1, r2, r3, r4, r5 = st.columns([1, 2, 1, 1, 1])
                r1.write(fila['op'])
                r2.write(fila['trabajo'])
                r3.write(fila['proxima_area'])
                r4.write(f" `{fila['estado']}`")
                if r5.button("🔎 Ver Detalle", key=f"mon_{fila['op']}"):
                    mostrar_detalle_op(fila)
    else:
        st.info("No hay órdenes pendientes en el sistema.")

# ==========================================
# 2. PLANIFICACIÓN (INGRESO)
# ==========================================
elif menu == "📅 Planificación (Ingreso OP)":
    st.title("📅 Registro de Nueva Orden")
    tipo_op_sel = st.selectbox("TIPO DE PRODUCTO:", ["-- Seleccione --", "RI (Rollo Impreso)", "RB (Rollo Blanco)", "FRI (Forma Impresa)", "FRB (Forma Blanca)"])

    if tipo_op_sel != "-- Seleccione --":
        pref = tipo_op_sel.split(" ")[0]
        es_forma = pref in ["FRI", "FRB"]
        es_impreso = pref in ["RI", "FRI"]

        with st.form("form_op"):
            st.markdown(f"<div class='title-area'>NUEVA OP: {tipo_op_sel}</div>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            op_num = c1.text_input("NÚMERO DE OP")
            vendedor = c2.text_input("VENDEDOR")
            cliente = c3.text_input("CLIENTE")
            trabajo = st.text_input("NOMBRE DEL TRABAJO")

            pld = {"core": "N/A", "unidades_bolsa": 0, "unidades_caja": 0, "num_desde": "N/A", "num_hasta": "N/A", "copias": "N/A", "presentacion": "N/A"}
            f1, f2, f3 = st.columns(3)
            material = f1.text_input("PAPEL")
            medida = f2.text_input("MEDIDA")
            cantidad = f3.number_input("CANTIDAD TOTAL", min_value=0)

            if not es_forma:
                r1, r2, r3 = st.columns(3)
                pld["core"] = r1.selectbox("CORE", ["13MM", "19MM", "1 PULG", "3 PULG"])
                pld["unidades_bolsa"] = r2.number_input("U. BOLSA", 0)
                pld["unidades_caja"] = r3.number_input("U. CAJA", 0)
                pArea = "IMPRESIÓN" if pref == "RI" else "CORTE"
            else:
                n1, n2, n3 = st.columns(3)
                pld["num_desde"], pld["num_hasta"] = n1.text_input("DESDE"), n2.text_input("HASTA")
                pld["copias"] = n3.selectbox("COPIAS", ["1", "2", "3", "4"])
                pArea = "IMPRESIÓN" if pref == "FRI" else "COLECTORAS"

            tin_n, tin_c = 0, "N/A"
            if es_impreso:
                i1, i2 = st.columns(2)
                tin_n = i1.number_input("CANTIDAD TINTAS", 0)
                tin_c = i2.text_input("COLOR TINTAS")

            obs = st.text_area("OBSERVACIONES")
            if st.form_submit_button("🚀 ENVIAR A PRODUCCIÓN"):
                if op_num and trabajo:
                    data = {
                        "op": f"{pref}-{op_num}".upper(), "nombre_cliente": cliente, "trabajo": trabajo,
                        "vendedor": vendedor, "tipo_acabado": pref, "material": material,
                        "ancho_medida": medida, "unidades_solicitadas": cantidad, "cant_tintas": tin_n,
                        "especificacion_tintas": tin_c, "proxima_area": pArea, "observaciones": obs, "estado": "Pendiente", **pld
                    }
                    supabase.table("ordenes_planeadas").insert(data).execute()
                    st.success(f"Registrada OP {pref}-{op_num}")
                    st.balloons()

# ==========================================
# 3. MÓDULOS OPERATIVOS
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}[menu]
    st.title(f"Área: {area}")
    
    act_data = supabase.table("trabajos_activos").select("*").eq("area", area).execute().data
    activos = {a['maquina']: a for a in act_data}
    
    # Grid de Máquinas
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS[area]):
        label = f"{'🔴' if m in activos else '⚪'} {m}"
        if cols[i % 4].button(label, key=f"btn_op_{m}"):
            st.session_state.m_sel = m

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area]:
        m_s = st.session_state.m_sel
        st.subheader(f"Máquina: {m_s}")
        
        if m_s not in activos:
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area).eq("estado", "Pendiente").execute().data
            if ops:
                op_opciones = [f"{o['op']} | {o['trabajo']}" for o in ops]
                sel = st.selectbox("Seleccione OP para iniciar:", ["--"] + op_opciones)
                if st.button("▶️ INICIAR TRABAJO"):
                    if sel != "--":
                        d = next(o for o in ops if o['op'] == sel.split(" | ")[0])
                        supabase.table("trabajos_activos").insert({
                            "maquina": m_s, "area": area, "op": d['op'], "trabajo": d['trabajo'],
                            "nombre_cliente": d['nombre_cliente'], "tipo_acabado": d['tipo_acabado'],
                            "hora_inicio": datetime.now().strftime("%H:%M")
                        }).execute()
                        supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d['op']).execute()
                        st.rerun()
            else:
                st.warning("No hay órdenes pendientes para esta área.")
        else:
            # TRABAJO EN PROCESO - CIERRE
            t = activos[m_s]
            st.success(f"TRABAJANDO: {t['op']} - {t['trabajo']}")
            if st.button("🏁 FINALIZAR Y PASAR A SIGUIENTE ÁREA"):
                # Lógica de Flujo
                sig = "FINALIZADO"
                if t['tipo_acabado'] == "RI" and area == "IMPRESIÓN": sig = "CORTE"
                elif t['tipo_acabado'] == "FRI" and area == "IMPRESIÓN": sig = "COLECTORAS"
                elif t['tipo_acabado'] in ["FRI","FRB"] and area == "COLECTORAS": sig = "ENCUADERNACIÓN"

                # Guardar Historial
                hist = {"op":t['op'], "maquina":m_s, "trabajo":t['trabajo'], "h_inicio":t['hora_inicio'], "h_fin":datetime.now().strftime("%H:%M")}
                supabase.table(normalizar(area)).insert(hist).execute()
                
                # Actualizar OP y Borrar Activo
                supabase.table("ordenes_planeadas").update({"proxima_area":sig, "estado":"Pendiente" if sig != "FINALIZADO" else "Finalizado"}).eq("op", t['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", m_s).execute()
                st.rerun()

# ==========================================
# 4. HISTORIAL
# ==========================================
elif menu == "📊 Historial KPI":
    st.title("📊 Historial de Producción")
    t_names = ["impresion", "corte", "colectoras", "encuadernacion"]
    tabs = st.tabs([n.capitalize() for n in t_names])
    for i, tab in enumerate(tabs):
        with tab:
            data = supabase.table(t_names[i]).select("*").execute().data
            if data: st.dataframe(pd.DataFrame(data), use_container_width=True)
            else: st.write("Sin datos registrados.")
