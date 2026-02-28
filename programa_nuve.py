import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import io

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V19", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 45px !important; border-radius: 8px; font-weight: bold; width: 100%; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 15px; border-radius: 12px; text-align: center; color: #1B5E20; font-weight: bold; }
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px; text-align: center; color: #9E9E9E; }
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .status-badge { padding: 4px 8px; border-radius: 4px; color: white; font-weight: bold; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("🏭 NUVE V19")
    menu = st.radio("MENÚ", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# --- 1. MONITOR ---
if menu == "🖥️ Monitor":
    st.title("Monitor de Producción en Tiempo Real")
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

# --- 2. SEGUIMIENTO (ESTILO FILA CON DETALLES) ---
elif menu == "🔍 Seguimiento":
    st.title("Historial y Seguimiento de Órdenes")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    
    if res:
        df = pd.DataFrame(res)
        
        # Botones de descarga global
        c_down1, c_down2 = st.columns([1, 5])
        csv = df.to_csv(index=False).encode('utf-8')
        c_down1.download_button("📥 Descargar Todo (CSV)", csv, "reporte_planta.csv", "text/csv")
        
        st.write("---")
        # Encabezados de la tabla
        h1, h2, h3, h4, h5, h6 = st.columns([1, 2, 2, 2, 2, 1])
        h1.bold("OP")
        h2.bold("Cliente")
        h3.bold("Trabajo")
        h4.bold("Tipo")
        h5.bold("Ubicación Actual")
        h6.bold("Acción")
        
        for index, row in df.iterrows():
            r1, r2, r3, r4, r5, r6 = st.columns([1, 2, 2, 2, 2, 1])
            r1.write(row['op'])
            r2.write(row['cliente'])
            r3.write(row['nombre_trabajo'])
            r4.write(row['tipo_orden'])
            
            color_area = "#FF9800" if row['proxima_area'] != "FINALIZADO" else "#4CAF50"
            r5.markdown(f"<span style='color:{color_area}; font-weight:bold;'>{row['proxima_area']}</span>", unsafe_allow_html=True)
            
            if r6.button("👁️", key=f"det_{row['op']}"):
                st.session_state.ver_op = row.to_dict()

        if 'ver_op' in st.session_state:
            v = st.session_state.ver_op
            with st.expander(f"DETALLES TÉCNICOS: OP {v['op']}", expanded=True):
                st.subheader(f"Información de {v['tipo_orden']}")
                col_a, col_b = st.columns(2)
                col_a.write(f"**Cliente:** {v['cliente']}")
                col_a.write(f"**Vendedor:** {v['vendedor']}")
                col_b.write(f"**Nombre Trabajo:** {v['nombre_trabajo']}")
                col_b.write(f"**Fecha Creación:** {v['created_at']}")
                
                st.markdown("---")
                st.write("**BITÁCORA DE PRODUCCIÓN:**")
                if v['historial_procesos']:
                    for p in v['historial_procesos']:
                        st.info(f"📍 {p['fecha']} - {p['area']} ({p['maquina']}) - Operario: {p['operario']} - {p['tipo_entrega']}")
                else:
                    st.warning("Sin movimientos registrados.")
                
                if st.button("Cerrar Detalles"):
                    del st.session_state.ver_op
                    st.rerun()

# --- 3. PLANIFICACIÓN (BOTONES SEPARADOS POR RUTA) ---
elif menu == "📅 Planificación":
    st.title("Nueva Orden de Producción")
    
    # 4 BOTONES SEPARADOS PARA DEFINIR RUTA AUTOMÁTICA
    st.write("Seleccione el tipo de producto para definir la ruta de producción:")
    c_btn1, c_btn2, c_btn3, c_btn4 = st.columns(4)
    
    if c_btn1.button("📑 FORMAS IMPRESAS"): st.session_state.sel_tipo = "FORMAS IMPRESAS"
    if c_btn2.button("📄 FORMAS BLANCAS"): st.session_state.sel_tipo = "FORMAS BLANCAS"
    if c_btn3.button("🌀 ROLLOS IMPRESOS"): st.session_state.sel_tipo = "ROLLOS IMPRESOS"
    if c_btn4.button("⚪ ROLLOS BLANCOS"): st.session_state.sel_tipo = "ROLLOS BLANCOS"

    if 'sel_tipo' in st.session_state:
        tipo = st.session_state.sel_tipo
        st.subheader(f"Formulario: {tipo}")
        
        with st.form("master_form"):
            c1, c2, c3 = st.columns(3)
            op_n = c1.text_input("Número de OP")
            op_a = c2.text_input("OP Anterior")
            cli = c3.text_input("Cliente")
            
            c4, c5 = st.columns(2)
            vend = c4.text_input("Vendedor")
            trab = c5.text_input("Nombre Trabajo")

            if "FORMAS" in tipo:
                st.markdown("### DATOS DE FORMAS")
                f1, f2 = st.columns(2)
                cant_f = f1.number_input("Cantidad Total", 0)
                partes_n = f2.selectbox("Número de Partes", [1,2,3,4,5,6])
                
                # Perforaciones y Barras
                p1, p2 = st.columns(2)
                perf = p1.selectbox("¿Perforaciones?", ["NO", "SI"])
                perf_d = p1.text_area("Detalle Perforación") if perf == "SI" else "N/A"
                barras = p2.selectbox("¿Código de Barras?", ["NO", "SI"])
                barras_d = p2.text_area("Detalle Barras") if barras == "SI" else "N/A"
                
                st.write("**Detalles por Parte:**")
                lista_p = []
                for i in range(1, partes_n + 1):
                    st.markdown(f"**PARTE {i}**")
                    d1, d2, d3, d4 = st.columns(4)
                    anc = d1.text_input(f"Ancho P{i}", key=f"anc_{i}")
                    lar = d2.text_input(f"Largo P{i}", key=f"lar_{i}")
                    pap = d3.text_input(f"Papel P{i}", key=f"pap_{i}")
                    gra = d4.text_input(f"Gramos P{i}", key=f"gra_{i}")
                    
                    t1, t2 = st.columns(2)
                    tf, tr = "N/A", "N/A"
                    if tipo == "FORMAS IMPRESAS":
                        tf = t1.text_input(f"Tintas Frente P{i}", key=f"tf_{i}")
                        tr = t2.text_input(f"Tintas Respaldo P{i}", key=f"tr_{i}")
                    lista_p.append({"p":i, "anc":anc, "lar":lar, "pap":pap, "tf":tf, "tr":tr})
                
                pres = st.selectbox("Presentación", ["LIBRETAS TAPADURA", "BLOCK LICOM", "HOJAS SUELTAS", "PAQUETES", "TACOS"])
                obs_f = st.text_area("Observaciones")

            else: # ROLLOS
                st.markdown("### DATOS DE ROLLOS")
                r1, r2, r3 = st.columns(3)
                mat = r1.text_input("Material")
                gra_r = r2.text_input("Gramaje")
                ref_c = r3.text_input("Referencia Comercial")
                
                r4, r5 = st.columns(2)
                cant_r = r4.number_input("Cantidad Rollos", 0)
                core = r5.selectbox("Core", ["13MM", "19MM", "1 PULGADA", "40 MM", "2 PULGADAS", "3 PULGADAS"])
                
                tf_r, tr_r = "N/A", "N/A"
                if tipo == "ROLLOS IMPRESOS":
                    ct1, ct2 = st.columns(2)
                    tf_r = ct1.text_input("Tintas Frente")
                    tr_r = ct2.text_input("Tintas Respaldo")
                
                r6, r7 = st.columns(2)
                u_b = r6.number_input("Cant x Bolsa", 0)
                u_c = r7.number_input("Cant x Caja", 0)
                obs_r = st.text_area("Observaciones")

            if st.form_submit_button("💾 GUARDAR Y DEFINIR RUTA"):
                # DEFINICIÓN AUTOMÁTICA DE RUTA
                ruta_inicial = "IMPRESIÓN"
                if tipo == "ROLLOS BLANCOS": ruta_inicial = "CORTE"
                if tipo == "FORMAS BLANCAS": ruta_inicial = "COLECTORAS"
                
                if "FORMAS" in tipo:
                    payload = {"op":op_n.upper(),"op_anterior":op_a,"cliente":cli,"vendedor":vend,"nombre_trabajo":trab,"tipo_orden":tipo,"cantidad_formas":int(cant_f),"num_partes":partes_n,"perforaciones_detalle":perf_d,"detalles_partes_json":lista_p,"presentacion":pres,"observaciones_formas":obs_f,"proxima_area":ruta_inicial}
                else:
                    payload = {"op":op_n.upper(),"op_anterior":op_a,"cliente":cli,"vendedor":vend,"nombre_trabajo":trab,"tipo_orden":tipo,"material":mat,"gramaje_rollos":gra_r,"ref_comercial":ref_c,"cantidad_rollos":int(cant_r),"core":core,"tintas_frente_rollos":tf_r,"tintas_respaldo_rollos":tr_r,"unidades_bolsa":int(u_b),"unidades_caja":int(u_c),"observaciones_rollos":obs_r,"proxima_area":ruta_inicial}
                
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.success("Orden creada con éxito"); time.sleep(1); del st.session_state.sel_tipo; st.rerun()

# --- MÓDULOS DE ÁREA ---
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.title(f"Área: {area_act}")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    
    cols = st.columns(4)
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols[idx % 4]:
            if m in activos:
                st.error(f"● {m} - {activos[m]['op']}")
                if st.button(f"Cerrar {m}", key=f"btn_{m}"): st.session_state.reporte = activos[m]
            else:
                st.success(f"○ {m} - LIBRE")
                ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
                if ops:
                    sel = st.selectbox(f"Asignar OP", [o['op'] for o in ops], key=f"sel_{m}")
                    if st.button(f"Iniciar {m}", key=f"start_{m}"):
                        d = next(o for o in ops if o['op'] == sel)
                        supabase.table("trabajos_activos").insert({"maquina":m,"area":area_act,"op":d['op'],"trabajo":d['nombre_trabajo'],"hora_inicio":datetime.now().strftime("%H:%M")}).execute()
                        st.rerun()

    if 'reporte' in st.session_state:
        r = st.session_state.reporte
        with st.expander(f"REPORTE FINAL {r['maquina']}", expanded=True):
            operario = st.text_input("Operario responsable")
            if st.button("🏁 FINALIZAR TAREA"):
                d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                tipo = d_op['tipo_orden']
                
                # LÓGICA DE RUTA SEGÚN TIPO
                n_area = "FINALIZADO"
                if tipo == "ROLLOS IMPRESOS" and area_act == "IMPRESIÓN": n_area = "CORTE"
                elif "FORMAS" in tipo:
                    if area_act == "IMPRESIÓN": n_area = "COLECTORAS"
                    elif area_act == "COLECTORAS": n_area = "ENCUADERNACIÓN"
                
                # Actualizar Historial
                h = d_op['historial_procesos']
                h.append({"area":area_act, "maquina":r['maquina'], "operario":operario, "fecha":datetime.now().strftime("%d/%m/%Y %H:%M"), "tipo_entrega":"Completa"})
                
                supabase.table("ordenes_planeadas").update({"proxima_area":n_area, "historial_procesos":h}).eq("op", r['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()
                del st.session_state.reporte
                st.rerun()
