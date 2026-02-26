import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V9.0", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 75px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    .card-proceso { padding: 15px; border-radius: 12px; background-color: #E3F2FD; border-left: 8px solid #1565C0; margin-bottom: 10px; }
    .card-libre { padding: 15px; border-radius: 12px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; margin-bottom: 10px; }
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

menu = st.sidebar.radio("MENÚ PRINCIPAL", ["🖥️ Monitor General", "📅 Planificación", "📊 Historial KPI", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# ==========================================
# 1. MONITOR GENERAL
# ==========================================
if menu == "🖥️ Monitor General":
    st.title("🖥️ Monitor de Producción en Tiempo Real")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    tabs = st.tabs(list(MAQUINAS.keys()))
    for i, area in enumerate(MAQUINAS.keys()):
        with tabs[i]:
            cols = st.columns(4)
            for idx, m in enumerate(MAQUINAS[area]):
                with cols[idx % 4]:
                    if m in activos:
                        st.markdown(f"<div class='card-proceso'><b>{m}</b><br>{activos[m]['op']}<br><small>{activos[m]['trabajo']}</small></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='card-libre'><b>{m}</b><br>DISPONIBLE</div>", unsafe_allow_html=True)
    
    st.divider()
    res_ops = supabase.table("ordenes_planeadas").select("*").order("fecha_creacion", desc=True).execute().data
    if res_ops:
        df_ops = pd.DataFrame(res_ops)
        op_ver = st.selectbox("🔍 Buscar OP para detalle técnico:", ["--"] + df_ops['op'].tolist())
        if op_ver != "--":
            d = df_ops[df_ops['op'] == op_ver].iloc[0]
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns(4)
                c1.write(f"**Vendedor:** {d['vendedor']}\n\n**Material:** {d['material']}")
                c2.write(f"**Medidas:** {d.get('medidas','N/A')}\n\n**Tipo:** {d['tipo_acabado']}")
                c3.write(f"**Unidades:** {d['unidades_solicitadas']}\n\n**Partes:** {d.get('num_partes',1)}")
                c4.write(f"**Status:** {d['estado']}\n\n**Área:** {d['proxima_area']}")
        st.dataframe(df_ops[['op', 'trabajo', 'vendedor', 'proxima_area', 'estado']], use_container_width=True, hide_index=True)

# ==========================================
# 2. PLANIFICACIÓN (FORMULARIO DINÁMICO)
# ==========================================
elif menu == "📅 Planificación":
    st.title("📅 Registro de Órdenes de Producción")
    with st.form("f_plan", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        op_n, trab, vend = c1.text_input("N° OP"), c2.text_input("Trabajo"), c3.text_input("Vendedor")
        tipo = st.radio("TIPO DE PRODUCTO", ["RI", "RB", "FRI", "FRB"], horizontal=True)
        
        # --- CAMPOS COMUNES ---
        f1, f2, f3 = st.columns(3)
        mat, gra, anc = f1.text_input("Tipo de Papel / Material"), f2.text_input("Gramaje"), f3.text_input("Ancho")
        medidas = st.text_input("Medidas del Producto")
        unid = st.number_input("Cantidad Solicitada (Unidades/Formas)", 0)

        # --- CAMPOS DINÁMICOS PARA FRI / FRB (FORMAS) ---
        num_si, n_d, n_h, pres, n_p, det_p = False, "N/A", "N/A", "N/A", 1, "N/A"
        if "FR" in tipo:
            st.markdown("### 📋 Especificaciones de Formas")
            df1, df2, df3 = st.columns([1,2,2])
            num_si = df1.checkbox("¿Lleva Numeración?")
            if num_si:
                n_d, n_h = df2.text_input("Desde"), df3.text_input("Hasta")
            
            df4, df5, df6 = st.columns(3)
            pres = df4.selectbox("Presentación", ["LIBRETA", "BLOCK", "LICOM", "PAQUETES", "SUELTAS", "FORMA CONTINUA"])
            n_p = df5.number_input("Número de Partes", 1, 10)
            det_p = df6.text_input("Detalle Partes (Ej: 1 Blanco / 1 Fondos)")

        # --- CAMPOS PARA TINTAS (DINÁMICO) ---
        c_t, e_t, o_t = 0, "N/A", "N/A"
        if tipo in ["RI", "FRI"]:
            st.markdown("### 🎨 Configuración de Tintas")
            i1, i2, i3 = st.columns(3)
            c_t = i1.number_input("Cantidad de Tintas", 0)
            e_t = i2.text_input("¿Qué Tintas? (Colores)")
            o_t = i3.selectbox("Orientación/Lado", ["Frente", "Respaldo", "Ambos"])

        if st.form_submit_button("🚀 REGISTRAR ORDEN"):
            pArea = "IMPRESIÓN" if tipo in ["RI", "FRI"] else "CORTE" if tipo == "RB" else "COLECTORAS"
            op_id = f"{tipo}-{op_n}".upper()
            p = {"op": op_id, "trabajo": trab, "vendedor": vend, "material": mat, "gramaje": gra, "ancho": anc, "unidades_solicitadas": unid, "tipo_acabado": tipo, "cant_tintas": c_t, "especificacion_tintas": e_t, "orientacion_impresion": o_t, "medidas": medidas, "lleva_numeracion": num_si, "num_desde": n_d, "num_hasta": n_h, "presentacion": pres, "num_partes": n_p, "detalle_partes": det_p, "estado": "Pendiente", "proxima_area": pArea}
            supabase.table("ordenes_planeadas").insert(p).execute()
            st.success(f"Orden {op_id} enviada a {pArea}")

# ==========================================
# 3. OPERACIÓN (CIERRE INTELIGENTE)
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}[menu]
    st.title(f"Módulo: {area_act}")
    
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    cols = st.columns(4)
    for i, m_id in enumerate(MAQUINAS[area_act]):
        lbl = f"⚙️ {m_id}\nOCUPADA" if m_id in act else f"⚪ {m_id}\nLIBRE"
        if cols[i % 4].button(lbl, key=m_id): st.session_state.m_sel = m_id

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        t = act.get(m)
        if not t:
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).eq("estado", "Pendiente").execute().data
            sel = st.selectbox("Iniciar OP:", ["--"] + [f"{o['op']} | {o['trabajo']}" for o in ops])
            if st.button("🚀 INICIAR TURNO"):
                if sel != "--":
                    d = [o for o in ops if o['op'] == sel.split(" | ")[0]][0]
                    d.update({"maquina": m, "area": area_act, "hora_inicio": datetime.now().strftime("%H:%M")})
                    d.pop('fecha_creacion', None); d.pop('estado', None); d.pop('proxima_area', None)
                    supabase.table("trabajos_activos").insert(d).execute()
                    supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d['op']).execute()
                    st.rerun()
        else:
            st.info(f"📌 OP: {t['op']} | {t['trabajo']}")
            with st.form("cierre"):
                res_f = {}
                c1, c2 = st.columns(2)
                if area_act == "IMPRESIÓN":
                    res_f["metros_impresos"] = c1.number_input("Metros Impresos", 0.0)
                    res_f["bobinas"] = c2.number_input("Bobinas", 0)
                elif area_act == "CORTE":
                    res_f["metros_finales"] = c1.number_input("Metros Finales", 0.0)
                    res_f["total_rollos"] = c2.number_input("Total Rollos", 0)
                    res_f["cant_varillas"] = st.number_input("Varillas", 0)
                elif area_act == "COLECTORAS":
                    res_f["total_cajas"] = c1.number_input("Cajas", 0)
                    res_f["total_formas"] = c2.number_input("Total Formas Producidas", 0)
                elif area_act == "ENCUADERNACIÓN":
                    res_f["cant_final"] = c1.number_input("Cantidad Final", 0)
                    res_f["presentacion"] = c2.text_input("Presentación Final", value=t.get('presentacion',''))

                dk = st.number_input("Desperdicio (Kg)", 0.0); mot = st.text_input("Motivo Desp.")
                if st.form_submit_button("🏁 CERRAR ÁREA"):
                    pref = t['op'].split("-")[0]
                    prox = "FINALIZADO"
                    if pref == "RI" and area_act == "IMPRESIÓN": prox = "CORTE"
                    elif pref == "FRI" and area_act == "IMPRESIÓN": prox = "COLECTORAS"
                    elif (pref == "FRI" or pref == "FRB") and area_act == "COLECTORAS": prox = "ENCUADERNACIÓN"
                    
                    h = {"op": t['op'], "maquina": m, "trabajo": t['trabajo'], "vendedor": t['vendedor'], "material": t['material'], "h_inicio": t['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"), "desp_kg": dk, "motivo_desp": mot}
                    if area_act in ["IMPRESIÓN", "COLECTORAS"]:
                        h.update({"lleva_num": t['lleva_numeracion'], "n_desde": t['num_desde'], "n_hasta": t['num_hasta']})
                    if area_act == "COLECTORAS":
                        h.update({"presentacion": t['presentacion'], "num_partes": t['num_partes']})
                    h.update(res_f)
                    
                    supabase.table(normalizar(area_act)).insert(h).execute()
                    supabase.table("ordenes_planeadas").update({"proxima_area": prox, "estado": "Pendiente" if prox != "FINALIZADO" else "Finalizado"}).eq("op", t['op']).execute()
                    supabase.table("trabajos_activos").delete().eq("id", t['id']).execute()
                    st.rerun()

# ==========================================
# 4. HISTORIAL KPI
# ==========================================
elif menu == "📊 Historial KPI":
    st.title("📊 Análisis de Rendimiento")
    tab1, tab2, tab3, tab4 = st.tabs(["Impresión", "Corte", "Colectoras", "Encuadernación"])
    areas_db = ["impresion", "corte", "colectoras", "encuadernacion"]
    for i, tab in enumerate([tab1, tab2, tab3, tab4]):
        with tab:
            data = supabase.table(areas_db[i]).select("*").order("fecha_fin", desc=True).execute().data
            st.dataframe(pd.DataFrame(data), use_container_width=True)
