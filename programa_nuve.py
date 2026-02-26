import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V6.0", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
# Asegúrate de tener estas keys en .streamlit/secrets.toml
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stButton > button { height: 80px !important; border-radius: 12px; font-weight: bold; border: 2px solid #0D47A1; width: 100%; white-space: pre-wrap !important; }
    .card-proceso { padding: 15px; border-radius: 12px; background-color: #E8F5E9; border-left: 8px solid #2E7D32; margin-bottom: 10px; }
    .card-libre { padding: 15px; border-radius: 12px; background-color: #F5F5F5; border-left: 8px solid #9E9E9E; text-align: center; color: #757575; margin-bottom: 10px; }
    .title-area { background-color: #1A237E; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

def normalizar(t):
    for k, v in {"Í":"I","Ó":"O","Á":"A","É":"E","Ú":"U"," ":"_"}.items(): t = t.upper().replace(k,v)
    return t.lower()

# --- BARRA LATERAL ---
menu = st.sidebar.radio("MENÚ PRINCIPAL", [
    "🖥️ Monitor Principal", 
    "📅 Planificación (Admin)", 
    "📊 Consolidados KPI",
    "🖨️ Impresión", 
    "✂️ Corte", 
    "📥 Colectoras", 
    "📕 Encuadernación"
])

# ==========================================
# 1. MONITOR PRINCIPAL (ESTADO DE MÁQUINAS Y OPs)
# ==========================================
if menu == "🖥️ Monitor Principal":
    st.title("🖥️ Tablero de Control en Tiempo Real")
    
    # Grid de máquinas
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    
    tabs_maquinas = st.tabs(list(MAQUINAS.keys()))
    for i, area in enumerate(MAQUINAS.keys()):
        with tabs_maquinas[i]:
            cols = st.columns(4)
            for idx, m in enumerate(MAQUINAS[area]):
                with cols[idx % 4]:
                    if m in act:
                        st.markdown(f"<div class='card-proceso'>⚙️ <b>{m}</b><br>{act[m]['op']}<br>{act[m]['trabajo']}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='card-libre'>⚪ {m}<br>LIBRE</div>", unsafe_allow_html=True)

    st.divider()
    
    # SEGUIMIENTO DE OPs
    st.subheader("📋 Estado de Órdenes de Producción")
    res_ops = supabase.table("ordenes_planeadas").select("*").order("fecha_creacion", desc=True).execute().data
    
    if res_ops:
        df_ops = pd.DataFrame(res_ops)
        
        # Lógica de etiquetas de estado
        def etiquetar_estado(row):
            if row['estado'] == 'Finalizado': return "✅ FINALIZADA"
            if row['estado'] == 'En Proceso': return f"🔄 PRODUCIENDO EN {row['proxima_area']}"
            return f"⏳ ESPERA DE {row['proxima_area']}"

        df_ops['Estado Actual'] = df_ops.apply(etiquetar_estado, axis=1)
        
        # Tabla Interactiva
        st.info("Haga clic en una fila para ver los detalles técnicos de la OP.")
        seleccion = st.dataframe(
            df_ops[['op', 'trabajo', 'vendedor', 'Estado Actual']],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single"
        )

        # Ventana de detalle
        if len(seleccion.selection.rows) > 0:
            idx_sel = seleccion.selection.rows[0]
            op_sel = df_ops.iloc[idx_sel]
            
            with st.expander(f"📑 EXPEDIENTE TÉCNICO: {op_sel['op']}", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Trabajo:** {op_sel['trabajo']}")
                c1.markdown(f"**Vendedor:** {op_sel['vendedor']}")
                
                c2.markdown(f"**Material:** {op_sel['material']}")
                c2.markdown(f"**Gramaje:** {op_sel['gramaje']} | **Ancho:** {op_sel['ancho']}")
                
                c3.markdown(f"**Unidades:** {op_sel['unidades_solicitadas']}")
                c3.markdown(f"**Core:** {op_sel['core']}")
                
                if op_sel['cant_tintas'] > 0:
                    st.divider()
                    t1, t2, t3 = st.columns(3)
                    t1.markdown(f"**Cant. Tintas:** {op_sel['cant_tintas']}")
                    t2.markdown(f"**Colores:** {op_sel['especificacion_tintas']}")
                    t3.markdown(f"**Lado:** {op_sel['orientacion_impresion']}")
                
                if st.button("Cerrar Detalle"):
                    st.rerun()

# ==========================================
# 2. PLANIFICACIÓN (ADMIN) - CON LÓGICA DE VISIBILIDAD
# ==========================================
elif menu == "📅 Planificación (Admin)":
    st.title("📅 Carga de Órdenes")
    with st.form("f_admin", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        op_num = c1.text_input("Número de OP")
        tr_nom = c2.text_input("Nombre del Trabajo")
        vend = c3.text_input("Vendedor")
        
        f1, f2, f3 = st.columns(3)
        mat, gra, anc = f1.text_input("Material"), f2.text_input("Gramaje"), f3.text_input("Ancho")
        
        f4, f5, f6 = st.columns(3)
        uni = f4.number_input("Unidades Solicitadas", 0)
        cor = f5.selectbox("Core", ["3 Pulgadas", "1.5 Pulgadas", "Sin Core"])
        # Se agregaron FRB y cambio a FRI
        tipo = f6.radio("Tipo de Orden", ["RI (Rollo Impreso)", "RB (Rollo Blanco)", "FRI (Formas Impresas)", "FRB (Formas Blancas)"], horizontal=True)
        
        tipo_clean = tipo.split(" ")[0]
        
        # Visibilidad condicional de tintas
        cant_t, espec_t, orient = 0, "N/A", "N/A"
        if tipo_clean in ["RI", "FRI"]:
            st.divider()
            st.subheader("🎨 Configuración de Tintas")
            i1, i2, i3 = st.columns(3)
            cant_t = i1.number_input("Cant. Tintas", 0, 10)
            espec_t = i2.text_input("Colores")
            orient = i3.selectbox("Lado", ["Frente", "Respaldo", "Ambos"])
            
        if st.form_submit_button("✅ REGISTRAR ORDEN"):
            if not op_num or not tr_nom:
                st.error("OP y Trabajo son obligatorios.")
            else:
                # Determinar primera área
                if tipo_clean in ["RI", "FRI"]: prox = "IMPRESIÓN"
                elif tipo_clean == "RB": prox = "CORTE"
                else: prox = "COLECTORAS" # FRB
                
                op_f = f"{tipo_clean}-{op_num}".strip().upper()
                payload = {
                    "op": op_f, "trabajo": tr_nom, "vendedor": vend, "material": mat, "gramaje": gra, "ancho": anc,
                    "unidades_solicitadas": uni, "core": cor, "tipo_acabado": tipo_clean, "cant_tintas": cant_t,
                    "especificacion_tintas": espec_t, "orientacion_impresion": orient, "estado": "Pendiente", "proxima_area": prox
                }
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.success(f"OP {op_f} registrada. Comienza en {prox}")

# ==========================================
# 3. MÓDULOS OPERATIVOS (FLUJO DE TRABAJO)
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}[menu]
    st.title(f"Área: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    
    cols = st.columns(4)
    for i, m_id in enumerate(MAQUINAS[area_act]):
        lbl = f"⚙️ {m_id}\n(OCUPADA)" if m_id in activos else f"⚪ {m_id}\n(LIBRE)"
        if cols[i % 4].button(lbl, key=m_id):
            st.session_state.m_sel = m_id

    if "m_sel" in st.session_state and st.session_state.m_sel in MAQUINAS[area_act]:
        m = st.session_state.m_sel
        trabajo = activos.get(m)
        st.divider()

        if not trabajo:
            # FILTRADO DE OPS DISPONIBLES PARA ESTA ÁREA
            res = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).eq("estado", "Pendiente").execute()
            ops = [f"{o['op']} | {o['trabajo']}" for o in res.data]
            if ops:
                sel = st.selectbox("Seleccione OP para iniciar:", ["-- SELECCIONE --"] + ops)
                if st.button("🚀 INICIAR TRABAJO"):
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
                        st.rerun()
            else: st.warning("No hay OPs esperando en esta área.")
        else:
            # FINALIZACIÓN CON BLOQUEO DE CAMPOS VACÍOS
            st.success(f"PROCESANDO: {trabajo['op']} - {trabajo['trabajo']}")
            with st.form("f_final_area"):
                st.subheader("🏁 Datos de KPI (Sin espacios vacíos)")
                res_kpi = {}
                c1, c2 = st.columns(2)
                if area_act == "IMPRESIÓN":
                    res_kpi["metros_impresos"] = c1.number_input("Metros Impresos", 0.0)
                    res_kpi["bobinas"] = c2.number_input("Bobinas", 0)
                elif area_act == "CORTE":
                    res_kpi["total_rollos"] = c1.number_input("Total Rollos", 0)
                    res_kpi["cant_varillas"] = c2.number_input("Varillas", 0)
                elif area_act == "COLECTORAS":
                    res_kpi["total_cajas"] = c1.number_input("Cajas", 0)
                    res_kpi["total_formas"] = c2.number_input("Formas", 0)
                elif area_act == "ENCUADERNACIÓN":
                    res_kpi["cant_final"] = c1.number_input("Cant. Final", 0)
                    res_kpi["presentacion"] = c2.text_input("Presentación (Ej: Paquetes)")

                st.divider()
                k1, k2 = st.columns(2)
                dk = k1.number_input("Desperdicio (Kg)", 0.0)
                mot = k2.text_input("Motivo del Desperdicio")
                obs = st.text_area("Notas Adicionales")
                
                if st.form_submit_button("🏁 FINALIZAR ÁREA"):
                    val_p = list(res_kpi.values())[0] if area_act != "ENCUADERNACIÓN" else res_kpi["cant_final"]
                    
                    if val_p <= 0:
                        st.error("La producción debe ser mayor a 0.")
                    elif dk > 0 and not mot:
                        st.error("Si hay desperdicio, el motivo es obligatorio.")
                    else:
                        op_pref = trabajo['op'].split("-")[0]
                        prox = "FINALIZADO"
                        # LÓGICA DE FLUJO DINÁMICA SEGÚN PREFIJO
                        if op_pref == "RI" and area_act == "IMPRESIÓN": prox = "CORTE"
                        elif op_pref == "FRI" and area_act == "IMPRESIÓN": prox = "COLECTORAS"
                        elif (op_pref == "FRI" or op_pref == "FRB") and area_act == "COLECTORAS": prox = "ENCUADERNACIÓN"
                        
                        # Guardar Historial
                        h = {"op": trabajo['op'], "maquina": m, "trabajo": trabajo['trabajo'], "h_inicio": trabajo['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"), "vendedor": trabajo['vendedor'], "material": trabajo['material'], "desp_kg": dk, "motivo_desp": mot, "observaciones": obs}
                        h.update(res_kpi)
                        
                        # Campos técnicos para KPI
                        if area_act in ["IMPRESIÓN", "CORTE"]: h.update({"gramaje": trabajo['gramaje'], "ancho": trabajo['ancho']})
                        if area_act == "IMPRESIÓN": h.update({"cant_tintas": trabajo['cant_tintas'], "especificacion_tintas": trabajo['especificacion_tintas'], "orientacion_impresion": trabajo['orientacion_impresion']})
                        
                        supabase.table(normalizar(area_act)).insert(h).execute()
                        
                        # Actualizar OP
                        nest = "Pendiente" if prox != "FINALIZADO" else "Finalizado"
                        supabase.table("ordenes_planeadas").update({"proxima_area": prox, "estado": nest}).eq("op", trabajo['op']).execute()
                        supabase.table("trabajos_activos").delete().eq("id", trabajo['id']).execute()
                        st.rerun()

# ==========================================
# 4. CONSOLIDADOS KPI
# ==========================================
elif menu == "📊 Consolidados KPI":
    st.title("📊 Resúmenes de Producción KPI")
    tabs_h = st.tabs(["Impresión", "Corte", "Colectoras", "Encuadernación"])
    areas_db = ["impresion", "corte", "colectoras", "encuadernacion"]
    for i, t in enumerate(tabs_h):
        with t:
            data = supabase.table(areas_db[i]).select("*").order("fecha_fin", desc=True).execute().data
            if data: st.dataframe(pd.DataFrame(data), use_container_width=True)
            else: st.info("Sin registros.")
