import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import io
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V10.2", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES ORIGINALES ---
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
# MODALES (SEGUIMIENTO Y REPORTES)
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
        st.write(f"🎨 **Tintas:** {row.get('cant_tintas')} ({row.get('especificacion_tintas')})")
    with col3:
        st.markdown("**PROCESO TÉCNICO**")
        st.write(f"⚙️ **Core:** {row.get('core')}")
        st.write(f"🔢 **Numeración:** {row.get('num_desde')} - {row.get('num_hasta')}")
        st.write(f"📑 **Copias:** {row.get('copias')}")
    
    st.info(f"📝 **Observaciones:** {row.get('observaciones')}")
    
    if row.get('url_arte'):
        st.markdown("---")
        st.markdown("### 🎨 ARTE DEL TRABAJO")
        st.link_button("📂 ABRIR ARTE / PDF", row['url_arte'], use_container_width=True)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        pd.DataFrame([row]).to_excel(writer, index=False)
    st.download_button("📥 DESCARGAR EXCEL INDIVIDUAL", output.getvalue(), f"OP_{row['op']}.xlsx", use_container_width=True)

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
                try: dur = str(datetime.now() - datetime.strptime(h_ini, "%H:%M"))
                except: dur = "N/A"
                
                data_insert = {
                    "op": str(t['op']), "maquina": str(m_s), "trabajo": str(t['trabajo']), "h_inicio": str(h_ini),
                    "h_fin": datetime.now().strftime("%H:%M"), "duracion": dur, "metros": int(metros),
                    "marca": str(marca), "bobinas": int(bobinas), "imagenes": int(n_img), "gramaje": str(gramaje),
                    "ancho": str(ancho), "tinta": str(tinta), "planchas": int(planchas), "kilos_desp": float(kilos_d),
                    "motivo_desp": str(m_desp), "operario": str(operario), "observaciones": str(obs), "tipo_entrega": tipo
                }
                
                try:
                    supabase.table("impresion").insert(data_insert).execute()
                    if tipo == "FINAL":
                        sig = "CORTE" if t.get('tipo_acabado') == "RI" else "COLECTORAS"
                        supabase.table("ordenes_planeadas").update({"proxima_area": sig, "estado": "Terminado en Impresión"}).eq("op", t['op']).execute()
                    else:
                        supabase.table("ordenes_planeadas").update({"estado": "Pendiente"}).eq("op", t['op']).execute()
                    
                    supabase.table("trabajos_activos").delete().eq("maquina", m_s).execute()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error en Base de Datos: {e}")
            else:
                st.error("El nombre del operario es obligatorio.")

@st.dialog("🚨 REGISTRAR PARADA")
def modal_parada(t, m_s):
    with st.form("f_p"):
        motivo = st.selectbox("Motivo:", ["MECÁNICO", "ELÉCTRICO", "MATERIAL", "AJUSTE", "REVENTÓN"])
        if st.form_submit_button("CONFIRMAR PARADA"):
            supabase.table("trabajos_activos").update({"estado_maquina": "PARADA", "h_parada": datetime.now().strftime("%H:%M:%S")}).eq("maquina", m_s).execute()
            st.rerun()

# ==========================================
# NAVEGACIÓN
# ==========================================
menu = st.sidebar.radio("SISTEMA NUVE V10.2", ["🖥️ Monitor General (TV)", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# 1. MONITOR GENERAL
if menu == "🖥️ Monitor General (TV)":
    st.title("🏭 Monitor General de Planta")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    d = act[m]
                    est = d.get('estado_maquina', 'PRODUCIENDO')
                    clase = "card-produccion" if est == 'PRODUCIENDO' else "card-parada" if est == 'PARADA' else "card-turno"
                    lbl = "⚡ ACTIVA" if est == 'PRODUCIENDO' else "🚨 PARADA" if est == 'PARADA' else "🌙 ESPERA"
                    st.markdown(f"<div class='{clase}'><b>{m}</b><br><small>{lbl}</small><hr><b>{d['op']}</b><br><small>{d['trabajo']}</small></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'><b>{m}</b><br><small>LIBRE</small></div>", unsafe_allow_html=True)
    time.sleep(15); st.rerun()

# 2. SEGUIMIENTO
elif menu == "🔍 Seguimiento":
    st.title("🔍 Seguimiento de Órdenes")
    ops = supabase.table("ordenes_planeadas").select("*").neq("estado", "Finalizado").execute().data
    if ops:
        df = pd.DataFrame(ops)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 DESCARGAR TODAS LAS ORDENES EN ESPERA", output.getvalue(), "Seguimiento_Completo.xlsx", use_container_width=True)
        
        st.divider()
        c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
        c1.markdown("**OP**"); c2.markdown("**TRABAJO**"); c3.markdown("**ÁREA ACTUAL**"); c4.markdown("**DETALLES**")
        for _, fila in df.iterrows():
            r1, r2, r3, r4 = st.columns([1, 2, 1, 1])
            r1.write(fila['op']); r2.write(fila['trabajo']); r3.warning(fila['proxima_area'])
            if r4.button("🔎 Ver Más / Arte", key=f"btn_seg_{fila['op']}"): mostrar_detalle_op(fila)

# 3. PLANIFICACIÓN
elif menu == "📅 Planificación":
    st.title("📅 Ingreso de Órdenes de Producción")
    tipo_op_sel = st.selectbox("Tipo de Producto:", ["-- Seleccione --", "RI (Rollo Impreso)", "RB (Rollo Blanco)", "FRI (Forma Impresa)", "FRB (Forma Blanca)"])
    
    if tipo_op_sel != "-- Seleccione --":
        pref = tipo_op_sel.split(" ")[0]
        es_impreso = pref in ["RI", "FRI"]
        
        # Carga de arte independiente
        if es_impreso:
            archivo_arte = st.file_uploader("🖼️ Cargar Arte (PDF/JPG/PNG)", type=["pdf", "png", "jpg", "jpeg"])
            if archivo_arte:
                if st.button("⬆️ SUBIR ARTE PRIMERO"):
                    with st.spinner("Subiendo archivo..."):
                        path = f"artes/{pref}_{int(time.time())}_{archivo_arte.name}"
                        try:
                            supabase.storage.from_("artes").upload(path, archivo_arte.getvalue())
                            url_res = supabase.storage.from_("artes").get_public_url(path)
                            st.session_state['url_temp'] = url_res
                            st.success("✅ Arte listo.")
                        except Exception as e:
                            st.error(f"Error: {e}")

        with st.form("form_alta_op"):
            c1, c2, c3 = st.columns(3)
            op_num = c1.text_input("Número de OP")
            vendedor = c2.text_input("Vendedor"); cliente = c3.text_input("Cliente")
            trabajo = st.text_input("Nombre del Trabajo")
            
            f1, f2, f3 = st.columns(3)
            material = f1.text_input("Papel / Material"); medida = f2.text_input("Medida")
            cantidad = f3.number_input("Cantidad Solicitada", min_value=0)
            
            pld = {"core": "N/A", "unidades_bolsa": 0, "unidades_caja": 0, "num_desde": "N/A", "num_hasta": "N/A", "copias": "N/A"}
            if pref in ["RI", "RB"]:
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
            
            tin_n = 0; tin_c = "N/A"
            if es_impreso:
                i1, i2 = st.columns(2)
                tin_n = i1.number_input("Número de Tintas", 0)
                tin_c = i2.text_input("Especificación de Colores")
            
            obs = st.text_area("Observaciones")
            if st.form_submit_button("🚀 REGISTRAR ORDEN"):
                u_final = st.session_state.get('url_temp', None)
                data = {"op": f"{pref}-{op_num}".upper(), "nombre_cliente": cliente, "trabajo": trabajo, "vendedor": vendedor, "tipo_acabado": pref, "material": material, "ancho_medida": medida, "unidades_solicitadas": cantidad, "cant_tintas": tin_n, "especificacion_tintas": tin_c, "proxima_area": pArea, "observaciones": obs, "estado": "Pendiente", "url_arte": u_final, **pld}
                supabase.table("ordenes_planeadas").insert(data).execute()
                if 'url_temp' in st.session_state: del st.session_state['url_temp']
                st.success("Orden registrada.")
                st.rerun()

# 4. IMPRESIÓN
elif menu == "🖨️ Impresión":
    st.title("🖨️ Operaciones de Impresión")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", "IMPRESIÓN").execute().data}
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS["IMPRESIÓN"]):
        lbl = f"⚪ {m}"
        if m in act:
            e = act[m].get('estado_maquina', 'PRODUCIENDO')
            lbl = f"🔴 {m}" if e == 'PARADA' else f"🟡 {m}" if e == 'TURNO_CERRADO' else f"🟢 {m}"
        if cols[i%4].button(lbl, key=f"im_{m}"): st.session_state.m_sel = m

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS["IMPRESIÓN"]:
        ms = st.session_state.m_sel
        st.divider()
        if ms not in act:
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", "IMPRESIÓN").eq("estado", "Pendiente").execute().data
            if ops:
                sel = st.selectbox("OP:", [o['op'] for o in ops])
                if st.button("▶️ INICIAR"):
                    d = next(o for o in ops if o['op'] == sel)
                    supabase.table("trabajos_activos").insert({"maquina": ms, "area": "IMPRESIÓN", "op": d['op'], "trabajo": d['trabajo'], "hora_inicio": datetime.now().strftime("%H:%M"), "tipo_acabado": d['tipo_acabado'], "estado_maquina": "PRODUCIENDO"}).execute()
                    supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d['op']).execute()
                    st.rerun()
        else:
            t = act[ms]
            est = t.get('estado_maquina', 'PRODUCIENDO')
            st.subheader(f"MÁQUINA {ms} | OP: {t['op']}")
            if est == "PRODUCIENDO":
                c1, c2, c3, c4 = st.columns(4)
                if c1.button("🚨 PARADA"): modal_parada(t, ms)
                if c2.button("🌙 TURNO"): 
                    supabase.table("trabajos_activos").update({"estado_maquina": "TURNO_CERRADO"}).eq("maquina", ms).execute()
                    st.rerun()
                if c3.button("📦 PARCIAL"): modal_reporte_impresion(t, ms, "PARCIAL")
                if c4.button("🏁 FINALIZAR"): modal_reporte_impresion(t, ms, "FINAL")
            else:
                if st.button("▶️ REANUDAR"): 
                    supabase.table("trabajos_activos").update({"estado_maquina": "PRODUCIENDO"}).eq("maquina", ms).execute()
                    st.rerun()

# 5. RESTO DE ÁREAS
elif menu in ["✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    a_nom = menu.split(" ")[1].upper()
    st.title(a_nom)
    act_a = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", a_nom).execute().data}
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS[a_nom]):
        if cols[i%4].button(f"{'🔴' if m in act_a else '⚪'} {m}", key=f"a_{m}"): st.session_state.m_sel_a = m
    if "m_sel_a" in st.session_state and st.session_state.m_sel_a in MAQUINAS[a_nom]:
        ms = st.session_state.m_sel_a
        if ms not in act_a:
            ops_a = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", a_nom).execute().data
            if ops_a:
                sel_a = st.selectbox("OP:", [o['op'] for o in ops_a])
                if st.button(f"INICIAR EN {ms}"):
                    d = next(o for o in ops_a if o['op'] == sel_a)
                    supabase.table("trabajos_activos").insert({"maquina": ms, "area": a_nom, "op": d['op'], "trabajo": d['trabajo'], "hora_inicio": datetime.now().strftime("%H:%M")}).execute()
                    st.rerun()
        else:
            if st.button("🏁 FINALIZAR"):
                sig = "ENCUADERNACIÓN" if a_nom in ["CORTE", "COLECTORAS"] else "DESPACHO"
                supabase.table("ordenes_planeadas").update({"proxima_area": sig}).eq("op", act_a[ms]['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", ms).execute()
                st.rerun()
