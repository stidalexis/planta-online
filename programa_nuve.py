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

    /* ESTILO PROFESIONAL PARA HISTORIAL EN PANTALLA */
    .historial-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        border-left: 5px solid #0D47A1;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .historial-header {
        display: flex;
        justify-content: space-between;
        font-weight: bold;
        color: #0D47A1;
        border-bottom: 1px solid #dee2e6;
        padding-bottom: 5px;
        margin-bottom: 10px;
    }
    .historial-tecnico {
        font-size: 0.9em;
        color: #333;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
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
    pdf.cell(0, 15, f"CERTIFICADO DE PRODUCCION - OP: {row['op']}", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"TRABAJO: {row['nombre_trabajo']}", ln=True, align='C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(20)
    
    # --- SECCIÓN 1: DATOS DE VENTA ---
    pdf.set_font("Arial", 'B', 11)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 8, " 1. INFORMACION GENERAL Y ORIGEN", ln=True, fill=True)
    pdf.set_font("Arial", '', 10)
    
    c1 = 100
    pdf.cell(c1, 7, f"Cliente: {row.get('cliente')}", border='B')
    pdf.cell(0, 7, f"Vendedor: {row.get('vendedor')}", border='B', ln=True)
    pdf.cell(c1, 7, f"Tipo de Orden: {row.get('tipo_orden')}", border='B')
    pdf.cell(0, 7, f"Fecha Creacion: {row.get('created_at', '')[:10]}", border='B', ln=True)
    pdf.ln(5)

    # --- SECCIÓN 2: ESPECIFICACIONES ---
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, " 2. ESPECIFICACIONES TECNICAS", ln=True, fill=True)
    pdf.set_font("Arial", '', 10)

    if "FORMAS" in row.get('tipo_orden', ''):
        pdf.cell(c1, 7, f"Cantidad: {row.get('cantidad_formas')}", border='B')
        pdf.cell(0, 7, f"Partes: {row.get('num_partes')}", border='B', ln=True)
        pdf.cell(c1, 7, f"Presentacion: {row.get('presentacion')}", border='B')
        pdf.cell(0, 7, f"Destino: {row.get('destino_formas', 'N/A')}", border='B', ln=True)
    else:
        pdf.cell(c1, 7, f"Material: {row.get('material')}", border='B')
        pdf.cell(0, 7, f"Gramaje: {row.get('gramaje_rollos')}g", border='B', ln=True)
        pdf.cell(c1, 7, f"Cantidad: {row.get('cantidad_rollos')}", border='B')
        pdf.cell(0, 7, f"Core: {row.get('core')}", border='B', ln=True)

    pdf.ln(5)

    # --- SECCIÓN 3: BITÁCORA TÉCNICA (EL CAMBIO SOLICITADO) ---
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, " 3. TRAZABILIDAD Y REGISTROS DE PLANTA", ln=True, fill=True)
    
    historial = row.get('historial_procesos', [])
    if not historial:
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 10, "Pendiente de procesamiento.", ln=True)
    else:
        for h in historial:
            pdf.ln(2)
            # Fila de Título de Área
            pdf.set_font("Arial", 'B', 10)
            pdf.set_fill_color(240, 245, 255)
            pdf.cell(0, 7, f" AREA: {h['area']} | MAQUINA: {h['maquina']}", ln=True, fill=True, border=1)
            
            # Fila de Responsables
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(65, 6, f"Operador: {h['operario']}", border='LR')
            pdf.cell(65, 6, f"Auxiliar: {h.get('auxiliar', 'N/A')}", border='R')
            pdf.cell(0, 6, f"Fecha: {h['fecha']}", border='R', ln=True)
            
            # Fila de Tiempos
            pdf.cell(130, 6, f"Duracion del Proceso: {h['duracion']}", border='LRB')
            pdf.cell(0, 6, "", border='RB', ln=True)

            # Datos Técnicos de Salida (JSON formateado)
            pdf.set_font("Arial", 'B', 8)
            pdf.set_fill_color(252, 252, 252)
            pdf.cell(0, 5, " DETALLES TECNICOS REGISTRADOS:", ln=True, fill=True, border='LR')
            
            pdf.set_font("Arial", '', 8)
            datos_c = h.get('datos_cierre', {})
            if datos_c:
                # Dibujamos los datos en formato de tabla pequeña
                for k, v in datos_c.items():
                    key_clean = k.replace('_', ' ').upper()
                    pdf.cell(45, 5, f" {key_clean}:", border='L')
                    pdf.cell(0, 5, f"{v}", border='R', ln=True)
            
            # Observaciones
            if h.get('observaciones'):
                pdf.set_font("Arial", 'I', 8)
                pdf.multi_cell(0, 5, f"OBSERVACIONES: {h['observaciones']}", border=1)
            else:
                pdf.cell(0, 1, "", ln=True, border='T')
            pdf.ln(2)

    pdf.ln(10)
    pdf.set_font("Arial", 'I', 7)
    pdf.cell(0, 10, f"DOCUMENTO OFICIAL NUVE - GENERADO AUTOMATICAMENTE - {datetime.now().strftime('%d/%m/%Y %H:%M')}", align='C')
    
    return bytes(pdf.output())

# --- DIALOG RADIOGRAFÍA ---
@st.dialog("📋 RADIOGRAFÍA TÉCNICA DE LA ORDEN", width="large")
def modal_detalle_op(row):
    st.markdown(f"### OP: {row['op']} — {row['nombre_trabajo']}")
    st.write(f"🏭 **Estado en Planta:** `{row['proxima_area']}`")
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div class='section-header'>👤 DATOS GENERALES</div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class='metric-box'>
        👤 <b>Cliente:</b> {row.get('cliente')}<br>
        💼 <b>Vendedor:</b> {row.get('vendedor')}<br>
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
            📦 <b>Cantidad:</b> {row.get('cantidad_rollos')}
            </div>
            """, unsafe_allow_html=True)

    with col3:
        st.markdown("<div class='section-header'>⚙️ EXTRAS</div>", unsafe_allow_html=True)
        if "FORMAS" in row['tipo_orden']:
            st.markdown(f"""
            <div class='metric-box'>
            ✂️ <b>Perforación:</b> {row.get('perforaciones_detalle')}<br>
            🚚 <b>Transporte:</b> {row.get('transportadora_formas', 'NO')}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='metric-box'>
            🎨 <b>Tintas F:</b> {row.get('tintas_frente_rollos')}<br>
            🌀 <b>Core:</b> {row.get('core')}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div class='section-header'>📜 BITÁCORA DE PRODUCCIÓN PROFESIONAL</div>", unsafe_allow_html=True)
    hist = row.get('historial_procesos', [])
    if not hist:
        st.info("No hay registros de producción todavía.")
    else:
        for h in hist:
            # Diseño de tarjeta profesional para cada entrada del historial
            with st.container():
                st.markdown(f"""
                <div class='historial-card'>
                    <div class='historial-header'>
                        <span>✅ {h['area']} — {h['maquina']}</span>
                        <span>📅 {h['fecha']}</span>
                    </div>
                    <div class='historial-tecnico'>
                        <div>👤 <b>Operario:</b> {h['operario']}</div>
                        <div>👥 <b>Auxiliar:</b> {h.get('auxiliar', 'N/A')}</div>
                        <div>⏱️ <b>Tiempo Proceso:</b> {h['duracion']}</div>
                        <div>📝 <b>Obs:</b> {h.get('observaciones', 'Sin observaciones')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Mostrar datos de cierre en una tabla limpia en lugar de JSON
                if h.get('datos_cierre'):
                    with st.expander("📊 Ver Datos Técnicos de Salida"):
                        df_datos = pd.DataFrame(list(h['datos_cierre'].items()), columns=['Parámetro', 'Valor'])
                        df_datos['Parámetro'] = df_datos['Parámetro'].str.replace('_', ' ').str.upper()
                        st.table(df_datos)

    st.divider()
    pdf_bytes = generar_pdf_op(row)
    st.download_button(label="🖨️ Descargar Certificado de Producción (PDF)", data=pdf_bytes, file_name=f"CERTIFICADO_{row['op']}.pdf", mime="application/pdf", use_container_width=True)

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
    busqueda = st.text_input("🔎 Buscar por OP o Nombre de Trabajo").upper()
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if res:
        df = pd.DataFrame(res)
        if busqueda:
            df = df[
                df["op"].str.contains(busqueda, case=False, na=False) |
                df["nombre_trabajo"].str.contains(busqueda, case=False, na=False)
            ]
        st.download_button("📥 Excel General", to_excel_limpio(df, "GENERAL"), "Reporte_General_Nuve.xlsx")
        st.divider()
        h1, h2, h3, h4, h5, h6, h7, h8 = st.columns([1,2,2,1.5,1.5,1.5,1.5,1])

        h1.write("**OP**")
        h2.write("**Cliente**")
        h3.write("**Trabajo**")
        h4.write("**Tipo**")
        h5.write("**Status**")
        h6.write("**Fecha**")
        h7.write("**Cantidad**")
        h8.write("**Ver**")
        for index, row in df.iterrows():
            r1, r2, r3, r4, r5, r6, r7, r8 = st.columns([1,2,2,1.5,1.5,1.5,1.5,1])
            r1.write(row['op'])
            r2.write(row['cliente'])
            r3.write(row['nombre_trabajo'])
            r4.write(row['tipo_orden'])
            color = "#FF9800" if row['proxima_area'] != "FINALIZADO" else "#4CAF50"
            r5.markdown(f"<span style='color:{color}; font-weight:bold;'>{row['proxima_area']}</span>", unsafe_allow_html=True)
            r6.write(row.get("created_at","")[:10])

            if "FORMAS" in row['tipo_orden']:
                r7.write(row.get("cantidad_formas",""))
            else:
                r7.write(row.get("cantidad_rollos",""))
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


            if st.form_submit_button("🚀 GUARDAR PLANIFICACIÓN"):
                op_final = f"{prefijo}{op_input.upper()}"
                ruta_inicial = "IMPRESIÓN" if "ROLLOS" in t or "IMPRESAS" in t else "CORTE"
                
                payload = {
                    "op": op_final, "op_anterior": op_a, "cliente": cli, 
                    "vendedor": vend, "nombre_trabajo": trab, "tipo_orden": t, 
                    "proxima_area": ruta_inicial, "historial_procesos": []
                }
                
                if "FORMAS" in t:
                    payload.update({"cantidad_formas": int(cant_f), "num_partes": partes, "perforaciones_detalle": perf_d, "codigo_barras_detalle": barr_d, "transportadora_formas": t_trans_f, "destino_formas": dest_f, "detalles_partes_json": lista_p, "presentacion": pres, "observaciones_formas": obs})
                else:
                    payload.update({"material": mat, "gramaje_rollos": gram, "cantidad_rollos": int(cant_r), "core": core, "tintas_frente_rollos": tf_r, "unidades_bolsa": int(ub), "unidades_caja": int(uc), "observaciones_rollos": obs})
                
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.success(f"Orden {op_final} registrada.")
                st.session_state.sel_tipo = None
                time.sleep(1.5); st.rerun()

# --- MÓDULO 4: PRODUCCIÓN ---
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.markdown(f"<div class='title-area'>PANEL DE PRODUCCIÓN: {area_act}</div>", unsafe_allow_html=True)
    
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
                        supabase.table("trabajos_activos").insert({"maquina": m, "area": area_act, "op": sel_op, "hora_inicio": datetime.now().isoformat()}).execute()
                        st.rerun()

    if st.session_state.rep:
        r = st.session_state.rep
        st.divider()
        with st.form("cierre_tecnico_completo"):
            st.warning(f"### REGISTRO DE CIERRE: OP {r['op']}")
            op_name = st.text_input("Nombre del Operario *")
            auxiliar = st.text_input("Auxiliar")
            datos_c = {}
            
            if area_act == "IMPRESIÓN":
                c1, c2, c3 = st.columns(3)
                datos_c['marca_papel_i'] = c1.text_input("marca de papel",)
                datos_c['medida_papel'] = c2.number_input("medida de papel", 0)
                datos_c['metros_impresos'] = c3.number_input("Metros", 0)
                datos_c['imagenes_impresas'] = c1.number_input("n° imagenes ", 0)
                datos_c['desperdicio_kg'] = c2.number_input("Desperdicio Kg", 0)
                datos_c['planchas'] = c3.number_input("planchas gastadas", 0)
            elif area_act == "CORTE":
                c1, c2, c3 = st.columns(3)
                datos_c['tipo_papel'] = c1.text_input("tipo de papel",)
                datos_c['marca_papel_c'] = c2.text_input("marca de papel",)
                datos_c['ancho_bobina'] = c3.number_input("ancho de bobina", 0)
                datos_c['imagenes_corte'] = c1.number_input("imagenes/bobina", 0)
                datos_c['gramos_bobinas'] = c2.number_input("gramaje de bobina", 0)
                datos_c['rollos_finales'] = c3.number_input("total Rollos cortados", 0)
                datos_c['varillas_finales'] = c1.number_input("total varillas", 0)
                datos_c['cajas_totales'] = c2.number_input("Cajas empacadas", 0)
                datos_c['desperdicio'] = c3.number_input("total desperdicio", 0)
                
            elif area_act == "COLECTORAS":
                c1, c2, c3 = st.columns(3) 
                datos_c['tipo_papel'] = c1.text_input("tipo de papel",)
                datos_c['formas_colectadas'] = c2.number_input("total formas colectadas", 0)
                datos_c['partes'] = c3.number_input("total partes colecatdas", 0)
                datos_c['cajas_empacadas'] = c1.number_input("total cajas empacadas", 0)
                datos_c['formas_dañadas'] = c2.number_input("formas dañadas", 0)
                datos_c['tipo_pegado'] = c3.text_input("que tipo de pegue lleva",)

            elif area_act == "ENCUADERNACIÓN":
                c1, c2, c3 = st.columns(3)
                datos_c['tipo_presentacion'] = c1.text_input("precetacion final",)
                datos_c['unidades_caja'] = c2.text_input("cantidad por caja",)
                datos_c['total_cajas'] = c3.number_input("total cajas empacadas", 0)
                datos_c['tipo_pegado'] = c1.text_input("lado de pegado",)
                datos_c['desperdicio'] = c2.number_input("cantidad hojas dañadas", 0)
                datos_c['total_formas'] = c3.number_input("total formas procesadas", 0)
                 
            obs_prod = st.text_area("Observaciones de producción / saldos ")

            if st.form_submit_button("🏁 FINALIZAR Y MOVER"):
                
                if op_name:
                    inicio_raw = r['hora_inicio']

                    # Convertir correctamente venga como string o datetime
                    if isinstance(inicio_raw, str):
                        inicio = datetime.fromisoformat(inicio_raw.replace("Z", "+00:00"))
                    else:
                        inicio = inicio_raw

                    fin = datetime.now(inicio.tzinfo) if inicio.tzinfo else datetime.now()

                    duracion = str(fin - inicio).split('.')[0]
                    
                    d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                    n_area = "FINALIZADO"
                    if "ROLLOS" in d_op['tipo_orden'] and area_act == "IMPRESIÓN": n_area = "CORTE"
                    elif "FORMAS" in d_op['tipo_orden']:
                        if area_act == "IMPRESIÓN": n_area = "COLECTORAS"
                        elif area_act == "COLECTORAS": n_area = "ENCUADERNACIÓN"
                    
                    hist = d_op.get('historial_procesos') or []
                    hist.append({"area": area_act, "maquina": r['maquina'], "operario": op_name, "auxiliar": auxiliar, "fecha": fin.strftime("%d/%m/%Y %H:%M"), "duracion": duracion, "datos_cierre": datos_c, "observaciones": obs_prod})
                    
                    supabase.table("ordenes_planeadas").update({"proxima_area": n_area, "historial_procesos": hist}).eq("op", r['op']).execute()
                    supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()
                    st.session_state.rep = None
                    st.rerun()


















