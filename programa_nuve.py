import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Sistema Planta Total Cloud", page_icon="🏭")

# --- 2. INICIALIZACIÓN DE TODAS LAS TABLAS (ESTRUCTURA COMPLETA) ---
columnas_tablas = {
    "Impresion": ["OP", "Fecha_Fin", "Máquina", "Nombre_Trabajo", "Marca_Papel", "Hora_Inicio_T", "Hora_Final_T", "Total_Metros", "Rollos_Sacar", "Peso_Tinta", "Peso_Desperdicio", "Motivo_Desperdicio", "Observaciones"],
    "Corte": ["OP", "Fecha_Fin", "Máquina", "Nombre_Trabajo", "Marca_Papel", "Total_Varillas", "Unidades_Por_Caja", "Total_Rollos_Cortados", "Peso_Desperdicio", "Motivo_Desperdicio", "Observaciones", "Hora_Inicio_T", "Hora_Final_T"],
    "Colectoras": ["OP", "Fecha_Fin", "Máquina", "Nombre_Trabajo", "Marca_Papel", "Hora_Inicio_T", "Hora_Final_T", "Total_Cajas", "Total_Formas", "Peso_Desperdicio", "Motivo_Desperdicio", "Observaciones"],
    "Encuadernacion": ["OP", "Fecha_Fin", "Nombre_Trabajo", "Cant_Formas", "Tipo_Material", "Medida_Forma", "Hora_Inicio_T", "Hora_Final_T", "Unid_Caja", "Cant_Final", "Tipo_Presentacion", "Peso_Desperdicio", "Motivo_Desperdicio", "Observaciones"],
    "Pendientes_Imp": ["OP", "Máquina", "Hora_I", "Fecha_I", "Nombre_Trabajo", "Marca_Papel", "Ancho_Bobina", "Gramaje", "Cant_Tintas", "Medida_Rollo", "Cant_Imagenes"],
    "Pendientes_Corte": ["OP", "Máquina", "Hora_I", "Fecha_I", "Nombre_Trabajo", "Marca_Papel", "Ancho_Bobina", "Gramaje", "Imagenes_Varilla", "Medida_Rollo"],
    "Pendientes_Col": ["OP", "Máquina", "Hora_I", "Fecha_I", "Nombre_Trabajo", "Marca_Papel", "Medida_Forma", "Unidades_Caja"],
    "Pendientes_Enc": ["OP", "Hora_I", "Fecha_I", "Nombre_Trabajo", "Cant_Formas", "Tipo_Material", "Medida_Forma"],
    "Paradas_Emergencia": ["Máquina", "Estado", "Fecha", "Hora_Inicio", "Hora_Fin", "Motivo"],
    "Seguimiento_Cortadoras": ["Fecha", "Hora_Registro", "Turno", "Máquina", "OP", "Nombre_Trabajo", "Tipo_Papel", "Metros_Rollo", "Unidades_Por_Caja", "Num_Cajas", "Observaciones"]
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
    "alexander": {"pass": "admin123", "rol": "admin", "vistas": ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación", "⏱️ Seguimiento Cortadoras", "📊 Historial en Línea"]},
    "giovanny": {"pass": "1503", "rol": "supervisor", "vistas": ["🖨️ Impresión", "📥 Colectoras", "📊 Historial en Línea"]},
    "leonel": {"pass": "0321", "rol": "supervisor", "vistas": ["✂️ Corte", "⏱️ Seguimiento Cortadoras", "📊 Historial en Línea"]},
    "gerardo": {"pass": "1234", "rol": "supervisor", "vistas": ["✂️ Corte", "⏱️ Seguimiento Cortadoras", "📊 Historial en Línea"]},
    "jinna": {"pass": "1234", "rol": "supervisor", "vistas": ["📕 Encuadernación","🖨️ Impresión", "📊 Historial en Línea"]}
}

# --- 4. FUNCIONES DE APOYO ---
def guardar_dato(df_nuevo, tabla):
    st.session_state[tabla] = pd.concat([st.session_state[tabla], df_nuevo], ignore_index=True)

def eliminar_pendiente(tabla, col, val):
    df = st.session_state[tabla]
    st.session_state[tabla] = df[df[col].astype(str) != str(val)]

def descargar_excel():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for t in columnas_tablas.keys():
            st.session_state[t].to_excel(writer, sheet_name=t, index=False)
    return output.getvalue()

def seccion_parada(maq):
    st.subheader("⚠️ Estado de Máquina")
    df_paradas = st.session_state["Paradas_Emergencia"]
    parada_activa = not df_paradas.empty and ((df_paradas["Máquina"] == maq) & (df_paradas["Estado"] == "Activa")).any()
    if parada_activa:
        st.error(f"🚨 LA MÁQUINA {maq} ESTÁ PARADA")
        if st.button(f"✅ REANUDAR TRABAJO EN {maq}", use_container_width=True):
            idx = df_paradas[(df_paradas["Máquina"] == maq) & (df_paradas["Estado"] == "Activa")].index[-1]
            st.session_state["Paradas_Emergencia"].at[idx, "Estado"] = "Finalizada"
            st.session_state["Paradas_Emergencia"].at[idx, "Hora_Fin"] = datetime.now().strftime("%H:%M")
            st.rerun()
    else:
        with st.expander("🚨 REGISTRAR PARADA DE EMERGENCIA / FALLA"):
            with st.form(f"form_parada_{maq}"):
                motivo = st.selectbox("Motivo", ["Mantenimiento", "Falla Eléctrica", "Falta Material", "Ajuste Técnico", "Cambio Repuesto", "Otro"])
                if st.form_submit_button("CONFIRMAR PARADA"):
                    d = {"Máquina": maq, "Estado": "Activa", "Fecha": datetime.now().strftime("%Y-%m-%d"), "Hora_Inicio": datetime.now().strftime("%H:%M"), "Hora_Fin": "", "Motivo": motivo}
                    guardar_dato(pd.DataFrame([d]), "Paradas_Emergencia"); st.rerun()

# --- 5. LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🏭 SISTEMA DE CONTROL PLANTA")
    u = st.text_input("Usuario")
    p = st.text_input("Password", type="password")
    if st.button("ENTRAR"):
        if u in USUARIOS and USUARIOS[u]["pass"] == p:
            st.session_state.update({"autenticado":True, "usuario":u, "rol":USUARIOS[u]["rol"], "vistas":USUARIOS[u]["vistas"]})
            st.rerun()
    st.stop()

# --- 6. SIDEBAR ---
st.sidebar.title(f"👤 {st.session_state.usuario.upper()}")
if st.session_state.rol == "admin":
    st.sidebar.download_button("📥 DESCARGAR EXCEL DEL DÍA", descargar_excel(), f"Reporte_{datetime.now().strftime('%d-%m-%Y')}.xlsx", use_container_width=True)
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

menu = st.sidebar.radio("MENÚ DE SECCIONES", st.session_state.vistas)

# --- 7. MÓDULO IMPRESIÓN ---
if menu == "🖨️ Impresión":
    st.header("🖨️ Módulo de Impresión")
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS_IMP):
        if cols[i%4].button(m, key=f"i_{m}", use_container_width=True): st.session_state.sel_i = m
    maq = st.session_state.get("sel_i")
    if maq:
        st.divider()
        seccion_parada(maq)
        st.divider()
        df_p = st.session_state["Pendientes_Imp"]
        actual = df_p[df_p["Máquina"] == maq]
        c1, c2 = st.columns(2)
        with c1:
            if actual.empty:
                with st.form("f_i_i"):
                    st.subheader(f"🟢 Iniciar OP en {maq}")
                    op, tr = st.text_input("Orden de Producción (OP)"), st.text_input("Nombre del Trabajo")
                    pa = st.selectbox("Marca de Papel", MARCAS_PAPEL)
                    ab, gr = st.text_input("Ancho Bobina"), st.text_input("Gramaje")
                    ct, mr = st.number_input("Cantidad de Tintas", 0), st.text_input("Medida Rollo")
                    ci = st.number_input("Cant. Imágenes", 0)
                    if st.form_submit_button("REGISTRAR INICIO"):
                        guardar_dato(pd.DataFrame([{"OP":op, "Máquina":maq, "Hora_I":datetime.now().strftime("%H:%M"), "Fecha_I":datetime.now().strftime("%Y-%m-%d"), "Nombre_Trabajo":tr, "Marca_Papel":pa, "Ancho_Bobina":ab, "Gramaje":gr, "Cant_Tintas":ct, "Medida_Rollo":mr, "Cant_Imagenes":ci}]), "Pendientes_Imp"); st.rerun()
            else: st.info(f"TRABAJANDO: OP {actual.iloc[0]['OP']} - {actual.iloc[0]['Nombre_Trabajo']}")
        with c2:
            if not actual.empty:
                with st.form("f_i_f"):
                    st.subheader("🏁 Finalizar Trabajo")
                    me, ro = st.number_input("Metros Totales", 0.0), st.number_input("Rollos Sacados", 0)
                    pt, pd_ = st.number_input("Peso Tinta", 0.0), st.number_input("Peso Desperdicio (kg)", 0.0)
                    mo, ob = st.text_input("Motivo Desperdicio"), st.text_area("Observaciones")
                    if st.form_submit_button("CERRAR TRABAJO"):
                        row = actual.iloc[0]
                        guardar_dato(pd.DataFrame([{"OP":row['OP'], "Fecha_Fin":datetime.now().strftime("%Y-%m-%d"), "Máquina":maq, "Nombre_Trabajo":row['Nombre_Trabajo'], "Marca_Papel":row['Marca_Papel'], "Hora_Inicio_T":row['Hora_I'], "Hora_Final_T":datetime.now().strftime("%H:%M"), "Total_Metros":me, "Rollos_Sacar":ro, "Peso_Tinta":pt, "Peso_Desperdicio":pd_, "Motivo_Desperdicio":mo, "Observaciones":ob}]), "Impresion")
                        eliminar_pendiente("Pendientes_Imp", "Máquina", maq); st.rerun()

# --- 8. MÓDULO CORTE ---
elif menu == "✂️ Corte":
    st.header("✂️ Módulo de Corte")
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS_CORTE):
        if cols[i%4].button(m, key=f"c_{m}", use_container_width=True): st.session_state.sel_c = m
    maq = st.session_state.get("sel_c")
    if maq:
        st.divider()
        seccion_parada(maq)
        st.divider()
        df_p = st.session_state["Pendientes_Corte"]
        actual = df_p[df_p["Máquina"] == maq]
        c1, c2 = st.columns(2)
        with c1:
            if actual.empty:
                with st.form("f_c_i"):
                    st.subheader(f"🟢 Iniciar Corte en {maq}")
                    op, tr = st.text_input("OP"), st.text_input("Nombre Trabajo")
                    pa = st.selectbox("Papel", MARCAS_PAPEL)
                    ab, gr = st.text_input("Ancho"), st.text_input("Gramaje")
                    iv, mr = st.number_input("Imágenes x Varilla", 0), st.text_input("Medida Rollo")
                    if st.form_submit_button("INICIAR CORTE"):
                        guardar_dato(pd.DataFrame([{"OP":op, "Máquina":maq, "Hora_I":datetime.now().strftime("%H:%M"), "Fecha_I":datetime.now().strftime("%Y-%m-%d"), "Nombre_Trabajo":tr, "Marca_Papel":pa, "Ancho_Bobina":ab, "Gramaje":gr, "Imagenes_Varilla":iv, "Medida_Rollo":mr}]), "Pendientes_Corte"); st.rerun()
        with c2:
            if not actual.empty:
                with st.form("f_c_f"):
                    st.subheader("🏁 Finalizar Corte")
                    tv, uc = st.number_input("Total Varillas", 0), st.number_input("Unid x Caja", 0)
                    rc, pd_ = st.number_input("Rollos Cortados", 0), st.number_input("Peso Desperdicio", 0.0)
                    md, ob = st.text_input("Motivo Desp."), st.text_area("Observaciones")
                    if st.form_submit_button("FINALIZAR"):
                        row = actual.iloc[0]
                        guardar_dato(pd.DataFrame([{"OP":row['OP'], "Fecha_Fin":datetime.now().strftime("%Y-%m-%d"), "Máquina":maq, "Nombre_Trabajo":row['Nombre_Trabajo'], "Marca_Papel":row['Marca_Papel'], "Total_Varillas":tv, "Unidades_Por_Caja":uc, "Total_Rollos_Cortados":rc, "Peso_Desperdicio":pd_, "Motivo_Desperdicio":md, "Observaciones":ob, "Hora_Inicio_T":row['Hora_I'], "Hora_Final_T":datetime.now().strftime("%H:%M")}]), "Corte")
                        eliminar_pendiente("Pendientes_Corte", "Máquina", maq); st.rerun()

# --- 9. MÓDULO COLECTORAS ---
elif menu == "📥 Colectoras":
    st.header("📥 Módulo de Colectoras")
    cols = st.columns(2)
    for i, m in enumerate(MAQUINAS_COL):
        if cols[i%2].button(m, key=f"col_{m}", use_container_width=True): st.session_state.sel_col = m
    maq = st.session_state.get("sel_col")
    if maq:
        st.divider()
        seccion_parada(maq)
        st.divider()
        df_p = st.session_state["Pendientes_Col"]
        actual = df_p[df_p["Máquina"] == maq]
        c1, c2 = st.columns(2)
        with
