import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import io
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V10.4", page_icon="🏭")

# Inicialización de estados críticos
if 'tipo_sel' not in st.session_state: st.session_state.tipo_sel = None
if 'url_temp' not in st.session_state: st.session_state.url_temp = None

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES ORIGINALES ---
st.markdown("""
    <style>
    .stButton > button { height: 55px !important; border-radius: 12px; font-weight: bold; width: 100%; transition: 0.3s; }
    .stButton > button:hover { transform: scale(1.02); border: 2px solid #1565C0; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 15px; border-radius: 12px; text-align: center; color: #1B5E20; box-shadow: 0px 4px 10px rgba(0,230,118,0.3); margin-bottom:10px;}
    .card-parada { background-color: #FF5252; border: 2px solid #D32F2F; padding: 15px; border-radius: 12px; text-align: center; color: white; box-shadow: 0px 4px 10px rgba(255,82,82,0.3); margin-bottom:10px;}
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px; text-align: center; color: #9E9E9E; margin-bottom:10px;}
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin: 20px 0 10px 0; }
    </style>
    """, unsafe_allow_html=True)

MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# ==========================================
# MODALES (LOGICA COMPLETA)
# ==========================================

@st.dialog("Detalles y Arte de la OP", width="large")
def mostrar_detalle_op(row):
    st.markdown(f"### 📄 Orden: {row['op']}")
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**INFORMACIÓN**")
        st.write(f"👤 **Cliente:** {row.get('nombre_cliente')}")
        st.write(f"🛠️ **Trabajo:** {row.get('trabajo')}")
        st.write(f"💼 **Vendedor:** {row.get('vendedor')}")
    with c2:
        st.markdown("**ESPECIFICACIONES**")
        st.write(f"📄 **Material:** {row.get('material')}")
        st.write(f"📦 **Cantidad:** {row.get('unidades_solicitadas')}")
        st.write(f"🎨 **Tintas:** {row.get('cant_tintas')} ({row.get('especificacion_tintas')})")
    with c3:
        st.markdown("**DATOS TÉCNICOS**")
        st.write(f"⚙️ **Core:** {row.get('core')}")
        st.write(f"🔢 **Numeración:** {row.get('num_desde')} - {row.get('num_hasta')}")
        st.write(f"📑 **Copias:** {row.get('copias')}")
    
    if row.get('url_arte'):
        st.link_button("📂 ABRIR ARTE / PDF", row['url_arte'], use_container_width=True)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        pd.DataFrame([row]).to_excel(writer, index=False)
    st.download_button("📥 DESCARGAR EXCEL", output.getvalue(), f"OP_{row['op']}.xlsx", use_container_width=True)

@st.dialog("REPORTE TÉCNICO DE IMPRESIÓN", width="large")
def modal_reporte_impresion(t, m_s, tipo="FINAL"):
    st.subheader(f"Reporte de Entrega {tipo}: {t['op']}")
    with st.form("f_rep"):
        c1, c2, c3 = st.columns(3)
        metros = c1.number_input("Metros Impresos", 0)
        marca = c2.text_input("Marca de Papel")
        bobinas = c3.number_input("Bobinas", 0)
        c4, c5, c6 = st.columns(3)
        n_img = c4.number_input("Imágenes", 0)
        gramaje = c5.text_input("Gramaje")
        ancho = c6.text_input("Ancho Bobina")
        c7, c8, c9 = st.columns(3)
        tinta = c7.text_input("Tinta Gastada")
        planchas = c8.number_input("Planchas", 0)
        kilos_d = c9.number_input("Kilos Desperdicio", 0.0)
        
        m_desp = st.selectbox("Motivo Desp.", ["N/A", "MONTAJE", "REVENTÓN", "MÁQUINA", "OPERARIO"])
        operario = st.text_input("Nombre Operario")
        obs = st.text_area("Observaciones")

        if st.form_submit_button("💾 GUARDAR REPORTE"):
            if operario:
                dur = "N/A"
                try: 
                    h_ini = t.get('hora_inicio', datetime.now().strftime("%H:%M"))
                    dur = str(datetime.now() - datetime.strptime(h_ini, "%H:%M"))
                except: pass

                data = {
                    "op": str(t['op']), "maquina": str(m_s), "trabajo": str(t['trabajo']),
                    "h_inicio": str(t.get('hora_inicio')), "h_fin": datetime.now().strftime("%H:%M"),
                    "duracion": dur, "metros": int(metros), "marca": str(marca), "bobinas": int(bobinas),
                    "imagenes": int(n_img), "gramaje": str(gramaje), "ancho": str(ancho),
                    "tinta": str(tinta), "planchas": int(planchas), "kilos_desp": float(kilos_d),
                    "motivo_desp": str(m_desp), "operario": str(operario), "observaciones": str(obs), "tipo_entrega": tipo
                }
                supabase.table("impresion").insert(data).execute()
                if tipo == "FINAL":
                    sig = "CORTE" if t.get('tipo_acabado') == "RI" else "COLECTORAS"
                    supabase.table("ordenes_planeadas").update({"proxima_area": sig, "estado": "Terminado"}).eq("op", t['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", m_s).execute()
                st.rerun()

# ==========================================
# NAVEGACIÓN
# ==========================================
menu = st.sidebar.radio("SISTEMA NUVE V10.4", ["🖥️ Monitor TV", "🔍 Seguimiento", "📅 Planificación", "🖨️ Operaciones"])

# 1. MONITOR GENERAL
if menu == "🖥️ Monitor TV":
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
                    clase = "card-produccion" if est == 'PRODUCIENDO' else "card-parada"
                    st.markdown(f"<div class='{clase}'><b>{m}</b><br><small>{est}</small><hr><b>{d['op']}</b><br><small>{d['trabajo']}</small></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'><b>{m}</b><br><small>LIBRE</small></div>", unsafe_allow_html=True)
    time.sleep(15); st.rerun()

# 2. SEGUIMIENTO (FULL EXCEL)
elif menu == "🔍 Seguimiento":
    st.title("🔍 Seguimiento y Auditoría")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if res:
        df = pd.DataFrame(res)
        c1, c2 = st.columns([3,1])
        with c2:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 DESCARGAR TODO EXCEL", csv, "Reporte_General.csv", "text/csv", use_container_width=True)
        
        st.divider()
        h1, h2, h3, h4 = st.columns([1,2,1,1])
        h1.write("**OP**"); h2.write("**TRABAJO**"); h3.write("**UBICACIÓN**"); h4.write("**ACCIÓN**")
        for _, f in df.iterrows():
            r1, r2, r3, r4 = st.columns([1,2,1,1])
            r1.write(f['op']); r2.write(f['trabajo']); r3.warning(f['proxima_area'])
            if r4.button("🔎 Detalles", key=f['op']): mostrar_detalle_op(f)

# 3. PLANIFICACIÓN (FORMULARIO ORIGINAL COMPLETO)
elif menu == "📅 Planificación":
    st.title("📅 Ingreso de Órdenes de Producción")
    
    st.markdown("### Seleccione Tipo de Producto:")
    colb1, colb2, colb3, colb4 = st.columns(4)
    if colb1.button("RI (Rollo Impreso)"): st.session_state.tipo_sel = "RI"
    if colb2.button("RB (Rollo Blanco)"): st.session_state.tipo_sel = "RB"
    if colb3.button("FRI (Forma Impresa)"): st.session_state.tipo_sel = "FRI"
    if colb4.button("FRB (Forma Blanca)"): st.session_state.tipo_sel = "FRB"

    if st.session_state.tipo_sel:
        pref = st.session_state.tipo_sel
        es_imp = "I" in pref
        st.info(f"Configurando Producto: {pref}")

        # Subida de arte asíncrona (Corregido para evitar bloqueos)
        if es_imp:
            archivo = st.file_uploader("🖼️ Cargar Arte del Trabajo", type=["pdf", "jpg", "png"])
            if archivo and not st.session_state.url_temp:
                if st.button("⬆️ CONFIRMAR SUBIDA DE ARTE"):
                    with st.spinner("Subiendo..."):
                        path = f"artes/{int(time.time())}_{archivo.name}"
                        supabase.storage.from_("artes").upload(path, archivo.getvalue())
                        st.session_state.url_temp = supabase.storage.from_("artes").get_public_url(path)
                        st.success("✅ Arte listo.")

        with st.form("f_alta_full", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            op_num = c1.text_input("Número de OP")
            vendedor = c2.text_input("Vendedor")
            cliente = c3.text_input("Cliente")
            trabajo = st.text_input("Nombre del Trabajo")
            
            f1, f2, f3 = st.columns(3)
            material = f1.text_input("Papel / Material")
            medida = f2.text_input("Medida")
            cantidad = f3.number_input("Cantidad Solicitada", 0)
            
            # Bloque técnico dinámico
            core, bolsa, caja, desde, hasta, copias = "N/A", 0, 0, "N/A", "N/A", "N/A"
            if "R" in pref:
                t1, t2, t3 = st.columns(3)
                core = t1.selectbox("Core", ["13MM", "19MM", "1 PULG", "3 PULG"])
                bolsa = t2.number_input("Unidades/Bolsa", 0)
                caja = t3.number_input("Unidades/Caja", 0)
            else:
                t1, t2, t3 = st.columns(3)
                desde = t1.text_input("Numeración Desde")
                hasta = t2.text_input("Numeración Hasta")
                copias = t3.selectbox("Copias", ["1","2","3","4"])

            tintas, espec = 0, "N/A"
            if es_imp:
                i1, i2 = st.columns(2)
                tintas = i1.number_input("Número de Tintas", 0)
                espec = i2.text_input("Especificación Colores")

            obs = st.text_area("Observaciones")
            
            if st.form_submit_button("🚀 REGISTRAR ORDEN COMPLETA"):
                area_ini = "IMPRESIÓN" if es_imp else ("CORTE" if pref == "RB" else "COLECTORAS")
                
                payload = {
                    "op": f"{pref}-{op_num}".upper(), "nombre_cliente": str(cliente), "trabajo": str(trabajo),
                    "vendedor": str(vendedor), "tipo_acabado": pref, "material": str(material), 
                    "ancho_medida": str(medida), "unidades_solicitadas": int(cantidad), "cant_tintas": int(tintas), 
                    "especificacion_tintas": str(espec), "proxima_area": area_ini, "observaciones": str(obs),
                    "estado": "Pendiente", "url_arte": st.session_state.url_temp,
                    "core": str(core), "unidades_bolsa": int(bolsa), "unidades_caja": int(caja),
                    "num_desde": str(desde), "num_hasta": str(hasta), "copias": str(copias)
                }
                try:
                    supabase.table("ordenes_planeadas").insert(payload).execute()
                    st.success("✅ Orden Registrada.")
                    st.session_state.url_temp = None
                    time.sleep(1); st.rerun()
                except Exception as e:
                    st.error(f"Error técnico: {e}")

# 4. OPERACIONES (IMPRESIÓN Y DEMÁS)
elif menu == "🖨️ Operaciones":
    area_sel = st.selectbox("Seleccione Área de Trabajo", ["IMPRESIÓN", "CORTE", "COLECTORAS", "ENCUADERNACIÓN"])
    st.divider()
    
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_sel).execute().data}
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS.get(area_sel, [])):
        lbl = f"🟢 {m}" if m in act else f"⚪ {m}"
        if cols[i%4].button(lbl, key=m): st.session_state.m_sel = m
    
    if "m_sel" in st.session_state:
        ms = st.session_state.m_sel
        if ms not in act:
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_sel).execute().data
            if ops:
                sel_op = st.selectbox("Seleccionar OP:", [o['op'] for o in ops])
                if st.button(f"Iniciar en {ms}"):
                    d = next(o for o in ops if o['op'] == sel_op)
                    supabase.table("trabajos_activos").insert({"maquina": ms, "area": area_sel, "op": d['op'], "trabajo": d['trabajo'], "hora_inicio": datetime.now().strftime("%H:%M"), "tipo_acabado": d.get('tipo_acabado')}).execute()
                    st.rerun()
            else: st.warning("No hay órdenes pendientes para esta área.")
        else:
            t = act[ms]
            st.subheader(f"MÁQUINA {ms} | {t['op']}")
            if area_sel == "IMPRESIÓN":
                if st.button("🏁 REPORTAR Y FINALIZAR"): modal_reporte_impresion(t, ms)
            else:
                if st.button("🏁 FINALIZAR TRABAJO"):
                    sig = "ENCUADERNACIÓN" if area_sel in ["CORTE", "COLECTORAS"] else "DESPACHO"
                    supabase.table("ordenes_planeadas").update({"proxima_area": sig}).eq("op", t['op']).execute()
                    supabase.table("trabajos_activos").delete().eq("maquina", ms).execute()
                    st.rerun()
