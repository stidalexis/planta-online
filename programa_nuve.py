import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import io
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V9.0", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES (CONFIGURACIÓN DE MARCAS Y ESTADOS) ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 15px; border-radius: 12px; text-align: center; color: #1B5E20; box-shadow: 0px 0px 15px rgba(0,230,118,0.5); margin-bottom:10px;}
    .card-parada { background-color: #FF5252; border: 2px solid #D32F2F; padding: 15px; border-radius: 12px; text-align: center; color: white; box-shadow: 0px 0px 15px rgba(255,82,82,0.5); margin-bottom:10px;}
    .card-turno { background-color: #FFD740; border: 2px solid #FFA000; padding: 15px; border-radius: 12px; text-align: center; color: #5D4037; margin-bottom:10px;}
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px; text-align: center; color: #9E9E9E; margin-bottom:10px;}
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

# ==========================================
# MODALES Y DIÁLOGOS (DINÁMICA DE PLANTA)
# ==========================================

@st.dialog("Detalles de la Orden de Producción", width="large")
def mostrar_detalle_op(row):
    st.markdown(f"### 📄 Orden: {row['op']}")
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**DATOS GENERALES**")
        st.write(f"👤 **Cliente:** {row.get('nombre_cliente')}")
        st.write(f"💼 **Vendedor:** {row.get('vendedor')}")
        st.write(f"🛠️ **Trabajo:** {row.get('trabajo')}")
    with col2:
        st.markdown("**ESPECIFICACIONES**")
        st.write(f"📄 **Material:** {row.get('material')}")
        st.write(f"📏 **Medida:** {row.get('ancho_medida')}")
        st.write(f"📦 **Cantidad:** {row.get('unidades_solicitadas')}")
    with col3:
        st.markdown("**PROCESO TÉCNICO**")
        st.write(f"🎨 **Tintas:** {row.get('cant_tintas')}")
        st.write(f"📍 **Área Siguiente:** {row.get('proxima_area')}")
        st.write(f"**Core/Copias:** {row.get('core') if row.get('core') != 'N/A' else row.get('copias')}")
    st.info(f"📝 **Observaciones:** {row.get('observaciones')}")
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        pd.DataFrame([row]).to_excel(writer, index=False)
    st.download_button("📥 DESCARGAR EXCEL", output.getvalue(), f"OP_{row['op']}.xlsx", use_container_width=True)

@st.dialog("REPORTE TÉCNICO DE IMPRESIÓN", width="large")
def modal_reporte_impresion(t, m_s, tipo="FINAL"):
    st.subheader(f"Reporte de Entrega {tipo}: {t['op']}")
    with st.form("f_reporte_detallado"):
        c1, c2, c3 = st.columns(3)
        metros = c1.number_input("Metros Impresos", 0)
        marca = c2.text_input("Marca de Papel")
        bobinas = c3.number_input("Cantidad de Bobinas", 0)
        
        c4, c5, c6 = st.columns(3)
        n_img = c4.number_input("Número de Imágenes", 0)
        gramaje = c5.text_input("Gramaje")
        ancho = c6.text_input("Ancho de Bobina")
        
        c7, c8, c9 = st.columns(3)
        tinta = c7.text_input("Tinta Gastada (Aprox)")
        planchas = c8.number_input("Planchas Gastadas", 0)
        kilos_d = c9.number_input("Kilos Desperdicio", 0.0)
        
        m_desp = st.selectbox("Motivo Desperdicio", ["N/A", "MONTAJE", "REVENTÓN", "MÁQUINA", "OPERARIO"])
        operario = st.text_input("Nombre del Operario")
        obs = st.text_area("Observaciones del Proceso")

        if st.form_submit_button(f"💾 REGISTRAR ENTREGA {tipo}"):
            if operario:
                h_ini = t.get('hora_inicio', datetime.now().strftime("%H:%M"))
                dur = str(datetime.now() - datetime.strptime(h_ini, "%H:%M"))
                
                # Registro en Historial de Impresión
                supabase.table("impresion").insert({
                    "op": t['op'], "maquina": m_s, "trabajo": t['trabajo'], "h_inicio": h_ini,
                    "h_fin": datetime.now().strftime("%H:%M"), "duracion": dur, "metros": metros,
                    "marca": marca, "bobinas": bobinas, "imagenes": n_img, "gramaje": gramaje,
                    "ancho": ancho, "tinta": tinta, "planchas": planchas, "kilos_desp": kilos_d,
                    "motivo_desp": m_desp, "operario": operario, "observaciones": obs, "tipo_entrega": tipo
                }).execute()
                
                if tipo == "FINAL":
                    sig = "CORTE" if t.get('tipo_acabado') == "RI" else "COLECTORAS"
                    supabase.table("ordenes_planeadas").update({"proxima_area": sig, "estado": "Terminado en Impresión"}).eq("op", t['op']).execute()
                else:
                    # Entrega parcial: la OP vuelve a quedar disponible para otra carga o reanudar
                    supabase.table("ordenes_planeadas").update({"estado": "Pendiente"}).eq("op", t['op']).execute()
                
                # Liberar máquina
                supabase.table("trabajos_activos").delete().eq("maquina", m_s).execute()
                st.rerun()
            else:
                st.error("El nombre del operario es obligatorio.")

@st.dialog("🚨 REGISTRAR PARADA DE MÁQUINA")
def modal_parada(t, m_s):
    with st.form("f_parada_tecnica"):
        motivo = st.selectbox("Motivo de la parada:", ["FALLA MECÁNICA", "FALLA ELÉCTRICA", "FALTA MATERIAL", "AJUSTE DE TINTAS", "LIMPIEZA", "REVENTÓN"])
        obs = st.text_area("Descripción del suceso")
        if st.form_submit_button("CONFIRMAR Y DETENER"):
            supabase.table("trabajos_activos").update({
                "estado_maquina": "PARADA", 
                "h_parada": datetime.now().strftime("%H:%M:%S")
            }).eq("maquina", m_s).execute()
            st.rerun()

# ==========================================
# NAVEGACIÓN Y MENÚ LATERAL
# ==========================================
menu = st.sidebar.radio("SISTEMA NUVE V9.0", [
    "🖥️ Monitor General (TV)", 
    "🔍 Seguimiento de Pedidos", 
    "📅 Planificación (Ingreso OP)", 
    "🖨️ Impresión", 
    "✂️ Corte", 
    "📥 Colectoras", 
    "📕 Encuadernación"
])

# 1. MONITOR GENERAL (TV)
if menu == "🖥️ Monitor General (TV)":
    st.title("🏭 Monitor General de Planta")
    try:
        act_data = supabase.table("trabajos_activos").select("*").execute().data
        act = {a['maquina']: a for a in act_data}
    except: act = {}

    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>ÁREA: {area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    d = act[m]
                    est = d.get('estado_maquina', 'PRODUCIENDO')
                    if est == 'PRODUCIENDO':
                        clase, lbl = "card-produccion", "⚡ ACTIVA"
                    elif est == 'PARADA':
                        clase, lbl = "card-parada", "🚨 PARADA"
                    else:
                        clase, lbl = "card-turno", "🌙 ESPERA"
                    
                    st.markdown(f"""
                        <div class='{clase}'>
                            <b style='font-size:1.2rem;'>{m}</b><br>
                            <small>{lbl}</small><hr style='margin:5px;'>
                            <b>{d['op']}</b><br>
                            <small>{d['trabajo']}</small>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'><b>{m}</b><br><small>DISPONIBLE</small></div>", unsafe_allow_html=True)
    time.sleep(15)
    st.rerun()

# 2. SEGUIMIENTO DE PEDIDOS
elif menu == "🔍 Seguimiento de Pedidos":
    st.title("🔍 Seguimiento de Órdenes")
    try:
        ops = supabase.table("ordenes_planeadas").select("*").neq("estado", "Finalizado").execute().data
        if ops:
            df = pd.DataFrame(ops)
            c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
            c1.markdown("**OP**"); c2.markdown("**TRABAJO**"); c3.markdown("**ÁREA ACTUAL**"); c4.markdown("**DETALLES**")
            for _, fila in df.iterrows():
                r1, r2, r3, r4 = st.columns([1, 2, 1, 1])
                r1.write(fila['op']); r2.write(fila['trabajo']); r3.write(fila['proxima_area'])
                if r4.button("🔎 Ver Más", key=f"btn_seg_{fila['op']}"):
                    mostrar_detalle_op(fila)
        else:
            st.info("No hay órdenes activas en el sistema.")
    except Exception as e:
        st.error(f"Error al cargar seguimiento: {e}")

# 3. PLANIFICACIÓN (INGRESO OP)
elif menu == "📅 Planificación (Ingreso OP)":
    st.title("📅 Ingreso de Órdenes de Producción")
    tipo_op_sel = st.selectbox("Tipo de Producto:", ["-- Seleccione --", "RI (Rollo Impreso)", "RB (Rollo Blanco)", "FRI (Forma Impresa)", "FRB (Forma Blanca)"])
    
    if tipo_op_sel != "-- Seleccione --":
        pref = tipo_op_sel.split(" ")[0]
        es_forma = pref in ["FRI", "FRB"]
        es_impreso = pref in ["RI", "FRI"]
        
        with st.form("form_alta_op"):
            st.markdown(f"<div class='title-area'>Formulario {tipo_op_sel}</div>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            op_num = c1.text_input("Número de OP")
            vendedor = c2.text_input("Vendedor")
            cliente = c3.text_input("Cliente")
            trabajo = st.text_input("Nombre del Trabajo")
            
            f1, f2, f3 = st.columns(3)
            material = f1.text_input("Papel / Material")
            medida = f2.text_input("Medida")
            cantidad = f3.number_input("Cantidad Solicitada", min_value=0)
            
            pld = {"core": "N/A", "unidades_bolsa": 0, "unidades_caja": 0, "num_desde": "N/A", "num_hasta": "N/A", "copias": "N/A"}
            
            if not es_forma:
                r1, r2, r3 = st.columns(3)
                pld["core"] = r1.selectbox("Core", ["13MM", "19MM", "1 PULG", "3 PULG"])
                pld["unidades_bolsa"] = r2.number_input("Unidades por Bolsa", 0)
                pld["unidades_caja"] = r3.number_input("Unidades por Caja", 0)
                pArea = "IMPRESIÓN" if pref == "RI" else "CORTE"
            else:
                n1, n2, n3 = st.columns(3)
                pld["num_desde"] = n1.text_input("Numeración Desde")
                pld["num_hasta"] = n2.text_input("Numeración Hasta")
                pld["copias"] = n3.selectbox("Número de Copias", ["1", "2", "3", "4"])
                pArea = "IMPRESIÓN" if pref == "FRI" else "COLECTORAS"
            
            tin_n, tin_c = (0, "N/A")
            if es_impreso:
                i1, i2 = st.columns(2)
                tin_n = i1.number_input("Número de Tintas", 0)
                tin_c = i2.text_input("Especificación de Colores")
            
            obs = st.text_area("Observaciones Generales")
            
            if st.form_submit_button("🚀 REGISTRAR ORDEN"):
                if op_num and trabajo:
                    data = {
                        "op": f"{pref}-{op_num}".upper(), "nombre_cliente": cliente, "trabajo": trabajo,
                        "vendedor": vendedor, "tipo_acabado": pref, "material": material,
                        "ancho_medida": medida, "unidades_solicitadas": cantidad, "cant_tintas": tin_n,
                        "especificacion_tintas": tin_c, "proxima_area": pArea, "observaciones": obs,
                        "estado": "Pendiente", **pld
                    }
                    supabase.table("ordenes_planeadas").insert(data).execute()
                    st.success(f"Orden {pref}-{op_num} registrada exitosamente.")
                    st.balloons()
                else:
                    st.error("Número de OP y Trabajo son obligatorios.")

# 4. MÓDULO DE IMPRESIÓN
elif menu == "🖨️ Impresión":
    st.title("🖨️ Operaciones de Impresión")
    act_list = supabase.table("trabajos_activos").select("*").eq("area", "IMPRESIÓN").execute().data
    act = {a['maquina']: a for a in act_list}
    
    cols_m = st.columns(4)
    for i, m in enumerate(MAQUINAS["IMPRESIÓN"]):
        label = f"⚪ {m}"
        if m in act:
            e = act[m].get('estado_maquina', 'PRODUCIENDO')
            label = f"🔴 {m}" if e == 'PARADA' else f"🟡 {m}" if e == 'TURNO_CERRADO' else f"🟢 {m}"
        if cols_m[i%4].button(label, key=f"btn_imp_main_{m}"):
            st.session_state.m_sel = m

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS["IMPRESIÓN"]:
        ms = st.session_state.m_sel
        st.divider()
        if ms not in act:
            st.subheader(f"Cargar trabajo en: {ms}")
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", "IMPRESIÓN").eq("estado", "Pendiente").execute().data
            if ops:
                sel = st.selectbox("Seleccione OP:", ["--"] + [o['op'] for o in ops])
                if st.button("▶️ INICIAR PRODUCCIÓN"):
                    if sel != "--":
                        d = next(o for o in ops if o['op'] == sel)
                        supabase.table("trabajos_activos").insert({
                            "maquina": ms, "area": "IMPRESIÓN", "op": d['op'], "trabajo": d['trabajo'],
                            "hora_inicio": datetime.now().strftime("%H:%M"), "tipo_acabado": d['tipo_acabado'],
                            "estado_maquina": "PRODUCIENDO"
                        }).execute()
                        supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d['op']).execute()
                        st.rerun()
            else:
                st.warning("No hay órdenes pendientes en Impresión.")
        else:
            t = act[ms]
            est = t.get('estado_maquina', 'PRODUCIENDO')
            st.subheader(f"MÁQUINA {ms} | OP: {t['op']}")
            st.write(f"💼 Trabajo: {t['trabajo']}")
            
            if est == "PRODUCIENDO":
                st.success("⚡ ESTADO: PRODUCIENDO")
                c1, c2, c3, c4 = st.columns(4)
                if c1.button("🚨 PARADA"): modal_parada(t, ms)
                if c2.button("🌙 CERRAR TURNO"):
                    supabase.table("trabajos_activos").update({"estado_maquina": "TURNO_CERRADO"}).eq("maquina", ms).execute()
                    st.rerun()
                if c3.button("📦 ENTREGA PARCIAL"): modal_reporte_impresion(t, ms, "PARCIAL")
                if c4.button("🏁 FINALIZAR TOTAL"): modal_reporte_impresion(t, ms, "FINAL")
            
            elif est == "PARADA":
                st.error(f"🚨 DETENIDA (Desde: {t.get('h_parada')})")
                if st.button("▶️ REANUDAR PRODUCCIÓN", type="primary"):
                    supabase.table("trabajos_activos").update({"estado_maquina": "PRODUCIENDO", "h_parada": None}).eq("maquina", ms).execute()
                    st.rerun()
            
            elif est == "TURNO_CERRADO":
                st.warning("🌙 TRABAJO PAUSADO (CAMBIO DE TURNO)")
                if st.button("☀️ REANUDAR TURNO", type="primary"):
                    supabase.table("trabajos_activos").update({"estado_maquina": "PRODUCIENDO"}).eq("maquina", ms).execute()
                    st.rerun()

# 5. RESTO DE ÁREAS (CORTE, COLECTORAS, ENCUADERNACIÓN)
elif menu in ["✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_nom = menu.split(" ")[1].upper()
    st.title(f"Área: {area_nom}")
    
    act_list = supabase.table("trabajos_activos").select("*").eq("area", area_nom).execute().data
    act = {a['maquina']: a for a in act_list}
    
    cols_area = st.columns(4)
    for i, m in enumerate(MAQUINAS[area_nom]):
        label = f"🔴 {m}" if m in act else f"⚪ {m}"
        if cols_area[i%4].button(label, key=f"btn_{area_nom}_{m}"):
            st.session_state.m_sel_area = m
            
    if "m_sel_area" in st.session_state and st.session_state.m_sel_area in MAQUINAS[area_nom]:
        ms = st.session_state.m_sel_area
        st.divider()
        if ms not in act:
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_nom).execute().data
            if ops:
                sel = st.selectbox("Cargar OP:", ["--"] + [o['op'] for o in ops])
                if st.button(f"▶️ INICIAR EN {ms}"):
                    if sel != "--":
                        d = next(o for o in ops if o['op'] == sel)
                        supabase.table("trabajos_activos").insert({
                            "maquina": ms, "area": area_nom, "op": d['op'], "trabajo": d['trabajo'],
                            "hora_inicio": datetime.now().strftime("%H:%M")
                        }).execute()
                        st.rerun()
        else:
            st.success(f"Trabajando OP: {act[ms]['op']}")
            with st.form("cierre_generico"):
                oper = st.text_input("Nombre Operario")
                if st.form_submit_button("🏁 FINALIZAR TRABAJO"):
                    # Lógica de flujo siguiente
                    if area_nom == "CORTE": sig = "ENCUADERNACIÓN"
                    elif area_nom == "COLECTORAS": sig = "ENCUADERNACIÓN"
                    else: sig = "DESPACHO"
                    
                    supabase.table("ordenes_planeadas").update({"proxima_area": sig}).eq("op", act[ms]['op']).execute()
                    supabase.table("trabajos_activos").delete().eq("maquina", ms).execute()
                    st.rerun()
