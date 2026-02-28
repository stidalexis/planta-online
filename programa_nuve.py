import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import io
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V10.3")

# Inicializar estados para evitar bloqueos
if 'tipo_sel' not in st.session_state: st.session_state.tipo_sel = None
if 'url_temp' not in st.session_state: st.session_state.url_temp = None

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 50px !important; border-radius: 10px; font-weight: bold; width: 100%; }
    .card-produccion { background-color: #C8E6C9; border-left: 10px solid #2E7D32; padding: 15px; border-radius: 8px; margin-bottom:10px; color: #1B5E20;}
    .card-vacia { background-color: #F5F5F5; border-left: 10px solid #9E9E9E; padding: 15px; border-radius: 8px; margin-bottom:10px; color: #757575;}
    .title-area { background-color: #1565C0; color: white; padding: 10px; border-radius: 5px; text-align: center; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("MENÚ PRINCIPAL", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Operaciones"])

# 1. MONITOR
if menu == "🖥️ Monitor":
    st.title("🏭 Monitor de Planta en Tiempo Real")
    try:
        act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
        for area, maquinas in MAQUINAS.items():
            st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
            cols = st.columns(4)
            for idx, m in enumerate(maquinas):
                with cols[idx % 4]:
                    if m in act:
                        d = act[m]
                        st.markdown(f"<div class='card-produccion'><b>{m}</b><br>{d['op']}<br><small>{d['trabajo']}</small></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='card-vacia'><b>{m}</b><br><small>DISPONIBLE</small></div>", unsafe_allow_html=True)
    except: st.error("Error al conectar con el monitor.")
    time.sleep(30); st.rerun()

# 2. SEGUIMIENTO
elif menu == "🔍 Seguimiento":
    st.title("🔍 Historial y Seguimiento")
    data = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if data:
        df = pd.DataFrame(data)
        st.download_button("📥 Descargar Todo (Excel)", pd.DataFrame(data).to_csv(index=False), "reporte.csv", "text/csv")
        st.dataframe(df[['op', 'nombre_cliente', 'trabajo', 'proxima_area', 'estado']], use_container_width=True)
    else: st.info("No hay órdenes.")

# 3. PLANIFICACIÓN (BOTONES + SOLUCIÓN A BLOQUEO)
elif menu == "📅 Planificación":
    st.title("📅 Nueva Orden de Producción")
    
    c_b1, c_b2, c_b3, c_b4 = st.columns(4)
    if c_b1.button("RI (Rollo Impreso)"): st.session_state.tipo_sel = "RI"
    if c_b2.button("RB (Rollo Blanco)"): st.session_state.tipo_sel = "RB"
    if c_b3.button("FRI (Forma Impresa)"): st.session_state.tipo_sel = "FRI"
    if c_b4.button("FRB (Forma Blanca)"): st.session_state.tipo_sel = "FRB"

    if st.session_state.tipo_sel:
        pref = st.session_state.tipo_sel
        st.subheader(f"Configurando: {pref}")
        
        # Subida de archivo mejorada (Sin bloqueo)
        if "I" in pref:
            archivo = st.file_uploader("🖼️ Arte (Opcional)", type=["pdf","jpg","png"])
            if archivo and not st.session_state.url_temp:
                if st.button("Subir Arte"):
                    with st.spinner("Subiendo..."):
                        path = f"artes/{int(time.time())}_{archivo.name}"
                        supabase.storage.from_("artes").upload(path, archivo.getvalue())
                        st.session_state.url_temp = supabase.storage.from_("artes").get_public_url(path)
                        st.success("✅ Arte cargado")

        with st.form("form_registro", clear_on_submit=True):
            col1, col2 = st.columns(2)
            op_num = col1.text_input("Número de OP")
            cliente = col2.text_input("Cliente")
            trabajo = st.text_input("Nombre del Trabajo")
            
            # Campos técnicos dinámicos
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
                copias = t3.selectbox("Copias", ["1","2","3","4"])

            if st.form_submit_button("🚀 GUARDAR ORDEN"):
                area_ini = "IMPRESIÓN" if "I" in pref else ("CORTE" if pref == "RB" else "COLECTORAS")
                
                payload = {
                    "op": f"{pref}-{op_num}".upper(),
                    "nombre_cliente": str(cliente),
                    "trabajo": str(trabajo),
                    "tipo_acabado": pref,
                    "proxima_area": area_ini,
                    "core": str(core),
                    "unidades_bolsa": int(bolsa),
                    "unidades_caja": int(caja),
                    "num_desde": str(desde),
                    "num_hasta": str(hasta),
                    "copias": str(copias),
                    "url_arte": st.session_state.url_temp
                }
                
                try:
                    supabase.table("ordenes_planeadas").insert(payload).execute()
                    st.success("✅ Orden registrada con éxito")
                    st.session_state.url_temp = None # Limpiar para la próxima
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error de base de datos: {e}")

# 4. OPERACIONES (RESUMIDAS PARA ROBUSTEZ)
elif menu == "🖨️ Operaciones":
    area = st.selectbox("Seleccione su Área", ["IMPRESIÓN", "CORTE", "COLECTORAS", "ENCUADERNACIÓN"])
    st.title(f"Panel: {area}")
    
    # Listar máquinas
    m_cols = st.columns(4)
    for i, m in enumerate(MAQUINAS.get(area, [])):
        if m_cols[i%4].button(m):
            st.session_state.m_act = m

    if 'm_act' in st.session_state:
        ms = st.session_state.m_act
        st.info(f"Máquina seleccionada: {ms}")
        ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area).execute().data
        if ops:
            op_sel = st.selectbox("OP disponible:", [o['op'] for o in ops])
            if st.button(f"Iniciar {ms}"):
                d = next(o for o in ops if o['op'] == op_sel)
                supabase.table("trabajos_activos").insert({"maquina": ms, "area": area, "op": d['op'], "trabajo": d['trabajo']}).execute()
                st.rerun()
        
        if st.button("Finalizar Trabajo"):
            supabase.table("trabajos_activos").delete().eq("maquina", ms).execute()
            st.success("Trabajo terminado")
            st.rerun()
