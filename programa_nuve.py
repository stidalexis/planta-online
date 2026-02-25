import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V2.3", page_icon="🏭")

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
        op_num = c1.text_input("Número de Orden (Sin prefijo)")
        tr_nom = c2.text_input("Nombre del Trabajo")
        vendedor = c3.text_input("Vendedor")
        
        st.subheader("Ficha Técnica del Trabajo")
        f1, f2, f3 = st.columns(3)
        material = f1.text_input("Material / Sustrato")
        gramaje = f2.text_input("Gramaje")
        ancho = f3.text_input("Ancho / Medida Base")
        
        f4, f5, f6 = st.columns(3)
        unid_sol = f4.number_input("Unidades Solicitadas", min_value=0, step=1)
        core_val = f5.selectbox("Core", ["3 Pulgadas", "1.5 Pulgadas", "Sin Core", "Otro"])
        acabado = f6.radio("Tipo de Prefijo (Siglas)", ["RI (Tintas)", "RB (Blanco)", "FR (Formas)"], horizontal=True)
        
        if st.form_submit_button("✅ REGISTRAR OP EN SISTEMA"):
            if op_num and tr_nom:
                # Lógica de Prefijos según selección
                pref = "RI-" if "RI" in acabado else "RB-" if "RB" in acabado else "FR-"
                op_final = f"{pref}{op_num}".strip().upper()
                
                payload = {
                    "op": op_final,
                    "trabajo": tr_nom,
                    "vendedor": vendedor,
                    "material": material,
                    "gramaje": gramaje,
                    "ancho": ancho,
                    "unidades_solicitadas": int(unid_sol),
                    "core": core_val,
                    "tipo_acabado": acabado,
                    "estado": "Pendiente"
                }
                
                try:
                    supabase.table("ordenes_planeadas").insert(payload).execute()
                    st.success(f"¡Orden {op_final} guardada exitosamente!")
                except Exception as e:
                    st.error(f"Error al guardar: La OP {op_final} ya podría existir.")
            else:
                st.error("Campos obligatorios: Número de OP y Nombre del Trabajo.")

    st.divider()
    st.subheader("Órdenes Registradas (Pendientes)")
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
                    a = activos[m]
                    st.markdown(f"<div class='card-proceso'>⚙️ <b>{m}</b><br>{a['op']}<br>{a['trabajo']}<br><small>{a['vendedor']}</small></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-libre'>⚪ {m}<br>LIBRE</div>", unsafe_allow_html=True)

# ==========================================
# 3. MÓDULOS DE ÁREA (OPERARIOS)
# ==========================================
elif opcion in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_map = {"🖨️ Impresión": "IMPRESIÓN", "✂️ Corte": "CORTE", "📥 Colectoras": "COLECTORAS", "📕 Encuadernación": "ENCUADERNACIÓN"}
    area_sel = area_map[opcion]
    st.title(f"Módulo: {area_sel}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_sel).execute().data}
    paradas = {p['maquina']: p for p in supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data}

    m_sel_lista = st.selectbox("Seleccione su Máquina", ["-- Seleccione --"] + MAQUINAS[area_sel])
    
    if m_sel_lista != "-- Seleccione --":
        m = m_sel_lista
        act = activos.get(m)
        par = paradas.get(m)
        
        st.divider()
        st.subheader(f"🛠️ Control de Máquina: {m}")

        if par:
            st.error(f"🚨 MÁQUINA EN PARADA POR: {par['motivo']}")
            if st.button("▶️ REANUDAR PRODUCCIÓN"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().strftime("%H:%M")}).eq("id", par['id']).execute()
                st.rerun()
        
        elif not act:
            # FLUJO DE INICIO: BUSCAR OP CARGADA
            with st.form("inicio_op_planta"):
                st.info("Escriba la OP completa incluyendo el prefijo (RI-, RB- o FR-)")
                op_input = st.text_input("Número de OP (Ej: RI-123)")
                if st.form_submit_button("🚀 COMENZAR TRABAJO"):
                    res = supabase.table("ordenes_planeadas").select("*").eq("op", op_input.upper().strip()).execute()
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
                        supabase.table("ordenes_planeadas").update({"estado": "En Proceso"}).eq("op", d['op']).execute()
                        st.success(f"¡Turno iniciado para {d['trabajo']}!")
                        st.rerun()
                    else:
                        st.error("La OP no existe en planificación. El administrador debe cargarla primero.")
        else:
            # TRABAJO EN CURSO: MOSTRAR DATOS Y BOTÓN DE FINALIZAR
            st.success(f"TRABAJANDO: {act['op']} | {act['trabajo']}")
            st.info(f"📍 **Vendedor:** {act['vendedor']} | **Material:** {act['material']} | **Core:** {act['core']}")
            
            if st.button("🛑 REGISTRAR PARADA TEMPORAL"):
                mot = st.selectbox("Motivo", ["Mecánico", "Eléctrico", "Limpieza", "Ajuste", "Falta de Material"])
                supabase.table("paradas_maquina").insert({"maquina": m, "op": act['op'], "motivo": mot, "h_inicio": datetime.now().strftime("%H:%M")}).execute()
                st.rerun()

            with st.form("form_final_turno"):
                st.subheader("🏁 Reporte Final de Turno")
                final_res = {}
                c1, c2 = st.columns(2)
                
                if area_sel == "IMPRESIÓN":
                    final_res["metros_impresos"] = c1.number_input("Metros Totales", 0.0)
                    final_res["bobinas"] = c2.number_input("Bobinas Utilizadas", 0)
                elif area_sel == "CORTE":
                    final_res["total_rollos"] = c1.number_input("Total Rollos", 0)
                    final_res["cant_varillas"] = c2.number_input("Total Varillas", 0)
                elif area_sel == "COLECTORAS":
                    final_res["total_cajas"] = c1.number_input("Cajas Producidas", 0)
                    final_res["total_formas"] = c2.number_input("Formas Totales", 0)
                elif area_sel == "ENCUADERNACIÓN":
                    final_res["cant_final"] = c1.number_input("Cantidad Final", 0)
                    final_res["presentacion"] = c2.text_input("Presentación (Ej: Paquetes)")

                dk = st.number_input("Desperdicio Total (Kg)", 0.0)
                obs = st.text_area("Observaciones Finales")
                
                if st.form_submit_button("💾 GUARDAR HISTORIAL Y LIBERAR MÁQUINA"):
                    hist_data = {
                        "op": act['op'], "maquina": m, "trabajo": act['trabajo'],
                        "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                        "vendedor": act['vendedor'], "material": act['material'],
                        "desp_kg": dk, "observaciones": obs
                    }
                    hist_data.update(final_res)
                    
                    # Guardar en la tabla correspondiente al área
                    supabase.table(normalizar(area_sel)).insert(hist_data).execute()
                    # Limpiar activos y actualizar planeación
                    supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                    supabase.table("ordenes_planeadas").update({"estado": "Finalizado"}).eq("op", act['op']).execute()
                    st.success("¡Historial guardado exitosamente!")
                    st.rerun()

# ==========================================
# 4. CONSOLIDADO MAESTRO
# ==========================================
elif opcion == "📊 Consolidado Maestro":
    st.title("📊 Historial de Producción por Área")
    t1, t2, t3, t4 = st.tabs(["Impresión", "Corte", "Colectoras", "Encuadernación"])
    
    with t1:
        st.dataframe(pd.DataFrame(supabase.table("impresion").select("*").order("fecha_fin", desc=True).execute().data), use_container_width=True)
    with t2:
        st.dataframe(pd.DataFrame(supabase.table("corte").select("*").order("fecha_fin", desc=True).execute().data), use_container_width=True)
    with t3:
        st.dataframe(pd.DataFrame(supabase.table("colectoras").select("*").order("fecha_fin", desc=True).execute().data), use_container_width=True)
    with t4:
        st.dataframe(pd.DataFrame(supabase.table("encuadernacion").select("*").order("fecha_fin", desc=True).execute().data), use_container_width=True)
