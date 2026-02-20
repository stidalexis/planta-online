import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="ERP PLANTA INDUSTRIAL 2026", page_icon="🏭")

# --- ESTILOS CSS PARA INTERFAZ TÁCTIL ---
st.markdown("""
    <style>
    .stButton > button { height: 70px; font-weight: bold; border-radius: 12px; font-size: 18px; }
    .card-activa { border-left: 10px solid #2ecc71; padding: 15px; background: #e8f5e9; border-radius: 10px; margin-bottom: 5px; color: #1b5e20; }
    .card-parada { border-left: 10px solid #e74c3c; padding: 15px; background: #fdecea; border-radius: 10px; margin-bottom: 5px; color: #b71c1c; }
    .card-libre { border-left: 10px solid #bdc3c7; padding: 15px; background: #f8f9fa; border-radius: 10px; margin-bottom: 5px; color: #616161; }
    </style>
    """, unsafe_allow_html=True)

# --- SISTEMA DE LOGIN ---
if "auth" not in st.session_state: st.session_state.update({"auth": False, "rol": None})
if not st.session_state.auth:
    st.title("🏭 ACCESO AL SISTEMA INTEGRAL")
    usuarios = {"administrador": "admin2026", "impresion": "imp2026", "colectoras": "col2026", "corte1": "c1p", "corte2": "c2p", "encuadernacion": "enc2026"}
    u = st.text_input("Usuario").lower().strip()
    p = st.text_input("Contraseña", type="password")
    if st.button("INGRESAR"):
        if u in usuarios and usuarios[u] == p:
            st.session_state.auth, st.session_state.rol = True, u
            st.rerun()
    st.stop()

rol = st.session_state.rol

# --- CONFIGURACIÓN DE MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": ["LINEA-01"]
}

# --- FUNCIONES DE MONITOREO ---
def monitor_visual(area_nombre=None):
    st.subheader(f"📊 MONITOR DE ESTADO - {area_nombre if area_nombre else 'PLANTA TOTAL'}")
    res_act = supabase.table("trabajos_activos").select("*").execute().data
    res_par = supabase.table("paradas_maquina").select("*").is_("h_fin", "null").execute().data
    
    activos = {a['maquina']: a for a in res_act}
    paradas = {p['maquina']: p for p in res_par}
    
    lista_maqs = MAQUINAS[area_nombre] if area_nombre else [m for l in MAQUINAS.values() for m in l]
    
    cols = st.columns(4)
    for i, m in enumerate(lista_maqs):
        with cols[i % 4]:
            if m in paradas:
                st.markdown(f"<div class='card-parada'>🚨 <b>{m}</b><br>PARADA: {paradas[m]['motivo']}</div>", unsafe_allow_html=True)
            elif m in activos:
                st.markdown(f"<div class='card-activa'>⚙️ <b>{m}</b><br>OP: {activos[m]['op']}<br>{activos[m]['trabajo']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='card-libre'>⚪ <b>{m}</b><br>DISPONIBLE</div>", unsafe_allow_html=True)

# --- PANEL DE ADMINISTRADOR ---
if rol == "administrador":
    menu = st.sidebar.radio("ADMINISTRACIÓN", ["MONITOR GLOBAL", "GESTIÓN DE METAS", "DESCARGAR DATOS"])
    
    if menu == "MONITOR GLOBAL":
        monitor_visual()
        
    elif menu == "GESTIÓN DE METAS":
        st.header("🎯 Configuración de Objetivos")
        a_sel = st.selectbox("Área", list(MAQUINAS.keys()))
        m_sel = st.selectbox("Máquina", MAQUINAS[a_sel])
        meta = st.number_input("Meta por Hora", 0)
        if st.button("ACTUALIZAR META"):
            supabase.table("metas_produccion").upsert({"maquina": m_sel, "meta_unidades": meta, "area": a_sel}).execute()
            st.success("Meta guardada")

    elif menu == "DESCARGAR DATOS":
        st.header("📂 Exportación de Historiales")
        tabla = st.selectbox("Tabla:", ["impresion", "corte", "colectoras", "encuadernacion", "paradas_maquina"])
        df = pd.DataFrame(supabase.table(tabla).select("*").execute().data)
        st.dataframe(df)
        st.download_button("Descargar CSV", df.to_csv(index=False), f"reporte_{tabla}.csv")

# --- MÓDULOS DE OPERARIOS ---
else:
    area_op = "IMPRESIÓN" if rol == "impresion" else "CORTE" if "corte" in rol else "COLECTORAS" if rol == "colectoras" else "ENCUADERNACIÓN"
    st.header(f"ZONA DE TRABAJO: {area_op}")
    
    monitor_visual(area_op)
    st.divider()
    
    # Selector de máquina táctil
    st.write("### 🔘 Seleccione su Máquina:")
    cols_t = st.columns(4)
    for i, m_btn in enumerate(MAQUINAS[area_op]):
        if cols_t[i % 4].button(m_btn, key=f"t_{m_btn}", use_container_width=True):
            st.session_state.m_seleccionada = m_btn
            
    if "m_seleccionada" in st.session_state:
        m = st.session_state.m_seleccionada
        st.subheader(f"Gestión de Máquina: {m}")
        
        # Verificar estado
        activos_db = supabase.table("trabajos_activos").select("*").eq("maquina", m).execute().data
        paradas_db = supabase.table("paradas_maquina").select("*").eq("maquina", m).is_("h_fin", "null").execute().data

        # CASO 1: MÁQUINA EN PARADA
        if paradas_db:
            st.error(f"⚠️ MÁQUINA DETENIDA POR: {paradas_db[0]['motivo']}")
            if st.button("✅ REANUDAR PRODUCCIÓN (FIN PARADA)"):
                supabase.table("paradas_maquina").update({"h_fin": datetime.now().isoformat()}).eq("id", paradas_db[0]['id']).execute()
                st.rerun()
        
        # CASO 2: MÁQUINA LIBRE
        elif not activos_db:
            with st.form("inicio_op"):
                st.write("📋 Iniciar Nueva Orden")
                op_i = st.text_input("OP")
                tr_i = st.text_input("Nombre del Trabajo")
                if st.form_submit_button("▶️ ABRIR TURNO"):
                    supabase.table("trabajos_activos").insert({"maquina":m, "op":op_i, "trabajo":tr_i, "area":area_op, "usuario":rol}).execute()
                    st.rerun()
        
        # CASO 3: TRABAJANDO (CIERRE O PARADA)
        else:
            act = activos_db[0]
            st.success(f"TRABAJANDO EN OP: {act['op']} - {act['trabajo']}")
            
            c_par, c_fin = st.columns(2)
            
            with c_par:
                st.warning("🚨 PARADA DE MÁQUINA")
                motivo = st.selectbox("Motivo:", ["Mantenimiento", "Falla Eléctrica", "Cambio de Rollo", "Falta Material", "Limpieza", "Almuerzo"])
                if st.button("DETENER MÁQUINA"):
                    supabase.table("paradas_maquina").insert({"maquina":m, "op":act['op'], "motivo":motivo, "usuario":rol}).execute()
                    st.rerun()

            with c_fin:
                st.subheader("🏁 FINALIZAR Y GUARDAR")
                with st.form("form_final"):
                    datos_finales = {}
                    if area_op == "IMPRESIÓN":
                        c1, c2 = st.columns(2)
                        datos_finales = {
                            "papel": c1.text_input("Papel"), "ancho": c2.text_input("Ancho"),
                            "gramaje": c1.text_input("Gramaje"), "tintas": c2.number_input("Tintas", 0),
                            "medida": c1.text_input("Medida"), "metros": c2.number_input("Metros Finales", 0)
                        }
                    elif area_op == "CORTE":
                        c1, c2 = st.columns(2)
                        datos_finales = {
                            "img_varilla": c1.number_input("Img x Varilla", 0), "medida": c2.text_input("Medida"),
                            "total_varillas": c1.number_input("Total Varillas", 0), "rollos_cortados": c2.number_input("Rollos", 0)
                        }
                    elif area_op == "COLECTORAS":
                        c1, c2 = st.columns(2)
                        datos_finales = {
                            "medida_forma": c1.text_input("Medida Forma"), "unid_caja": c2.number_input("Unid/Caja", 0),
                            "total_cajas": c1.number_input("Total Cajas", 0), "total_formas": c2.number_input("Total Formas", 0)
                        }
                    elif area_op == "ENCUADERNACIÓN":
                        c1, c2 = st.columns(2)
                        datos_finales = {
                            "material": c1.text_input("Material"), "medida": c2.text_input("Medida"),
                            "cant_final": c1.number_input("Cant. Final", 0), "presentacion": c2.text_input("Presentación")
                        }

                    dk = st.number_input("Desperdicio Kg", 0.0)
                    obs = st.text_area("Notas")
                    
                    if st.form_submit_button("GUARDAR HISTORIAL"):
                        # Insertar en tabla del área
                        tabla_hist = area_op.lower()
                        datos_finales.update({
                            "op": act['op'], "maquina": m, "trabajo": act['trabajo'],
                            "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M"),
                            "desp_kg": dk, "obs": obs
                        })
                        supabase.table(tabla_hist).insert(datos_finales).execute()
                        # Borrar de activos
                        supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                        st.rerun()

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()
