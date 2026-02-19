import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Sistema Planta Cloud", page_icon="🏭")

# --- 2. INICIALIZACIÓN DE TABLAS EN MEMORIA ---
tablas_nombres = [
    "Impresion", "Corte", "Colectoras", "Encuadernacion", 
    "Pendientes_Imp", "Pendientes_Corte", "Pendientes_Col", "Pendientes_Enc",
    "Paradas_Emergencia", "Seguimiento_Cortadoras"
]

for tabla in tablas_nombres:
    if tabla not in st.session_state:
        st.session_state[tabla] = pd.DataFrame()

# --- 3. CONFIGURACIÓN ESTATICA ORIGINAL ---
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

# --- 7. LÓGICA DE MÁQUINAS ---
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

# --- 8. MÓDULOS COMPLETOS ---

# IMPRESIÓN
if menu == "🖨️ Impresión":
    mostrar_botones(MAQUINAS_IMP, "Pendientes_Imp", "imp")
    maq = st.session_state.get("sel_imp")
    if maq:
        st.divider()
        st.header(f"Máquina: {maq}")
        df_p = st.session_state["Pendientes_Imp"]
        actual = df_p[df_p["Máquina"] == maq]
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if actual.empty:
                with st.form("f_imp_ini", clear_on_submit=True):
                    st.write("🟢 Iniciar Trabajo")
                    op = st.text_input("OP")
                    tr = st.text_input("Nombre Trabajo")
                    pa = st.selectbox("Marca Papel", MARCAS_PAPEL)
                    an = st.text_input("Ancho Bobina")
                    gr = st.text_input("Gramaje")
                    ti = st.number_input("Cant. Tintas", 0)
                    me = st.text_input("Medida Rollo")
                    im = st.number_input("Cant. Imágenes", 0)
                    if st.form_submit_button("REGISTRAR INICIO"):
                        d = {"OP":str(op), "Máquina":maq, "Hora_I":datetime.now().strftime("%H:%M:%S"), "Fecha_I":datetime.now().strftime("%Y-%m-%d"), "Nombre_Trabajo":tr, "Marca_Papel":pa, "Ancho_Bobina":an, "Gramaje":gr, "Cant_Tintas":ti, "Medida_Rollo":me, "Cant_Imagenes":im}
                        guardar_en_memoria(pd.DataFrame([d]), "Pendientes_Imp"); st.rerun()
            else: st.info(f"En curso: OP {actual.iloc[0]['OP']}")

        with c2:
            if not actual.empty:
                with st.form("f_imp_fin"):
                    st.write("🏁 Finalizar Trabajo")
                    m = st.number_input("Metros Totales", 0)
                    r = st.number_input("Rollos a Sacar", 0)
                    pt = st.number_input("Peso Tinta", 0.0)
                    pd_ = st.number_input("Peso Desperdicio", 0.0)
                    mo = st.text_input("Motivo Desperdicio")
                    ob = st.text_area("Observaciones")
                    if st.form_submit_button("FINALIZAR"):
                        row = actual.iloc[0]
                        d = {"OP":row['OP'], "Fecha_Fin":datetime.now().strftime("%Y-%m-%d"), "Máquina":maq, "Nombre_Trabajo":row['Nombre_Trabajo'], "Marca_Papel":row['Marca_Papel'], "Hora_Inicio_T":row['Hora_I'], "Hora_Final_T":datetime.now().strftime("%H:%M:%S"), "Total_Metros":m, "Rollos_Sacar":r, "Peso_Tinta":pt, "Peso_Desperdicio":pd_, "Motivo_Desperdicio":mo, "Observaciones":ob}
                        guardar_en_memoria(pd.DataFrame([d]), "Impresion")
                        eliminar_de_memoria("Pendientes_Imp", "Máquina", maq); st.rerun()
        with c3:
            if st.button("🚨 PARADA/REANUDAR"):
                # Lógica simplificada de parada
                st.session_state["Paradas_Emergencia"] = pd.concat([st.session_state["Paradas_Emergencia"], pd.DataFrame([{"Máquina":maq, "Estado":"Activa"}])])
                st.rerun()

# CORTE
elif menu == "✂️ Corte":
    mostrar_botones(MAQUINAS_CORTE, "Pendientes_Corte", "cor")
    maq = st.session_state.get("sel_cor")
    if maq:
        st.divider(); st.header(f"Máquina: {maq}")
        df_p = st.session_state["Pendientes_Corte"]
        actual = df_p[df_p["Máquina"] == maq]
        c1, c2 = st.columns(2)
        with c1:
            if actual.empty:
                with st.form("f_cor_ini"):
                    op = st.text_input("OP")
                    tr = st.text_input("Trabajo")
                    pa = st.selectbox("Papel", MARCAS_PAPEL)
                    iv = st.number_input("Imágenes por Varilla", 0)
                    if st.form_submit_button("INICIAR CORTE"):
                        d = {"OP":str(op), "Máquina":maq, "Hora_I":datetime.now().strftime("%H:%M:%S"), "Nombre_Trabajo":tr, "Marca_Papel":pa, "Imagenes_Varilla":iv}
                        guardar_en_memoria(pd.DataFrame([d]), "Pendientes_Corte"); st.rerun()
        with c2:
            if not actual.empty:
                with st.form("f_cor_fin"):
                    tv = st.number_input("Total Varillas", 0)
                    uc = st.number_input("Unid. por Caja", 0)
                    pd_ = st.number_input("Peso Desperdicio", 0.0)
                    if st.form_submit_button("FINALIZAR CORTE"):
                        row = actual.iloc[0]
                        d = {"OP":row['OP'], "Máquina":maq, "Total_Varillas":tv, "Unidades_Por_Caja":uc, "Peso_Desperdicio":pd_, "Fecha_Fin":datetime.now().strftime("%Y-%m-%d")}
                        guardar_en_memoria(pd.DataFrame([d]), "Corte")
                        eliminar_de_memoria("Pendientes_Corte", "Máquina", maq); st.rerun()

# COLECTORAS
elif menu == "📥 Colectoras":
    mostrar_botones(MAQUINAS_COL, "Pendientes_Col", "col")
    maq = st.session_state.get("sel_col")
    if maq:
        st.divider(); st.header(f"Máquina: {maq}")
        df_p = st.session_state["Pendientes_Col"]
        actual = df_p[df_p["Máquina"] == maq]
        c1, c2 = st.columns(2)
        with c1:
            if actual.empty:
                with st.form("f_col_ini"):
                    op = st.text_input("OP"); tr = st.text_input("Trabajo")
                    if st.form_submit_button("INICIAR COLECTORA"):
                        guardar_en_memoria(pd.DataFrame([{"OP":op, "Máquina":maq, "Hora_I":datetime.now().strftime("%H:%M:%S"), "Nombre_Trabajo":tr}]), "Pendientes_Col"); st.rerun()
        with c2:
            if not actual.empty:
                with st.form("f_col_fin"):
                    tc = st.number_input("Total Cajas", 0)
                    if st.form_submit_button("FINALIZAR"):
                        guardar_en_memoria(pd.DataFrame([{"OP":actual.iloc[0]['OP'], "Máquina":maq, "Total_Cajas":tc, "Fecha_Fin":datetime.now().strftime("%Y-%m-%d")}]), "Colectoras")
                        eliminar_de_memoria("Pendientes_Col", "Máquina", maq); st.rerun()

# SEGUIMIENTO CORTADORAS (SISTEMA DE AVANCES)
elif menu == "⏱️ Seguimiento Cortadoras":
    st.header("Seguimiento de Cortadoras (Turnos)")
    mostrar_botones(MAQUINAS_CORTE, "Pendientes_Corte", "seg")
    maq = st.session_state.get("sel_seg")
    if maq:
        with st.form("f_seg"):
            tu = st.selectbox("Turno", ["1", "2", "3"])
            op = st.text_input("OP")
            mr = st.number_input("Metros Rollo", 0.0)
            nc = st.number_input("Número Cajas", 0)
            if st.form_submit_button("GUARDAR AVANCE"):
                d = {"Fecha":datetime.now().strftime("%Y-%m-%d"), "Turno":tu, "Máquina":maq, "OP":op, "Num_Cajas":nc, "Metros_Rollo":mr}
                guardar_en_memoria(pd.DataFrame([d]), "Seguimiento_Cortadoras"); st.success("Avance Guardado")
