import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA DE PRODUCCIÓN", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 75px; font-weight: bold; border-radius: 12px; font-size: 16px; border: 2px solid #0D47A1; }
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
        return round((t_fin - t_ini).total_seconds() / 3600, 2)
    except: return 0.0

# --- NAVEGACIÓN ---
st.sidebar.title("🏭 MENÚ PRINCIPAL")
opcion = st.sidebar.radio("Ir a:", ["🖥️ Monitor General", "📊 Consolidado Gerencial", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# ==========================================
# 1. MONITOR GENERAL
# ==========================================
if opcion == "🖥️ Monitor General":
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
# 2. CONSOLIDADO GERENCIAL (PRODUCCIÓN & EFICIENCIA)
# ==========================================
elif opcion == "📊 Consolidado Gerencial":
    st.title("📊 Reporte de Eficiencia y Tiempos Muertos")

    try:
        # Carga de datos base [cite: 2, 3, 4, 5, 7, 8]
        imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
        cor = pd.DataFrame(supabase.table("corte").select("*").execute().data)
        paradas = pd.DataFrame(supabase.table("paradas_maquina").select("*").execute().data)
        col = pd.DataFrame(supabase.table("colectoras").select("*").execute().data)
        enc = pd.DataFrame(supabase.table("encuadernacion").select("*").execute().data)

        # --- SECCIÓN DE MÉTRICAS GLOBALES (KPIs) ---
        st.subheader("💡 Resumen Ejecutivo")
        k1, k2, k3, k4 = st.columns(4)
        
        if not paradas.empty:
            # Calculamos horas totales perdidas 
            paradas['horas_paro'] = paradas.apply(lambda r: calcular_horas(str(r['h_inicio']), str(r['h_fin'])), axis=1)
            total_paro = paradas['horas_paro'].sum()
            k1.metric("Tiempo Muerto Total", f"{total_paro:.2f} Hrs", delta_color="inverse")
            
            # Motivo más frecuente 
            top_motivo = paradas['motivo'].mode()[0] if not paradas['motivo'].empty else "N/A"
            k2.metric("Principal Causa Paro", top_motivo)

        if not imp.empty:
            total_metros = imp['metros_impresos'].sum()
            k3.metric("Metraje Total", f"{total_metros:,.0f} m")
            
            total_desp = imp['desp_kg'].sum() + (cor['desp_kg'].sum() if not cor.empty else 0)
            k4.metric("Desperdicio Total", f"{total_desp:.2f} Kg", delta="-5%" if total_desp > 0 else "0%")

        # --- TABS DE ANÁLISIS DETALLADO ---
        t1, t2, t3 = st.tabs(["🔗 Cruce Operativo", "🚨 Análisis de Paradas", "📈 Rendimiento por Área"])

        with t1:
            st.subheader("Seguimiento de OPs (Flujo Impresión -> Corte)")
            if not imp.empty:
                # Unimos datos de Impresión y Corte 
                df_i = imp[['op', 'trabajo', 'maquina', 'h_inicio', 'h_fin', 'metros_impresos', 'desp_kg']].copy()
                df_i.columns = ['OP', 'TRABAJO', 'MAQ_IMP', 'INI_I', 'FIN_I', 'METROS', 'DESP_I']
                
                df_c = cor[['op', 'maquina', 'h_inicio', 'h_fin', 'total_rollos', 'desp_kg']].copy() if not cor.empty else pd.DataFrame(columns=['op'])
                df_c.columns = ['OP', 'MAQ_COR', 'INI_C', 'FIN_C', 'ROLLOS', 'DESP_C'] if not cor.empty else ['OP']

                merged = pd.merge(df_i, df_c, on='OP', how='left')
                
                # Cálculo de Lead Time (Tiempo total desde inicio Imp hasta fin Corte) 
                merged['LEAD_TIME_HRS'] = merged.apply(lambda r: calcular_horas(str(r['INI_I']), str(r.get('FIN_C', r['FIN_I']))), axis=1)
                
                st.dataframe(merged, use_container_width=True)

        with t2:
            st.subheader("Registro de Tiempos Perdidos por Máquina")
            if not paradas.empty:
                # Tabla de paradas con duración 
                st.dataframe(paradas[['maquina', 'op', 'motivo', 'h_inicio', 'h_fin', 'horas_paro', 'fecha']], use_container_width=True)
                
                # Gráfico rápido de motivos (Streamlit nativo)
                st.bar_chart(paradas.groupby('motivo')['horas_paro'].sum())
            else:
                st.info("No se registran paradas de máquina.")

        with t3:
            # Vista simplificada para gerencia de otras áreas [cite: 7, 8]
            c_col, c_enc = st.columns(2)
            with c_col:
                st.write("📥 **Colectoras**")
                if not col.empty: st.write(f"Cajas totales: {col['total_cajas'].sum()}")
            with c_enc:
                st.write("📕 **Encuadernación**")
                if not enc.empty: st.write(f"Total Formas: {enc['cant_final'].sum()}")

    except Exception as e:
        st.error(f"Error en consolidado: {e}")

# ==========================================
# 3. JOYSTICKS DE ÁREA
# ==========================================
else:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_act = area_map[opcion]
    st.title(f"Joystick: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    # SELECCIÓN VISUAL POR BOTONES
    cols_m = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS[area_act]):
        label = m_btn
        if m_btn in paradas: label = f"🚨 {m_btn}"
        elif m_btn in activos: label = f"⚙️ {m_btn}\nOP: {activos[m_btn]['op']}"
        
        if cols_m[i % 4].button(label, key=f"btn_{m_btn}", use_container_width=True):
            st.session_state.m_sel = m_btn

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        act, par = activos.get(m), paradas.get(m)
        st.divider()

        if par:
            st.error(f"⚠️ MÁQUINA EN PARADA: {par['motivo']}")
            if st.button("REANUDAR"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()

        elif not act:
            with st.form("inicio"):
                st.subheader(f"🚀 Iniciar OP en {m}")
                c1, c2 = st.columns(2)
                op = c1.text_input("Número de OP")
                tr = c2.text_input("Nombre del Trabajo")
                
                extra = {}
                if area_act == "IMPRESIÓN":
                    k1, k2, k3, k4 = st.columns(4)
                    extra = {"tipo_papel": k1.text_input("Papel"), "ancho": k2.text_input("Ancho"), "gramaje": k3.text_input("Gramaje"), "medida_trabajo": k4.text_input("Medida")}
                elif area_act == "CORTE":
                    k1, k2, k3, k4 = st.columns(4)
                    extra = {"tipo_papel": k1.text_input("Papel"), "img_varilla": k2.number_input("Img/Varilla", 0), "medida_rollos": k3.text_input("Medida Rollos"), "unidades_caja": k4.number_input("Und/Caja", 0)}
                elif area_act == "COLECTORAS":
                    k1, k2, k3 = st.columns(3)
                    extra = {"tipo_papel": k1.text_input("Papel"), "medida_trabajo": k2.text_input("Medida"), "unidades_caja": k3.number_input("Und/Caja", 0)}
                elif area_act == "ENCUADERNACIÓN":
                    k1, k2, k3 = st.columns(3)
                    extra = {"formas_totales": k1.number_input("Formas Totales", 0), "material": k2.text_input("Material"), "medida": k3.text_input("Medida")}

                if st.form_submit_button("EMPEZAR"):
                    if op and tr:
                        data = {"maquina": m, "op": op, "trabajo": tr, "area": area_act, "hora_inicio": datetime.now().strftime("%H:%M")}
                        data.update(extra)
                        supabase.table("trabajos_activos").insert(data).execute()
                        st.rerun()
        else:
            if st.button("🚨 REGISTRAR PARADA"):
                mot_p = st.selectbox("Motivo", ["Mecánico", "Eléctrico", "Cambio Rollo", "Limpieza"])
                supabase.table("paradas_maquina").insert({"maquina": m, "op": act['op'], "motivo": mot_p, "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                st.rerun()

            with st.form("cierre"):
                st.info(f"Finalizando OP: {act['op']}")
                res = {}
                if area_act == "IMPRESIÓN":
                    f1, f2 = st.columns(2); res = {"metros_impresos": f1.number_input("Metros", 0.0), "bobinas": f2.number_input("Bobinas", 0)}
                elif area_act == "CORTE":
                    f1, f2, f3 = st.columns(3); res = {"total_rollos": f1.number_input("Rollos", 0), "cant_varillas": f2.number_input("Varillas", 0), "unidades_caja": f3.number_input("Unidades/Caja", 0)}
                elif area_act == "COLECTORAS":
                    f1, f2 = st.columns(2); res = {"total_cajas": f1.number_input("Cajas", 0), "total_formas": f2.number_input("Formas Totales", 0)}
                elif area_act == "ENCUADERNACIÓN":
                    f1, f2 = st.columns(2); res = {"cant_final": f1.number_input("Cantidad Final", 0), "presentacion": f2.text_input("Presentación")}

                dk = st.number_input("Desperdicio (Kg)", 0.0)
                mot = st.text_input("Motivo Desperdicio")
                obs = st.text_input("Observaciones")

                if st.form_submit_button("🏁 FINALIZAR"):
                    final_data = {
                        "op": act['op'], "maquina": m, "trabajo": act['trabajo'],
                        "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                        "desp_kg": safe_float(dk), "motivo_desperdicio": mot, "observaciones": obs
                    }
                    final_data.update(res)
                    
                    # --- FILTRADO DE COLUMNAS PARA EVITAR PGRST204 ---
                    nom_t = normalizar(area_act)
                    # Campos permitidos por tabla
                    cols_permitidas = {
                        "impresion": ["tipo_papel", "ancho", "gramaje", "medida_trabajo"],
                        "corte": ["tipo_papel", "ancho", "gramaje", "img_varilla", "medida_rollos", "unidades_caja"],
                        "colectoras": ["tipo_papel", "medida_trabajo", "unidades_caja"],
                        "encuadernacion": ["formas_totales", "material", "medida"]
                    }

                    for col in cols_permitidas.get(nom_t, []):
                        if col in act and act[col] is not None:
                            if col in ["ancho", "gramaje"]: final_data[col] = safe_float(act[col])
                            else: final_data[col] = act[col]

                    try:
                        supabase.table(nom_t).insert(final_data).execute()
                        supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error de guardado: {e}")


