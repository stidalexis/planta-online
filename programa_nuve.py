import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="Sistema Planta Full", page_icon="🏭")

# --- 2. INICIALIZACIÓN DE TABLAS CON TODOS LOS CAMPOS ---
columnas_tablas = {
    "Impresion": ["OP", "Fecha_Fin", "Máquina", "Nombre_Trabajo", "Marca_Papel", "Hora_Inicio_T", "Hora_Final_T", "Total_Metros", "Rollos_Sacar", "Peso_Tinta", "Peso_Desperdicio", "Motivo_Desperdicio", "Observaciones"],
    "Corte": ["OP", "Fecha_Fin", "Máquina", "Nombre_Trabajo", "Marca_Papel", "Total_Varillas", "Unidades_Por_Caja", "Total_Rollos_Cortados", "Peso_Desperdicio", "Motivo_Desperdicio", "Observaciones", "Hora_Inicio_T", "Hora_Final_T"],
    "Colectoras": ["OP", "Fecha_Fin", "Máquina", "Nombre_Trabajo", "Marca_Papel", "Hora_Inicio_T", "Hora_Final_T", "Total_Cajas", "Total_Formas", "Peso_Desperdicio", "Motivo_Desperdicio", "Observaciones"],
    "Encuadernacion": ["OP", "Fecha_Fin", "Nombre_Trabajo", "Cant_Formas", "Tipo_Material", "Medida_Forma", "Hora_Inicio_T", "Hora_Final_T", "Unid_Caja", "Cant_Final", "Tipo_Presentacion", "Peso_Desperdicio", "Motivo_Desperdicio", "Observaciones"],
    "Pendientes_Imp": ["OP", "Máquina", "Hora_I", "Fecha_I", "Nombre_Trabajo", "Marca_Papel", "Ancho_Bobina", "Gramaje", "Cant_Tintas", "Medida_Rollo", "Cant_Imagenes"],
    "Pendientes_Corte": ["OP", "Máquina", "Hora_I", "Fecha_I", "Nombre_Trabajo", "Marca_Papel", "Ancho_Bobina", "Gramaje", "Imagenes_Varilla", "Medida_Rollo"],
    "Pendientes_Col": ["OP", "Máquina", "Hora_I", "Fecha_I", "Nombre_Trabajo", "Marca_Papel", "Medida_Forma", "Unidades_Caja"],
    "Pendientes_Enc": ["OP", "Hora_I", "Fecha_I", "Nombre_Trabajo", "Cant_Formas", "Tipo_Material", "Medida_Forma"],
    "Paradas_Emergencia": ["Máquina", "Estado", "Fecha", "Hora_Inicio", "Motivo"],
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
    "alexander": {"pass": "admin123", "rol": "admin", "vistas": ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación", "⏱️ Seguimiento Cortadoras"]},
    "giovanny": {"pass": "1503", "rol": "supervisor", "vistas": ["🖨️ Impresión", "📥 Colectoras"]},
    "leonel": {"pass": "0321", "rol": "supervisor", "vistas": ["✂️ Corte", "⏱️ Seguimiento Cortadoras"]},
    "gerardo": {"pass": "1234", "rol": "supervisor", "vistas": ["✂️ Corte", "⏱️ Seguimiento Cortadoras"]},
    "jinna": {"pass": "1234", "rol": "supervisor", "vistas": ["📕 Encuadernación","🖨️ Impresión"]}
}

# --- 4. FUNCIONES ---
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

# --- 5. LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🏭 SISTEMA PLANTA")
    u = st.text_input("Usuario")
    p = st.text_input("Password", type="password")
    if st.button("ENTRAR"):
        if u in USUARIOS and USUARIOS[u]["pass"] == p:
            st.session_state.update({"autenticado":True, "usuario":u, "rol":USUARIOS[u]["rol"], "vistas":USUARIOS[u]["vistas"]})
            st.rerun()
    st.stop()

# --- 6. SIDEBAR ---
st.sidebar.title(f"👤 {st.session_state.usuario}")
if st.session_state.rol == "admin":
    st.sidebar.download_button("📥 DESCARGAR EXCEL", descargar_excel(), f"Reporte_{datetime.now().strftime('%d-%m-%Y')}.xlsx", use_container_width=True)
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

menu = st.sidebar.radio("MENÚ", st.session_state.vistas)

# --- 7. MÓDULOS ---

# IMPRESIÓN
if menu == "🖨️ Impresión":
    st.header("🖨️ Impresión")
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS_IMP):
        if cols[i%4].button(m, key=f"i_{m}", use_container_width=True): st.session_state.sel_i = m
    maq = st.session_state.get("sel_i")
    if maq:
        df_p = st.session_state["Pendientes_Imp"]
        actual = df_p[df_p["Máquina"] == maq]
        c1, c2 = st.columns(2)
        with c1:
            if actual.empty:
                with st.form("f_i_i"):
                    op, tr = st.text_input("OP"), st.text_input("Trabajo")
                    pa = st.selectbox("Papel", MARCAS_PAPEL)
                    ab, gr = st.text_input("Ancho"), st.text_input("Gramaje")
                    ct, mr = st.number_input("Tintas", 0), st.text_input("Medida Rollo")
                    if st.form_submit_button("INICIAR"):
                        guardar_dato(pd.DataFrame([{"OP":op, "Máquina":maq, "Hora_I":datetime.now().strftime("%H:%M"), "Fecha_I":datetime.now().strftime("%Y-%m-%d"), "Nombre_Trabajo":tr, "Marca_Papel":pa, "Ancho_Bobina":ab, "Gramaje":gr, "Cant_Tintas":ct, "Medida_Rollo":mr}]), "Pendientes_Imp")
                        st.rerun()
        with c2:
            if not actual.empty:
                with st.form("f_i_f"):
                    me, ro = st.number_input("Metros", 0.0), st.number_input("Rollos", 0)
                    pt, pd_ = st.number_input("Peso Tinta", 0.0), st.number_input("Peso Desp.", 0.0)
                    mo, ob = st.text_input("Motivo"), st.text_area("Obs")
                    if st.form_submit_button("FINALIZAR"):
                        row = actual.iloc[0]
                        guardar_dato(pd.DataFrame([{"OP":row['OP'], "Fecha_Fin":datetime.now().strftime("%Y-%m-%d"), "Máquina":maq, "Nombre_Trabajo":row['Nombre_Trabajo'], "Marca_Papel":row['Marca_Papel'], "Hora_Inicio_T":row['Hora_I'], "Hora_Final_T":datetime.now().strftime("%H:%M"), "Total_Metros":me, "Rollos_Sacar":ro, "Peso_Tinta":pt, "Peso_Desperdicio":pd_, "Motivo_Desperdicio":mo, "Observaciones":ob}]), "Impresion")
                        eliminar_pendiente("Pendientes_Imp", "Máquina", maq); st.rerun()

# CORTE
elif menu == "✂️ Corte":
    st.header("✂️ Corte")
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS_CORTE):
        if cols[i%4].button(m, key=f"c_{m}", use_container_width=True): st.session_state.sel_c = m
    maq = st.session_state.get("sel_c")
    if maq:
        df_p = st.session_state["Pendientes_Corte"]
        actual = df_p[df_p["Máquina"] == maq]
        c1, c2 = st.columns(2)
        with c1:
            if actual.empty:
                with st.form("f_c_i"):
                    op, tr = st.text_input("OP"), st.text_input("Trabajo")
                    pa = st.selectbox("Papel", MARCAS_PAPEL)
                    iv, mr = st.number_input("Imágenes x Varilla", 0), st.text_input("Medida Rollo")
                    if st.form_submit_button("INICIAR"):
                        guardar_dato(pd.DataFrame([{"OP":op, "Máquina":maq, "Hora_I":datetime.now().strftime("%H:%M"), "Fecha_I":datetime.now().strftime("%Y-%m-%d"), "Nombre_Trabajo":tr, "Marca_Papel":pa, "Imagenes_Varilla":iv, "Medida_Rollo":mr}]), "Pendientes_Corte")
                        st.rerun()
        with c2:
            if not actual.empty:
                with st.form("f_c_f"):
                    tv, uc = st.number_input("Varillas", 0), st.number_input("Unid x Caja", 0)
                    pd_, md = st.number_input("Peso Desp.", 0.0), st.text_input("Motivo")
                    if st.form_submit_button("FINALIZAR"):
                        row = actual.iloc[0]
                        guardar_dato(pd.DataFrame([{"OP":row['OP'], "Fecha_Fin":datetime.now().strftime("%Y-%m-%d"), "Máquina":maq, "Nombre_Trabajo":row['Nombre_Trabajo'], "Total_Varillas":tv, "Unidades_Por_Caja":uc, "Peso_Desperdicio":pd_, "Motivo_Desperdicio":md, "Hora_Inicio_T":row['Hora_I'], "Hora_Final_T":datetime.now().strftime("%H:%M")}]), "Corte")
                        eliminar_pendiente("Pendientes_Corte", "Máquina", maq); st.rerun()

# COLECTORAS
elif menu == "📥 Colectoras":
    st.header("📥 Colectoras")
    cols = st.columns(2)
    for i, m in enumerate(MAQUINAS_COL):
        if cols[i%2].button(m, key=f"col_{m}", use_container_width=True): st.session_state.sel_col = m
    maq = st.session_state.get("sel_col")
    if maq:
        df_p = st.session_state["Pendientes_Col"]
        actual = df_p[df_p["Máquina"] == maq]
        c1, c2 = st.columns(2)
        with c1:
            if actual.empty:
                with st.form("f_co_i"):
                    op, tr = st.text_input("OP"), st.text_input("Trabajo")
                    mf, uc = st.text_input("Medida Forma"), st.number_input("Unid x Caja", 0)
                    if st.form_submit_button("INICIAR"):
                        guardar_dato(pd.DataFrame([{"OP":op, "Máquina":maq, "Hora_I":datetime.now().strftime("%H:%M"), "Fecha_I":datetime.now().strftime("%Y-%m-%d"), "Nombre_Trabajo":tr, "Medida_Forma":mf, "Unidades_Caja":uc}]), "Pendientes_Col")
                        st.rerun()
        with c2:
            if not actual.empty:
                with st.form("f_co_f"):
                    tc, tf = st.number_input("Total Cajas", 0), st.number_input("Total Formas", 0)
                    pd_ = st.number_input("Peso Desp.", 0.0)
                    if st.form_submit_button("FINALIZAR"):
                        row = actual.iloc[0]
                        guardar_dato(pd.DataFrame([{"OP":row['OP'], "Fecha_Fin":datetime.now().strftime("%Y-%m-%d"), "Máquina":maq, "Total_Cajas":tc, "Total_Formas":tf, "Peso_Desperdicio":pd_, "Hora_Inicio_T":row['Hora_I'], "Hora_Final_T":datetime.now().strftime("%H:%M")}]), "Colectoras")
                        eliminar_pendiente("Pendientes_Col", "Máquina", maq); st.rerun()

# ENCUADERNACIÓN
elif menu == "📕 Encuadernación":
    st.header("📕 Encuadernación")
    c1, c2 = st.columns(2)
    with c1:
        with st.form("f_e_i"):
            op, tr = st.text_input("OP"), st.text_input("Trabajo")
            cf, tm = st.number_input("Cant Formas", 0), st.text_input("Material")
            if st.form_submit_button("INICIAR"):
                guardar_dato(pd.DataFrame([{"OP":op, "Nombre_Trabajo":tr, "Cant_Formas":cf, "Tipo_Material":tm, "Hora_I":datetime.now().strftime("%H:%M"), "Fecha_I":datetime.now().strftime("%Y-%m-%d")}]), "Pendientes_Enc"); st.rerun()
    with c2:
        df_p = st.session_state["Pendientes_Enc"]
        for i, row in df_p.iterrows():
            with st.expander(f"OP {row['OP']}"):
                with st.form(f"f_e_f_{i}"):
                    uc, cf_ = st.number_input("Unid x Caja", 0), st.number_input("Cant Final", 0)
                    pd_ = st.number_input("Peso Desp.", 0.0)
                    if st.form_submit_button("FINALIZAR"):
                        guardar_dato(pd.DataFrame([{"OP":row['OP'], "Nombre_Trabajo":row['Nombre_Trabajo'], "Cant_Final":cf_, "Unid_Caja":uc, "Peso_Desperdicio":pd_, "Fecha_Fin":datetime.now().strftime("%Y-%m-%d"), "Hora_Inicio_T":row['Hora_I'], "Hora_Final_T":datetime.now().strftime("%H:%M")}]), "Encuadernacion")
                        eliminar_pendiente("Pendientes_Enc", "OP", row['OP']); st.rerun()

# SEGUIMIENTO CORTADORAS (RESTRICCIÓN 2 TURNOS)
elif menu == "⏱️ Seguimiento Cortadoras":
    st.header("⏱️ Seguimiento (Cierre de Turno)")
    h_act = datetime.now().hour
    perm, turno = False, ""
    if 13 <= h_act < 14: perm, turno = True, "Mañana (6am-2pm)"
    elif 21 <= h_act < 22: perm, turno = True, "Tarde (2pm-10pm)"
    
    if perm or st.session_state.rol == "admin":
        with st.form("f_s"):
            st.subheader(f"Cierre de Turno: {turno if turno else 'Admin'}")
            c1, c2, c3 = st.columns(3)
            with c1:
                ma = st.selectbox("Máquina", MAQUINAS_CORTE)
                tu = st.selectbox("Turno", ["Mañana (6am-2pm)", "Tarde (2pm-10pm)"], index=0 if turno == "Mañana (6am-2pm)" else 1)
            with c2:
                op, tr = st.text_input("OP"), st.text_input("Trabajo")
            with c3:
                nc, mr = st.number_input("Cajas", 0), st.number_input("Metros Rollo", 0.0)
            if st.form_submit_button("GUARDAR CIERRE"):
                guardar_dato(pd.DataFrame([{"Fecha":datetime.now().strftime("%Y-%m-%d"), "Turno":tu, "Máquina":ma, "OP":op, "Nombre_Trabajo":tr, "Num_Cajas":nc, "Metros_Rollo":mr, "Hora_Registro":datetime.now().strftime("%H:%M")}]), "Seguimiento_Cortadoras")
                st.success("Guardado")
    else: st.error("⏳ Solo disponible de 1:00 PM a 2:00 PM y de 9:00 PM a 10:00 PM")
