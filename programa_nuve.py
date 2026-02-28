import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import io

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V20", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 40px !important; border-radius: 8px; font-weight: bold; width: 100%; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 15px; border-radius: 12px; text-align: center; color: #1B5E20; font-weight: bold; }
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px; text-align: center; color: #9E9E9E; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

with st.sidebar:
    st.title("🏭 NUVE V20")
    menu = st.radio("MENÚ", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# --- MONITOR ---
if menu == "🖥️ Monitor":
    st.title("Monitor de Planta")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    st.markdown(f"<div class='card-produccion'>{m}<br>{act[m]['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'>{m}<br>LIBRE</div>", unsafe_allow_html=True)
    time.sleep(20); st.rerun()

# --- SEGUIMIENTO (CON EXCEL Y MODAL) ---
elif menu == "🔍 Seguimiento":
    st.title("Seguimiento y Registro Histórico")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    
    if res:
        df = pd.DataFrame(res)
        
        # Función para convertir a Excel
        def to_excel(df_input):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_input.to_excel(writer, index=False, sheet_name='Ordenes')
            return output.getvalue()

        col_ex1, col_ex2 = st.columns([1, 4])
        excel_data = to_excel(df)
        col_ex1.download_button(label="📥 Descargar Todo (Excel)", data=excel_data, file_name=f"reporte_nuve_{datetime.now().strftime('%Y%m%d')}.xlsx")

        st.write("---")
        # Encabezados corregidos (sin .bold)
        h1, h2, h3, h4, h5, h6 = st.columns([1, 2, 2, 2, 2, 1])
        h1.markdown("**OP**")
        h2.markdown("**Cliente**")
        h3.markdown("**Trabajo**")
        h4.markdown("**Tipo de Orden**")
        h5.markdown("**Ubicación / Status**")
        h6.markdown("**Ver**")

        for index, row in df.iterrows():
            r1, r2, r3, r4, r5, r6 = st.columns([1, 2, 2, 2, 2, 1])
            r1.write(row['op'])
            r2.write(row['cliente'])
            r3.write(row['nombre_trabajo'])
            r4.write(row['tipo_orden'])
            
            color = "#FF9800" if row['proxima_area'] != "FINALIZADO" else "#4CAF50"
            r5.markdown(f"<span style='color:{color}; font-weight:bold;'>{row['proxima_area']}</span>", unsafe_allow_html=True)
            
            if r6.button("👁️", key=f"btn_{row['op']}"):
                st.session_state.detalle_op = row.to_dict()

        if 'detalle_op' in st.session_state:
            d = st.session_state.detalle_op
            with st.expander(f"DETALLE TÉCNICO COMPLETO - OP: {d['op']}", expanded=True):
                st.write(f"### {d['tipo_orden']}")
                c_det1, c_det2 = st.columns(2)
                with c_det1:
                    st.write(f"**Cliente:** {d['cliente']}")
                    st.write(f"**Vendedor:** {d['vendedor']}")
                    st.write(f"**Creado:** {d['created_at']}")
                with c_det2:
                    st.write(f"**Trabajo:** {d['nombre_trabajo']}")
                    st.write(f"**OP Anterior:** {d['op_anterior']}")
                
                st.write("---")
                st.write("**BITÁCORA DE MOVIMIENTOS:**")
                if d['historial_procesos']:
                    for p in d['historial_procesos']:
                        st.success(f"✅ {p['fecha']} | {p['area']} - {p['maquina']} | Op: {p['operario']} | {p['tipo_entrega']}")
                else:
                    st.info("Sin movimientos registrados.")
                
                # Botón para descargar esta OP individual a Excel
                df_single = pd.DataFrame([d])
                excel_single = to_excel(df_single)
                st.download_button(f"📥 Descargar Ficha OP {d['op']}", excel_single, f"OP_{d['op']}.xlsx")
                
                if st.button("Cerrar Vista"):
                    del st.session_state.detalle_op
                    st.rerun()

# --- PLANIFICACIÓN (RUTAS AUTOMÁTICAS) ---
elif menu == "📅 Planificación":
    st.title("Creación de Orden de Producción")
    st.info("Seleccione el tipo de producto. El sistema asignará la ruta técnica automáticamente.")
    
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📑 FORMAS IMPRESAS"): st.session_state.tipo = "FORMAS IMPRESAS"
    if c2.button("📄 FORMAS BLANCAS"): st.session_state.tipo = "FORMAS BLANCAS"
    if c3.button("🌀 ROLLOS IMPRESOS"): st.session_state.tipo = "ROLLOS IMPRESOS"
    if c4.button("⚪ ROLLOS BLANCOS"): st.session_state.tipo = "ROLLOS BLANCOS"

    if 'tipo' in st.session_state:
        t = st.session_state.tipo
        with st.form("main_form"):
            st.subheader(f"Formulario para: {t}")
            f_c1, f_c2, f_c3 = st.columns(3)
            op_n = f_c1.text_input("Número de OP")
            op_a = f_c2.text_input("OP Anterior")
            cli = f_c3.text_input("Cliente")
            
            f_c4, f_c5 = st.columns(2)
            vend = f_c4.text_input("Vendedor")
            trab = f_c5.text_input("Nombre Trabajo")

            if "FORMAS" in t:
                f_c6, f_c7 = st.columns(2)
                cant_f = f_c6.number_input("Cantidad de Formas", 0)
                partes = f_c7.selectbox("Partes", [1,2,3,4,5,6])
                
                p_c1, p_c2 = st.columns(2)
                perf = p_c1.selectbox("¿Perforaciones?", ["NO", "SI"])
                perf_d = p_c1.text_area("Detalle Perforación") if perf == "SI" else "NO"
                barras = p_c2.selectbox("¿Código de Barras?", ["NO", "SI"])
                barras_d = p_c2.text_area("Detalle Barras") if barras == "SI" else "NO"

                st.write("**Especificación por Parte:**")
                lista_p = []
                for i in range(1, partes + 1):
                    st.markdown(f"**PARTE {i}**")
                    d1, d2, d3, d4 = st.columns(4)
                    anc = d1.text_input(f"Ancho P{i}", key=f"anc_{i}")
                    lar = d2.text_input(f"Largo P{i}", key=f"lar_{i}")
                    pap = d3.text_input(f"Papel P{i}", key=f"pap_{i}")
                    gra = d4.text_input(f"Gramos P{i}", key=f"gra_{i}")
                    
                    tf, tr = "N/A", "N/A"
                    if t == "FORMAS IMPRESAS":
                        t1, t2 = st.columns(2)
                        tf = t1.text_input(f"Tintas Frente P{i}", key=f"tf_{i}")
                        tr = t2.text_input(f"Tintas Respaldo P{i}", key=f"tr_{i}")
                    lista_p.append({"p":i, "anc":anc, "lar":lar, "tf":tf, "tr":tr})
                
                pres = st.selectbox("Presentación", ["LIBRETAS TAPADURA", "BLOCK LICOM", "HOJAS SUELTAS", "PAQUETES", "TACOS"])
                obs = st.text_area("Observaciones")

            else: # ROLLOS
                r1, r2, r3 = st.columns(3)
                mat = r1.text_input("Material")
                gram = r2.text_input("Gramaje")
                ref_c = r3.text_input("Ref. Comercial")
                
                r4, r5 = st.columns(2)
                cant_r = r4.number_input("Cantidad Rollos", 0)
                core = r5.selectbox("Core", ["13MM", "19MM", "1 PULGADA", "40 MM", "2 PULGADAS", "3 PULGADAS"])
                
                tf_r, tr_r = "N/A", "N/A"
                if t == "ROLLOS IMPRESOS":
                    ct1, ct2 = st.columns(2)
                    tf_r = ct1.text_input("Tintas Frente")
                    tr_r = ct2.text_input("Tintas Respaldo")
                obs = st.text_area("Observaciones")

            if st.form_submit_button("💾 REGISTRAR ORDEN"):
                # RUTA AUTOMÁTICA
                ruta = "IMPRESIÓN"
                if t == "ROLLOS BLANCOS": ruta = "CORTE"
                if t == "FORMAS BLANCAS": ruta = "COLECTORAS"
                
                if "FORMAS" in t:
                    payload = {"op":op_n.upper(),"op_anterior":op_a,"cliente":cli,"vendedor":vend,"nombre_trabajo":trab,"tipo_orden":t,"cantidad_formas":int(cant_f),"num_partes":partes,"perforaciones_detalle":perf_d,"detalles_partes_json":lista_p,"presentacion":pres,"observaciones_formas":obs,"proxima_area":ruta}
                else:
                    payload = {"op":op_n.upper(),"op_anterior":op_a,"cliente":cli,"vendedor":vend,"nombre_trabajo":trab,"tipo_orden":t,"material":mat,"gramaje_rollos":gram,"ref_comercial":ref_c,"cantidad_rollos":int(cant_r),"core":core,"tintas_frente_rollos":tf_r,"tintas_respaldo_rollos":tr_r,"observaciones_rollos":obs,"proxima_area":ruta}
                
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.success(f"Orden enviada a {ruta}"); time.sleep(1); del st.session_state.tipo; st.rerun()

# --- MÓDULOS DE PRODUCCIÓN ---
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.title(f"Módulo: {area_act}")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    
    cols = st.columns(4)
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols[idx % 4]:
            if m in activos:
                st.error(f"● {m} - {activos[m]['op']}")
                if st.button(f"Cerrar {m}", key=f"c_{m}"): st.session_state.re = activos[m]
            else:
                st.success(f"○ {m} - LIBRE")
                ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
                if ops:
                    sel = st.selectbox(f"Asignar OP", [o['op'] for o in ops], key=f"s_{m}")
                    if st.button(f"Iniciar {m}", key=f"i_{m}"):
                        d = next(o for o in ops if o['op'] == sel)
                        supabase.table("trabajos_activos").insert({"maquina":m,"area":area_act,"op":d['op'],"trabajo":d['nombre_trabajo'],"hora_inicio":datetime.now().strftime("%H:%M")}).execute()
                        st.rerun()

    if 're' in st.session_state:
        r = st.session_state.re
        with st.expander(f"FINALIZAR EN {r['maquina']}", expanded=True):
            op_name = st.text_input("Operario")
            if st.button("🏁 COMPLETAR"):
                d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                tipo = d_op['tipo_orden']
                n_area = "FINALIZADO"
                if tipo == "ROLLOS IMPRESOS" and area_act == "IMPRESIÓN": n_area = "CORTE"
                elif "FORMAS" in tipo:
                    if area_act == "IMPRESIÓN": n_area = "COLECTORAS"
                    elif area_act == "COLECTORAS": n_area = "ENCUADERNACIÓN"
                
                h = d_op['historial_procesos']
                h.append({"area":area_act, "maquina":r['maquina'], "operario":op_name, "fecha":datetime.now().strftime("%d/%m/%Y %H:%M"), "tipo_entrega":"Completa"})
                supabase.table("ordenes_planeadas").update({"proxima_area":n_area, "historial_procesos":h}).eq("op", r['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()
                del st.session_state.re; st.rerun()
