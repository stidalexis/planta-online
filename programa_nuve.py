import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import io
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V8.5", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES (RESPETANDO TU DISEÑO) ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 15px; border-radius: 12px; text-align: center; color: #1B5E20; box-shadow: 0px 0px 15px rgba(0,230,118,0.5); margin-bottom:10px;}
    .card-parada { background-color: #FF5252; border: 2px solid #D32F2F; padding: 15px; border-radius: 12px; text-align: center; color: white; box-shadow: 0px 0px 15px rgba(255,82,82,0.5); margin-bottom:10px;}
    .card-turno { background-color: #FFD740; border: 2px solid #FFA000; padding: 15px; border-radius: 12px; text-align: center; color: #5D4037; margin-bottom:10px;}
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px; text-align: center; color: #9E9E9E; margin-bottom:10px;}
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

# --- VENTANA EMERGENTE (DETALLE OP - SAGRADA) ---
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

# --- MODALES TÉCNICOS IMPRESIÓN ---
@st.dialog("🚨 PARADA DE EMERGENCIA")
def modal_parada_emergencia(t, m_s):
    with st.form("f_p"):
        motivo = st.selectbox("Motivo", ["FALLA MECÁNICA", "FALLA ELÉCTRICA", "FALTA MATERIAL", "AJUSTE", "REVENTÓN"])
        obs = st.text_area("Notas")
        if st.form_submit_button("CONFIRMAR"):
            supabase.table("trabajos_activos").update({"estado_maquina": "PARADA", "h_parada": datetime.now().strftime("%H:%M:%S")}).eq("maquina", m_s).execute()
            st.rerun()

@st.dialog("📦 ENTREGA PARCIAL")
def modal_parcial(t, m_s):
    with st.form("f_parc"):
        cant = st.number_input("Cantidad enviada a siguiente área", min_value=1)
        if st.form_submit_button("REGISTRAR PARCIAL"):
            st.success(f"Parcial registrado: {cant}")
            st.rerun()

@st.dialog("🏁 FINALIZACIÓN IMPRESIÓN", width="large")
def modal_finalizar_total(t, m_s):
    with st.form("f_fin"):
        st.subheader("Datos de Cierre")
        c1, c2, c3 = st.columns(3)
        metros = c1.number_input("Metros Impresos", 0)
        bobinas = c2.number_input("Bobinas", 0)
        kilos = c3.number_input("Kilos Desp.", 0.0)
        operario = st.text_input("Nombre Operario")
        if st.form_submit_button("FINALIZAR OP"):
            if operario:
                dur = str(datetime.now() - datetime.strptime(t['hora_inicio'], "%H:%M"))
                supabase.table("impresion").insert({"op":t['op'], "maquina":m_s, "metros":metros, "kilos_desp":kilos, "operario":operario, "h_fin": datetime.now().strftime("%H:%M"), "duracion": dur}).execute()
                sig = "CORTE" if t.get('tipo_acabado') == "RI" else "COLECTORAS"
                supabase.table("ordenes_planeadas").update({"proxima_area": sig, "estado": "Pendiente"}).eq("op", t['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", m_s).execute()
                st.rerun()

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("SISTEMA NUVE V8.5", ["🖥️ Monitor General (TV)", "🔍 Seguimiento de Pedidos", "📅 Planificación (Ingreso OP)", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# 1. MONITOR GENERAL (TV)
if menu == "🖥️ Monitor General (TV)":
    st.title("🏭 Tablero de Control de Planta")
    try: act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    except: act = {}
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>ÁREA: {area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    d = act[m]
                    est = d.get('estado_maquina', 'PRODUCIENDO')
                    clase = "card-produccion" if est == 'PRODUCIENDO' else "card-parada" if est == 'PARADA' else "card-turno"
                    st.markdown(f"<div class='{clase}'><b>{m}</b><br><b>{d['op']}</b><br><small>{d['trabajo']}</small></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'><b>{m}</b><br><small>LIBRE</small></div>", unsafe_allow_html=True)
    time.sleep(15); st.rerun()

# 2. SEGUIMIENTO DE PEDIDOS (SAGRADA)
elif menu == "🔍 Seguimiento de Pedidos":
    st.title("🔍 Seguimiento de Órdenes")
    try:
        ops = supabase.table("ordenes_planeadas").select("*").neq("estado", "Finalizado").execute().data
        if ops:
            df = pd.DataFrame(ops)
            c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
            c1.write("**OP**"); c2.write("**TRABAJO**"); c3.write("**PROX. ÁREA**"); c4.write("**ACCIÓN**")
            for _, fila in df.iterrows():
                r1, r2, r3, r4 = st.columns([1, 2, 1, 1])
                r1.write(fila['op']); r2.write(fila['trabajo']); r3.write(fila['proxima_area'])
                if r4.button("🔎 Detalles", key=f"seg_{fila['op']}"): mostrar_detalle_op(fila)
    except: st.info("Sin órdenes activas.")

# 3. PLANIFICACIÓN (SAGRADA)
elif menu == "📅 Planificación (Ingreso OP)":
    st.title("📅 Registro de Nueva OP")
    tipo_op_sel = st.selectbox("TIPO DE PRODUCTO:", ["-- Seleccione --", "RI (Rollo Impreso)", "RB (Rollo Blanco)", "FRI (Forma Impresa)", "FRB (Forma Blanca)"])
    if tipo_op_sel != "-- Seleccione --":
        pref = tipo_op_sel.split(" ")[0]
        es_forma = pref in ["FRI", "FRB"]; es_impreso = pref in ["RI", "FRI"]
        with st.form("form_op"):
            st.markdown(f"<div class='title-area'>FORMULARIO: {tipo_op_sel}</div>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3); op_num = c1.text_input("NÚMERO DE OP"); vendedor = c2.text_input("VENDEDOR"); cliente = c3.text_input("CLIENTE"); trabajo = st.text_input("TRABAJO")
            pld = {"core": "N/A", "unidades_bolsa": 0, "unidades_caja": 0, "num_desde": "N/A", "num_hasta": "N/A", "copias": "N/A"}
            f1, f2, f3 = st.columns(3); material = f1.text_input("PAPEL"); medida = f2.text_input("MEDIDA"); cantidad = f3.number_input("CANTIDAD", min_value=0)
            if not es_forma:
                r1, r2, r3 = st.columns(3); pld["core"] = r1.selectbox("CORE", ["13MM", "19MM", "1 PULG", "3 PULG"]); pld["unidades_bolsa"] = r2.number_input("U. BOLSA", 0); pld["unidades_caja"] = r3.number_input("U. CAJA", 0)
                pArea = "IMPRESIÓN" if pref == "RI" else "CORTE"
            else:
                n1, n2, n3 = st.columns(3); pld["num_desde"], pld["num_hasta"] = n1.text_input("DESDE"), n2.text_input("HASTA"); pld["copias"] = n3.selectbox("COPIAS", ["1", "2", "3", "4"])
                pArea = "IMPRESIÓN" if pref == "FRI" else "COLECTORAS"
            tin_n, tin_c = (0, "N/A")
            if es_impreso:
                i1, i2 = st.columns(2); tin_n = i1.number_input("TINTAS", 0); tin_c = i2.text_input("COLORES")
            obs = st.text_area("OBSERVACIONES")
            if st.form_submit_button("🚀 REGISTRAR"):
                data = {"op": f"{pref}-{op_num}".upper(), "nombre_cliente": cliente, "trabajo": trabajo, "vendedor": vendedor, "tipo_acabado": pref, "material": material, "ancho_medida": medida, "unidades_solicitadas": cantidad, "cant_tintas": tin_n, "especificacion_tintas": tin_c, "proxima_area": pArea, "observaciones": obs, "estado": "Pendiente", **pld}
                supabase.table("ordenes_planeadas").insert(data).execute()
                st.success("OP Registrada"); st.balloons()

# 4. MÓDULO IMPRESIÓN (OPERATIVO CON DINÁMICA NUEVA)
elif menu == "🖨️ Impresión":
    st.title("🖨️ Área de Impresión")
    
    # Obtener trabajos activos en tiempo real
    act_list = supabase.table("trabajos_activos").select("*").eq("area", "IMPRESIÓN").execute().data
    act = {a['maquina']: a for a in act_list}
    
    # Dibujar botones de máquinas
    m_cols = st.columns(4)
    for i, m in enumerate(MAQUINAS["IMPRESIÓN"]):
        # Color del botón según estado
        label_btn = f"⚪ {m}"
        if m in act:
            est_m = act[m].get('estado_maquina', 'PRODUCIENDO')
            if est_m == 'PARADA': label_btn = f"🔴 {m} (PARADA)"
            elif est_m == 'TURNO_CERRADO': label_btn = f"🟡 {m} (ESPERA)"
            else: label_btn = f"🟢 {m} (ACTIVA)"
        
        if m_cols[i%4].button(label_btn, key=f"btn_imp_{m}"):
            st.session_state.m_sel = m

    # PANEL DE CONTROL DE LA MÁQUINA SELECCIONADA
    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS["IMPRESIÓN"]:
        ms = st.session_state.m_sel
        st.divider()
        st.subheader(f"🕹️ Panel de Control: {ms}")
        
        if ms not in act:
            # --- FLUJO DE INICIO ---
            st.info(f"La máquina {ms} está disponible.")
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", "IMPRESIÓN").eq("estado", "Pendiente").execute().data
            if ops:
                op_list = [f"{o['op']} | {o['trabajo']}" for o in ops]
                sel_op = st.selectbox("Seleccione Orden para Iniciar:", ["--"] + op_list)
                if st.button("▶️ INICIAR TRABAJO"):
                    if sel_op != "--":
                        op_id = sel_op.split(" | ")[0]
                        d = next(o for o in ops if o['op'] == op_id)
                        supabase.table("trabajos_activos").insert({
                            "maquina": ms, "area": "IMPRESIÓN", "op": d['op'], 
                            "trabajo": d['trabajo'], "hora_inicio": datetime.now().strftime("%H:%M"),
                            "tipo_acabado": d['tipo_acabado'], "estado_maquina": "PRODUCIENDO"
                        }).execute()
                        supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d['op']).execute()
                        st.rerun()
            else:
                st.warning("No hay órdenes pendientes para Impresión.")
        else:
            # --- FLUJO DE OPERACIÓN ACTIVA ---
            t = act[ms]
            est_actual = t.get('estado_maquina', 'PRODUCIENDO')
            
            st.markdown(f"**TRABAJANDO EN:** `{t['op']} - {t['trabajo']}`")
            st.write(f"⏱️ Hora de inicio: {t['hora_inicio']}")

            # 1. SI LA MÁQUINA ESTÁ PRODUCIENDO
            if est_actual == "PRODUCIENDO":
                st.success("✅ ESTADO: EN PRODUCCIÓN")
                c1, c2, c3, c4 = st.columns(4)
                
                if c1.button("🚨 PARADA DE EMERGENCIA", help="Detener por falla o ajuste"):
                    modal_parada_emergencia(t, ms)
                
                if c2.button("🌙 CIERRE DE TURNO", help="Pausar trabajo hasta el siguiente turno"):
                    supabase.table("trabajos_activos").update({"estado_maquina": "TURNO_CERRADO"}).eq("maquina", ms).execute()
                    st.rerun()
                
                if c3.button("📦 ENTREGA PARCIAL", help="Enviar una parte a corte sin cerrar la OP"):
                    modal_parcial(t, ms)
                
                if c4.button("🏁 FINALIZAR TODO", help="Cerrar OP y registrar metros/kilos"):
                    modal_finalizar_total(t, ms)

            # 2. SI LA MÁQUINA ESTÁ EN PARADA
            elif est_actual == "PARADA":
                st.error(f"🚨 MÁQUINA DETENIDA (Desde: {t.get('h_parada')})")
                st.info("Resuelva el suceso y presione el botón para continuar.")
                if st.button("▶️ REANUDAR PRODUCCIÓN", type="primary"):
                    # Cálculo de tiempo de parada opcional para el log
                    supabase.table("trabajos_activos").update({
                        "estado_maquina": "PRODUCIENDO", 
                        "h_parada": None
                    }).eq("maquina", ms).execute()
                    st.rerun()

            # 3. SI LA MÁQUINA ESTÁ EN CIERRE DE TURNO
            elif est_actual == "TURNO_CERRADO":
                st.warning("🌙 TRABAJO PAUSADO POR CIERRE DE TURNO")
                st.write("La máquina está esperando la reanudación del nuevo turno.")
                if st.button("☀️ REANUDAR TURNO / TRABAJO", type="primary"):
                    supabase.table("trabajos_activos").update({"estado_maquina": "PRODUCIENDO"}).eq("maquina", ms).execute()
                    st.rerun()

# 5. RESTO DE ÁREAS (MANTENIENDO TU ESTRUCTURA)
elif menu in ["✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area = menu.replace("✂️ ", "").replace("📥 ", "").replace("📕 ", "").upper()
    st.title(f"Área: {area}")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area).execute().data}
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS[area]):
        if cols[i%4].button(f"{'🔴' if m in act else '⚪'} {m}", key=f"btn_{m}"): st.session_state.m_sel = m
    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area]:
        ms = st.session_state.m_sel
        if ms not in act:
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area).eq("estado", "Pendiente").execute().data
            if ops:
                sel = st.selectbox("OP:", [o['op'] for o in ops])
                if st.button("▶️ INICIAR"):
                    d = next(o for o in ops if o['op'] == sel)
                    supabase.table("trabajos_activos").insert({"maquina": ms, "area": area, "op": d['op'], "trabajo": d['trabajo'], "hora_inicio": datetime.now().strftime("%H:%M")}).execute()
                    st.rerun()
        else:
            st.success(f"Trabajando: {act[ms]['op']}")
            if st.button("🏁 FINALIZAR"):
                # Aquí puedes integrar parámetros de corte después
                supabase.table("trabajos_activos").delete().eq("maquina", ms).execute()
                st.rerun()

