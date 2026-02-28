import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V18", page_icon="🏭")

# --- CONEXIÓN SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 15px; border-radius: 12px; text-align: center; color: #1B5E20; box-shadow: 0px 0px 15px rgba(0,230,118,0.5); margin-bottom:10px;}
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px; text-align: center; color: #9E9E9E; margin-bottom:10px;}
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .seguimiento-card { background-color: #E3F2FD; border-left: 5px solid #2196F3; padding: 10px; margin-bottom: 5px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- MENÚ LATERAL ---
with st.sidebar:
    st.title("🏭 NUVE V18")
    menu = st.radio("MENÚ", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# ==========================================
# 1. MONITOR GENERAL (VISTA TOTAL DE PLANTA)
# ==========================================
if menu == "🖥️ Monitor General (TV)":
    st.title("🏭 Tablero de Control de Planta - Vista Total")
    
    # Estilo específico para el brillo verde y las tarjetas
    st.markdown("""
        <style>
        .card-activa-brillante { 
            padding: 15px; border-radius: 12px; 
            background-color: #00E676; /* Verde Brillante */
            border: 2px solid #00C853;
            box-shadow: 0px 0px 15px rgba(0, 230, 118, 0.5);
            margin-bottom: 15px; text-align: center; color: #1B5E20;
        }
        .card-vacia-monitor { 
            padding: 15px; border-radius: 12px; 
            background-color: #F5F5F5; border: 1px solid #E0E0E0;
            margin-bottom: 15px; text-align: center; color: #9E9E9E;
        }
        .text-maquina { font-size: 1.3rem; font-weight: 800; margin-bottom: 5px; display: block; }
        .text-op { font-size: 1.1rem; font-weight: 700; color: #000; display: block; }
        .text-trabajo { font-size: 0.85rem; font-weight: 500; display: block; line-height: 1.1; }
        </style>
    """, unsafe_allow_html=True)

    try:
        act_data = supabase.table("trabajos_activos").select("*").execute().data
        act = {a['maquina']: a for a in act_data}
    except:
        act = {}

    # Renderizamos cada área una tras otra
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>ÁREA: {area}</div>", unsafe_allow_html=True)
        cols = st.columns(4) # 4 columnas para que quepan más en pantalla
        
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    d = act[m]
                    st.markdown(f"""
                        <div class='card-activa-brillante'>
                            <span class='text-maquina'>{m}</span>
                            <span class='text-op'>{d['op']}</span>
                            <span class='text-trabajo'>{d['trabajo']}</span>
                            <hr style='margin: 8px 0; border: 0.5px solid #00C853;'>
                            <small>Inicio: {d.get('hora_inicio', '--:--')}</small>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                        <div class='card-vacia-monitor'>
                            <span class='text-maquina'>{m}</span>
                            <br>
                            <small>DISPONIBLE</small>
                        </div>
                    """, unsafe_allow_html=True)
    
    # Auto-refresco de datos cada 30 segundos para que gerencia vea cambios
    time.sleep(30)
    st.rerun()
# --- 2. SEGUIMIENTO DETALLADO ---
elif menu == "🔍 Seguimiento":
    st.title("Seguimiento Detallado de Órdenes")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if res:
        df = pd.DataFrame(res)
        sel_op = st.selectbox("Seleccione OP para ver su historial:", df['op'].tolist())
        det = df[df['op'] == sel_op].iloc[0]
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("Datos Generales")
            st.write(f"**Cliente:** {det['cliente']}")
            st.write(f"**Trabajo:** {det['nombre_trabajo']}")
            st.write(f"**Estado Actual:** {det['proxima_area']}")
            st.write(f"**Tipo:** {det['tipo_orden']}")
        
        with c2:
            st.subheader("Bitácora de Producción")
            historial = det['historial_procesos']
            if historial:
                for paso in historial:
                    st.markdown(f"""
                    <div class='seguimiento-card'>
                        <b>ÁREA: {paso['area']}</b> | Máquina: {paso['maquina']}<br>
                        <small>Operario: {paso['operario']} | Fecha: {paso['fecha']}</small><br>
                        Status: {paso['tipo_entrega']}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Esta orden aún no ha iniciado procesos en máquinas.")

# --- 3. PLANIFICACIÓN (FORMULARIOS PDF MASIVOS) ---
elif menu == "📅 Planificación":
    st.title("Registro de Órdenes")
    op_tipo = st.radio("SELECCIONE TIPO:", ["FORMAS IMPRESAS", "FORMAS BLANCAS", "ROLLOS"], horizontal=True)

    with st.form("form_master_v18"):
        c1, c2, c3 = st.columns(3)
        op_num = c1.text_input("Número de OP")
        op_ant = c2.text_input("OP Anterior")
        cliente = c3.text_input("Cliente")
        
        c4, c5 = st.columns(2)
        vendedor = c4.text_input("Vendedor")
        n_trabajo = c5.text_input("Nombre de la Forma / Trabajo")

        if "FORMAS" in op_tipo:
            st.markdown("### CONFIGURACIÓN DE FORMAS")
            f1, f2 = st.columns(2)
            cant_f = f1.number_input("Cantidad de Formas", 0)
            partes_n = f2.selectbox("Número de Partes", [1, 2, 3, 4, 5, 6])
            
            cp1, cp2 = st.columns(2)
            perf_si = cp1.selectbox("¿Lleva Perforaciones?", ["NO", "SI"])
            perf_det = cp1.text_area("Detalle Perforaciones", "N/A") if perf_si == "SI" else "NO"
            
            cb_si = cp2.selectbox("¿Código de Barras?", ["NO", "SI"])
            cb_det = cp2.text_area("Detalle Código de Barras", "N/A") if cb_si == "SI" else "NO"

            st.write("**Numeración:**")
            n1, n2, n3 = st.columns(3)
            n_del = n1.text_input("DEL:")
            n_al = n2.text_input("AL:")
            n_tipo = n3.selectbox("Tipo Numeración", ["MECANICA", "INKJET"])

            st.markdown("#### DETALLE TÉCNICO POR PARTE")
            lista_partes = []
            for i in range(1, partes_n + 1):
                st.markdown(f"--- **PARTE #{i}** ---")
                d1, d2, d3, d4 = st.columns(4)
                ancho = d1.text_input(f"Ancho P{i}", key=f"a_{i}")
                largo = d2.text_input(f"Largo P{i}", key=f"l_{i}")
                papel = d3.text_input(f"Tipo Papel P{i}", key=f"p_{i}")
                grama = d4.text_input(f"Gramaje P{i}", key=f"g_{i}")
                
                d5, d6, d7 = st.columns(3)
                fondo = d5.text_input(f"Fondo P{i}", key=f"f_{i}")
                trafico_si = d6.selectbox(f"Tráfico P{i}?", ["NO", "SI"], key=f"ts_{i}")
                trafico_det = d7.text_input(f"Defina Tráfico P{i}", key=f"td_{i}") if trafico_si == "SI" else "N/A"
                
                t_f, t_r = "N/A", "N/A"
                if op_tipo == "FORMAS IMPRESAS":
                    t1, t2 = st.columns(2)
                    t_f = t1.text_input(f"Tintas FRENTE P{i}", key=f"tf_{i}")
                    t_r = t2.text_input(f"Tintas RESPALDO P{i}", key=f"tr_{i}")
                
                lista_partes.append({"p": i, "an": ancho, "la": largo, "pa": papel, "gr": grama, "fo": fondo, "tr": trafico_det, "tf": t_f, "tr": t_r})

            st.markdown("#### ACABADO")
            p1, p2 = st.columns(2)
            pres = p1.selectbox("Presentación", ["LIBRETAS TAPADURA", "BLOCK LICOM", "HOJAS SUELTAS", "PAQUETES", "TACOS"])
            term = p2.selectbox("Cosidas/Encoladas por", ["CABEZA", "IZQUIERDA", "PATA", "N/A"])
            obs_f = st.text_area("Observaciones Generales")

        else: # ROLLOS
            st.markdown("### CONFIGURACIÓN DE ROLLOS")
            r1, r2, r3 = st.columns(3)
            mat = r1.text_input("Material")
            gram_r = r2.text_input("Gramaje")
            ref_com = r3.text_input("Referencia Comercial")
            
            r4, r5, r6 = st.columns(3)
            cant_r = r4.number_input("Cantidad Solicitada", 0)
            core_r = r5.selectbox("Core", ["13MM", "19MM", "1 PULGADA", "40 MM", "2 PULGADAS", "3 PULGADAS"])
            tiene_i = r6.selectbox("¿Lleva Impresión?", ["NO", "SI"])
            
            t_f_r, t_r_r, c_t = "N/A", "N/A", 0
            if tiene_i == "SI":
                c_t = st.number_input("Cantidad Tintas", 0)
                ct1, ct2 = st.columns(2)
                t_f_r = ct1.text_input("Tintas FRENTE")
                t_r_r = ct2.text_input("Tintas RESPALDO")
            
            r7, r8, r9 = st.columns(3)
            u_b = r7.number_input("Cant x Bolsa", 0)
            u_c = r8.number_input("Cant x Caja", 0)
            obs_r = st.text_area("Observaciones Rollos")

        if st.form_submit_button("🚀 REGISTRAR OP"):
            if not op_num: st.error("OP requerida")
            else:
                if "FORMAS" in op_tipo:
                    payload = {
                        "op": op_num.upper(), "op_anterior": op_ant, "cliente": cliente, "vendedor": vendedor, "nombre_trabajo": n_trabajo,
                        "tipo_orden": op_tipo, "cantidad_formas": int(cant_f), "num_partes": partes_n, "perforaciones_si_no": perf_si,
                        "perforaciones_detalle": perf_det, "num_desde": n_del, "num_hasta": n_al, "presentacion": pres,
                        "terminado_por": term, "tipo_numeracion": n_tipo, "codigo_barras_si_no": cb_si,
                        "codigo_barras_detalle": cb_det, "detalles_partes_json": lista_partes, "observaciones_formas": obs_f,
                        "proxima_area": "IMPRESIÓN" if op_tipo == "FORMAS IMPRESAS" else "COLECTORAS"
                    }
                else:
                    payload = {
                        "op": op_num.upper(), "op_anterior": op_ant, "cliente": cliente, "vendedor": vendedor, "nombre_trabajo": n_trabajo,
                        "tipo_orden": "ROLLOS", "material": mat, "gramaje_rollos": gram_r, "ref_comercial": ref_com, "cantidad_rollos": int(cant_r),
                        "core": core_r, "tiene_impresion": tiene_i, "cantidad_tintas": int(c_t), "tintas_frente_rollos": t_f_r,
                        "tintas_respaldo_rollos": t_r_r, "unidades_bolsa": int(u_b), "unidades_caja": int(u_c), "observaciones_rollos": obs_r,
                        "proxima_area": "IMPRESIÓN" if tiene_i == "SI" else "CORTE"
                    }
                try:
                    supabase.table("ordenes_planeadas").insert(payload).execute()
                    st.success("✅ Orden Guardada"); time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# --- MÓDULOS DE ÁREA (CON ACTUALIZACIÓN DE SEGUIMIENTO) ---
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.title(f"Área: {area_act}")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    cols = st.columns(4)
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols[idx % 4]:
            if m in activos:
                st.error(f"● {m} - {activos[m]['op']}")
                if st.button(f"Cerrar {m}", key=f"c_{m}"): st.session_state.temp = activos[m]
            else:
                st.success(f"○ {m} - LIBRE")
                ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
                if ops:
                    sel = st.selectbox(f"Asignar OP", [o['op'] for o in ops], key=f"s_{m}")
                    if st.button(f"Iniciar {m}", key=f"i_{m}"):
                        d = next(o for o in ops if o['op'] == sel)
                        supabase.table("trabajos_activos").insert({"maquina":m,"area":area_act,"op":d['op'],"trabajo":d['nombre_trabajo'],"hora_inicio":datetime.now().strftime("%H:%M")}).execute()
                        st.rerun()

    if 'temp' in st.session_state:
        tm = st.session_state.temp
        with st.expander(f"REPORTE DE FINALIZACIÓN {tm['maquina']}", expanded=True):
            nom_op = st.text_input("Nombre Operario")
            parcial = st.checkbox("¿Entrega Parcial?")
            if st.button("🏁 COMPLETAR Y ACTUALIZAR SEGUIMIENTO"):
                d_op = supabase.table("ordenes_planeadas").select("*").eq("op", tm['op']).single().execute().data
                
                # ACTUALIZAR BITÁCORA DE SEGUIMIENTO
                nuevo_paso = {
                    "area": area_act, "maquina": tm['maquina'], "operario": nom_op,
                    "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "tipo_entrega": "Parcial" if parcial else "Completa"
                }
                historial = d_op['historial_procesos']
                historial.append(nuevo_paso)
                
                # LÓGICA DE RUTA
                n_area = "FINALIZADO"
                if d_op['tipo_orden'] == "ROLLOS" and area_act == "IMPRESIÓN": n_area = "CORTE"
                elif "FORMAS" in d_op['tipo_orden']:
                    if area_act == "IMPRESIÓN": n_area = "COLECTORAS"
                    elif area_act == "COLECTORAS": n_area = "ENCUADERNACIÓN"
                
                supabase.table("ordenes_planeadas").update({"proxima_area": n_area, "historial_procesos": historial}).eq("op", tm['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", tm['maquina']).execute()
                del st.session_state.temp
                st.rerun()
