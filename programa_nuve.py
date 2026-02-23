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

# --- ESTILOS (TU ORIGINAL) ---
st.markdown("""
    <style>
    .stButton > button { height: 75px; font-weight: bold; border-radius: 12px; font-size: 16px; border: 2px solid #0D47A1; }
    .card-proceso { padding: 15px; border-radius: 10px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; text-align: center; font-weight: bold; }
    .card-parada { padding: 15px; border-radius: 10px; background-color: #FFEBEE; border-left: 8px solid #C62828; text-align: center; font-weight: bold; }
    .card-libre { padding: 15px; border-radius: 10px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES CORE (TUS ORIGINALES) ---
def safe_float(val):
    try: return float(val) if val else 0.0
    except: return 0.0

def calcular_horas(inicio, fin):
    try:
        fmt = "%H:%M"
        h1 = datetime.strptime(inicio, fmt)
        h2 = datetime.strptime(fin, fmt)
        diff = (h2 - h1).total_seconds() / 3600
        return diff if diff > 0 else diff + 24
    except: return 0.0

def normalizar(t):
    return t.lower().replace("ó", "o").replace(" ", "_")

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2268/2268710.png", width=100)
    st.title("MENÚ")
    opcion = st.radio("Ir a:", ["🖥️ Monitor General", "🎮 Joysticks de Áreas", "📊 Consolidado Gerencial"])

# ==========================================
# 1. MONITOR GENERAL (BLOQUE ORIGINAL)
# ==========================================
if opcion == "🖥️ Monitor General":
    st.title("🖥️ Monitor de Planta en Tiempo Real")
    maquinas = ["M1", "M2", "M3", "C1", "C2", "COL1", "ENC1"]
    
    activos = supabase.table("trabajos_activos").select("*").execute().data
    paradas = supabase.table("paradas_maquina").select("*").filter("h_fin", "is", "null").execute().data
    
    cols = st.columns(4)
    for i, maq in enumerate(maquinas):
        with cols[i % 4]:
            st.subheader(maq)
            en_paro = next((p for p in paradas if p['maquina'] == maq), None)
            en_prog = next((a for a in activos if a['maquina'] == maq), None)
            
            if en_paro:
                st.markdown(f'<div class="card-parada">🚨 PARADA<br>{en_paro["motivo"]}</div>', unsafe_allow_html=True)
            elif en_prog:
                st.markdown(f'<div class="card-proceso">⚙️ OP: {en_prog["op"]}<br>{en_prog["trabajo"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="card-libre">✅ DISPONIBLE</div>', unsafe_allow_html=True)

# ==========================================
# 2. JOYSTICKS DE ÁREAS (BLOQUE ORIGINAL INTACTO)
# ==========================================
elif opcion == "🎮 Joysticks de Áreas":
    area_act = st.selectbox("Seleccione Área:", ["Impresión", "Corte", "Colectoras", "Encuadernación"])
    maqs = {"Impresión": ["M1", "M2", "M3"], "Corte": ["C1", "C2"], "Colectoras": ["COL1"], "Encuadernación": ["ENC1"]}
    maquina_act = st.selectbox("Máquina:", maqs[area_act])

    act = supabase.table("trabajos_activos").select("*").eq("maquina", maquina_act).execute().data
    par = supabase.table("paradas_maquina").select("*").eq("maquina", maquina_act).is_("h_fin", "null").execute().data
    
    act = act[0] if act else None
    par = par[0] if par else None

    # UI de Botones Original
    c1, c2, c3 = st.columns(3)

    if not act and not par:
        with c1:
            if st.button("▶️ INICIAR TRABAJO", use_container_width=True):
                with st.form("form_inicio"):
                    op = st.text_input("OP")
                    tr = st.text_input("Trabajo")
                    # Tus campos originales por área
                    res_ini = {}
                    if area_act == "Impresión":
                        res_ini['tipo_papel'] = st.selectbox("Papel", ["Bond", "Químico", "Térmico"])
                        res_ini['ancho'] = st.text_input("Ancho")
                        res_ini['gramaje'] = st.text_input("Gramaje")
                    elif area_act == "Corte":
                        res_ini['img_varilla'] = st.number_input("Imágenes", 1)
                    
                    if st.form_submit_button("Confirmar"):
                        d = {"maquina": maquina_act, "op": op, "trabajo": tr, "area": area_act, "hora_inicio": datetime.now().strftime("%H:%M")}
                        d.update(res_ini)
                        supabase.table("trabajos_activos").insert(d).execute()
                        st.rerun()

    if act and not par:
        with c2:
            if st.button("🚨 PARADA", use_container_width=True):
                mot = st.selectbox("Motivo", ["Mecánico", "Eléctrico", "Limpia", "Cambio"])
                if st.button("Registrar"):
                    supabase.table("paradas_maquina").insert({"maquina": maquina_act, "op": act['op'], "motivo": mot, "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                    st.rerun()
        with c3:
            if st.button("🏁 FINALIZAR", use_container_width=True):
                with st.form("form_fin"):
                    dk = st.number_input("Desperdicio Kg", 0.0)
                    res_fin = {}
                    if area_act == "Impresión": res_fin['metros_impresos'] = st.number_input("Metros")
                    elif area_act == "Corte": res_fin['total_rollos'] = st.number_input("Rollos")
                    
                    if st.form_submit_button("Cerrar OP"):
                        f_d = {"op": act['op'], "maquina": maquina_act, "trabajo": act['trabajo'], "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"), "desp_kg": dk}
                        f_d.update(res_fin)
                        supabase.table(normalizar(area_act)).insert(f_d).execute()
                        supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                        st.rerun()

    if par:
        if st.button("✅ REANUDAR"):
            supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
            st.rerun()

# ==========================================
# 3. CONSOLIDADO GERENCIAL (BLOQUE EDITADO)
# ==========================================
elif opcion == "📊 Consolidado Gerencial":
    st.title("📊 Consolidado y Resumen de Producción")

    try:
        # Carga de datos
        imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
        cor = pd.DataFrame(supabase.table("corte").select("*").execute().data)
        col = pd.DataFrame(supabase.table("colectoras").select("*").execute().data)
        enc = pd.DataFrame(supabase.table("encuadernacion").select("*").execute().data)
        par = pd.DataFrame(supabase.table("paradas_maquina").select("*").execute().data)

        # --- KPIs SUPERIORES ---
        st.subheader("💡 Indicadores Clave")
        k1, k2, k3, k4 = st.columns(4)
        
        hrs_p = 0.0
        if not par.empty:
            par['hrs'] = par.apply(lambda r: calcular_horas(str(r['h_inicio']), str(r['h_fin']) if r['h_fin'] else datetime.now().strftime("%H:%M")), axis=1)
            hrs_p = par['hrs'].sum()
        
        k1.metric("Tiempo Muerto", f"{hrs_p:.2f} Hrs")
        k2.metric("Metraje Total", f"{imp['metros_impresos'].sum():,.0f} m" if not imp.empty else "0 m")
        k3.metric("Total Rollos", f"{cor['total_rollos'].sum():,.0f}" if not cor.empty else "0")
        desp_t = (imp['desp_kg'].sum() if not imp.empty else 0) + (cor['desp_kg'].sum() if not cor.empty else 0)
        k4.metric("Desperdicio (I+C)", f"{desp_t:.1f} Kg")

        # --- PESTAÑAS ---
        t1, t2, t3, t4, t5, t6 = st.tabs(["🔗 Cruce Imp-Cor", "🚨 Paradas", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

        with t1:
            st.subheader("Seguimiento de OPs (Impresión vs Corte)")
            if not imp.empty and not cor.empty:
                m = pd.merge(imp[['op','trabajo','maquina','h_inicio','h_fin','metros_impresos','desp_kg']], 
                             cor[['op','maquina','h_inicio','h_fin','total_rollos','desp_kg']], 
                             on='op', how='left', suffixes=('_Imp', '_Cor'))
                st.dataframe(m, use_container_width=True)
            else: st.info("No hay datos suficientes para el cruce.")

        with t2:
            st.subheader("Análisis de Paradas")
            if not par.empty:
                st.dataframe(par, use_container_width=True)
                st.bar_chart(par.groupby('motivo')['hrs'].sum())
            else: st.info("Sin paradas registradas.")

        # Consolidados Individuales (Tu petición: Pestañas limpias)
        with t3: 
            st.subheader("Tabla Impresión")
            if not imp.empty: st.dataframe(imp, use_container_width=True)
            else: st.info("Sin datos")
        with t4: 
            st.subheader("Tabla Corte")
            if not cor.empty: st.dataframe(cor, use_container_width=True)
            else: st.info("Sin datos")
        with t5: 
            st.subheader("Tabla Colectoras")
            if not col.empty: st.dataframe(col, use_container_width=True)
            else: st.info("Sin datos")
        with t6: 
            st.subheader("Tabla Encuadernación")
            if not enc.empty: st.dataframe(enc, use_container_width=True)
            else: st.info("Sin datos")

    except Exception as e:
        st.error(f"Error en consolidado: {e}")
