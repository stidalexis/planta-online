import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE - GESTIÓN DE PRODUCCIÓN", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stButton > button { height: 75px !important; border-radius: 12px; font-weight: bold; border: 2px solid #0D47A1; width: 100%; white-space: pre-wrap !important; }
    .card-proceso { padding: 15px; border-radius: 12px; background-color: #E8F5E9; border-left: 10px solid #2E7D32; margin-bottom: 10px; font-size: 14px; }
    .card-parada { padding: 15px; border-radius: 12px; background-color: #FFEBEE; border-left: 10px solid #C62828; margin-bottom: 10px; font-size: 14px; }
    .card-libre { padding: 15px; border-radius: 12px; background-color: #F5F5F5; border-left: 10px solid #9E9E9E; text-align: center; color: #757575; margin-bottom: 10px; }
    .title-area { background-color: #1A237E; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES DE MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- FUNCIONES AUXILIARES ---
def normalizar(t):
    for k, v in {"Í":"I","Ó":"O","Á":"A","É":"E","Ú":"U"," ":"_"}.items(): t = t.upper().replace(k,v)
    return t.lower()

def safe_float(v):
    if v is None or v == "": return 0.0
    try: return float(str(v).replace(',', '.'))
    except: return 0.0

# --- MENÚ LATERAL ---
opcion = st.sidebar.radio("SISTEMA NUVE", [
    "🖥️ Monitor General", 
    "📅 Planificación (Admin)", 
    "📊 Consolidado Maestro", 
    "🖨️ Impresión", 
    "✂️ Corte", 
    "📥 Colectoras", 
    "📕 Encuadernación"
])

# ==========================================
# 1. PLANIFICACIÓN (ADMINISTRADOR)
# ==========================================
if opcion == "📅 Planificación (Admin)":
    st.title("📅 Carga de Órdenes de Producción")
    
    with st.form("form_plan", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        op_num = c1.text_input("Número de OP (Solo números)")
        tr_nom = c2.text_input("Nombre del Trabajo")
        vendedor = c3.text_input("Vendedor")
        
        st.subheader("Ficha Técnica")
        f1, f2, f3 = st.columns(3)
        material = f1.text_input("Material / Sustrato")
        gramaje = f2.text_input("Gramaje")
        ancho = f3.text_input("Ancho / Medida Base")
        
        f4, f5, f6 = st.columns(3)
        unid_sol = f4.number_input("Unidades Solicitadas", min_value=0)
        core_val = f5.selectbox("Core", ["3 Pulgadas", "1.5 Pulgadas", "Sin Core", "Otro"])
        acabado = f6.radio("Tipo de Prefijo", ["RI (Tintas)", "RB (Blanco)", "FR (Formas)"], horizontal=True)
        
        if st.form_submit_button("✅ REGISTRAR ORDEN"):
            if op_num and tr_nom:
                # Aplicación de Prefijos
                pref = "RI-" if "RI" in acabado else "RB-" if "RB" in acabado else "FR-"
                op_final = f"{pref}{op_num}"
                
                payload = {
                    "op": op_final, "trabajo": tr_nom, "vendedor": vendedor,
                    "material": material, "gramaje": gramaje, "ancho": ancho,
                    "unidades_solicitadas": unid_sol, "core": core_val,
                    "tipo_acabado": acabado, "estado": "Pendiente"
                }
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.success(f"Orden {op_final} guardada exitosamente.")
            else:
                st.error("Por favor rellene el número de OP y el nombre del trabajo.")

    st.divider()
    st.subheader("Órdenes en Espera")
    ops_pend = supabase.table("ordenes_planeadas").select("*").eq("estado", "Pendiente").order("fecha_creacion", desc=True).execute()
    if ops_pend.data:
        st.dataframe(pd.DataFrame(ops_pend.data), use_container_width=True)

# ==========================================
# 2. MONITOR GENERAL
# ==========================================
elif opcion == "🖥️ Monitor General":
    st.title("🖥️ Estado de Planta")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}
    
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(lista):
            with cols[idx % 4]:
                if m in paradas:
                    st.markdown(f"<div class='card-parada'>🚨 <b>{m}</b><br>PARADA: {paradas[m]['motivo']}<br>OP: {paradas[m]['op']}</div>", unsafe_allow_html=True)
                elif m in activos:
                    st.markdown(f"<div class='card-proceso'>⚙️ <b>{m}</b><br>OP: {activos[m]['op']}<br>{activos[m]['trabajo']}<br><small>{activos[m]['vendedor']}</small></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-libre'>⚪ {m}<br>LIBRE</div>", unsafe_allow_html=True)

# ==========================================
# 3. ÁREAS DE PRODUCCIÓN
# ==========================================
elif opcion in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_sel = area_map[opcion]
    st.title(f"Módulo: {area_sel}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_sel).execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    # Grid de selección de máquina
    m_cols = st.columns(3)
    for i, m in enumerate(MAQUINAS[area_sel]):
        label = f"⚪ {m}\nDISPONIBLE"
        if m in paradas: label = f"🚨 {m}\nPARADA"
        elif m in activos: label = f"⚙️ {m}\n{activos[m]['op']}"
        
        if m_cols[i % 3].button(label, key=f"btn_{m}"):
            st.session_state.active_m = m

    # Panel de Operación
    if "active_m" in st.session_state and st.session_state.active_m in MAQUINAS[area_sel]:
        m = st.session_state.active_m
        act = activos.get(m)
        par = paradas.get(m)
        st.divider()
        st.subheader(f"🕹️ Control de Máquina: {m}")

        if par:
            st.warning(f"MÁQUINA PARADA POR: {par['motivo']}")
            if st.button("▶️ REANUDAR TRABAJO"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()
        
        elif not act:
            # INICIO DE TRABAJO (JALANDO OP)
            with st.form("inicio_planta"):
                st.info("Ingrese la OP completa (Ej: RI-123, RB-456, FR-789)")
                op_input = st.text_input("Número de OP")
                if st.form_submit_button("🚀 INICIAR TURNO"):
                    res = supabase.table("ordenes_planeadas").select("*").eq("op", op_input).execute()
                    if res.data:
                        d = res.data[0]
                        payload_act = {
                            "maquina": m, "op": d['op'], "trabajo": d['trabajo'], "area": area_sel,
                            "vendedor": d['vendedor'], "material": d['material'], "gramaje": d['gramaje'],
                            "ancho": d['ancho'], "unidades_solicitadas": d['unidades_solicitadas'],
                            "core": d['core'], "tipo_acabado": d['tipo_acabado'],
                            "hora_inicio": datetime.now().strftime("%H:%M")
                        }
                        supabase.table("trabajos_activos").insert(payload_act).execute()
                        supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", op_input).execute()
                        st.success("¡Buen turno! Trabajo iniciado."); st.rerun()
                    else:
                        st.error("La OP no existe en la planificación del administrador.")
        else:
            # TRABAJO EN CURSO - FINALIZACIÓN
            st.success(f"PRODUCIENDO: {act['op']} | {act['trabajo']}")
            st.write(f"**Material:** {act['material']} | **Vendedor:** {act['vendedor']} | **Core:** {act['core']}")
            
            c1, c2 = st.columns(2)
            if c1.button("🛑 REGISTRAR PARADA"):
                mot = st.selectbox("Motivo de parada", ["Mecánico", "Ajuste", "Limpieza", "Material", "Eléctrico"])
                supabase.table("paradas_maquina").insert({"maquina": m, "op": act['op'], "motivo": mot, "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                st.rerun()

            with st.form("form_fin"):
                st.subheader("🏁 Reporte de Finalización")
                data_fin = {}
                col_a, col_b = st.columns(2)
                
                if area_sel == "IMPRESIÓN":
                    data_fin["metros_impresos"] = col_a.number_input("Metros Totales", 0.0)
                    data_fin["bobinas"] = col_b.number_input("Cantidad Bobinas", 0)
                elif area_sel == "CORTE":
                    data_fin["total_rollos"] = col_a.number_input("Total Rollos", 0)
                    data_fin["cant_varillas"] = col_b.number_input("Total Varillas", 0)
                elif area_sel == "COLECTORAS":
                    data_fin["total_cajas"] = col_a.number_input("Total Cajas", 0)
                    data_fin["total_formas"] = col_b.number_input("Total Formas", 0)
                elif area_sel == "ENCUADERNACIÓN":
                    data_fin["cant_final"] = col_a.number_input("Cantidad Final", 0)
                    data_fin["presentacion"] = col_b.text_input("Presentación (Ej: Paquetes)")

                dk = st.number_input("Desperdicio (Kg)", 0.0)
                obs = st.text_area("Observaciones del turno")
                
                if st.form_submit_button("💾 FINALIZAR Y GUARDAR HISTORIAL"):
                    final_hist = {
                        "op": act['op'], "maquina": m, "trabajo": act['trabajo'],
                        "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                        "vendedor": act['vendedor'], "material": act['material'],
                        "desp_kg": dk, "observaciones": obs
                    }
                    final_hist.update(data_fin)
                    
                    # Guardar y limpiar
                    supabase.table(normalizar(area_sel)).insert(final_hist).execute()
                    supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                    supabase.table("ordenes_planeadas").update({"estado": "Finalizado"}).eq("op", act['op']).execute()
                    st.success("Historial guardado. Máquina liberada."); st.rerun()

# ==========================================
# 4. CONSOLIDADO MAESTRO
# ==========================================
elif opcion == "📊 Consolidado Maestro":
    st.title("📊 Historial de Producción")
    t1, t2, t3, t4 = st.tabs(["Impresión", "Corte", "Colectoras", "Encuadernación"])
    
    with t1:
        st.dataframe(pd.DataFrame(supabase.table("impresion").select("*").execute().data), use_container_width=True)
    with t2:
        st.dataframe(pd.DataFrame(supabase.table("corte").select("*").execute().data), use_container_width=True)
    with t3:
        st.dataframe(pd.DataFrame(supabase.table("colectoras").select("*").execute().data), use_container_width=True)
    with t4:
        st.dataframe(pd.DataFrame(supabase.table("encuadernacion").select("*").execute().data), use_container_width=True)
