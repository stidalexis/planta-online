import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V27 - TOTAL", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
# Asegúrate de tener estas llaves en tu archivo .streamlit/secrets.toml
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS CSS (DISEÑO TÁCTIL Y CORPORATIVO) ---
st.markdown("""
    <style>
    /* Estilos Generales */
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; font-size: 18px !important; width: 100%; }
    .title-area { background-color: #0D47A1; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 22px; margin-bottom: 20px; }
    .info-box { background-color: #f8f9fa; border-left: 5px solid #0d47a1; padding: 10px; margin-bottom: 5px; border-radius: 4px; }
    
    /* Tarjetas de Monitor y Producción */
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 20px; border-radius: 15px; text-align: center; color: #1B5E20; font-weight: bold; font-size: 18px; margin-bottom: 10px; }
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 20px; border-radius: 15px; text-align: center; color: #9E9E9E; font-size: 16px; margin-bottom: 10px; }
    .card-parada { background-color: #FFCDD2; border: 2px solid #D32F2F; padding: 20px; border-radius: 15px; text-align: center; color: #B71C1C; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

MOTIVOS_PARADA = ["CAMBIO DE TRABAJO", "MANTENIMIENTO", "FALLA MECÁNICA", "FALLA ELÉCTRICA", "ESPERA DE MATERIAL", "ALMUERZO / DESCANSO", "AJUSTE DE CALIDAD"]

# --- ESTADOS DE SESIÓN ---
if 'sel_tipo' not in st.session_state: st.session_state.sel_tipo = None
if 'detalle_op_id' not in st.session_state: st.session_state.detalle_op_id = None
if 'rep' not in st.session_state: st.session_state.rep = None

# --- SIDEBAR NAV ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/8039/8039501.png", width=100)
    st.title("NUVE V27 - CONTROL TOTAL")
    menu = st.radio("MÓDULOS", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])
    st.divider()
    st.caption("Sistema de Gestión de Planta v27.0")

# --- FUNCIONES DE AYUDA (EXCEL) ---
def to_excel_limpio(df_input, tipo=None):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        if tipo == "GENERAL":
            df_f = df_input[df_input['tipo_orden'].str.contains("FORMAS", na=False)].dropna(axis=1, how='all')
            df_r = df_input[df_input['tipo_orden'].str.contains("ROLLOS", na=False)].dropna(axis=1, how='all')
            if not df_f.empty: df_f.to_excel(writer, index=False, sheet_name='FORMAS')
            if not df_r.empty: df_r.to_excel(writer, index=False, sheet_name='ROLLOS')
        else:
            df_unit = df_input.dropna(axis=1, how='all')
            cols_to_drop = [c for c in ['id', 'detalles_partes_json'] if c in df_unit.columns]
            df_unit.drop(columns=cols_to_drop).to_excel(writer, index=False, sheet_name='DETALLE_OP')
    return output.getvalue()

# ==========================================
# 1. MONITOR DE PLANTA
# ==========================================
if menu == "🖥️ Monitor":
    st.title("Monitor de Planta en Tiempo Real")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    st.markdown(f"<div class='card-produccion'>{m}<br><small>{act[m]['op']}</small></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'>{m}<br><small>LIBRE</small></div>", unsafe_allow_html=True)
    time.sleep(30); st.rerun()

# ==========================================
# 2. SEGUIMIENTO (HISTORIAL Y EXCEL)
# ==========================================
elif menu == "🔍 Seguimiento":
    st.title("Seguimiento de Órdenes")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    
    if res:
        df = pd.DataFrame(res)
        st.download_button("📥 Reporte General Excel", to_excel_limpio(df, "GENERAL"), "Reporte_Planta.xlsx")
        
        st.write("---")
        h1, h2, h3, h4, h5, h6 = st.columns([1, 2, 2, 2, 2, 1])
        h1.write("**OP**"); h2.write("**Cliente**"); h3.write("**Trabajo**"); h4.write("**Tipo**"); h5.write("**Ubicación**"); h6.write("**Ver**")
        
        for index, row in df.iterrows():
            r1, r2, r3, r4, r5, r6 = st.columns([1, 2, 2, 2, 2, 1])
            r1.write(row['op'])
            r2.write(row['cliente'])
            r3.write(row['nombre_trabajo'])
            r4.write(row['tipo_orden'])
            color = "#FF9800" if row['proxima_area'] != "FINALIZADO" else "#4CAF50"
            r5.markdown(f"<span style='color:{color}; font-weight:bold;'>{row['proxima_area']}</span>", unsafe_allow_html=True)
            if r6.button("👁️", key=f"v_{row['op']}"): st.session_state.detalle_op_id = row['op']

        if st.session_state.detalle_op_id:
            d = df[df['op'] == st.session_state.detalle_op_id].iloc[0].to_dict()
            st.markdown("---")
            with st.expander(f"FICHA TÉCNICA: {d['op']}", expanded=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("**INFORMACIÓN COMERCIAL**")
                    st.info(f"Cliente: {d['cliente']}\n\nTrabajo: {d['nombre_trabajo']}\n\nVendedor: {d['vendedor']}")
                with c2:
                    st.markdown("**DATOS TÉCNICOS**")
                    if "FORMAS" in d['tipo_orden']:
                        st.write(f"Cant: {d['cantidad_formas']} | Partes: {d['num_partes']}")
                        st.write(f"Perf: {d['perforaciones_detalle']}")
                    else:
                        st.write(f"Material: {d['material']} | Core: {d['core']}")
                with c3:
                    st.markdown("**BITÁCORA DE PLANTA**")
                    if d['historial_procesos']:
                        for h in d['historial_procesos']:
                            st.success(f"📍 {h['area']} ({h['operario']}) - {h.get('duracion', '')}")
                if st.button("Cerrar Ficha"): st.session_state.detalle_op_id = None; st.rerun()

# ==========================================
# 3. PLANIFICACIÓN
# ==========================================
elif menu == "📅 Planificación":
    st.title("Crear Nueva Orden")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📑 FORMAS IMPRESAS"): st.session_state.sel_tipo = "FORMAS IMPRESAS"
    if c2.button("📄 FORMAS BLANCAS"): st.session_state.sel_tipo = "FORMAS BLANCAS"
    if c3.button("🌀 ROLLOS IMPRESOS"): st.session_state.sel_tipo = "ROLLOS IMPRESOS"
    if c4.button("⚪ ROLLOS BLANCOS"): st.session_state.sel_tipo = "ROLLOS BLANCOS"

    if st.session_state.sel_tipo:
        t = st.session_state.sel_tipo
        with st.form("form_planificacion", clear_on_submit=True):
            st.subheader(f"Formulario: {t}")
            f1, f2, f3 = st.columns(3)
            op_n = f1.text_input("Número de OP *")
            op_a = f2.text_input("OP Anterior")
            cli = f3.text_input("Cliente *")
            
            if "FORMAS" in t:
                g1, g2 = st.columns(2)
                cant_f = g1.number_input("Cantidad Formas", 0)
                partes = g2.selectbox("Número de Partes", [1,2,3,4,5,6])
                p1, p2 = st.columns(2)
                t_perf = p1.selectbox("¿Perforación?", ["NO", "SI"])
                perf_d = p1.text_area("Detalle Perf.") if t_perf == "SI" else "NO"
                t_barr = p2.selectbox("¿Barras?", ["NO", "SI"])
                barr_d = p2.text_area("Detalle Barras") if t_barr == "SI" else "NO"
                obs = st.text_area("Observaciones")
            else:
                r1, r2, r3 = st.columns(3)
                mat = r1.text_input("Material")
                gram = r2.text_input("Gramaje")
                core = st.selectbox("Core", ["13MM", "19MM", "1 PULGADA", "40 MM", "3 PULGADAS"])
                cant_r = st.number_input("Cantidad Rollos", 0)
                obs = st.text_area("Observaciones")

            if st.form_submit_button("🚀 GUARDAR E INICIAR RUTA"):
                ruta = "IMPRESIÓN"
                if t == "ROLLOS BLANCOS": ruta = "CORTE"
                if t == "FORMAS BLANCAS": ruta = "COLECTORAS"
                
                payload = {"op": op_n.upper(), "op_anterior": op_a, "cliente": cli, "tipo_orden": t, "proxima_area": ruta}
                if "FORMAS" in t: payload.update({"cantidad_formas": int(cant_f), "num_partes": partes, "perforaciones_detalle": perf_d, "codigo_barras_detalle": barr_d, "observaciones_formas": obs})
                else: payload.update({"material": mat, "gramaje_rollos": gram, "cantidad_rollos": int(cant_r), "core": core, "observaciones_rollos": obs})
                
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.success(f"OP {op_n} enviada a {ruta}")
                st.session_state.sel_tipo = None; time.sleep(1); st.rerun()

# ==========================================
# 4. PANELES DE PRODUCCIÓN (TÁCTILES)
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.markdown(f"<div class='title-area'>PANEL TÁCTIL: {area_act}</div>", unsafe_allow_html=True)
    
    # Obtener activos
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    
    cols = st.columns(3)
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols[idx % 3]:
            if m in activos:
                tr = activos[m]
                st.markdown(f"<div class='card-produccion'>🟡 {m}<br>OP: {tr['op']}</div>", unsafe_allow_html=True)
                
                c_btn1, c_btn2 = st.columns(2)
                if c_btn1.button(f"🛑 PARADA", key=f"p_{m}"):
                    st.toast(f"Parada de emergencia registrada en {m}")
                    # Aquí se puede extender para guardar en tabla de paradas
                if c_btn2.button(f"✅ CERRAR", key=f"f_{m}"):
                    st.session_state.rep = tr
            else:
                st.markdown(f"<div class='card-vacia'>⚪ {m}<br>LIBRE</div>", unsafe_allow_html=True)
                ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
                if ops:
                    sel_op = st.selectbox("Asignar OP", [o['op'] for o in ops], key=f"s_{m}")
                    if st.button(f"🚀 INICIAR {m}", key=f"start_{m}"):
                        d = next(o for o in ops if o['op'] == sel_op)
                        supabase.table("trabajos_activos").insert({
                            "maquina": m, "area": area_act, "op": d['op'], 
                            "trabajo": d['nombre_trabajo'], "hora_inicio": datetime.now().isoformat()
                        }).execute()
                        st.rerun()

    # --- MODAL DE CIERRE TÉCNICO ---
    if st.session_state.rep:
        r = st.session_state.rep
        st.markdown("---")
        st.warning(f"### 📋 CIERRE TÉCNICO - OP: {r['op']} en {r['maquina']}")
        
        with st.form("cierre_tecnico"):
            operario = st.text_input("Nombre Operario *")
            
            if area_act == "IMPRESIÓN":
                
                c1, c2, c3 = st.columns(3)
                metros = c1.number_input("Metros Impresos", 0)
                bobinas = c2.number_input("Cant. Bobinas", 0)
                imgs = c3.number_input("Imágenes x Bobina", 0)
                c4, c5, c6 = st.columns(3)
                tinta = c4.number_input("Tinta Gastada (Kg)", 0.0)
                planchas = c5.number_input("Planchas Gastadas", 0)
                desp = c6.number_input("Desperdicio", 0.0)
                motivo = st.selectbox("Motivo Desperdicio", ["Arranque", "Falla Máquina", "Papel Defectuoso"])
                obs = st.text_area("Observaciones de Impresión")

            elif area_act == "CORTE":
                
                c1, c2, c3 = st.columns(3)
                varillas = c1.number_input("Total Varillas", 0)
                rollos_c = c2.number_input("Total Rollos", 0)
                imgs_v = c3.number_input("Imágenes x Varilla", 0)
                c4, c5 = st.columns(2)
                cajas = c4.number_input("Cantidad de Cajas", 0)
                desp_c = c5.number_input("Desperdicio Corte", 0.0)
                motivo = st.selectbox("Motivo Desperdicio", ["Mal Corte", "Núcleo Dañado"])
                obs = st.text_area("Observaciones de Corte")

            else: # Colectoras y Encuadernación
                desp = st.number_input("Desperdicio", 0.0)
                obs = st.text_area("Observaciones Generales")
                motivo = "Proceso"

            if st.form_submit_button("🏁 FINALIZAR Y ACTUALIZAR STATUS"):
                if not operario:
                    st.error("El nombre del operario es obligatorio")
                else:
                    # Calcular tiempo
                    inicio = datetime.fromisoformat(r['hora_inicio'])
                    fin = datetime.now()
                    duracion = str(fin - inicio).split('.')[0]
                    
                    # Datos OP
                    d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                    
                    # Siguiente paso
                    n_area = "FINALIZADO"
                    if "ROLLOS" in d_op['tipo_orden'] and area_act == "IMPRESIÓN": n_area = "CORTE"
                    elif "FORMAS" in d_op['tipo_orden']:
                        if area_act == "IMPRESIÓN": n_area = "COLECTORAS"
                        elif area_act == "COLECTORAS": n_area = "ENCUADERNACIÓN"
                    
                    # Guardar Historial
                    h = d_op['historial_procesos'] if d_op['historial_procesos'] else []
                    h.append({
                        "area": area_act, "maquina": r['maquina'], "operario": operario,
                        "fecha": fin.strftime("%d/%m/%Y %H:%M"), "duracion": duracion,
                        "tecnico": {"desperdicio": locals().get('desp', 0), "obs": obs}
                    })
                    
                    supabase.table("ordenes_planeadas").update({"proxima_area": n_area, "historial_procesos": h}).eq("op", r['op']).execute()
                    supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()
                    
                    st.session_state.rep = None
                    st.success(f"Trabajo Finalizado. Duración: {duracion}")
                    time.sleep(1); st.rerun()
