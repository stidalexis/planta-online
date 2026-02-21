import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA DE PLANTA MASTER", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- FUNCIONES DE SOPORTE ---
def normalizar(texto):
    reemplazos = {"Í": "I", "Ó": "O", "Á": "A", "É": "E", "Ú": "U", " ": "_"}
    t = texto.upper()
    for k, v in reemplazos.items(): t = t.replace(k, v)
    return t.lower()

def safe_float(valor):
    if valor is None or valor == "": return 0.0
    try: return float(str(valor).replace(',', '.'))
    except: return 0.0

def calcular_horas(inicio, fin):
    try:
        t_ini = datetime.strptime(inicio, "%H:%M")
        t_fin = datetime.strptime(fin, "%H:%M")
        h = (t_fin - t_ini).total_seconds() / 3600
        return h if h > 0 else 0.01
    except: return 0.01

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 75px; font-weight: bold; border-radius: 12px; font-size: 18px; border: 2px solid #0D47A1; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- NAVEGACIÓN ---
st.sidebar.title("🏭 MENÚ DE CONTROL")
opciones = ["🖥️ Monitor en Vivo", "📊 Análisis Gerencial (OP)", "🖨️ Impresión", "✂️ Corte"]
seleccion = st.sidebar.radio("Seleccione módulo:", opciones)

# ==========================================
# 📊 ANÁLISIS GERENCIAL (TABLA MAESTRA)
# ==========================================
if seleccion == "📊 Análisis Gerencial (OP)":
    st.title("📊 Análisis de Rendimiento por Orden de Producción")
    
    # Cargar datos de ambas tablas
    res_imp = supabase.table("impresion").select("*").execute()
    res_cor = supabase.table("corte").select("*").execute()
    
    df_imp = pd.DataFrame(res_imp.data)
    df_cor = pd.DataFrame(res_cor.data)
    
    if not df_imp.empty and not df_cor.empty:
        # Cruce de datos por OP con sufijos para evitar KeyError
        df_master = pd.merge(df_cor, df_imp, on="op", how="inner", suffixes=('_cor', '_imp'))
        
        analisis_filas = []
        for _, fila in df_master.iterrows():
            # Variables numéricas seguras
            ancho_mm = safe_float(fila['ancho_imp'])
            ancho_m = ancho_mm / 1000 if ancho_mm > 10 else ancho_mm
            metros = safe_float(fila['metros_impresos'])
            gramaje = safe_float(fila['gramaje_imp'])
            rollos = safe_float(fila['total_rollos'])
            
            # Cálculos Avanzados
            kilos_brutos = (ancho_m * metros * gramaje) / 1000
            merma_kg = safe_float(fila['desp_kg_imp']) + safe_float(fila['desp_kg_cor'])
            kilos_netos = kilos_brutos - merma_kg
            eficiencia = (kilos_netos / kilos_brutos * 100) if kilos_brutos > 0 else 0
            
            # Formateo de fila para tabla
            analisis_filas.append({
                "OP": fila['op'],
                "Trabajo": fila['trabajo_imp'],
                "Papel": f"{fila['tipo_papel_imp']} {int(gramaje)}g",
                "Kilos Brutos": round(kilos_brutos, 2),
                "Merma Total (Kg)": round(merma_kg, 2),
                "Kilos Netos": round(kilos_netos, 2),
                "Eficiencia": f"{round(eficiencia, 1)}%",
                "Peso/Rollo (Kg)": round(kilos_netos/rollos, 3) if rollos > 0 else 0,
                "Obs. Impresión": fila['observaciones_imp'],
                "Obs. Corte": fila['observaciones_cor'],
                "Fecha": fila['fecha_fin_cor']
            })

        st.dataframe(pd.DataFrame(analisis_filas).style.background_gradient(subset=['Kilos Netos'], cmap='Greens'), use_container_width=True)
    else:
        st.info("💡 Sugerencia: Finalice una OP en Impresión y luego en Corte para ver los resultados aquí.")

# ==========================================
# 🖨️ / ✂️ MÓDULOS DE OPERACIÓN
# ==========================================
elif seleccion in ["🖨️ Impresión", "✂️ Corte"]:
    area_actual = "IMPRESIÓN" if seleccion == "🖨️ Impresión" else "CORTE"
    MAQUINAS = {
        "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
        "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"]
    }
    
    st.title(f"Joystick de Operación: {area_actual}")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}

    # Botonera
    cols = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS[area_actual]):
        if cols[i % 4].button(m_btn, key=f"btn_{m_btn}"):
            st.session_state.m_sel = m_btn

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_actual]:
        m = st.session_state.m_sel
        act = activos.get(m)
        
        if not act:
            with st.form("inicio_op"):
                st.subheader(f"🚀 Iniciar OP en {m}")
                f_op = st.text_input("Número de OP")
                f_tr = st.text_input("Nombre del Trabajo")
                c1, c2, c3 = st.columns(3)
                f_pa = c1.text_input("Tipo de Papel")
                f_an = c2.text_input("Ancho (mm)")
                f_gr = c3.text_input("Gramaje (g)")
                
                if st.form_submit_button("EMPEZAR TRABAJO"):
                    if f_op and f_tr:
                        data = {
                            "maquina": m, "op": f_op, "trabajo": f_tr, "area": area_actual,
                            "tipo_papel": f_pa, "ancho": f_an, "gramaje": f_gr,
                            "hora_inicio": datetime.now().strftime("%H:%M")
                        }
                        supabase.table("trabajos_activos").insert(data).execute()
                        st.rerun()
        else:
            with st.form("cierre_op"):
                st.success(f"📌 OP Actual: {act['op']} | {act['trabajo']}")
                
                if area_actual == "IMPRESIÓN":
                    prod = st.number_input("Metros Impresos Finales", 0.0)
                else:
                    prod = st.number_input("Total Rollos Obtenidos", 0)
                
                c_dk = st.number_input("Desperdicio (Kg)", 0.0)
                c_obs = st.text_area("📝 Observaciones / Incidencias", help="Escriba aquí cualquier novedad del turno.")
                
                if st.form_submit_button("🏁 FINALIZAR Y LIBERAR MÁQUINA"):
                    # Preparar data de cierre
                    final_data = {
                        "op": act['op'], "maquina": m, "trabajo": act['trabajo'],
                        "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                        "desp_kg": c_dk, "observaciones": c_obs,
                        "tipo_papel": act['tipo_papel'], 
                        "ancho": safe_float(act['ancho']), 
                        "gramaje": safe_float(act['gramaje'])
                    }
                    if area_actual == "IMPRESIÓN": final_data["metros_impresos"] = prod
                    else: final_data["total_rollos"] = prod

                    # Guardar y borrar de activos
                    supabase.table(normalizar(area_actual)).insert(final_data).execute()
                    supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                    st.rerun()

# ==========================================
# 🖥️ MONITOR EN VIVO
# ==========================================
elif seleccion == "🖥️ Monitor en Vivo":
    st.title("🖥️ Estatus General de Planta")
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
