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

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 15px; border-radius: 12px; text-align: center; color: #1B5E20; box-shadow: 0px 0px 15px rgba(0,230,118,0.5); margin-bottom:10px;}
    .card-parada { background-color: #FF5252; border: 2px solid #D32F2F; padding: 15px; border-radius: 12px; text-align: center; color: white; box-shadow: 0px 0px 15px rgba(255,82,82,0.5); margin-bottom:10px;}
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px; text-align: center; color: #9E9E9E; margin-bottom:10px;}
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- FUNCIONES DE EXCEL ---
def generar_excel(df, nombre_archivo):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Datos')
    return output.getvalue()

# --- MODALES ---
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
        st.write(f"⚙️ **Core:** {row.get('core')}")
        st.write(f"🔢 **Numeración:** {row.get('num_desde')} - {row.get('num_hasta')}")
        st.write(f"📑 **Copias:** {row.get('copias')}")
    
    st.info(f"📝 **Observaciones:** {row.get('observaciones')}")
    
    if row.get('url_arte'):
        st.link_button("🎨 ABRIR ARTE / PDF", row['url_arte'], use_container_width=True)

    excel_data = generar_excel(pd.DataFrame([row]), f"OP_{row['op']}.xlsx")
    st.download_button("📥 DESCARGAR EXCEL INDIVIDUAL", excel_data, f"OP_{row['op']}.xlsx", use_container_width=True)

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
        tinta = c7.text_input("Tinta Gastada")
        planchas = c8.number_input("Planchas Gastadas", 0)
        kilos_d = c9.number_input("Kilos Desperdicio", 0.0)
        
        m_desp = st.selectbox("Motivo Desperdicio", ["N/A", "MONTAJE", "REVENTÓN", "MÁQUINA", "OPERARIO"])
        operario = st.text_input("Nombre del Operario")
        obs = st.text_area("Observaciones")

        if st.form_submit_button(f"💾 REGISTRAR ENTREGA {tipo}"):
            if operario:
                h_ini = t.get('hora_inicio', datetime.now().strftime("%H:%M"))
                data_insert = {
                    "op": str(t['op']), "maquina": str(m_s), "trabajo": str(t['trabajo']), "h_inicio": str(h_ini),
                    "h_fin": datetime.now().strftime("%H:%M"), "metros": int(metros), "marca": str(marca), 
                    "bobinas": int(bobinas), "imagenes": int(n_img), "gramaje": str(gramaje), "ancho": str(ancho),
                    "tinta": str(tinta), "planchas": int(planchas), "kilos_desp": float(kilos_d),
                    "motivo_desp": str(m_desp), "operario": str(operario), "observaciones": str(obs), "tipo_entrega": tipo
                }
                supabase.table("impresion").insert(data_insert).execute()
                if tipo == "FINAL":
                    sig = "CORTE" if t.get('tipo_acabado') == "RI" else "COLECTORAS"
                    supabase.table("ordenes_planeadas").update({"proxima_area": sig, "estado": "Terminado"}).eq("op", t['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", m_s).execute()
                st.rerun()
            else: st.error("Operario es obligatorio.")

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("SISTEMA NUVE V10.2", ["🖥️ Monitor General", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# 1. MONITOR GENERAL
if menu == "🖥️ Monitor General":
    st.title("🏭 Monitor General de Planta")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    d = act[m]
                    clase = "card-produccion" if d.get('estado_maquina') == 'PRODUCIENDO' else "card-parada"
                    st.markdown(f"<div class='{clase}'><b>{m}</b><br><small>{d['op']}</small><br><b>{d['trabajo']}</b></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'><b>{m}</b><br><small>LIBRE</small></div>", unsafe_allow_html=True)
    time.sleep(15); st.rerun()

# 2. SEGUIMIENTO (HISTORIAL Y DESCARGAS)
elif menu == "🔍 Seguimiento":
    st.title("🔍 Seguimiento de Órdenes")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if res:
        df = pd.DataFrame(res)
        
        c1, c2 = st.columns([3, 1])
        with c1: st.info(f"Total de órdenes en sistema: {len(df)}")
        with c2:
            excel_all = generar_excel(df, "Seguimiento_General.xlsx")
            st.download_button("📥 DESCARGAR TODO (EXCEL)", excel_all, "Seguimiento_General.xlsx", use_container_width=True)
        
        st.divider()
        # Buscador básico
        busqueda = st.text_input("Filtrar por OP o Cliente:", "").upper()
        if busqueda:
            df = df[df['op'].str.contains(busqueda) | df['nombre_cliente'].str.contains(busqueda)]

        # Header de tabla personalizada
        h1, h2, h3, h4, h5 = st.columns([1, 2, 1, 1, 1])
        h1.write("**OP**"); h2.write("**TRABAJO**"); h3.write("**CLIENTE**"); h4.write("**ÁREA ACTUAL**"); h5.write("**DETALLES**")
        
        for _, fila in df.iterrows():
            r1, r2, r3, r4, r5 = st.columns([1, 2, 1, 1, 1])
            r1.write(fila['op'])
            r2.write(fila['trabajo'])
            r3.write(fila['nombre_cliente'])
            r4.warning(fila['proxima_area'])
            if r5.button("🔎 Ver / Excel", key=f"seg_{fila['op']}"):
                mostrar_detalle_op(fila)
    else:
        st.warning("No hay órdenes registradas.")

# 3. PLANIFICACIÓN (BOTONES + FORMULARIO COMPLETO)
elif menu == "📅 Planificación":
    st.title("📅 Ingreso de Órdenes de Producción")
    
    st.markdown("### Seleccione Tipo de Producto:")
    b1, b2, b3, b4 = st.columns(4)
    if b1.button("RI (Rollo Impreso)"): st.session_state.tipo = "RI"
    if b2.button("RB (Rollo Blanco)"): st.session_state.tipo = "RB"
    if b3.button("FRI (Forma Impresa)"): st.session_state.tipo = "FRI"
    if b4.button("FRB (Forma Blanca)"): st.session_state.tipo = "FRB"

    if "tipo" in st.session_state:
        pref = st.session_state.tipo
        es_impreso = "I" in pref
        st.success(f"Configurando: {pref}")

        # Subida de Arte (Fuera del form para evitar bugs)
        url_arte = None
        if es_impreso:
            archivo = st.file_uploader("🖼️ Cargar Arte", type=["pdf", "png", "jpg"])
            if archivo:
                if st.button("⬆️ SUBIR ARCHIVO"):
                    with st.spinner("Subiendo..."):
                        path = f"artes/{int(time.time())}_{archivo.name}"
                        supabase.storage.from_("artes").upload(path, archivo.getvalue())
                        url_arte = supabase.storage.from_("artes").get_public_url(path)
                        st.session_state.url_temp = url_arte
                        st.toast("Arte subido correctamente")

        with st.form("f_alta", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            op_num = c1.text_input("Número de OP")
            vendedor = c2.text_input("Vendedor")
            cliente = c3.text_input("Cliente")
            trabajo = st.text_input("Nombre del Trabajo")
            
            f1, f2, f3 = st.columns(3)
            material = f1.text_input("Papel / Material")
            medida = f2.text_input("Medida")
            cantidad = f3.number_input("Cantidad Solicitada", 0)
            
            # Datos técnicos dinámicos
            core_val, bolsa, caja, desde, hasta, copias = "N/A", 0, 0, "N/A", "N/A", "N/A"
            if "R" in pref: # Rollos
                t1, t2, t3 = st.columns(3)
                core_val = t1.selectbox("Core", ["13MM", "19MM", "1 PULG", "3 PULG"])
                bolsa = t2.number_input("Unidades/Bolsa", 0)
                caja = t3.number_input("Unidades/Caja", 0)
            else: # Formas
                t1, t2, t3 = st.columns(3)
                desde = t1.text_input("Numeración Desde")
                hasta = t2.text_input("Numeración Hasta")
                copias = t3.selectbox("Copias", ["1", "2", "3", "4"])

            tintas, espec = 0, "N/A"
            if es_impreso:
                i1, i2 = st.columns(2)
                tintas = i1.number_input("Número de Tintas", 0)
                espec = i2.text_input("Colores Específicos")

            obs = st.text_area("Observaciones")
            
            if st.form_submit_button("🚀 REGISTRAR ORDEN"):
                pArea = "IMPRESIÓN" if es_impreso else ("CORTE" if pref == "RB" else "COLECTORAS")
                final_url = st.session_state.get('url_temp', None)
                
                data = {
                    "op": f"{pref}-{op_num}".upper(), "nombre_cliente": cliente, "trabajo": trabajo,
                    "vendedor": vendedor, "tipo_acabado": pref, "material": material, "ancho_medida": medida,
                    "unidades_solicitadas": int(cantidad), "cant_tintas": int(tintas), "especificacion_tintas": espec,
                    "proxima_area": pArea, "observaciones": obs, "estado": "Pendiente", "url_arte": final_url,
                    "core": core_val, "unidades_bolsa": int(bolsa), "unidades_caja": int(caja),
                    "num_desde": desde, "num_hasta": hasta, "copias": copias
                }
                supabase.table("ordenes_planeadas").insert(data).execute()
                st.success("Orden Registrada con Éxito")
                if 'url_temp' in st.session_state: del st.session_state['url_temp']

# 4. IMPRESIÓN (OPERATIVO)
elif menu == "🖨️ Impresión":
    st.title("🖨️ Operaciones de Impresión")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", "IMPRESIÓN").execute().data}
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS["IMPRESIÓN"]):
        lbl = f"🟢 {m}" if m in act else f"⚪ {m}"
        if cols[i%4].button(lbl, key=m): st.session_state.m_sel = m

    if "m_sel" in st.session_state:
        ms = st.session_state.m_sel
        if ms not in act:
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", "IMPRESIÓN").execute().data
            if ops:
                sel = st.selectbox("Elegir OP:", [o['op'] for o in ops])
                if st.button("▶️ INICIAR"):
                    d = next(o for o in ops if o['op'] == sel)
                    supabase.table("trabajos_activos").insert({"maquina": ms, "area": "IMPRESIÓN", "op": d['op'], "trabajo": d['trabajo'], "hora_inicio": datetime.now().strftime("%H:%M"), "tipo_acabado": d['tipo_acabado']}).execute()
                    st.rerun()
        else:
            t = act[ms]
            st.subheader(f"MÁQUINA {ms} | {t['op']}")
            c1, c2 = st.columns(2)
            if c1.button("🚨 PARADA"):
                supabase.table("trabajos_activos").update({"estado_maquina": "PARADA"}).eq("maquina", ms).execute()
                st.rerun()
            if c2.button("🏁 REPORTAR / FINALIZAR"): modal_reporte_impresion(t, ms)

# 5. ÁREAS SIGUIENTES
elif menu in ["✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    a_nom = menu.split(" ")[1].upper()
    st.title(a_nom)
    act_a = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", a_nom).execute().data}
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS[a_nom]):
        lbl = f"🔴 {m}" if m in act_a else f"⚪ {m}"
        if cols[i%4].button(lbl, key=m):
            if m in act_a:
                sig = "ENCUADERNACIÓN" if a_nom in ["CORTE", "COLECTORAS"] else "DESPACHO"
                supabase.table("ordenes_planeadas").update({"proxima_area": sig}).eq("op", act_a[m]['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", m).execute()
                st.rerun()
            else:
                ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", a_nom).execute().data
                if ops:
                    sel = st.selectbox("OP:", [o['op'] for o in ops], key=f"sel_{m}")
                    if st.button(f"Iniciar en {m}"):
                        d = next(o for o in ops if o['op'] == sel)
                        supabase.table("trabajos_activos").insert({"maquina": m, "area": a_nom, "op": d['op'], "trabajo": d['trabajo']}).execute()
                        st.rerun()
