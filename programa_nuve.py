import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA PLANTA INTEGRAL", page_icon="🏭")

# --- CONEXIÓN DIRECTA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(hoja):
    try:
        return conn.read(worksheet=hoja, ttl=0).dropna(how='all')
    except:
        return pd.DataFrame()

def guardar_datos(df_nuevo, hoja):
    df_actual = cargar_datos(hoja)
    df_final = pd.concat([df_actual, df_nuevo], ignore_index=True)
    conn.update(worksheet=hoja, data=df_final)
    st.success(f"✅ Sincronizado en {hoja}")

# --- LISTADO COMPLETO DE MÁQUINAS ---
MAQ_IMP = ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"]
MAQ_COR = ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"]
MAQ_COL = ["COL-01", "COL-02"]

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🏭 ACCESO SISTEMA PLANTA")
    col1, col2 = st.columns(2)
    u = col1.text_input("Usuario")
    p = col2.text_input("Password", type="password")
    if st.button("ENTRAR", use_container_width=True):
        st.session_state.auth = True
        st.rerun()
    st.stop()

# --- NAVEGACIÓN TÁCTIL ---
menu = st.sidebar.radio("MENÚ PRINCIPAL", ["🖨️ IMPRESIÓN", "✂️ CORTE", "📥 COLECTORAS", "📕 ENCUADERNACIÓN", "⏱️ AVANCE (GAP)", "📊 HISTORIAL"])

# Función para selector táctil de máquinas (Botones grandes)
def selector_táctil(lista, titulo):
    st.write(f"### {titulo}")
    # Mostrar botones en filas de 4 para que sean fáciles de tocar
    cols = st.columns(4)
    for i, m in enumerate(lista):
        if cols[i % 4].button(m, key=f"btn_{m}", use_container_width=True):
            st.session_state.maquina_activa = m
    return st.session_state.get("maquina_activa")

# --- MÓDULOS ---

if menu == "🖨️ IMPRESIÓN":
    st.header("Formulario Técnico de Impresión")
    maq = selector_táctil(MAQ_IMP, "Seleccione Prensa:")
    if maq:
        with st.form("f_imp"):
            st.info(f"Máquina: {maq}")
            c1, c2, c3 = st.columns(3)
            op = c1.text_input("OP")
            tr = c2.text_input("Trabajo")
            pa = c3.text_input("Marca Papel")
            an = c1.text_input("Ancho Bobina")
            gr = c2.text_input("Gramaje")
            ti = c3.number_input("Cant. Tintas", 0)
            me = c1.text_input("Medida Rollo")
            im = c2.number_input("Cant. Imágenes", 0)
            me_t = c3.number_input("Total Metros", 0)
            hi = c1.text_input("Hora Inicio (HH:MM)")
            hf = c2.text_input("Hora Fin (HH:MM)")
            de = c3.number_input("Desperdicio (Kg)", 0.0)
            mo = st.text_input("Motivo Desperdicio")
            ob = st.text_area("Observaciones")
            if st.form_submit_button("GUARDAR DATOS", use_container_width=True):
                nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Máquina":maq, "Trabajo":tr, "Papel":pa, "Ancho":an, "Gramaje":gr, "Tintas":ti, "Medida":me, "Imágenes":im, "Metros":me_t, "H_Inicio":hi, "H_Fin":hf, "Desp_Kg":de, "Motivo":mo, "Obs":ob}])
                guardar_datos(nuevo, "Impresion")

elif menu == "✂️ CORTE":
    st.header("Formulario Técnico de Corte")
    maq = selector_táctil(MAQ_COR, "Seleccione Cortadora:")
    if maq:
        with st.form("f_cor"):
            st.info(f"Máquina: {maq}")
            c1, c2, c3 = st.columns(3)
            op = c1.text_input("OP")
            tr = c2.text_input("Trabajo")
            iv = c3.number_input("Imágenes x Varilla", 0)
            me = c1.text_input("Medida Final")
            tv = c2.number_input("Total Varillas", 0)
            rc = c3.number_input("Total Rollos Cortados", 0)
            uc = c1.number_input("Unid. por Caja", 0)
            hi = c2.text_input("Hora Inicio")
            hf = c3.text_input("Hora Fin")
            de = c1.number_input("Desperdicio (Kg)", 0.0)
            mo = st.text_input("Motivo Desperdicio")
            if st.form_submit_button("GUARDAR CORTE", use_container_width=True):
                nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Máquina":maq, "Trabajo":tr, "Img_Varilla":iv, "Medida":me, "Total_Varillas":tv, "Rollos_Cortados":rc, "Unid_Caja":uc, "H_Inicio":hi, "H_Fin":hf, "Desp_Kg":de, "Motivo":mo}])
                guardar_datos(nuevo, "Corte")

elif menu == "📥 COLECTORAS":
    st.header("Formulario de Colectoras")
    maq = selector_táctil(MAQ_COL, "Seleccione Colectora:")
    if maq:
        with st.form("f_col"):
            c1, c2 = st.columns(2)
            op = c1.text_input("OP")
            tr = c2.text_input("Nombre Trabajo")
            mf = c1.text_input("Medida Forma")
            uc = c2.number_input("Unidades x Caja", 0)
            tc = c1.number_input("Total Cajas", 0)
            tf = c2.number_input("Total Formas", 0)
            hi = c1.text_input("Hora Inicio")
            hf = c2.text_input("Hora Fin")
            if st.form_submit_button("GUARDAR COLECTORAS"):
                nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Máquina":maq, "Trabajo":tr, "Medida_Forma":mf, "Unid_Caja":uc, "Total_Cajas":tc, "Total_Formas":tf, "H_Inicio":hi, "H_Fin":hf}])
                guardar_datos(nuevo, "Colectoras")

elif menu == "📕 ENCUADERNACIÓN":
    st.header("Formulario de Encuadernación")
    with st.form("f_enc"):
        c1, c2, c3 = st.columns(3)
        op = c1.text_input("OP")
        tr = c2.text_input("Trabajo")
        cf = c3.number_input("Cant. Formas", 0)
        tm = c1.text_input("Tipo Material")
        me = c2.text_input("Medida Forma")
        hi = c3.text_input("Hora Inicio")
        hf = c1.text_input("Hora Fin")
        uc = c2.number_input("Unid. Caja", 0)
        cf_fin = c3.number_input("Cant. Final", 0)
        if st.form_submit_button("GUARDAR ENCUADERNACIÓN"):
            nuevo = pd.DataFrame([{"OP":op, "Fecha":datetime.now().strftime("%d/%m/%Y"), "Trabajo":tr, "Cant_Formas":cf, "Material":tm, "Medida":me, "H_Inicio":hi, "H_Fin":hf, "Unid_Caja":uc, "Cant_Final":cf_fin}])
            guardar_datos(nuevo, "Encuadernacion")

elif menu == "⏱️ AVANCE (GAP)":
    st.header("Seguimiento de Metas (GAP)")
    maq = selector_táctil(MAQ_COR, "Seleccione Máquina de Corte:")
    if maq:
        meta_dia = st.number_input(f"Meta diaria para {maq} (Varillas)", value=5000)
        df_hoy = cargar_datos("Seguimiento_Avance")
        # Filtrar solo hoy y esta máquina
        hoy = datetime.now().strftime("%d/%m/%Y")
        if not df_hoy.empty:
            df_maq = df_hoy[(df_hoy["Máquina"] == maq) & (df_hoy["Fecha"] == hoy)]
            total_logrado = df_maq["Varillas_Hora"].sum()
        else:
            total_logrado = 0
        
        # Mostrar métricas
        gap = meta_dia - total_logrado
        c1, c2, c3 = st.columns(3)
        c1.metric("LOGRADO", f"{total_logrado}")
        c2.metric("META", f"{meta_dia}")
        c3.metric("GAP (Faltante)", f"{gap}", delta=-gap)
        
        with st.form("f_gap"):
            st.write("### Registrar Producción de esta hora")
            c1, c2 = st.columns(2)
            op_h = c1.text_input("OP actual")
            vh = c2.number_input("Varillas producidas en esta hora", 0)
            if st.form_submit_button("REGISTRAR AVANCE"):
                nuevo = pd.DataFrame([{"Fecha":hoy, "Hora":datetime.now().strftime("%H:%M"), "Máquina":maq, "OP":op_h, "Varillas_Hora":vh}])
                guardar_datos(nuevo, "Seguimiento_Avance")
                st.rerun()

elif menu == "📊 HISTORIAL":
    st.header("Centro de Datos")
    t = st.selectbox("Seleccione Tabla para consultar:", ["Impresion", "Corte", "Colectoras", "Encuadernacion", "Seguimiento_Avance"])
    df = cargar_datos(t)
    st.dataframe(df, use_container_width=True)
    if not df.empty:
        st.download_button("Descargar Excel", df.to_csv(index=False), f"{t}.csv")
