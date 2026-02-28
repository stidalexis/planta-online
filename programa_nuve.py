import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import io

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V11", page_icon="🏭")
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTADOS DE SESIÓN ---
if 'url_arte' not in st.session_state: st.session_state.url_arte = None

# --- LÓGICA DE FLUJO POR PREFIJO ---
FLUJO = {
    "RB": ["CORTE", "FINALIZADO"],
    "RI": ["IMPRESIÓN", "CORTE", "FINALIZADO"],
    "FRI": ["IMPRESIÓN", "COLECTORAS", "ENCUADERNACIÓN", "FINALIZADO"],
    "FRB": ["IMPRESIÓN", "COLECTORAS", "ENCUADERNACIÓN", "FINALIZADO"]
}

MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11"],
    "CORTE": ["COR-01", "COR-02", "COR-03"],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": ["LINEA-01", "LINEA-02"]
}

# --- FUNCIONES DE APOYO ---
def avanzar_area(op_id, prefijo, area_actual):
    ruta = FLUJO.get(prefijo, [])
    if area_actual in ruta:
        nueva_idx = ruta.index(area_actual) + 1
        nueva_area = ruta[nueva_idx]
        estado = "Terminado" if nueva_area == "FINALIZADO" else "En Proceso"
        supabase.table("ordenes_planeadas").update({"proxima_area": nueva_area, "estado": estado}).eq("op", op_id).execute()

# --- INTERFAZ: MENÚ LATERAL ---
with st.sidebar:
    st.title("🏭 NUVE V11")
    menu = st.radio("MÓDULOS", ["🖥️ MONITOR", "🔍 SEGUIMIENTO", "📅 PLANIFICACIÓN"])
    st.divider()
    st.subheader("🛠️ ÁREAS DE PRODUCCIÓN")
    area_menu = st.radio("IR A:", ["🖨️ IMPRESIÓN", "✂️ CORTE", "📥 COLECTORAS", "📕 ENCUADERNACIÓN"])

# --- MÓDULO: PLANIFICACIÓN ---
if menu == "📅 PLANIFICACIÓN":
    st.header("📅 Registro de Nueva Orden")
    cols = st.columns(4)
    if cols[0].button("RI"): st.session_state.pref = "RI"
    if cols[1].button("RB"): st.session_state.pref = "RB"
    if cols[2].button("FRI"): st.session_state.pref = "FRI"
    if cols[3].button("FRB"): st.session_state.pref = "FRB"

    if 'pref' in st.session_state:
        pref = st.session_state.pref
        st.subheader(f"Formulario: {pref}")
        
        # Cargador de Arte (Corregido: no bloquea)
        archivo = st.file_uploader("Subir Arte (Opcional)", type=["pdf", "png", "jpg"])
        if archivo:
            if st.button("Validar y Subir Archivo"):
                with st.spinner("Subiendo..."):
                    path = f"artes/{int(time.time())}_{archivo.name}"
                    supabase.storage.from_("artes").upload(path, archivo.getvalue())
                    st.session_state.url_arte = supabase.storage.from_("artes").get_public_url(path)
                    st.success("Archivo listo!")

        with st.form("form_op"):
            c1, c2, c3 = st.columns(3)
            op_n = c1.text_input("Número OP")
            cli = c2.text_input("Cliente")
            tra = c3.text_input("Trabajo")
            
            # Datos técnicos según prefijo
            core, desde, hasta = "N/A", "N/A", "N/A"
            if "R" in pref:
                core = st.selectbox("Core", ["13mm", "19mm", "1 pulg", "3 pulg"])
            else:
                d1, d2 = st.columns(2)
                desde = d1.text_input("Desde")
                hasta = d2.text_input("Hasta")
            
            if st.form_submit_button("REGISTRAR ORDEN"):
                area_ini = FLUJO[pref][0]
                data = {
                    "op": f"{pref}-{op_n}".upper(), "nombre_cliente": cli, "trabajo": tra,
                    "tipo_acabado": pref, "proxima_area": area_ini, "core": core,
                    "num_desde": desde, "num_hasta": hasta, "url_arte": st.session_state.url_arte
                }
                supabase.table("ordenes_planeadas").insert(data).execute()
                st.session_state.url_arte = None
                st.success("Orden Creada")

# --- MÓDULO: ÁREAS (LÓGICA GENÉRICA) ---
def render_area(nombre_area):
    st.header(f"Área: {nombre_area}")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", nombre_area).execute().data}
    
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS[nombre_area]):
        with cols[i%4]:
            if m in activos:
                t = activos[m]
                st.error(f"● {m} - {t['op']}")
                if st.button(f"Reportar {m}", key=f"rep_{m}"):
                    st.session_state.m_rep = t
            else:
                st.success(f"○ {m} - LIBRE")
                ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", nombre_area).execute().data
                if ops:
                    op_sel = st.selectbox(f"OP para {m}", [o['op'] for o in ops], key=f"sel_{m}")
                    if st.button(f"Iniciar {m}", key=f"btn_{m}"):
                        d = next(o for o in ops if o['op'] == op_sel)
                        supabase.table("trabajos_activos").insert({"maquina": m, "area": nombre_area, "op": d['op'], "trabajo": d['trabajo'], "hora_inicio": datetime.now().strftime("%H:%M")}).execute()
                        st.rerun()

    # Formulario de Reporte Técnico (Emergente si se selecciona máquina)
    if 'm_rep' in st.session_state:
        t = st.session_state.m_rep
        with st.expander(f"FINALIZAR TRABAJO: {t['op']}", expanded=True):
            with st.form("form_tecnico"):
                st.write("Datos de Producción")
                op_n = st.text_input("Operario")
                dato_extra = st.number_input("Metros / Unidades Finales", 0)
                parcial = st.checkbox("¿Es entrega Parcial?")
                
                c1, c2 = st.columns(2)
                if c1.form_submit_button("🏁 FINALIZAR Y ENVIAR"):
                    # Guardar en historial de área
                    supabase.table(f"reporte_{nombre_area.lower().replace('ó','o')}").insert({"op": t['op'], "maquina": t['maquina'], "operario": op_n, "metros": dato_extra, "tipo_entrega": "PARCIAL" if parcial else "FINAL"}).execute()
                    
                    if not parcial:
                        avanzar_area(t['op'], t['op'].split("-")[0], nombre_area)
                    
                    supabase.table("trabajos_activos").delete().eq("maquina", t['maquina']).execute()
                    del st.session_state.m_rep
                    st.rerun()
                
                if c2.form_submit_button("🚨 PARADA DE EMERGENCIA"):
                    supabase.table("trabajos_activos").update({"estado_maquina": "PARADA", "h_parada": datetime.now().strftime("%H:%M")}).eq("maquina", t['maquina']).execute()
                    st.rerun()

# --- RENDERIZADO DE ÁREAS ---
if area_menu == "🖨️ IMPRESIÓN": render_area("IMPRESIÓN")
elif area_menu == "✂️ CORTE": render_area("CORTE")
elif area_menu == "📥 COLECTORAS": render_area("COLECTORAS")
elif area_menu == "📕 ENCUADERNACIÓN": render_area("ENCUADERNACIÓN")

# --- MÓDULO: SEGUIMIENTO (CONSOLIDADO) ---
if menu == "🔍 SEGUIMIENTO":
    st.header("🔍 Seguimiento de Órdenes")
    ops = supabase.table("ordenes_planeadas").select("*").execute().data
    if ops:
        for o in ops:
            with st.expander(f"OP: {o['op']} - {o['nombre_cliente']}"):
                st.write(f"**Estado:** {o['estado']} | **Ubicación:** {o['proxima_area']}")
                st.write("**Datos Iniciales:**", o)
                
                # Buscar reportes de todas las áreas para esta OP
                for area in ["impresion", "corte", "colectoras"]:
                    rep = supabase.table(f"reporte_{area}").select("*").eq("op", o['op']).execute().data
                    if rep: st.write(f"**Reporte {area.upper()}:**", rep)
