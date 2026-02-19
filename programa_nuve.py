import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Sistema Planta Cloud", page_icon="🏭")

# --- 2. INICIALIZACIÓN DE DATOS (ESTADO DE SESIÓN) ---
# Esto reemplaza al archivo Excel local. Los datos viven en la nube mientras la app esté activa.
tablas_nombres = [
    "Impresion", "Corte", "Colectoras", "Encuadernacion", 
    "Pendientes_Imp", "Pendientes_Corte", "Pendientes_Col", "Pendientes_Enc",
    "Paradas_Emergencia", "Seguimiento_Cortadoras"
]

for tabla in tablas_nombres:
    if tabla not in st.session_state:
        st.session_state[tabla] = pd.DataFrame()

# --- 3. CONFIGURACIÓN ESTATICA (TU ORIGINAL) ---
MAQUINAS_IMP = ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"]
MAQUINAS_CORTE = ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"]
MAQUINAS_COL = ["COL-01", "COL-02"]
MARCAS_PAPEL = ["HANSOL", "KOEHLER", "APP", "OTRO", "IMPRESO", "BOND", "KRAFT", "PROPALCOTE", "PLASTIFICADO"]

USUARIOS = {
    "alexander": {"pass": "admin123", "rol": "admin", "vistas": ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación", "⏱️ Seguimiento Cortadoras"]},
    "giovanny": {"pass": "1503", "rol": "supervisor", "vistas": ["🖨️ Impresión", "📥 Colectoras"]},
    "leonel": {"pass": "0321", "rol": "supervisor", "vistas": ["✂️ Corte", "⏱️ Seguimiento Cortadoras"]},
    "gerardo": {"pass": "1234", "rol": "supervisor", "vistas": ["✂️ Corte", "⏱️ Seguimiento Cortadoras"]},
    "jinna": {"pass": "1234", "rol": "supervisor", "vistas": ["📕 Encuadernación","🖨️ Impresión"]}
}

# --- 4. FUNCIONES DE GESTIÓN ---
def guardar_en_memoria(df_nuevo, nombre_tabla):
    st.session_state[nombre_tabla] = pd.concat([st.session_state[nombre_tabla], df_nuevo], ignore_index=True)

def eliminar_de_memoria(nombre_tabla, columna, valor):
    df = st.session_state[nombre_tabla]
    st.session_state[nombre_tabla] = df[df[columna] != valor]

def generar_excel_descarga():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for tabla in tablas_nombres:
            st.session_state[tabla].to_excel(writer, sheet_name=tabla, index=False)
    return output.getvalue()

# --- 5. INTERFAZ DE LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🏭 ACCESO SISTEMA PLANTA")
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("ENTRAR"):
            if u in USUARIOS and USUARIOS[u]["pass"] == p:
                st.session_state.autenticado = True
                st.session_state.usuario = u
                st.session_state.rol = USUARIOS[u]["rol"]
                st.session_state.vistas = USUARIOS[u]["vistas"]
                st.rerun()
            else: st.error("Clave incorrecta")
    st.stop()

# --- 6. SIDEBAR Y DESCARGA ---
st.sidebar.title(f"👤 {st.session_state.usuario}")
if st.session_state.rol == "admin":
    st.sidebar.divider()
    st.sidebar.subheader("Descargar Reporte")
    excel_btn = generar_excel_descarga()
    st.sidebar.download_button(
        label="📥 BAJAR EXCEL DEL DÍA",
        data=excel_btn,
        file_name=f"Reporte_Planta_{datetime.now().strftime('%d-%m-%Y')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

menu = st.sidebar.radio("Módulos", st.session_state.vistas)

# --- 7. RENDERIZADO DE MÁQUINAS ---
def mostrar_botones(lista, tabla_p, prefix):
    st.subheader("Seleccione Máquina")
    df_p = st.session_state[tabla_p]
    df_paradas = st.session_state["Paradas_Emergencia"]
    cols = st.columns(4)
    for i, m in enumerate(lista):
        parada = not df_paradas.empty and m in df_paradas[df_paradas["Estado"]=="Activa"]["Máquina"].values
        ocupada = not df_p.empty and m in df_p["Máquina"].values
        icon = "⚠️" if parada else ("🔴" if ocupada else "⚪")
        if cols[i % 4].button(f"{icon} {m}", key=f"{prefix}_{m}", use_container_width=True):
            st.session_state[f"sel_{prefix}"] = m

# --- 8. MÓDULOS (EJEMPLO IMPRESIÓN - REPETIR PARA OTROS) ---
if menu == "🖨️ Impresión":
    mostrar_botones(MAQUINAS_IMP, "Pendientes_Imp", "imp")
    maq = st.session_state.get("sel_imp")
    if maq:
        st.divider()
        st.header(f"Máquina: {maq}")
        df_p = st.session_state["Pendientes_Imp"]
        actual = df_p[df_p["Máquina"] == maq]
        
        c1, c2 = st.columns(2)
        with c1:
            if actual.empty:
                with st.form("f_ini"):
                    st.write("🟢 Iniciar")
                    op = st.text_input("OP")
                    if st.form_submit_button("REGISTRAR INICIO"):
                        guardar_en_memoria(pd.DataFrame([{"OP":op, "Máquina":maq, "Fecha":datetime.now().strftime("%Y-%m-%d")}]), "Pendientes_Imp")
                        st.rerun()
            else:
                st.info(f"En curso: OP {actual.iloc[0]['OP']}")
        with c2:
            if not actual.empty:
                with st.form("f_fin"):
                    st.write("🏁 Finalizar")
                    metros = st.number_input("Metros", 0)
                    if st.form_submit_button("GUARDAR"):
                        guardar_en_memoria(pd.DataFrame([{"OP":actual.iloc[0]['OP'], "Máquina":maq, "Metros":metros}]), "Impresion")
                        eliminar_de_memoria("Pendientes_Imp", "Máquina", maq)
                        st.rerun()