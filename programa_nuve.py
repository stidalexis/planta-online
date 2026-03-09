import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import io
from fpdf import FPDF

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V0.01 - TOTAL", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("Error de conexión a Base de Datos. Revisa los Secrets.")
    st.stop()

# --- ESTILOS CSS (DISEÑO INDUSTRIAL Y TÁCTIL) ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; font-size: 18px !important; width: 100%; }
    .title-area { background-color: #0D47A1; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 22px; margin-bottom: 20px; }
    
    /* MONITOR: Cartas con fondo vibrante y texto en NEGRO absoluto */
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 20px; border-radius: 15px; text-align: center; color: #000000 !important; font-weight: bold; font-size: 18px; margin-bottom: 10px; }
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 20px; border-radius: 15px; text-align: center; color: #000000 !important; font-size: 16px; margin-bottom: 10px; }
    
    .section-header { background-color: #F0F2F6; padding: 10px; border-radius: 8px; font-weight: bold; color: #0D47A1; margin-top: 15px; margin-bottom: 10px; border-left: 6px solid #0D47A1; }
    
    /* RADIOGRAFÍA: Cuadros blancos con texto en NEGRO */
    .metric-box { background-color: #ffffff; border: 1px solid #e0e0e0; padding: 12px; border-radius: 8px; margin-bottom: 5px; color: #000000 !important; line-height: 1.6; }
    .metric-box b { color: #000000 !important; }
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
PRESENTACIONES2 = ["POR CABEZA", "IZQUIERDA", "DERECHA", "PATA", ]

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
    
    # --- ENCABEZADO INDUSTRIAL ---
    pdf.set_fill_color(13, 71, 161)
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 15, f"REPORTE TECNICO INTEGRAL - OP: {row['op']}", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"TRABAJO: {row['nombre_trabajo']}", ln=True, align='C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(20)
    
    # --- SECCIÓN 1: DATOS DE VENTA ---
    pdf.set_font("Arial", 'B', 11)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 8, " 1. INFORMACION DE VENTA Y ORIGEN", ln=True, fill=True)
    pdf.set_font("Arial", '', 10)
    
    c1 = 100
    pdf.cell(c1, 7, f"Cliente: {row.get('cliente')}", border='B')
    pdf.cell(0, 7, f"Vendedor: {row.get('vendedor')}", border='B', ln=True)
    pdf.cell(c1, 7, f"Tipo de Orden: {row.get('tipo_orden')}", border='B')
    pdf.cell(0, 7, f"Fecha de Creacion: {row.get('created_at', '')[:10]}", border='B', ln=True)
    pdf.cell(0, 7, f"OP Anterior: {row.get('op_anterior', 'N/A')}", border='B', ln=True)
    
    pdf.ln(5)

    # --- SECCIÓN 2: DETALLES TECNICOS ---
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, " 2. ESPECIFICACIONES DE MATERIALES", ln=True, fill=True)
    pdf.set_font("Arial", '', 10)

    if "FORMAS" in row.get('tipo_orden', ''):
        pdf.cell(c1, 7, f"Cantidad Total: {row.get('cantidad_formas')}", border='B')
        pdf.cell(0, 7, f"Num. Partes: {row.get('num_partes')}", border='B', ln=True)
        pdf.cell(c1, 7, f"Presentacion: {row.get('presentacion')}", border='B')
        pdf.cell(0, 7, f"Transporte: {row.get('transportadora_formas', 'NO')} - {row.get('destino_formas', '')}", border='B', ln=True)
        pdf.cell(0, 7, f"Perforaciones: {row.get('perforaciones_detalle')}", border='B', ln=True)
        
        partes = row.get('detalles_partes_json', [])
        if partes:
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(0, 7, "DESGLOSE POR PARTE:", ln=True)
            pdf.set_font("Arial", '', 8)
            for p in partes:
                pdf.cell(0, 6, f"P{p['p']}: {p['papel']} {p['gramos']}g | Medida: {p['anc']}x{p['lar']} | Tintas: F:{p.get('tf','-')} / R:{p.get('tr','-')}", ln=True, border='L')
    else:
        pdf.cell(c1, 7, f"Material Base: {row.get('material')}", border='B')
        pdf.cell(0, 7, f"Gramaje: {row.get('gramaje_rollos')}", border='B', ln=True)
        pdf.cell(c1, 7, f"Cantidad Rollos: {row.get('cantidad_rollos')}", border='B')
        pdf.cell(0, 7, f"Core / Centro: {row.get('core')}", border='B', ln=True)
        pdf.cell(c1, 7, f"Tintas Frente: {row.get('tintas_frente_rollos')}", border='B')
        pdf.cell(0, 7, f"Empaque: {row.get('unidades_bolsa')} p/b | {row.get('unidades_caja')} p/c", border='B', ln=True)

    pdf.ln(5)

    # --- SECCIÓN 3: RESULTADOS DE PRODUCCION ---
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, " 3. TRAZABILIDAD Y CIERRES DE PRODUCCION", ln=True, fill=True)
    
    historial = row.get('historial_procesos', [])
    if not historial:
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 10, "Orden pendiente de iniciar procesos en planta.", ln=True)
    else:
        for h in historial:
            pdf.ln(2)
            pdf.set_font("Arial", 'B', 10)
            pdf.set_text_color(13, 71, 161)
            pdf.cell(0, 7, f">> AREA: {h['area']} ({h['maquina']})", ln=True)
            pdf.set_text_color(0, 0, 0)
            
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(70, 6, f"Operario: {h['operario']}", border=0)
            pdf.cell(60, 6, f"Duracion: {h['duracion']}", border=0)
            pdf.cell(0, 6, f"Fecha Cierre: {h['fecha']}", border=0, ln=True)
            
            pdf.set_font("Arial", '', 9)
            datos_c = h.get('datos_cierre', {})
            if datos_c:
                detalle_texto = " | ".join([f"{k.replace('_',' ').upper()}: {v}" for k, v in datos_c.items()])
                pdf.set_fill_color(245, 245, 245)
                pdf.multi_cell(0, 6, f"DATOS DE CAMPO: {detalle_texto}", border='L', fill=True)
            pdf.ln(1)

    pdf.ln(10)
    pdf.set_font("Arial", 'I', 7)
    pdf.cell(0, 10, f"NUVE V31 - Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}", align='C')
    
    return bytes(pdf.output())

# --- DIALOG RADIOGRAFÍA ---
@st.dialog("📋 RADIOGRAFÍA TÉCNICA DE LA ORDEN", width="large")
def modal_detalle_op(row):
    st.markdown(f"## OP: {row['op']} — {row['nombre_trabajo']}")
    st.write(f"🏭 **Estado en Planta:** `{row['proxima_area']}`")
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div class='section-header'>👤 DATOS GENERALES</div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class='metric-box'>
        👤 <b>Cliente:</b> {row.get('cliente')}<br>
        💼 <b>Vendedor:</b> {row.get('vendedor')}<br>
        🛠️ <b>Trabajo:</b> {row.get('nombre_trabajo')}<br>
        📅 <b>Fecha:</b> {row.get('created_at', '')[:10]}
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='section-header'>📐 ESPECIFICACIONES</div>", unsafe_allow_html=True)
        if "FORMAS" in row['tipo_orden']:
            st.markdown(f"""
            <div class='metric-box'>
            📦 <b>Cantidad:</b> {row.get('cantidad_formas')}<br>
            📑 <b>Partes:</b> {row.get('num_partes')}<br>
            🎨 <b>Presentación:</b> {row.get('presentacion')}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='metric-box'>
            📄 <b>Material:</b> {row.get('material')}<br>
            📏 <b>Gramaje:</b> {row.get('gramaje_rollos')}<br>
            📦 <b>Cantidad:</b> {row.get('cantidad_rollos')}<br>
            🌀 <b>Core:</b> {row.get('core')}
            </div>
            """, unsafe_allow_html=True)

    with col3:
        st.markdown("<div class='section-header'>⚙️ PROCESO TÉCNICO</div>", unsafe_allow_html=True)
        if "FORMAS" in row['tipo_orden']:
            st.markdown(f"""
            <div class='metric-box'>
            ✂️ <b>Perforación:</b> {row.get('perforaciones_detalle')}<br>
            🔢 <b>Barras:</b> {row.get('codigo_barras_detalle')}<br>
            🚚 <b>Transporte:</b> {row.get('transportadora_formas', 'NO')} ({row.get('destino_formas', 'N/A')})<br>
            📋 <b>Obs:</b> {row.get('observaciones_formas') or 'N/A'}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='metric-box'>
            🎨 <b>Tintas F:</b> {row.get('tintas_frente_rollos')}<br>
            🎨 <b>Tintas R:</b> {row.get('tintas_respaldo_rollos')}<br>
            🛍️ <b>Empaque:</b> {row.get('unidades_bolsa')} p/b<br>
            📦 <b>Cajas:</b> {row.get('unidades_caja')} p/c
            </div>
            """, unsafe_allow_html=True)

    if "FORMAS" in row['tipo_orden'] and row.get('detalles_partes_json'):
        st.markdown("<div class='section-header'>📑 DETALLE DE PAPELES POR PARTE</div>", unsafe_allow_html=True)
        st.table(pd.DataFrame(row['detalles_partes_json']))

    st.markdown("<div class='section-header'>📜 BITÁCORA DE CIERRES EN PLANTA</div>", unsafe_allow_html=True)
    hist = row.get('historial_procesos', [])
    if not hist:
        st.info("No hay registros de producción todavía.")
    else:
        for h in hist:
            with st.expander(f"✅ {h['area']} — {h['maquina']} ({h['operario']})"):
                st.write(f"⏱️ **Tiempo:** {h['duracion']} | 📅 **Fecha:** {h['fecha']}")
                st.json(h.get('datos_cierre', {}))

    st.divider()
    pdf_bytes = generar_pdf_op(row)
    st.download_button(label="🖨️ Descargar Radiografía Total (PDF)", data=pdf_bytes, file_name=f"RADIOGRAFIA_OP_{row['op']}.pdf", mime="application/pdf", use_container_width=True)

# --- ESTRUCTURA DE MENÚ ---
if 'sel_tipo' not in st.session_state: st.session_state.sel_tipo = None
if 'rep' not in st.session_state: st.session_state.rep = None

with st.sidebar:
    st.title("🏭 NUVE V31.0")
    menu = st.radio("SELECCIONE MÓDULO:", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])
    st.divider()
    st.caption("Conectado a Supabase Cloud")

# --- MÓDULO 1: MONITOR ---
if menu == "🖥️ Monitor":
    st.title("Monitor de Planta")
    act_data = supabase.table("trabajos_activos").select("*").execute().data
    act = {a['maquina']: a for a in act_data}
    for area, maquinas in MAQUINAS.items():
        st.markdown(f<div class='title-area'>{area}</div>", unsafe_allow_html=True)
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
        st.download_button("📥 Excel General", to_excel_limpio(df, "GENERAL"), "Reporte_General_Nuve.xlsx")
        st.divider()
        h1, h2, h3, h4, h5, h6 = st.columns([1, 2, 2, 1.5, 1.5, 1])
        h1.write("**OP**"); h2.write("**Cliente**"); h3.write("**Trabajo**"); h4.write("**Tipo**"); h5.write("**Status**"); h6.write("**Ver**")
        for index, row in df.iterrows():
            r1, r2, r3, r4, r5, r6 = st.columns([1, 2, 2, 1.5, 1.5, 1])
            r1.write(row['op'])
            r2.write(row['cliente'])
            r3.write(row['nombre_trabajo'])
            r4.write(row['tipo_orden'])
            color = "#FF9800" if row['proxima_area'] != "FINALIZADO" else "#4CAF50"
            r5.markdown(f"<span style='color:{color}; font-weight:bold;'>{row['proxima_area']}</span>", unsafe_allow_html=True)
            if r6.button("👁️", key=f"v_{row['op']}"):
                modal_detalle_op(row.to_dict())

# --- MÓDULO 3: PLANIFICACIÓN (CON REPETICIÓN Y AUTO-LLENADO) ---
elif menu == "📅 Planificación":
    st.title("Planificación de Órdenes 🌐")
    
    # 1. Selector de Origen de la Orden
    st.markdown("<div class='section-header'>📂 ORIGEN DE LA INFORMACIÓN</div>", unsafe_allow_html=True)
    origen = st.radio("¿Cómo desea ingresar la orden?", 
                      ["Nueva (Desde cero)", "Repetición Exacta", "Repetición con Cambios"], 
                      horizontal=True)
    
    # Variable para almacenar datos recuperados
    datos_rec = {}
    
    if "Repetición" in origen:
        col_busq1, col_busq2 = st.columns([3, 1])
        op_a_buscar = col_busq1.text_input("Ingrese el número de OP Anterior para buscar (Ej: FRI-100):")
        if col_busq2.button("🔍 Buscar y Cargar"):
            if op_a_buscar:
                try:
                    res_busq = supabase.table("ordenes_planeadas").select("*").eq("op", op_a_buscar.upper()).execute()
                    if res_busq.data:
                        datos_rec = res_busq.data[0]
                        st.success(f"✅ Datos de '{datos_rec['nombre_trabajo']}' cargados correctamente.")
                    else:
                        st.error("No se encontró la OP. Verifique el prefijo y número.")
                except Exception as e:
                    st.error(f"Error en la base de datos: {e}")
            else:
                st.warning("Por favor ingrese un número de OP.")

    st.divider()

    # . Selección de Tipo de Producto 
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📑 FORMAS IMPRESAS"): st.session_state.sel_tipo = "FORMAS IMPRESAS"
    if c2.button("📄 FORMAS BLANCAS"): st.session_state.sel_tipo = "FORMAS BLANCAS"
    if c3.button("🌀 ROLLOS IMPRESOS"): st.session_state.sel_tipo = "ROLLOS IMPRESOS"
    if c4.button("⚪ ROLLOS BLANCOS"): st.session_state.sel_tipo = "ROLLOS BLANCOS"

    if st.session_state.sel_tipo:
        t = st.session_state.sel_tipo
        prefijo = {"FORMAS IMPRESAS": "FRI-", "FORMAS BLANCAS": "FRB-", "ROLLOS IMPRESOS": "RI-", "ROLLOS BLANCOS": "RB-"}.get(t, "")

        with st.form("form_plan", clear_on_submit=True):
            st.subheader(f"Nueva Orden: {t} (Prefijo: {prefijo})")
            
            # --- SECCIÓN: DATOS GENERALES ---
            f1, f2, f3 = st.columns(3)
            op_input = f1.text_input("Número de Nueva OP (Solo número) *")
            
            # Si es repetición, sugerimos la OP anterior buscada
            val_op_ant = datos_rec.get('op', "") if "Repetición" in origen else ""
            op_a = f2.text_input("OP Anterior", value=val_op_ant)
            
            cli = f3.text_input("Cliente *", value=datos_rec.get('cliente', ""))
            
            f4, f5 = st.columns(2)
            vend = f4.text_input("Vendedor", value=datos_rec.get('vendedor', ""))
            trab = f5.text_input("Nombre del Trabajo", value=datos_rec.get('nombre_trabajo', ""))

            if "FORMAS" in t:
                # --- SECCIÓN: ESPECIFICACIONES FORMAS ---
                g1, g2, g3, g4 = st.columns(4)
                cant_f = g1.number_input("Cantidad Formas", 0, value=int(datos_rec.get('cantidad_formas', 0)))
                
                # Manejo de índices para Selectbox (evita errores si el valor no existe)
                val_partes = int(datos_rec.get('num_partes', 1))
                idx_partes = val_partes - 1 if 1 <= val_partes <= 6 else 0
                partes = g2.selectbox("Número de Partes", [1,2,3,4,5,6], index=idx_partes)
                
                idx_pres = PRESENTACIONES.index(datos_rec['presentacion']) if datos_rec.get('presentacion') in PRESENTACIONES else 0
                pres = g3.selectbox("Presentación", PRESENTACIONES, index=idx_pres)
                pres_peg = g4.selectbox("Encolada o Grapada", PRESENTACIONES2)
                
                p1, p2, p3, p4, = st.columns(4)
                t_perf = p1.selectbox("¿Tiene Perforaciones?", ["NO", "SI"], index=1 if datos_rec.get('perforaciones_detalle') != "NO" and datos_rec.get('perforaciones_detalle') else 0)
                perf_d = p1.text_area("Detalle Perforación", value=datos_rec.get('perforaciones_detalle', "")) if t_perf == "SI" else "NO"
                
                t_barr = p2.selectbox("¿Tiene Código de Barras?", ["NO", "SI"], index=1 if datos_rec.get('codigo_barras_detalle') != "NO" and datos_rec.get('codigo_barras_detalle') else 0)
                barr_d = p2.text_area("Detalle Barras", value=datos_rec.get('codigo_barras_detalle', "")) if t_barr == "SI" else "NO"
                
                t_num = p3.selectbox("¿Tiene Numeracion?", ["NO", "SI"])
                num_id = p3.text_input("Desde") if t_num == "SI" else "NO"
                num_fd = p3.text_input("Hasta") if t_num == "SI" else "NO"
                t_trans_f = p4.selectbox("¿Transportadora?", ["NO", "SI"], index=1 if datos_rec.get('transportadora_formas') == "SI" else 0)
                dest_f = p4.text_area("ciudad de destino", value=datos_rec.get('destino_formas', "")) if t_trans_f == "SI" else "NO"
                
                # --- SECCIÓN: DETALLES DE PARTES (PAPELES) ---
                lista_p = []
                rec_partes = datos_rec.get('detalles_partes_json', [])
                
                for i in range(1, partes + 1):
                    # Intentar extraer datos de la parte específica si existe en la repetición
                    p_data = rec_partes[i-1] if i <= len(rec_partes) else {}
                    
                    st.markdown(f"**PARTE {i}**")
                    d1, d2, d3, d4, d5, d6 = st.columns(6)
                    anc = d1.text_input(f"Ancho P{i}", key=f"a_{i}", value=p_data.get('anc', ""))
                    lar = d2.text_input(f"Largo P{i}", key=f"l_{i}", value=p_data.get('lar', ""))
                    pap = d3.text_input(f"Papel P{i}", key=f"p_{i}", value=p_data.get('papel', ""))
                    fon = d4.text_input(f"Color Fondo P{i}", key=f"f_{i}", value=p_data.get('color_fondo', "")) # Campo nuevo detectado en tu código
                    gra = d5.text_input(f"Gramos P{i}", key=f"g_{i}", value=p_data.get('gramos', ""))
                    tra = d6.text_input(f"Tráfico P{i}", key=f"t_{i}", value=p_data.get('trafico', ""))
                    
                    tf, tr = "N/A", "N/A"
                    if t == "FORMAS IMPRESAS":
                        t1, t2, t3 = st.columns(3)
                        tf = t1.text_input(f"Tintas Frente P{i}", key=f"tf_{i}", value=p_data.get('tf', ""))
                        tr = t2.text_input(f"Tintas Respaldo P{i}", key=f"tr_{i}", value=p_data.get('tr', ""))
                        obe = t3.text_input(f"Obs. Especial P{i}", key=f"obe_{i}")
                    
                    lista_p.append({"p":i, "anc":anc, "lar":lar, "papel":pap, "gramos":gra, "tf":tf, "tr":tr})
                
                obs = st.text_area("Observaciones Generales Formas", value=datos_rec.get('observaciones_formas', ""))

            else: # --- SECCIÓN: ROLLOS ---
                r1, r2, r3 = st.columns(3)
                mat = r1.text_input("Material Base", value=datos_rec.get('material', ""))
                gram = r2.number_input("Gramaje", 0, value=int(datos_rec.get('gramaje_rollos', 0)))
                ref_c = r3.text_input("Referencia Comercial", value=datos_rec.get('ref_comercial', ""))
                
                r4, r5, r6 = st.columns(3)
                cant_r = r4.number_input("Cantidad Rollos", 0, value=int(datos_rec.get('cantidad_rollos', 0)))
                
                cores = ["13MM", "19MM", "1 PULGADA", "40 MM", "2 PULGADAS", "3 PULGADAS"]
                idx_core = cores.index(datos_rec['core']) if datos_rec.get('core') in cores else 0
                core = r5.selectbox("Core / Centro", cores, index=idx_core)
                
                tra_opt = ["NO", "SI"]
                tra = r6.selectbox("¿Requiere Transportadora?", tra_opt, index=1 if datos_rec.get('ciudad de destino') != "NO" and datos_rec.get('ciudad de destino') else 0)
                c_tra = st.text_input("Especifique Ciudad de Destino", value=datos_rec.get('ciudad de destino', "")) if tra == "SI" else "NO"
                                        
                tf_r, tr_r = "N/A", "N/A"
                if t == "ROLLOS IMPRESOS":
                    ct1, ct2 = st.columns(2)
                    tf_r = ct1.text_input("Tintas Frente", value=datos_rec.get('tintas_frente_rollos', ""))
                    tr_r = ct2.text_input("Tintas Respaldo", value=datos_rec.get('tintas_respaldo_rollos', ""))
                
                r7, r8 = st.columns(2)
                ub = r7.number_input("Unidades x Bolsa", 0, value=int(datos_rec.get('unidades_bolsa', 0)))
                uc = r8.number_input("Unidades x Caja", 0, value=int(datos_rec.get('unidades_caja', 0)))
                obs = st.text_area("Observaciones Generales Rollos", value=datos_rec.get('observaciones_rollos', ""))

            # --- BOTÓN DE GUARDADO ---
            if st.form_submit_button("🚀 GUARDAR PLANIFICACIÓN"):
                if not op_input or not cli:
                    st.error("El número de OP y el Cliente son obligatorios.")
                else:
                    op_final = f"{prefijo}{op_input.upper()}"
                    
                    # Definición de ruta inicial automática
                    ruta_inicial = "IMPRESIÓN"
                    if t == "ROLLOS BLANCOS": ruta_inicial = "CORTE"
                    if t == "FORMAS BLANCAS": ruta_inicial = "COLECTORAS"
                    
                    payload = {
                        "op": op_final, "op_anterior": op_a, "cliente": cli, 
                        "vendedor": vend, "nombre_trabajo": trab, "tipo_orden": t, 
                        "proxima_area": ruta_inicial, "historial_procesos": []
                    }
                    
                    if "FORMAS" in t:
                        payload.update({
                            "cantidad_formas": int(cant_f), "num_partes": partes, 
                            "perforaciones_detalle": perf_d, "codigo_barras_detalle": barr_d, 
                            "transportadora_formas": t_trans_f, "destino_formas": dest_f,
                            "detalles_partes_json": lista_p, "presentacion": pres, 
                            "observaciones_formas": obs
                        })
                    else:
                        payload.update({
                            "material": mat, "gramaje_rollos": gram, "ref_comercial": ref_c, 
                            "cantidad_rollos": int(cant_r), "core": core, "ciudad de destino": c_tra,
                            "tintas_frente_rollos": tf_r, "tintas_respaldo_rollos": tr_r, 
                            "unidades_bolsa": int(ub), "unidades_caja": int(uc), "observaciones_rollos": obs
                        })
                    
                    try:
                        supabase.table("ordenes_planeadas").insert(payload).execute()
                        st.success(f"¡Éxito! Orden {op_final} registrada en sistema.")
                        st.session_state.sel_tipo = None
                        time.sleep(1.5); st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

# --- MÓDULO 4: PRODUCCIÓN (PANEL TÁCTIL) ---
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.markdown(f"<div class='title-area'>PANEL DE PRODUCCIÓN: {area_act}</div>", unsafe_allow_html=True)
    
    # Consultar máquinas ocupadas
    activos_data = supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data
    activos = {a['maquina']: a for a in activos_data}
    
    cols = st.columns(3)
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols[idx % 3]:
            if m in activos:
                tr = activos[m]
                st.markdown(f"<div class='card-produccion'>🟡 EN PROCESO<br>{m}<br>OP: {tr['op']}</div>", unsafe_allow_html=True)
                if st.button(f"✅ FINALIZAR TRABAJO", key=f"f_{m}"):
                    st.session_state.rep = tr
                    st.rerun()
            else:
                st.markdown(f"<div class='card-vacia'>⚪ DISPONIBLE<br>{m}</div>", unsafe_allow_html=True)
                ops_p = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
                if ops_p:
                    sel_op = st.selectbox("Seleccionar OP", [o['op'] for o in ops_p], key=f"s_{m}")
                    if st.button(f"🚀 INICIAR {m}", key=f"str_{m}"):
                        supabase.table("trabajos_activos").insert({
                            "maquina": m, "area": area_act, "op": sel_op, 
                            "hora_inicio": datetime.now().isoformat()
                        }).execute()
                        st.rerun()

    # Formulario de Cierre de Producción
    if st.session_state.rep:
        r = st.session_state.rep
        
        # --- CAMBIO QUIRÚRGICO: VALIDACIÓN DE ÁREA ---
        if r['area'] == area_act:
            st.divider()
            with st.form("cierre_tecnico_completo"):
                st.warning(f"### REGISTRO DE CIERRE: OP {r['op']} en {r['maquina']}")
                col_inf1, col_inf2 = st.columns(2)
                op_name = col_inf1.text_input("Nombre del Operario *")
                auxiliar = col_inf2.text_input("Auxiliar (opcional)")
                
                st.markdown("**DATOS TÉCNICOS DE SALIDA**")
                datos_c = {}
                
                if area_act == "IMPRESIÓN":
                    cc1, cc2, cc3 = st.columns(3)
                    datos_c['metros_lineales'] = cc1.number_input("Metros Impresos", 0)
                    datos_c['bobinas_impresas'] = cc2.number_input("Bobinas impresas", 0)
                    datos_c['desperdicio_kg'] = cc3.number_input("Desperdicio (Kg)", 0)
                    cc4, cc5 = st.columns(2)
                    datos_c['tintas_usadas'] = cc4.text_input("Tintas/Colores Usados")
                    datos_c['planchas_cliches'] = cc5.number_input("Planchas/Usadas", 0)
                
                elif area_act == "CORTE":
                    cc1, cc2, cc3 = st.columns(3)
                    datos_c['rollos_producidos'] = cc1.number_input("Rollos Finales", 0)
                    datos_c['varillas_sacadas'] = cc2.number_input("Varillas", 0)
                    datos_c['unidades_caja'] = cc1.number_input("unidades por caja", 0)
                    datos_c['cajas_sacadas'] = cc2.number_input("total cajas", 0)
                    datos_c['desperdicio_corte'] = cc3.number_input("Desperdicio (Kg)", 0)
                
                elif area_act == "COLECTORAS":
                    cc1, cc2 = st.columns(2)
                    datos_c['formas_colectadas'] = cc1.number_input("Cantidad Colectada", 0)
                    datos_c['unidades por caja'] = cc2.number_input("cantidad d eformas / caja", 0)
                    datos_c['cajas sacadas'] = cc2.number_input("total cajas", 0)
                    datos_c['desperdicio_hojas'] = cc2.number_input("Hojas Desperdicio", 0)
                
                obs_prod = st.text_area("Observaciones presentadas durante el proceso")

                if st.form_submit_button("🏁 REGISTRAR Y MOVER A SIGUIENTE ÁREA"):
                    if not op_name:
                        st.error("Debe ingresar el nombre del operario.")
                    else:
                        # --- CAMBIO QUIRÚRGICO: PARSEO DE FECHA PARA EVITAR TYPEERROR ---
                        hora_inicio_val = r['hora_inicio']
                        if isinstance(hora_inicio_val, str):
                            inicio = datetime.fromisoformat(hora_inicio_val.replace('Z', '+00:00'))
                        else:
                            inicio = hora_inicio_val
                            
                        fin = datetime.now()
                        duracion = str(fin-inicio).split('.')[0]
                        
                        # Obtener datos de la OP para determinar flujo
                        d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                        
                        # Lógica de Flujo Industrial
                        n_area = "FINALIZADO"
                        if "ROLLOS" in d_op['tipo_orden']:
                            if area_act == "IMPRESIÓN": n_area = "CORTE"
                        elif "FORMAS" in d_op['tipo_orden']:
                            if area_act == "IMPRESIÓN": n_area = "COLECTORAS"
                            elif area_act == "COLECTORAS": n_area = "ENCUADERNACIÓN"
                        
                        hist = d_op.get('historial_procesos') or []
                        hist.append({
                            "area": area_act, "maquina": r['maquina'], "operario": op_name, 
                            "auxiliar": auxiliar, "fecha": fin.strftime("%d/%m/%Y %H:%M"), 
                            "duracion": duracion, "datos_cierre": datos_c, "observaciones": obs_prod
                        })
                        
                        # Actualizar OP y Liberar Máquina
                        supabase.table("ordenes_planeadas").update({"proxima_area": n_area, "historial_procesos": hist}).eq("op", r['op']).execute()
                        supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()
                        
                        st.session_state.rep = None
                        st.success(f"Trabajo Finalizado. OP movida a: {n_area}")
                        time.sleep(1.5); st.rerun()
        else:
            # Si el área no coincide, limpiamos para no mostrar el formulario en el panel equivocado
            st.session_state.rep = None
