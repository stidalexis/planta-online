import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V6.5", page_icon="🏭")

# --- CONEXIÓN A BASE DE DATOS ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS PERSONALIZADOS ---
st.markdown("""
    <style>
    .stButton > button { height: 75px !important; border-radius: 12px; font-weight: bold; border: 2px solid #0D47A1; width: 100%; transition: 0.3s; }
    .stButton > button:hover { background-color: #BBDEFB; color: #0D47A1; }
    .card-proceso { padding: 15px; border-radius: 12px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; margin-bottom: 10px; }
    .card-libre { padding: 15px; border-radius: 12px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; margin-bottom: 10px; }
    .title-area { background-color: #1A237E; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- MAQUINARIA ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

def normalizar(t):
    for k, v in {"Í":"I","Ó":"O","Á":"A","É":"E","Ú":"U"," ":"_"}.items(): t = t.upper().replace(k,v)
    return t.lower()

# --- MENÚ DE NAVEGACIÓN ---
menu = st.sidebar.radio("SISTEMA DE CONTROL", [
    "🖥️ Monitor General", 
    "📅 Planificación (Admin)", 
    "📊 Historial KPI", 
    "🖨️ Impresión", 
    "✂️ Corte", 
    "📥 Colectoras", 
    "📕 Encuadernación"
])

# ==========================================
# 1. MONITOR GENERAL (MÁQUINAS Y ESTADO OPs)
# ==========================================
if menu == "🖥️ Monitor General":
    st.title("🖥️ Tablero de Control de Planta")
    
    # Grid de máquinas activas
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    tabs = st.tabs(list(MAQUINAS.keys()))
    
    for i, area in enumerate(MAQUINAS.keys()):
        with tabs[i]:
            cols = st.columns(4)
            for idx, m in enumerate(MAQUINAS[area]):
                with cols[idx % 4]:
                    if m in act:
                        st.markdown(f"<div class='card-proceso'>⚙️ <b>{m}</b><br>{act[m]['op']}<br><small>{act[m]['trabajo']}</small></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='card-libre'>⚪ <b>{m}</b><br>LIBRE</div>", unsafe_allow_html=True)

    st.divider()

    # BUSCADOR DE EXPEDIENTES (Para evitar error de selección en tabla)
    st.subheader("📋 Seguimiento de Órdenes (OPs)")
    res_ops = supabase.table("ordenes_planeadas").select("*").order("fecha_creacion", desc=True).execute().data
    
    if res_ops:
        df_ops = pd.DataFrame(res_ops)
        def label_est(r):
            if r['estado'] == 'Finalizado': return "✅ FINALIZADA"
            if r['estado'] == 'En Proceso': return f"🔄 PRODUCIENDO EN {r['proxima_area']}"
            return f"⏳ ESPERA DE {r['proxima_area']}"
        df_ops['Status'] = df_ops.apply(label_est, axis=1)

        # Selector de OP para ver detalle
        col_s1, col_s2 = st.columns([1, 2])
        op_info = col_s1.selectbox("🔍 Ver expediente de OP:", ["-- Seleccione una OP --"] + df_ops['op'].tolist())
        
        if op_info != "-- Seleccione una OP --":
            d = df_ops[df_ops['op'] == op_info].iloc[0]
            with st.container(border=True):
                st.markdown(f"### 📑 Datos Originales: {d['op']}")
                c1, c2, c3, c4 = st.columns(4)
                c1.write(f"**Trabajo:** {d['trabajo']}\n\n**Vendedor:** {d['vendedor']}")
                c2.write(f"**Material:** {d['material']}\n\n**Gramaje:** {d['gramaje']}")
                c3.write(f"**Ancho:** {d['ancho']}\n\n**Core:** {d['core']}")
                c4.write(f"**Unidades:** {d['unidades_solicitadas']}\n\n**Estado:** {d['Status']}")
                
                if d['cant_tintas'] > 0:
                    st.divider()
                    st.write(f"🎨 **Tintas:** {d['cant_tintas']} colores | **Especificación:** {d['especificacion_tintas']} | **Lado:** {d['orientacion_impresion']}")

        st.markdown("#### Listado General de Carga")
        st.dataframe(df_ops[['op', 'trabajo', 'vendedor', 'Status']], use_container_width=True, hide_index=True)

# ==========================================
# 2. PLANIFICACIÓN (LÓGICA DE VISIBILIDAD)
# ==========================================
elif menu == "📅 Planificación (Admin)":
    st.title("📅 Carga de Nueva OP")
    with st.form("f_plan", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        op_n = c1.text_input("N° de OP")
        tr_n = c2.text_input("Nombre del Trabajo")
        vend = c3.text_input("Vendedor")
        
        f1, f2, f3 = st.columns(3)
        mat, gra, anc = f1.text_input("Material"), f2.text_input("Gramaje"), f3.text_input("Ancho")
        
        f4, f5, f6 = st.columns(3)
        uni = f4.number_input("Unidades Solicitadas", 0)
        cor = f5.selectbox("Core", ["3 Pulgadas", "1.5 Pulgadas", "Sin Core"])
        tipo = f6.radio("Tipo de Orden", ["RI", "RB", "FRI", "FRB"], horizontal=True)
        
        cant_t, esp_t, ori_t = 0, "N/A", "N/A"
        if tipo in ["RI", "FRI"]:
            st.divider()
            st.subheader("🎨 Configuración de Tintas")
            i1, i2, i3 = st.columns(3)
            cant_t = i1.number_input("N° de Tintas", 0, 10)
            esp_t = i2.text_input("Colores Tintas")
            ori_t = i3.selectbox("Lado Impresión", ["Frente", "Respaldo", "Ambos"])
            
        if st.form_submit_button("🚀 CARGAR A PLANTA"):
            if not op_n or not tr_n:
                st.error("❌ OP y Nombre son obligatorios.")
            else:
                # Flujo inicial dinámico
                if tipo in ["RI", "FRI"]: prox = "IMPRESIÓN"
                elif tipo == "RB": prox = "CORTE"
                else: prox = "COLECTORAS" # FRB salta a colectoras
                
                op_id = f"{tipo}-{op_n}".upper()
                p = {"op": op_id, "trabajo": tr_n, "vendedor": vend, "material": mat, "gramaje": gra, "ancho": anc, "unidades_solicitadas": uni, "core": cor, "tipo_acabado": tipo, "cant_tintas": cant_t, "especificacion_tintas": esp_t, "orientacion_impresion": ori_t, "estado": "Pendiente", "proxima_area": prox}
                supabase.table("ordenes_planeadas").insert(p).execute()
                st.success(f"✅ OP {op_id} enviada a {prox}")

# ==========================================
# 3. MÓDULOS OPERATIVOS (FLUJO AUTOMÁTICO)
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}[menu]
    st.title(f"Módulo: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    cols = st.columns(4)
    for i, m_id in enumerate(MAQUINAS[area_act]):
        label = f"{m_id} (OCUPADA)" if m_id in activos else f"{m_id} (LIBRE)"
        if cols[i % 4].button(label, key=m_id): st.session_state.m_sel = m_id

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        trabajo = activos.get(m)
        st.subheader(f"🛠️ Máquina: {m}")
        
        if not trabajo:
            ops_pend = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).eq("estado", "Pendiente").execute().data
            lista_ops = [f"{o['op']} | {o['trabajo']}" for o in ops_pend]
            if lista_ops:
                op_sel = st.selectbox("Seleccione Orden para Iniciar:", ["--"] + lista_ops)
                if st.button("🚀 INICIAR TURNO"):
                    if op_sel != "--":
                        d = [o for o in ops_pend if o['op'] == op_sel.split(" | ")[0]][0]
                        ini = {"maquina": m, "op": d['op'], "trabajo": d['trabajo'], "area": area_act, "vendedor": d['vendedor'], "material": d['material'], "gramaje": d['gramaje'], "ancho": d['ancho'], "unidades_solicitadas": d['unidades_solicitadas'], "core": d['core'], "tipo_acabado": d['tipo_acabado'], "cant_tintas": d['cant_tintas'], "especificacion_tintas": d['especificacion_tintas'], "orientacion_impresion": d['orientacion_impresion'], "hora_inicio": datetime.now().strftime("%H:%M")}
                        supabase.table("trabajos_activos").insert(ini).execute()
                        supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d['op']).execute()
                        st.rerun()
            else: st.warning("No hay órdenes pendientes para esta área.")
        else:
            st.info(f"📌 Trabajando en: {trabajo['op']}")
            with st.form("f_cierre_kpi"):
                st.write("🏁 Datos de Finalización (Obligatorios)")
                res_kpi = {}
                c1, c2 = st.columns(2)
                if area_act == "IMPRESIÓN":
                    res_kpi["metros_impresos"] = c1.number_input("Metros Impresos", 0.0)
                    res_kpi["bobinas"] = c2.number_input("Bobinas totales", 0)
                elif area_act == "CORTE":
                    res_kpi["total_rollos"] = c1.number_input("Total Rollos", 0)
                    res_kpi["cant_varillas"] = c2.number_input("Varillas", 0)
                elif area_act == "COLECTORAS":
                    res_kpi["total_cajas"] = c1.number_input("Cajas", 0)
                    res_kpi["total_formas"] = c2.number_input("Formas", 0)
                elif area_act == "ENCUADERNACIÓN":
                    res_kpi["cant_final"] = c1.number_input("Cantidad Final", 0)
                    res_kpi["presentacion"] = c2.text_input("Tipo de Paquete")

                st.divider()
                dk = st.number_input("Desperdicio (Kg)", 0.0)
                mot = st.text_input("Motivo Desperdicio")
                obs = st.text_area("Observaciones")
                
                if st.form_submit_button("🏁 CERRAR ÁREA"):
                    val_p = list(res_kpi.values())[0] if area_act != "ENCUADERNACIÓN" else res_kpi["cant_final"]
                    if val_p <= 0: st.error("❌ Producción no puede ser 0")
                    else:
                        pref = trabajo['op'].split("-")[0]
                        prox = "FINALIZADO"
                        if pref == "RI" and area_act == "IMPRESIÓN": prox = "CORTE"
                        elif pref == "FRI" and area_act == "IMPRESIÓN": prox = "COLECTORAS"
                        elif (pref == "FRI" or pref == "FRB") and area_act == "COLECTORAS": prox = "ENCUADERNACIÓN"
                        
                        # Guardar Historial con datos heredados
                        h = {"op": trabajo['op'], "maquina": m, "trabajo": trabajo['trabajo'], "h_inicio": trabajo['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"), "vendedor": trabajo['vendedor'], "material": trabajo['material'], "desp_kg": dk, "motivo_desp": mot, "observaciones": obs}
                        if area_act in ["IMPRESIÓN", "CORTE"]: h.update({"gramaje": trabajo['gramaje'], "ancho": trabajo['ancho']})
                        if area_act == "IMPRESIÓN": h.update({"cant_tintas": trabajo['cant_tintas'], "especificacion_tintas": trabajo['especificacion_tintas'], "orientacion_impresion": trabajo['orientacion_impresion']})
                        
                        h.update(res_kpi)
                        supabase.table(normalizar(area_act)).insert(h).execute()
                        
                        # Actualizar OP y Liberar Máquina
                        nest = "Pendiente" if prox != "FINALIZADO" else "Finalizado"
                        supabase.table("ordenes_planeadas").update({"proxima_area": prox, "estado": nest}).eq("op", trabajo['op']).execute()
                        supabase.table("trabajos_activos").delete().eq("id", trabajo['id']).execute()
                        st.success(f"✅ Movido a {prox}"); st.rerun()

# ==========================================
# 4. CONSOLIDADOS KPI
# ==========================================
elif menu == "📊 Historial KPI":
    st.title("📊 Resumen Maestro de Producción")
    t1, t2, t3, t4 = st.tabs(["Impresión", "Corte", "Colectoras", "Encuadernación"])
    tablas_db = ["impresion", "corte", "colectoras", "encuadernacion"]
    for i, tab in enumerate([t1, t2, t3, t4]):
        with tab:
            data = supabase.table(tablas_db[i]).select("*").order("fecha_fin", desc=True).execute().data
            if data: st.dataframe(pd.DataFrame(data), use_container_width=True)
            else: st.info("No hay registros en esta área.")
