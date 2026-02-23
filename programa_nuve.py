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

# --- ESTILOS (IGUAL A TU V6) ---
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
    if valor is None or valor == "": return 0.0
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
    res_activos = supabase.table("trabajos_activos").select("*").execute().data
    res_paradas = supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data
    
    activos = {a['maquina']: a for a in res_activos} if res_activos else {}
    paradas = {p['maquina']: p for p in res_paradas} if res_paradas else {}
    
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(6)
        for idx, m in enumerate(lista):
            with cols[idx % 6]:
                if m in paradas: st.markdown(f"<div class='card-parada'>🚨 {m}</div>", unsafe_allow_html=True)
                elif m in activos: st.markdown(f"<div class='card-proceso'>⚙️ {m}<br>OP: {activos[m]['op']}</div>", unsafe_allow_html=True)
                else: st.markdown(f"<div class='card-libre'>⚪ {m}</div>", unsafe_allow_html=True)

# ==========================================
# 2. CONSOLIDADO GERENCIAL
# ==========================================
elif seleccion == "📊 Consolidado Gerencial":
    st.title("📊 Indicadores de Rendimiento por OP")
    
    res_imp = supabase.table("impresion").select("*").execute().data
    res_cor = supabase.table("corte").select("*").execute().data
    
    df_imp = pd.DataFrame(res_imp) if res_imp else pd.DataFrame()
    df_cor = pd.DataFrame(res_cor) if res_cor else pd.DataFrame()
    
    if not df_imp.empty and not df_cor.empty:
        df_join = pd.merge(df_cor, df_imp, on="op", how="inner", suffixes=('_cor', '_imp'))
        
        datos_tabla = []
        for _, fila in df_join.iterrows():
            ancho_m = safe_float(fila.get('ancho_imp', 0))
            ancho_m = ancho_m / 1000 if ancho_m > 10 else ancho_m
            metros = safe_float(fila.get('metros_impresos', 0))
            gramaje = safe_float(fila.get('gramaje_imp', 0))
            
            kilos_salida = (ancho_m * metros * gramaje) / 100
            kilos_desp = safe_float(fila.get('desp_kg_imp', 0)) + safe_float(fila.get('desp_kg_cor', 0))
            
            eficiencia = 100 - ((kilos_desp / kilos_salida * 100) if kilos_salida > 0 else 0)
            horas_imp = calcular_horas(fila.get('h_inicio_imp', "00:00"), fila.get('h_fin_imp', "00:00"))
            vel_imp = metros / horas_imp if horas_imp > 0 else 0

            datos_tabla.append({
                "OP": fila['op'],
                "Trabajo": fila['trabajo_imp'],
                "Kilos Producidos": round(kilos_salida, 2),
                "Kilos Desperdicio": round(kilos_desp, 2),
                "% Eficiencia": f"{round(eficiencia, 1)}%",
                "Velocidad (mts/h)": round(vel_imp, 0),
                "Metros": metros,
                "Rollos Corte": fila.get('total_rollos', 0),
                "Fecha": fila.get('fecha_fin_cor', '')
            })
        
        if datos_tabla:
            st.dataframe(pd.DataFrame(datos_tabla), use_container_width=True)
            st.divider()
            res_df = pd.DataFrame(datos_tabla)
            c1, c2, c3 = st.columns(3)
            c1.metric("Kilos Totales", f"{round(res_df['Kilos Producidos'].sum(), 1)} Kg")
            c2.metric("Eficiencia Media", f"{round(res_df['Kilos Producidos'].sum() / (res_df['Kilos Producidos'].sum() + res_df['Kilos Desperdicio'].sum()) * 100, 1)}%")
            c3.metric("Total Desperdicio", f"{round(res_df['Kilos Desperdicio'].sum(), 1)} Kg", delta="-MERMA", delta_color="inverse")
    else:
        st.info("Complete procesos en Impresión y Corte con la misma OP para ver indicadores.")

# ==========================================
# 3. MÓDULOS DE ÁREA (CON FORMULARIOS ORIGINALES)
# ==========================================
else:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_actual = area_map[seleccion]
    st.title(f"Joystick: {area_actual}")
    
    res_activos = supabase.table("trabajos_activos").select("*").execute().data
    activos = {a['maquina']: a for a in res_activos} if res_activos else {}

    cols_m = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS[area_actual]):
        if cols_m[i % 4].button(m_btn, key=f"btn_{m_btn}", use_container_width=True):
            st.session_state.m_sel = m_btn

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_actual]:
        m = st.session_state.m_sel
        act = activos.get(m)
        
        if not act:
            with st.form("inicio"):
                st.subheader(f"🚀 Iniciar OP en {m}")
                c1, c2 = st.columns(2)
                op, tr = c1.text_input("OP"), c2.text_input("Trabajo")
                extra = {}
                if area_actual == "IMPRESIÓN":
                    p1, p2, p3 = st.columns(3)
                    extra = {"tipo_papel": p1.text_input("Papel"), "ancho": p2.text_input("Ancho mm"), "gramaje": p3.text_input("Gramaje")}
                elif area_actual == "CORTE":
                    p1, p2, p3 = st.columns(3)
                    extra = {"tipo_papel": p1.text_input("Papel"), "img_varilla": p2.text_input("Img/Var"), "medida_rollos": p3.text_input("Medida")}
                
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

                    nom_tabla = normalizar(area_actual)
                    # CAMPOS TÉCNICOS SEGÚN TU V6
                    mapeo = {
                        "impresion": ["tipo_papel", "ancho", "gramaje"],
                        "corte": ["tipo_papel", "img_varilla", "medida_rollos"]
                    }
                    
                    for campo in mapeo.get(nom_tabla, []):
                        if campo in act:
                            if campo in ["ancho", "gramaje"]: final_data[campo] = safe_float(act[campo])
                            else: final_data[campo] = act[campo]

                    supabase.table(nom_tabla).insert(final_data).execute()
                    supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                    st.rerun()
