import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="SISTEMA PLANTA - FINAL")

# --- CSS TÁCTIL ---
st.markdown("""
    <style>
    .stButton > button { height: 60px; font-weight: bold; border-radius: 10px; border: 2px solid #1E88E5; }
    .card-proceso { padding: 10px; border-radius: 10px; background-color: #e8f5e9; border-left: 8px solid #2e7d32; }
    .card-parada { padding: 10px; border-radius: 10px; background-color: #ffebee; border-left: 8px solid #c62828; }
    .card-libre { padding: 10px; border-radius: 10px; background-color: #f5f5f5; border-left: 8px solid #9e9e9e; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- FUNCIÓN PARA QUITAR TILDES ---
def normalizar(texto):
    reemplazos = {"Í": "I", "Ó": "O", "Á": "A", "É": "E", "Ú": "U"}
    for t, r in reemplazos.items():
        texto = texto.replace(t, r)
    return texto.lower()

# --- MONITOR ---
def monitor_estado(area):
    st.write(f"### 📊 Monitor: {area}")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
    
    n_cols = 5 if area == "ENCUADERNACIÓN" else 4
    cols = st.columns(n_cols)
    for i, m in enumerate(MAQUINAS[area]):
        with cols[i % n_cols]:
            if m in paradas:
                st.markdown(f"<div class='card-parada'>🚨 {m}</div>", unsafe_allow_html=True)
            elif m in activos:
                st.markdown(f"<div class='card-proceso'>⚙️ {m}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='card-libre'>⚪ {m}</div>", unsafe_allow_html=True)

# --- MENÚ ---
menu = st.sidebar.radio("VENTANAS", ["IMPRESIÓN", "CORTE", "COLECTORAS", "ENCUADERNACIÓN", "METAS", "HISTORIAL"])

if menu in MAQUINAS.keys():
    monitor_estado(menu)
    st.divider()
    
    c_btn = st.columns(5 if menu == "ENCUADERNACIÓN" else 4)
    for i, m_btn in enumerate(MAQUINAS[menu]):
        if c_btn[i % len(c_btn)].button(m_btn, key=f"btn_{m_btn}", use_container_width=True):
            st.session_state.maq_seleccionada = m_btn

    if "maq_seleccionada" in st.session_state:
        m = st.session_state.maq_seleccionada
        if m in MAQUINAS[menu]:
            st.subheader(f"⚙️ Gestión: {m}")
            
            act = supabase.table("trabajos_activos").select("*").eq("maquina", m).execute().data
            par = supabase.table("paradas_maquina").select("*").eq("maquina", m).is_("h_fin", "null").execute().data

            if par:
                if st.button("✅ REANUDAR PRODUCCIÓN"):
                    supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par[0]['id']).execute()
                    st.rerun()
            elif not act:
                with st.form("form_inicio"):
                    op = st.text_input("OP")
                    tr = st.text_input("Trabajo")
                    if st.form_submit_button("▶️ INICIAR"):
                        if op and tr:
                            supabase.table("trabajos_activos").insert({"maquina": m, "op": op, "trabajo": tr, "area": menu, "hora_inicio": datetime.now().strftime("%H:%M")}).execute()
                            st.rerun()
            else:
                datos_act = act[0]
                st.info(f"Produciendo: OP {datos_act['op']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🚨 REGISTRAR PARADA"):
                        supabase.table("paradas_maquina").insert({"maquina": m, "op": datos_act['op'], "motivo": "Parada Técnica", "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                        st.rerun()
                
                with col2:
                    with st.form("form_cierre"):
                        st.write("🏁 CIERRE TÉCNICO")
                        res = {}
                        if menu == "IMPRESIÓN":
                            res = {"papel": st.text_input("Papel"), "ancho": st.text_input("Ancho"), "gramaje": st.text_input("Gramaje"), "tintas": st.number_input("Tintas", 0), "metros": st.number_input("Metros", 0)}
                        elif menu == "CORTE":
                            res = {"img_varilla": st.number_input("Img x Varilla", 0), "medida": st.text_input("Medida"), "total_varillas": st.number_input("Total Varillas", 0), "rollos_cortados": st.number_input("Rollos", 0)}
                        elif menu == "COLECTORAS":
                            res = {"papel": st.text_input("Papel"), "medida_forma": st.text_input("Medida Forma"), "total_cajas": st.number_input("Total Cajas", 0), "total_formas": st.number_input("Total Formas", 0)}
                        elif menu == "ENCUADERNACIÓN":
                            res = {"cant_formas": st.number_input("Cant. Formas", 0), "material": st.text_input("Material"), "cant_final": st.number_input("Cant. Final", 0)}

                        dk = st.number_input("Desperdicio (Kg)", 0.0)
                        
                        if st.form_submit_button("GUARDAR"):
                            # PROCESO DE GUARDADO SEGURO
                            tabla_ok = normalizar(menu)
                            res.update({
                                "op": datos_act['op'], "maquina": m, "trabajo": datos_act['trabajo'],
                                "h_inicio": datos_act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                                "desp_kg": dk
                            })
                            try:
                                supabase.table(tabla_ok).insert(res).execute()
                                supabase.table("trabajos_activos").delete().eq("id", datos_act['id']).execute()
                                st.success("Guardado!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

elif menu == "METAS":
    st.write("Panel de Metas")
    # Lógica de metas aquí...

elif menu == "HISTORIAL":
    t_h = st.selectbox("Tabla:", ["impresion", "corte", "colectoras", "encuadernacion"])
    data = supabase.table(t_h).select("*").execute().data
    st.dataframe(pd.DataFrame(data))
