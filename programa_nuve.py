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

# --- ESTILOS VISUALES ORIGINALES + MEJORAS ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    .card-proceso { 
        padding: 15px; border-radius: 12px; background-color: #E8F5E9; 
        border-left: 8px solid #2E7D32; border-top: 1px solid #C8E6C9;
        border-right: 1px solid #C8E6C9; border-bottom: 1px solid #C8E6C9;
        margin-bottom: 15px; 
    }
    .card-libre { 
        padding: 15px; border-radius: 12px; background-color: #F5F5F5; 
        border-left: 8px solid #9E9E9E; text-align: center; color: #757575; 
        margin-bottom: 15px; 
    }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
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

# --- VENTANA EMERGENTE (MODAL) ---
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
        st.write(f"Core/Copias: {row.get('core') if row.get('core') != 'N/A' else row.get('copias')}")

    st.info(f"📝 **Observaciones:** {row.get('observaciones')}")
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        pd.DataFrame([row]).to_excel(writer, index=False)
    st.download_button("📥 DESCARGAR EXCEL", output.getvalue(), f"OP_{row['op']}.xlsx", use_container_width=True)

# --- BARRA LATERAL ---
menu = st.sidebar.radio("SISTEMA NUVE V7.5", [
    "🖥️ Monitor General (TV)", 
    "🔍 Seguimiento de Pedidos",
    "📅 Planificación (Ingreso OP)", 
    "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación",
    "📊 Historial KPI"
])

# ==========================================
# 1. MONITOR GENERAL (VISTA TOTAL DE PLANTA)
# ==========================================
if menu == "🖥️ Monitor General (TV)":
    st.title("🏭 Tablero de Control de Planta - Vista Total")
    
    # Estilo específico para el brillo verde y las tarjetas
    st.markdown("""
        <style>
        .card-activa-brillante { 
            padding: 15px; border-radius: 12px; 
            background-color: #00E676; /* Verde Brillante */
            border: 2px solid #00C853;
            box-shadow: 0px 0px 15px rgba(0, 230, 118, 0.5);
            margin-bottom: 15px; text-align: center; color: #1B5E20;
        }
        .card-vacia-monitor { 
            padding: 15px; border-radius: 12px; 
            background-color: #F5F5F5; border: 1px solid #E0E0E0;
            margin-bottom: 15px; text-align: center; color: #9E9E9E;
        }
        .text-maquina { font-size: 1.3rem; font-weight: 800; margin-bottom: 5px; display: block; }
        .text-op { font-size: 1.1rem; font-weight: 700; color: #000; display: block; }
        .text-trabajo { font-size: 0.85rem; font-weight: 500; display: block; line-height: 1.1; }
        </style>
    """, unsafe_allow_html=True)

    try:
        act_data = supabase.table("trabajos_activos").select("*").execute().data
        act = {a['maquina']: a for a in act_data}
    except:
        act = {}

    # Renderizamos cada área una tras otra
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>ÁREA: {area}</div>", unsafe_allow_html=True)
        cols = st.columns(4) # 4 columnas para que quepan más en pantalla
        
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    d = act[m]
                    st.markdown(f"""
                        <div class='card-activa-brillante'>
                            <span class='text-maquina'>{m}</span>
                            <span class='text-op'>{d['op']}</span>
                            <span class='text-trabajo'>{d['trabajo']}</span>
                            <hr style='margin: 8px 0; border: 0.5px solid #00C853;'>
                            <small>Inicio: {d.get('hora_inicio', '--:--')}</small>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                        <div class='card-vacia-monitor'>
                            <span class='text-maquina'>{m}</span>
                            <br>
                            <small>DISPONIBLE</small>
                        </div>
                    """, unsafe_allow_html=True)
    
    # Auto-refresco de datos cada 30 segundos para que gerencia vea cambios
    time.sleep(30)
    st.rerun()
# ==========================================
# 2. SEGUIMIENTO DE PEDIDOS (NUEVA VENTANA)
# ==========================================
elif menu == "🔍 Seguimiento de Pedidos":
    st.title("🔍 Seguimiento de Órdenes de Producción")
    try:
        ops = supabase.table("ordenes_planeadas").select("*").neq("estado", "Finalizado").execute().data
        if ops:
            df = pd.DataFrame(ops)
            st.write("Seleccione una orden para ver sus detalles técnicos y descargar el Excel:")
            c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
            c1.write("**OP**"); c2.write("**TRABAJO**"); c3.write("**PROX. ÁREA**"); c4.write("**ACCIÓN**")
            
            for _, fila in df.iterrows():
                r1, r2, r3, r4 = st.columns([1, 2, 1, 1])
                r1.write(fila['op'])
                r2.write(fila['trabajo'])
                r3.write(fila['proxima_area'])
                if r4.button("🔎 Detalles", key=f"seg_{fila['op']}"):
                    mostrar_detalle_op(fila)
        else: st.info("No hay órdenes pendientes.")
    except Exception as e: st.error(f"Error: {e}")

# ==========================================
# 3. PLANIFICACIÓN (INGRESO OP COMPLETO)
# ==========================================
elif menu == "📅 Planificación (Ingreso OP)":
    st.title("📅 Registro de Nueva Orden de Producción")
    tipo_op_sel = st.selectbox("TIPO DE PRODUCTO:", ["-- Seleccione --", "RI (Rollo Impreso)", "RB (Rollo Blanco)", "FRI (Forma Impresa)", "FRB (Forma Blanca)"])

    if tipo_op_sel != "-- Seleccione --":
        pref = tipo_op_sel.split(" ")[0]
        es_forma = pref in ["FRI", "FRB"]; es_impreso = pref in ["RI", "FRI"]

        with st.form("form_op_definitivo"):
            st.markdown(f"<div class='title-area'>FORMULARIO: {tipo_op_sel}</div>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            op_num = c1.text_input("NÚMERO DE OP")
            vendedor = c2.text_input("VENDEDOR")
            cliente = c3.text_input("NOMBRE DEL CLIENTE")
            trabajo = st.text_input("NOMBRE DEL TRABAJO")
            st.divider()

            pld = {"core": "N/A", "unidades_bolsa": 0, "unidades_caja": 0, "num_desde": "N/A", "num_hasta": "N/A", "copias": "N/A", "fondo_copias": "N/A", "traficos_orden": "N/A", "codigo_barras": "NO", "perforaciones": "N/A", "presentacion": "N/A"}
            f1, f2, f3 = st.columns(3)
            material = f1.text_input("TIPO DE PAPEL")
            medida = f2.text_input("MEDIDA")
            cantidad = f3.number_input("CANTIDAD TOTAL", min_value=0)

            if not es_forma: # ROLLOS
                r1, r2, r3 = st.columns(3)
                pld["core"] = r1.selectbox("CORE", ["13MM", "19MM", "1 PULG", "2 PULG", "3 PULG", "40MM"])
                pld["unidades_bolsa"], pld["unidades_caja"] = r2.number_input("U. BOLSA", 0), r3.number_input("U. CAJA", 0)
                pArea = "IMPRESIÓN" if pref == "RI" else "CORTE"
            else: # FORMAS
                n1, n2, n3 = st.columns(3)
                pld["num_desde"], pld["num_hasta"], pld["copias"] = n1.text_input("DESDE"), n2.text_input("HASTA"), n3.selectbox("COPIAS", ["1", "2", "3", "4", "5", "6", "7"])
                b1, b2, b3 = st.columns(3)
                pld["fondo_copias"], pld["traficos_orden"], pld["codigo_barras"] = b1.text_input("FONDO"), b2.text_input("TRÁFICOS"), b3.text_input("CÓDIGO B.")
                p1, p2 = st.columns(2)
                pld["perforaciones"], pld["presentacion"] = p1.text_input("PERFORACIONES"), p2.selectbox("PRESENTACIÓN", ["BLOCK TAPA DURA", "BLOCK NORMAL", "LICOM", "PAQUETES", "SUELTAS"])
                pArea = "IMPRESIÓN" if pref == "FRI" else "COLECTORAS"

            tin_n, tin_c, cara = 0, "N/A", "N/A"
            if es_impreso:
                st.subheader("Configuración de Impresión")
                i1, i2, i3 = st.columns(3)
                tin_n, tin_c, cara = i1.number_input("CANT. TINTAS", 0), i2.text_input("CUALES TINTAS"), i3.selectbox("CARA", ["FRENTE", "RESPALDO", "AMBAS"])

            obs = st.text_area("OBSERVACIONES")
            if st.form_submit_button("🚀 REGISTRAR E INVIAR A PRODUCCIÓN"):
                if op_num and trabajo:
                    final_data = {
                        "op": f"{pref}-{op_num}".upper(), "nombre_cliente": cliente, "trabajo": trabajo, "vendedor": vendedor, "tipo_acabado": pref, "material": material,
                        "ancho_medida": medida, "unidades_solicitadas": cantidad, "cant_tintas": tin_n, "especificacion_tintas": tin_c, "orientacion_impresion": cara,
                        "proxima_area": pArea, "observaciones": obs, "estado": "Pendiente", **pld
                    }
                    supabase.table("ordenes_planeadas").insert(final_data).execute()
                    st.success(f"✅ OP {pref}-{op_num} enviada a {pArea}"); st.balloons()

# ==========================================
# 4. MÓDULOS OPERATIVOS (REDISEÑO ROBUSTO)
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}[menu]
    st.title(f"Área: {area}")
    
    act_data = supabase.table("trabajos_activos").select("*").eq("area", area).execute().data
    activos = {a['maquina']: a for a in act_data}
    
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS[area]):
        label = f"{'🔴' if m in activos else '⚪'} {m}"
        if cols[i % 4].button(label, key=f"op_mod_{m}"): st.session_state.m_sel = m

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area]:
        m_s = st.session_state.m_sel
        st.subheader(f"Máquina: {m_s}")
        if m_s not in activos:
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area).eq("estado", "Pendiente").execute().data
            if ops:
                sel = st.selectbox("Seleccione OP:", ["--"] + [f"{o['op']} | {o['trabajo']}" for o in ops])
                if st.button("▶️ INICIAR"):
                    if sel != "--":
                        d = next(o for o in ops if o['op'] == sel.split(" | ")[0])
                        supabase.table("trabajos_activos").insert({
                            "maquina": m_s, "area": area, "op": d['op'], "trabajo": d['trabajo'], "nombre_cliente": d['nombre_cliente'],
                            "material": d['material'], "ancho_medida": d['ancho_medida'], "unidades_solicitadas": d['unidades_solicitadas'],
                            "tipo_acabado": d['tipo_acabado'], "cant_tintas": d['cant_tintas'], "core": d['core'], "copias": d['copias'], 
                            "hora_inicio": datetime.now().strftime("%H:%M")
                        }).execute()
                        supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d['op']).execute()
                        st.rerun()
        else:
            t = activos[m_s]
            st.info(f"TRABAJANDO: {t['op']} - {t['trabajo']}")
            if st.button("🏁 FINALIZAR TRABAJO"):
                sig = "FINALIZADO"
                if t['tipo_acabado'] == "RI" and area == "IMPRESIÓN": sig = "CORTE"
                elif t['tipo_acabado'] == "FRI" and area == "IMPRESIÓN": sig = "COLECTORAS"
                elif t['tipo_acabado'] in ["FRI","FRB"] and area == "COLECTORAS": sig = "ENCUADERNACIÓN"
                
                hist = {"op":t['op'],"maquina":m_s,"trabajo":t['trabajo'],"h_inicio":t['hora_inicio'],"h_fin":datetime.now().strftime("%H:%M")}
                supabase.table(normalizar(area)).insert(hist).execute()
                supabase.table("ordenes_planeadas").update({"proxima_area":sig,"estado":"Pendiente" if sig != "FINALIZADO" else "Finalizado"}).eq("op", t['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", m_s).execute()
                st.rerun()

# ==========================================
# 5. HISTORIAL KPI
# ==========================================
elif menu == "📊 Historial KPI":
    st.title("📊 Análisis de KPIs")
    t_names = ["impresion", "corte", "colectoras", "encuadernacion"]
    tabs = st.tabs([n.capitalize() for n in t_names])
    for i, tab in enumerate(tabs):
        with tab:
            data = supabase.table(t_names[i]).select("*").execute().data
            if data: st.dataframe(pd.DataFrame(data), use_container_width=True)


