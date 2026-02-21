import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="CONTROL DE PRODUCCIÓN", page_icon="🏭")

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
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- FUNCIONES ---
def normalizar(texto):
    reemplazos = {"Í": "I", "Ó": "O", "Á": "A", "É": "E", "Ú": "U", " ": "_"}
    t = texto.upper()
    for k, v in reemplazos.items(): t = t.replace(k, v)
    return t.lower()

def safe_float(valor):
    if valor is None: return 0.0
    try: return float(str(valor).replace(',', '.'))
    except: return 0.0

def calcular_horas(inicio, fin):
    try:
        t_ini = datetime.strptime(inicio, "%H:%M")
        t_fin = datetime.strptime(fin, "%H:%M")
        return (t_fin - t_ini).total_seconds() / 3600
    except: return 0.0

# --- NAVEGACIÓN ---
st.sidebar.title("🏭 MENÚ PLANTA")
opciones = ["🖥️ Monitor General", "📊 Consolidado Gerencial", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]
seleccion = st.sidebar.radio("Ir a:", opciones)

# ==========================================
# 1. MONITOR GENERAL
# ==========================================
if seleccion == "🖥️ Monitor General":
    st.title("🖥️ Estatus en Tiempo Real")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
    
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(6)
        for idx, m in enumerate(lista):
            with cols[idx % 6]:
                if m in paradas: st.markdown(f"<div class='card-parada'>🚨 {m}</div>", unsafe_allow_html=True)
                elif m in activos: st.markdown(f"<div class='card-proceso'>⚙️ {m}<br>OP: {activos[m]['op']}</div>", unsafe_allow_html=True)
                else: st.markdown(f"<div class='card-libre'>⚪ {m}</div>", unsafe_allow_html=True)

# ==========================================
# 2. CONSOLIDADO GERENCIAL (INDICADORES POR OP)
# ==========================================
elif seleccion == "📊 Consolidado Gerencial":
    st.title("📊 Indicadores de Rendimiento por OP")
    
    df_imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
    df_cor = pd.DataFrame(supabase.table("corte").select("*").execute().data)
    
    if not df_imp.empty and not df_cor.empty:
        # Cruce de datos por OP
        df_join = pd.merge(df_cor, df_imp, on="op", how="inner", suffixes=('_cor', '_imp'))
        
        datos_tabla = []
        for _, fila in df_join.iterrows():
            # Cálculos de Peso y Eficiencia
            ancho_m = safe_float(fila['ancho_imp']) / 1000 if safe_float(fila['ancho_imp']) > 10 else safe_float(fila['ancho_imp'])
            metros = safe_float(fila['metros_impresos'])
            gramaje = safe_float(fila['gramaje_imp'])
            
            kilos_salida = (ancho_m * metros * gramaje) / 100
            kilos_desp = safe_float(fila['desp_kg_imp']) + safe_float(fila['desp_kg_cor'])
            
            eficiencia = 100 - ((kilos_desp / kilos_salida * 100) if kilos_salida > 0 else 0)
            
            horas_imp = calcular_horas(fila['h_inicio_imp'], fila['h_fin_imp'])
            vel_imp = metros / horas_imp if horas_imp > 0 else 0

            datos_tabla.append({
                "OP": fila['op'],
                "Trabajo": fila['trabajo_imp'],
                "Kilos Producidos": round(kilos_salida, 2),
                "Kilos Desperdicio": round(kilos_desp, 2),
                "% Eficiencia": f"{round(eficiencia, 1)}%",
                "Velocidad (mts/h)": round(vel_imp, 0),
                "Metros": metros,
                "Rollos Corte": fila['total_rollos'],
                "Fecha": fila['fecha_fin_cor']
            })
        
        st.dataframe(pd.DataFrame(datos_tabla), use_container_width=True)
        
        # Resumen Global
        st.divider()
        res_df = pd.DataFrame(datos_tabla)
        c1, c2, c3 = st.columns(3)
        c1.metric("Kilos Totales", f"{round(res_df['Kilos Producidos'].sum(), 1)} Kg")
        c2.metric("Eficiencia Media", f"{round(res_df['Kilos Producidos'].sum() / (res_df['Kilos Producidos'].sum() + res_df['Kilos Desperdicio'].sum()) * 100, 1)}%")
        c3.metric("Total Desperdicio", f"{round(res_df['Kilos Desperdicio'].sum(), 1)} Kg", delta="-MERMA", delta_color="inverse")
    else:
        st.info("Complete procesos en Impresión y Corte con la misma OP para ver indicadores.")

# ==========================================
# 3. MÓDULOS DE ÁREA
# ==========================================
else:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_actual = area_map[seleccion]
    st.title(f"Joystick: {area_actual}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    cols_m = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS[area_actual]):
        if cols_m[i % 4].button(m_btn, key=f"btn_{m_btn}", use_container_width=True):
            st.session_state.m_sel = m_btn

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_actual]:
        m = st.session_state.m_sel
        act, par = activos.get(m), paradas.get(m)
        
        if not act:
            with st.form("inicio"):
                st.subheader(f"🚀 Iniciar OP en {m}")
                c1, c2 = st.columns(2)
                op = c1.text_input("OP")
                tr = c2.text_input("Trabajo")
                extra = {}
                if area_actual == "IMPRESIÓN":
                    p1, p2, p3 = st.columns(3)
                    extra = {"tipo_papel": p1.text_input("Papel"), "ancho": p2.text_input("Ancho mm"), "gramaje": p3.text_input("Gramaje")}
                elif area_actual == "CORTE":
                    p1, p2, p3 = st.columns(3)
                    extra = {"tipo_papel": p1.text_input("Papel"), "img_varilla": p2.number_input("Img/Var", 0), "medida_rollos": p3.text_input("Medida")}
                
                if st.form_submit_button("✅ EMPEZAR"):
                    if op and tr:
                        data = {"maquina": m, "op": op, "trabajo": tr, "area": area_actual, "hora_inicio": datetime.now().strftime("%H:%M")}
                        data.update(extra)
                        supabase.table("trabajos_activos").insert(data).execute()
                        st.rerun()
        else:
            with st.form("cierre"):
                st.info(f"Produciendo OP: {act['op']}")
                res = {}
                if area_actual == "IMPRESIÓN":
                    c1, c2 = st.columns(2); res = {"metros_impresos": c1.number_input("Metros", 0.0), "bobinas": c2.number_input("Bobinas", 0)}
                elif area_actual == "CORTE":
                    c1, c2 = st.columns(2); res = {"cant_varillas": c1.number_input("Varillas", 0), "total_rollos": c2.number_input("Rollos", 0)}

                dk = st.number_input("Desperdicio (Kg)", 0.0)
                mot = st.text_input("Motivo")
                
                if st.form_submit_button("🏁 FINALIZAR"):
                    final_data = {
                        "op": act['op'], "maquina": m, "trabajo": act['trabajo'],
                        "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                        "desp_kg": safe_float(dk), "motivo_desperdicio": mot
                    }
                    final_data.update(res)

                    # MAPEO DE CAMPOS TÉCNICOS SEGÚN TABLA
                    campos_tabla = {
                        "impresion": ["tipo_papel", "ancho", "gramaje"],
                        "corte": ["tipo_papel", "img_varilla", "medida_rollos"]
                    }
                    
                    nom_tabla = normalizar(area_actual)
                    for campo in campos_tabla.get(nom_tabla, []):
                        if campo in act:
                            if campo in ["ancho", "gramaje"]: final_data[campo] = safe_float(act[campo])
                            else: final_data[campo] = act[campo]

                    try:
                        supabase.table(nom_tabla).insert(final_data).execute()
                        supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

