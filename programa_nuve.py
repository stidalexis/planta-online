import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA PLANTA FULL", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 70px; font-weight: bold; border-radius: 12px; }
    .card-proceso { padding: 15px; border-radius: 10px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; text-align: center; }
    .card-parada { padding: 15px; border-radius: 10px; background-color: #FFEBEE; border-left: 8px solid #C62828; text-align: center; }
    .card-libre { padding: 15px; border-radius: 10px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; }
    </style>
    """, unsafe_allow_html=True)

# --- MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- FUNCIONES AUXILIARES ---
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
opcion = st.sidebar.radio("Menú:", ["🖥️ Monitor", "📊 Consolidado Gerencial", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# ==========================================
# MONITOR Y CONSOLIDADO (Omitidos aquí para brevedad, pero se mantienen igual que la versión anterior)
# ==========================================

# ==========================================
# JOYSTICKS DE ÁREA (LÓGICA MEJORADA)
# ==========================================
if opcion not in ["🖥️ Monitor", "📊 Consolidado Gerencial"]:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_act = area_map[opcion]
    st.title(f"Joystick: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    # SELECCIÓN VISUAL
    cols_m = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS[area_act]):
        label = m_btn
        if m_btn in paradas: label = f"🚨 {m_btn}"
        elif m_btn in activos: label = f"⚙️ {m_btn}\nOP: {activos[m_btn]['op']}"
        
        if cols_m[i % 4].button(label, key=f"btn_{m_btn}", use_container_width=True):
            st.session_state.m_sel = m_btn

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        act = activos.get(m)
        par = paradas.get(m)
        st.divider()

        if not act:
            # FORMULARIO DE INICIO (TODOS LOS CAMPOS SEGÚN TABLA)
            with st.form("inicio_op"):
                st.subheader(f"🚀 Iniciar {m}")
                c1, c2 = st.columns(2)
                op_in = c1.text_input("N° OP")
                tr_in = c2.text_input("Trabajo")
                
                extra = {}
                if area_act == "IMPRESIÓN":
                    k1, k2, k3, k4 = st.columns(4)
                    extra = {"tipo_papel": k1.text_input("Papel"), "ancho": k2.text_input("Ancho"), "gramaje": k3.text_input("Gramaje"), "medida_trabajo": k4.text_input("Medida")}
                elif area_act == "CORTE":
                    k1, k2, k3, k4 = st.columns(4)
                    extra = {"tipo_papel": k1.text_input("Papel"), "img_varilla": k2.number_input("Img/Var", 0), "medida_rollos": k3.text_input("Medida Rollos"), "unidades_caja": k4.number_input("Und/Caja", 0)}
                elif area_act == "COLECTORAS":
                    k1, k2, k3 = st.columns(3)
                    extra = {"tipo_papel": k1.text_input("Papel"), "medida_trabajo": k2.text_input("Medida"), "unidades_caja": k3.number_input("Und/Caja", 0)}
                elif area_act == "ENCUADERNACIÓN":
                    k1, k2, k3 = st.columns(3)
                    extra = {"formas_totales": k1.number_input("Formas", 0), "material": k2.text_input("Material"), "medida": k3.text_input("Medida")}

                if st.form_submit_button("EMPEZAR TRABAJO"):
                    if op_in and tr_in:
                        data = {"maquina": m, "op": op_in, "trabajo": tr_in, "area": area_act, "hora_inicio": datetime.now().strftime("%H:%M")}
                        data.update(extra)
                        supabase.table("trabajos_activos").insert(data).execute()
                        st.rerun()
        else:
            # MÁQUINA EN USO
            st.info(f"TRABAJANDO: OP {act['op']} | Inicio: {act['hora_inicio']}")
            
            # --- LÓGICA DE PARADAS (REANUDA/DETIENE) ---
            if par:
                st.error(f"⚠️ MÁQUINA DETENIDA DESDE LAS {par['h_inicio']} POR: {par['motivo']}")
                if st.button("▶️ REANUDAR TRABAJO", use_container_width=True):
                    supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                    st.rerun()
            else:
                with st.expander("🚨 REGISTRAR PARADA DE MÁQUINA"):
                    motivo_p = st.selectbox("Motivo de parada:", ["Mecánico", "Eléctrico", "Limpia/Ajuste", "Falta Material", "Cambio de Rollo", "Almuerzo/Turno"])
                    if st.button("DETENER MÁQUINA"):
                        supabase.table("paradas_maquina").insert({
                            "maquina": m, "op": act['op'], "motivo": motivo_p, 
                            "h_inicio": datetime.now().strftime("%H:%M")
                        }).execute()
                        st.rerun()

                # --- FORMULARIO DE CIERRE (Solo si no está parada) ---
                with st.form("cierre_op"):
                    st.subheader("🏁 Finalizar Producción")
                    res = {}
                    if area_act == "IMPRESIÓN":
                        f1, f2 = st.columns(2); res = {"metros_impresos": f1.number_input("Metros", 0.0), "bobinas": f2.number_input("Bobinas", 0)}
                    elif area_act == "CORTE":
                        f1, f2, f3 = st.columns(3); res = {"total_rollos": f1.number_input("Rollos", 0), "cant_varillas": f2.number_input("Varillas", 0), "unidades_caja": f3.number_input("Und/Caja", 0)}
                    elif area_act == "COLECTORAS":
                        f1, f2 = st.columns(2); res = {"total_cajas": f1.number_input("Cajas", 0), "total_formas": f2.number_input("Formas", 0)}
                    elif area_act == "ENCUADERNACIÓN":
                        f1, f2 = st.columns(2); res = {"cant_final": f1.number_input("Cant. Final", 0), "presentacion": f2.text_input("Presentación")}

                    dk = st.number_input("Kilos Desperdicio", 0.0)
                    mot_d = st.text_input("Motivo Desperdicio")
                    obs = st.text_area("Observaciones")

                    if st.form_submit_button("GUARDAR REGISTRO FINAL"):
                        final_data = {
                            "op": act['op'], "maquina": m, "trabajo": act['trabajo'],
                            "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                            "desp_kg": dk, "motivo_desperdicio": mot_d, "observaciones": obs
                        }
                        final_data.update(res)
                        
                        # Mapeo de campos técnicos desde 'activos'
                        nom_t = normalizar(area_act)
                        columnas_originales = {
                            "impresion": ["tipo_papel", "ancho", "gramaje", "medida_trabajo"],
                            "corte": ["tipo_papel", "ancho", "gramaje", "img_varilla", "medida_rollos", "unidades_caja"],
                            "colectoras": ["tipo_papel", "medida_trabajo", "unidades_caja"],
                            "encuadernacion": ["formas_totales", "material", "medida"]
                        }
                        
                        for col in columnas_originales.get(nom_t, []):
                            if col in act:
                                final_data[col] = safe_float(act[col]) if col in ["ancho", "gramaje"] else act[col]

                        supabase.table(nom_t).insert(final_data).execute()
                        supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                        st.success("¡Datos guardados!")
                        st.rerun()
