import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V7.5", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES (UX/UI) ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    .card-proceso { 
        padding: 15px; border-radius: 12px; background-color: #E8F5E9; 
        border-left: 8px solid #2E7D32; border-top: 1px solid #C8E6C9;
        border-right: 1px solid #C8E6C9; border-bottom: 1px solid #C8E6C9;
        margin-bottom: 15px; 
    }
    .card-libre { 
        padding: 15px; border-radius: 12px; background-color: #F5F5F5; 
        border-left: 8px solid #9E9E9E; text-align: center; color: #757575; 
        margin-bottom: 15px; 
    }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .detalles-op { font-size: 0.85rem; color: #1B5E20; line-height: 1.2; }
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
# 1. MONITOR GENERAL (DETALLADO + PENDIENTES)
# ==========================================
if menu == "🖥️ Monitor General":
    st.title("🖥️ Tablero de Control de Planta")
    
    # Traer datos de OPs activas y planeadas
    try:
        act_data = supabase.table("trabajos_activos").select("*").execute().data
        act = {a['maquina']: a for a in act_data}
        
        # Traer todas las OPs que aún no terminan (Pendientes)
        ops_pendientes = supabase.table("ordenes_planeadas").select("*").neq("estado", "Finalizado").execute().data
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        act, ops_pendientes = {}, []

    # --- PARTE A: ESTADO DE MÁQUINAS ---
    st.subheader("Estado de Máquinas")
    tabs = st.tabs(list(MAQUINAS.keys()))
    
    for i, area in enumerate(MAQUINAS.keys()):
        with tabs[i]:
            cols = st.columns(3)
            for idx, m in enumerate(MAQUINAS[area]):
                with cols[idx % 3]:
                    if m in act:
                        d = act[m]
                        st.markdown(f"<div class='card-proceso'><b>⚙️ {m}</b><br>OCUPADA: {d['op']}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='card-libre'>⚪ <b>{m}</b><br>DISPONIBLE</div>", unsafe_allow_html=True)

    st.divider()

    # --- PARTE B: COLA DE TRABAJO (PENDIENTES POR ÁREA) ---
    st.subheader("📋 Órdenes en Cola (Pendientes)")
    
    if ops_pendientes:
        df_pendientes = pd.DataFrame(ops_pendientes)
        
        # Filtro por área en el monitor
        area_f = st.selectbox("Filtrar cola por área:", ["TODAS"] + list(MAQUINAS.keys()))
        cola_mostrar = df_pendientes if area_f == "TODAS" else df_pendientes[df_pendientes['proxima_area'] == area_f]

        for _, row in cola_mostrar.iterrows():
            with st.expander(f"📌 OP: {row['op']} | {row['trabajo']} | {row['proxima_area']}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Mostrar toda la información técnica que pediste
                    st.write(f"**Cliente:** {row['nombre_cliente']}")
                    st.write(f"**Material:** {row['material']} | **Medida:** {row['ancho_medida']}")
                    st.write(f"**Cantidad:** {row['unidades_solicitadas']}")
                    if row['tipo_acabado'] in ["RI", "FRI"]:
                        st.write(f"**Tintas:** {row['cant_tintas']} ({row['especificacion_tintas']})")
                    st.write(f"**Observaciones:** {row['observaciones']}")

                with col2:
                    # BOTÓN DE DESCARGA EXCEL PARA ESTA OP
                    # Creamos un DF de una sola fila para el Excel
                    df_export = pd.DataFrame([row])
                    
                    # Convertir a Excel en memoria
                    import io
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_export.to_excel(writer, index=False, sheet_name='Orden_Produccion')
                    
                    st.download_button(
                        label="📥 Descargar Excel OP",
                        data=output.getvalue(),
                        file_name=f"OP_{row['op']}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_{row['op']}"
                    )
    else:
        st.info("No hay órdenes pendientes en este momento.")

# ==========================================
# 2. PLANIFICACIÓN (VENDEDORES)
# ==========================================
elif menu == "📅 Planificación (Ingreso OP)":
    st.title("📅 Registro de Nueva Orden de Producción")
    
    tipo_op_sel = st.selectbox("TIPO DE PRODUCTO:", 
                             ["-- Seleccione --", "RI (Rollo Impreso)", "RB (Rollo Blanco)", "FRI (Forma Impresa)", "FRB (Forma Blanca)"])

    if tipo_op_sel != "-- Seleccione --":
        pref = tipo_op_sel.split(" ")[0]
        es_forma = pref in ["FRI", "FRB"]
        es_impreso = pref in ["RI", "FRI"]

        with st.form("form_op_definitivo"):
            st.markdown(f"<div class='title-area'>FORMULARIO: {tipo_op_sel}</div>", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            op_num = c1.text_input("NÚMERO DE OP")
            vendedor = c2.text_input("VENDEDOR")
            cliente = c3.text_input("NOMBRE DEL CLIENTE")
            trabajo = st.text_input("NOMBRE DEL TRABAJO")

            st.divider()

            # Variables para Payload
            pld = {"core": "N/A", "unidades_bolsa": 0, "unidades_caja": 0, "num_desde": "N/A", "num_hasta": "N/A", "copias": "N/A", "fondo_copias": "N/A", "traficos_orden": "N/A", "codigo_barras": "NO", "perforaciones": "N/A", "presentacion": "N/A"}

            f1, f2, f3 = st.columns(3)
            material = f1.text_input("TIPO DE PAPEL")
            medida = f2.text_input("MEDIDA")
            cantidad = f3.number_input("CANTIDAD TOTAL", min_value=0)

            if not es_forma: # ROLLOS
                r1, r2, r3 = st.columns(3)
                pld["core"] = r1.selectbox("CORE", ["13MM", "19MM", "1 PULG", "2 PULG", "3 PULG", "40MM"])
                pld["unidades_bolsa"] = r2.number_input("UNIDADES POR BOLSA", 0)
                pld["unidades_caja"] = r3.number_input("UNIDADES POR CAJA", 0)
                pArea = "IMPRESIÓN" if pref == "RI" else "CORTE"
            else: # FORMAS
                n1, n2, n3 = st.columns(3)
                pld["num_desde"] = n1.text_input("NUMERACIÓN DESDE")
                pld["num_hasta"] = n2.text_input("NUMERACIÓN HASTA")
                pld["copias"] = n3.selectbox("COPIAS", ["1", "2", "3", "4", "5", "6", "7"])
                b1, b2, b3 = st.columns(3)
                pld["fondo_copias"] = b1.text_input("FONDO DE COPIAS")
                pld["traficos_orden"] = b2.text_input("TRÁFICOS EN ORDEN")
                pld["codigo_barras"] = b3.text_input("CÓDIGO DE BARRAS (TIPO O NO)")
                p1, p2 = st.columns(2)
                pld["perforaciones"] = p1.text_input("PERFORACIONES")
                pld["presentacion"] = p2.selectbox("PRESENTACIÓN", ["BLOCK TAPA DURA", "BLOCK NORMAL", "LICOM", "PAQUETES", "SUELTAS"])
                pArea = "IMPRESIÓN" if pref == "FRI" else "COLECTORAS"

            tin_n, tin_c, cara = 0, "N/A", "N/A"
            if es_impreso:
                st.subheader("Configuración de Impresión")
                i1, i2, i3 = st.columns(3)
                tin_n = i1.number_input("CANTIDAD DE TINTAS", 0)
                tin_c = i2.text_input("CUALES TINTAS")
                cara = i3.selectbox("CARA DE IMPRESIÓN", ["FRENTE", "RESPALDO", "AMBAS"])

            obs = st.text_area("OBSERVACIONES")

            if st.form_submit_button("🚀 REGISTRAR E INVIAR A PRODUCCIÓN"):
                if op_num and trabajo:
                    try:
                        final_data = {
                            "op": f"{pref}-{op_num}".upper(), "nombre_cliente": cliente, "trabajo": trabajo,
                            "vendedor": vendedor, "tipo_acabado": pref, "material": material,
                            "ancho_medida": medida, "unidades_solicitadas": cantidad, "cant_tintas": tin_n,
                            "especificacion_tintas": tin_c, "orientacion_impresion": cara,
                            "proxima_area": pArea, "observaciones": obs, **pld
                        }
                        supabase.table("ordenes_planeadas").insert(final_data).execute()
                        st.success(f"✅ OP {pref}-{op_num} registrada en {pArea}")
                        st.balloons()
                    except Exception as e: st.error(f"Error: {e}")

# ==========================================
# 3. MÓDULOS OPERATIVOS
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}[menu]
    st.title(f"Área: {area}")
    
    act_data = supabase.table("trabajos_activos").select("*").eq("area", area).execute().data
    activos = {a['maquina']: a for a in act_data}
    
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS[area]):
        label = f"{'🔴' if m in activos else '⚪'} {m}"
        if cols[i % 4].button(label, key=m): st.session_state.m_sel = m

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area]:
        m_s = st.session_state.m_sel
        st.subheader(f"Máquina: {m_s}")
        
        if m_s not in activos:
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area).eq("estado", "Pendiente").execute().data
            if ops:
                sel = st.selectbox("Seleccione OP:", ["--"] + [f"{o['op']} | {o['trabajo']}" for o in ops])
                if st.button("▶️ INICIAR"):
                    if sel != "--":
                        d = next(o for o in ops if o['op'] == sel.split(" | ")[0])
                        # Insertar en activos incluyendo los nuevos campos para el monitor
                        supabase.table("trabajos_activos").insert({
                            "maquina": m_s, "area": area, "op": d['op'], "trabajo": d['trabajo'],
                            "nombre_cliente": d['nombre_cliente'], "vendedor": d['vendedor'],
                            "material": d['material'], "ancho_medida": d['ancho_medida'],
                            "unidades_solicitadas": d['unidades_solicitadas'], "tipo_acabado": d['tipo_acabado'],
                            "cant_tintas": d['cant_tintas'], "especificacion_tintas": d['especificacion_tintas'],
                            "core": d['core'], "copias": d['copias'], "hora_inicio": datetime.now().strftime("%H:%M")
                        }).execute()
                        supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d['op']).execute()
                        st.rerun()
        else:
            t = activos[m_s]
            st.info(f"TRABAJANDO: {t['op']} - {t['trabajo']}")
            with st.form("cierre"):
                kpi = {}
                if area == "IMPRESIÓN": kpi["metros_impresos"], kpi["bobinas"] = st.columns(2)[0].number_input("Metros",0.0), st.columns(2)[1].number_input("Bobinas",0)
                elif area == "CORTE": kpi["metros_finales"], kpi["total_rollos"] = st.columns(2)[0].number_input("Metros",0.0), st.columns(2)[1].number_input("Rollos",0)
                elif area == "COLECTORAS": kpi["total_cajas"], kpi["total_formas"] = st.columns(2)[0].number_input("Cajas",0), st.columns(2)[1].number_input("Formas",0)
                elif area == "ENCUADERNACIÓN": kpi["cant_final"], kpi["presentacion"] = st.columns(2)[0].number_input("Final",0), st.columns(2)[1].text_input("Empaque")
                
                des = st.number_input("Desperdicio KG", 0.0)
                if st.form_submit_button("🏁 FINALIZAR"):
                    sig = "FINALIZADO"
                    if t['tipo_acabado'] == "RI" and area == "IMPRESIÓN": sig = "CORTE"
                    elif t['tipo_acabado'] == "FRI" and area == "IMPRESIÓN": sig = "COLECTORAS"
                    elif t['tipo_acabado'] in ["FRI","FRB"] and area == "COLECTORAS": sig = "ENCUADERNACIÓN"
                    
                    hist = {"op":t['op'],"maquina":m_s,"trabajo":t['trabajo'],"vendedor":t['vendedor'],"h_inicio":t['hora_inicio'],"h_fin":datetime.now().strftime("%H:%M"),"desp_kg":des,**kpi}
                    supabase.table(normalizar(area)).insert(hist).execute()
                    supabase.table("ordenes_planeadas").update({"proxima_area":sig,"estado":"Pendiente" if sig != "FINALIZADO" else "Finalizado"}).eq("op", t['op']).execute()
                    supabase.table("trabajos_activos").delete().eq("id", t['id']).execute()
                    st.rerun()

# ==========================================
# 4. HISTORIAL KPI
# ==========================================
elif menu == "📊 Historial KPI":
    st.title("📊 Análisis de KPIs")
    t_names = ["impresion", "corte", "colectoras", "encuadernacion"]
    tabs = st.tabs([n.capitalize() for n in t_names])
    for i, tab in enumerate(tabs):
        with tab:
            data = supabase.table(t_names[i]).select("*").order("fecha_fin", desc=True).execute().data
            if data: st.dataframe(pd.DataFrame(data), use_container_width=True)
                

