import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import io
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V7.5 - MONITOR", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES (UX/UI) ---
st.markdown("""
    <style>
    /* Estilo para máquinas ocupadas (VERDE) */
    .card-activa { 
        padding: 20px; border-radius: 15px; background-color: #2E7D32; 
        color: white; border: 2px solid #1B5E20; text-align: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2); margin-bottom: 15px;
    }
    /* Estilo para máquinas libres (GRIS) */
    .card-vacia { 
        padding: 20px; border-radius: 15px; background-color: #F5F5F5; 
        color: #9E9E9E; border: 1px dashed #BDBDBD; text-align: center;
        margin-bottom: 15px;
    }
    .op-text { font-size: 1.2rem; font-weight: bold; display: block; }
    .job-text { font-size: 0.9rem; opacity: 0.9; }
    .maquina-id { font-size: 1.4rem; font-weight: 800; border-bottom: 1px solid rgba(255,255,255,0.3); margin-bottom: 5px; }
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
@st.dialog("Detalle de la Orden", width="large")
def ventana_detalle_op(row):
    st.write(f"### 📄 {row['op']} - {row['trabajo']}")
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**Cliente:** {row['nombre_cliente']}")
        st.write(f"**Vendedor:** {row['vendedor']}")
        st.write(f"**Material:** {row['material']}")
    with c2:
        st.write(f"**Cantidad:** {row['unidades_solicitadas']}")
        st.write(f"**Área Sig:** {row['proxima_area']}")
        st.write(f"**Estado:** {row['estado']}")
    st.info(f"**Observaciones:** {row['observaciones']}")
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        pd.DataFrame([row]).to_excel(writer, index=False)
    st.download_button("📥 Descargar Excel", output.getvalue(), f"{row['op']}.xlsx", use_container_width=True)

# --- BARRA LATERAL ---
menu = st.sidebar.radio("MENÚ PRINCIPAL", [
    "🖥️ Monitor en Tiempo Real", 
    "🔍 Seguimiento de Pedidos",
    "📅 Planificación (Ventas)", 
    "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación",
    "📊 Historial KPI"
])

# ==========================================
# 1. MONITOR EN TIEMPO REAL (TV MODE)
# ==========================================
if menu == "🖥️ Monitor en Tiempo Real":
    st.title("🚀 Monitor de Producción")
    
    # --- LÓGICA DE AUTO-ROTACIÓN ---
    # Usamos session_state para que las pestañas cambien solas
    if "tab_index" not in st.session_state: st.session_state.tab_index = 0
    
    # Checkbox para activar/desactivar rotación automática
    auto_rotate = st.sidebar.toggle("🔄 Rotación Automática (TV Mode)", value=True)
    
    try:
        act_data = supabase.table("trabajos_activos").select("*").execute().data
        act = {a['maquina']: a for a in act_data}
    except: act = {}

    areas = list(MAQUINAS.keys())
    
    # Si la rotación está activa, seleccionamos el tab según el índice
    tabs = st.tabs(areas)
    
    for i, area in enumerate(areas):
        with tabs[i]:
            st.markdown(f"### ÁREA: {area}")
            cols = st.columns(4)
            for idx, m in enumerate(MAQUINAS[area]):
                with cols[idx % 4]:
                    if m in act:
                        d = act[m]
                        st.markdown(f"""
                            <div class='card-activa'>
                                <div class='maquina-id'>{m}</div>
                                <span class='op-text'>{d['op']}</span>
                                <span class='job-text'>{d['trabajo']}</span>
                                <div style='font-size:0.7rem; margin-top:5px;'>Desde: {d['hora_inicio']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                            <div class='card-vacia'>
                                <div class='maquina-id' style='border-bottom: 1px solid #ddd;'>{m}</div>
                                <span style='font-size:0.8rem;'>DISPONIBLE</span>
                            </div>
                            """, unsafe_allow_html=True)

    # Lógica de refresco para la pantalla
    if auto_rotate:
        time.sleep(10) # Tiempo que dura cada pestaña (10 segundos)
        st.session_state.tab_index = (st.session_state.tab_index + 1) % len(areas)
        st.rerun()

# ==========================================
# 2. SEGUIMIENTO DE PEDIDOS (VENTANA INDEPENDIENTE)
# ==========================================
elif menu == "🔍 Seguimiento de Pedidos":
    st.title("🔍 Seguimiento de Órdenes de Producción")
    try:
        ops = supabase.table("ordenes_planeadas").select("*").neq("estado", "Finalizado").execute().data
        if ops:
            df = pd.DataFrame(ops)
            st.dataframe(df[["op", "nombre_cliente", "trabajo", "proxima_area", "estado"]], use_container_width=True)
            
            st.divider()
            sel_op = st.selectbox("Seleccione OP para ver detalle completo:", [o['op'] for o in ops])
            if st.button("Ver Ficha Técnica"):
                fila = next(o for o in ops if o['op'] == sel_op)
                ventana_detalle_op(fila)
        else:
            st.info("No hay órdenes activas.")
    except Exception as e:
        st.error(f"Error: {e}")

# ==========================================
# 3. PLANIFICACIÓN (VENDEDORES) - IGUAL AL ANTERIOR
# ==========================================
elif menu == "📅 Planificación (Ventas)":
    st.title("📅 Ingreso de Nueva OP")
    with st.form("registro_op"):
        c1, c2 = st.columns(2)
        op_id = c1.text_input("Número OP")
        tipo = c2.selectbox("Tipo", ["RI", "RB", "FRI", "FRB"])
        cliente = st.text_input("Cliente")
        trabajo = st.text_input("Nombre del Trabajo")
        material = st.text_input("Material / Papel")
        cant = st.number_input("Cantidad", min_value=1)
        area_ini = "IMPRESIÓN" if "I" in tipo else ("CORTE" if tipo=="RB" else "COLECTORAS")
        
        if st.form_submit_button("Guardar"):
            res = supabase.table("ordenes_planeadas").insert({
                "op": f"{tipo}-{op_id}", "nombre_cliente": cliente, "trabajo": trabajo,
                "material": material, "unidades_solicitadas": cant, "proxima_area": area_ini,
                "tipo_acabado": tipo, "estado": "Pendiente"
            }).execute()
            st.success("Orden Guardada")

# ==========================================
# 4. MÓDULOS OPERATIVOS (REDISEÑADO)
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.title(f"Operación: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    
    m_cols = st.columns(4)
    for i, m in enumerate(MAQUINAS[area_act]):
        status = "🔴" if m in activos else "⚪"
        if m_cols[i%4].button(f"{status} {m}", key=f"op_{m}"):
            st.session_state.m_sel = m

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        ms = st.session_state.m_sel
        st.subheader(f"Gestión de Máquina: {ms}")
        
        if ms not in activos:
            # Iniciar
            pendientes = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).eq("estado", "Pendiente").execute().data
            if pendientes:
                op_sel = st.selectbox("Seleccionar OP:", [p['op'] for p in pendientes])
                if st.button("▶️ COMENZAR TRABAJO"):
                    d_op = next(p for p in pendientes if p['op'] == op_sel)
                    supabase.table("trabajos_activos").insert({
                        "maquina": ms, "area": area_act, "op": d_op['op'], "trabajo": d_op['trabajo'],
                        "hora_inicio": datetime.now().strftime("%H:%M")
                    }).execute()
                    supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d_op['op']).execute()
                    st.rerun()
        else:
            # Finalizar
            t = activos[ms]
            st.info(f"Ocupada con: {t['op']}")
            if st.button("🏁 TERMINAR"):
                # Lógica simple de flujo (puedes ampliarla)
                sig_area = "FINALIZADO"
                # Reglas de flujo según tipo
                if "I" in t['op'] and area_act == "IMPRESIÓN": sig_area = "CORTE" if "R" in t['op'] else "COLECTORAS"
                
                # Guardar en historial real de la base de datos
                supabase.table(normalizar(area_act)).insert({
                    "op": t['op'], "maquina": ms, "trabajo": t['trabajo'],
                    "h_inicio": t['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M")
                }).execute()
                
                supabase.table("ordenes_planeadas").update({"proxima_area": sig_area, "estado": "Pendiente" if sig_area != "FINALIZADO" else "Finalizado"}).eq("op", t['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", ms).execute()
                st.rerun()
