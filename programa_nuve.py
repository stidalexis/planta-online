import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="SISTEMA DE PRODUCCIÓN", page_icon="🏭")

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 75px; font-weight: bold; border-radius: 15px; font-size: 20px; border: 2px solid #0D47A1; margin-bottom: 10px; }
    .card-proceso { padding: 15px; border-radius: 10px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; text-align: center; }
    .card-parada { padding: 15px; border-radius: 10px; background-color: #FFEBEE; border-left: 8px solid #C62828; text-align: center; }
    .card-libre { padding: 15px; border-radius: 10px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin-top: 25px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

def normalizar(texto):
    reemplazos = {"Í": "I", "Ó": "O", "Á": "A", "É": "E", "Ú": "U"}
    for t, r in reemplazos.items():
        texto = texto.replace(t, r)
    return texto.lower()

def calcular_duracion(inicio, fin):
    try:
        t_ini = datetime.strptime(inicio, "%H:%M")
        t_fin = datetime.strptime(fin, "%H:%M")
        return str(t_fin - t_ini)
    except: return "0:00:00"

# --- NAVEGACIÓN ---
st.sidebar.title("⚙️ CONTROL CENTRAL")
opciones = ["🖥️ Monitor General", "📊 Consolidado Total", "⏱️ Seguimiento Cortadoras", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]
seleccion = st.sidebar.radio("Ir a:", opciones)

# ==========================================
# 1. CONSOLIDADO TOTAL (VISTA GERENCIAL)
# ==========================================
if seleccion == "📊 Consolidado Total":
    st.title("📊 Consolidado Gerencial de Producción")
    
    df_imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
    df_cor = pd.DataFrame(supabase.table("corte").select("*").execute().data)
    
    if not df_cor.empty:
        st.subheader("🚀 Unificado: Impresión vs Corte")
        # Unificar por OP
        consolidado = pd.merge(df_cor, df_imp, on="op", how="left", suffixes=('_corte', '_imp'))
        
        resumen = []
        for _, fila in consolidado.iterrows():
            # Cálculos Gerenciales
            # Peso Teórico: (Ancho(m) * Metros * Gramaje) / 1000
            try:
                # Normalizamos ancho si está en mm
                ancho_val = float(fila.get('ancho_imp', 0))
                ancho_m = ancho_val / 1000 if ancho_val > 10 else ancho_val
                peso_teorico = (ancho_m * float(fila.get('metros_impresos', 0)) * float(fila.get('gramaje_imp', 0))) / 1000
            except: peso_teorico = 0
            
            desp_total = (fila.get('desp_kg_imp', 0) or 0) + (fila.get('desp_kg_corte', 0) or 0)
            tipo = "Impreso" if pd.notnull(fila.get('h_inicio_imp')) else "Rollo Blanco"
            
            resumen.append({
                "OP": fila['op'], 
                "Trabajo": fila['trabajo_corte'], 
                "Tipo": tipo,
                "Peso Teórico (Kg)": round(peso_teorico, 2),
                "Metros": fila.get('metros_impresos', 0),
                "T. Impresión": calcular_duracion(fila.get('h_inicio_imp', ''), fila.get('h_fin_imp', '')),
                "T. Corte": calcular_duracion(fila.get('h_inicio_corte', ''), fila.get('h_fin_corte', '')),
                "Rollos Finales": fila.get('total_rollos', 0),
                "Desp. Total (Kg)": round(desp_total, 2),
                "% Desp.": f"{round((desp_total/peso_teorico*100),1)}%" if peso_teorico > 0 else "0%"
            })
        
        st.dataframe(pd.DataFrame(resumen), use_container_width=True)
        
        st.divider()
        m1, m2, m3 = st.columns(3)
        df_res = pd.DataFrame(resumen)
        m1.metric("Kilos Producidos", f"{round(df_res['Peso Teórico (Kg)'].sum(), 2)} Kg")
        m2.metric("Kilos Desperdicio", f"{round(df_res['Desp. Total (Kg)'].sum(), 2)} Kg")
        m3.metric("Total Rollos", int(df_res['Rollos Finales'].sum()))

    # Otras tablas normales
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.write("📥 Colectoras")
        st.dataframe(pd.DataFrame(supabase.table("colectoras").select("*").execute().data))
    with c2:
        st.write("📕 Encuadernación")
        st.dataframe(pd.DataFrame(supabase.table("encuadernacion").select("*").execute().data))

# ==========================================
# 2. MONITOR GENERAL
# ==========================================
elif seleccion == "🖥️ Monitor General":
    st.title("🖥️ Planta en Tiempo Real")
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
# 3. SEGUIMIENTO CORTADORAS (BOTONES GRANDES)
# ==========================================
elif seleccion == "⏱️ Seguimiento Cortadoras":
    st.title("⏱️ Seguimiento de Cortadoras")
    cols_s = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS["CORTE"]):
        if cols_s[i % 4].button(m_btn, key=f"seg_{m_btn}", use_container_width=True):
            st.session_state.m_seg = m_btn
    
    if "m_seg" in st.session_state:
        m_s = st.session_state.m_seg
        act_seg = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}.get(m_s, {})
        with st.form("f_seg"):
            st.subheader(f"Avance de {m_s}")
            c1, c2, c3 = st.columns(3)
            op_s = c1.text_input("OP", value=act_seg.get('op', ""))
            tr_s = c2.text_input("Trabajo", value=act_seg.get('trabajo', ""))
            pa_s = c3.text_input("Papel", value=act_seg.get('tipo_papel', ""))
            var_s = st.number_input("Varillas en esta hora", 0)
            if st.form_submit_button("💾 GUARDAR LECTURA"):
                supabase.table("seguimiento_corte").insert({"maquina": m_s, "op": op_s, "nombre_trabajo": tr_s, "tipo_papel": pa_s, "n_varillas_actual": var_s}).execute()
                st.success("Registrado.")

# ==========================================
# 4. MÓDULOS OPERATIVOS
# ==========================================
else:
    mapa_areas = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_actual = mapa_areas[seleccion]
    st.title(f"Módulo: {area_actual}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    n_cols = 5 if area_actual == "ENCUADERNACIÓN" else 4
    cols_v = st.columns(n_cols)
    for i, m_btn in enumerate(MAQUINAS[area_actual]):
        if cols_v[i % n_cols].button(m_btn, key=f"btn_{m_btn}", use_container_width=True):
            st.session_state.m_sel = m_btn

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_actual]:
        m = st.session_state.m_sel
        act, par = activos.get(m), paradas.get(m)
        
        if par:
            st.error(f"🚨 {m} EN PARADA")
            if st.button("REANUDAR"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()
        
        elif not act:
            with st.form("inicio_op"):
                st.subheader(f"🚀 Iniciar en {m}")
                c1, c2 = st.columns(2)
                op = c1.text_input("Número de OP")
                tr = c2.text_input("Trabajo")
                extra = {}
                if area_actual == "IMPRESIÓN":
                    p1, p2, p3 = st.columns(3); extra = {"tipo_papel": p1.text_input("Tipo Papel"), "ancho": p2.number_input("Ancho (mm)", 0.0), "gramaje": p3.number_input("Gramaje", 0.0), "medida_trabajo": p1.text_input("Medida")}
                elif area_actual == "CORTE":
                    p1, p2, p3 = st.columns(3); extra = {"tipo_papel": p1.text_input("Papel"), "ancho": p2.number_input("Ancho", 0.0), "gramaje": p3.number_input("Gramaje", 0.0), "img_varilla": p1.number_input("Imágenes*Varilla", 0), "medida_rollos": p2.text_input("Medida Rollos")}
                elif area_actual == "COLECTORAS":
                    p1, p2 = st.columns(2); extra = {"tipo_papel": p1.text_input("Papel"), "medida_trabajo": p2.text_input("Medida"), "unidades_caja": p1.number_input("Und*Caja", 0)}
                elif area_actual == "ENCUADERNACIÓN":
                    p1, p2 = st.columns(2); extra = {"formas_totales": p1.number_input("Formas", 0), "material": p2.text_input("Material"), "medida": p1.text_input("Medida")}
                
                if st.form_submit_button("🚀 INICIAR"):
                    if op and tr:
                        data = {"maquina": m, "op": op, "trabajo": tr, "area": area_actual, "hora_inicio": datetime.now().strftime("%H:%M")}
                        data.update(extra)
                        supabase.table("trabajos_activos").insert(data).execute()
                        st.rerun()
        else:
            with st.form("cierre_op"):
                st.info(f"Produciendo: {act['trabajo']} (OP: {act['op']})")
                res_fields = {}
                if area_actual == "IMPRESIÓN":
                    c1, c2 = st.columns(2); res_fields = {"metros_impresos": c1.number_input("Metros", 0), "bobinas": c2.number_input("Bobinas", 0)}
                elif area_actual == "CORTE":
                    c1, c2, c3 = st.columns(3); res_fields = {"cant_varillas": c1.number_input("Varillas", 0), "unidades_caja": c2.number_input("Und/Caja", 0), "total_rollos": c3.number_input("Total Rollos", 0)}
                elif area_actual == "COLECTORAS":
                    c1, c2 = st.columns(2); res_fields = {"total_cajas": c1.number_input("Cajas", 0), "total_formas": c2.number_input("Total Formas", 0)}
                elif area_actual == "ENCUADERNACIÓN":
                    c1, c2 = st.columns(2); res_fields = {"cant_final": c1.number_input("Cant. Final", 0), "presentacion": c2.text_input("Presentación")}

                dk = st.number_input("Desp (Kg)", 0.0); mot = st.text_input("Motivo Desp."); obs = st.text_area("Observaciones")
                
                if st.form_submit_button("💾 FINALIZAR"):
                    final_data = {"op": act['op'], "maquina": m, "trabajo": act['trabajo'], "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"), "desp_kg": dk, "motivo_desperdicio": mot, "observaciones": obs}
                    final_data.update(res_fields)
                    
                    # Transferencia selectiva para evitar errores de columna
                    columnas_validas = ["tipo_papel", "ancho", "gramaje", "medida_trabajo", "img_varilla", "medida_rollos", "unidades_caja", "formas_totales", "material", "medida"]
                    for col in columnas_validas:
                        if col in act: final_data[col] = act[col]
                    
                    supabase.table(normalizar(area_actual)).insert(final_data).execute()
                    supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                    st.rerun()
