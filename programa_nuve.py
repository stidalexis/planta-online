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

# --- ESTILOS ---
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
    st.title("MENÚ DE CONTROL")
    opcion = st.radio("Ir a:", ["🖥️ Monitor General", "🎮 Joysticks de Áreas", "📊 Consolidado Gerencial"])

# ==========================================
# 1. MONITOR GENERAL (ORIGINAL)
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
# 2. JOYSTICKS DE ÁREAS (ORIGINAL COMPLETO)
# ==========================================
elif opcion == "🎮 Joysticks de Áreas":
    area_act = st.selectbox("Seleccione Área:", ["Impresión", "Corte", "Colectoras", "Encuadernación"])
    maqs = {"Impresión": ["M1", "M2", "M3"], "Corte": ["C1", "C2"], "Colectoras": ["COL1"], "Encuadernación": ["ENC1"]}
    maquina_act = st.selectbox("Máquina:", maqs[area_act])

    act = supabase.table("trabajos_activos").select("*").eq("maquina", maquina_act).execute().data
    par = supabase.table("paradas_maquina").select("*").eq("maquina", maquina_act).is_("h_fin", "null").execute().data
    
    act = act[0] if act else None
    par = par[0] if par else None

    # Lógica de Inicio (Tu formulario original completo)
    if not act and not par:
        with st.form("form_inicio"):
            st.subheader(f"🚀 Iniciar en {maquina_act}")
            c1, c2 = st.columns(2)
            op = c1.text_input("Orden de Producción (OP)")
            tr = c2.text_input("Nombre del Trabajo")
            
            # Campos originales por área
            ext = {}
            if area_act == "Impresión":
                ext['tipo_papel'] = st.selectbox("Tipo Papel", ["Bond", "Químico", "Térmico"])
                ext['ancho'] = st.text_input("Ancho (mm)")
                ext['gramaje'] = st.text_input("Gramaje")
                ext['medida_trabajo'] = st.text_input("Medida Trabajo")
            elif area_act == "Corte":
                ext['img_varilla'] = st.number_input("Imágenes por Varilla", 1)
                ext['medida_rollos'] = st.text_input("Medida de Rollos")
                ext['unidades_caja'] = st.number_input("Unidades por Caja", 1)
            
            if st.form_submit_button("CONFIRMAR INICIO"):
                data = {"maquina": maquina_act, "op": op, "trabajo": tr, "area": area_act, "hora_inicio": datetime.now().strftime("%H:%M")}
                data.update(ext)
                supabase.table("trabajos_activos").insert(data).execute()
                st.rerun()

    # Lógica de Parada
    if act and not par:
        if st.button("🚨 REGISTRAR PARADA", use_container_width=True):
            mot = st.selectbox("Motivo:", ["Mecánico", "Cambio Color", "Falta Material", "Ajuste"])
            if st.button("Confirmar Parada"):
                supabase.table("paradas_maquina").insert({"maquina": maquina_act, "op": act['op'], "motivo": mot, "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                st.rerun()

    # Lógica de Finalización (Tu lógica original de inserción)
    if act and not par:
        with st.form("form_final"):
            st.subheader("🏁 Finalizar y Reportar")
            dk = st.number_input("Desperdicio (Kg)", 0.0)
            mot = st.text_input("Motivo Desperdicio")
            obs = st.text_area("Observaciones")
            
            res = {}
            if area_act == "Impresión":
                res['metros_impresos'] = st.number_input("Metros Impresos", 0)
                res['bobinas'] = st.number_input("Bobinas", 0)
            elif area_act == "Corte":
                res['total_rollos'] = st.number_input("Total Rollos", 0)
                res['cant_varillas'] = st.number_input("Varillas", 0)

            if st.form_submit_button("GUARDAR EN HISTORIAL"):
                final_data = {
                    "op": act['op'], "maquina": maquina_act, "trabajo": act['trabajo'],
                    "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                    "desp_kg": dk, "motivo_desperdicio": mot, "observaciones": obs
                }
                final_data.update(res)
                
                # Mapeo de columnas adicionales originales
                nom_t = normalizar(area_act)
                supabase.table(nom_t).insert(final_data).execute()
                supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                st.success("¡Datos guardados!")
                st.rerun()

    if par:
        if st.button("✅ REANUDAR"):
            supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
            st.rerun()

# ==========================================
# 3. CONSOLIDADO GERENCIAL (CAMBIOS ACORDADOS)
# ==========================================
elif opcion == "📊 Consolidado Gerencial":
    st.title("📊 Reporte de Inteligencia de Planta")
    
    try:
        # Carga masiva para reportes
        imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
        cor = pd.DataFrame(supabase.table("corte").select("*").execute().data)
        par = pd.DataFrame(supabase.table("paradas_maquina").select("*").execute().data)
        col = pd.DataFrame(supabase.table("colectoras").select("*").execute().data)
        enc = pd.DataFrame(supabase.table("encuadernacion").select("*").execute().data)

        # Métrica de Tiempo Muerto (Calculado)
        hrs_paro = 0.0
        if not par.empty:
            par['duracion'] = par.apply(lambda r: calcular_horas(r['h_inicio'], r['h_fin'] if r['h_fin'] else datetime.now().strftime("%H:%M")), axis=1)
            hrs_paro = par['duracion'].sum()

        # KPIs superiores
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Tiempo Muerto", f"{hrs_paro:.2f} Hrs")
        k2.metric("Producción Imp", f"{imp['metros_impresos'].sum():,.0f} m" if not imp.empty else "0")
        k3.metric("Producción Corte", f"{cor['total_rollos'].sum():,.0f} rollos" if not cor.empty else "0")
        k4.metric("Desperdicio", f"{(imp['desp_kg'].sum() if not imp.empty else 0) + (cor['desp_kg'].sum() if not cor.empty else 0):.1f} Kg")

        tabs = st.tabs(["🔗 Cruce Imp-Cor", "🚨 Paradas", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

        with tabs[0]:
            st.subheader("Eficiencia Cruzada")
            if not imp.empty and not cor.empty:
                df_cruce = pd.merge(imp[['op','trabajo','metros_impresos','desp_kg']], cor[['op','total_rollos','desp_kg']], on='op', suffixes=('_Imp', '_Cor'), how='left')
                st.dataframe(df_cruce, use_container_width=True)
            else: st.info("Faltan datos para realizar el cruce.")

        with tabs[1]:
            st.subheader("Detalle de Paradas")
            if not par.empty:
                st.dataframe(par[['fecha','maquina','op','motivo','h_inicio','h_fin','duracion']], use_container_width=True)
                st.bar_chart(par.groupby('motivo')['duracion'].sum())

        # Pestañas individuales protegidas contra el error DeltaGenerator
        with tabs[2]:
             if not imp.empty: st.dataframe(imp, use_container_width=True)
             else: st.info("Sin registros.")
        with tabs[3]:
             if not cor.empty: st.dataframe(cor, use_container_width=True)
             else: st.info("Sin registros.")
        with tabs[4]:
             if not col.empty: st.dataframe(col, use_container_width=True)
             else: st.info("Sin registros.")
        with tabs[5]:
             if not enc.empty: st.dataframe(enc, use_container_width=True)
             else: st.info("Sin registros.")

    except Exception as e:
        st.error(f"Error en consolidado: {e}")
