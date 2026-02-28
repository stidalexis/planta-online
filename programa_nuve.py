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

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    .card-proceso { 
        padding: 15px; border-radius: 12px; background-color: #E8F5E9; 
        border-left: 8px solid #2E7D32; margin-bottom: 15px; 
    }
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
    .card-libre { padding: 15px; border-radius: 12px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; margin-bottom: 15px; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .text-maquina { font-size: 1.3rem; font-weight: 800; margin-bottom: 5px; display: block; }
    .text-op { font-size: 1.1rem; font-weight: 700; color: #000; display: block; }
    .text-trabajo { font-size: 0.85rem; font-weight: 500; display: block; line-height: 1.1; }
    .detalles-op { font-size: 0.85rem; color: #1B5E20; line-height: 1.2; }
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

# --- VENTANA EMERGENTE (DETALLE OP) ---
@st.dialog("Detalles de la Orden de Producción", width="large")
def mostrar_detalle_op(row):
    st.markdown(f"### 📄 Orden: {row['op']}")
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**CLIENTE Y TRABAJO**")
        st.write(f"👤 **Cliente:** {row.get('nombre_cliente')}")
        st.write(f"💼 **Vendedor:** {row.get('vendedor')}")
        st.write(f"🛠️ **Trabajo:** {row.get('trabajo')}")
    with col2:
        st.markdown("**ESPECIFICACIONES**")
        st.write(f"📄 **Material:** {row.get('material')}")
        st.write(f"📏 **Medida:** {row.get('ancho_medida')}")
        st.write(f"📦 **Cantidad:** {row.get('unidades_solicitadas')}")
    with col3:
        st.markdown("**PROCESO**")
        st.write(f"🎨 **Tintas:** {row.get('cant_tintas')}")
        st.write(f"📍 **Área Sig:** {row.get('proxima_area')}")
        core_val = row.get('core') if row.get('core') != 'N/A' else row.get('copias')
        st.write(f"Core/Copias: {core_val}")

    st.info(f"📝 **Observaciones:** {row.get('observaciones')}")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        pd.DataFrame([row]).to_excel(writer, index=False)
    st.download_button("📥 DESCARGAR EXCEL", output.getvalue(), f"OP_{row['op']}.xlsx", use_container_width=True)

# --- MODAL DE CIERRE (A LA ESPERA DE TUS PARÁMETROS) ---
@st.dialog("Finalizar Trabajo", width="medium")
def modal_finalizar_trabajo(t, m_s, area):
    st.warning(f"Cerrando OP: {t['op']} en {m_s}")
    with st.form("form_kpi"):
        st.write("Datos de Producción")
        # Aquí es donde incluiremos tus parámetros personalizados
        operario = st.text_input("Nombre del Operario")
        if st.form_submit_button("✅ GUARDAR Y FINALIZAR"):
            if operario:
                sig = "FINALIZADO"
                if t['tipo_acabado'] == "RI" and area == "IMPRESIÓN": sig = "CORTE"
                elif t['tipo_acabado'] == "FRI" and area == "IMPRESIÓN": sig = "COLECTORAS"
                elif t['tipo_acabado'] in ["FRI","FRB"] and area == "COLECTORAS": sig = "ENCUADERNACIÓN"

                hist = {"op":t['op'], "maquina":m_s, "trabajo":t['trabajo'], "h_inicio":t['hora_inicio'], "h_fin":datetime.now().strftime("%H:%M"), "operario": operario}
                supabase.table(normalizar(area)).insert(hist).execute()
                supabase.table("ordenes_planeadas").update({"proxima_area":sig, "estado":"Pendiente" if sig != "FINALIZADO" else "Finalizado"}).eq("op", t['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", m_s).execute()
                st.rerun()

# --- BARRA LATERAL ---
menu = st.sidebar.radio("SISTEMA NUVE V7.5", ["🖥️ Monitor General (TV)", "🔍 Seguimiento de Pedidos", "📅 Planificación (Ingreso OP)", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación", "📊 Historial KPI"])

# 1. MONITOR GENERAL (TV) - SIN TOCAR
if menu == "🖥️ Monitor General (TV)":
    st.title("🏭 Tablero de Control de Planta - Vista Total")
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
                    st.markdown(f"<div class='card-activa-brillante'><span class='text-maquina'>{m}</span><span class='text-op'>{d['op']}</span><span class='text-trabajo'>{d['trabajo']}</span><hr style='margin: 8px 0; border: 0.5px solid #00C853;'><small>Inicio: {d.get('hora_inicio', '--:--')}</small></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia-monitor'><span class='text-maquina'>{m}</span><br><small>DISPONIBLE</small></div>", unsafe_allow_html=True)
    time.sleep(30)
    st.rerun()

# 2. SEGUIMIENTO DE PEDIDOS - SIN TOCAR
elif menu == "🔍 Seguimiento de Pedidos":
    st.title("🔍 Seguimiento de Órdenes")
    try:
        ops = supabase.table("ordenes_planeadas").select("*").neq("estado", "Finalizado").execute().data
        if ops:
            df = pd.DataFrame(ops)
            c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
            c1.write("**OP**"); c2.write("**TRABAJO**"); c3.write("**PROX. ÁREA**"); c4.write("**ACCIÓN**")
            for _, fila in df.iterrows():
                r1, r2, r3, r4 = st.columns([1, 2, 1, 1])
                r1.write(fila['op']); r2.write(fila['trabajo']); r3.write(fila['proxima_area'])
                if r4.button("🔎 Detalles", key=f"seg_{fila['op']}"): mostrar_detalle_op(fila)
    except: st.info("No hay órdenes pendientes.")

# 3. PLANIFICACIÓN - SIN TOCAR
elif menu == "📅 Planificación (Ingreso OP)":
    st.title("📅 Registro de Nueva OP")
    tipo_op_sel = st.selectbox("TIPO DE PRODUCTO:", ["-- Seleccione --", "RI (Rollo Impreso)", "RB (Rollo Blanco)", "FRI (Forma Impresa)", "FRB (Forma Blanca)"])
    if tipo_op_sel != "-- Seleccione --":
        pref = tipo_op_sel.split(" ")[0]
        es_forma = pref in ["FRI", "FRB"]; es_impreso = pref in ["RI", "FRI"]
        with st.form("form_op"):
            st.markdown(f"<div class='title-area'>FORMULARIO: {tipo_op_sel}</div>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3); op_num = c1.text_input("NÚMERO DE OP"); vendedor = c2.text_input("VENDEDOR"); cliente = c3.text_input("CLIENTE"); trabajo = st.text_input("TRABAJO")
            pld = {"core": "N/A", "unidades_bolsa": 0, "unidades_caja": 0, "num_desde": "N/A", "num_hasta": "N/A", "copias": "N/A", "fondo_copias": "N/A", "traficos_orden": "N/A", "codigo_barras": "NO", "perforaciones": "N/A", "presentacion": "N/A"}
            f1, f2, f3 = st.columns(3); material = f1.text_input("PAPEL"); medida = f2.text_input("MEDIDA"); cantidad = f3.number_input("CANTIDAD", min_value=0)
            if not es_forma:
                r1, r2, r3 = st.columns(3); pld["core"] = r1.selectbox("CORE", ["13MM", "19MM", "1 PULG", "2 PULG", "3 PULG"]); pld["unidades_bolsa"] = r2.number_input("U. BOLSA", 0); pld["unidades_caja"] = r3.number_input("U. CAJA", 0)
                pArea = "IMPRESIÓN" if pref == "RI" else "CORTE"
            else:
                n1, n2, n3 = st.columns(3); pld["num_desde"], pld["num_hasta"] = n1.text_input("DESDE"), n2.text_input("HASTA"); pld["copias"] = n3.selectbox("COPIAS", ["1", "2", "3", "4"])
                pArea = "IMPRESIÓN" if pref == "FRI" else "COLECTORAS"
            tin_n, tin_c = (0, "N/A")
            if es_impreso:
                i1, i2 = st.columns(2); tin_n = i1.number_input("TINTAS", 0); tin_c = i2.text_input("COLORES")
            obs = st.text_area("OBSERVACIONES")
            if st.form_submit_button("🚀 REGISTRAR"):
                final_data = {"op": f"{pref}-{op_num}".upper(), "nombre_cliente": cliente, "trabajo": trabajo, "vendedor": vendedor, "tipo_acabado": pref, "material": material, "ancho_medida": medida, "unidades_solicitadas": cantidad, "cant_tintas": tin_n, "especificacion_tintas": tin_c, "proxima_area": pArea, "observaciones": obs, "estado": "Pendiente", **pld}
                supabase.table("ordenes_planeadas").insert(final_data).execute()
                st.success("✅ OP Registrada"); st.balloons()

# 4. MÓDULOS OPERATIVOS (AQUÍ ES DONDE TRABAJAREMOS TUS PARÁMETROS)
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}[menu]
    st.title(f"Área: {area}")
    try: activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area).execute().data}
    except: activos = {}
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS[area]):
        if cols[i % 4].button(f"{'🔴' if m in activos else '⚪'} {m}", key=f"btn_{m}"): st.session_state.m_sel = m
    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area]:
        ms = st.session_state.m_sel
        if ms not in activos:
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area).eq("estado", "Pendiente").execute().data
            if ops:
                sel = st.selectbox("Seleccione OP:", ["--"] + [f"{o['op']} | {o['trabajo']}" for o in ops])
                if st.button("▶️ INICIAR"):
                    d = next(o for o in ops if o['op'] == sel.split(" | ")[0])
                    supabase.table("trabajos_activos").insert({"maquina": ms, "area": area, "op": d['op'], "trabajo": d['trabajo'], "hora_inicio": datetime.now().strftime("%H:%M"), "tipo_acabado": d['tipo_acabado']}).execute()
                    supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d['op']).execute()
                    st.rerun()
        else:
            t = activos[ms]
            st.success(f"TRABAJANDO: {t['op']}")
            if st.button("🏁 FINALIZAR"): modal_finalizar_trabajo(t, ms, area)

# 5. HISTORIAL KPI
elif menu == "📊 Historial KPI":
    st.title("📊 Historial")
    t_names = ["impresion", "corte", "colectoras", "encuadernacion"]
    tabs = st.tabs([n.capitalize() for n in t_names])
    for i, tab in enumerate(tabs):
        with tab:
            data = supabase.table(t_names[i]).select("*").execute().data
            if data: st.dataframe(pd.DataFrame(data), use_container_width=True)
