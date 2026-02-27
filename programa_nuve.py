import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import io
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V10.0", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES (MONITOR Y BOTONES) ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 15px; border-radius: 12px; text-align: center; color: #1B5E20; box-shadow: 0px 0px 15px rgba(0,230,118,0.5); margin-bottom:10px;}
    .card-parada { background-color: #FF5252; border: 2px solid #D32F2F; padding: 15px; border-radius: 12px; text-align: center; color: white; box-shadow: 0px 0px 15px rgba(255,82,82,0.5); margin-bottom:10px;}
    .card-turno { background-color: #FFD740; border: 2px solid #FFA000; padding: 15px; border-radius: 12px; text-align: center; color: #5D4037; margin-bottom:10px;}
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px; text-align: center; color: #9E9E9E; margin-bottom:10px;}
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# ==========================================
# MODALES TÉCNICOS (SIN OMISIONES)
# ==========================================

@st.dialog("Detalles de la Orden de Producción", width="large")
def mostrar_detalle_op(row):
    st.markdown(f"### 📄 Orden: {row['op']}")
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"👤 **Cliente:** {row.get('nombre_cliente')}")
        st.write(f"💼 **Vendedor:** {row.get('vendedor')}")
        st.write(f"🛠️ **Trabajo:** {row.get('trabajo')}")
    with col2:
        st.write(f"📄 **Material:** {row.get('material')}")
        st.write(f"📏 **Medida:** {row.get('ancho_medida')}")
        st.write(f"📦 **Cantidad:** {row.get('unidades_solicitadas')}")
    with col3:
        st.write(f"🎨 **Tintas:** {row.get('cant_tintas')}")
        st.write(f"📍 **Siguiente:** {row.get('proxima_area')}")
    st.info(f"📝 **Observaciones:** {row.get('observaciones')}")

@st.dialog("REPORTE TÉCNICO DE IMPRESIÓN", width="large")
def modal_reporte_impresion(t, m_s, tipo="FINAL"):
    st.subheader(f"Registro de Entrega {tipo}: {t['op']}")
    with st.form("f_reporte_kpi"):
        c1, c2, c3 = st.columns(3)
        metros = c1.number_input("Metros Impresos", 0)
        marca = c2.text_input("Marca de Papel")
        bobinas = c3.number_input("Cantidad Bobinas", 0)
        
        c4, c5, c6 = st.columns(3)
        n_img = c4.number_input("N° Imágenes", 0)
        gramaje = c5.text_input("Gramaje")
        ancho = c6.text_input("Ancho Bobina")
        
        c7, c8, c9 = st.columns(3)
        tinta = c7.text_input("Tinta Gastada")
        planchas = c8.number_input("Planchas Gastadas", 0)
        kilos_d = c9.number_input("Kilos Desperdicio", 0.0)
        
        m_desp = st.selectbox("Motivo Desp.", ["N/A", "MONTAJE", "REVENTÓN", "MÁQUINA", "OPERARIO"])
        operario = st.text_input("Nombre del Operario")
        obs = st.text_area("Observaciones del Turno")

        if st.form_submit_button(f"🚀 GUARDAR E INFORMAR {tipo}"):
            if operario:
                h_ini_str = t.get('hora_inicio', datetime.now().strftime("%H:%M"))
                try: dur = str(datetime.now() - datetime.strptime(h_ini_str, "%H:%M"))
                except: dur = "0:00"
                
                # Inserción en Historial
                supabase.table("impresion").insert({
                    "op": t['op'], "maquina": m_s, "trabajo": t['trabajo'], "h_inicio": h_ini_str,
                    "h_fin": datetime.now().strftime("%H:%M"), "duracion": dur, "metros": metros,
                    "marca": marca, "bobinas": bobinas, "imagenes": n_img, "gramaje": gramaje,
                    "ancho": ancho, "tinta": tinta, "planchas": planchas, "kilos_desp": kilos_d,
                    "motivo_desp": m_desp, "operario": operario, "observaciones": obs, "tipo_entrega": tipo
                }).execute()
                
                if tipo == "FINAL":
                    sig = "CORTE" if t.get('tipo_acabado') == "RI" else "COLECTORAS"
                    supabase.table("ordenes_planeadas").update({"proxima_area": sig, "estado": "Terminado en Impresión"}).eq("op", t['op']).execute()
                else:
                    # Entrega parcial: la OP se libera de la máquina pero vuelve a 'Pendiente' para ser retomada
                    supabase.table("ordenes_planeadas").update({"estado": "Pendiente"}).eq("op", t['op']).execute()
                
                supabase.table("trabajos_activos").delete().eq("maquina", m_s).execute()
                st.success("Reporte registrado con éxito")
                st.rerun()
            else:
                st.error("El nombre del operario es obligatorio")

@st.dialog("🚨 REGISTRAR PARADA")
def modal_parada(t, m_s):
    with st.form("f_p"):
        motivo = st.selectbox("Motivo:", ["MECÁNICO", "ELÉCTRICO", "MATERIAL", "AJUSTE", "REVENTÓN"])
        if st.form_submit_button("DETENER MÁQUINA"):
            supabase.table("trabajos_activos").update({
                "estado_maquina": "PARADA", 
                "h_parada": datetime.now().strftime("%H:%M:%S")
            }).eq("maquina", m_s).execute()
            st.rerun()

# ==========================================
# NAVEGACIÓN PRINCIPAL
# ==========================================
menu = st.sidebar.radio("SISTEMA NUVE V10.0", [
    "🖥️ Monitor General (TV)", 
    "🔍 Seguimiento", 
    "📅 Planificación", 
    "🖨️ Impresión", 
    "✂️ Corte", 
    "📥 Colectoras", 
    "📕 Encuadernación"
])

# 1. MONITOR GENERAL
if menu == "🖥️ Monitor General (TV)":
    st.title("🏭 Monitor General de Producción")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    d = act[m]
                    est = d.get('estado_maquina', 'PRODUCIENDO')
                    clase = "card-produccion" if est == 'PRODUCIENDO' else "card-parada" if est == 'PARADA' else "card-turno"
                    lbl = "⚡ ACTIVA" if est == 'PRODUCIENDO' else "🚨 PARADA" if est == 'PARADA' else "🌙 ESPERA"
                    st.markdown(f"<div class='{clase}'><b>{m}</b><br><small>{lbl}</small><hr><b>{d['op']}</b><br><small>{d['trabajo']}</small></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'><b>{m}</b><br><small>LIBRE</small></div>", unsafe_allow_html=True)
    time.sleep(15); st.rerun()

# 2. SEGUIMIENTO
elif menu == "🔍 Seguimiento":
    st.title("🔍 Seguimiento de Pedidos")
    ops = supabase.table("ordenes_planeadas").select("*").neq("estado", "Finalizado").execute().data
    if ops:
        df = pd.DataFrame(ops)
        c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
        c1.write("**OP**"); c2.write("**TRABAJO**"); c3.write("**PROX. ÁREA**"); c4.write("**ACCIÓN**")
        for _, fila in df.iterrows():
            r1, r2, r3, r4 = st.columns([1, 2, 1, 1])
            r1.write(fila['op']); r2.write(fila['trabajo']); r3.write(fila['proxima_area'])
            if r4.button("🔎 Ver", key=f"s_{fila['op']}"): mostrar_detalle_op(fila)

# 3. PLANIFICACIÓN
elif menu == "📅 Planificación":
    st.title("📅 Ingreso de Órdenes")
    pref = st.selectbox("Tipo:", ["RI", "RB", "FRI", "FRB"])
    with st.form("f_plan"):
        c1, c2 = st.columns(2)
        op_n = c1.text_input("Número OP")
        trab = c2.text_input("Nombre Trabajo")
        cli = st.text_input("Cliente")
        vende = st.text_input("Vendedor")
        cant = st.number_input("Cantidad", 0)
        pArea = "IMPRESIÓN" if pref in ["RI", "FRI"] else "CORTE"
        if st.form_submit_button("🚀 REGISTRAR OP"):
            data = {"op": f"{pref}-{op_n}".upper(), "trabajo": trab, "nombre_cliente": cli, "vendedor": vende, "unidades_solicitadas": cant, "proxima_area": pArea, "tipo_acabado": pref, "estado": "Pendiente"}
            supabase.table("ordenes_planeadas").insert(data).execute()
            st.success("OP Guardada")

# 4. IMPRESIÓN (OPERATIVO AVANZADO)
elif menu == "🖨️ Impresión":
    st.title("🖨️ Operación de Impresión")
    act_list = supabase.table("trabajos_activos").select("*").eq("area", "IMPRESIÓN").execute().data
    act = {a['maquina']: a for a in act_list}
    cols_m = st.columns(4)
    for i, m in enumerate(MAQUINAS["IMPRESIÓN"]):
        lbl = f"⚪ {m}"
        if m in act:
            e = act[m].get('estado_maquina', 'PRODUCIENDO')
            lbl = f"🔴 {m}" if e == 'PARADA' else f"🟡 {m}" if e == 'TURNO_CERRADO' else f"🟢 {m}"
        if cols_m[i%4].button(lbl, key=f"im_{m}"): st.session_state.m_sel = m

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS["IMPRESIÓN"]:
        ms = st.session_state.m_sel
        st.divider()
        if ms not in act:
            st.subheader(f"Cargar en {ms}")
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", "IMPRESIÓN").eq("estado", "Pendiente").execute().data
            if ops:
                sel = st.selectbox("OP:", [o['op'] for o in ops])
                if st.button("▶️ INICIAR"):
                    d = next(o for o in ops if o['op'] == sel)
                    supabase.table("trabajos_activos").insert({"maquina": ms, "area": "IMPRESIÓN", "op": d['op'], "trabajo": d['trabajo'], "hora_inicio": datetime.now().strftime("%H:%M"), "tipo_acabado": d['tipo_acabado'], "estado_maquina": "PRODUCIENDO"}).execute()
                    supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d['op']).execute()
                    st.rerun()
        else:
            t = act[ms]
            est = t.get('estado_maquina', 'PRODUCIENDO')
            st.subheader(f"MAQ: {ms} | OP: {t['op']}")
            if est == "PRODUCIENDO":
                st.success("PRODUCIENDO ACTUALMENTE")
                c1, c2, c3, c4 = st.columns(4)
                if c1.button("🚨 PARADA"): modal_parada(t, ms)
                if c2.button("🌙 TURNO"): 
                    supabase.table("trabajos_activos").update({"estado_maquina": "TURNO_CERRADO"}).eq("maquina", ms).execute()
                    st.rerun()
                if c3.button("📦 PARCIAL"): modal_reporte_impresion(t, ms, "PARCIAL")
                if c4.button("🏁 FINALIZAR"): modal_reporte_impresion(t, ms, "FINAL")
            elif est == "PARADA":
                st.error(f"PARADA DESDE: {t.get('h_parada')}")
                if st.button("▶️ REANUDAR PRODUCCIÓN"):
                    supabase.table("trabajos_activos").update({"estado_maquina": "PRODUCIENDO", "h_parada": None}).eq("maquina", ms).execute()
                    st.rerun()
            elif est == "TURNO_CERRADO":
                st.warning("MODO ESPERA (TURNO)")
                if st.button("☀️ REANUDAR TURNO"):
                    supabase.table("trabajos_activos").update({"estado_maquina": "PRODUCIENDO"}).eq("maquina", ms).execute()
                    st.rerun()

# 5. RESTO DE ÁREAS (CORTE, COLECTORAS, ENCUADERNACIÓN)
elif menu in ["✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    a_nom = menu.split(" ")[1].upper()
    st.title(f"Área: {a_nom}")
    act_a = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", a_nom).execute().data}
    cols_a = st.columns(4)
    for i, m in enumerate(MAQUINAS[a_nom]):
        if cols_a[i%4].button(f"{'🔴' if m in act_a else '⚪'} {m}", key=f"a_{m}"): st.session_state.m_sel_a = m
    if "m_sel_a" in st.session_state and st.session_state.m_sel_a in MAQUINAS[a_nom]:
        ms = st.session_state.m_sel_a
        st.divider()
        if ms not in act_a:
            ops_a = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", a_nom).execute().data
            if ops_a:
                sel_a = st.selectbox("Cargar OP:", [o['op'] for o in ops_a])
                if st.button(f"INICIAR EN {ms}"):
                    d = next(o for o in ops_a if o['op'] == sel_a)
                    supabase.table("trabajos_activos").insert({"maquina": ms, "area": a_nom, "op": d['op'], "trabajo": d['trabajo'], "hora_inicio": datetime.now().strftime("%H:%M")}).execute()
                    st.rerun()
        else:
            st.info(f"Procesando: {act_a[ms]['op']}")
            if st.button("🏁 FINALIZAR ÁREA"):
                sig = "ENCUADERNACIÓN" if a_nom in ["CORTE", "COLECTORAS"] else "DESPACHO"
                supabase.table("ordenes_planeadas").update({"proxima_area": sig}).eq("op", act_a[ms]['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", ms).execute()
                st.rerun()
