import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from datetime import datetime
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA INTEGRAL PLANTA", page_icon="🏭")

# --- 2. ESTRUCTURA MAESTRA DE COLUMNAS ---
ESTRUCTURA_SISTEMA = {
    "Impresion": ["OP", "Fecha_Fin", "Máquina", "Nombre_Trabajo", "Marca_Papel", "Ancho_Bobina", "Gramaje", "Cant_Tintas", "Medida_Rollo", "Cant_Imagenes", "Hora_Inicio_T", "Hora_Final_T", "Total_Metros", "Rollos_Sacar", "Peso_Tinta", "Peso_Desperdicio", "Motivo_Desperdicio", "Observaciones"],
    "Corte": ["OP", "Fecha_Fin", "Máquina", "Nombre_Trabajo", "Marca_Papel", "Ancho_Bobina", "Gramaje", "Imagenes_Varilla", "Medida_Rollo", "Total_Varillas", "Unidades_Por_Caja", "Total_Rollos_Cortados", "Peso_Desperdicio", "Motivo_Desperdicio", "Observaciones", "Hora_Inicio_T", "Hora_Final_T"],
    "Colectoras": ["OP", "Fecha_Fin", "Máquina", "Nombre_Trabajo", "Marca_Papel", "Medida_Forma", "Unidades_Caja", "Hora_Inicio_T", "Hora_Final_T", "Total_Cajas", "Total_Formas", "Peso_Desperdicio", "Motivo_Desperdicio", "Observaciones"],
    "Encuadernacion": ["OP", "Fecha_Fin", "Nombre_Trabajo", "Cant_Formas", "Tipo_Material", "Medida_Forma", "Hora_Inicio_T", "Hora_Final_T", "Unid_Caja", "Cant_Final", "Tipo_Presentacion", "Peso_Desperdicio", "Motivo_Desperdicio", "Observaciones"],
    "Seguimiento_Avance": ["Fecha", "Hora_Registro", "Máquina", "OP", "Varillas_Hora", "Cajas_Hora"],
    "Metas_Config": ["Maquina", "Meta"]
}

# --- 3. FUNCIÓN DE CONEXIÓN (SEGURA PARA NUBE) ---
def conectar_nube():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = {
            "type": st.secrets["connections"]["gsheets"]["type"],
            "project_id": st.secrets["connections"]["gsheets"]["project_id"],
            "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
            "private_key": st.secrets["connections"]["gsheets"]["private_key"],
            "client_email": st.secrets["connections"]["gsheets"]["client_email"],
            "client_id": st.secrets["connections"]["gsheets"]["client_id"],
            "auth_uri": st.secrets["connections"]["gsheets"]["auth_uri"],
            "token_uri": st.secrets["connections"]["gsheets"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["connections"]["gsheets"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"],
        }
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        gc = gspread.authorize(creds)
        url_hoja = st.secrets["connections"]["gsheets"]["spreadsheet"]
        return gc.open_by_url(url_hoja)
    except Exception as e:
        st.error(f"Error crítico de conexión: {e}")
        return None

def obtener_tabla(nombre_tabla):
    sh = conectar_nube()
    if not sh: return pd.DataFrame()
    try:
        ws = sh.worksheet(nombre_tabla)
        return get_as_dataframe(ws).dropna(how='all').dropna(axis=1, how='all')
    except gspread.exceptions.WorksheetNotFound:
        columnas = ESTRUCTURA_SISTEMA[nombre_tabla]
        sh.add_worksheet(title=nombre_tabla, rows="1000", cols=str(len(columnas)))
        ws = sh.worksheet(nombre_tabla)
        df_ini = pd.DataFrame(columns=columnas)
        set_with_dataframe(ws, df_ini)
        return df_ini

def guardar_registro(df_nuevo, nombre_tabla):
    sh = conectar_nube()
    if sh:
        try:
            ws = sh.worksheet(nombre_tabla)
            df_actual = get_as_dataframe(ws).dropna(how='all').dropna(axis=1, how='all')
            df_final = pd.concat([df_actual, df_nuevo], ignore_index=True)
            set_with_dataframe(ws, df_final)
            st.success(f"✅ Sincronizado en {nombre_tabla}")
        except Exception as e:
            st.error(f"Error al guardar: {e}")

# --- 4. LISTAS ---
MAQUINAS_IMP = ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"]
MAQUINAS_CORTE = ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"]
MAQUINAS_COL = ["COL-01", "COL-02"]
PAPEL_LISTA = ["HANSOL", "KOEHLER", "APP", "BOND", "KRAFT", "PROPALCOTE", "PLASTIFICADO"]

# --- 5. LOGIN ---
USUARIOS = {
    "alexander": {"pass": "admin123", "rol": "admin", "vistas": ["⚙️ Configuración", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación", "⏱️ Seguimiento Cortadoras", "📊 Historial"]},
    "leonel": {"pass": "0321", "rol": "supervisor", "vistas": ["✂️ Corte", "⏱️ Seguimiento Cortadoras", "📊 Historial"]},
    "giovanny": {"pass": "1503", "rol": "supervisor", "vistas": ["🖨️ Impresión", "📥 Colectoras", "📊 Historial"]}
}

if "autenticado" not in st.session_state: st.session_state.autenticado = False
if not st.session_state.autenticado:
    st.title("🏭 CONTROL PLANTA - ACCESO NUBE")
    u = st.text_input("Usuario")
    p = st.text_input("Password", type="password")
    if st.button("ENTRAR"):
        if u in USUARIOS and USUARIOS[u]["pass"] == p:
            st.session_state.update({"autenticado":True, "usuario":u, "rol":USUARIOS[u]["rol"], "vistas":USUARIOS[u]["vistas"]})
            st.rerun()
    st.stop()

# --- 6. SIDEBAR ---
st.sidebar.title(f"Usuario: {st.session_state.usuario.capitalize()}")
menu = st.sidebar.radio("MENÚ", st.session_state.vistas)
if st.sidebar.button("Salir"):
    st.session_state.autenticado = False
    st.rerun()

# --- 7. MÓDULOS COMPLETOS ---

if menu == "⚙️ Configuración":
    st.header("⚙️ Configuración de Metas")
    df_m = obtener_tabla("Metas_Config")
    with st.form("f_metas"):
        meta_list = []
        c = st.columns(3)
        for i, m in enumerate(MAQUINAS_CORTE):
            val = df_m[df_m["Maquina"] == m]["Meta"].values[0] if not df_m.empty and m in df_m["Maquina"].values else 5000
            with c[i%3]:
                n_v = st.number_input(f"Meta {m}", value=int(val))
                meta_list.append({"Maquina": m, "Meta": n_v})
        if st.form_submit_button("ACTUALIZAR METAS"):
            guardar_registro(pd.DataFrame(meta_list), "Metas_Config")

elif menu == "🖨️ Impresión":
    st.header("🖨️ Módulo de Impresión")
    with st.form("f_imp"):
        c1, c2, c3 = st.columns(3)
        op, maq, tr = c1.text_input("OP"), c2.selectbox("Máquina", MAQUINAS_IMP), c3.text_input("Trabajo")
        pa, ab, gr = c1.selectbox("Papel", PAPEL_LISTA), c2.text_input("Ancho"), c3.text_input("Gramaje")
        tin, med, img = c1.number_input("Tintas", 0), c2.text_input("Medida"), c3.number_input("Imágenes", 0)
        hi, hf, met = c1.text_input("H. Inicio"), c2.text_input("H. Fin"), c3.number_input("Metros", 0)
        pd, mot = c1.number_input("Desp. Kg", 0.0), c2.text_input("Motivo")
        if st.form_submit_button("GUARDAR EN NUBE"):
            nuevo = pd.DataFrame([{"OP":op, "Fecha_Fin":datetime.now().strftime("%Y-%m-%d"), "Máquina":maq, "Nombre_Trabajo":tr, "Marca_Papel":pa, "Ancho_Bobina":ab, "Gramaje":gr, "Cant_Tintas":tin, "Medida_Rollo":med, "Cant_Imagenes":img, "Hora_Inicio_T":hi, "Hora_Final_T":hf, "Total_Metros":met, "Peso_Desperdicio":pd, "Motivo_Desperdicio":mot}])
            guardar_registro(nuevo, "Impresion")

elif menu == "✂️ Corte":
    st.header("✂️ Módulo de Corte")
    with st.form("f_corte"):
        c1, c2, c3 = st.columns(3)
        op, maq, tr = c1.text_input("OP"), c2.selectbox("Máquina", MAQUINAS_CORTE), c3.text_input("Trabajo")
        iv, mr, tv = c1.number_input("Imágenes x Varilla", 0), c2.text_input("Medida"), c3.number_input("Total Varillas", 0)
        uc, rc, pd = c1.number_input("Unid/Caja", 0), c2.number_input("Rollos Cortados", 0), c3.number_input("Desp. Kg", 0.0)
        hi, hf = c1.text_input("H. Inicio"), c2.text_input("H. Fin")
        if st.form_submit_button("GUARDAR EN NUBE"):
            nuevo = pd.DataFrame([{"OP":op, "Fecha_Fin":datetime.now().strftime("%Y-%m-%d"), "Máquina":maq, "Nombre_Trabajo":tr, "Imagenes_Varilla":iv, "Medida_Rollo":mr, "Total_Varillas":tv, "Unidades_Por_Caja":uc, "Total_Rollos_Cortados":rc, "Peso_Desperdicio":pd, "Hora_Inicio_T":hi, "Hora_Final_T":hf}])
            guardar_registro(nuevo, "Corte")

elif menu == "📥 Colectoras":
    st.header("📥 Módulo de Colectoras")
    with st.form("f_col"):
        c1, c2, c3 = st.columns(3)
        op, maq, tr = c1.text_input("OP"), c2.selectbox("Máquina", MAQUINAS_COL), c3.text_input("Trabajo")
        mf, uc, tc = c1.text_input("Medida Forma"), c2.number_input("Unid/Caja", 0), c3.number_input("Total Cajas", 0)
        if st.form_submit_button("GUARDAR EN NUBE"):
            nuevo = pd.DataFrame([{"OP":op, "Fecha_Fin":datetime.now().strftime("%Y-%m-%d"), "Máquina":maq, "Nombre_Trabajo":tr, "Medida_Forma":mf, "Unidades_Caja":uc, "Total_Cajas":tc}])
            guardar_registro(nuevo, "Colectoras")

elif menu == "📕 Encuadernación":
    st.header("📕 Módulo de Encuadernación")
    with st.form("f_enc"):
        c1, c2 = st.columns(2)
        op, tr = c1.text_input("OP"), c2.text_input("Trabajo")
        cf, tm = c1.number_input("Cant. Formas", 0), c2.text_input("Material")
        fin = c1.number_input("Cant. Final", 0)
        if st.form_submit_button("GUARDAR EN NUBE"):
            nuevo = pd.DataFrame([{"OP":op, "Fecha_Fin":datetime.now().strftime("%Y-%m-%d"), "Nombre_Trabajo":tr, "Cant_Formas":cf, "Tipo_Material":tm, "Cant_Final":fin}])
            guardar_registro(nuevo, "Encuadernacion")

elif menu == "⏱️ Seguimiento Cortadoras":
    st.header("⏱️ Seguimiento de Productividad")
    df_m = obtener_tabla("Metas_Config")
    df_a = obtener_tabla("Seguimiento_Avance")
    maq = st.selectbox("Máquina:", MAQUINAS_CORTE)
    meta = df_m[df_m["Maquina"] == maq]["Meta"].values[0] if not df_m.empty and maq in df_m["Maquina"].values else 5000
    prod = df_a[(df_a["Máquina"] == maq) & (df_a["Fecha"] == datetime.now().strftime("%Y-%m-%d"))]["Varillas_Hora"].sum()
    st.metric("TOTAL LOGRADO HOY", f"{prod} Varillas", delta=int(prod - meta))
    st.progress(min(prod/meta, 1.0) if meta > 0 else 0)
    with st.form("f_horario"):
        c1, c2, c3 = st.columns(3)
        op_h, v_h, c_h = c1.text_input("OP"), c2.number_input("Varillas", 0), c3.number_input("Cajas", 0)
        if st.form_submit_button("REGISTRAR HORA"):
            nuevo = pd.DataFrame([{"Fecha":datetime.now().strftime("%Y-%m-%d"), "Hora_Registro":datetime.now().strftime("%H:%M"), "Máquina":maq, "OP":op_h, "Varillas_Hora":v_h, "Cajas_Hora":c_h}])
            guardar_registro(nuevo, "Seguimiento_Avance")
            st.rerun()

elif menu == "📊 Historial":
    st.header("📊 Centro de Control de Datos")
    tabla = st.selectbox("Seleccione la hoja a inspeccionar:", list(ESTRUCTURA_SISTEMA.keys()))
    if st.button("🔄 Refrescar Datos de la Nube"):
        st.cache_data.clear()
    df_ver = obtener_tabla(tabla)
    st.dataframe(df_ver, use_container_width=True)
    st.download_button("📥 Descargar Reporte CSV", df_ver.to_csv(index=False), f"{tabla}.csv")
