import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# --- CONEXIÓN ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(layout="wide", page_title="SISTEMA PLANTA SUPABASE")

# --- FUNCIONES ---
def guardar_en_nube(tabla, datos):
    try:
        supabase.table(tabla).insert(datos).execute()
        st.success(f"✅ Guardado en Nube")
        st.balloons()
    except Exception as e:
        st.error(f"Error: {e}")

def obtener_datos(tabla):
    res = supabase.table(tabla).select("*").execute()
    return pd.DataFrame(res.data)

# --- MENÚ ---
menu = st.sidebar.radio("MENÚ", ["🖨️ IMPRESIÓN", "✂️ CORTE", "📊 HISTORIAL Y DESCARGA"])

if menu == "🖨️ IMPRESIÓN":
    st.header("Módulo de Impresión")
    # ... (Aquí van tus campos de texto como OP, Trabajo, etc.) ...
    with st.form("f_imp"):
        op = st.text_input("OP")
        tr = st.text_input("Trabajo")
        # Al final del formulario:
        if st.form_submit_button("ENVIAR A NUBE"):
            datos = {"op": op, "trabajo": tr, "fecha": str(datetime.now().date())} # Ejemplo
            guardar_en_nube("impresion", datos)

elif menu == "📊 HISTORIAL Y DESCARGA":
    st.header("Panel de Administración")
    t = st.selectbox("Seleccione Tabla para descargar:", ["impresion", "corte", "seguimiento_avance"])
    
    df = obtener_datos(t)
    
    if not df.empty:
        st.write(f"Registros encontrados: {len(df)}")
        st.dataframe(df)
        
        # BOTÓN MÁGICO PARA TU PC
        @st.cache_data
        def convertir_excel(df_descarga):
            return df_descarga.to_csv(index=False).encode('utf-8')

        csv = convertir_excel(df)
        st.download_button(
            label="📥 DESCARGAR DATOS PARA MI EXCEL",
            data=csv,
            file_name=f"datos_{t}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv',
            use_container_width=True
        )
    else:
        st.warning("No hay datos en esta tabla todavía.")
