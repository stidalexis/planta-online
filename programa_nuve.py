import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE CONEXIÓN ---
# Asegúrate de tener estas credenciales en st.secrets
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="PLANTA INDUSTRIAL - PRUEBAS", page_icon="🏭")

# --- CSS PARA INTERFAZ TÁCTIL ---
st.markdown("""
    <style>
    .stButton > button { height: 60px; font-weight: bold; border-radius: 10px; font-size: 16px; border: 2px solid #1E88E5; }
    .card-proceso { padding: 15px; border-radius: 10px; background-color: #e8f5e9; border-left: 8px solid #2e7d32; margin-bottom: 5px; }
    .card-parada { padding: 15px; border-radius: 10px; background-color: #ffebee; border-left: 8px solid #c62828; margin-bottom: 5px; }
    .card-libre { padding: 15px; border-radius: 10px; background-color: #f5f5f5; border-left: 8px solid #9e9e9e; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": ["LINEA-01"]
}

# --- FUNCIÓN DE MONITOR DE ESTADO ---
def monitor_estado(area):
    st.write(f"### 📊 Monitor de Estado: {area}")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
    
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS[area]):
        with cols[i % 4]:
            if m in paradas:
                st.markdown(f"<div class='card-parada'>🚨 <b>{m}</b><br>PARADA: {paradas[m]['motivo']}</div>", unsafe_allow_html=True)
            elif m in activos:
                st.markdown(f"<div class='card-proceso'>⚙️ <b>{m}</b><br>OP: {activos[m]['op']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='card-libre'>⚪ <b>{m}</b><br>DISPONIBLE</div>", unsafe_allow_html=True)

# --- NAVEGACIÓN PRINCIPAL (SIN LOGIN) ---
menu = st.sidebar.radio("VENTANAS INDEPENDIENTES", ["IMPRESIÓN", "CORTE", "COLECTORAS", "ENCUADERNACIÓN", "METAS POR MÁQUINA", "HISTORIAL"])

# --- INTERFAZ DINÁMICA ---
st.title(f"Módulo: {menu}")

if menu in MAQUINAS.keys():
    monitor_estado(menu)
    st.divider()
    
    # Selector de máquina táctil
    st.write("#### 🔘 Toque una máquina para gestionar:")
    c_btn = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS[menu]):
        if c_btn[i % 4].button(m_btn, key=f"btn_{m_btn}", use_container_width=True):
            st.session_state.maq_seleccionada = m_btn

    if "maq_seleccionada" in st.session_state:
        m = st.session_state.maq_seleccionada
        st.subheader(f"⚙️ Gestión: {m}")
        
        # Obtener estados actuales de la DB
        act = supabase.table("trabajos_activos").select("*").eq("maquina", m).execute().data
        par = supabase.table("paradas_maquina").select("*").eq("maquina", m).is_("h_fin", "null").execute().data

        # 1. SI ESTÁ EN PARADA
        if par:
            st.error(f"MÁQUINA DETENIDA POR: {par[0]['motivo']}")
            if st.button("✅ REANUDAR PRODUCCIÓN"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().isoformat()}).eq("id", par[0]['id']).execute()
                st.rerun()

        # 2. SI ESTÁ LIBRE (SOLICITAR DATOS INICIALES)
        elif not act:
            with st.form("form_inicio"):
                st.write("📋 **DATOS DE INICIO DE TRABAJO**")
                op = st.text_input("Número de OP")
                tr = st.text_input("Nombre del Trabajo")
                if st.form_submit_button("▶️ INICIAR PRODUCCIÓN"):
                    if op and tr:
                        supabase.table("trabajos_activos").insert({"maquina": m, "op": op, "trabajo": tr, "area": menu}).execute()
                        st.rerun()
                    else:
                        st.warning("Debe ingresar OP y Trabajo")

        # 3. SI ESTÁ TRABAJANDO (MOSTRAR PARADA Y CIERRE TÉCNICO)
        else:
            datos_act = act[0]
            st.success(f"EN PRODUCCIÓN: OP {datos_act['op']} - {datos_act['trabajo']}")
            
            col_izq, col_der = st.columns(2)
            
            with col_izq:
                st.warning("⚠️ REGISTRAR PARADA")
                with st.form("form_parada"):
                    motivo = st.selectbox("Motivo de parada:", ["Mantenimiento", "Falla Mecánica", "Ajuste", "Limpieza", "Falta de Material", "Almuerzo"])
                    if st.form_submit_button("DETENER MÁQUINA"):
                        supabase.table("paradas_maquina").insert({"maquina": m, "op": datos_act['op'], "motivo": motivo, "usuario": "Operario"}).execute()
                        st.rerun()

            with col_der:
                st.info("🏁 DATOS TÉCNICOS FINALIZACIÓN")
                with st.form("form_cierre"):
                    res = {}
                    if menu == "IMPRESIÓN":
                        c1, c2 = st.columns(2)
                        res = {"papel": c1.text_input("Papel"), "ancho": c2.text_input("Ancho"), "gramaje": c1.text_input("Gramaje"), "tintas": c2.number_input("Tintas", 0), "medida": c1.text_input("Medida"), "metros": c2.number_input("Metros Finales", 0)}
                    elif menu == "CORTE":
                        c1, c2 = st.columns(2)
                        res = {"img_varilla": c1.number_input("Img x Varilla", 0), "medida": c2.text_input("Medida"), "total_varillas": c1.number_input("Total Varillas", 0), "rollos_cortados": c2.number_input("Rollos", 0), "unid_caja": c1.number_input("Unid/Caja", 0)}
                    elif menu == "COLECTORAS":
                        c1, c2 = st.columns(2)
                        res = {"papel": c1.text_input("Papel"), "medida_forma": c2.text_input("Medida Forma"), "unid_caja": c1.number_input("Unid/Caja", 0), "total_cajas": c2.number_input("Total Cajas", 0), "total_formas": c1.number_input("Total Formas", 0)}
                    elif menu == "ENCUADERNACIÓN":
                        c1, c2 = st.columns(2)
                        res = {"cant_formas": c1.number_input("Cant. Formas", 0), "material": c2.text_input("Material"), "medida": c1.text_input("Medida"), "unid_caja": c2.number_input("Unid/Caja", 0), "cant_final": c1.number_input("Cant. Final", 0), "presentacion": c2.text_input("Presentación")}

                    dk = st.number_input("Desperdicio (Kg)", 0.0)
                    obs = st.text_area("Notas Finales")

                    if st.form_submit_button("FINALIZAR Y GUARDAR HISTORIAL"):
                        res.update({
                            "op": datos_act['op'], "maquina": m, "trabajo": datos_act['trabajo'],
                            "h_inicio": datos_act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                            "desp_kg": dk, "obs": obs
                        })
                        supabase.table(menu.lower()).insert(res).execute()
                        supabase.table("trabajos_activos").delete().eq("id", datos_act['id']).execute()
                        st.rerun()

elif menu == "METAS POR MÁQUINA":
    st.subheader("🎯 Configuración de Objetivos")
    a_meta = st.selectbox("Área:", list(MAQUINAS.keys()))
    m_meta = st.selectbox("Máquina:", MAQUINAS[a_meta])
    val_meta = st.number_input("Meta (Unidades/Hora):", 0)
    if st.button("GUARDAR META"):
        supabase.table("metas_produccion").upsert({"maquina": m_meta, "meta_unidades": val_meta, "area": a_meta}).execute()
        st.success("Meta actualizada")

elif menu == "HISTORIAL":
    st.subheader("📂 Reportes de Producción")
    t_hist = st.selectbox("Seleccione Tabla:", ["impresion", "corte", "colectoras", "encuadernacion", "paradas_maquina"])
    df = pd.DataFrame(supabase.table(t_hist).select("*").execute().data)
    st.dataframe(df, use_container_width=True)
