import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA DE CONTROL DE PRODUCCIÓN", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("Error en las credenciales de Supabase. Verifica tu archivo secrets.")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stButton > button { height: 70px; font-weight: bold; border-radius: 12px; font-size: 18px; border: 2px solid #0D47A1; margin-bottom: 10px; }
    .card-proceso { padding: 15px; border-radius: 10px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; text-align: center; color: #1B5E20; font-weight: bold; }
    .card-parada { padding: 15px; border-radius: 10px; background-color: #FFEBEE; border-left: 8px solid #C62828; text-align: center; color: #B71C1C; font-weight: bold; }
    .card-libre { padding: 15px; border-radius: 10px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #616161; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin-top: 25px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- DICCIONARIO DE MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- FUNCIONES DE SOPORTE ---
def normalizar(texto):
    reemplazos = {"Í": "I", "Ó": "O", "Á": "A", "É": "E", "Ú": "U", " ": "_"}
    t = texto.upper()
    for k, v in reemplazos.items(): t = t.replace(k, v)
    return t.lower()

def safe_float(valor):
    if valor is None: return 0.0
    try: return float(str(valor).replace(',', '.'))
    except: return 0.0

def calcular_duracion(inicio, fin):
    try:
        t_ini = datetime.strptime(inicio, "%H:%M")
        t_fin = datetime.strptime(fin, "%H:%M")
        return str(t_fin - t_ini)
    except: return "0:00:00"

# --- BARRA LATERAL (NAVEGACIÓN) ---
st.sidebar.title("🏭 MENÚ PRINCIPAL")
opciones = ["🖥️ Monitor General", "📊 Consolidado Total", "⏱️ Seguimiento Cortadoras", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]
seleccion = st.sidebar.radio("Seleccione Área:", opciones)

# ==============================================================================
# SECCIÓN 1: MONITOR GENERAL
# ==============================================================================
if seleccion == "🖥️ Monitor General":
    st.title("🖥️ Estatus de Planta en Tiempo Real")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
    
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(6)
        for idx, m in enumerate(lista):
            with cols[idx % 6]:
                if m in paradas:
                    st.markdown(f"<div class='card-parada'>🚨 PARADA<br>{m}<br>OP: {paradas[m]['op']}</div>", unsafe_allow_html=True)
                elif m in activos:
                    st.markdown(f"<div class='card-proceso'>⚙️ TRABAJANDO<br>{m}<br>OP: {activos[m]['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-libre'>⚪ LIBRE<br>{m}</div>", unsafe_allow_html=True)

# ==============================================================================
# SECCIÓN 2: CONSOLIDADO TOTAL (VISTA GERENCIAL)
# ==============================================================================
elif seleccion == "📊 Consolidado Total":
    st.title("📊 Consolidado Gerencial de Producción")
    
    df_imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
    df_cor = pd.DataFrame(supabase.table("corte").select("*").execute().data)
    
    if not df_cor.empty and not df_imp.empty:
        st.subheader("🚀 Análisis Unificado: Impresión vs Corte")
        # Unión de datos por número de OP
        consolidado = pd.merge(df_cor, df_imp, on="op", how="left", suffixes=('_corte', '_imp'))
        
        resumen = []
        for _, fila in consolidado.iterrows():
            # Cálculo de Peso Teórico (Kg)
            ancho_mm = safe_float(fila.get('ancho_imp', 0))
            ancho_m = ancho_mm / 1000 if ancho_mm > 10 else ancho_mm
            peso_t = (ancho_m * safe_float(fila.get('metros_impresos', 0)) * safe_float(fila.get('gramaje_imp', 0))) / 100
            
            # Cálculo de Desperdicio Total
            desp_t = safe_float(fila.get('desp_kg_imp', 0)) + safe_float(fila.get('desp_kg_corte', 0))
            
            resumen.append({
                "OP": fila['op'],
                "Trabajo": fila['trabajo_corte'],
                "Peso Teórico (Kg)": round(peso_t, 2),
                "Desp. Total (Kg)": round(desp_t, 2),
                "% Desperdicio": f"{round((desp_t/peso_t*100),1)}%" if peso_t > 0 else "0%",
                "Tiempo Imp.": calcular_duracion(fila.get('h_inicio_imp', ''), fila.get('h_fin_imp', '')),
                "Tiempo Corte": calcular_duracion(fila.get('h_inicio_corte', ''), fila.get('h_fin_corte', '')),
                "Metros": fila.get('metros_impresos', 0),
                "Rollos": fila.get('total_rollos', 0)
            })
        
        st.dataframe(pd.DataFrame(resumen), use_container_width=True)
        
        st.divider()
        m1, m2, m3 = st.columns(3)
        res_df = pd.DataFrame(resumen)
        m1.metric("Kilos Totales", f"{round(res_df['Peso Teórico (Kg)'].sum(), 2)} Kg")
        m2.metric("Desperdicio Acumulado", f"{round(res_df['Desp. Total (Kg)'].sum(), 2)} Kg")
        m3.metric("Eficiencia Promedio", f"{round(100 - (res_df['Desp. Total (Kg)'].sum() / res_df['Peso Teórico (Kg)'].sum() * 100), 1)}%" if res_df['Peso Teórico (Kg)'].sum() > 0 else "0%")

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📥 Colectoras")
        st.dataframe(pd.DataFrame(supabase.table("colectoras").select("*").execute().data))
    with col_b:
        st.subheader("📕 Encuadernación")
        st.dataframe(pd.DataFrame(supabase.table("encuadernacion").select("*").execute().data))

# ==============================================================================
# SECCIÓN 3: SEGUIMIENTO HORARIO CORTADORAS
# ==============================================================================
elif seleccion == "⏱️ Seguimiento Cortadoras":
    st.title("⏱️ Seguimiento Horario de Cortadoras")
    cols_s = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS["CORTE"]):
        if cols_s[i % 4].button(m_btn, key=f"seg_{m_btn}", use_container_width=True):
            st.session_state.m_seg = m_btn
    
    if "m_seg" in st.session_state:
        m_s = st.session_state.m_seg
        # Obtener datos de OP activa para facilitar llenado
        act_s = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}.get(m_s, {})
        
        with st.form("form_seguimiento"):
            st.subheader(f"Registro Horario: {m_s}")
            c1, c2, c3 = st.columns(3)
            f_op = c1.text_input("OP Actual", value=act_s.get('op', ""))
            f_tr = c2.text_input("Trabajo", value=act_s.get('trabajo', ""))
            f_var = c3.number_input("Varillas en esta hora", 0)
            
            c4, c5 = st.columns(2)
            f_desp = c4.number_input("Desperdicio (Kg)", 0.0)
            f_mot = c5.text_input("Motivo Desp.")
            
            if st.form_submit_button("💾 GUARDAR AVANCE HORARIO"):
                supabase.table("seguimiento_corte").insert({
                    "maquina": m_s, "op": f_op, "nombre_trabajo": f_tr,
                    "n_varillas_actual": f_var, "desperdicio_kg": f_desp, "motivo_desperdicio": f_mot
                }).execute()
                st.success("Avance guardado correctamente.")

# ==============================================================================
# SECCIÓN 4: MÓDULOS DE OPERACIÓN (IMPRESIÓN, CORTE, ETC)
# ==============================================================================
else:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_actual = area_map[seleccion]
    st.title(f"🕹️ Terminal de Operación: {area_actual}")
    
    # Cargar estados
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
    
    # Botonera de Máquinas
    cols_v = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS[area_actual]):
        if cols_v[i % 4].button(m_btn, key=f"btn_{m_btn}", use_container_width=True):
            st.session_state.m_sel = m_btn

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_actual]:
        m = st.session_state.m_sel
        act, par = activos.get(m), paradas.get(m)
        
        # --- ESTADO: EN PARADA ---
        if par:
            st.error(f"🚨 LA MÁQUINA {m} ESTÁ DETENIDA")
            st.warning(f"Motivo: {par['motivo']} | Desde: {par['h_inicio']}")
            if st.button("▶️ REANUDAR PRODUCCIÓN"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()

        # --- ESTADO: LIBRE (INICIAR TRABAJO) ---
        elif not act:
            with st.form("form_inicio"):
                st.subheader(f"🚀 Iniciar Producción en {m}")
                c1, c2 = st.columns(2)
                op_in = c1.text_input("Número de OP")
                tr_in = c2.text_input("Nombre del Trabajo")
                
                extra = {}
                if area_actual == "IMPRESIÓN":
                    p1, p2, p3 = st.columns(3)
                    extra = {"tipo_papel": p1.text_input("Tipo Papel"), "ancho": p2.text_input("Ancho (mm)"), "gramaje": p3.text_input("Gramaje")}
                elif area_actual == "CORTE":
                    p1, p2, p3 = st.columns(3)
                    extra = {"tipo_papel": p1.text_input("Tipo Papel"), "img_varilla": p2.number_input("Imágenes por Varilla", 0), "medida_rollos": p3.text_input("Medida Rollos")}
                elif area_actual == "COLECTORAS":
                    p1, p2 = st.columns(2)
                    extra = {"tipo_papel": p1.text_input("Tipo Papel"), "unidades_caja": p2.number_input("Unidades por Caja", 0)}
                elif area_actual == "ENCUADERNACIÓN":
                    p1, p2 = st.columns(2)
                    extra = {"formas_totales": p1.number_input("Formas Totales", 0), "material": p2.text_input("Material / Pegamento")}
                
                if st.form_submit_button("✅ COMENZAR TRABAJO"):
                    if op_in and tr_in:
                        data_in = {"maquina": m, "op": op_in, "trabajo": tr_in, "area": area_actual, "hora_inicio": datetime.now().strftime("%H:%M")}
                        data_in.update(extra)
                        supabase.table("trabajos_activos").insert(data_in).execute()
                        st.rerun()
                    else: st.warning("Por favor llene OP y Trabajo.")

        # --- ESTADO: TRABAJANDO (CIERRE O PARADA) ---
        else:
            st.success(f"🟢 TRABAJO ACTUAL: {act['trabajo']} (OP: {act['op']})")
            
            with st.form("form_cierre"):
                st.subheader("🏁 Finalizar Producción")
                res_fin = {}
                if area_actual == "IMPRESIÓN":
                    c1, c2 = st.columns(2)
                    res_fin = {"metros_impresos": c1.number_input("Metros Impresos Total", 0.0), "bobinas": c2.number_input("Cant. Bobinas", 0)}
                elif area_actual == "CORTE":
                    c1, c2, c3 = st.columns(3)
                    res_fin = {"cant_varillas": c1.number_input("Total Varillas", 0), "total_rollos": c2.number_input("Total Rollos Finales", 0), "unidades_caja": c3.number_input("Unidades por Caja", 0)}
                elif area_actual == "COLECTORAS":
                    c1, c2 = st.columns(2)
                    res_fin = {"total_cajas": c1.number_input("Total Cajas", 0), "total_formas": c2.number_input("Total Formas", 0)}
                elif area_actual == "ENCUADERNACIÓN":
                    c1, c2 = st.columns(2)
                    res_fin = {"cant_final": c1.number_input("Cantidad Final", 0), "presentacion": c2.text_input("Presentación (Ej: Paquete x 10)")}

                st.divider()
                c4, c5 = st.columns(2)
                dk_fin = c4.number_input("Desperdicio Total (Kg)", 0.0)
                mot_fin = c5.text_input("Motivo del Desperdicio")
                obs_fin = st.text_area("Observaciones Adicionales")
                
                if st.form_submit_button("🏁 GUARDAR Y LIBERAR MÁQUINA"):
                    # 1. Diccionario Base
                    final_data = {
                        "op": act['op'], "maquina": m, "trabajo": act['trabajo'],
                        "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                        "desp_kg": safe_float(dk_fin), "motivo_desperdicio": mot_fin, "observaciones": obs_fin
                    }
                    final_data.update(res_fin)
                    
                    # 2. Mapeo selectivo según tabla (Evita APIError por columnas sobrantes)
                    mapeo_campos = {
                        "impresion": ["tipo_papel", "ancho", "gramaje"],
                        "corte": ["tipo_papel", "img_varilla", "medida_rollos"],
                        "colectoras": ["tipo_papel", "unidades_caja"],
                        "encuardernacion": ["formas_totales", "material"]
                    }
                    
                    tabla_nom = normalizar(area_actual)
                    for campo in mapeo_campos.get(tabla_nom, []):
                        if campo in act:
                            if campo in ["ancho", "gramaje"]: final_data[campo] = safe_float(act[campo])
                            else: final_data[campo] = act[campo]
                    
                    try:
                        supabase.table(tabla_nom).insert(final_data).execute()
                        supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

            if st.button("🚨 NOTIFICAR PARADA DE MÁQUINA"):
                supabase.table("paradas_maquina").insert({
                    "maquina": m, "op": act['op'], "motivo": "Ajuste / Problema Técnico", 
                    "h_inicio": datetime.now().strftime("%H:%M")
                }).execute()
                st.rerun()

