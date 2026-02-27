import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import io
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V7.5", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES (MANTENIDOS) ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    .card-activa-brillante { 
        padding: 15px; border-radius: 12px; 
        background-color: #00E676; border: 2px solid #00C853;
        box-shadow: 0px 0px 15px rgba(0, 230, 118, 0.5);
        margin-bottom: 15px; text-align: center; color: #1B5E20;
    }
    .card-vacia-monitor { 
        padding: 15px; border-radius: 12px; 
        background-color: #F5F5F5; border: 1px solid #E0E0E0;
        margin-bottom: 15px; text-align: center; color: #9E9E9E;
    }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .text-maquina { font-size: 1.3rem; font-weight: 800; margin-bottom: 5px; display: block; }
    .text-op { font-size: 1.1rem; font-weight: 700; color: #000; display: block; }
    .text-trabajo { font-size: 0.85rem; font-weight: 500; display: block; line-height: 1.1; }
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
# MODALES DE IMPRESIÓN (KPI Y PARADAS)
# ==========================================

@st.dialog("🚨 REGISTRAR PARADA DE EMERGENCIA", width="medium")
def modal_parada_emergencia(t, m_s):
    st.error(f"Registrando parada para {m_s} (OP: {t['op']})")
    with st.form("form_parada"):
        motivo = st.selectbox("Motivo de la parada:", [
            "FALLA MECÁNICA", "FALLA ELÉCTRICA", "FALTA DE MATERIAL", 
            "REVENTÓN DE PAPEL", "AJUSTE DE TINTAS", "LIMPIEZA DE CILINDROS"
        ])
        obs_p = st.text_area("Detalles de la parada")
        if st.form_submit_button("REGISTRAR PARADA"):
            data_p = {
                "op": t['op'], "maquina": m_s, "area": "IMPRESIÓN",
                "tipo": "PARADA EMERGENCIA", "motivo": motivo, "observaciones": obs_p,
                "hora": datetime.now().strftime("%H:%M:%S")
            }
            supabase.table("paradas_maquina").insert(data_p).execute()
            st.success("Parada registrada en el historial.")
            st.rerun()

@st.dialog("Cierre de Trabajo - IMPRESIÓN", width="large")
def modal_finalizar_impresion(t, m_s):
    st.info(f"Reporte Final: {t['op']} en {m_s}")
    h_inicio = datetime.strptime(t['hora_inicio'], "%H:%M")
    h_fin = datetime.now()
    duracion = h_fin - h_inicio
    
    with st.form("form_final_impresion"):
        c1, c2, c3 = st.columns(3)
        metros = c1.number_input("Metros Impresos", min_value=0)
        marca = c2.text_input("Marca de Papel")
        bobinas = c3.number_input("Cantidad de Bobinas", min_value=0)
        
        c4, c5, c6 = st.columns(3)
        n_imagenes = c4.number_input("N° Imágenes", min_value=0)
        gramaje = c5.text_input("Gramaje")
        ancho = c6.text_input("Ancho de Bobina")
        
        c7, c8, c9 = st.columns(3)
        tinta = c7.text_input("Tinta Gastada (Aprox)")
        planchas = c8.number_input("Planchas Gastadas", min_value=0)
        kilos_desp = c9.number_input("Kilos Desperdicio", min_value=0.0)
        
        motivo_desp = st.selectbox("Motivo Desperdicio", ["N/A", "MONTAJE", "REVENTÓN", "FALLA MÁQUINA", "ERROR OPERARIO"])
        operario = st.text_input("Nombre del Operario")
        obs = st.text_area("Observaciones Finales")
        
        if st.form_submit_button("💾 GUARDAR Y ENVIAR A SIGUIENTE ÁREA"):
            if operario:
                # Determinar siguiente área
                sig = "CORTE" if t['tipo_acabado'] == "RI" else "COLECTORAS"
                
                datos_kpi = {
                    "op": t['op'], "maquina": m_s, "trabajo": t['trabajo'],
                    "h_inicio": t['hora_inicio'], "h_fin": h_fin.strftime("%H:%M"),
                    "duracion_total": str(duracion), "metros_impresos": metros,
                    "marca_papel": marca, "bobinas": bobinas, "n_imagenes": n_imagenes,
                    "gramaje": gramaje, "ancho_bobina": ancho, "tinta_aprox": tinta,
                    "planchas": planchas, "kilos_desperdicio": kilos_desp,
                    "motivo_desperdicio": motivo_desp, "operario": operario, "observaciones": obs
                }
                supabase.table("impresion").insert(datos_kpi).execute()
                supabase.table("ordenes_planeadas").update({"proxima_area": sig, "estado": "Pendiente"}).eq("op", t['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", m_s).execute()
                st.rerun()

# ==========================================
# MENÚ Y NAVEGACIÓN
# ==========================================
menu = st.sidebar.radio("SISTEMA NUVE V7.5", ["🖥️ Monitor General (TV)", "🔍 Seguimiento de Pedidos", "📅 Planificación (Ingreso OP)", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación", "📊 Historial KPI"])

# --- MONITOR GENERAL (TV) - SIN CAMBIOS ---
if menu == "🖥️ Monitor General (TV)":
    st.title("🏭 Tablero de Control de Planta")
    try: act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    except: act = {}
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>ÁREA: {area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    d = act[m]
                    st.markdown(f"<div class='card-activa-brillante'><span class='text-maquina'>{m}</span><span class='text-op'>{d['op']}</span><span class='text-trabajo'>{d['trabajo']}</span><hr style='margin: 8px 0;'><small>Inicio: {d.get('hora_inicio')}</small></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia-monitor'><span class='text-maquina'>{m}</span><br><small>DISPONIBLE</small></div>", unsafe_allow_html=True)
    time.sleep(30); st.rerun()

# --- SEGUIMIENTO DE PEDIDOS - SIN CAMBIOS ---
elif menu == "🔍 Seguimiento de Pedidos":
    st.title("🔍 Seguimiento de Pedidos")
    try:
        ops = supabase.table("ordenes_planeadas").select("*").neq("estado", "Finalizado").execute().data
        if ops:
            df = pd.DataFrame(ops)
            st.dataframe(df[["op", "nombre_cliente", "trabajo", "proxima_area", "estado"]], use_container_width=True)
    except: st.info("No hay órdenes.")

# --- PLANIFICACIÓN - SIN CAMBIOS ---
elif menu == "📅 Planificación (Ingreso OP)":
    st.title("📅 Registro de Nueva OP")
    # ... (Aquí va todo tu código de formulario original sin cambios)
    st.info("Formulario de ingreso activo.")

# ==========================================
# 🖨️ MÓDULO DE IMPRESIÓN (PERSONALIZADO)
# ==========================================
elif menu == "🖨️ Impresión":
    st.title("🖨️ Área de Impresión")
    try: activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", "IMPRESIÓN").execute().data}
    except: activos = {}
    
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS["IMPRESIÓN"]):
        if cols[i % 4].button(f"{'🔴' if m in activos else '⚪'} {m}", key=f"imp_{m}"): st.session_state.m_sel = m

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS["IMPRESIÓN"]:
        ms = st.session_state.m_sel
        st.subheader(f"Gestión de Máquina: {ms}")
        
        if ms not in activos:
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", "IMPRESIÓN").eq("estado", "Pendiente").execute().data
            if ops:
                sel = st.selectbox("Seleccione OP:", ["--"] + [f"{o['op']} | {o['trabajo']}" for o in ops])
                if st.button("▶️ INICIAR TRABAJO"):
                    d = next(o for o in ops if o['op'] == sel.split(" | ")[0])
                    supabase.table("trabajos_activos").insert({"maquina": ms, "area": "IMPRESIÓN", "op": d['op'], "trabajo": d['trabajo'], "hora_inicio": datetime.now().strftime("%H:%M"), "tipo_acabado": d['tipo_acabado']}).execute()
                    supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d['op']).execute()
                    st.rerun()
        else:
            t = activos[ms]
            st.success(f"PROCESANDO: {t['op']} - {t['trabajo']}")
            
            # --- BOTONES DE CONTROL DE IMPRESIÓN ---
            c1, c2, c3 = st.columns(3)
            if c1.button("🚨 PARADA EMERGENCIA"):
                modal_parada_emergencia(t, ms)
            
            if c2.button("🌙 CIERRE DE TURNO"):
                # Aquí podrías agregar lógica para pausar y guardar estado
                st.warning("Función de Cierre de Turno: La máquina quedará detenida.")
                supabase.table("trabajos_activos").update({"estado_turno": "Pausado"}).eq("maquina", ms).execute()

            if c3.button("🏁 FINALIZAR TRABAJO"):
                modal_finalizar_impresion(t, ms)

# --- DEMÁS ÁREAS (PENDIENTES DE PERSONALIZAR) ---
elif menu in ["✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    st.title(f"Módulo {menu}")
    st.info("Esta área usa el cierre genérico hasta que definamos sus parámetros.")
