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

# --- FUNCIONES AUXILIARES ---
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
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 15, f"REPORTE TECNICO INTEGRAL - OP: {row['op']}", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(20)
    pdf.set_font("Arial", 'B', 11)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 8, " 1. INFORMACION DE VENTA", ln=True, fill=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(100, 7, f"Cliente: {row.get('cliente')}", border='B')
    pdf.cell(0, 7, f"Vendedor: {row.get('vendedor')}", border='B', ln=True)
    pdf.ln(10)
    pdf.cell(0, 7, "Documento de control interno NUVE V31", ln=True)
    return bytes(pdf.output())

@st.dialog("📋 RADIOGRAFÍA TÉCNICA DE LA ORDEN", width="large")
def modal_detalle_op(row):
    st.markdown(f"## OP: {row['op']} — {row['nombre_trabajo']}")
    st.write(f"🏭 **Estado en Planta:** `{row['proxima_area']}`")
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='section-header'>👤 DATOS GENERALES</div>", unsafe_allow_html=True)
        st.write(f"**Cliente:** {row.get('cliente')}")
        st.write(f"**Vendedor:** {row.get('vendedor')}")
    with col2:
        st.markdown("<div class='section-header'>📐 ESPECIFICACIONES</div>", unsafe_allow_html=True)
        st.write(f"**Tipo:** {row['tipo_orden']}")
    
    st.divider()
    pdf_bytes = generar_pdf_op(row)
    st.download_button("🖨️ Descargar PDF", data=pdf_bytes, file_name=f"OP_{row['op']}.pdf", mime="application/pdf")

# ==========================================
# ESTRUCTURA DE MENÚ
# ==========================================
if 'sel_tipo' not in st.session_state: st.session_state.sel_tipo = None
if 'rep' not in st.session_state: st.session_state.rep = None

with st.sidebar:
    st.title("🏭 NUVE V31.0")
    menu = st.radio("SELECCIONE MÓDULO:", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# ==========================================
# MÓDULO 1: MONITOR
# ==========================================
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

# ==========================================
# MÓDULO 2: SEGUIMIENTO
# ==========================================
elif menu == "🔍 Seguimiento":
    st.title("Seguimiento de Producción")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if res:
        df = pd.DataFrame(res)
        st.download_button("📥 Excel General", to_excel_limpio(df, "GENERAL"), "Reporte_General_Nuve.xlsx")
        for index, row in df.iterrows():
            with st.container():
                c1, c2, c3, c4 = st.columns([1, 3, 2, 1])
                c1.write(f"**{row['op']}**")
                c2.write(row['cliente'])
                c3.write(row['proxima_area'])
                if c4.button("👁️", key=f"v_{row['op']}"):
                    modal_detalle_op(row.to_dict())

# ==========================================
# MÓDULO 3: PLANIFICACIÓN (CON PREFIJOS DINÁMICOS)
# ==========================================
elif menu == "📅 Planificación":
    st.title("Planificación de Órdenes")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📑 FORMAS IMPRESAS"): st.session_state.sel_tipo = "FORMAS IMPRESAS"
    if c2.button("📄 FORMAS BLANCAS"): st.session_state.sel_tipo = "FORMAS BLANCAS"
    if c3.button("🌀 ROLLOS IMPRESOS"): st.session_state.sel_tipo = "ROLLOS IMPRESOS"
    if c4.button("⚪ ROLLOS BLANCOS"): st.session_state.sel_tipo = "ROLLOS BLANCOS"

    if st.session_state.sel_tipo:
        t = st.session_state.sel_tipo
        
        # --- LOGICA DE PREFIJOS ---
        prefijo = ""
        if t == "ROLLOS IMPRESOS": prefijo = "RI-"
        elif t == "ROLLOS BLANCOS": prefijo = "RB-"
        elif t == "FORMAS IMPRESAS": prefijo = "FRI-"
        elif t == "FORMAS BLANCAS": prefijo = "FRB-"

        with st.form("form_plan", clear_on_submit=True):
            st.subheader(f"Nueva Orden: {t}")
            st.info(f"Se asignará automáticamente el prefijo: **{prefijo}**")
            
            f1, f2, f3 = st.columns(3)
            num_op_input = f1.text_input("Número de OP (sin prefijo) *")
            op_a = f2.text_input("OP Anterior")
            cli = f3.text_input("Cliente *")
            
            f4, f5 = st.columns(2)
            vend = f4.text_input("Vendedor")
            trab = f5.text_input("Nombre Trabajo")

            if "FORMAS" in t:
                g1, g2 = st.columns(2)
                cant_f = g1.number_input("Cantidad Formas", 0)
                partes = g2.selectbox("Número de Partes", [1,2,3,4,5,6])
                
                t_perf = st.selectbox("¿Tiene Perforaciones?", ["NO", "SI"])
                perf_d = st.text_area("Detalle Perforación") if t_perf == "SI" else "NO"
                
                t_barr = st.selectbox("¿Tiene Código de Barras?", ["NO", "SI"])
                barr_d = st.text_area("Detalle Barras") if t_barr == "SI" else "NO"

                lista_p = []
                for i in range(1, partes + 1):
                    st.markdown(f"**PARTE {i}**")
                    d1, d2, d3, d4, d5 = st.columns(5)
                    anc = d1.text_input(f"Ancho P{i}", key=f"a_{i}")
                    lar = d2.text_input(f"Largo P{i}", key=f"l_{i}")
                    pap = d3.text_input(f"Papel P{i}", key=f"p_{i}")
                    gra = d4.text_input(f"Gramos P{i}", key=f"g_{i}")
                    fnd = d5.text_input(f"Fondo P{i}", key=f"fnd_{i}")
                    
                    tf, tr = "N/A", "N/A"
                    if t == "FORMAS IMPRESAS":
                        t1, t2 = st.columns(2)
                        tf = t1.text_input(f"Tintas F P{i}", key=f"tf_{i}")
                        tr = t2.text_input(f"Tintas R P{i}", key=f"tr_{i}")
                    lista_p.append({"p":i, "anc":anc, "lar":lar, "papel":pap, "gramos":gra, "fondo":fnd, "tf":tf, "tr":tr})
                
                pres = st.selectbox("Presentación", ["LIBRETAS TAPADURA", "BLOCK LICOM", "HOJAS SUELTAS", "PAQUETES", "TACOS"])
                obs = st.text_area("Observaciones")

            else: # ROLLOS
                r1, r2, r3 = st.columns(3)
                mat = r1.text_input("Material")
                gram = r2.text_input("Gramaje")
                ref_c = r3.text_input("Ref. Comercial")
                
                r4, r5 = st.columns(2)
                cant_r = r4.number_input("Cantidad Rollos", 0)
                core = r5.selectbox("Core", ["13MM", "19MM", "1 PULGADA", "40 MM", "2 PULGADAS", "3 PULGADAS"])
                
                tf_r, tr_r = "N/A", "N/A"
                if t == "ROLLOS IMPRESOS":
                    ct1, ct2 = st.columns(2)
                    tf_r = ct1.text_input("Tintas Frente")
                    tr_r = ct2.text_input("Tintas Respaldo")
                
                ub = st.number_input("Cant x Bolsa", 0)
                uc = st.number_input("Cant x Caja", 0)
                obs = st.text_area("Observaciones")

            if st.form_submit_button("🚀 GUARDAR PLANIFICACIÓN"):
                if not num_op_input or not cli:
                    st.error("Faltan campos obligatorios")
                else:
                    # CONSTRUCCIÓN DE LA OP CON PREFIJO
                    op_final = f"{prefijo}{num_op_input.strip().upper()}"
                    
                    ruta = "IMPRESIÓN"
                    if t == "ROLLOS BLANCOS": ruta = "CORTE"
                    if t == "FORMAS BLANCAS": ruta = "COLECTORAS"
                    
                    payload = {
                        "op": op_final, 
                        "op_anterior": op_a, 
                        "cliente": cli, 
                        "vendedor": vend, 
                        "nombre_trabajo": trab, 
                        "tipo_orden": t, 
                        "proxima_area": ruta
                    }
                    
                    if "FORMAS" in t:
                        payload.update({"cantidad_formas": int(cant_f), "num_partes": partes, "perforaciones_detalle": perf_d, "codigo_barras_detalle": barr_d, "detalles_partes_json": lista_p, "presentacion": pres, "observaciones_formas": obs})
                    else:
                        payload.update({"material": mat, "gramaje_rollos": gram, "ref_comercial": ref_c, "cantidad_rollos": int(cant_r), "core": core, "tintas_frente_rollos": tf_r, "tintas_respaldo_rollos": tr_r, "unidades_bolsa": int(ub), "unidades_caja": int(uc), "observaciones_rollos": obs})
                    
                    try:
                        supabase.table("ordenes_planeadas").insert(payload).execute()
                        st.success(f"Orden {op_final} guardada con éxito")
                        st.session_state.sel_tipo = None
                        time.sleep(1); st.rerun()
                    except Exception as e:
                        st.error(f"Error: La OP {op_final} ya podría existir. {e}")

# ==========================================
# MÓDULO 4: PRODUCCIÓN
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
                if st.button(f"✅ FINALIZAR {m}", key=f"f_{m}"):
                    st.session_state.rep = tr
            else:
                st.markdown(f"<div class='card-vacia'>⚪ {m}<br>LIBRE</div>", unsafe_allow_html=True)
                ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
                if ops:
                    sel = st.selectbox("Asignar OP", [o['op'] for o in ops], key=f"s_{m}")
                    if st.button(f"🚀 INICIAR {m}", key=f"str_{m}"):
                        d = next(o for o in ops if o['op'] == sel)
                        supabase.table("trabajos_activos").insert({"maquina": m, "area": area_act, "op": d['op'], "trabajo": d['nombre_trabajo'], "hora_inicio": datetime.now().isoformat()}).execute()
                        st.rerun()

    if st.session_state.rep:
        r = st.session_state.rep
        with st.form("cierre_tecnico"):
            st.warning(f"CIERRE: OP {r['op']} en {r['maquina']}")
            op_name = st.text_input("Operario *")
            papel_real = st.text_input("Papel Real Utilizado *")
            
            if st.form_submit_button("🏁 FINALIZAR"):
                inicio = datetime.fromisoformat(r['hora_inicio'])
                fin = datetime.now()
                duracion = str(fin - inicio).split('.')[0]
                
                d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                
                n_area = "FINALIZADO"
                if "ROLLOS" in d_op['tipo_orden'] and area_act == "IMPRESIÓN": n_area = "CORTE"
                elif "FORMAS" in d_op['tipo_orden']:
                    if area_act == "IMPRESIÓN": n_area = "COLECTORAS"
                    elif area_act == "COLECTORAS": n_area = "ENCUADERNACIÓN"
                
                h = d_op['historial_procesos'] if d_op['historial_procesos'] else []
                h.append({"area": area_act, "maquina": r['maquina'], "operario": op_name, "fecha": fin.strftime("%d/%m/%Y %H:%M"), "duracion": duracion, "datos_cierre": {"papel": papel_real}})
                
                supabase.table("ordenes_planeadas").update({"proxima_area": n_area, "historial_procesos": h}).eq("op", r['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()
                st.session_state.rep = None
                st.success("Cierre exitoso"); time.sleep(1); st.rerun()
