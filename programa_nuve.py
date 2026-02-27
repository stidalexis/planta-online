import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import io
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V10.1", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ---
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

MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# ==========================================
# MODALES
# ==========================================

@st.dialog("Detalles de la Orden")
def mostrar_detalle_op(row):
    st.write(f"### OP: {row['op']}")
    st.write(f"**Cliente:** {row.get('nombre_cliente')}")
    st.write(f"**Trabajo:** {row.get('trabajo')}")
    st.write(f"**Cantidad:** {row.get('unidades_solicitadas')}")
    st.info(f"**Observaciones:** {row.get('observaciones')}")

@st.dialog("REPORTE TÉCNICO", width="large")
def modal_reporte_impresion(t, m_s, tipo="FINAL"):
    st.subheader(f"Entrega {tipo}: {t['op']}")
    with st.form("f_final"):
        c1, c2, c3 = st.columns(3)
        metros = c1.number_input("Metros", 0)
        marca = c2.text_input("Marca Papel")
        bobinas = c3.number_input("Bobinas", 0)
        c4, c5, c6 = st.columns(3)
        n_img = c4.number_input("Imágenes", 0)
        gramaje = c5.text_input("Gramaje")
        ancho = c6.text_input("Ancho")
        c7, c8, c9 = st.columns(3)
        tinta = c7.text_input("Tinta")
        planchas = c8.number_input("Planchas", 0)
        kilos_d = c9.number_input("Kilos Desp.", 0.0)
        operario = st.text_input("Operario")
        
        if st.form_submit_button("GUARDAR"):
            if operario:
                # Blindaje de datos
                data_insert = {
                    "op": str(t['op']), "maquina": str(m_s), "trabajo": str(t['trabajo']),
                    "h_inicio": str(t.get('hora_inicio', '00:00')), "h_fin": datetime.now().strftime("%H:%M"),
                    "duracion": "Cálculo en proceso", "metros": int(metros), "marca": str(marca),
                    "bobinas": int(bobinas), "imagenes": int(n_img), "gramaje": str(gramaje),
                    "ancho": str(ancho), "tinta": str(tinta), "planchas": int(planchas),
                    "kilos_desp": float(kilos_d), "operario": str(operario), "tipo_entrega": tipo
                }
                try:
                    supabase.table("impresion").insert(data_insert).execute()
                    if tipo == "FINAL":
                        sig = "CORTE" if t.get('tipo_acabado') == "RI" else "COLECTORAS"
                        supabase.table("ordenes_planeadas").update({"proxima_area": sig, "estado": "Terminado"}).eq("op", t['op']).execute()
                    else:
                        supabase.table("ordenes_planeadas").update({"estado": "Pendiente"}).eq("op", t['op']).execute()
                    
                    supabase.table("trabajos_activos").delete().eq("maquina", m_s).execute()
                    st.success("¡Guardado!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al insertar: {e}")
            else:
                st.warning("Nombre de operario requerido")

@st.dialog("🚨 PARADA")
def modal_parada(t, m_s):
    with st.form("f_p"):
        motivo = st.selectbox("Motivo", ["FALLA", "MATERIAL", "AJUSTE"])
        if st.form_submit_button("PARAR"):
            supabase.table("trabajos_activos").update({"estado_maquina": "PARADA", "h_parada": datetime.now().strftime("%H:%M")}).eq("maquina", m_s).execute()
            st.rerun()

# ==========================================
# MENÚ Y SECCIONES
# ==========================================
menu = st.sidebar.radio("SISTEMA NUVE V10.1", ["🖥️ Monitor General (TV)", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

if menu == "🖥️ Monitor General (TV)":
    st.title("Monitor de Planta")
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
                    st.markdown(f"<div class='{clase}'><b>{m}</b><br>{d['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'><b>{m}</b><br>LIBRE</div>", unsafe_allow_html=True)
    time.sleep(15); st.rerun()

elif menu == "🔍 Seguimiento":
    st.title("Seguimiento")
    ops = supabase.table("ordenes_planeadas").select("*").neq("estado", "Finalizado").execute().data
    if ops:
        for f in ops:
            c1, c2, c3 = st.columns([1,2,1])
            c1.write(f['op']); c2.write(f['trabajo'])
            if c3.button("🔎", key=f['op']): mostrar_detalle_op(f)

elif menu == "📅 Planificación":
    st.title("Ingreso OP")
    with st.form("f_plan"):
        op_n = st.text_input("Número OP")
        pref = st.selectbox("Tipo", ["RI", "RB", "FRI", "FRB"])
        trab = st.text_input("Trabajo")
        cant = st.number_input("Cantidad", 0)
        if st.form_submit_button("GUARDAR"):
            pArea = "IMPRESIÓN" if pref in ["RI", "FRI"] else "CORTE"
            data = {"op": f"{pref}-{op_n}".upper(), "trabajo": trab, "unidades_solicitadas": cant, "proxima_area": pArea, "tipo_acabado": pref}
            supabase.table("ordenes_planeadas").insert(data).execute()
            st.success("OK")

elif menu == "🖨️ Impresión":
    st.title("Impresión")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", "IMPRESIÓN").execute().data}
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS["IMPRESIÓN"]):
        lbl = f"⚪ {m}"
        if m in act:
            e = act[m].get('estado_maquina', 'PRODUCIENDO')
            lbl = f"🔴 {m}" if e == 'PARADA' else f"🟡 {m}" if e == 'TURNO_CERRADO' else f"🟢 {m}"
        if cols[i%4].button(lbl, key=f"im_{m}"): st.session_state.m_sel = m

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS["IMPRESIÓN"]:
        ms = st.session_state.m_sel
        if ms not in act:
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", "IMPRESIÓN").eq("estado", "Pendiente").execute().data
            if ops:
                sel = st.selectbox("OP:", [o['op'] for o in ops])
                if st.button("INICIAR"):
                    d = next(o for o in ops if o['op'] == sel)
                    supabase.table("trabajos_activos").insert({"maquina": ms, "area": "IMPRESIÓN", "op": d['op'], "trabajo": d['trabajo'], "hora_inicio": datetime.now().strftime("%H:%M"), "tipo_acabado": d['tipo_acabado']}).execute()
                    supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d['op']).execute()
                    st.rerun()
        else:
            t = act[ms]
            st.subheader(f"MÁQUINA {ms} | {t['op']}")
            est = t.get('estado_maquina', 'PRODUCIENDO')
            if est == "PRODUCIENDO":
                c1, c2, c3, c4 = st.columns(4)
                if c1.button("🚨 PARADA"): modal_parada(t, ms)
                if c2.button("🌙 TURNO"): 
                    supabase.table("trabajos_activos").update({"estado_maquina": "TURNO_CERRADO"}).eq("maquina", ms).execute()
                    st.rerun()
                if c3.button("📦 PARCIAL"): modal_reporte_impresion(t, ms, "PARCIAL")
                if c4.button("🏁 FINALIZAR"): modal_reporte_impresion(t, ms, "FINAL")
            else:
                if st.button("▶️ REANUDAR"):
                    supabase.table("trabajos_activos").update({"estado_maquina": "PRODUCIENDO"}).eq("maquina", ms).execute()
                    st.rerun()

elif menu in ["✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    a_nom = menu.split(" ")[1].upper()
    st.title(a_nom)
    act_a = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", a_nom).execute().data}
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS[a_nom]):
        if cols[i%4].button(f"{'🔴' if m in act_a else '⚪'} {m}", key=f"a_{m}"): st.session_state.m_sel_a = m
    if "m_sel_a" in st.session_state and st.session_state.m_sel_a in MAQUINAS[a_nom]:
        ms = st.session_state.m_sel_a
        if ms not in act_a:
            ops_a = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", a_nom).execute().data
            if ops_a:
                sel_a = st.selectbox("OP:", [o['op'] for o in ops_a])
                if st.button(f"INICIAR EN {ms}"):
                    d = next(o for o in ops_a if o['op'] == sel_a)
                    supabase.table("trabajos_activos").insert({"maquina": ms, "area": a_nom, "op": d['op'], "trabajo": d['trabajo'], "hora_inicio": datetime.now().strftime("%H:%M")}).execute()
                    st.rerun()
        else:
            if st.button("🏁 FINALIZAR"):
                sig = "ENCUADERNACIÓN" if a_nom in ["CORTE", "COLECTORAS"] else "DESPACHO"
                supabase.table("ordenes_planeadas").update({"proxima_area": sig}).eq("op", act_a[ms]['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", ms).execute()
                st.rerun()
