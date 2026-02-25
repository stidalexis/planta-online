import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V5.1", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 85px !important; border-radius: 12px; font-weight: bold; border: 2px solid #0D47A1; width: 100%; white-space: pre-wrap !important; }
    .card-proceso { padding: 15px; border-radius: 12px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; margin-bottom: 10px; }
    .card-libre { padding: 15px; border-radius: 12px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; margin-bottom: 10px; }
    .title-area { background-color: #1A237E; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

def normalizar(t):
    for k, v in {"Í":"I","Ó":"O","Á":"A","É":"E","Ú":"U"," ":"_"}.items(): t = t.upper().replace(k,v)
    return t.lower()

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("SISTEMA NUVE", ["🖥️ Monitor", "📅 Planificación", "📊 Consolidados KPI", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# ==========================================
# 1. PLANIFICACIÓN (ADMIN)
# ==========================================
if menu == "📅 Planificación":
    st.title("📅 Carga de Órdenes de Producción")
    with st.form("f_admin", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        op_num = c1.text_input("Número de OP")
        tr_nom = c2.text_input("Nombre del Trabajo")
        vend = c3.text_input("Vendedor")
        
        f1, f2, f3 = st.columns(3)
        mat = f1.text_input("Material / Papel")
        gra = f2.text_input("Gramaje")
        anc = f3.text_input("Ancho")
        
        f4, f5, f6 = st.columns(3)
        uni = f4.number_input("Unidades Solicitadas", 0)
        cor = f5.selectbox("Core", ["3 Pulgadas", "1.5 Pulgadas", "Sin Core"])
        tipo = f6.radio("Tipo de Orden", ["RI", "RB", "FR"], horizontal=True)
        
        # Flujo inicial
        prox = "IMPRESIÓN" if tipo in ["RI", "FR"] else "CORTE"
        
        cant_t, espec_t, orient = 0, "N/A", "N/A"
        if tipo in ["RI", "FR"]:
            st.divider()
            i1, i2, i3 = st.columns(3)
            cant_t = i1.number_input("Cant. Tintas", 0, 10)
            espec_t = i2.text_input("Colores Tintas")
            orient = i3.selectbox("Lado Impresión", ["Frente", "Respaldo", "Ambos"])
            
        if st.form_submit_button("✅ CARGAR A PLANTA"):
            if not op_num or not tr_nom:
                st.error("OP y Trabajo son obligatorios.")
            else:
                op_f = f"{tipo}-{op_num}".strip().upper()
                payload = {
                    "op": op_f, "trabajo": tr_nom, "vendedor": vend, "material": mat, "gramaje": gra, "ancho": anc,
                    "unidades_solicitadas": uni, "core": cor, "tipo_acabado": tipo, "cant_tintas": cant_t,
                    "especificacion_tintas": espec_t, "orientacion_impresion": orient, "estado": "Pendiente", "proxima_area": prox
                }
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.success(f"Orden {op_f} enviada a {prox}")

# ==========================================
# 2. MÓDULOS POR ÁREA
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}[menu]
    st.title(f"Módulo: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    
    # Grid de Máquinas
    cols = st.columns(4)
    for i, m_id in enumerate(MAQUINAS[area_act]):
        label = f"⚙️ {m_id}\n(OCUPADA)" if m_id in activos else f"⚪ {m_id}\n(LIBRE)"
        if cols[i % 4].button(label, key=m_id):
            st.session_state.m_sel = m_id

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        trabajo = activos.get(m)
        st.divider()
        st.subheader(f"🛠️ Máquina Seleccionada: {m}")

        if not trabajo:
            # INICIO DE TRABAJO
            res = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).eq("estado", "Pendiente").execute()
            ops = [f"{o['op']} | {o['trabajo']}" for o in res.data]
            if ops:
                sel = st.selectbox("📋 Seleccione OP para iniciar:", ["-- SELECCIONE --"] + ops)
                if st.button("🚀 INICIAR TURNO"):
                    if sel != "-- SELECCIONE --":
                        d = [o for o in res.data if o['op'] == sel.split(" | ")[0]][0]
                        ini_p = {
                            "maquina": m, "op": d['op'], "trabajo": d['trabajo'], "area": area_act,
                            "vendedor": d['vendedor'], "material": d['material'], "gramaje": d['gramaje'],
                            "ancho": d['ancho'], "unidades_solicitadas": d['unidades_solicitadas'],
                            "core": d['core'], "tipo_acabado": d['tipo_acabado'],
                            "cant_tintas": d['cant_tintas'], "especificacion_tintas": d['especificacion_tintas'],
                            "orientacion_impresion": d['orientacion_impresion'], "hora_inicio": datetime.now().strftime("%H:%M")
                        }
                        supabase.table("trabajos_activos").insert(ini_p).execute()
                        supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d['op']).execute()
                        st.success("Máquina iniciada correctamente."); st.rerun()
            else: st.warning("No hay OPs pendientes para esta área.")
        else:
            # CIERRE DE TRABAJO (KPIs COMPLETOS)
            st.warning(f"🔔 TRABAJANDO: {trabajo['op']} - {trabajo['trabajo']}")
            with st.form("f_kpi"):
                st.subheader("🏁 Datos de Finalización (Obligatorios)")
                res_kpi = {}
                c1, c2 = st.columns(2)
                
                if area_act == "IMPRESIÓN":
                    res_kpi["metros_impresos"] = c1.number_input("Metros Impresos Finales", 0.0)
                    res_kpi["bobinas"] = c2.number_input("Cantidad de Bobinas", 0)
                elif area_act == "CORTE":
                    res_kpi["total_rollos"] = c1.number_input("Total Rollos Producidos", 0)
                    res_kpi["cant_varillas"] = c2.number_input("Varillas Utilizadas", 0)
                elif area_act == "COLECTORAS":
                    res_kpi["total_cajas"] = c1.number_input("Cajas Completadas", 0)
                    res_kpi["total_formas"] = c2.number_input("Total Formas", 0)
                elif area_act == "ENCUADERNACIÓN":
                    res_kpi["cant_final"] = c1.number_input("Cantidad Final Entregada", 0)
                    res_kpi["presentacion"] = c2.text_input("Presentación (Ej: Paquetes x 50)")

                st.divider()
                k1, k2 = st.columns(2)
                dk = k1.number_input("Desperdicio Total (Kg)", 0.0)
                mot = k2.text_input("Motivo del Desperdicio")
                obs = st.text_area("Observaciones Generales")
                
                if st.form_submit_button("🏁 FINALIZAR Y GUARDAR KPI"):
                    # VALIDACIÓN DE ROBUSTEZ: No permitir campos en cero si son KPIs
                    val_kpi = list(res_kpi.values())[0] if area_act != "ENCUADERNACIÓN" else res_kpi["cant_final"]
                    
                    if val_kpi <= 0 or (dk > 0 and not mot):
                        st.error("❌ ERROR: Debe ingresar la producción total y el motivo del desperdicio si es mayor a 0.")
                    else:
                        op_pref = trabajo['op'].split("-")[0]
                        pro_a = "FINALIZADO"
                        if op_pref == "RI" and area_act == "IMPRESIÓN": pro_a = "CORTE"
                        elif op_pref == "FR" and area_act == "IMPRESIÓN": pro_a = "COLECTORAS"
                        elif op_pref == "FR" and area_act == "COLECTORAS": pro_a = "ENCUADERNACIÓN"
                        
                        # Guardar en Historial
                        h = {
                            "op": trabajo['op'], "maquina": m, "trabajo": trabajo['trabajo'],
                            "h_inicio": trabajo['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                            "vendedor": trabajo['vendedor'], "material": trabajo['material'],
                            "desp_kg": dk, "motivo_desp": mot, "observaciones": obs
                        }
                        if area_act == "IMPRESIÓN": h.update({"gramaje": trabajo["gramaje"], "ancho": trabajo["ancho"], "cant_tintas": trabajo["cant_tintas"], "especificacion_tintas": trabajo["especificacion_tintas"], "orientacion_impresion": trabajo["orientacion_impresion"]})
                        if area_act == "CORTE": h.update({"gramaje": trabajo["gramaje"], "ancho": trabajo["ancho"], "core": trabajo["core"]})
                        
                        h.update(res_kpi)
                        supabase.table(normalizar(area_act)).insert(h).execute()
                        
                        # Actualizar estado de OP
                        nuevo_est = "Pendiente" if pro_a != "FINALIZADO" else "Finalizado"
                        supabase.table("ordenes_planeadas").update({"proxima_area": pro_a, "estado": nuevo_est}).eq("op", trabajo['op']).execute()
                        supabase.table("trabajos_activos").delete().eq("id", trabajo['id']).execute()
                        
                        st.success("✅ Datos consolidados correctamente."); st.rerun()

# ==========================================
# 3. MONITOR Y CONSOLIDADOS KPI
# ==========================================
elif menu == "🖥️ Monitor":
    st.title("🖥️ Monitor de Planta")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for i, m in enumerate(lista):
            with cols[i % 4]:
                if m in act:
                    st.markdown(f"<div class='card-proceso'>⚙️ <b>{m}</b><br>{act[m]['op']}<br>{act[m]['trabajo']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-libre'>⚪ {m}<br>LIBRE</div>", unsafe_allow_html=True)

elif menu == "📊 Consolidados KPI":
    st.title("📊 KPIs de Producción")
    tabs = st.tabs(["Impresión", "Corte", "Colectoras", "Encuadernación"])
    areas = ["impresion", "corte", "colectoras", "encuadernacion"]
    for i, t in enumerate(tabs):
        with t:
            data = supabase.table(areas[i]).select("*").order("fecha_fin", desc=True).execute().data
            if data: st.dataframe(pd.DataFrame(data), use_container_width=True)
            else: st.info("Sin registros aún.")
