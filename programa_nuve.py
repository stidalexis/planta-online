import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Sistema Planta Cloud", page_icon="🏭")

# --- 2. INICIALIZACIÓN DE TABLAS CON COLUMNAS (PARA EVITAR KEYERROR) ---
columnas_tablas = {
    "Impresion": ["OP", "Fecha_Fin", "Máquina", "Nombre_Trabajo", "Total_Metros"],
    "Corte": ["OP", "Fecha_Fin", "Máquina", "Total_Varillas"],
    "Colectoras": ["OP", "Fecha_Fin", "Máquina", "Total_Cajas"],
    "Encuadernacion": ["OP", "Fecha_Fin", "Nombre_Trabajo", "Cant_Final"],
    "Pendientes_Imp": ["OP", "Máquina", "Hora_I", "Fecha_I", "Nombre_Trabajo"],
    "Pendientes_Corte": ["OP", "Máquina", "Hora_I", "Nombre_Trabajo"],
    "Pendientes_Col": ["OP", "Máquina", "Hora_I", "Nombre_Trabajo"],
    "Pendientes_Enc": ["OP", "Hora_I", "Nombre_Trabajo"],
    "Paradas_Emergencia": ["Máquina", "Estado", "Fecha", "Hora_Inicio"],
    "Seguimiento_Cortadoras": ["Fecha", "Máquina", "OP", "Num_Cajas"]
}

for nombre, cols in columnas_tablas.items():
    if nombre not in st.session_state:
        st.session_state[nombre] = pd.DataFrame(columns=cols)

# --- 3. CONFIGURACIÓN ESTATICA ---
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
    st.session_state[nombre_tabla] = df[df[columna].astype(str) != str(valor)]

def generar_excel_descarga():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for tabla in columnas_tablas.keys():
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
            else: st.error("Credenciales incorrectas")
    st.stop()

# --- 6. SIDEBAR ---
st.sidebar.title(f"👤 {st.session_state.usuario}")
if st.session_state.rol == "admin":
    st.sidebar.divider()
    excel_btn = generar_excel_descarga()
    st.sidebar.download_button(label="📥 DESCARGAR EXCEL DEL DÍA", data=excel_btn, file_name=f"Reporte_{datetime.now().strftime('%d-%m-%Y')}.xlsx")

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

menu = st.sidebar.radio("Módulos", st.session_state.vistas)

# --- 7. MODULOS DE PRODUCCION ---

# --- IMPRESIÓN ---
if menu == "🖨️ Impresión":
    st.header("🖨️ Módulo de Impresión")
    cols_btn = st.columns(4)
    for i, m in enumerate(MAQUINAS_IMP):
        if cols_btn[i % 4].button(m, key=f"imp_{m}", use_container_width=True):
            st.session_state.sel_imp = m
    
    maq = st.session_state.get("sel_imp")
    if maq:
        st.divider()
        df_p = st.session_state["Pendientes_Imp"]
        actual = df_p[df_p["Máquina"] == maq]
        
        c1, c2 = st.columns(2)
        with c1:
            if actual.empty:
                with st.form("f_imp_ini"):
                    st.subheader(f"🟢 Iniciar en {maq}")
                    op = st.text_input("OP")
                    tr = st.text_input("Nombre Trabajo")
                    if st.form_submit_button("REGISTRAR INICIO"):
                        guardar_en_memoria(pd.DataFrame([{"OP":op, "Máquina":maq, "Hora_I":datetime.now().strftime("%H:%M"), "Nombre_Trabajo":tr}]), "Pendientes_Imp")
                        st.rerun()
            else:
                st.success(f"Trabajando OP: {actual.iloc[0]['OP']}")
        with c2:
            if not actual.empty:
                with st.form("f_imp_fin"):
                    st.subheader("🏁 Finalizar")
                    metros = st.number_input("Metros", 0)
                    if st.form_submit_button("FINALIZAR TRABAJO"):
                        guardar_en_memoria(pd.DataFrame([{"OP":actual.iloc[0]['OP'], "Máquina":maq, "Total_Metros":metros, "Fecha_Fin":datetime.now().strftime("%Y-%m-%d")}]), "Impresion")
                        eliminar_de_memoria("Pendientes_Imp", "Máquina", maq)
                        st.rerun()

# --- CORTE ---
elif menu == "✂️ Corte":
    st.header("✂️ Módulo de Corte")
    cols_btn = st.columns(4)
    for i, m in enumerate(MAQUINAS_CORTE):
        if cols_btn[i % 4].button(m, key=f"cor_{m}", use_container_width=True):
            st.session_state.sel_cor = m
    
    maq = st.session_state.get("sel_cor")
    if maq:
        st.divider()
        df_p = st.session_state["Pendientes_Corte"]
        actual = df_p[df_p["Máquina"] == maq]
        c1, c2 = st.columns(2)
        with c1:
            if actual.empty:
                with st.form("f_cor_ini"):
                    st.subheader(f"🟢 Iniciar en {maq}")
                    op = st.text_input("OP")
                    if st.form_submit_button("INICIAR CORTE"):
                        guardar_en_memoria(pd.DataFrame([{"OP":op, "Máquina":maq, "Hora_I":datetime.now().strftime("%H:%M")}]), "Pendientes_Corte")
                        st.rerun()
            else: st.success(f"En corte OP: {actual.iloc[0]['OP']}")
        with c2:
            if not actual.empty:
                with st.form("f_cor_fin"):
                    var = st.number_input("Varillas", 0)
                    if st.form_submit_button("FINALIZAR"):
                        guardar_en_memoria(pd.DataFrame([{"OP":actual.iloc[0]['OP'], "Máquina":maq, "Total_Varillas":var, "Fecha_Fin":datetime.now().strftime("%Y-%m-%d")}]), "Corte")
                        eliminar_de_memoria("Pendientes_Corte", "Máquina", maq)
                        st.rerun()

# --- ENCUADERNACIÓN (AHORA COMPLETO) ---
elif menu == "📕 Encuadernación":
    st.header("📕 Módulo de Encuadernación")
    df_p = st.session_state["Pendientes_Enc"]
    
    c1, c2 = st.columns(2)
    with c1:
        with st.form("f_enc_ini", clear_on_submit=True):
            st.subheader("🟢 Iniciar Nuevo Trabajo")
            op = st.text_input("OP")
            tr = st.text_input("Nombre del Trabajo")
            ma = st.text_input("Tipo Material")
            if st.form_submit_button("REGISTRAR INICIO"):
                d = {"OP": op, "Nombre_Trabajo": tr, "Tipo_Material": ma, "Hora_I": datetime.now().strftime("%H:%M")}
                guardar_en_memoria(pd.DataFrame([d]), "Pendientes_Enc")
                st.rerun()

    with c2:
        st.subheader("🏁 Trabajos en Curso")
        if not df_p.empty:
            for i, row in df_p.iterrows():
                with st.expander(f"OP: {row['OP']} - {row['Nombre_Trabajo']}"):
                    with st.form(f"fin_enc_{i}"):
                        cant = st.number_input("Cantidad Final", 0)
                        if st.form_submit_button(f"Finalizar {row['OP']}"):
                            d_fin = {"OP": row['OP'], "Nombre_Trabajo": row['Nombre_Trabajo'], "Cant_Final": cant, "Fecha_Fin": datetime.now().strftime("%Y-%m-%d")}
                            guardar_en_memoria(pd.DataFrame([d_fin]), "Encuadernacion")
                            eliminar_de_memoria("Pendientes_Enc", "OP", row['OP'])
                            st.rerun()
        else:
            st.write("No hay trabajos pendientes.")

# --- SEGUIMIENTO CORTADORAS ---
elif menu == "⏱️ Seguimiento Cortadoras":
    st.header("⏱️ Seguimiento Diario")
    with st.form("f_seg"):
        m = st.selectbox("Máquina", MAQUINAS_CORTE)
        op = st.text_input("OP")
        cj = st.number_input("Cajas", 0)
        if st.form_submit_button("GUARDAR AVANCE"):
            guardar_en_memoria(pd.DataFrame([{"Fecha":datetime.now().strftime("%Y-%m-%d"), "Máquina":m, "OP":op, "Num_Cajas":cj}]), "Seguimiento_Cortadoras")
            st.success("Guardado")
