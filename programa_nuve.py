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

    /* ESTILO BITÁCORA MEJORADA V2 */
    .log-card { background-color: #ffffff; border: 1px solid #dee2e6; border-left: 8px solid #1976D2; padding: 20px; border-radius: 10px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .log-title { color: #0D47A1; font-weight: bold; font-size: 18px; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    .log-meta { font-size: 14px; color: #555; margin-bottom: 12px; background: #f1f3f5; padding: 5px 10px; border-radius: 5px; display: inline-block; }
    .log-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; }
    .data-chip { background: #e3f2fd; padding: 8px; border-radius: 6px; border: 1px solid #bbdefb; font-size: 13px; color: #0D47A1; }
    .data-chip b { color: #000; display: block; font-size: 11px; text-transform: uppercase; margin-bottom: 2px; }
    .obs-box { margin-top: 12px; padding: 10px; background: #fffde7; border-radius: 5px; border-left: 4px solid #fbc02d; font-style: italic; font-size: 13px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}
PRESENTACIONES = ["LIBRETAS TAPADURA", "BLOCK LICOM", "HOJAS SUELTAS", "PAQUETES", "TACOS", "CAJAS", "ROLLOS"]

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
    
    es_formas = "FORMAS" in row.get('tipo_orden', '')
    
    try:
        if es_formas:
            # PLANTILLA DE FORMAS C&B [cite: 86]
            pdf.image("plantilla_formas.jpg", x=0, y=0, w=210, h=297)
            pdf.set_font("Arial", 'B', 10)
            pdf.text(175, 29, f"{row.get('op')}") # No. OP [cite: 87, 89]
            pdf.text(32, 48, f"{row.get('cliente')}") # Cliente [cite: 94]
            pdf.text(142, 48, f"{row.get('vendedor')}") # Vendedor [cite: 95]
            pdf.text(32, 59, f"{row.get('nombre_trabajo')}") # Nombre de la Forma [cite: 100]
            pdf.text(25, 68, f"{row.get('cantidad_formas')}") # Cantidad [cite: 99]
            pdf.text(76, 68, f"{row.get('num_partes')}") # # Partes [cite: 101]
            
            # Tabla de Papel [cite: 111]
            partes = row.get('detalles_partes_json', [])
            y_off = 104
            for p in partes[:6]:
                pdf.set_font("Arial", '', 8)
                pdf.text(24, y_off, f"{p.get('anc','')}")
                pdf.text(42, y_off, f"{p.get('lar','')}")
                pdf.text(62, y_off, f"{p.get('papel','')}")
                pdf.text(112, y_off, f"{p.get('tf','')}")
                y_off += 7.2
        else:
            # PLANTILLA DE ROLLOS C&B [cite: 12]
            pdf.image("plantilla_rollos.jpg", x=0, y=0, w=210, h=297)
            pdf.set_font("Arial", 'B', 10)
            pdf.text(175, 29, f"{row.get('op')}") # No. OP [cite: 13, 15]
            pdf.text(38, 52, f"{row.get('cliente')}") # Cliente/Ref [cite: 20]
            pdf.text(148, 52, f"{row.get('vendedor')}") # Vendedor [cite: 21]
            pdf.text(35, 68, f"{row.get('cantidad_rollos')}") # Cantidad [cite: 24]
            
            # Tabla técnica [cite: 26]
            pdf.text(22, 95, f"{row.get('material','')}")
            pdf.text(62, 95, f"{row.get('gramaje_rollos','')}")
            pdf.text(158, 95, f"{row.get('core','')}")
            pdf.text(82, 111, f"{row.get('tintas_frente_rollos','')}")
            
    except Exception as e:
        pdf.set_font("Arial", 'B', 12)
        pdf.text(10, 20, f"Error cargando plantilla JPG: {e}")

    return bytes(pdf.output())

# ==========================================
# VENTANA EMERGENTE (MODAL) RADIOGRAFÍA
# ==========================================
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
            📄 <b>Tipo:</b> {row['tipo_orden']}<br>
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

    st.markdown("<div class='section-header'>📜 BITÁCORA TÉCNICA DE PRODUCCIÓN</div>", unsafe_allow_html=True)
    hist = row.get('historial_procesos', [])
    if not hist:
        st.info("No hay registros de producción todavía.")
    else:
        for h in hist:
            datos_c = h.get('datos', {})
            chips_html = "".join([f"<div class='data-chip'><b>{k.replace('_',' ').upper()}</b>{v}</div>" for k, v in datos_c.items() if v and v != "N/A" and v != 0])
            
            st.markdown(f"""
            <div class='log-card'>
                <div class='log-title'>📍 {h['area']} — {h['maquina']}</div>
                <div class='log-meta'>👤 <b>{h['operario']}</b> | ⏱️ <b>{h['duracion']}</b> | 📅 <b>{h['fecha']}</b></div>
                <div class='log-grid'>{chips_html}</div>
                {f"<div class='obs-box'><b>Observaciones:</b> {h['observaciones']}</div>" if h.get('observaciones') else ""}
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    try:
        pdf_bytes = generar_pdf_op(row)
        st.download_button(label="🖨️ Descargar Ficha Técnica C&B (PDF)", data=pdf_bytes, file_name=f"FICHA_TECNICA_OP_{row['op']}.pdf", mime="application/pdf", use_container_width=True)
    except Exception as e:
        st.error(f"Error generando PDF: {e}")

# ==========================================
# ESTRUCTURA DE MENÚ Y ESTADOS
# ==========================================
if 'sel_tipo' not in st.session_state: st.session_state.sel_tipo = None
if 'rep' not in st.session_state: st.session_state.rep = None

with st.sidebar:
    st.title("🏭 NUVE V31.0")
    menu = st.radio("SELECCIONE MÓDULO:", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])
    st.divider()
    st.caption("Conectado a Supabase Cloud")

# ==========================================
# MÓDULOS DE NAVEGACIÓN (LÓGICA ORIGINAL)
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
            st.subheader(f"Nueva Orden: {t}")
            f1, f2, f3 = st.columns(3)
            op_n = f1.text_input("OP Número *")
            op_a = f2.text_input("OP Anterior")
            cli = f3.text_input("Cliente *")
            f4, f5 = st.columns(2)
            vend = f4.text_input("Vendedor")
            trab = f5.text_input("Nombre Trabajo")

            if "FORMAS" in t:
                g1, g2 = st.columns(2)
                cant_f = g1.number_input("Cantidad Formas", 0)
                partes = g2.selectbox("Número de Partes", [1,2,3,4,5,6])
                p1, p2 = st.columns(2)
                t_perf = p1.selectbox("¿Tiene Perforaciones?", ["NO", "SI"])
                perf_d = p1.text_area("Detalle Perforación") if t_perf == "SI" else "NO"
                t_barr = p2.selectbox("¿Tiene Código de Barras?", ["NO", "SI"])
                barr_d = p2.text_area("Detalle Barras") if t_barr == "SI" else "NO"
                
                lista_p = []
                for i in range(1, partes + 1):
                    st.markdown(f"**PARTE {i}**")
                    d1, d2, d3, d4 = st.columns(4)
                    anc = d1.text_input(f"Ancho P{i}", key=f"a_{i}")
                    lar = d2.text_input(f"Largo P{i}", key=f"l_{i}")
                    pap = d3.text_input(f"Papel P{i}", key=f"p_{i}")
                    gra = d4.text_input(f"Gramos P{i}", key=f"g_{i}")
                    tf, tr = "N/A", "N/A"
                    if t == "FORMAS IMPRESAS":
                        t1, t2 = st.columns(2)
                        tf = t1.text_input(f"Tintas Frente P{i}", key=f"tf_{i}")
                        tr = t2.text_input(f"Tintas Respaldo P{i}", key=f"tr_{i}")
                    lista_p.append({"p":i, "anc":anc, "lar":lar, "papel":pap, "gramos":gra, "tf":tf, "tr":tr})
                pres = st.selectbox("Presentación", ["LIBRETAS TAPADURA", "BLOCK LICOM", "HOJAS SUELTAS", "PAQUETES", "TACOS"])
                obs = st.text_area("Observaciones Formas")

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
                r6, r7 = st.columns(2)
                ub = r6.number_input("Cant x Bolsa", 0)
                uc = r7.number_input("Cant x Caja", 0)
                obs = st.text_area("Observaciones Rollos")

            if st.form_submit_button("🚀 GUARDAR PLANIFICACIÓN"):
                ruta = "IMPRESIÓN"
                if t == "ROLLOS BLANCOS": ruta = "CORTE"
                if t == "FORMAS BLANCAS": ruta = "COLECTORAS"
                payload = {"op": op_n.upper(), "op_anterior": op_a, "cliente": cli, "vendedor": vend, "nombre_trabajo": trab, "tipo_orden": t, "proxima_area": ruta}
                if "FORMAS" in t:
                    payload.update({"cantidad_formas": int(cant_f), "num_partes": partes, "perforaciones_detalle": perf_d, "codigo_barras_detalle": barr_d, "detalles_partes_json": lista_p, "presentacion": pres, "observaciones_formas": obs})
                else:
                    payload.update({"material": mat, "gramaje_rollos": gram, "ref_comercial": ref_c, "cantidad_rollos": int(cant_r), "core": core, "tintas_frente_rollos": tf_r, "tintas_respaldo_rollos": tr_r, "unidades_bolsa": int(ub), "unidades_caja": int(uc), "observaciones_rollos": obs})
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.session_state.sel_tipo = None; st.success("Guardado!"); time.sleep(1); st.rerun()

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
                c_b1, c_b2 = st.columns(2)
                if c_b1.button(f"🛑 PARADA", key=f"p_{m}"):
                    st.toast(f"Parada registrada en {m}")
                if c_b2.button(f"✅ FINALIZAR", key=f"f_{m}"):
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
        st.divider()
        with st.form("cierre_tecnico_v31"):
            st.warning(f"### CIERRE TÉCNICO: OP {r['op']} en {r['maquina']}")
            op_name = st.text_input("Nombre del Operario *")
            datos_para_historial = {}

            if area_act == "IMPRESIÓN":
                c1, c2, c3 = st.columns(3)
                datos_para_historial['metros_impresos'] = c1.number_input("Metros Impresos", 0)
                datos_para_historial['bobinas'] = c2.number_input("Cant. Bobinas", 0)
                datos_para_historial['imgs_por_bobina'] = c3.number_input("Imágenes x Bobina", 0)
                obs_t = st.text_area("Observaciones del Proceso")
            elif area_act == "CORTE":
                c1, c2, c3 = st.columns(3)
                datos_para_historial['rollos_cortados'] = c2.number_input("Total Rollos Cortados", 0)
                obs_t = st.text_area("Observaciones de Corte")
            else:
                datos_para_historial['unidades_finales'] = st.number_input("Unidades Terminadas", 0)
                obs_t = st.text_area("Observaciones")

            if st.form_submit_button("🏁 REGISTRAR Y FINALIZAR"):
                if not op_name: st.error("Debe ingresar el operario")
                else:
                    inicio = datetime.fromisoformat(r['hora_inicio'])
                    fin = datetime.now()
                    duracion = str(fin - inicio).split('.')[0]
                    d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                    
                    n_area = "FINALIZADO"
                    if "ROLLOS" in d_op['tipo_orden'] and area_act == "IMPRESIÓN": n_area = "CORTE"
                    elif "FORMAS" in d_op['tipo_orden']:
                        if area_act == "IMPRESIÓN": n_area = "COLECTORAS"
                        elif area_act == "COLECTORAS": n_area = "ENCUADERNACIÓN"
                    
                    h = d_op.get('historial_procesos') or []
                    h.append({"area": area_act, "maquina": r['maquina'], "operario": op_name, "fecha": fin.strftime("%d/%m/%Y %H:%M"), "duracion": duracion, "datos": datos_para_historial, "observaciones": obs_t})
                    
                    supabase.table("ordenes_planeadas").update({"proxima_area": n_area, "historial_procesos": h}).eq("op", r['op']).execute()
                    supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()
                    st.session_state.rep = None; st.success("Finalizado!"); time.sleep(1); st.rerun()
