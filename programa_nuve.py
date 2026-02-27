import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import io
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V8.5", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    /* Colores del Monitor */
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
# MODALES DE IMPRESIÓN (NUEVA DINÁMICA)
# ==========================================

@st.dialog("🚨 REGISTRAR PARADA DE EMERGENCIA", width="medium")
def modal_parada_emergencia(t, m_s):
    st.error(f"Deteniendo máquina: {m_s}")
    with st.form("f_parada"):
        motivo = st.selectbox("Motivo de parada:", ["FALLA MECÁNICA", "FALLA ELÉCTRICA", "FALTA MATERIAL", "AJUSTE TINTA", "REVENTÓN PAPEL"])
        obs = st.text_area("Detalles")
        if st.form_submit_button("CONFIRMAR PARADA"):
            supabase.table("trabajos_activos").update({
                "estado_maquina": "PARADA", 
                "h_parada": datetime.now().strftime("%H:%M:%S")
            }).eq("maquina", m_s).execute()
            st.rerun()

@st.dialog("📦 REGISTRAR ENTREGA PARCIAL", width="medium")
def modal_parcial(t, m_s):
    st.info("La OP seguirá abierta en Impresión")
    with st.form("f_parcial"):
        cant = st.number_input("Cantidad enviada a Corte", min_value=1)
        if st.form_submit_button("REGISTRAR PARCIAL"):
            # Aquí podrías enviar un trigger a la tabla de Corte si fuera necesario
            st.success(f"Parcial de {cant} registrado exitosamente.")
            st.rerun()

@st.dialog("🏁 FINALIZACIÓN TOTAL DE IMPRESIÓN", width="large")
def modal_finalizar_total(t, m_s):
    with st.form("f_final_imp"):
        st.subheader("Reporte Técnico Final")
        c1, c2, c3 = st.columns(3)
        metros = c1.number_input("Metros Impresos", min_value=0)
        marca = c2.text_input("Marca de Papel")
        bobinas = c3.number_input("Bobinas", min_value=0)
        
        c4, c5, c6 = st.columns(3)
        n_img = c4.number_input("N° Imágenes", min_value=0)
        gramaje = c5.text_input("Gramaje")
        ancho = c6.text_input("Ancho Bobina")
        
        c7, c8, c9 = st.columns(3)
        tinta = c7.text_input("Tinta Aprox.")
        planchas = c8.number_input("Planchas", min_value=0)
        kilos_d = c9.number_input("Kilos Desp.", min_value=0.0)
        
        motivo_d = st.selectbox("Motivo Desp.", ["N/A", "MONTAJE", "REVENTÓN", "MÁQUINA", "OPERARIO"])
        operario = st.text_input("Nombre Operario")
        obs = st.text_area("Observaciones Finales")

        if st.form_submit_button("💾 GUARDAR KPI Y CERRAR"):
            if operario:
                h_inicio = datetime.strptime(t['hora_inicio'], "%H:%M")
                duracion = str(datetime.now() - h_inicio)
                
                # Guardar Historial
                supabase.table("impresion").insert({
                    "op": t['op'], "maquina": m_s, "trabajo": t['trabajo'], "h_inicio": t['hora_inicio'],
                    "h_fin": datetime.now().strftime("%H:%M"), "duracion": duracion, "metros": metros,
                    "marca": marca, "bobinas": bobinas, "imagenes": n_img, "gramaje": gramaje,
                    "ancho": ancho, "tinta": tinta, "planchas": planchas, "kilos_desp": kilos_d,
                    "motivo_desp": motivo_d, "operario": operario, "observaciones": obs
                }).execute()
                
                # Mover OP a Corte (RI) o Colectoras (FRI)
                sig = "CORTE" if t.get('tipo_acabado') == "RI" else "COLECTORAS"
                supabase.table("ordenes_planeadas").update({"proxima_area": sig, "estado": "Pendiente"}).eq("op", t['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", m_s).execute()
                st.rerun()

# ==========================================
# NAVEGACIÓN Y MENÚ
# ==========================================
menu = st.sidebar.radio("SISTEMA NUVE V8.5", ["🖥️ Monitor General (TV)", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte"])

# 1. MONITOR GENERAL (TV)
if menu == "🖥️ Monitor General (TV)":
    st.title("🏭 Monitor General de Planta")
    try: act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    except: act = {}
    
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>ÁREA: {area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    d = act[m]
                    est = d.get('estado_maquina', 'PRODUCIENDO')
                    clase = "card-produccion" if est == 'PRODUCIENDO' else "card-parada" if est == 'PARADA' else "card-turno"
                    label = "⚡ PRODUCIENDO" if est == 'PRODUCIENDO' else "🚨 PARADA" if est == 'PARADA' else "🌙 TURNO CERRADO"
                    st.markdown(f"<div class='{clase}'><b>{m}</b><br><b>{d['op']}</b><br><small>{label}</small></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'><b>{m}</b><br><small>LIBRE</small></div>", unsafe_allow_html=True)
    time.sleep(15); st.rerun()

# 2. SEGUIMIENTO
elif menu == "🔍 Seguimiento":
    st.title("🔍 Seguimiento de Pedidos")
    ops = supabase.table("ordenes_planeadas").select("*").neq("estado","Finalizado").execute().data
    if ops: st.dataframe(pd.DataFrame(ops)[["op", "nombre_cliente", "trabajo", "proxima_area", "estado"]], use_container_width=True)

# 3. PLANIFICACIÓN
elif menu == "📅 Planificación":
    st.title("📅 Ingreso de Ordenes")
    tipo = st.selectbox("Producto:", ["RI", "RB", "FRI", "FRB"])
    with st.form("f_plan"):
        c1, c2 = st.columns(2)
        op_n = c1.text_input("Número OP")
        trabajo = c2.text_input("Nombre del Trabajo")
        cliente = st.text_input("Cliente")
        cant = st.number_input("Cantidad", min_value=0)
        
        # Determinar área inicial
        if "RI" in tipo: pArea = "IMPRESIÓN"
        elif "RB" in tipo: pArea = "CORTE"
        elif "FRI" in tipo: pArea = "IMPRESIÓN"
        else: pArea = "COLECTORAS"
        
        if st.form_submit_button("REGISTRAR"):
            data = {"op": f"{tipo}-{op_n}".upper(), "trabajo": trabajo, "nombre_cliente": cliente, "unidades_solicitadas": cant, "tipo_acabado": tipo, "proxima_area": pArea, "estado": "Pendiente"}
            supabase.table("ordenes_planeadas").insert(data).execute()
            st.success("OP Registrada")

# 4. MÓDULO IMPRESIÓN (OPERATIVO)
elif menu == "🖨️ Impresión":
    st.title("🖨️ Panel de Impresión")
    act_list = supabase.table("trabajos_activos").select("*").eq("area", "IMPRESIÓN").execute().data
    act = {a['maquina']: a for a in act_list}
    
    m_cols = st.columns(4)
    for i, m in enumerate(MAQUINAS["IMPRESIÓN"]):
        if m_cols[i%4].button(f"{'🔴' if m in act else '⚪'} {m}", key=f"btn_{m}"): st.session_state.m_sel = m

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS["IMPRESIÓN"]:
        ms = st.session_state.m_sel
        if ms not in act:
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", "IMPRESIÓN").eq("estado", "Pendiente").execute().data
            if ops:
                sel = st.selectbox("Seleccione OP:", [o['op'] for o in ops])
                if st.button("▶️ INICIAR"):
                    d = next(o for o in ops if o['op'] == sel)
                    supabase.table("trabajos_activos").insert({"maquina": ms, "area": "IMPRESIÓN", "op": d['op'], "trabajo": d['trabajo'], "hora_inicio": datetime.now().strftime("%H:%M"), "tipo_acabado": d['tipo_acabado'], "estado_maquina": "PRODUCIENDO"}).execute()
                    supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d['op']).execute()
                    st.rerun()
        else:
            t = act[ms]
            est = t.get('estado_maquina', 'PRODUCIENDO')
            st.subheader(f"MÁQUINA: {ms} | OP: {t['op']}")
            
            if est == "PRODUCIENDO":
                st.success("Estado: EN PRODUCCIÓN")
                c1, c2, c3, c4 = st.columns(4)
                if c1.button("🚨 PARADA"): modal_parada_emergencia(t, ms)
                if c2.button("🌙 CERRAR TURNO"):
                    supabase.table("trabajos_activos").update({"estado_maquina": "TURNO_CERRADO"}).eq("maquina", ms).execute()
                    st.rerun()
                if c3.button("📦 PARCIAL"): modal_parcial(t, ms)
                if c4.button("🏁 FINALIZAR TOTAL"): modal_finalizar_total(t, ms)
            
            elif est == "PARADA":
                st.error(f"🚨 MÁQUINA DETENIDA DESDE {t.get('h_parada')}")
                if st.button("▶️ REANUDAR (FIN DE PARADA)"):
                    h_ini = datetime.strptime(t.get('h_parada'), "%H:%M:%S")
                    dur = (datetime.now() - h_ini).seconds // 60
                    supabase.table("paradas_maquina").insert({"op": t['op'], "maquina": ms, "motivo": "Emergencia", "h_inicio": t.get('h_parada'), "h_fin": datetime.now().strftime("%H:%M:%S"), "duracion_min": dur}).execute()
                    supabase.table("trabajos_activos").update({"estado_maquina": "PRODUCIENDO", "h_parada": None}).eq("maquina", ms).execute()
                    st.rerun()
            
            elif est == "TURNO_CERRADO":
                st.warning("🌙 TURNO CERRADO")
                if st.button("☀️ REANUDAR TURNO"):
                    supabase.table("trabajos_activos").update({"estado_maquina": "PRODUCIENDO"}).eq("maquina", ms).execute()
                    st.rerun()

elif menu == "✂️ Corte":
    st.title("✂️ Corte")
    st.info("Módulo de corte pendiente de parámetros técnicos.")
