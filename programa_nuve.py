import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import io
from fpdf import FPDF

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V31 - TOTAL", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("Error de conexión a Base de Datos. Revisa los Secrets.")
    st.stop()

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; font-size: 18px !important; width: 100%; }
    .title-area { background-color: #0D47A1; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 22px; margin-bottom: 20px; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 20px; border-radius: 15px; text-align: center; color: #000000 !important; font-weight: bold; font-size: 18px; margin-bottom: 10px; }
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 20px; border-radius: 15px; text-align: center; color: #000000 !important; font-size: 16px; margin-bottom: 10px; }
    .section-header { background-color: #F0F2F6; padding: 10px; border-radius: 8px; font-weight: bold; color: #0D47A1; margin-top: 15px; margin-bottom: 10px; border-left: 6px solid #0D47A1; }
    .metric-box { background-color: #ffffff; border: 1px solid #e0e0e0; padding: 12px; border-radius: 8px; margin-bottom: 5px; color: #000000 !important; line-height: 1.6; }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}
PRESENTACIONES = ["BLOCK TAPADURA", "LIBRETA LICOM", "HOJAS SUELTAS", "PAQUETES", "TACOS", "CAJAS", "FAJILLAS"]
PRESENTACIONES2 = ["POR CABEZA", "IZQUIERDA", "DERECHA", "PATA"]

# --- FUNCIONES AUXILIARES ---
def to_excel_limpio(df_input, tipo=None):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_input.to_excel(writer, index=False, sheet_name='REPORTE')
    return output.getvalue()

def generar_pdf_op(row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(13, 71, 161)
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 15, f"REPORTE TECNICO - OP: {row['op']}", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"TRABAJO: {row['nombre_trabajo']}", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)
    pdf.cell(0, 10, f"Cliente: {row.get('cliente')}", border='B', ln=True)
    pdf.cell(0, 10, f"Tipo: {row.get('tipo_orden')}", border='B', ln=True)
    return bytes(pdf.output())

@st.dialog("📋 RADIOGRAFÍA TÉCNICA", width="large")
def modal_detalle_op(row):
    st.markdown(f"## OP: {row['op']} — {row['nombre_trabajo']}")
    st.write(f"🏭 **Estado:** `{row['proxima_area']}`")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div class='section-header'>👤 GENERAL</div>", unsafe_allow_html=True)
        st.write(f"**Cliente:** {row.get('cliente')}")
        st.write(f"**Vendedor:** {row.get('vendedor')}")
    with col2:
        st.markdown("<div class='section-header'>📐 ESPECIFICACIONES</div>", unsafe_allow_html=True)
        st.write(f"**Tipo:** {row.get('tipo_orden')}")
    with col3:
        st.markdown("<div class='section-header'>⚙️ PROCESO</div>", unsafe_allow_html=True)
        st.write(f"**Próxima Área:** {row.get('proxima_area')}")
    
    st.markdown("<div class='section-header'>📜 HISTORIAL</div>", unsafe_allow_html=True)
    st.json(row.get('historial_procesos', []))
    
    pdf_bytes = generar_pdf_op(row)
    st.download_button("🖨️ Descargar PDF", pdf_bytes, f"OP_{row['op']}.pdf", "application/pdf")

# --- ESTRUCTURA DE MENÚ ---
if 'sel_tipo' not in st.session_state: st.session_state.sel_tipo = None
if 'rep' not in st.session_state: st.session_state.rep = None

with st.sidebar:
    st.title("🏭 NUVE V31.0")
    menu = st.radio("MÓDULO:", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# --- MÓDULO 1: MONITOR ---
if menu == "🖥️ Monitor":
    st.title("Monitor de Planta")
    act_data = supabase.table("trabajos_activos").select("*").execute().data
    act = {a['maquina']: a for a in act_data}
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    st.markdown(f"<div class='card-produccion'>{m}<br>OP: {act[m]['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'>{m}<br>LIBRE</div>", unsafe_allow_html=True)
    time.sleep(30); st.rerun()

# --- MÓDULO 2: SEGUIMIENTO ---
elif menu == "🔍 Seguimiento":
    st.title("Seguimiento de Producción")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if res:
        df = pd.DataFrame(res)
        st.download_button("📥 Excel General", to_excel_limpio(df), "Reporte_Nuve.xlsx")
        for index, row in df.iterrows():
            with st.container():
                c1, c2, c3, c4 = st.columns([1, 3, 2, 1])
                c1.write(row['op'])
                c2.write(row['cliente'])
                c3.write(row['proxima_area'])
                if c4.button("👁️", key=f"btn_{row['op']}"):
                    modal_detalle_op(row.to_dict())

# --- MÓDULO 3: PLANIFICACIÓN ---
elif menu == "📅 Planificación":
    st.title("Planificación de Órdenes")
    origen = st.radio("Origen:", ["Nueva", "Repetición"], horizontal=True)
    datos_rec = {}
    if origen == "Repetición":
        op_busq = st.text_input("OP Anterior:")
        if st.button("Buscar"):
            res_b = supabase.table("ordenes_planeadas").select("*").eq("op", op_busq.upper()).execute()
            if res_b.data: datos_rec = res_b.data[0]; st.success("Cargado")

    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📑 FORMAS IMPRESAS"): st.session_state.sel_tipo = "FORMAS IMPRESAS"
    if c2.button("📄 FORMAS BLANCAS"): st.session_state.sel_tipo = "FORMAS BLANCAS"
    if c3.button("🌀 ROLLOS IMPRESOS"): st.session_state.sel_tipo = "ROLLOS IMPRESOS"
    if c4.button("⚪ ROLLOS BLANCOS"): st.session_state.sel_tipo = "ROLLOS BLANCOS"

    if st.session_state.sel_tipo:
        t = st.session_state.sel_tipo
        pref = {"FORMAS IMPRESAS": "FRI-", "FORMAS BLANCAS": "FRB-", "ROLLOS IMPRESOS": "RI-", "ROLLOS BLANCOS": "RB-"}[t]
        
        with st.form("plan_form", clear_on_submit=True):
            f1, f2, f3 = st.columns(3)
            op_in = f1.text_input("Número OP*")
            cli = f2.text_input("Cliente*", value=datos_rec.get('cliente', ""))
            vend = f3.text_input("Vendedor", value=datos_rec.get('vendedor', ""))
            trab = st.text_input("Trabajo", value=datos_rec.get('nombre_trabajo', ""))

            lista_p = []
            if "FORMAS" in t:
                g1, g2, g3 = st.columns(3)
                cant_f = g1.number_input("Cantidad", value=int(datos_rec.get('cantidad_formas', 0)))
                partes = g2.selectbox("Partes", [1,2,3,4,5,6], index=int(datos_rec.get('num_partes', 1))-1)
                pres = g3.selectbox("Presentación", PRESENTACIONES)
                
                for i in range(1, partes + 1):
                    st.markdown(f"**Parte {i}**")
                    d1, d2, d3 = st.columns(3)
                    anc = d1.text_input(f"Ancho P{i}", key=f"anc_{i}")
                    lar = d2.text_input(f"Largo P{i}", key=f"lar_{i}")
                    pap = d3.text_input(f"Papel P{i}", key=f"pap_{i}")
                    lista_p.append({"p": i, "anc": anc, "lar": lar, "papel": pap})
                obs = st.text_area("Obs Formas")
            else:
                r1, r2, r3 = st.columns(3)
                mat = r1.text_input("Material", value=datos_rec.get('material', ""))
                gram = r2.number_input("Gramaje", value=int(datos_rec.get('gramaje_rollos', 0)))
                cant_r = r3.number_input("Cantidad Rollos", value=int(datos_rec.get('cantidad_rollos', 0)))
                c_dest = st.text_input("Ciudad Destino", value=datos_rec.get('ciudad_destino', "NO"))
                obs = st.text_area("Obs Rollos")

            if st.form_submit_button("GUARDAR"):
                payload = {
                    "op": f"{pref}{op_in.upper()}", "cliente": cli, "vendedor": vend, "nombre_trabajo": trab,
                    "tipo_orden": t, "proxima_area": "IMPRESIÓN" if "IMPRESOS" in t else "CORTE",
                    "historial_procesos": []
                }
                if "FORMAS" in t:
                    payload.update({"cantidad_formas": cant_f, "num_partes": partes, "presentacion": pres, "detalles_partes_json": lista_p, "observaciones_formas": obs})
                else:
                    payload.update({"material": mat, "gramaje_rollos": gram, "cantidad_rollos": cant_r, "ciudad_destino": c_dest, "observaciones_rollos": obs})
                
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.success("Orden Guardada"); time.sleep(1); st.rerun()

# --- MÓDULO 4: PRODUCCIÓN ---
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.markdown(f"<div class='title-area'>PANEL {area_act}</div>", unsafe_allow_html=True)
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    cols = st.columns(3)
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols[idx % 3]:
            if m in activos:
                st.markdown(f"<div class='card-produccion'>TRABAJANDO<br>{m}<br>OP: {activos[m]['op']}</div>", unsafe_allow_html=True)
                if st.button(f"FINALIZAR {m}", key=f"fin_{m}"):
                    st.session_state.rep = activos[m]; st.rerun()
            else:
                st.markdown(f"<div class='card-vacia'>LIBRE<br>{m}</div>", unsafe_allow_html=True)
                ops_p = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
                if ops_p:
                    sel_op = st.selectbox("OP", [o['op'] for o in ops_p], key=f"sel_{m}")
                    if st.button(f"INICIAR {m}", key=f"ini_{m}"):
                        supabase.table("trabajos_activos").insert({"maquina": m, "area": area_act, "op": sel_op, "hora_inicio": datetime.now().isoformat()}).execute()
                        st.rerun()

    if st.session_state.rep:
        r = st.session_state.rep
        with st.form("cierre_form"):
            st.subheader(f"Cierre OP {r['op']}")
            operario = st.text_input("Operario*")
            datos_c = {"metros": st.number_input("Metros/Cant")}
            if st.form_submit_button("REGISTRAR"):
                d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                n_area = "FINALIZADO"
                if "ROLLOS" in d_op['tipo_orden'] and area_act == "IMPRESIÓN": n_area = "CORTE"
                elif "FORMAS" in d_op['tipo_orden']:
                    if area_act == "IMPRESIÓN": n_area = "COLECTORAS"
                    elif area_act == "COLECTORAS": n_area = "ENCUADERNACIÓN"
                
                hist = d_op.get('historial_procesos') or []
                hist.append({"area": area_act, "maquina": r['maquina'], "operario": operario, "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"), "datos": datos_c})
                
                supabase.table("ordenes_planeadas").update({"proxima_area": n_area, "historial_procesos": hist}).eq("op", r['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()
                st.session_state.rep = None; st.success("OK"); time.sleep(1); st.rerun()
