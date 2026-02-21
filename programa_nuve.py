import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="PRODUCCIÓN 360", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 75px; font-weight: bold; border-radius: 12px; font-size: 16px; border: 2px solid #0D47A1; }
    .card-proceso { padding: 15px; border-radius: 10px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; text-align: center; }
    .card-parada { padding: 15px; border-radius: 10px; background-color: #FFEBEE; border-left: 8px solid #C62828; text-align: center; }
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
        diff = (t_fin - t_ini).total_seconds() / 3600
        return round(diff if diff > 0 else diff + 24, 2)
    except: return 0.0

# --- NAVEGACIÓN ---
st.sidebar.title("🏭 PLANTA ONLINE")
opcion = st.sidebar.radio("Menú:", ["🖥️ Monitor General", "📊 Consolidado Gerencial", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

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
                else: st.markdown(f"<div class='card-libre' style='text-align:center; padding:15px; border:1px solid #ccc; border-radius:10px;'>⚪ {m}</div>", unsafe_allow_html=True)

# ==========================================
# 2. CONSOLIDADO GERENCIAL (FILA ÚNICA POR OP)
# ==========================================
elif opcion == "📊 Consolidado Gerencial":
    st.title("📊 Seguimiento de Producción por OP")
    
    imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
    cor = pd.DataFrame(supabase.table("corte").select("*").execute().data)
    col = pd.DataFrame(supabase.table("colectoras").select("*").execute().data)
    enc = pd.DataFrame(supabase.table("encuadernacion").select("*").execute().data)

    if not imp.empty:
        # Iniciamos con Impresión como base
        df = imp[['op', 'trabajo', 'maquina', 'h_inicio', 'h_fin', 'ancho', 'gramaje', 'metros_impresos', 'desp_kg']].copy()
        df.columns = ['OP', 'TRABAJO', 'MAQ_IMP', 'INI_IMP', 'FIN_IMP', 'ANCHO', 'GRAM', 'METROS', 'DESP_IMP']
        
        # Cálculo Kilos Entrantes (Fórmula)
        df['KG_ENTRADA'] = df.apply(lambda r: round(((safe_float(r['ANCHO'])/1000) * safe_float(r['METROS']) * safe_float(r['GRAM']))/100, 2), axis=1)

        # Merge con Corte
        if not cor.empty:
            cor_sub = cor[['op', 'maquina', 'total_rollos', 'desp_kg']].copy()
            cor_sub.columns = ['OP', 'MAQ_COR', 'ROLLOS', 'DESP_COR']
            df = pd.merge(df, cor_sub, on='OP', how='left')

        # Merge con Colectoras
        if not col.empty:
            col_sub = col[['op', 'total_cajas', 'total_formas']].copy()
            col_sub.columns = ['OP', 'CAJAS_COL', 'FORMAS_COL']
            df = pd.merge(df, col_sub, on='OP', how='left')

        # Totales por Fila
        df['DESP_TOTAL_KG'] = df.apply(lambda r: safe_float(r['DESP_IMP']) + safe_float(r.get('DESP_COR', 0)), axis=1)
        df['%_MERMA'] = df.apply(lambda r: f"{round((r['DESP_TOTAL_KG']/r['KG_ENTRADA']*100),1)}%" if r['KG_ENTRADA']>0 else "0%", axis=1)

        # Mostrar Tabla
        st.dataframe(df.fillna("-"), use_container_width=True)
        
        
    else:
        st.info("Aún no hay datos en Impresión para consolidar.")

# ==========================================
# 3. JOYSTICKS DE ÁREA (CUADROS VISUALES)
# ==========================================
else:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_act = area_map[opcion]
    st.title(f"Área: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    # SELECCIÓN VISUAL (CUADROS)
    m_cols = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS[area_act]):
        label = m_btn
        if m_btn in paradas: label = f"🚨 {m_btn}"
        elif m_btn in activos: label = f"⚙️ {m_btn}\nOP: {activos[m_btn]['op']}"
        
        if m_cols[i % 4].button(label, key=f"btn_{m_btn}", use_container_width=True):
            st.session_state.m_sel = m_btn

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        act, par = activos.get(m), paradas.get(m)
        st.divider()

        if not act:
            with st.form("inicio"):
                st.subheader(f"🚀 Iniciar {m}")
                c1, c2 = st.columns(2)
                op = c1.text_input("N° OP")
                tr = c2.text_input("Trabajo")
                extra = {}
                if area_act == "IMPRESIÓN":
                    k1, k2, k3 = st.columns(3)
                    extra = {"tipo_papel": k1.text_input("Papel"), "ancho": k2.text_input("Ancho mm"), "gramaje": k3.text_input("Gramaje")}
                elif area_act == "CORTE":
                    k1, k2 = st.columns(2)
                    extra = {"img_varilla": k1.number_input("Img/Var", 0), "medida_rollos": k2.text_input("Medida")}
                
                if st.form_submit_button("✅ EMPEZAR"):
                    if op and tr:
                        data = {"maquina": m, "op": op, "trabajo": tr, "area": area_act, "hora_inicio": datetime.now().strftime("%H:%M")}
                        data.update(extra)
                        supabase.table("trabajos_activos").insert(data).execute()
                        st.rerun()
        else:
            # Máquina Trabajando
            st.success(f"TRABAJANDO EN OP {act['op']}")
            if st.button("🚨 NOTIFICAR PARADA"):
                supabase.table("paradas_maquina").insert({"maquina": m, "op": act['op'], "motivo": "Ajuste", "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                st.rerun()

            with st.form("cierre"):
                res = {}
                if area_act == "IMPRESIÓN":
                    f1, f2 = st.columns(2); res = {"metros_impresos": f1.number_input("Metros", 0.0), "bobinas": f2.number_input("Bobinas", 0)}
                elif area_act == "CORTE":
                    f1, f2 = st.columns(2); res = {"total_rollos": f1.number_input("Rollos", 0), "cant_varillas": f2.number_input("Varillas", 0)}
                
                dk = st.number_input("Kilos Desperdicio", 0.0)
                mot = st.text_input("Motivo Merma")

                if st.form_submit_button("🏁 FINALIZAR Y GUARDAR"):
                    final_data = {
                        "op": act['op'], "maquina": m, "trabajo": act['trabajo'],
                        "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                        "desp_kg": dk, "motivo_desperdicio": mot
                    }
                    final_data.update(res)

                    # FILTRO DE COLUMNAS PARA EVITAR APIERROR
                    nom_t = normalizar(area_act)
                    columnas_validas = {
                        "impresion": ["tipo_papel", "ancho", "gramaje"],
                        "corte": ["tipo_papel", "ancho", "gramaje", "img_varilla", "medida_rollos"],
                        "colectoras": ["tipo_papel", "unidades_caja"],
                        "encuadernacion": ["material", "medida"]
                    }

                    for col in columnas_validas.get(nom_t, []):
                        if col in act:
                            final_data[col] = safe_float(act[col]) if col in ["ancho", "gramaje"] else act[col]

                    try:
                        supabase.table(nom_t).insert(final_data).execute()
                        supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
