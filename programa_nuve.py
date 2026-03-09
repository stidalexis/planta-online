import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V28 - TOTAL", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; font-size: 18px !important; width: 100%; }
    .title-area { background-color: #0D47A1; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 22px; margin-bottom: 20px; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 20px; border-radius: 15px; text-align: center; color: #1B5E20; font-weight: bold; font-size: 18px; margin-bottom: 10px; }
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 20px; border-radius: 15px; text-align: center; color: #9E9E9E; font-size: 16px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}
PRESENTACIONES = ["LIBRETAS TAPADURA", "BLOCK LICOM", "HOJAS SUELTAS", "PAQUETES", "TACOS", "CAJAS", "ROLLOS"]

# --- ESTADOS DE SESIÓN ---
if 'sel_tipo' not in st.session_state: st.session_state.sel_tipo = None
if 'detalle_op_id' not in st.session_state: st.session_state.detalle_op_id = None
if 'rep' not in st.session_state: st.session_state.rep = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🏭 NUVE V28")
    menu = st.radio("MÓDULOS", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# --- MONITOR ---
if menu == "🖥️ Monitor":
    st.title("Monitor de Planta")
    res = supabase.table("trabajos_activos").select("*").execute().data
    act = {a['maquina']: a for a in res}
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    st.markdown(f"<div class='card-produccion'>{m}<br>{act[m]['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'>{m}<br>LIBRE</div>", unsafe_allow_html=True)
    time.sleep(30); st.rerun()

# --- SEGUIMIENTO ---
elif menu == "🔍 Seguimiento":
    st.title("Seguimiento y Registro Histórico")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if res:
        df = pd.DataFrame(res)
        st.dataframe(df[['op', 'cliente', 'nombre_trabajo', 'proxima_area']])
        # (Se puede añadir aquí la lógica de visualización detallada original si se desea)

# --- PLANIFICACIÓN ---
elif menu == "📅 Planificación":
    st.title("Nueva Orden de Producción")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📑 FORMAS IMPRESAS"): st.session_state.sel_tipo = "FORMAS IMPRESAS"
    if c2.button("📄 FORMAS BLANCAS"): st.session_state.sel_tipo = "FORMAS BLANCAS"
    if c3.button("🌀 ROLLOS IMPRESOS"): st.session_state.sel_tipo = "ROLLOS IMPRESOS"
    if c4.button("⚪ ROLLOS BLANCOS"): st.session_state.sel_tipo = "ROLLOS BLANCOS"

    if st.session_state.sel_tipo:
        t = st.session_state.sel_tipo
        with st.form("form_v28"):
            st.subheader(f"Configurando: {t}")
            f1, f2, f3 = st.columns(3)
            op_n = f1.text_input("Número de OP").upper()
            op_a = f2.text_input("OP Anterior")
            cli = f3.text_input("Cliente")
            f4, f5 = st.columns(2)
            vend = f4.text_input("Vendedor")
            trab = f5.text_input("Nombre Trabajo")

            payload = {"op": op_n, "op_anterior": op_a, "cliente": cli, "vendedor": vend, "nombre_trabajo": trab, "tipo_orden": t}

            if "FORMAS" in t:
                g1, g2 = st.columns(2)
                cant_f = g1.number_input("Cantidad Formas", 0)
                partes = g2.selectbox("Partes", [1,2,3,4,5,6])
                p1, p2 = st.columns(2)
                perf_d = p1.text_area("Detalle Perforación", "N/A")
                barr_d = p2.text_area("Detalle Barras", "N/A")
                pres = st.selectbox("Presentación", ["LIBRETAS TAPADURA", "BLOCK LICOM", "HOJAS SUELTAS", "PAQUETES", "TACOS"])
                obs = st.text_area("Observaciones")
                
                ruta = "IMPRESIÓN" if t == "FORMAS IMPRESAS" else "COLECTORAS"
                payload.update({"proxima_area": ruta, "cantidad_formas": int(cant_f), "num_partes": partes, "perforaciones_detalle": perf_d, "codigo_barras_detalle": barr_d, "presentacion": pres, "observaciones_formas": obs})
            else:
                r1, r2, r3 = st.columns(3)
                mat = r1.text_input("Material")
                gram = r2.text_input("Gramaje")
                ref_c = r3.text_input("Ref. Comercial")
                cant_r = st.number_input("Cantidad Rollos", 0)
                obs = st.text_area("Observaciones")
                
                ruta = "IMPRESIÓN" if t == "ROLLOS IMPRESOS" else "CORTE"
                payload.update({"proxima_area": ruta, "material": mat, "gramaje_rollos": gram, "ref_comercial": ref_c, "cantidad_rollos": int(cant_r), "observaciones_rollos": obs})

            if st.form_submit_button("🚀 GUARDAR ORDEN"):
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.success(f"Guardado. Próxima área: {ruta}")
                st.session_state.sel_tipo = None
                time.sleep(1); st.rerun()

# --- MÓDULOS DE PRODUCCIÓN ---
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.markdown(f"<div class='title-area'>PANEL: {area_act}</div>", unsafe_allow_html=True)
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    
    cols = st.columns(3)
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols[idx % 3]:
            if m in activos:
                tr = activos[m]
                st.markdown(f"<div class='card-produccion'>🟡 {m}<br>OP: {tr['op']}</div>", unsafe_allow_html=True)
                if st.button(f"✅ FINALIZAR", key=f"f_{m}"):
                    st.session_state.rep = tr
                    st.rerun()
            else:
                st.markdown(f"<div class='card-vacia'>⚪ {m}<br>LIBRE</div>", unsafe_allow_html=True)
                ops = supabase.table("ordenes_planeadas").select("op").eq("proxima_area", area_act).execute().data
                if ops:
                    sel = st.selectbox("Asignar OP", [o['op'] for o in ops], key=f"s_{m}")
                    if st.button(f"🚀 INICIAR {m}", key=f"str_{m}"):
                        supabase.table("trabajos_activos").insert({"maquina": m, "area": area_act, "op": sel, "hora_inicio": datetime.now().isoformat()}).execute()
                        st.rerun()

    # --- CIERRE TÉCNICO ---
    if st.session_state.rep:
        r = st.session_state.rep
        st.divider()
        with st.form("cierre_tecnico"):
            st.warning(f"### CIERRE TÉCNICO: {area_act} | OP {r['op']}")
            op_name = st.text_input("Operario Responsable *")
            desp = st.number_input("Desperdicio", 0.0)
            obs_t = st.text_area("Observaciones")

            if st.form_submit_button("🏁 FINALIZAR TAREA"):
                if not op_name:
                    st.error("Debe ingresar el operario")
                else:
                    # CORRECCIÓN DE FECHA ROBUSTA
                    inicio = pd.to_datetime(r['hora_inicio']).replace(tzinfo=None)
                    fin = datetime.now()
                    duracion = str(fin - inicio).split('.')[0]
                    
                    d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                    
                    # Lógica de flujo
                    n_area = "FINALIZADO"
                    if "ROLLOS" in d_op['tipo_orden'] and area_act == "IMPRESIÓN": n_area = "CORTE"
                    elif "FORMAS" in d_op['tipo_orden']:
                        if area_act == "IMPRESIÓN": n_area = "COLECTORAS"
                        elif area_act == "COLECTORAS": n_area = "ENCUADERNACIÓN"

                    # HISTORIAL (CORREGIDO: historial_procesos)
                    h = d_op.get('historial_procesos', []) or []
                    h.append({
                        "area": area_act, "maquina": r['maquina'], "operario": op_name,
                        "fecha": fin.strftime("%d/%m/%Y %H:%M"), "duracion": duracion,
                        "datos_cierre": {"desperdicio": desp, "obs": obs_t}
                    })
                    
                    # ACTUALIZACIÓN EN SUPABASE
                    supabase.table("ordenes_planeadas").update({"proxima_area": n_area, "historial_procesos": h}).eq("op", r['op']).execute()
                    supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()
                    
                    st.session_state.rep = None
                    st.success("¡OP Actualizada!")
                    time.sleep(1); st.rerun()
