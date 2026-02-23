import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA DE PRODUCCIÓN INTEGRAL", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS CSS (ORIGINALES + MEJORAS) ---
st.markdown("""
    <style>
    .stButton > button { height: 75px; font-weight: bold; border-radius: 12px; font-size: 16px; border: 2px solid #0D47A1; }
    .card-proceso { padding: 15px; border-radius: 10px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; text-align: center; font-weight: bold; }
    .card-parada { padding: 15px; border-radius: 10px; background-color: #FFEBEE; border-left: 8px solid #C62828; text-align: center; font-weight: bold; }
    .card-libre { padding: 15px; border-radius: 10px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES CORE ---
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
    st.image("https://cdn-icons-png.flaticon.com/512/2268/2268710.png", width=80)
    st.title("MENÚ PRINCIPAL")
    opcion = st.radio("Ir a:", ["🖥️ Monitor General", "🎮 Joysticks de Áreas", "📊 Consolidado Gerencial"])

# ==========================================
# 1. MONITOR GENERAL (Igual al Original)
# ==========================================
if opcion == "🖥️ Monitor General":
    st.title("🖥️ Monitor de Planta en Tiempo Real")
    maquinas = {
        "Impresión": ["M1", "M2", "M3"],
        "Corte": ["C1", "C2"],
        "Colectoras": ["COL1"],
        "Encuadernación": ["ENC1"]
    }
    
    activos = supabase.table("trabajos_activos").select("*").execute().data
    paradas = supabase.table("paradas_maquina").select("*").filter("h_fin", "is", "null").execute().data
    
    for area, lista in maquinas.items():
        st.subheader(f"Área: {area}")
        cols = st.columns(len(lista))
        for i, maq in enumerate(lista):
            with cols[i]:
                st.write(f"**{maq}**")
                en_paro = next((p for p in paradas if p['maquina'] == maq), None)
                en_prog = next((a for a in activos if a['maquina'] == maq), None)
                
                if en_paro:
                    st.markdown(f'<div class="card-parada">🚨 PARADA<br>{en_paro["motivo"]}</div>', unsafe_allow_html=True)
                elif en_prog:
                    st.markdown(f'<div class="card-proceso">⚙️ OP: {en_prog["op"]}<br>{en_prog["trabajo"]}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="card-libre">✅ DISPONIBLE</div>', unsafe_allow_html=True)

# ==========================================
# 2. JOYSTICKS DE ÁREAS (RESTAURADO COMPLETO)
# ==========================================
elif opcion == "🎮 Joysticks de Áreas":
    area_sel = st.selectbox("Seleccione Área:", ["Impresión", "Corte", "Colectoras", "Encuadernación"])
    maqs = {"Impresión": ["M1", "M2", "M3"], "Corte": ["C1", "C2"], "Colectoras": ["COL1"], "Encuadernación": ["ENC1"]}
    maquina_sel = st.selectbox("Máquina:", maqs[area_sel])

    # Estado actual
    act = supabase.table("trabajos_activos").select("*").eq("maquina", maquina_sel).execute().data
    par = supabase.table("paradas_maquina").select("*").eq("maquina", maquina_sel).is_("h_fin", "null").execute().data
    
    act = act[0] if act else None
    par = par[0] if par else None

    # Lógica de Botones (Tu lógica original)
    c1, c2, c3 = st.columns(3)

    # BOTÓN INICIAR
    if not act and not par:
        with c1:
            if st.button("▶️ INICIAR TRABAJO", use_container_width=True):
                with st.form("form_inicio"):
                    st.write("Datos de la OP")
                    op = st.text_input("Orden de Producción (OP)")
                    tr = st.text_input("Nombre del Trabajo")
                    if st.form_submit_button("Confirmar Inicio"):
                        data = {"maquina": maquina_sel, "op": op, "trabajo": tr, "area": area_sel, "hora_inicio": datetime.now().strftime("%H:%M")}
                        supabase.table("trabajos_activos").insert(data).execute()
                        st.rerun()

    # BOTÓN PARADA
    if act and not par:
        with c2:
            if st.button("⚠️ REGISTRAR PARADA", use_container_width=True):
                motivo = st.selectbox("Motivo:", ["Mecánico", "Eléctrico", "Falta Material", "Cambio de Trabajo"])
                if st.button("Confirmar Parada"):
                    supabase.table("paradas_maquina").insert({
                        "maquina": maquina_sel, "op": act['op'], "motivo": motivo, 
                        "h_inicio": datetime.now().strftime("%H:%M")
                    }).execute()
                    st.rerun()

    # BOTÓN FINALIZAR
    if act and not par:
        with c3:
            if st.button("🏁 FINALIZAR TRABAJO", use_container_width=True):
                st.subheader("Reporte Final de Producción")
                with st.form("form_final"):
                    dk = st.number_input("Desperdicio (Kg)", min_value=0.0)
                    mot = st.text_input("Motivo Desperdicio")
                    obs = st.text_area("Observaciones")
                    
                    # Campos específicos según área
                    res_extra = {}
                    if area_sel == "Impresión":
                        res_extra['metros_impresos'] = st.number_input("Metros Impresos", min_value=0)
                    elif area_sel == "Corte":
                        res_extra['total_rollos'] = st.number_input("Total Rollos", min_value=0)

                    if st.form_submit_button("Guardar y Cerrar"):
                        final_data = {
                            "op": act['op'], "maquina": maquina_sel, "trabajo": act['trabajo'],
                            "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                            "desp_kg": dk, "motivo_desperdicio": mot, "observaciones": obs
                        }
                        final_data.update(res_extra)
                        supabase.table(normalizar(area_sel)).insert(final_data).execute()
                        supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                        st.success("Trabajo Guardado!")
                        st.rerun()

    if par:
        if st.button("✅ REANUDAR TRABAJO"):
            supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
            st.rerun()

# ==========================================
# 3. CONSOLIDADO GERENCIAL (NUEVA VERSIÓN)
# ==========================================
elif opcion == "📊 Consolidado Gerencial":
    st.title("📊 Reporte Gerencial de Producción")
    
    try:
        # Carga de datos
        imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
        cor = pd.DataFrame(supabase.table("corte").select("*").execute().data)
        par = pd.DataFrame(supabase.table("paradas_maquina").select("*").execute().data)
        col = pd.DataFrame(supabase.table("colectoras").select("*").execute().data)
        enc = pd.DataFrame(supabase.table("encuadernacion").select("*").execute().data)

        # KPIs
        k1, k2, k3 = st.columns(3)
        k1.metric("Metros Totales", f"{imp['metros_impresos'].sum():,.0f} m" if not imp.empty else "0")
        k2.metric("Rollos Producidos", f"{cor['total_rollos'].sum():,.0f}" if not cor.empty else "0")
        k3.metric("Desperdicio Total", f"{(imp['desp_kg'].sum() if not imp.empty else 0) + (cor['desp_kg'].sum() if not cor.empty else 0):.1f} Kg")

        t1, t2, t3, t4, t5, t6 = st.tabs(["🔗 Cruce Imp-Cor", "🚨 Paradas", "🖨️ Imp", "✂️ Cor", "📥 Col", "📕 Enc"])

        with t1:
            if not imp.empty and not cor.empty:
                merged = pd.merge(imp[['op','trabajo','metros_impresos']], cor[['op','total_rollos','desp_kg']], on='op', how='left')
                st.dataframe(merged, use_container_width=True)
            else: st.info("Datos insuficientes para cruce")

        with t2:
            if not par.empty:
                par['hrs'] = par.apply(lambda r: calcular_horas(r['h_inicio'], r['h_fin'] if r['h_fin'] else "00:00"), axis=1)
                st.dataframe(par, use_container_width=True)
                st.bar_chart(par.groupby('motivo')['hrs'].sum())
            else: st.info("Sin paradas")

        # Pestañas individuales sin el error de DeltaGenerator
        with t3: 
            if not imp.empty: st.dataframe(imp, use_container_width=True)
            else: st.info("Vacío")
        with t4:
            if not cor.empty: st.dataframe(cor, use_container_width=True)
            else: st.info("Vacío")
        with t5:
            if not col.empty: st.dataframe(col, use_container_width=True)
            else: st.info("Vacío")
        with t6:
            if not enc.empty: st.dataframe(enc, use_container_width=True)
            else: st.info("Vacío")

    except Exception as e:
        st.error(f"Error: {e}")
