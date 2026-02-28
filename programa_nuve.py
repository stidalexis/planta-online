import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V12", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES ORIGINALES ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #1a1a1a; color: white; }
    .stButton > button { height: 50px !important; border-radius: 8px; font-weight: bold; width: 100%; }
    .card-produccion { background-color: #2ecc71; border: 2px solid #27ae60; padding: 15px; border-radius: 12px; text-align: center; color: white; margin-bottom:10px;}
    .card-parada { background-color: #e74c3c; border: 2px solid #c0392b; padding: 15px; border-radius: 12px; text-align: center; color: white; margin-bottom:10px;}
    .card-vacia { background-color: #ecf0f1; border: 1px solid #bdc3c7; padding: 15px; border-radius: 12px; text-align: center; color: #7f8c8d; margin-bottom:10px;}
    .area-header { background-color: #2980b9; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin-bottom:15px;}
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE FLUJOS Y MÁQUINAS ---
FLUJOS = {
    "RI": ["IMPRESIÓN", "CORTE", "FINALIZADO"],
    "RB": ["CORTE", "FINALIZADO"],
    "FRI": ["IMPRESIÓN", "COLECTORAS", "ENCUADERNACIÓN", "FINALIZADO"],
    "FRB": ["IMPRESIÓN", "COLECTORAS", "ENCUADERNACIÓN", "FINALIZADO"]
}

MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- FUNCIONES DE LÓGICA ---
def avanzar_proceso(op_full, area_actual):
    pref = op_full.split("-")[0]
    ruta = FLUJOS.get(pref, [])
    if area_actual in ruta:
        idx = ruta.index(area_actual)
        siguiente = ruta[idx + 1]
        estado = "Terminado" if siguiente == "FINALIZADO" else "En Proceso"
        supabase.table("ordenes_planeadas").update({"proxima_area": siguiente, "estado": estado}).eq("op", op_full).execute()

# --- MENÚ LATERAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2622/2622267.png", width=80)
    st.title("SISTEMA NUVE")
    mod_principal = st.radio("PRINCIPAL", ["🖥️ MONITOR", "🔍 SEGUIMIENTO", "📅 PLANIFICACIÓN"])
    st.divider()
    st.subheader("ÁREAS")
    mod_area = st.radio("MODULOS DE ÁREA", ["🖨️ IMPRESIÓN", "✂️ CORTE", "📥 COLECTORAS", "📕 ENCUADERNACIÓN"])

# --- 1. MONITOR ---
if mod_principal == "🖥️ MONITOR":
    st.title("Monitor de Planta")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    for area, lista in MAQUINAS.items():
        st.markdown(f"<div class='area-header'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for i, m in enumerate(lista):
            with cols[i%4]:
                if m in act:
                    clase = "card-produccion" if act[m]['estado_maquina'] == "PRODUCIENDO" else "card-parada"
                    st.markdown(f"<div class='{clase}'><b>{m}</b><br>{act[m]['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'><b>{m}</b><br>LIBRE</div>", unsafe_allow_html=True)
    time.sleep(15); st.rerun()

# --- 2. SEGUIMIENTO ---
elif mod_principal == "🔍 SEGUIMIENTO":
    st.title("Seguimiento de Órdenes")
    data = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df[['op', 'nombre_cliente', 'trabajo', 'proxima_area', 'estado']], use_container_width=True)
        
        # Historial técnico consolidado
        sel_op = st.selectbox("Ver detalle técnico de:", [d['op'] for d in data])
        reps = supabase.table("reportes_produccion").select("*").eq("op", sel_op).execute().data
        if reps:
            st.table(pd.DataFrame(reps)[['fecha', 'area', 'maquina', 'operario', 'cantidad_reportada', 'tipo_entrega']])
            
# --- 3. PLANIFICACIÓN ---
elif mod_principal == "📅 PLANIFICACIÓN":
    st.title("📅 Nueva Orden de Producción")
    
    # Botones de Prefijo
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("RI (Rollo Impreso)"): st.session_state.pref = "RI"
    if c2.button("RB (Rollo Blanco)"): st.session_state.pref = "RB"
    if c3.button("FRI (Forma Impresa)"): st.session_state.pref = "FRI"
    if c4.button("FRB (Forma Blanca)"): st.session_state.pref = "FRB"

    if "pref" in st.session_state:
        pref = st.session_state.pref
        
        # Subida de arte corregida
        archivo = st.file_uploader("🖼️ Cargar Arte", type=["pdf", "png", "jpg"])
        if archivo:
            if st.button("Subir Arte"):
                with st.spinner("Subiendo..."):
                    path = f"artes/{int(time.time())}_{archivo.name}"
                    supabase.storage.from_("artes").upload(path, archivo.getvalue())
                    st.session_state.url_temp = supabase.storage.from_("artes").get_public_url(path)
                    st.success("Arte cargado con éxito")

        with st.form("form_alta"):
            st.subheader(f"Formulario Original - {pref}")
            col1, col2, col3 = st.columns(3)
            op_num = col1.text_input("Número OP")
            vendedor = col2.text_input("Vendedor")
            cliente = col3.text_input("Cliente")
            trabajo = st.text_input("Nombre del Trabajo")
            
            f1, f2, f3 = st.columns(3)
            material = f1.text_input("Papel / Material")
            medida = f2.text_input("Medida")
            cantidad = f3.number_input("Cantidad Solicitada", 0)
            
            core, bolsa, caja, desde, hasta, copias = "N/A", 0, 0, "N/A", "N/A", "N/A"
            if "R" in pref:
                t1, t2, t3 = st.columns(3)
                core = t1.selectbox("Core", ["13MM", "19MM", "1 PULG", "3 PULG"])
                bolsa = t2.number_input("Unds/Bolsa", 0)
                caja = t3.number_input("Unds/Caja", 0)
            else:
                t1, t2, t3 = st.columns(3)
                desde = t1.text_input("Desde")
                hasta = t2.text_input("Hasta")
                copias = t3.selectbox("Copias", ["1", "2", "3", "4"])

            tintas = st.number_input("Número de Tintas", 0) if "I" in pref else 0
            obs = st.text_area("Observaciones")
            
            if st.form_submit_button("🚀 REGISTRAR"):
                # Determinar área inicial según flujo
                area_inicial = FLUJOS[pref][0]
                
                payload = {
                    "op": f"{pref}-{op_num}".upper(), "nombre_cliente": cliente, "trabajo": trabajo,
                    "vendedor": vendedor, "tipo_acabado": pref, "material": material, "ancho_medida": medida,
                    "unidades_solicitadas": int(cantidad), "cant_tintas": int(tintas),
                    "proxima_area": area_inicial, "observaciones": obs, "url_arte": st.session_state.get('url_temp'),
                    "core": core, "unidades_bolsa": bolsa, "unidades_caja": caja,
                    "num_desde": desde, "num_hasta": hasta, "copias": copias
                }
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.success("Orden Guardada"); st.session_state.url_temp = None

# --- LÓGICA DE ÁREA INDEPENDIENTE ---
def gestionar_area(nombre_area):
    st.title(f"Módulo de {nombre_area}")
    
    # 1. Máquinas Activas
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", nombre_area).execute().data}
    cols = st.columns(4)
    for i, m in enumerate(MAQUINAS[nombre_area]):
        btn_txt = f"🔴 {m}" if m in act else f"⚪ {m}"
        if cols[i%4].button(btn_txt, key=m):
            st.session_state.m_sel = m
            st.session_state.area_sel = nombre_area

    # 2. Panel de Control de la Máquina
    if "m_sel" in st.session_state and st.session_state.area_sel == nombre_area:
        m = st.session_state.m_sel
        st.divider()
        if m in act:
            t = act[m]
            st.subheader(f"Control de {m} - OP: {t['op']}")
            
            with st.form(f"form_reporte_{m}"):
                operario = st.text_input("Operario")
                cantidad = st.number_input("Cantidad Producida", 0)
                desp = st.number_input("Kilos Desperdicio", 0.0)
                parcial = st.checkbox("¿Entrega PARCIAL?")
                
                c1, c2 = st.columns(2)
                if c1.form_submit_button("🏁 FINALIZAR"):
                    # Registrar Historial
                    supabase.table("reportes_produccion").insert({
                        "op": t['op'], "area": nombre_area, "maquina": m, 
                        "operario": operario, "cantidad_reportada": cantidad,
                        "kilos_desp": desp, "tipo_entrega": "PARCIAL" if parcial else "FINAL"
                    }).execute()
                    
                    # Avanzar flujo si es final
                    if not parcial:
                        avanzar_proceso(t['op'], nombre_area)
                    
                    supabase.table("trabajos_activos").delete().eq("maquina", m).execute()
                    st.rerun()
                
                if c2.form_submit_button("🚨 PARADA"):
                    supabase.table("trabajos_activos").update({"estado_maquina": "PARADA"}).eq("maquina", m).execute()
                    st.rerun()
        else:
            # Seleccionar nueva OP
            ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", nombre_area).execute().data
            if ops:
                sel = st.selectbox("Seleccione OP:", [o['op'] for o in ops])
                if st.button(f"Iniciar {m}"):
                    d = next(o for o in ops if o['op'] == sel)
                    supabase.table("trabajos_activos").insert({
                        "maquina": m, "area": nombre_area, "op": d['op'], 
                        "trabajo": d['trabajo'], "hora_inicio": datetime.now().strftime("%H:%M")
                    }).execute()
                    st.rerun()
            else: st.warning("Sin órdenes pendientes.")

# --- RENDER DE ÁREAS ---
if mod_area == "🖨️ IMPRESIÓN": gestionar_area("IMPRESIÓN")
elif mod_area == "✂️ CORTE": gestionar_area("CORTE")
elif mod_area == "📥 COLECTORAS": gestionar_area("COLECTORAS")
elif mod_area == "📕 ENCUADERNACIÓN": gestionar_area("ENCUADERNACIÓN")
