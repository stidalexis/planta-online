import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# --- CONEXIÓN A NUBE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="SISTEMA PLANTA TIEMPO REAL", page_icon="🏭")

# --- FUNCIONES NÚCLEO ---
def db_insert(tabla, datos):
    try:
        supabase.table(tabla).insert(datos).execute()
        return True
    except Exception as e:
        st.error(f"Error DB: {e}")
        return False

def db_get_activos():
    res = supabase.table("trabajos_activos").select("*").execute()
    return res.data

# --- LOGIN Y ROLES ---
if "auth" not in st.session_state:
    st.session_state.update({"auth": False, "rol": None})

if not st.session_state.auth:
    st.title("🏭 CONTROL DE PRODUCCIÓN - ACCESO")
    usuarios = {
        "administrador": "admin2026",
        "impresion": "imp2026",
        "colectoras": "col2026",
        "corte1": "c1p",
        "corte2": "c2p",
        "encuadernacion": "enc2026"
    }
    u = st.text_input("Usuario").lower().strip()
    p = st.text_input("Contraseña", type="password")
    if st.button("ENTRAR AL SISTEMA", use_container_width=True):
        if u in usuarios and usuarios[u] == p:
            st.session_state.auth, st.session_state.rol = True, u
            st.rerun()
        else:
            st.error("Credenciales Incorrectas")
    st.stop()

rol = st.session_state.rol

# --- CONFIGURACIÓN TÉCNICA ---
MAQ_DATOS = {
    "impresion": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "corte1": ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07"],
    "corte2": ["COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"],
    "colectoras": ["COL-01", "COL-02"],
    "encuadernacion": ["LINEA-01"]
}

# --- NAVEGACIÓN ---
st.sidebar.title(f"Usuario: {rol.upper()}")
if rol == "administrador":
    menu = st.sidebar.radio("IR A:", ["PRODUCCIÓN VIVO", "REPORTES GENERALES"])
else:
    menu = "PRODUCCIÓN VIVO"

if st.sidebar.button("Log Out"):
    st.session_state.auth = False
    st.rerun()

# --- PANEL DE PRODUCCIÓN EN VIVO ---
if menu == "PRODUCCIÓN VIVO":
    st.header(f"Gestión de Piso - {rol.upper()}")
    
    # Obtener máquinas del área del usuario
    maquinas_area = MAQ_DATOS.get(rol, [m for a in MAQ_DATOS.values() for m in a])
    activos = db_get_activos()
    maquinas_en_uso = [a['maquina'] for a in activos]

    col_ini, col_viv = st.columns([1, 2])

    with col_ini:
        st.subheader("▶️ Iniciar Trabajo")
        m_sel = st.selectbox("Máquina", maquinas_area)
        op_sel = st.text_input("Orden de Producción (OP)")
        tr_sel = st.text_input("Nombre del Trabajo")
        
        if st.button("ABRIR TURNO", use_container_width=True):
            if m_sel in maquinas_en_uso:
                st.error("⚠️ Esta máquina ya tiene un trabajo activo.")
            elif op_sel and tr_sel:
                datos_ini = {"maquina": m_sel, "op": op_sel, "trabajo": tr_sel, "area": rol, "usuario": rol}
                if db_insert("trabajos_activos", datos_ini):
                    st.success(f"Trabajo iniciado en {m_sel}")
                    st.rerun()
            else:
                st.warning("Complete OP y Trabajo.")

    with col_viv:
        st.subheader("🕒 Trabajos Activos")
        if not activos:
            st.info("No hay máquinas operando en este momento.")
        
        for act in activos:
            # Filtrar para que operarios solo vean sus máquinas, admin ve todo
            if rol == "administrador" or act['area'] == rol or (rol[:5] == "corte" and act['area'][:5] == "corte"):
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    c1.markdown(f"**MAQ: {act['maquina']}** | OP: {act['op']}\n\n*{act['trabajo']}*")
                    c2.caption(f"Inició: {act['hora_inicio'][11:16]}")
                    
                    # --- BOTÓN PARADA ---
                    if c2.button("⚠️ PARADA", key=f"p_{act['id']}"):
                        st.session_state[f"st_{act['id']}"] = True

                    if st.session_state.get(f"st_{act['id']}"):
                        with st.form(f"f_p_{act['id']}"):
                            motivo = st.selectbox("Motivo", ["Mantenimiento", "Falla Mecánica", "Ajuste/Set-up", "Falta de Material", "Limpieza", "Almuerzo"])
                            if st.form_submit_button("Registrar Parada"):
                                db_insert("paradas_maquina", {"maquina": act['maquina'], "op": act['op'], "motivo": motivo, "usuario": rol})
                                st.toast("Parada registrada")
                                del st.session_state[f"st_{act['id']}"]

                    # --- BOTÓN FINALIZAR (CHECK-OUT) ---
                    if c3.button("🏁 FINALIZAR", key=f"f_{act['id']}", type="primary"):
                        st.session_state[f"fin_{act['id']}"] = True

                    if st.session_state.get(f"fin_{act['id']}"):
                        st.divider()
                        with st.form(f"final_{act['id']}"):
                            st.write("### Datos Técnicos de Cierre")
                            
                            # Cuestionario según área
                            area_act = act['area']
                            res_tecnico = {}
                            
                            if "impresion" in area_act:
                                col_a, col_b = st.columns(2)
                                res_tecnico = {
                                    "papel": col_a.text_input("Marca Papel"), "ancho": col_b.text_input("Ancho Bobina"),
                                    "gramaje": col_a.text_input("Gramaje"), "tintas": col_b.number_input("Tintas", 0),
                                    "medida": col_a.text_input("Medida"), "imagenes": col_b.number_input("Imágenes x Vuelta", 0),
                                    "metros": st.number_input("Metros Finales", 0)
                                }
                            elif "corte" in area_act:
                                col_a, col_b = st.columns(2)
                                res_tecnico = {
                                    "img_varilla": col_a.number_input("Img x Varilla", 0), "medida": col_b.text_input("Medida Final"),
                                    "total_varillas": col_a.number_input("Total Varillas", 0), "rollos_cortados": col_b.number_input("Rollos Cortados", 0),
                                    "unid_caja": st.number_input("Unid/Caja", 0)
                                }
                            elif "colectoras" in area_act:
                                col_a, col_b = st.columns(2)
                                res_tecnico = {
                                    "papel": col_a.text_input("Papel"), "medida_forma": col_b.text_input("Medida Forma"),
                                    "unid_caja": col_a.number_input("Unid/Caja", 0), "total_cajas": col_b.number_input("Total Cajas", 0),
                                    "total_formas": st.number_input("Total Formas", 0)
                                }
                            elif "encuadernacion" in area_act:
                                col_a, col_b = st.columns(2)
                                res_tecnico = {
                                    "cant_formas": col_a.number_input("Cant. Formas", 0), "material": col_b.text_input("Tipo Material"),
                                    "medida": col_a.text_input("Medida"), "unid_caja": col_b.number_input("Unid/Caja", 0),
                                    "cant_final": st.number_input("Cantidad Final", 0), "presentacion": st.text_input("Presentación")
                                }

                            # Campos comunes a todos
                            st.divider()
                            dk = st.number_input("Desperdicio Total (Kg)", 0.0)
                            md = st.text_input("Motivo Desperdicio")
                            ob = st.text_area("Observaciones Finales")

                            if st.form_submit_button("GUARDAR HISTORIAL Y CERRAR OP"):
                                # 1. Construir registro final
                                registro = {
                                    "op": act['op'], "maquina": act['maquina'], "trabajo": act['trabajo'],
                                    "h_inicio": act['hora_inicio'], "h_fin": datetime.now().strftime("%H:%M:%S"),
                                    "desp_kg": dk, "motivo_desp": md, "obs": ob, **res_tecnico
                                }
                                # 2. Insertar en tabla histórica (impresion, corte, etc)
                                tabla_h = "corte" if "corte" in area_act else area_act
                                db_insert(tabla_h, registro)
                                # 3. Borrar de activos
                                supabase.table("trabajos_activos").delete().eq("id", act['id']).execute()
                                del st.session_state[f"fin_{act['id']}"]
                                st.rerun()

# --- REPORTES ADMINISTRATIVOS ---
elif menu == "REPORTES GENERALES":
    st.header("Consolidado de Planta")
    tab_rep = st.selectbox("Seleccione Tabla para Exportar:", ["impresion", "corte", "colectoras", "encuadernacion", "paradas_maquina"])
    
    res = supabase.table(tab_rep).select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 DESCARGAR EXCEL (CSV)", data=csv, file_name=f"reporte_{tab_rep}.csv", mime='text/csv')
    else:
        st.warning("No hay datos en esta categoría.")
