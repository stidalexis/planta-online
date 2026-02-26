import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="NUVE V7.5 - SISTEMA INTEGRAL", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES (UX/UI) ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    .card-proceso { padding: 15px; border-radius: 12px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; margin-bottom: 10px; }
    .card-libre { padding: 15px; border-radius: 12px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; margin-bottom: 10px; }
    .title-area { background-color: #1A237E; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

def normalizar(t):
    for k, v in {"Í":"I","Ó":"O","Á":"A","É":"E","Ú":"U"," ":"_"}.items(): t = t.upper().replace(k,v)
    return t.lower()

# --- BARRA LATERAL ---
menu = st.sidebar.radio("SISTEMA NUVE V7.5", [
    "🖥️ Monitor General", 
    "📅 Planificación (Vendedores)", 
    "📊 Historial KPI", 
    "🖨️ Impresión", 
    "✂️ Corte", 
    "📥 Colectoras", 
    "📕 Encuadernación"
])

# ==========================================
# 1. MONITOR GENERAL
# ==========================================
if menu == "🖥️ Monitor General":
    st.title("🖥️ Tablero de Control en Tiempo Real")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    tabs = st.tabs(list(MAQUINAS.keys()))
    
    for i, area in enumerate(MAQUINAS.keys()):
        with tabs[i]:
            cols = st.columns(4)
            for idx, m in enumerate(MAQUINAS[area]):
                with cols[idx % 4]:
                    if m in act:
                        st.markdown(f"<div class='card-proceso'>⚙️ <b>{m}</b><br>{act[m]['op']}<br><small>{act[m]['trabajo']}</small></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='card-libre'>⚪ <b>{m}</b><br>LIBRE</div>", unsafe_allow_html=True)

# ==========================================
# 2. PLANIFICACIÓN (VENDEDORES) - DINÁMICO
# ==========================================
elif menu == "📅 Planificación (Vendedores)":
    st.title("📅 Registro de Nueva Orden de Producción")
    
    tipo_op_sel = st.selectbox("TIPO DE TRABAJO:", ["-- Seleccione --", "RI (Rollo Impreso)", "RB (Rollo Blanco)", "FRI (Forma Impresa)", "FRB (Forma Blanca)"])

    if tipo_op_sel != "-- Seleccione --":
        prefijo = tipo_op_sel.split(" ")[0]
        es_forma = prefijo in ["FRI", "FRB"]
        es_impreso = prefijo in ["RI", "FRI"]

        with st.form("form_registro_op"):
            st.markdown(f"<div class='title-area'>DETALLES TÉCNICOS: {tipo_op_sel}</div>", unsafe_allow_html=True)
            
            # BLOQUE 1: IDENTIFICACIÓN
            c1, c2, c3 = st.columns(3)
            op_num = c1.text_input("NÚMERO DE OP")
            vendedor = c2.text_input("VENDEDOR")
            if es_forma:
                cliente = c3.text_input("NOMBRE DEL CLIENTE")
                trab_nom = st.text_input("NOMBRE DEL TRABAJO")
            else:
                trab_nom = c3.text_input("NOMBRE DEL TRABAJO")
                cliente = "N/A"

            st.divider()

            # BLOQUE 2: ESPECIFICACIONES (DINÁMICO)
            f1, f2, f3 = st.columns(3)
            payload_especifico = {}

            if not es_forma: # ROLLOS
                tipo_papel = f1.text_input("TIPO DE PAPEL")
                medida = f2.text_input("MEDIDA SOLICITADA")
                cantidad = f3.number_input("CANTIDAD SOLICITADA", 0)
                
                a1, a2, a3 = st.columns(3)
                core = a1.selectbox("CORE", ["13MM", "19MM", "1 PULG", "2 PULG", "3 PULG", "40MM"])
                u_bolsa = a2.number_input("UNIDADES POR BOLSA", 0)
                u_caja = a3.number_input("UNIDADES POR CAJA", 0)
                
                payload_especifico = {"core": core, "unidades_bolsa": u_bolsa, "unidades_caja": u_caja}
                pArea = "IMPRESIÓN" if prefijo == "RI" else "CORTE"

            else: # FORMAS
                cantidad = f1.number_input("CANTIDAD", 0)
                medida = f2.text_input("MEDIDA")
                tipo_papel = f3.text_input("TIPO DE PAPEL")
                
                n1, n2, n3 = st.columns(3)
                num_d = n1.text_input("NUMERACIÓN DESDE")
                num_h = n2.text_input("NUMERACIÓN HASTA")
                copias = n3.selectbox("COPIAS", ["1", "2", "3", "4", "5", "6", "7"])
                
                b1, b2, b3 = st.columns(3)
                fondo = b1.text_input("FONDO DE COPIAS")
                traficos = b2.text_input("TRÁFICOS EN ORDEN")
                c_barras = b3.text_input("CÓDIGO DE BARRAS (TIPO O 'NO')")
                
                p1, p2 = st.columns(2)
                perforaciones = p1.text_input("PERFORACIONES")
                presentacion = p2.selectbox("PRESENTACIÓN", ["BLOCK TAPA DURA", "BLOCK NORMAL", "LICOM", "PAQUETES", "SUELTAS"])
                
                payload_especifico = {
                    "num_desde": num_d, "num_hasta": num_h, "copias": copias, "fondo_copias": fondo,
                    "traficos_orden": traficos, "codigo_barras": c_barras, "perforaciones": perforaciones,
                    "presentacion": presentacion
                }
                pArea = "IMPRESIÓN" if prefijo == "FRI" else "COLECTORAS"

            # BLOQUE 3: IMPRESIÓN (SOLO SI APLICA)
            cant_t, cuales_t, cara_i = 0, "N/A", "N/A"
            if es_impreso:
                st.divider()
                st.subheader("🎨 Configuración de Tintas")
                i1, i2, i3 = st.columns(3)
                cant_t = i1.number_input("CANTIDAD DE TINTAS", 0)
                cuales_t = i2.text_input("CUÁLES TINTAS")
                cara_i = i3.selectbox("CARA DE IMPRESIÓN", ["FRENTE", "RESPALDO", "AMBAS"])

            st.divider()
            obs = st.text_area("OBSERVACIONES")

            if st.form_submit_button("✅ CARGAR A PRODUCCIÓN"):
                if not op_num or not trab_nom:
                    st.error("Error: OP y Nombre de trabajo son obligatorios.")
                else:
                    final_payload = {
                        "op": f"{prefijo}-{op_num}".upper(), "nombre_cliente": cliente, "trabajo": trab_nom,
                        "vendedor": vendedor, "tipo_acabado": prefijo, "material": tipo_papel,
                        "ancho_medida": medida, "unidades_solicitadas": cantidad, "cant_tintas": cant_t,
                        "especificacion_tintas": cuales_t, "orientacion_impresion": cara_i,
                        "proxima_area": pArea, "observaciones": obs, **payload_especifico
                    }
                    supabase.table("ordenes_planeadas").insert(final_payload).execute()
                    st.success(f"OP registrada. Destino: {pArea}")
                    st.balloons()

# ==========================================
# 3. MÓDULOS OPERATIVOS (IMPRESIÓN, CORTE, ETC)
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}[menu]
    st.title(f"Área: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    cols_m = st.columns(4)
    
    for i, m_id in enumerate(MAQUINAS[area_act]):
        label = f"🔴 {m_id}" if m_id in activos else f"⚪ {m_id}"
        if cols_m[i % 4].button(label, key=f"btn_{m_id}"):
            st.session_state.m_sel = m_id

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m_actual = st.session_state.m_sel
        st.subheader(f"Máquina: {m_actual}")
        
        if m_actual not in activos:
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).eq("estado", "Pendiente").execute().data
            op_sel = st.selectbox("Iniciar OP:", ["--"] + [f"{o['op']} | {o['trabajo']}" for o in ops])
            if st.button("🚀 INICIAR"):
                if op_sel != "--":
                    d = [o for o in ops if o['op'] == op_sel.split(" | ")[0]][0]
                    supabase.table("trabajos_activos").insert({
                        "maquina": m_actual, "area": area_act, "op": d['op'], "trabajo": d['trabajo'],
                        "hora_inicio": datetime.now().strftime("%H:%M"), "vendedor": d['vendedor'],
                        "material": d['material'], "ancho_medida": d['ancho_medida'],
                        "unidades_solicitadas": d['unidades_solicitadas'], "tipo_acabado": d['tipo_acabado'],
                        "cant_tintas": d['cant_tintas'], "especificacion_tintas": d['especificacion_tintas']
                    }).execute()
                    supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d['op']).execute()
                    st.rerun()
        else:
            t_act = activos[m_actual]
            st.info(f"TRABAJANDO: {t_act['op']}")
            with st.form("cierre"):
                datos_kpi = {}
                if area_act == "IMPRESIÓN":
                    c1, c2 = st.columns(2); datos_kpi["metros_impresos"] = c1.number_input("Metros", 0.0); datos_kpi["bobinas"] = c2.number_input("Bobinas", 0)
                elif area_act == "CORTE":
                    c1, c2 = st.columns(2); datos_kpi["metros_finales"] = c1.number_input("Metros", 0.0); datos_kpi["total_rollos"] = c2.number_input("Rollos", 0)
                elif area_act == "COLECTORAS":
                    c1, c2 = st.columns(2); datos_kpi["total_cajas"] = c1.number_input("Cajas", 0); datos_kpi["total_formas"] = c2.number_input("Formas", 0)
                elif area_act == "ENCUADERNACIÓN":
                    c1, c2 = st.columns(2); datos_kpi["cant_final"] = c1.number_input("Cant Final", 0); datos_kpi["presentacion"] = c2.text_input("Empaque")

                st.divider()
                d_kg = st.number_input("Desperdicio (Kg)", 0.0)
                if st.form_submit_button("🏁 FINALIZAR"):
                    pref = t_act['op'].split("-")[0]
                    sig = "FINALIZADO"
                    if pref == "RI" and area_act == "IMPRESIÓN": sig = "CORTE"
                    elif pref == "FRI" and area_act == "IMPRESIÓN": sig = "COLECTORAS"
                    elif (pref == "FRI" or pref == "FRB") and area_act == "COLECTORAS": sig = "ENCUADERNACIÓN"
                    
                    hist = {
                        "op": t_act['op'], "maquina": m_actual, "trabajo": t_act['trabajo'], "vendedor": t_act['vendedor'],
                        "h_inicio": t_act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"), "desp_kg": d_kg, **datos_kpi
                    }
                    supabase.table(normalizar(area_act)).insert(hist).execute()
                    supabase.table("ordenes_planeadas").update({"proxima_area": sig, "estado": "Pendiente" if sig != "FINALIZADO" else "Finalizado"}).eq("op", t_act['op']).execute()
                    supabase.table("trabajos_activos").delete().eq("id", t_act['id']).execute()
                    st.rerun()

# ==========================================
# 4. HISTORIAL KPI
# ==========================================
elif menu == "📊 Historial KPI":
    st.title("📊 Análisis de Históricos")
    tabs = st.tabs(["Impresión", "Corte", "Colectoras", "Encuadernación"])
    for i, t_name in enumerate(["impresion", "corte", "colectoras", "encuadernacion"]):
        with tabs[i]:
            data = supabase.table(t_name).select("*").order("fecha_fin", desc=True).execute().data
            if data: st.dataframe(pd.DataFrame(data), use_container_width=True)
