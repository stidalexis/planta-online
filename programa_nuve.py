import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import io
from fpdf import FPDF

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V31.0 - FULL INDUSTRIAL", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("Error de conexión a Base de Datos. Revisa los Secrets.")
    st.stop()

# --- ESTILOS CSS (DISEÑO TÁCTIL Y LIMPIO) ---
st.markdown("""
    <style>
    .stButton > button { height: 65px !important; border-radius: 12px; font-weight: bold; font-size: 18px !important; width: 100%; border: 2px solid #0D47A1; transition: 0.3s; }
    .stButton > button:hover { background-color: #0D47A1; color: white; }
    .title-area { background-color: #0D47A1; color: white; padding: 20px; border-radius: 15px; text-align: center; font-weight: bold; font-size: 26px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .card-produccion { background-color: #00E676; border: 3px solid #00C853; padding: 25px; border-radius: 20px; text-align: center; color: #000000 !important; font-weight: bold; font-size: 20px; margin-bottom: 15px; }
    .card-vacia { background-color: #FFFFFF; border: 2px dashed #BDBDBD; padding: 25px; border-radius: 20px; text-align: center; color: #757575 !important; font-size: 18px; margin-bottom: 15px; }
    .section-header { background-color: #E3F2FD; padding: 12px; border-radius: 10px; font-weight: bold; color: #0D47A1; margin-top: 20px; margin-bottom: 15px; border-left: 8px solid #0D47A1; font-size: 18px; }
    .metric-box { background-color: #ffffff; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; margin-bottom: 10px; color: #000000 !important; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES DE MAQUINARIA ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- MOTOR DE GENERACIÓN DE PDF ---
def generar_pdf_op(row):
    pdf = FPDF()
    pdf.add_page()
    
    # Header Estilo Corporativo
    pdf.set_fill_color(13, 71, 161)
    pdf.rect(0, 0, 210, 45, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 22)
    pdf.cell(0, 15, f"ORDEN DE PRODUCCION: {row['op']}", ln=True, align='C')
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"TRABAJO: {row['nombre_trabajo']}", ln=True, align='C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(25)
    
    # Bloque 1: Información Comercial
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, " 1. DATOS GENERALES Y COMERCIALES", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    
    cw = 95
    pdf.cell(cw, 8, f"Cliente: {row.get('cliente')}", border='B')
    pdf.cell(cw, 8, f" Vendedor: {row.get('vendedor')}", border='B', ln=True)
    pdf.cell(cw, 8, f"Tipo Orden: {row.get('tipo_orden')}", border='B')
    pdf.cell(cw, 8, f" Fecha Sistema: {row.get('created_at', '')[:10]}", border='B', ln=True)
    pdf.cell(0, 8, f"Referencia: {row.get('ref_comercial', 'N/A')}", border='B', ln=True)
    pdf.ln(8)

    # Bloque 2: Ficha Técnica de Materiales
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, " 2. ESPECIFICACIONES TECNICAS DE MONTAJE", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)

    if "FORMAS" in row.get('tipo_orden', ''):
        pdf.cell(cw, 8, f"Cantidad Total: {row.get('cantidad_formas')}", border='B')
        pdf.cell(cw, 8, f" Numero de Partes: {row.get('num_partes')}", border='B', ln=True)
        pdf.cell(cw, 8, f"Presentacion: {row.get('presentacion')}", border='B')
        pdf.cell(cw, 8, f" Perforacion: {row.get('perforaciones_detalle')}", border='B', ln=True)
        
        pdf.ln(4)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, "DESGLOSE POR PARTE (PAPEL Y TINTAS):", ln=True)
        pdf.set_font("Arial", '', 9)
        for p in row.get('detalles_partes_json', []):
            pdf.cell(0, 7, f"P{p['p']}: {p.get('papel')} {p.get('gramos')}g | {p.get('anc')}x{p.get('lar')} | TINTAS: F:{p.get('tf')} / R:{p.get('tr')}", ln=True, border='L')
    else:
        pdf.cell(cw, 8, f"Material: {row.get('material')}", border='B')
        pdf.cell(cw, 8, f" Gramaje: {row.get('gramaje_rollos')}", border='B', ln=True)
        pdf.cell(cw, 8, f"Core: {row.get('core')}", border='B')
        pdf.cell(cw, 8, f" Cantidad Rollos: {row.get('cantidad_rollos')}", border='B', ln=True)
        pdf.cell(cw, 8, f"Tintas Frente: {row.get('tintas_frente_rollos')}", border='B')
        pdf.cell(cw, 8, f" Tintas Respaldo: {row.get('tintas_respaldo_rollos')}", border='B', ln=True)
    
    pdf.ln(8)

    # Bloque 3: Trazabilidad de Planta
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, " 3. HISTORIAL DE PRODUCCION Y CIERRES", ln=True, fill=True)
    
    hist = row.get('historial_procesos', [])
    if not hist:
        pdf.set_font("Arial", 'I', 11)
        pdf.cell(0, 12, "Pendiente por iniciar procesos en planta.", ln=True)
    else:
        for h in hist:
            pdf.ln(2)
            pdf.set_font("Arial", 'B', 11)
            pdf.set_text_color(13, 71, 161)
            pdf.cell(0, 8, f">> AREA: {h['area']} - MAQUINA: {h['maquina']}", ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", '', 10)
            pdf.cell(60, 7, f"Operario: {h['operario']}", border=0)
            pdf.cell(50, 7, f"Duracion: {h['duracion']}", border=0)
            pdf.cell(0, 7, f"Fecha: {h['fecha']}", border=0, ln=True)
            
            datos = h.get('datos', {})
            if datos:
                pdf.set_fill_color(248, 248, 248)
                txt_datos = " | ".join([f"{k.replace('_',' ').upper()}: {v}" for k, v in datos.items() if k != 'obs'])
                pdf.multi_cell(0, 7, f"DATOS TECNICOS: {txt_datos}", fill=True, border='L')
                if 'obs' in datos and datos['obs']:
                    pdf.set_font("Arial", 'I', 9)
                    pdf.multi_cell(0, 6, f"OBSERVACIONES: {datos['obs']}", border='L')
    
    # Pie de página técnico
    pdf.ln(15)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 10, f"Generado por NUVE V31 - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", align='C')
    
    return bytes(pdf.output())

# ==========================================
# VENTANA EMERGENTE (MODAL) RADIOGRAFÍA
# ==========================================
@st.dialog("📋 RADIOGRAFÍA TÉCNICA DE PROCESOS", width="large")
def modal_detalle_op(row):
    st.markdown(f"## 🛠️ OP: {row['op']} — {row['nombre_trabajo']}")
    st.write(f"🏭 **Estado Logístico:** `{row['proxima_area']}`")
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='section-header'>👤 DATOS DEL CLIENTE</div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class='metric-box'>
        <b>Cliente:</b> {row.get('cliente')}<br>
        <b>Vendedor:</b> {row.get('vendedor')}<br>
        <b>Creado:</b> {row.get('created_at')[:10]}
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='section-header'>📐 FICHA TÉCNICA</div>", unsafe_allow_html=True)
        if "FORMAS" in row['tipo_orden']:
            st.markdown(f"""
            <div class='metric-box'>
            <b>Cant:</b> {row.get('cantidad_formas')}<br>
            <b>Partes:</b> {row.get('num_partes')}<br>
            <b>Presentación:</b> {row.get('presentacion')}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='metric-box'>
            <b>Material:</b> {row.get('material')}<br>
            <b>Gramaje:</b> {row.get('gramaje_rollos')}<br>
            <b>Core:</b> {row.get('core')}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div class='section-header'>📜 TRAZABILIDAD DE PLANTA</div>", unsafe_allow_html=True)
    hist = row.get('historial_procesos', [])
    if not hist:
        st.warning("No hay registros de operarios todavía.")
    else:
        for h in hist:
            with st.expander(f"✅ FINALIZADO EN {h['area']} — {h['maquina']}"):
                st.write(f"👤 **Operario:** {h['operario']} | ⏱️ **Tiempo:** {h['duracion']}")
                st.write("**Datos Técnicos Reportados:**")
                st.json(h.get('datos', {}))

    st.divider()
    pdf_bytes = generar_pdf_op(row)
    st.download_button(
        label="🖨️ Descargar Reporte de Producción (PDF)",
        data=pdf_bytes,
        file_name=f"RADIOGRAFIA_OP_{row['op']}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

# ==========================================
# ESTRUCTURA DE CONTROL
# ==========================================
if 'sel_tipo' not in st.session_state: st.session_state.sel_tipo = None
if 'rep' not in st.session_state: st.session_state.rep = None

with st.sidebar:
    st.title("🏭 NUVE V31.0")
    menu = st.radio("SISTEMA DE CONTROL:", 
                    ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])
    st.divider()
    st.info(f"Sesión: {datetime.now().strftime('%H:%M')}")

# ==========================================
# MÓDULO 1: MONITOR DE PLANTA
# ==========================================
if menu == "🖥️ Monitor":
    st.title("Monitor de Máquinas en Tiempo Real")
    act_data = supabase.table("trabajos_activos").select("*").execute().data
    act = {a['maquina']: a for a in act_data}
    
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    st.markdown(f"<div class='card-produccion'>{m}<br><small>OP: {act[m]['op']}</small></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'>{m}<br><small>LIBRE</small></div>", unsafe_allow_html=True)
    
    time.sleep(30)
    st.rerun()

# ==========================================
# MÓDULO 2: SEGUIMIENTO
# ==========================================
elif menu == "🔍 Seguimiento":
    st.title("Control de Órdenes")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if res:
        df = pd.DataFrame(res)
        
        # Filtro rápido
        search = st.text_input("Filtrar por OP o Cliente")
        if search:
            df = df[df['op'].str.contains(search.upper()) | df['cliente'].str.contains(search.upper())]

        st.divider()
        # Header de tabla personalizada
        h_cols = st.columns([1, 2, 2, 1.5, 1])
        headers = ["OP", "CLIENTE", "TRABAJO", "UBICACIÓN", "ACCIONES"]
        for col, h in zip(h_cols, headers): col.subheader(h)

        for index, row in df.iterrows():
            r_cols = st.columns([1, 2, 2, 1.5, 1])
            r_cols[0].write(row['op'])
            r_cols[1].write(row['cliente'])
            r_cols[2].write(row['nombre_trabajo'])
            color = "#FF9800" if row['proxima_area'] != "FINALIZADO" else "#4CAF50"
            r_cols[3].markdown(f"<b style='color:{color};'>{row['proxima_area']}</b>", unsafe_allow_html=True)
            if r_cols[4].button("👁️", key=f"v_{row['op']}"):
                modal_detalle_op(row.to_dict())
            st.divider()

# ==========================================
# MÓDULO 3: PLANIFICACIÓN (EL CORE)
# ==========================================
elif menu == "📅 Planificación":
    st.title("Ingreso de Nueva Orden")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📑 FORMAS IMPRESAS"): st.session_state.sel_tipo = "FORMAS IMPRESAS"
    if c2.button("📄 FORMAS BLANCAS"): st.session_state.sel_tipo = "FORMAS BLANCAS"
    if c3.button("🌀 ROLLOS IMPRESOS"): st.session_state.sel_tipo = "ROLLOS IMPRESOS"
    if c4.button("⚪ ROLLOS BLANCOS"): st.session_state.sel_tipo = "ROLLOS BLANCOS"

    if st.session_state.sel_tipo:
        t = st.session_state.sel_tipo
        with st.form("form_master", clear_on_submit=True):
            st.markdown(f"### 🖋️ Registro: {t}")
            
            f1, f2, f3 = st.columns(3)
            op_n = f1.text_input("NÚMERO DE OP (Requerido)").upper()
            cli = f2.text_input("CLIENTE")
            vend = f3.text_input("VENDEDOR")
            
            f4, f5 = st.columns([2, 1])
            trab = f4.text_input("NOMBRE DEL TRABAJO")
            ref_c = f5.text_input("REF. COMERCIAL / PO")

            if "FORMAS" in t:
                st.markdown("#### Especificaciones de Formas")
                g1, g2, g3 = st.columns(3)
                cant_f = g1.number_input("Cantidad Formas", 0)
                partes = g2.selectbox("Número de Partes", [1,2,3,4,5,6])
                pres = g3.selectbox("Presentación", ["LIBRETAS TAPADURA", "BLOCK LICOM", "HOJAS SUELTAS", "PAQUETES", "TACOS"])
                
                p1, p2 = st.columns(2)
                perf_d = p1.text_area("Detalle Perforación", "N/A")
                barr_d = p2.text_area("Detalle Barras / Numeración", "N/A")
                
                lista_p = []
                for i in range(1, partes + 1):
                    st.markdown(f"**PARTE {i}**")
                    d1, d2, d3, d4, d5, d6 = st.columns(6)
                    anc = d1.text_input("Ancho", key=f"a_{i}")
                    lar = d2.text_input("Largo", key=f"l_{i}")
                    pap = d3.text_input("Papel", key=f"p_{i}")
                    gra = d4.text_input("Gramos", key=f"g_{i}")
                    tf = d5.text_input("Tintas F", value="1x0", key=f"tf_{i}")
                    tr = d6.text_input("Tintas R", value="0x0", key=f"tr_{i}")
                    lista_p.append({"p":i, "anc":anc, "lar":lar, "papel":pap, "gramos":gra, "tf":tf, "tr":tr})
                obs = st.text_area("Observaciones Generales")

            else: # ROLLOS
                st.markdown("#### Especificaciones de Rollos")
                r1, r2, r3 = st.columns(3)
                mat = r1.text_input("Material Base")
                gram = r2.text_input("Gramaje")
                core = st.selectbox("Core / Centro", ["13MM", "19MM", "1 PULGADA", "40 MM", "2 PULGADAS", "3 PULGADAS"])
                
                r4, r5, r6 = st.columns(3)
                cant_r = r4.number_input("Cantidad Rollos", 0)
                tf_r = r5.text_input("Tintas Frente", value="1x0")
                tr_r = r6.text_input("Tintas Respaldo", value="0x0")
                
                r7, r8 = st.columns(2)
                ub = r7.number_input("Unidades x Bolsa", 0)
                uc = r8.number_input("Unidades x Caja", 0)
                obs = st.text_area("Observaciones de Empaque")

            if st.form_submit_button("🏁 GUARDAR Y ENVIAR A PLANTA"):
                if not op_n:
                    st.error("Error: La OP es obligatoria.")
                else:
                    # RUTA LÓGICA
                    ruta = "IMPRESIÓN"
                    if t == "ROLLOS BLANCOS": ruta = "CORTE"
                    if t == "FORMAS BLANCAS": ruta = "COLECTORAS"
                    
                    payload = {
                        "op": op_n, "cliente": cli, "vendedor": vend, "nombre_trabajo": trab,
                        "tipo_orden": t, "proxima_area": ruta, "ref_comercial": ref_c
                    }
                    
                    if "FORMAS" in t:
                        payload.update({
                            "cantidad_formas": int(cant_f), "num_partes": partes,
                            "perforaciones_detalle": perf_d, "codigo_barras_detalle": barr_d,
                            "detalles_partes_json": lista_p, "presentacion": pres, "observaciones_formas": obs
                        })
                    else:
                        payload.update({
                            "material": mat, "gramaje_rollos": gram, "cantidad_rollos": int(cant_r),
                            "core": core, "tintas_frente_rollos": tf_r, "tintas_respaldo_rollos": tr_r,
                            "unidades_bolsa": int(ub), "unidades_caja": int(uc), "observaciones_rollos": obs
                        })

                    try:
                        supabase.table("ordenes_planeadas").insert(payload).execute()
                        st.success(f"✅ Orden {op_n} enviada a {ruta}")
                        st.session_state.sel_tipo = None
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error en Base de Datos: {e}")

# ==========================================
# MÓDULOS DE PRODUCCIÓN (EL CORAZÓN OPERATIVO)
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.markdown(f"<div class='title-area'>PANEL DE OPERACIONES: {area_act}</div>", unsafe_allow_html=True)
    
    # Obtener trabajos activos en este momento
    activos_db = supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data
    activos = {a['maquina']: a for a in activos_db}
    
    # Cuadrícula de Máquinas
    cols = st.columns(3)
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols[idx % 3]:
            if m in activos:
                tr = activos[m]
                st.markdown(f"<div class='card-produccion'>🟡 {m}<br>OP: {tr['op']}</div>", unsafe_allow_html=True)
                if st.button(f"🏁 FINALIZAR {m}", key=f"f_{m}"):
                    st.session_state.rep = tr
                    st.rerun()
            else:
                st.markdown(f"<div class='card-vacia'>⚪ {m}<br>LIBRE</div>", unsafe_allow_html=True)
                ops_disp = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
                if ops_disp:
                    sel_op = st.selectbox("Cargar OP", [o['op'] for o in ops_disp], key=f"s_{m}")
                    if st.button(f"🚀 INICIAR {m}", key=f"str_{m}"):
                        supabase.table("trabajos_activos").insert({
                            "maquina": m, "area": area_act, "op": sel_op, 
                            "hora_inicio": datetime.now().isoformat()
                        }).execute()
                        st.rerun()

    # FORMULARIO DE CIERRE (EXTENDIDO)
    if st.session_state.rep:
        r = st.session_state.rep
        st.divider()
        with st.form("form_cierre_tecnico"):
            st.warning(f"### 📋 CIERRE TÉCNICO: OP {r['op']} en {r['maquina']}")
            op_nombre = st.text_input("Nombre del Operario Responsable *")
            
            # Dinámica de Cierre según el área
            if area_act == "IMPRESIÓN":
                c1, c2, c3 = st.columns(3)
                metros = c1.number_input("Metros Totales", 0)
                bobinas = c2.number_input("Bobinas Usadas", 0)
                desp = c3.number_input("Desperdicio (Kg)", 0.0)
                
                c4, c5 = st.columns(2)
                planchas = c4.number_input("Planchas / Clichés", 0)
                tinta = c5.number_input("Tinta Consumida (Kg)", 0.0)
                obs_t = st.text_area("Observaciones de Calidad / Máquina")
                datos_save = {"metros": metros, "bobinas": bobinas, "planchas": planchas, "tinta": tinta, "desperdicio": desp, "obs": obs_t}

            elif area_act == "CORTE":
                c1, c2, c3 = st.columns(3)
                rollos_f = c1.number_input("Total Rollos Finales", 0)
                cajas_f = c2.number_input("Total Cajas", 0)
                desp_c = c3.number_input("Desperdicio Corte (Kg)", 0.0)
                obs_t = st.text_area("Reporte de Novedades")
                datos_save = {"rollos_ok": rollos_f, "cajas": cajas_f, "desperdicio": desp_c, "obs": obs_t}

            elif area_act == "COLECTORAS":
                c1, c2 = st.columns(2)
                formas_f = c1.number_input("Total Formas Colectadas", 0)
                desp_f = c2.number_input("Hojas Desperdicio", 0)
                obs_t = st.text_area("Observaciones")
                datos_save = {"formas_ok": formas_f, "desp_hojas": desp_f, "obs": obs_t}
            
            else: # Encuadernación
                res_f = st.number_input("Unidades Terminadas", 0)
                obs_t = st.text_area("Notas Finales")
                datos_save = {"unidades": res_f, "obs": obs_t}

            if st.form_submit_button("🏁 REGISTRAR Y LIBERAR MÁQUINA"):
                if not op_nombre:
                    st.error("Error: Debe ingresar el nombre del operario.")
                else:
                    # Lógica de tiempos y rutas
                    inicio = datetime.fromisoformat(r['hora_inicio'])
                    fin = datetime.now()
                    duracion = str(fin - inicio).split('.')[0]
                    
                    d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                    
                    # RUTA DE FLUJO
                    next_a = "FINALIZADO"
                    if "ROLLOS" in d_op['tipo_orden'] and area_act == "IMPRESIÓN": next_a = "CORTE"
                    elif "FORMAS" in d_op['tipo_orden']:
                        if area_act == "IMPRESIÓN": next_a = "COLECTORAS"
                        elif area_act == "COLECTORAS": next_a = "ENCUADERNACIÓN"
                    
                    # Actualización de Historial (Append)
                    historial = d_op['historial_procesos'] if d_op['historial_procesos'] else []
                    historial.append({
                        "area": area_act, "maquina": r['maquina'], "operario": op_nombre,
                        "fecha": fin.strftime("%d/%m/%Y %H:%M"), "duracion": duracion,
                        "datos": datos_save
                    })
                    
                    # DB Updates
                    supabase.table("ordenes_planeadas").update({
                        "proxima_area": next_a, 
                        "historial_procesos": historial
                    }).eq("op", r['op']).execute()
                    
                    supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()
                    
                    st.session_state.rep = None
                    st.success("Cierre registrado con éxito.")
                    time.sleep(1)
                    st.rerun()
