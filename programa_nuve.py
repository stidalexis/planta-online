import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V4.0", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stButton > button { height: 90px !important; border-radius: 15px; font-weight: bold; border: 2px solid #0D47A1; width: 100%; white-space: pre-wrap !important; font-size: 16px; }
    .card-proceso { padding: 15px; border-radius: 12px; background-color: #E8F5E9; border-left: 10px solid #2E7D32; margin-bottom: 10px; font-size: 14px; }
    .card-libre { padding: 15px; border-radius: 12px; background-color: #F5F5F5; border-left: 10px solid #9E9E9E; text-align: center; color: #757575; margin-bottom: 10px; }
    .title-area { background-color: #1A237E; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 25px; font-size: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

def normalizar(t):
    for k, v in {"Í":"I","Ó":"O","Á":"A","É":"E","Ú":"U"," ":"_"}.items(): t = t.upper().replace(k,v)
    return t.lower()

# --- MENÚ LATERAL ---
opcion = st.sidebar.radio("MENÚ PRINCIPAL", [
    "🖥️ Monitor General", 
    "📅 Planificación (Admin)", 
    "📊 Consolidado Maestro",
    "🖨️ Impresión", 
    "✂️ Corte", 
    "📥 Colectoras", 
    "📕 Encuadernación"
])

# ==========================================
# 1. MONITOR GENERAL
# ==========================================
if opcion == "🖥️ Monitor General":
    st.title("🖥️ Estado de Planta")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for i, m in enumerate(lista):
            with cols[i % 4]:
                if m in activos:
                    st.markdown(f"<div class='card-proceso'>⚙️ <b>{m}</b><br>{activos[m]['op']}<br>{activos[m]['trabajo']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-libre'>⚪ {m}<br>LIBRE</div>", unsafe_allow_html=True)

# ==========================================
# 2. PLANIFICACIÓN (ADMIN)
# ==========================================
elif opcion == "📅 Planificación (Admin)":
    st.title("📅 Carga de Órdenes")
    with st.form("f_admin", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        op_n = c1.text_input("Número de OP (Solo número)")
        tr_n = c2.text_input("Nombre del Trabajo")
        vend = c3.text_input("Vendedor")
        f1, f2, f3 = st.columns(3)
        mat = f1.text_input("Material")
        gra = f2.text_input("Gramaje")
        anc = f3.text_input("Ancho")
        f4, f5, f6 = st.columns(3)
        uni = f4.number_input("Unidades Solicitadas", 0)
        cor = f5.selectbox("Core", ["3 Pulgadas", "1.5 Pulgadas", "Sin Core"])
        tip = f6.radio("Tipo", ["RI", "RB", "FR"], horizontal=True)
        
        cant_t, espec_t, orient = 0, "N/A", "N/A"
        if tip in ["RI", "FR"]:
            st.divider()
            i1, i2, i3 = st.columns(3)
            cant_t = i1.number_input("Tintas", 0, 10)
            espec_t = i2.text_input("Colores")
            orient = i3.selectbox("Lado", ["Frente", "Respaldo", "Ambos"])
            
        if st.form_submit_button("✅ REGISTRAR"):
            op_f = f"{tip}-{op_n}".strip().upper()
            payload = {
                "op": op_f, "trabajo": tr_n, "vendedor": vend, "material": mat, "gramaje": gra, "ancho": anc,
                "unidades_solicitadas": int(uni), "core": cor, "tipo_acabado": tip, "cant_tintas": int(cant_t),
                "especificacion_tintas": espec_t, "orientacion_impresion": orient, "estado": "Pendiente"
            }
            supabase.table("ordenes_planeadas").insert(payload).execute()
            st.success("Guardado.")

# ==========================================
# 3. CONSOLIDADO MAESTRO (HISTORIALES)
# ==========================================
elif opcion == "📊 Consolidado Maestro":
    st.title("📊 Historial General de Producción")
    t1, t2, t3, t4 = st.tabs(["Impresión", "Corte", "Colectoras", "Encuadernación"])
    with t1:
        data = supabase.table("impresion").select("*").order("fecha_fin", desc=True).execute().data
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    with t2:
        data = supabase.table("corte").select("*").order("fecha_fin", desc=True).execute().data
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    with t3:
        data = supabase.table("colectoras").select("*").order("fecha_fin", desc=True).execute().data
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    with t4:
        data = supabase.table("encuadernacion").select("*").order("fecha_fin", desc=True).execute().data
        st.dataframe(pd.DataFrame(data), use_container_width=True)

# ==========================================
# 4. MÓDULOS OPERATIVOS (BOTONES + DESPLEGABLE)
# ==========================================
elif opcion in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_act = area_map[opcion]
    st.title(f"Área: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    
    st.subheader("Máquinas:")
    cols_b = st.columns(4)
    for i, m_id in enumerate(MAQUINAS[area_act]):
        lbl = f"⚙️ {m_id}\n(EN USO)" if m_id in activos else f"⚪ {m_id}\n(LIBRE)"
        if cols_b[i % 4].button(lbl, key=f"btn_{m_id}"):
            st.session_state.m_sel = m_id

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        trabajo = activos.get(m)
        st.divider()
        st.subheader(f"Panel: {m}")

        if not trabajo:
            res_ops = supabase.table("ordenes_planeadas").select("*").eq("estado", "Pendiente").execute()
            ops_list = [f"{o['op']} | {o['trabajo']}" for o in res_ops.data]
            if ops_list:
                sel_op = st.selectbox("Seleccione OP:", ["-- Seleccione --"] + ops_list)
                if st.button("🚀 INICIAR TRABAJO"):
                    if sel_op != "-- Seleccione --":
                        id_op = sel_op.split(" | ")[0]
                        d = supabase.table("ordenes_planeadas").select("*").eq("op", id_op).execute().data[0]
                        ini_p = {
                            "maquina": m, "op": d['op'], "trabajo": d['trabajo'], "area": area_act,
                            "vendedor": d['vendedor'], "material": d['material'], "gramaje": d['gramaje'],
                            "ancho": d['ancho'], "unidades_solicitadas": d['unidades_solicitadas'],
                            "core": d['core'], "tipo_acabado": d['tipo_acabado'],
                            "cant_tintas": d['cant_tintas'], "especificacion_tintas": d['especificacion_tintas'],
                            "orientacion_impresion": d['orientacion_impresion'], "hora_inicio": datetime.now().strftime("%H:%M")
                        }
                        supabase.table("trabajos_activos").insert(ini_p).execute()
                        supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", id_op).execute()
                        st.rerun()
        else:
            st.success(f"TRABAJANDO: {trabajo['op']}")
            with st.form("f_fin"):
                res_f = {}
                c1, c2 = st.columns(2)
                if area_act == "IMPRESIÓN":
                    res_f["metros_impresos"] = c1.number_input("Metros", 0.0)
                    res_f["bobinas"] = c2.number_input("Bobinas", 0)
                elif area_act == "CORTE":
                    res_f["total_rollos"] = c1.number_input("Rollos", 0)
                    res_f["cant_varillas"] = c2.number_input("Varillas", 0)
                elif area_act == "COLECTORAS":
                    res_f["total_cajas"] = c1.number_input("Cajas", 0)
                    res_f["total_formas"] = c2.number_input("Formas", 0)
                
                dk = st.number_input("Desperdicio (Kg)", 0.0)
                obs = st.text_area("Notas")
                if st.form_submit_button("🏁 FINALIZAR"):
                    h = {"op": trabajo['op'], "maquina": m, "trabajo": trabajo['trabajo'], "h_inicio": trabajo['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"), "vendedor": trabajo['vendedor'], "material": trabajo['material'], "desp_kg": dk, "observaciones": obs}
                    h.update(res_f)
                    supabase.table(normalizar(area_act)).insert(h).execute()
                    supabase.table("trabajos_activos").delete().eq("id", trabajo['id']).execute()
                    supabase.table("ordenes_planeadas").update({"estado": "Finalizado"}).eq("op", trabajo['op']).execute()
                    st.rerun()
