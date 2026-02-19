import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA PLANTA TOTAL", page_icon="🏭")

# --- 2. ESTRUCTURA DE DATOS COMPLETA ---
columnas_tablas = {
    "Impresion": ["OP", "Fecha_Fin", "Máquina", "Nombre_Trabajo", "Marca_Papel", "Ancho_Bobina", "Gramaje", "Cant_Tintas", "Medida_Rollo", "Cant_Imagenes", "Hora_Inicio_T", "Hora_Final_T", "Total_Metros", "Rollos_Sacar", "Peso_Tinta", "Peso_Desperdicio", "Motivo_Desperdicio", "Observaciones"],
    "Corte": ["OP", "Fecha_Fin", "Máquina", "Nombre_Trabajo", "Marca_Papel", "Ancho_Bobina", "Gramaje", "Imagenes_Varilla", "Medida_Rollo", "Total_Varillas", "Unidades_Por_Caja", "Total_Rollos_Cortados", "Peso_Desperdicio", "Motivo_Desperdicio", "Observaciones", "Hora_Inicio_T", "Hora_Final_T"],
    "Colectoras": ["OP", "Fecha_Fin", "Máquina", "Nombre_Trabajo", "Marca_Papel", "Medida_Forma", "Unidades_Caja", "Hora_Inicio_T", "Hora_Final_T", "Total_Cajas", "Total_Formas", "Peso_Desperdicio", "Motivo_Desperdicio", "Observaciones"],
    "Encuadernacion": ["OP", "Fecha_Fin", "Nombre_Trabajo", "Cant_Formas", "Tipo_Material", "Medida_Forma", "Hora_Inicio_T", "Hora_Final_T", "Unid_Caja", "Cant_Final", "Tipo_Presentacion", "Peso_Desperdicio", "Motivo_Desperdicio", "Observaciones"],
    "Pendientes_Imp": ["OP", "Máquina", "Hora_I", "Fecha_I", "Nombre_Trabajo", "Marca_Papel", "Ancho_Bobina", "Gramaje", "Cant_Tintas", "Medida_Rollo", "Cant_Imagenes"],
    "Pendientes_Corte": ["OP", "Máquina", "Hora_I", "Fecha_I", "Nombre_Trabajo", "Marca_Papel", "Ancho_Bobina", "Gramaje", "Imagenes_Varilla", "Medida_Rollo"],
    "Pendientes_Col": ["OP", "Máquina", "Hora_I", "Fecha_I", "Nombre_Trabajo", "Marca_Papel", "Medida_Forma", "Unidades_Caja"],
    "Pendientes_Enc": ["OP", "Hora_I", "Fecha_I", "Nombre_Trabajo", "Cant_Formas", "Tipo_Material", "Medida_Forma"],
    "Paradas_Emergencia": ["Máquina", "Estado", "Fecha", "Hora_Inicio", "Hora_Fin", "Motivo"],
    "Seguimiento_Avance": ["Fecha", "Hora_Registro", "Máquina", "OP", "Varillas_Hora", "Cajas_Hora"],
    "Seguimiento_Cierre": ["Fecha", "Hora_Registro", "Turno", "Máquina", "OP", "Nombre_Trabajo", "Tipo_Papel", "Total_Varillas", "Total_Cajas", "Metros_Totales", "Unid_Caja", "Observaciones_Turno"]
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
    "alexander": {"pass": "admin123", "rol": "admin", "vistas": ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación", "⏱️ Seguimiento Cortadoras", "📊 Historial"]},
    "giovanny": {"pass": "1503", "rol": "supervisor", "vistas": ["🖨️ Impresión", "📥 Colectoras", "📊 Historial"]},
    "leonel": {"pass": "0321", "rol": "supervisor", "vistas": ["✂️ Corte", "⏱️ Seguimiento Cortadoras", "📊 Historial"]},
    "gerardo": {"pass": "1234", "rol": "supervisor", "vistas": ["✂️ Corte", "⏱️ Seguimiento Cortadoras", "📊 Historial"]},
    "jinna": {"pass": "1234", "rol": "supervisor", "vistas": ["📕 Encuadernación","🖨️ Impresión", "📊 Historial"]}
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

def seccion_parada(maq):
    st.subheader("⚠️ Estado de Máquina")
    df_p = st.session_state["Paradas_Emergencia"]
    activa = not df_p.empty and ((df_p["Máquina"] == maq) & (df_p["Estado"] == "Activa")).any()
    if activa:
        st.error(f"🚨 MÁQUINA {maq} EN PARADA")
        if st.button(f"✅ REANUDAR {maq}", use_container_width=True):
            idx = df_p[(df_p["Máquina"] == maq) & (df_p["Estado"] == "Activa")].index[-1]
            st.session_state["Paradas_Emergencia"].at[idx, "Estado"] = "Finalizada"
            st.session_state["Paradas_Emergencia"].at[idx, "Hora_Fin"] = datetime.now().strftime("%H:%M")
            st.rerun()
    else:
        with st.expander("🚨 REGISTRAR PARADA"):
            with st.form(f"p_{maq}"):
                mot = st.selectbox("Motivo", ["Mantenimiento", "Falla Eléctrica", "Falta Material", "Cambio Repuesto", "Ajuste Técnico", "Otro"])
                if st.form_submit_button("CONFIRMAR PARADA"):
                    guardar_dato(pd.DataFrame([{"Máquina":maq, "Estado":"Activa", "Fecha":datetime.now().strftime("%Y-%m-%d"), "Hora_Inicio":datetime.now().strftime("%H:%M"), "Hora_Fin":"", "Motivo":mot}]), "Paradas_Emergencia"); st.rerun()

# --- 5. LOGIN ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False
if not st.session_state.autenticado:
    st.title("🏭 SISTEMA PLANTA")
    u, p = st.text_input("Usuario"), st.text_input("Password", type="password")
    if st.button("ENTRAR"):
        if u in USUARIOS and USUARIOS[u]["pass"] == p:
            st.session_state.update({"autenticado":True, "usuario":u, "rol":USUARIOS[u]["rol"], "vistas":USUARIOS[u]["vistas"]})
            st.rerun()
    st.stop()

# --- 6. SIDEBAR ---
st.sidebar.title(f"👤 {st.session_state.usuario}")
if st.session_state.rol == "admin":
    st.sidebar.download_button("📥 EXPORTAR EXCEL", descargar_excel(), f"Reporte_{datetime.now().strftime('%d-%m-%Y')}.xlsx", use_container_width=True)
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

menu = st.sidebar.radio("MENÚ", st.session_state.vistas)

# --- 7. MÓDULOS ---
if menu == "🖨️ Impresión":
    st.header("🖨️ Impresión")
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS_IMP):
        if cols[i%4].button(m, key=f"i_{m}", use_container_width=True): st.session_state.sel_i = m
    maq = st.session_state.get("sel_i")
    if maq:
        seccion_parada(maq); st.divider()
        df_p = st.session_state["Pendientes_Imp"]
        actual = df_p[df_p["Máquina"] == maq]
        c1, c2 = st.columns(2)
        with c1:
            if actual.empty:
                with st.form("f_i_i"):
                    st.subheader("🟢 Iniciar")
                    op, tr = st.text_input("OP"), st.text_input("Trabajo")
                    pa = st.selectbox("Papel", MARCAS_PAPEL)
                    ab, gr = st.text_input("Ancho"), st.text_input("Gramaje")
                    ct, mr = st.number_input("Tintas", 0), st.text_input("Medida Rollo")
                    ci = st.number_input("Imágenes", 0)
                    if st.form_submit_button("REGISTRAR INICIO"):
                        guardar_dato(pd.DataFrame([{"OP":op, "Máquina":maq, "Hora_I":datetime.now().strftime("%H:%M"), "Fecha_I":datetime.now().strftime("%Y-%m-%d"), "Nombre_Trabajo":tr, "Marca_Papel":pa, "Ancho_Bobina":ab, "Gramaje":gr, "Cant_Tintas":ct, "Medida_Rollo":mr, "Cant_Imagenes":ci}]), "Pendientes_Imp"); st.rerun()
        with c2:
            if not actual.empty:
                with st.form("f_i_f"):
                    st.subheader("🏁 Finalizar")
                    me, ro = st.number_input("Metros", 0.0), st.number_input("Rollos", 0)
                    pt, pd_ = st.number_input("Peso Tinta", 0.0), st.number_input("Peso Desp. (kg)", 0.0)
                    mo, ob = st.text_input("Motivo Desp."), st.text_area("Obs")
                    if st.form_submit_button("GUARDAR"):
                        row = actual.iloc[0]
                        guardar_dato(pd.DataFrame([{"OP":row['OP'], "Fecha_Fin":datetime.now().strftime("%Y-%m-%d"), "Máquina":maq, "Nombre_Trabajo":row['Nombre_Trabajo'], "Marca_Papel":row['Marca_Papel'], "Ancho_Bobina":row['Ancho_Bobina'], "Gramaje":row['Gramaje'], "Cant_Tintas":row['Cant_Tintas'], "Medida_Rollo":row['Medida_Rollo'], "Cant_Imagenes":row['Cant_Imagenes'], "Hora_Inicio_T":row['Hora_I'], "Hora_Final_T":datetime.now().strftime("%H:%M"), "Total_Metros":me, "Rollos_Sacar":ro, "Peso_Tinta":pt, "Peso_Desperdicio":pd_, "Motivo_Desperdicio":mo, "Observaciones":ob}]), "Impresion")
                        eliminar_pendiente("Pendientes_Imp", "Máquina", maq); st.rerun()

elif menu == "✂️ Corte":
    st.header("✂️ Corte")
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS_CORTE):
        if cols[i%4].button(m, key=f"c_{m}", use_container_width=True): st.session_state.sel_c = m
    maq = st.session_state.get("sel_c")
    if maq:
        seccion_parada(maq); st.divider()
        df_p = st.session_state["Pendientes_Corte"]
        actual = df_p[df_p["Máquina"] == maq]
        c1, c2 = st.columns(2)
        with c1:
            if actual.empty:
                with st.form("f_c_i"):
                    st.subheader("🟢 Iniciar")
                    op, tr = st.text_input("OP"), st.text_input("Trabajo")
                    pa, ab, gr = st.selectbox("Papel", MARCAS_PAPEL), st.text_input("Ancho"), st.text_input("Gramaje")
                    iv, mr = st.number_input("Imágenes x Varilla", 0), st.text_input("Medida Rollo")
                    if st.form_submit_button("INICIAR"):
                        guardar_dato(pd.DataFrame([{"OP":op, "Máquina":maq, "Hora_I":datetime.now().strftime("%H:%M"), "Fecha_I":datetime.now().strftime("%Y-%m-%d"), "Nombre_Trabajo":tr, "Marca_Papel":pa, "Ancho_Bobina":ab, "Gramaje":gr, "Imagenes_Varilla":iv, "Medida_Rollo":mr}]), "Pendientes_Corte"); st.rerun()
        with c2:
            if not actual.empty:
                with st.form("f_c_f"):
                    st.subheader("🏁 Finalizar")
                    tv, uc = st.number_input("Total Varillas", 0), st.number_input("Unid x Caja", 0)
                    rc, pd_ = st.number_input("Rollos Cortados", 0), st.number_input("Peso Desp.", 0.0)
                    md, ob = st.text_input("Motivo"), st.text_area("Obs")
                    if st.form_submit_button("FINALIZAR"):
                        row = actual.iloc[0]
                        guardar_dato(pd.DataFrame([{"OP":row['OP'], "Fecha_Fin":datetime.now().strftime("%Y-%m-%d"), "Máquina":maq, "Nombre_Trabajo":row['Nombre_Trabajo'], "Marca_Papel":row['Marca_Papel'], "Ancho_Bobina":row['Ancho_Bobina'], "Gramaje":row['Gramaje'], "Imagenes_Varilla":row['Imagenes_Varilla'], "Medida_Rollo":row['Medida_Rollo'], "Total_Varillas":tv, "Unidades_Por_Caja":uc, "Total_Rollos_Cortados":rc, "Peso_Desperdicio":pd_, "Motivo_Desperdicio":md, "Observaciones":ob, "Hora_Inicio_T":row['Hora_I'], "Hora_Final_T":datetime.now().strftime("%H:%M")}]), "Corte")
                        eliminar_pendiente("Pendientes_Corte", "Máquina", maq); st.rerun()

elif menu == "📥 Colectoras":
    st.header("📥 Colectoras")
    cols = st.columns(2)
    for i, m in enumerate(MAQUINAS_COL):
        if cols[i%2].button(m, key=f"col_{m}", use_container_width=True): st.session_state.sel_col = m
    maq = st.session_state.get("sel_col")
    if maq:
        seccion_parada(maq); st.divider()
        df_p = st.session_state["Pendientes_Col"]
        actual = df_p[df_p["Máquina"] == maq]
        c1, c2 = st.columns(2)
        with c1:
            if actual.empty:
                with st.form("f_co_i"):
                    st.subheader("🟢 Iniciar")
                    op, tr = st.text_input("OP"), st.text_input("Trabajo")
                    pa, mf, uc = st.selectbox("Papel", MARCAS_PAPEL), st.text_input("Medida Forma"), st.number_input("Unid x Caja", 0)
                    if st.form_submit_button("REGISTRAR"):
                        guardar_dato(pd.DataFrame([{"OP":op, "Máquina":maq, "Hora_I":datetime.now().strftime("%H:%M"), "Fecha_I":datetime.now().strftime("%Y-%m-%d"), "Nombre_Trabajo":tr, "Marca_Papel":pa, "Medida_Forma":mf, "Unidades_Caja":uc}]), "Pendientes_Col"); st.rerun()
        with c2:
            if not actual.empty:
                with st.form("f_co_f"):
                    st.subheader("🏁 Finalizar")
                    tc, tf, pd_ = st.number_input("Cajas", 0), st.number_input("Formas", 0), st.number_input("Peso Desp.", 0.0)
                    mo, ob = st.text_input("Motivo"), st.text_area("Obs")
                    if st.form_submit_button("FINALIZAR"):
                        row = actual.iloc[0]
                        guardar_dato(pd.DataFrame([{"OP":row['OP'], "Fecha_Fin":datetime.now().strftime("%Y-%m-%d"), "Máquina":maq, "Nombre_Trabajo":row['Nombre_Trabajo'], "Marca_Papel":row['Marca_Papel'], "Medida_Forma":row['Medida_Forma'], "Unidades_Caja":row['Unidades_Caja'], "Hora_Inicio_T":row['Hora_I'], "Hora_Final_T":datetime.now().strftime("%H:%M"), "Total_Cajas":tc, "Total_Formas":tf, "Peso_Desperdicio":pd_, "Motivo_Desperdicio":mo, "Observaciones":ob}]), "Colectoras")
                        eliminar_pendiente("Pendientes_Col", "Máquina", maq); st.rerun()

elif menu == "📕 Encuadernación":
    st.header("📕 Encuadernación")
    c1, c2 = st.columns(2)
    with c1:
        with st.form("f_e_i"):
            st.subheader("🟢 Nuevo")
            op, tr = st.text_input("OP"), st.text_input("Trabajo")
            cf, tm, mf = st.number_input("Formas", 0), st.text_input("Material"), st.text_input("Medida")
            if st.form_submit_button("INICIAR"):
                guardar_dato(pd.DataFrame([{"OP":op, "Hora_I":datetime.now().strftime("%H:%M"), "Fecha_I":datetime.now().strftime("%Y-%m-%d"), "Nombre_Trabajo":tr, "Cant_Formas":cf, "Tipo_Material":tm, "Medida_Forma":mf}]), "Pendientes_Enc"); st.rerun()
    with c2:
        st.subheader("🏁 Finalizar")
        df_p = st.session_state["Pendientes_Enc"]
        for i, row in df_p.iterrows():
            with st.expander(f"OP {row['OP']}"):
                with st.form(f"f_e_f_{i}"):
                    uc, cf_, tp = st.number_input("Unid/Caja", 0), st.number_input("Total", 0), st.selectbox("Tipo", ["Caja", "Paquete"])
                    pd_, mo = st.number_input("Desp.", 0.0), st.text_input("Motivo")
                    if st.form_submit_button(f"CERRAR {row['OP']}"):
                        guardar_dato(pd.DataFrame([{"OP":row['OP'], "Fecha_Fin":datetime.now().strftime("%Y-%m-%d"), "Nombre_Trabajo":row['Nombre_Trabajo'], "Cant_Formas":row['Cant_Formas'], "Tipo_Material":row['Tipo_Material'], "Medida_Forma":row['Medida_Forma'], "Hora_Inicio_T":row['Hora_I'], "Hora_Final_T":datetime.now().strftime("%H:%M"), "Unid_Caja":uc, "Cant_Final":cf_, "Tipo_Presentacion":tp, "Peso_Desperdicio":pd_, "Motivo_Desperdicio":mo}]), "Encuadernacion")
                        eliminar_pendiente("Pendientes_Enc", "OP", row['OP']); st.rerun()

elif menu == "⏱️ Seguimiento Cortadoras":
    st.header("⏱️ Seguimiento Cortadoras")
    tab_av, tab_ci = st.tabs(["📈 Avance Hora a Hora", "🏁 Cierre de Turno"])
    with tab_av:
        with st.form("f_av"):
            c1, c2, c3, c4 = st.columns(4)
            ma = c1.selectbox("Máquina", MAQUINAS_CORTE, key="ma_av")
            op = c2.text_input("OP", key="op_av")
            va = c3.number_input("Varillas hora", 0)
            ca = c4.number_input("Cajas hora", 0)
            if st.form_submit_button("REGISTRAR AVANCE"):
                guardar_dato(pd.DataFrame([{"Fecha":datetime.now().strftime("%Y-%m-%d"), "Hora_Registro":datetime.now().strftime("%H:%M"), "Máquina":ma, "OP":op, "Varillas_Hora":va, "Cajas_Hora":ca}]), "Seguimiento_Avance"); st.success("Registrado")
    with tab_ci:
        h = datetime.now().hour
        perm = (13 <= h < 14) or (21 <= h < 22) or (st.session_state.rol == "admin")
        if perm:
            with st.form("f_ci"):
                c1, c2, c3 = st.columns(3)
                ma_c, tu_c = c1.selectbox("Máquina", MAQUINAS_CORTE), c1.selectbox("Turno", ["Mañana", "Tarde"])
                op_c, tr_c, pa_c = c2.text_input("OP"), c2.text_input("Trabajo"), c2.selectbox("Papel", MARCAS_PAPEL)
                va_t, ca_t, me_t = c3.number_input("TOTAL Varillas", 0), c3.number_input("TOTAL Cajas", 0), c3.number_input("TOTAL Metros", 0.0)
                obs_c = st.text_area("Observaciones")
                if st.form_submit_button("CERRAR TURNO"):
                    guardar_dato(pd.DataFrame([{"Fecha":datetime.now().strftime("%Y-%m-%d"), "Hora_Registro":datetime.now().strftime("%H:%M"), "Turno":tu_c, "Máquina":ma_c, "OP":op_c, "Nombre_Trabajo":tr_c, "Tipo_Papel":pa_c, "Total_Varillas":va_t, "Total_Cajas":ca_t, "Metros_Totales":me_t, "Unid_Caja":0, "Observaciones_Turno":obs_c}]), "Seguimiento_Cierre"); st.success("Turno Cerrado")
        else: st.warning("Cierre habilitado solo a la 1 PM o 9 PM.")

elif menu == "📊 Historial":
    st.header("📊 Historial")
    tabs = st.tabs(["Impresión", "Corte", "Colectoras", "Encuadernación", "Paradas", "Avance Cort.", "Cierre Cort."])
    with tabs[0]: st.dataframe(st.session_state["Impresion"], use_container_width=True)
    with tabs[1]: st.dataframe(st.session_state["Corte"], use_container_width=True)
    with tabs[2]: st.dataframe(st.session_state["Colectoras"], use_container_width=True)
    with tabs[3]: st.dataframe(st.session_state["Encuadernacion"], use_container_width=True)
    with tabs[4]: st.dataframe(st.session_state["Paradas_Emergencia"], use_container_width=True)
    with tabs[5]: st.dataframe(st.session_state["Seguimiento_Avance"], use_container_width=True)
    with tabs[6]: st.dataframe(st.session_state["Seguimiento_Cierre"], use_container_width=True)
