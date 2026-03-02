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

# --- DICCIONARIO DE ETIQUETAS PARA MOSTRAR DATOS ---
LABELS = {
    "metros": "Metros", "bobinas": "Bobinas", "imgs_bobina": "Imgs x Bobina",
    "tinta_kg": "Tinta (Kg)", "planchas": "Planchas", "desperdicio": "Desp.",
    "desperdicio_corte": "Desp. Corte", "motivo": "Motivo", "varillas": "Varillas",
    "rollos_cortados": "Rollos", "imgs_varilla": "Imgs x Varilla", "cajas": "Cajas"
}

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; font-size: 18px !important; width: 100%; }
    .title-area { background-color: #0D47A1; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 22px; margin-bottom: 20px; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 20px; border-radius: 15px; text-align: center; color: #000000 !important; font-weight: bold; font-size: 18px; margin-bottom: 10px; }
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 20px; border-radius: 15px; text-align: center; color: #000000 !important; font-size: 16px; margin-bottom: 10px; }
    .section-header { background-color: #F0F2F6; padding: 10px; border-radius: 8px; font-weight: bold; color: #0D47A1; margin-top: 15px; margin-bottom: 10px; border-left: 6px solid #0D47A1; }
    .metric-box { background-color: #ffffff; border: 1px solid #e0e0e0; padding: 12px; border-radius: 8px; margin-bottom: 5px; color: #000000 !important; line-height: 1.6; }
    
    .log-card { background-color: #ffffff; border: 1px solid #dee2e6; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 5px solid #0D47A1; }
    .log-title { color: #0D47A1; font-weight: bold; font-size: 16px; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    .log-data { font-size: 14px; color: #333; display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 10px; }
    .data-item { background: #f8f9fa; padding: 6px; border: 1px solid #e9ecef; border-radius: 4px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- FUNCIONES AUXILIARES ---

def format_label(key):
    return LABELS.get(key, key.replace('_', ' ').title())

def to_excel_limpio(df_input, tipo=None):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        if tipo == "GENERAL":
            df_f = df_input[df_input['tipo_orden'].str.contains("FORMAS", na=False)].dropna(axis=1, how='all')
            df_r = df_input[df_input['tipo_orden'].str.contains("ROLLOS", na=False)].dropna(axis=1, how='all')
            if not df_f.empty: df_f.to_excel(writer, index=False, sheet_name='FORMAS')
            if not df_r.empty: df_r.to_excel(writer, index=False, sheet_name='ROLLOS')
        else:
            df_unit = df_input.dropna(axis=1, how='all')
            if 'id' in df_unit.columns: df_unit = df_unit.drop(columns=['id'])
            df_unit.to_excel(writer, index=False, sheet_name='DETALLE_OP')
    return output.getvalue()

def generar_pdf_op(row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(13, 71, 161)
    pdf.rect(0, 0, 210, 45, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 22)
    pdf.cell(0, 12, f"FICHA TECNICA DE PRODUCCION", ln=True, align='C')
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"ORDEN DE PRODUCCION: {row['op']}", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(15)
    
    # --- SECCIÓN 1 ---
    pdf.set_font("Arial", 'B', 11)
    pdf.set_fill_color(235, 235, 235)
    pdf.cell(0, 8, " 1. INFORMACION COMERCIAL", ln=True, fill=True)
    pdf.set_font("Arial", '', 10)
    c1 = 95
    pdf.cell(c1, 7, f" CLIENTE: {row.get('cliente')}", border='LRB')
    pdf.cell(0, 7, f" VENDEDOR: {row.get('vendedor')}", border='RB', ln=True)
    pdf.cell(c1, 7, f" TRABAJO: {row.get('nombre_trabajo')}", border='LRB')
    pdf.cell(0, 7, f" TIPO: {row.get('tipo_orden')}", border='RB', ln=True)
    pdf.ln(5)

    # --- SECCIÓN 2 ---
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, " 2. ESPECIFICACIONES DE MONTAJE", ln=True, fill=True)
    pdf.set_font("Arial", '', 10)
    if "FORMAS" in row.get('tipo_orden', ''):
        pdf.cell(c1, 7, f" CANTIDAD: {row.get('cantidad_formas')}", border='LRB')
        pdf.cell(0, 7, f" NUM. PARTES: {row.get('num_partes')}", border='RB', ln=True)
        pdf.cell(c1, 7, f" PRESENTACION: {row.get('presentacion')}", border='LRB')
        pdf.cell(0, 7, f" PERFORACION: {row.get('perforaciones_detalle')}", border='RB', ln=True)
    else:
        pdf.cell(c1, 7, f" MATERIAL: {row.get('material')}", border='LRB')
        pdf.cell(0, 7, f" GRAMAJE: {row.get('gramaje_rollos')}", border='RB', ln=True)
    pdf.ln(5)

    # --- SECCIÓN 3 ---
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, " 3. BITACORA DE PROCESOS (DATOS TECNICOS)", ln=True, fill=True)
    historial = row.get('historial_procesos', [])
    if not historial:
        pdf.cell(0, 10, " Sin registros.", border=1, ln=True, align='C')
    else:
        for h in historial:
            pdf.set_fill_color(245, 250, 255)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 7, f" >> {h['area']} / {h['maquina']} | Operario: {h['operario']} | {h['fecha']}", ln=True, fill=True, border='TRL')
            datos_c = h.get('datos', {})
            txt_datos = " | ".join([f"{format_label(k)}: {v}" for k, v in datos_c.items() if v or v == 0])
            pdf.set_font("Arial", '', 9)
            pdf.multi_cell(0, 6, f" {txt_datos}", border='LRB')
            if h.get('observaciones'):
                pdf.set_font("Arial", 'I', 8)
                pdf.multi_cell(0, 5, f" OBS: {h['observaciones']}", border='LRB')
            pdf.ln(2)

    pdf.set_y(-30)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 10, f"Generado por NUVE V31 el {datetime.now().strftime('%d/%m/%Y %H:%M')}", align='C')
    return bytes(pdf.output())

# ==========================================
# VENTANA EMERGENTE (MODAL) RADIOGRAFÍA
# ==========================================
@st.dialog("📋 RADIOGRAFÍA TÉCNICA", width="large")
def modal_detalle_op(row):
    st.markdown(f"## OP: {row['op']} — {row['nombre_trabajo']}")
    st.write(f"🏭 **Estado:** `{row['proxima_area']}`")
    
    st.markdown("<div class='section-header'>📜 BITÁCORA DE CIERRES EN PLANTA</div>", unsafe_allow_html=True)
    hist = row.get('historial_procesos', [])
    if not hist:
        st.info("No hay registros de producción todavía.")
    else:
        for h in hist:
            datos_c = h.get('datos', {})
            # Crear elementos visuales para CADA dato
            items_html = ""
            for k, v in datos_c.items():
                if v or v == 0:
                    label = format_label(k)
                    items_html += f"<div class='data-item'><b>{label}:</b> {v}</div>"
            
            st.markdown(f"""
            <div class='log-card'>
                <div class='log-title'>✅ {h['area']} — Máquina: {h['maquina']}</div>
                <div style='font-size:13px; color:#666;'>
                    👤 <b>{h['operario']}</b> | ⏱️ <b>{h['duracion']}</b> | 📅 <b>{h['fecha']}</b>
                </div>
                <div class='log-data'>
                    {items_html}
                </div>
                {f"<div style='margin-top:10px; font-size:12px; font-style:italic;'>📝 {h['observaciones']}</div>" if h.get('observaciones') else ""}
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    try:
        st.download_button("🖨️ Descargar Ficha Técnica PDF", data=generar_pdf_op(row), 
                           file_name=f"Ficha_{row['op']}.pdf", mime="application/pdf", use_container_width=True)
    except Exception as e:
        st.error(f"Error PDF: {e}")

# ==========================================
# MENÚ Y LÓGICA PRINCIPAL
# ==========================================
if 'sel_tipo' not in st.session_state: st.session_state.sel_tipo = None
if 'rep' not in st.session_state: st.session_state.rep = None

with st.sidebar:
    st.title("🏭 NUVE V31.0")
    menu = st.radio("SELECCIONE MÓDULO:", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# ... (Módulos Monitor, Seguimiento, Planificación iguales) ...
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

elif menu == "🔍 Seguimiento":
    st.title("Seguimiento de Producción")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if res:
        df = pd.DataFrame(res)
        for index, row in df.iterrows():
            if st.button(f"👁️ Ver OP: {row['op']}", key=f"v_{row['op']}"):
                modal_detalle_op(row.to_dict())

elif menu == "📅 Planificación":
    st.title("Planificación de Órdenes")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📑 FORMAS IMPRESAS"): st.session_state.sel_tipo = "FORMAS IMPRESAS"
    if c2.button("📄 FORMAS BLANCAS"): st.session_state.sel_tipo = "FORMAS BLANCAS"
    if c3.button("🌀 ROLLOS IMPRESOS"): st.session_state.sel_tipo = "ROLLOS IMPRESOS"
    if c4.button("⚪ ROLLOS BLANCOS"): st.session_state.sel_tipo = "ROLLOS BLANCOS"
    if st.session_state.sel_tipo:
        t = st.session_state.sel_tipo
        with st.form("form_plan", clear_on_submit=True):
            f1, f2 = st.columns(2)
            op_n = f1.text_input("OP *")
            cli = f2.text_input("Cliente *")
            if st.form_submit_button("🚀 GUARDAR"):
                payload = {"op": op_n.upper(), "cliente": cli, "tipo_orden": t, "proxima_area": "IMPRESIÓN" if "IMPRESOS" in t else ("CORTE" if "BLANCOS" in t and "ROLLOS" in t else "COLECTORAS")}
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.session_state.sel_tipo = None; st.rerun()

# ==========================================
# PRODUCCIÓN (TÁCTIL)
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.markdown(f"<div class='title-area'>PANEL TÁCTIL: {area_act}</div>", unsafe_allow_html=True)
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    cols = st.columns(3)
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols[idx % 3]:
            if m in activos:
                tr = activos[m]
                st.markdown(f"<div class='card-produccion'>🟡 {m}<br>OP: {tr['op']}</div>", unsafe_allow_html=True)
                if st.button(f"✅ FINALIZAR {m}", key=f"f_{m}"): st.session_state.rep = tr
            else:
                st.markdown(f"<div class='card-vacia'>⚪ {m}<br>LIBRE</div>", unsafe_allow_html=True)
                ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
                if ops:
                    sel = st.selectbox("Asignar OP", [o['op'] for o in ops], key=f"s_{m}")
                    if st.button(f"🚀 INICIAR {m}", key=f"str_{m}"):
                        d = next(o for o in ops if o['op'] == sel)
                        supabase.table("trabajos_activos").insert({"maquina": m, "area": area_act, "op": d['op'], "hora_inicio": datetime.now().isoformat()}).execute()
                        st.rerun()

    if st.session_state.rep:
        r = st.session_state.rep
        st.divider()
        with st.form("cierre_tecnico_v27"):
            st.warning(f"CIERRE: OP {r['op']} en {r['maquina']}")
            op_name = st.text_input("Operario")
            datos = {}
            if area_act == "IMPRESIÓN":
                datos['metros'] = st.number_input("Metros", 0)
                datos['bobinas'] = st.number_input("Bobinas", 0)
                datos['tinta_kg'] = st.number_input("Tinta (Kg)", 0.0)
            elif area_act == "CORTE":
                datos['varillas'] = st.number_input("Varillas", 0)
                datos['rollos_cortados'] = st.number_input("Rollos", 0)
            obs_t = st.text_area("Observaciones")
            
            if st.form_submit_button("🏁 FINALIZAR"):
                d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                h = d_op.get('historial_procesos', []) or []
                h.append({"area": area_act, "maquina": r['maquina'], "operario": op_name, "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"), "duracion": "N/A", "datos": datos, "observaciones": obs_t})
                supabase.table("ordenes_planeadas").update({"historial_procesos": h, "proxima_area": "FINALIZADO"}).eq("op", r['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()
                st.session_state.rep = None; st.rerun()
