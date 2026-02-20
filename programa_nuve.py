import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN Y CONEXIÓN ---
# Reemplaza con tus credenciales o usa st.secrets
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="SISTEMA DE PRODUCCIÓN - ENSAYOS")

# --- VARIABLES DE CONFIGURACIÓN ---
MARCAS_PAPEL = ["Bond 75g", "Químico CB", "Químico CFB", "Químico CF", "Cartulina 180g"]
MAQUINAS_IMP = ["HR-22", "ATF-22", "HR-17", "DID-11"]
MAQUINAS_CORTE = ["COR-01", "COR-02", "COR-PP-01"]
MAQUINAS_COL = ["COL-01", "COL-02"]

# --- FUNCIONES CORE ---
def cargar_datos(tabla):
    try:
        res = supabase.table(tabla).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

def render_maquinas(lista, df_pendientes, prefix):
    # Simulación simple de tu función visual
    cols = st.columns(len(lista))
    for i, m in enumerate(lista):
        esta_ocupada = not df_pendientes.empty and m in df_pendientes["maquina"].values
        color = "🟢" if not esta_ocupada else "🔴"
        if cols[i].button(f"{color} {m}", key=f"btn_{prefix}_{m}"):
            st.session_state[f"sel_{prefix}"] = m

# --- LÓGICA DE INTERFAZ ---
menu = st.sidebar.radio("MENÚ PRODUCCIÓN", ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])
df_paradas = cargar_datos("paradas_emergencia")

# 1. MÓDULO IMPRESIÓN
if menu == "🖨️ Impresión":
    df_p_imp = cargar_datos("pendientes_imp")
    render_maquinas(MAQUINAS_IMP, df_p_imp, "imp")
    maq = st.session_state.get("sel_imp")
    
    if maq:
        st.divider()
        st.subheader(f"⚙️ Máquina: {maq}")
        es_p = not df_paradas.empty and maq in df_paradas[df_paradas["estado"]=="Activa"]["maquina"].values
        actual = df_p_imp[df_p_imp["maquina"] == maq] if not df_p_imp.empty else pd.DataFrame()
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if actual.empty and not es_p:
                with st.form("f_i_i", clear_on_submit=True):
                    st.write("🟢 Registrar Inicio")
                    op, tr = st.text_input("OP"), st.text_input("Trabajo")
                    pa = st.selectbox("Papel", MARCAS_PAPEL)
                    an, gr = st.text_input("Ancho"), st.text_input("Gramaje")
                    ti, me, im = st.number_input("Tintas", 0), st.text_input("Medida"), st.number_input("Imágenes", 0)
                    if st.form_submit_button("REGISTRAR INICIO"):
                        data = {"op":str(op), "maquina":maq, "hora_i":datetime.now().strftime("%H:%M:%S"), "fecha_i":datetime.now().strftime("%Y-%m-%d"), "nombre_trabajo":tr, "marca_papel":pa, "ancho_bobina":an, "gramaje":gr, "cant_tintas":ti, "medida_rollo":me, "cant_imagenes":im}
                        supabase.table("pendientes_imp").insert(data).execute()
                        st.rerun()
            elif es_p: st.warning("MÁQUINA EN PARADA DE EMERGENCIA")
            else: st.success(f"OP {actual.iloc[0]['op']} en curso")

        with c2:
            if not actual.empty and not es_p:
                with st.form("f_i_f"):
                    st.write("🏁 Registrar Cierre")
                    m_val, r_val = st.number_input("Metros", 0), st.number_input("Rollos", 0)
                    pt, pd_ = st.number_input("P. Tinta", 0), st.number_input("P. Desp.", 0)
                    mo, ob = st.text_input("Motivo"), st.text_area("Observaciones")
                    if st.form_submit_button("FINALIZAR TRABAJO"):
                        row = actual.iloc[0]
                        final = {"op":str(row['op']), "fecha_fin":datetime.now().strftime("%Y-%m-%d"), "maquina":maq, "nombre_trabajo":row['nombre_trabajo'], "marca_papel":row['marca_papel'], "hora_inicio_t":row['hora_i'], "hora_final_t":datetime.now().strftime("%H:%M:%S"), "total_metros":m_val, "rollos_sacar":r_val, "peso_tinta":pt, "peso_desperdicio":pd_, "motivo_desperdicio":mo, "observaciones":ob}
                        supabase.table("impresion").insert(final).execute()
                        supabase.table("pendientes_imp").delete().eq("maquina", maq).execute()
                        st.rerun()

        with c3:
            if es_p:
                if st.button("✅ REANUDAR MÁQUINA"):
                    id_p = df_paradas[(df_paradas["maquina"]==maq) & (df_paradas["estado"]=="Activa")].iloc[0]['id']
                    supabase.table("paradas_emergencia").update({"estado":"Finalizada"}).eq("id", id_p).execute()
                    st.rerun()
            else:
                with st.form("f_i_p"):
                    st.write("🚨 Reportar Parada")
                    mot = st.selectbox("Motivo", ["Falla Mecánica", "Mantenimiento", "Falta Material", "Limpieza"])
                    if st.form_submit_button("SUSPENDER MÁQUINA"):
                        supabase.table("paradas_emergencia").insert({"maquina":maq, "fecha":datetime.now().strftime("%Y-%m-%d"), "hora_inicio":datetime.now().strftime("%H:%M:%S"), "motivo":mot, "estado":"Activa"}).execute()
                        st.rerun()

# 2. MÓDULO CORTE (Resumen de lógica igual a Impresión)
elif menu == "✂️ Corte":
    df_p_cor = cargar_datos("pendientes_corte")
    render_maquinas(MAQUINAS_CORTE, df_p_cor, "cor")
    maq = st.session_state.get("sel_cor")
    if maq:
        st.divider(); st.subheader(f"⚙️ Máquina: {maq}")
        es_p = not df_paradas.empty and maq in df_paradas[df_paradas["estado"]=="Activa"]["maquina"].values
        actual = df_p_cor[df_p_cor["maquina"] == maq] if not df_p_cor.empty else pd.DataFrame()
        c1, c2, c3 = st.columns(3)
        with c1:
            if actual.empty and not es_p:
                with st.form("f_c_i"):
                    st.write("🟢 Registrar Inicio")
                    op, tr = st.text_input("OP"), st.text_input("Trabajo")
                    iv, me = st.number_input("Img/Var", 0), st.text_input("Medida")
                    if st.form_submit_button("REGISTRAR INICIO"):
                        supabase.table("pendientes_corte").insert({"op":str(op), "maquina":maq, "hora_i":datetime.now().strftime("%H:%M:%S"), "nombre_trabajo":tr, "imagenes_varilla":iv, "medida_rollo":me}).execute()
                        st.rerun()
            elif es_p: st.warning("MÁQUINA EN PARADA")
            else: st.success(f"OP {actual.iloc[0]['op']} en curso")
        with c2:
            if not actual.empty and not es_p:
                with st.form("f_c_f"):
                    st.write("🏁 Cierre")
                    vt, uc = st.number_input("Varillas", 0), st.number_input("Unid/Caja", 0)
                    if st.form_submit_button("FINALIZAR"):
                        row = actual.iloc[0]
                        supabase.table("corte").insert({"op":row['op'], "maquina":maq, "total_varillas":vt, "unidades_por_caja":uc, "hora_inicio_t":row['hora_i'], "hora_final_t":datetime.now().strftime("%H:%M:%S")}).execute()
                        supabase.table("pendientes_corte").delete().eq("maquina", maq).execute()
                        st.rerun()

# 3. MÓDULO ENCUADERNACIÓN (Lógica especial de Expander)
elif menu == "📕 Encuadernación":
    df_p_enc = cargar_datos("pendientes_enc")
    st.subheader("📦 Manual / Encuadernación")
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("f_e_i"):
            st.write("🟢 Iniciar OP")
            op, tr = st.text_input("OP"), st.text_input("Trabajo")
            cf = st.number_input("Formas", 0)
            if st.form_submit_button("REGISTRAR INICIO"):
                supabase.table("pendientes_enc").insert({"op":str(op), "hora_i":datetime.now().strftime("%H:%M:%S"), "nombre_trabajo":tr, "cant_formas":cf}).execute()
                st.rerun()
    with c2:
        st.write("🏁 Trabajos en Curso")
        if not df_p_enc.empty:
            for idx, row in df_p_enc.iterrows():
                with st.expander(f"OP: {row['op']} - {row['nombre_trabajo']}"):
                    with st.form(f"f_e_f_{row['op']}"):
                        cf_final = st.number_input("Cant. Final", 0, key=f"c{idx}")
                        if st.form_submit_button("CERRAR TRABAJO"):
                            supabase.table("encuadernacion").insert({"op":row['op'], "nombre_trabajo":row['nombre_trabajo'], "cant_final":cf_final, "hora_inicio_t":row['hora_i'], "hora_final_t":datetime.now().strftime("%H:%M:%S")}).execute()
                            supabase.table("pendientes_enc").delete().eq("op", row['op']).execute()
                            st.rerun()
