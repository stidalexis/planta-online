import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

st.set_page_config(layout="wide", page_title="SISTEMA DE PLANTA V2")

# --- CONFIGURACIÓN DE MÁQUINAS ---
MAQUINAS_IMP = ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"]
MAQUINAS_CORTE = ["COR-01", "COR-02", "COR-03", "COR-04", "COR-05", "COR-06", "COR-07", "COR-08", "COR-09", "COR-10", "COR-11", "COR-12", "COR-PP-01", "COR-PP-02"]

# --- FUNCIONES DE APOYO ---
def cargar_datos(tabla):
    try:
        return pd.DataFrame(supabase.table(tabla).select("*").execute().data)
    except:
        return pd.DataFrame()

def render_maquinas(lista, df_p, prefix):
    cols = st.columns(len(lista))
    for i, m in enumerate(lista):
        ocupada = not df_p.empty and m in df_p["maquina"].values
        color = "🟢" if not ocupada else "🔴"
        if cols[i].button(f"{color}\n{m}", key=f"{prefix}_{m}"):
            st.session_state[f"sel_{prefix}"] = m

# --- INTERFAZ PRINCIPAL ---
menu = st.sidebar.radio("ÁREAS", ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])
df_paradas = cargar_datos("paradas_emergencia")

# --- MÓDULO IMPRESIÓN ---
if menu == "🖨️ Impresión":
    df_p_imp = cargar_datos("pendientes_imp")
    render_maquinas(MAQUINAS_IMP, df_p_imp, "imp")
    maq = st.session_state.get("sel_imp")
    
    if maq:
        st.divider(); st.subheader(f"⚙️ Máquina: {maq}")
        es_p = not df_paradas.empty and maq in df_paradas[df_paradas["estado"]=="Activa"]["maquina"].values
        actual = df_p_imp[df_p_imp["maquina"] == maq] if not df_p_imp.empty else pd.DataFrame()
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if actual.empty and not es_p:
                with st.form("f_imp_i"):
                    st.write("🟢 INICIAR TRABAJO")
                    op, nom = st.text_input("OP"), st.text_input("Nombre")
                    pap, anc = st.text_input("Tipo de Papel"), st.text_input("Ancho")
                    gra, med = st.text_input("Gramaje"), st.text_input("Medida de Trabajo")
                    if st.form_submit_button("REGISTRAR INICIO"):
                        supabase.table("pendientes_imp").insert({"maquina":maq, "op":op, "nombre":nom, "papel":pap, "ancho":anc, "gramaje":gra, "medida":med, "hora_i":datetime.now().strftime("%H:%M")}).execute()
                        st.rerun()
            elif es_p: st.error("🚨 MÁQUINA EN PARADA")
            else: st.success(f"TRABAJANDO: {actual.iloc[0]['nombre']}")

        with c2:
            if not actual.empty and not es_p:
                with st.form("f_imp_f"):
                    st.write("🏁 FINALIZAR TRABAJO")
                    met, bob = st.number_input("Metros Impresos", 0), st.number_input("Bobinas", 0)
                    des, mot = st.number_input("Peso Desperdicio (Kg)", 0.0), st.text_input("Motivo Desperdicio")
                    obs = st.text_area("Observaciones")
                    if st.form_submit_button("CERRAR"):
                        row = actual.iloc[0]
                        supabase.table("impresion").insert({"op":row['op'], "nombre":row['nombre'], "metros_impresos":met, "bobinas":bob, "peso_desperdicio":des, "motivo_desperdicio":mot, "observaciones":obs}).execute()
                        supabase.table("pendientes_imp").delete().eq("maquina", maq).execute()
                        st.rerun()
        with c3:
            if es_p:
                if st.button("✅ REANUDAR"):
                    id_p = df_paradas[(df_paradas["maquina"]==maq) & (df_paradas["estado"]=="Activa")].iloc[0]['id']
                    supabase.table("paradas_emergencia").update({"estado":"Finalizada"}).eq("id", id_p).execute()
                    st.rerun()
            else:
                if st.button("🚨 PARADA DE EMERGENCIA"):
                    supabase.table("paradas_emergencia").insert({"maquina":maq, "estado":"Activa", "hora_inicio":datetime.now().strftime("%H:%M")}).execute()
                    st.rerun()

# --- MÓDULO CORTE ---
elif menu == "✂️ Corte":
    df_p_cor = cargar_datos("pendientes_cor")
    render_maquinas(MAQUINAS_CORTE, df_p_cor, "cor")
    maq = st.session_state.get("sel_cor")
    if maq:
        st.divider(); st.subheader(f"⚙️ Máquina: {maq}")
        actual = df_p_cor[df_p_cor["maquina"] == maq] if not df_p_cor.empty else pd.DataFrame()
        c1, c2, c3 = st.columns(3)
        with c1:
            if actual.empty:
                with st.form("f_cor_i"):
                    st.write("🟢 INICIAR")
                    op, nom = st.text_input("OP"), st.text_input("Nombre")
                    pap, anc = st.text_input("Tipo de Papel"), st.text_input("Ancho")
                    gra, imv = st.text_input("Gramaje"), st.number_input("Imagenes*Varilla", 0)
                    med_r = st.text_input("Medida de Rollos a Sacar")
                    if st.form_submit_button("INICIAR"):
                        supabase.table("pendientes_cor").insert({"maquina":maq, "op":op, "nombre":nom, "papel":pap, "ancho":anc, "gramaje":gra, "img_varilla":imv, "medida_rollos":med_r}).execute()
                        st.rerun()
        with c2:
            if not actual.empty:
                with st.form("f_cor_f"):
                    st.write("🏁 FINALIZAR")
                    var, uc = st.number_input("Cantidad de Varillas", 0), st.number_input("Unidades*Caja", 0)
                    t_r, des = st.number_input("Total Rollos Cortados", 0), st.number_input("Peso Desperdicio", 0.0)
                    mot, obs = st.text_input("Motivo Desperdicio"), st.text_area("Observaciones")
                    if st.form_submit_button("CERRAR"):
                        row = actual.iloc[0]
                        supabase.table("corte").insert({"op":row['op'], "nombre":row['nombre'], "cant_varillas":var, "unidades_caja":uc, "total_rollos":t_r, "peso_desperdicio":des, "motivo_desperdicio":mot, "observaciones":obs}).execute()
                        supabase.table("pendientes_cor").delete().eq("maquina", maq).execute()
                        st.rerun()

# --- MÓDULO ENCUADERNACIÓN ---
elif menu == "📕 Encuadernación":
    df_p_enc = cargar_datos("pendientes_enc")
    st.subheader("📦 Encuadernación / Manual")
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("f_enc_i"):
            st.write("🟢 INICIAR")
            op, nom = st.text_input("OP"), st.text_input("Nombre")
            f_t, mat = st.number_input("Formas Totales", 0), st.text_input("Material")
            med = st.text_input("Medida")
            if st.form_submit_button("REGISTRAR INICIO"):
                supabase.table("pendientes_enc").insert({"op":op, "nombre":nom, "formas_totales":f_t, "material":mat, "medida":med, "hora_i":datetime.now().strftime("%H:%M")}).execute()
                st.rerun()
    with c2:
        if not df_p_enc.empty:
            for idx, row in df_p_enc.iterrows():
                with st.expander(f"OP: {row['op']} - {row['nombre']}"):
                    with st.form(f"f_enc_f_{idx}"):
                        c_f, pres = st.number_input("Cantidad Final", 0), st.text_input("Presentación")
                        des, obs = st.number_input("Desperdicio", 0.0), st.text_area("Observaciones")
                        if st.form_submit_button("CERRAR TRABAJO"):
                            supabase.table("encuadernacion").insert({"op":row['op'], "nombre":row['nombre'], "cant_final":c_f, "presentacion":pres, "desperdicio":des, "observaciones":obs}).execute()
                            supabase.table("pendientes_enc").delete().eq("op", row['op']).execute()
                            st.rerun()

# --- MÓDULO COLECTORAS ---
elif menu == "📥 Colectoras":
    st.subheader("📊 Registro Directo de Colectoras")
    with st.form("f_col_direct"):
        c1, c2 = st.columns(2)
        op, nom = c1.text_input("OP"), c2.text_input("Nombre")
        pap, pre = c1.text_input("Tipo Papel"), c2.text_input("Presentación")
        des, mot = c1.number_input("Desperdicio", 0.0), c2.text_input("Motivo de Desperdicio")
        obs = st.text_area("Observaciones")
        if st.form_submit_button("GUARDAR REGISTRO"):
            supabase.table("colectoras").insert({"op":op, "nombre":nom, "tipo_papel":pap, "presentacion":pre, "desperdicio":des, "motivo_desperdicio":mot, "observaciones":obs}).execute()
            st.success("✅ Datos guardados correctamente")
