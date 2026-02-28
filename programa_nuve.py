import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time

# --- CONFIGURACIÓN DE PÁGINA (ESTILO ORIGINAL) ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ORIGINALES (PROHIBIDO CAMBIAR) ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 15px; border-radius: 12px; text-align: center; color: #1B5E20; box-shadow: 0px 0px 15px rgba(0,230,118,0.5); margin-bottom:10px;}
    .card-parada { background-color: #FF5252; border: 2px solid #D32F2F; padding: 15px; border-radius: 12px; text-align: center; color: white; box-shadow: 0px 0px 15px rgba(255,82,82,0.5); margin-bottom:10px;}
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px; text-align: center; color: #9E9E9E; margin-bottom:10px;}
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE RUTAS ---
RUTAS = {
    "RI": ["IMPRESIÓN", "CORTE", "FINALIZADO"],
    "RB": ["CORTE", "FINALIZADO"],
    "FRI": ["IMPRESIÓN", "COLECTORAS", "ENCUADERNACIÓN", "FINALIZADO"],
    "FRB": ["IMPRESIÓN", "COLECTORAS", "ENCUADERNACIÓN", "FINALIZADO"]
}

MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- MENÚ LATERAL ORIGINAL ---
with st.sidebar:
    st.title("🏭 NUVE")
    menu = st.radio("MENÚ", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# --- 1. MONITOR ---
if menu == "🖥️ Monitor":
    st.title("Monitor de Planta")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for i, m in enumerate(lista):
            with cols[i%4]:
                if m in act:
                    clase = "card-produccion" if act[m]['estado_maquina'] == "PRODUCIENDO" else "card-parada"
                    st.markdown(f"<div class='{clase}'><b>{m}</b><br>{act[m]['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'><b>{m}</b><br>LIBRE</div>", unsafe_allow_html=True)
    time.sleep(20); st.rerun()

# --- 2. SEGUIMIENTO (AHORA CON DATOS) ---
elif menu == "🔍 Seguimiento":
    st.title("Historial de Órdenes")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if res:
        df = pd.DataFrame(res)
        # Reordenar columnas para mejor visual
        columnas = ['op', 'nombre_cliente', 'trabajo', 'proxima_area', 'estado', 'url_arte']
        st.dataframe(df[columnas], use_container_width=True)
        
        # Buscador por OP
        op_buscar = st.text_input("Buscar detalle por OP (Ej: RI-123):")
        if op_buscar:
            detalle = df[df['op'] == op_buscar.upper()]
            if not detalle.empty:
                st.write(detalle.iloc[0])
                if detalle.iloc[0]['url_arte']:
                    st.image(detalle.iloc[0]['url_arte'], caption="Arte de la OP", width=400)
    else:
        st.info("No hay órdenes registradas aún.")

# --- 3. PLANIFICACIÓN (FORMULARIOS DIFERENCIADOS COMPLETOS) ---
elif menu == "📅 Planificación":
    st.title("Ingreso de Órdenes")
    
    col1, col2, col3, col4 = st.columns(4)
    if col1.button("RI (Rollo Impreso)"): st.session_state.pref = "RI"
    if col2.button("RB (Rollo Blanco)"): st.session_state.pref = "RB"
    if col3.button("FRI (Forma Impresa)"): st.session_state.pref = "FRI"
    if col4.button("FRB (Forma Blanca)"): st.session_state.pref = "FRB"

    if "pref" in st.session_state:
        pref = st.session_state.pref
        es_impreso = "I" in pref
        es_rollo = "R" in pref

        # Subida de arte independiente
        archivo = st.file_uploader("🖼️ Cargar Arte", type=["pdf", "png", "jpg"])
        url_subida = None
        if archivo:
            if st.button("Subir Archivo de Arte"):
                with st.spinner("Subiendo..."):
                    path = f"artes/{int(time.time())}_{archivo.name}"
                    supabase.storage.from_("artes").upload(path, archivo.getvalue())
                    url_subida = supabase.storage.from_("artes").get_public_url(path)
                    st.session_state.u_temp = url_subida
                    st.success("✅ Arte cargado")

        with st.form("form_registro"):
            st.subheader(f"DATOS ORIGINALES - {pref}")
            c1, c2, c3 = st.columns(3)
            op_num = c1.text_input("Número de OP")
            vendedor = c2.text_input("Vendedor")
            cliente = c3.text_input("Cliente")
            
            trabajo = st.text_input("Nombre del Trabajo")
            
            f1, f2, f3 = st.columns(3)
            material = f1.text_input("Material / Papel")
            medida = f2.text_input("Medida / Ancho")
            cantidad = f3.number_input("Cantidad Solicitada", 0)

            # --- DIFERENCIACIÓN DE FORMULARIOS ---
            core, bolsa, caja, desde, hasta, copias = "N/A", 0, 0, "N/A", "N/A", "N/A"
            
            if es_rollo:
                st.markdown("--- **ESPECIFICACIONES DE ROLLO** ---")
                r1, r2, r3 = st.columns(3)
                core = r1.selectbox("Core", ["13MM", "19MM", "1 PULG", "3 PULG"])
                bolsa = r2.number_input("Unidades por Bolsa", 0)
                caja = r3.number_input("Unidades por Caja", 0)
            else:
                st.markdown("--- **ESPECIFICACIONES DE FORMAS** ---")
                o1, o2, o3 = st.columns(3)
                desde = o1.text_input("Numeración Desde")
                hasta = o2.text_input("Numeración Hasta")
                copias = o3.selectbox("Número de Copias", ["1", "2", "3", "4"])

            tintas, espec_tintas = 0, "N/A"
            if es_impreso:
                st.markdown("--- **DATOS DE IMPRESIÓN** ---")
                i1, i2 = st.columns(2)
                tintas = i1.number_input("Cantidad de Tintas", 0)
                espec_tintas = i2.text_input("Colores / Tintas Especiales")

            obs = st.text_area("Observaciones Adicionales")
            
            if st.form_submit_button("🚀 REGISTRAR ORDEN"):
                area_inicial = RUTAS[pref][0]
                
                data = {
                    "op": f"{pref}-{op_num}".upper(), "nombre_cliente": cliente, "trabajo": trabajo,
                    "vendedor": vendedor, "tipo_acabado": pref, "material": material,
                    "ancho_medida": medida, "unidades_solicitadas": int(cantidad),
                    "cant_tintas": int(tintas), "especificacion_tintas": espec_tintas,
                    "proxima_area": area_inicial, "observaciones": obs,
                    "url_arte": st.session_state.get('u_temp'),
                    "core": core, "unidades_bolsa": int(bolsa), "unidades_caja": int(caja),
                    "num_desde": desde, "num_hasta": hasta, "copias": copias
                }
                try:
                    supabase.table("ordenes_planeadas").insert(data).execute()
                    st.success("✅ Orden registrada exitosamente.")
                    st.session_state.u_temp = None
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

# --- MÓDULOS DE ÁREA (CON PARADA Y ENTREGA PARCIAL) ---
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    a_nombre = menu.split(" ")[1].upper()
    st.title(f"Operaciones: {a_nombre}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", a_nombre).execute().data}
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS[a_nombre]):
        btn_label = f"🔴 {m}" if m in activos else f"⚪ {m}"
        if cols[i%4].button(btn_label, key=m):
            st.session_state.m_sel = m
            st.session_state.a_sel = a_nombre

    if "m_sel" in st.session_state and st.session_state.a_sel == a_nombre:
        m = st.session_state.m_sel
        st.divider()
        if m in activos:
            t = activos[m]
            st.subheader(f"Control: {m} | OP: {t['op']}")
            with st.form(f"f_control_{m}"):
                operario = st.text_input("Operario responsable")
                parcial = st.checkbox("¿Es una Entrega Parcial?")
                
                c1, c2 = st.columns(2)
                if c1.form_submit_button("🏁 FINALIZAR TAREA"):
                    if not parcial:
                        # Avanzar en la ruta automática
                        pref_op = t['op'].split("-")[0]
                        ruta = RUTAS[pref_op]
                        nueva_area = ruta[ruta.index(a_nombre) + 1]
                        est_f = "Terminado" if nueva_area == "FINALIZADO" else "Pendiente"
                        supabase.table("ordenes_planeadas").update({"proxima_area": nueva_area, "estado": est_f}).eq("op", t['op']).execute()
                    
                    supabase.table("trabajos_activos").delete().eq("maquina", m).execute()
                    st.rerun()
                
                if c2.form_submit_button("🚨 PARADA DE EMERGENCIA"):
                    supabase.table("trabajos_activos").update({"estado_maquina": "PARADA", "h_parada": datetime.now().strftime("%H:%M")}).eq("maquina", m).execute()
                    st.rerun()
        else:
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", a_nombre).execute().data
            if ops:
                op_elegida = st.selectbox("Elegir Orden Pendiente:", [o['op'] for o in ops])
                if st.button(f"Iniciar Trabajo en {m}"):
                    d = next(o for o in ops if o['op'] == op_elegida)
                    supabase.table("trabajos_activos").insert({
                        "maquina": m, "area": a_nombre, "op": d['op'], 
                        "trabajo": d['trabajo'], "hora_inicio": datetime.now().strftime("%H:%M")
                    }).execute()
                    st.rerun()
            else:
                st.warning("No hay órdenes pendientes para esta área.")
