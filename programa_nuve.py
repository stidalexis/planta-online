import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA PRODUCCIÓN", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 65px; font-weight: bold; border-radius: 10px; }
    .card-parada { padding: 10px; border-radius: 8px; background-color: #FFEBEE; border-left: 5px solid #C62828; text-align: center; }
    .card-proceso { padding: 10px; border-radius: 8px; background-color: #E8F5E9; border-left: 5px solid #2E7D32; text-align: center; }
    .card-libre { padding: 10px; border-radius: 8px; background-color: #F5F5F5; border-left: 5px solid #9E9E9E; text-align: center; }
    .title-area { background-color: #0D47A1; color: white; padding: 5px; border-radius: 5px; text-align: center; margin-top: 15px; }
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
def normalizar_tabla(texto):
    reemplazos = {"Í": "I", "Ó": "O", "Á": "A", "É": "E", "Ú": "U", " ": "_"}
    t = texto.upper()
    for k, v in reemplazos.items(): t = t.replace(k, v)
    return t.lower()

def safe_float(valor):
    try: return float(str(valor).replace(',', '.'))
    except: return 0.0

# --- NAVEGACIÓN ---
st.sidebar.title("🏭 PLANTA")
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
                if m in paradas: st.markdown(f"<div class='card-parada'>🚨 {m}<br><small>{paradas[m]['motivo']}</small></div>", unsafe_allow_html=True)
                elif m in activos: st.markdown(f"<div class='card-proceso'>⚙️ {m}<br>OP: {activos[m]['op']}</div>", unsafe_allow_html=True)
                else: st.markdown(f"<div class='card-libre'>⚪ {m}</div>", unsafe_allow_html=True)

# ==========================================
# 2. CONSOLIDADO (CON DATOS ORIGINALES)
# ==========================================
elif seleccion == "📊 Consolidado Gerencial":
    st.title("📊 Resumen de Producción")
    df_imp = pd.DataFrame(supabase.table("impresion").select("*").execute().data)
    if not df_imp.empty:
        st.dataframe(df_imp, use_container_width=True)
        st.metric("Total Kilos Impresos", f"{round(df_imp['metros_impresos'].sum() * 0.05, 2)} Kg (Est.)") # Ejemplo de cálculo
    else:
        st.info("No hay datos registrados aún.")

# ==========================================
# 3. JOYSTICKS DE ÁREA
# ==========================================
else:
    area_actual = seleccion.replace("🖨️ ", "").replace("✂️ ", "").replace("📥 ", "").replace("📕 ", "").upper()
    st.title(f"Control: {area_actual}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    m = st.selectbox("Seleccione Máquina:", MAQUINAS[area_actual])
    act, par = activos.get(m), paradas.get(m)

    if par:
        st.error(f"🚨 MÁQUINA PARADA: {par['motivo']}")
        if st.button("✅ REANUDAR TRABAJO"):
            supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
            st.rerun()

    elif not act:
        with st.form("inicio"):
            st.subheader(f"🚀 Iniciar en {m}")
            c1, c2 = st.columns(2)
            
            # FLUJO INTELIGENTE PARA CORTE (Lee de Impresión)
            if area_actual == "CORTE":
                ops_imp = [d['op'] for d in supabase.table("impresion").select("op").execute().data]
                op = c1.selectbox("Seleccione OP (de Impresión)", [""] + list(set(ops_imp)))
                tr = c2.text_input("Trabajo")
            else:
                op = c1.text_input("OP")
                tr = c2.text_input("Trabajo")

            # TODAS LAS CASILLAS ORIGINALES SEGÚN EL ÁREA
            extra = {}
            if area_actual == "IMPRESIÓN":
                k1, k2, k3, k4 = st.columns(4)
                extra = {"tipo_papel": k1.text_input("Papel"), "ancho": k2.text_input("Ancho"), "gramaje": k3.text_input("Gramaje"), "medida_trabajo": k4.text_input("Medida")}
            elif area_actual == "CORTE":
                k1, k2, k3, k4 = st.columns(4)
                extra = {"tipo_papel": k1.text_input("Papel"), "img_varilla": k2.number_input("Img/Varilla", 0), "medida_rollos": k3.text_input("Medida Rollos"), "unidades_caja": k4.number_input("Und/Caja", 0)}
            elif area_actual == "COLECTORAS":
                k1, k2, k3 = st.columns(3)
                extra = {"tipo_papel": k1.text_input("Papel"), "medida_trabajo": k2.text_input("Medida"), "unidades_caja": k3.number_input("Und/Caja", 0)}
            elif area_actual == "ENCUADERNACIÓN":
                k1, k2, k3 = st.columns(3)
                extra = {"formas_totales": k1.number_input("Formas Totales", 0), "material": k2.text_input("Material"), "medida": k3.text_input("Medida")}

            if st.form_submit_button("EMPEZAR"):
                if op and tr:
                    data = {"maquina": m, "op": op, "trabajo": tr, "area": area_actual, "hora_inicio": datetime.now().strftime("%H:%M")}
                    data.update(extra)
                    supabase.table("trabajos_activos").insert(data).execute()
                    st.rerun()
    else:
        st.success(f"En producción: OP {act['op']} - {act['trabajo']}")
        
        # BOTÓN DE PARADA
        if st.button("🚨 INICIAR PARADA (AVERÍA/LIMPIEZA)"):
            motivo_p = st.selectbox("Motivo", ["Mecánico", "Eléctrico", "Cambio Formato", "Limpieza"])
            supabase.table("paradas_maquina").insert({"maquina": m, "op": act['op'], "motivo": motivo_p, "h_inicio": datetime.now().strftime("%H:%M")}).execute()
            st.rerun()

        st.divider()
        
        # FORMULARIO DE CIERRE CON TODAS LAS CASILLAS ORIGINALES
        with st.form("cierre"):
            st.subheader("🏁 Finalizar y Registrar")
            res = {}
            if area_actual == "IMPRESIÓN":
                f1, f2 = st.columns(2)
                res = {"metros_impresos": f1.number_input("Metros", 0.0), "bobinas": f2.number_input("Bobinas", 0)}
            elif area_actual == "CORTE":
                f1, f2, f3 = st.columns(3)
                res = {"cant_varillas": f1.number_input("Varillas", 0), "total_rollos": f2.number_input("Total Rollos", 0), "unidades_caja": f3.number_input("Unidades/Caja", 0)}
            elif area_actual == "COLECTORAS":
                f1, f2, f3 = st.columns(3)
                res = {"total_cajas": f1.number_input("Total Cajas", 0), "total_formas": f2.number_input("Total Formas", 0), "unidades_caja": f3.number_input("Unidades/Caja", 0)}
            elif area_actual == "ENCUADERNACIÓN":
                f1, f2 = st.columns(2)
                res = {"cant_final": f1.number_input("Cantidad Final", 0), "presentacion": f2.text_input("Presentación")}

            dk = st.number_input("Desperdicio (Kg)", 0.0)
            mot = st.text_input("Motivo Desperdicio")
            obs = st.text_input("Observaciones Generales")

            if st.form_submit_button("GUARDAR HISTORIAL"):
                nom_t = normalizar_tabla(area_actual)
                final_data = {
                    "op": act['op'], "maquina": m, "trabajo": act['trabajo'],
                    "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                    "desp_kg": dk, "motivo_desperdicio": mot, "observaciones": obs
                }
                final_data.update(res)
                
                # Mapeo de datos técnicos desde 'activos'
                for campo in ["tipo_papel", "ancho", "gramaje", "medida_trabajo", "img_varilla", "medida_rollos", "formas_totales", "material", "medida"]:
                    if campo in act and act[campo]:
                        final_data[campo] = safe_float(act[campo]) if campo in ["ancho", "gramaje"] else act[campo]

                supabase.table(nom_t).insert(final_data).execute()
                supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                st.rerun()
