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

# --- ESTILOS VISUALES (MANTENIDOS SEGÚN TU SOLICITUD) ---
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
# MODALES DE IMPRESIÓN (PERSONALIZADOS)
# ==========================================

@st.dialog("🚨 PARADA DE EMERGENCIA", width="medium")
def modal_parada_emergencia(t, m_s):
    st.error(f"Máquina: {m_s} | OP: {t['op']}")
    with st.form("form_parada"):
        motivo = st.selectbox("Motivo:", ["FALLA MECÁNICA", "FALLA ELÉCTRICA", "FALTA DE MATERIAL", "AJUSTE", "LIMPIEZA", "OTRO"])
        obs = st.text_area("Descripción")
        if st.form_submit_button("REGISTRAR PARADA"):
            supabase.table("paradas_maquina").insert({
                "op": t['op'], "maquina": m_s, "area": "IMPRESIÓN", "motivo": motivo, "observaciones": obs, "hora": datetime.now().strftime("%H:%M")
            }).execute()
            st.rerun()

@st.dialog("CIERRE DE TRABAJO - IMPRESIÓN", width="large")
def modal_finalizar_impresion(t, m_s):
    st.subheader(f"Reporte de Producción: {t['op']}")
    with st.form("cierre_imp"):
        c1, c2, c3 = st.columns(3)
        metros = c1.number_input("Metros Impresos", min_value=0)
        marca = c2.text_input("Marca de Papel")
        bobinas = c3.number_input("Cant. Bobinas", min_value=0)
        
        c4, c5, c6 = st.columns(3)
        n_img = c4.number_input("N° Imágenes", min_value=0)
        gramaje = c5.text_input("Gramaje")
        ancho = c6.text_input("Ancho de Bobina")
        
        c7, c8, c9 = st.columns(3)
        tinta = c7.text_input("Tinta Gastada (Aprox)")
        planchas = c8.number_input("Planchas Gastadas", min_value=0)
        kilos_d = c9.number_input("Kilos Desperdicio", min_value=0.0)
        
        motivo_d = st.selectbox("Motivo Desperdicio", ["N/A", "MONTAJE", "REVENTÓN", "MÁQUINA", "OPERARIO"])
        operario = st.text_input("Nombre Operario")
        obs = st.text_area("Observaciones")

        if st.form_submit_button("🏁 FINALIZAR Y GUARDAR"):
            if operario:
                h_inicio = datetime.strptime(t['hora_inicio'], "%H:%M")
                duracion = str(datetime.now() - h_inicio)
                
                # Guardar en Historial Impresión
                supabase.table("impresion").insert({
                    "op": t['op'], "maquina": m_s, "trabajo": t['trabajo'], "h_inicio": t['hora_inicio'], 
                    "h_fin": datetime.now().strftime("%H:%M"), "duracion": duracion, "metros": metros,
                    "marca": marca, "bobinas": bobinas, "imagenes": n_img, "gramaje": gramaje,
                    "ancho": ancho, "tinta": tinta, "planchas": planchas, "kilos_desp": kilos_d,
                    "motivo_desp": motivo_d, "operario": operario, "observaciones": obs
                }).execute()
                
                # Mover OP
                sig = "CORTE" if t.get('tipo_acabado') == "RI" else "COLECTORAS"
                supabase.table("ordenes_planeadas").update({"proxima_area": sig, "estado": "Pendiente"}).eq("op", t['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", m_s).execute()
                st.rerun()

# ==========================================
# NAVEGACIÓN
# ==========================================
menu = st.sidebar.radio("SISTEMA NUVE V7.5", ["🖥️ Monitor General (TV)", "🔍 Seguimiento de Pedidos", "📅 Planificación (Ingreso OP)", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación", "📊 Historial KPI"])

# 1. MONITOR GENERAL (TV) - NO TOCAR
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

# 2. SEGUIMIENTO DE PEDIDOS - NO TOCAR
elif menu == "🔍 Seguimiento de Pedidos":
    st.title("🔍 Seguimiento de Pedidos")
    try:
        ops = supabase.table("ordenes_planeadas").select("*").neq("estado", "Finalizado").execute().data
        if ops: st.dataframe(pd.DataFrame(ops)[["op", "nombre_cliente", "trabajo", "proxima_area", "estado"]], use_container_width=True)
    except: st.info("Sin órdenes.")

# 3. PLANIFICACIÓN - NO TOCAR (CORREGIDO ERROR DE ENVÍO)
elif menu == "📅 Planificación (Ingreso OP)":
    st.title("📅 Registro de Nueva OP")
    tipo_op_sel = st.selectbox("TIPO DE PRODUCTO:", ["-- Seleccione --", "RI (Rollo Impreso)", "RB (Rollo Blanco)", "FRI (Forma Impresa)", "FRB (Forma Blanca)"])
    if tipo_op_sel != "-- Seleccione --":
        pref = tipo_op_sel.split(" ")[0]
        es_forma = pref in ["FRI", "FRB"]; es_impreso = pref in ["RI", "FRI"]
        with st.form("form_op"):
            st.markdown(f"<div class='title-area'>FORMULARIO: {tipo_op_sel}</div>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3); op_num = c1.text_input("NÚMERO DE OP"); vendedor = c2.text_input("VENDEDOR"); cliente = c3.text_input("CLIENTE"); trabajo = st.text_input("TRABAJO")
            f1, f2, f3 = st.columns(3); material = f1.text_input("PAPEL"); medida = f2.text_input("MEDIDA"); cantidad = f3.number_input("CANTIDAD", min_value=0)
            
            pld = {"core": "N/A", "unidades_bolsa": 0, "unidades_caja": 0, "num_desde": "N/A", "num_hasta": "N/A", "copias": "N/A"}
            if not es_forma:
                r1, r2, r3 = st.columns(3); pld["core"] = r1.selectbox("CORE", ["13MM", "19MM", "1 PULG", "3 PULG"]); pld["unidades_bolsa"] = r2.number_input("U. BOLSA", 0); pld["unidades_caja"] = r3.number_input("U. CAJA", 0)
                pArea = "IMPRESIÓN" if pref == "RI" else "CORTE"
            else:
                n1, n2, n3 = st.columns(3); pld["num_desde"], pld["num_hasta"] = n1.text_input("DESDE"), n2.text_input("HASTA"); pld["copias"] = n3.selectbox("COPIAS", ["1", "2", "3", "4"])
                pArea = "IMPRESIÓN" if pref == "FRI" else "COLECTORAS"
            
            t_n, t_c = (0, "N/A")
            if es_impreso:
                i1, i2 = st.columns(2); t_n = i1.number_input("TINTAS", 0); t_c = i2.text_input("COLORES")
            
            obs = st.text_area("OBSERVACIONES")
            if st.form_submit_button("🚀 REGISTRAR"):
                if op_num and trabajo:
                    # NOTA: Solo enviamos columnas que existen en la tabla base
                    data = {"op": f"{pref}-{op_num}".upper(), "nombre_cliente": cliente, "trabajo": trabajo, "vendedor": vendedor, "tipo_acabado": pref, "material": material, "ancho_medida": medida, "unidades_solicitadas": cantidad, "cant_tintas": t_n, "especificacion_tintas": t_c, "proxima_area": pArea, "observaciones": obs, "estado": "Pendiente", **pld}
                    supabase.table("ordenes_planeadas").insert(data).execute()
                    st.success("OP Registrada"); st.balloons()

# 4. IMPRESIÓN (PERSONALIZADO)
elif menu == "🖨️ Impresión":
    st.title("🖨️ Módulo de Impresión")
    try: activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", "IMPRESIÓN").execute().data}
    except: activos = {}
    
    m_cols = st.columns(4)
    for i, m in enumerate(MAQUINAS["IMPRESIÓN"]):
        if m_cols[i%4].button(f"{'🔴' if m in activos else '⚪'} {m}", key=f"btn_{m}"): st.session_state.m_sel = m

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS["IMPRESIÓN"]:
        ms = st.session_state.m_sel
        if ms not in activos:
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", "IMPRESIÓN").eq("estado", "Pendiente").execute().data
            if ops:
                sel = st.selectbox("Seleccione OP:", ["--"] + [f"{o['op']} | {o['trabajo']}" for o in ops])
                if st.button("▶️ INICIAR"):
                    d = next(o for o in ops if o['op'] == sel.split(" | ")[0])
                    supabase.table("trabajos_activos").insert({"maquina": ms, "area": "IMPRESIÓN", "op": d['op'], "trabajo": d['trabajo'], "hora_inicio": datetime.now().strftime("%H:%M"), "tipo_acabado": d['tipo_acabado']}).execute()
                    supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d['op']).execute()
                    st.rerun()
        else:
            t = activos[ms]
            st.success(f"TRABAJANDO: {t['op']}")
            c1, c2, c3 = st.columns(3)
            if c1.button("🚨 PARADA"): modal_parada_emergencia(t, ms)
            if c2.button("🌙 CIERRE TURNO"): 
                supabase.table("trabajos_activos").delete().eq("maquina", ms).execute() # Pausa: se quita de activo pero queda Pendiente en OP
                st.rerun()
            if c3.button("🏁 FINALIZAR"): modal_finalizar_impresion(t, ms)

elif menu in ["✂️ Corte", "📥 Colectoras", "📕 Encuadernación", "📊 Historial KPI"]:
    st.info("Módulos en espera de configuración de parámetros.")
