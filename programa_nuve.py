import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import io

# --- CONFIGURACIÓN DE PÁGINA (ESTILO ORIGINAL) ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ORIGINALES ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 15px; border-radius: 12px; text-align: center; color: #1B5E20; box-shadow: 0px 0px 15px rgba(0,230,118,0.5); margin-bottom:10px;}
    .card-parada { background-color: #FF5252; border: 2px solid #D32F2F; padding: 15px; border-radius: 12px; text-align: center; color: white; box-shadow: 0px 0px 15px rgba(255,82,82,0.5); margin-bottom:10px;}
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px; text-align: center; color: #9E9E9E; margin-bottom:10px;}
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE FLUJOS AUTOMÁTICOS ---
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

# --- MENÚ LATERAL (IDENTICO AL ORIGINAL) ---
with st.sidebar:
    st.title("🏭 NUVE V12")
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

# --- 2. SEGUIMIENTO ---
elif menu == "🔍 Seguimiento":
    st.title("Seguimiento de Órdenes")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if res:
        df = pd.DataFrame(res)
        st.dataframe(df[['op', 'nombre_cliente', 'trabajo', 'proxima_area', 'estado']], use_container_width=True)
        
# --- 3. PLANIFICACIÓN (CON FORMULARIO COMPLETO ORIGINAL) ---
elif menu == "📅 Planificación":
    st.title("Registro de Órdenes")
    
    # Botones de selección de tipo (Solicitados)
    col1, col2, col3, col4 = st.columns(4)
    if col1.button("RI (Rollo Impreso)"): st.session_state.p = "RI"
    if col2.button("RB (Rollo Blanco)"): st.session_state.p = "RB"
    if col3.button("FRI (Forma Impresa)"): st.session_state.p = "FRI"
    if col4.button("FRB (Forma Blanca)"): st.session_state.p = "FRB"

    if "p" in st.session_state:
        pref = st.session_state.p
        
        # Cargador de arte (No bloqueante)
        archivo = st.file_uploader("🖼️ Cargar Arte", type=["pdf", "png", "jpg"])
        if archivo:
            if st.button("Subir Arte"):
                with st.spinner("Subiendo..."):
                    path = f"artes/{int(time.time())}_{archivo.name}"
                    supabase.storage.from_("artes").upload(path, archivo.getvalue())
                    st.session_state.u_temp = supabase.storage.from_("artes").get_public_url(path)
                    st.success("✅ Arte listo.")

        with st.form("form_original"):
            st.subheader(f"Especificaciones para: {pref}")
            c1, c2, c3 = st.columns(3)
            op_num = c1.text_input("Número de OP")
            vendedor = c2.text_input("Vendedor")
            cliente = c3.text_input("Cliente")
            trabajo = st.text_input("Nombre del Trabajo")
            
            f1, f2, f3 = st.columns(3)
            material = f1.text_input("Material")
            medida = f2.text_input("Medida")
            cantidad = f3.number_input("Cantidad", 0)
            
            # Bloque técnico dinámico original
            core, bolsa, caja, desde, hasta, copias = "N/A", 0, 0, "N/A", "N/A", "N/A"
            if "R" in pref:
                t1, t2, t3 = st.columns(3)
                core = t1.selectbox("Core", ["13MM", "19MM", "1 PULG", "3 PULG"])
                bolsa = t2.number_input("Bolsa", 0)
                caja = t3.number_input("Caja", 0)
            else:
                t1, t2, t3 = st.columns(3)
                desde = t1.text_input("Desde")
                hasta = t2.text_input("Hasta")
                copias = t3.selectbox("Copias", ["1", "2", "3", "4"])

            tintas = st.number_input("Tintas", 0) if "I" in pref else 0
            obs = st.text_area("Observaciones")
            
            if st.form_submit_button("🚀 REGISTRAR ORDEN"):
                # Asignar área inicial según el flujo solicitado
                area_inicial = RUTAS[pref][0]
                
                data = {
                    "op": f"{pref}-{op_num}".upper(), "nombre_cliente": str(cliente), "trabajo": str(trabajo),
                    "vendedor": str(vendedor), "tipo_acabado": pref, "material": str(material),
                    "ancho_medida": str(medida), "unidades_solicitadas": int(cantidad),
                    "cant_tintas": int(tintas), "proxima_area": area_inicial, "observaciones": str(obs),
                    "url_arte": st.session_state.get('u_temp'), "core": str(core),
                    "unidades_bolsa": int(bolsa), "unidades_caja": int(caja),
                    "num_desde": str(desde), "num_hasta": str(hasta), "copias": str(copias)
                }
                try:
                    supabase.table("ordenes_planeadas").insert(data).execute()
                    st.success("Orden Guardada"); st.session_state.u_temp = None
                except Exception as e: st.error(f"Error: {e}")

# --- LÓGICA DE ÁREAS (IMPRESIÓN, CORTE, ETC) ---
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    a_nombre = menu.split(" ")[1].upper()
    st.title(f"Área de {a_nombre}")
    
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
            st.subheader(f"Control: {m} | {t['op']}")
            with st.form(f"f_{m}"):
                st.write("Datos de Finalización:")
                operario = st.text_input("Operario")
                parcial = st.checkbox("¿Entrega Parcial?")
                
                c1, c2 = st.columns(2)
                if c1.form_submit_button("🏁 FINALIZAR"):
                    if not parcial:
                        # Lógica de avance automático
                        pref_op = t['op'].split("-")[0]
                        ruta = RUTAS[pref_op]
                        nueva_area = ruta[ruta.index(a_nombre) + 1]
                        est = "Terminado" if nueva_area == "FINALIZADO" else "Pendiente"
                        supabase.table("ordenes_planeadas").update({"proxima_area": nueva_area, "estado": est}).eq("op", t['op']).execute()
                    
                    supabase.table("trabajos_activos").delete().eq("maquina", m).execute()
                    st.rerun()
                
                if c2.form_submit_button("🚨 PARADA"):
                    supabase.table("trabajos_activos").update({"estado_maquina": "PARADA", "h_parada": datetime.now().strftime("%H:%M")}).eq("maquina", m).execute()
                    st.rerun()
        else:
            ops_disponibles = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", a_nombre).execute().data
            if ops_disponibles:
                op_elegida = st.selectbox("Seleccione OP:", [o['op'] for o in ops_disponibles])
                if st.button(f"Iniciar {m}"):
                    d = next(o for o in ops_disponibles if o['op'] == op_elegida)
                    supabase.table("trabajos_activos").insert({
                        "maquina": m, "area": a_nombre, "op": d['op'], 
                        "trabajo": d['trabajo'], "hora_inicio": datetime.now().strftime("%H:%M")
                    }).execute()
                    st.rerun()
            else: st.warning("No hay órdenes para esta área.")
