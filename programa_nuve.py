import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA DE PRODUCCIÓN MASTER", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 75px; font-weight: bold; border-radius: 12px; font-size: 18px; border: 2px solid #0D47A1; }
    .card-proceso { padding: 15px; border-radius: 10px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; text-align: center; font-weight: bold; }
    .card-parada { padding: 15px; border-radius: 10px; background-color: #FFEBEE; border-left: 8px solid #C62828; text-align: center; font-weight: bold; }
    .card-libre { padding: 15px; border-radius: 10px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"]
}

# --- FUNCIONES ---
def normalizar(texto):
    reemplazos = {"Í": "I", "Ó": "O", "Á": "A", "É": "E", "Ú": "U", " ": "_"}
    t = texto.upper()
    for k, v in reemplazos.items(): t = t.replace(k, v)
    return t.lower()

def safe_float(valor):
    if valor is None or valor == "": return 0.0
    try: return float(str(valor).replace(',', '.'))
    except: return 0.0

# --- NAVEGACIÓN ---
st.sidebar.title("🏭 MENÚ DE PLANTA")
opciones = ["🖥️ Monitor", "📊 Consolidado Gerencial", "🖨️ Impresión", "✂️ Corte"]
seleccion = st.sidebar.radio("Ir a:", opciones)

# ==========================================
# 📊 CONSOLIDADO GERENCIAL (TABLA ÚNICA POR OP)
# ==========================================
if seleccion == "📊 Consolidado Gerencial":
    st.title("📊 Análisis de Inteligencia y Eficiencia por OP")
    
    df_imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
    df_cor = pd.DataFrame(supabase.table("corte").select("*").execute().data)
    
    if not df_imp.empty and not df_cor.empty:
        # Cruce de datos por OP (Pandas añade _imp y _cor automáticamente)
        df_master = pd.merge(df_cor, df_imp, on="op", how="inner", suffixes=('_cor', '_imp'))
        
        filas_gerencia = []
        for _, fila in df_master.iterrows():
            # Cálculos de Ingeniería de Papel
            ancho_mm = safe_float(fila['ancho_imp'])
            ancho_m = ancho_mm / 1000 if ancho_mm > 10 else ancho_mm
            metros = safe_float(fila['metros_impresos'])
            gramaje = safe_float(fila['gramaje_imp'])
            
            # Kilos Brutos = (Ancho(m) * Metros * Gramaje) / 1000
            kilos_brutos = (ancho_m * metros * gramaje) / 1000
            merma_total = safe_float(fila['desp_kg_imp']) + safe_float(fila['desp_kg_cor'])
            kilos_netos = kilos_brutos - merma_total
            
            # Eficiencia y Peso/Rollo
            eficiencia = (kilos_netos / kilos_brutos * 100) if kilos_brutos > 0 else 0
            rollos = safe_float(fila['total_rollos'])
            peso_prom_rollo = kilos_netos / rollos if rollos > 0 else 0

            filas_gerencia.append({
                "OP": fila['op'],
                "Trabajo": fila['trabajo_imp'],
                "Papel": f"{fila.get('tipo_papel_imp', 'N/A')} {int(gramaje)}g",
                "Kilos Brutos": round(kilos_brutos, 2),
                "Merma (Kg)": round(merma_total, 2),
                "Kilos Netos": round(kilos_netos, 2),
                "% Eficiencia": f"{round(eficiencia, 1)}%",
                "Peso/Rollo (Kg)": round(peso_prom_rollo, 3),
                "Rollos Fin.": int(rollos),
                "Obs. Impresión": fila.get('observaciones_imp', ''),
                "Obs. Corte": fila.get('observaciones_cor', ''),
                "Maquinaria": f"{fila['maquina_imp']} / {fila['maquina_cor']}"
            })
        
        df_final = pd.DataFrame(filas_gerencia)
        st.dataframe(df_final.style.background_gradient(subset=['% Eficiencia'], cmap='RdYlGn'), use_container_width=True)
    else:
        st.info("💡 Complete procesos en Impresión y Corte para ver el análisis aquí.")

# ==========================================
# 🖨️ / ✂️ MÓDULOS OPERATIVOS
# ==========================================
elif seleccion in ["🖨️ Impresión", "✂️ Corte"]:
    area_actual = "IMPRESIÓN" if seleccion == "🖨️ Impresión" else "CORTE"
    st.title(f"Terminal de Trabajo: {area_actual}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}

    # Botonera de Máquinas
    cols = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS[area_actual]):
        if cols[i % 4].button(m_btn, key=f"btn_{m_btn}"):
            st.session_state.m_sel = m_btn

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_actual]:
        m = st.session_state.m_sel
        act = activos.get(m)
        
        if not act:
            with st.form("inicio"):
                st.subheader(f"🚀 Iniciar en {m}")
                c1, c2 = st.columns(2)
                op = c1.text_input("Número de OP")
                tr = c2.text_input("Nombre del Trabajo")
                p1, p2, p3 = st.columns(3)
                pa = p1.text_input("Tipo de Papel")
                an = p2.text_input("Ancho (mm)")
                gr = p3.text_input("Gramaje (g)")
                
                if st.form_submit_button("EMPEZAR"):
                    if op and tr:
                        data = {"maquina": m, "op": op, "trabajo": tr, "area": area_actual, 
                                "tipo_papel": pa, "ancho": an, "gramaje": gr, "hora_inicio": datetime.now().strftime("%H:%M")}
                        supabase.table("trabajos_activos").insert(data).execute()
                        st.rerun()
        else:
            with st.form("cierre"):
                st.success(f"📌 OP: {act['op']} | {act['trabajo']}")
                res = {}
                if area_actual == "IMPRESIÓN":
                    res["metros_impresos"] = st.number_input("Metros Totales", 0.0)
                else:
                    res["total_rollos"] = st.number_input("Rollos Finales", 0)
                
                dk = st.number_input("Desperdicio (Kg)", 0.0)
                obs = st.text_area("📝 Observaciones del Trabajo (Merma, fallas, etc.)")
                
                if st.form_submit_button("🏁 FINALIZAR TRABAJO"):
                    final_data = {
                        "op": act['op'], "maquina": m, "trabajo": act['trabajo'],
                        "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                        "desp_kg": safe_float(dk), "observaciones": obs,
                        "tipo_papel": act['tipo_papel'], "ancho": safe_float(act['ancho']), "gramaje": safe_float(act['gramaje'])
                    }
                    final_data.update(res)

                    try:
                        supabase.table(normalizar(area_actual)).insert(final_data).execute()
                        supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

# ==========================================
# 🖥️ MONITOR EN VIVO
# ==========================================
elif seleccion == "🖥️ Monitor General":
    st.title("🖥️ Estatus de Maquinaria")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols_mon = st.columns(6)
        for idx, m_mon in enumerate(lista):
            with cols_mon[idx % 6]:
                if m_mon in activos:
                    st.success(f"⚙️ {m_mon}\nOP: {activos[m_mon]['op']}")
                else:
                    st.info(f"⚪ {m_mon}\nLibre")
