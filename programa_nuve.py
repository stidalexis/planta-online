import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V16", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 15px; border-radius: 12px; text-align: center; color: #1B5E20; box-shadow: 0px 0px 15px rgba(0,230,118,0.5); margin-bottom:10px;}
    .card-parada { background-color: #FF5252; border: 2px solid #D32F2F; padding: 15px; border-radius: 12px; text-align: center; color: white; box-shadow: 0px 0px 15px rgba(255,82,82,0.5); margin-bottom:10px;}
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px; text-align: center; color: #9E9E9E; margin-bottom:10px;}
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
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
    st.title("🏭 NUVE V16")
    menu = st.radio("MENÚ", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# ==========================================
# MONITOR Y SEGUIMIENTO (BÁSICO)
# ==========================================
if menu == "🖥️ Monitor":
    st.title("Monitor de Planta")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    clase = "card-produccion" if act[m]['estado_maquina'] == 'PRODUCIENDO' else "card-parada"
                    st.markdown(f"<div class='{clase}'><b>{m}</b><br>{act[m]['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'><b>{m}</b><br>LIBRE</div>", unsafe_allow_html=True)
    time.sleep(15); st.rerun()

elif menu == "🔍 Seguimiento":
    st.title("Historial de Órdenes")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if res:
        df = pd.DataFrame(res)
        st.dataframe(df[['op', 'tipo_orden', 'cliente', 'nombre_trabajo', 'proxima_area']], use_container_width=True)

# ==========================================
# PLANIFICACIÓN (EL CAMBIO MASIVO)
# ==========================================
elif menu == "📅 Planificación":
    st.title("Registro de Órdenes de Producción")
    
    op_tipo = st.radio("SELECCIONE TIPO DE TRABAJO:", ["FORMAS IMPRESAS", "FORMAS BLANCAS", "ROLLOS (Impresos/Blancos)"], horizontal=True)

    with st.form("form_masivo"):
        # --- ENCABEZADO COMÚN ---
        c1, c2, c3 = st.columns(3)
        op_num = c1.text_input("Número de OP")
        op_ant = c2.text_input("OP Anterior")
        cliente = c3.text_input("Cliente")
        
        c4, c5, c6 = st.columns(3)
        vendedor = c4.text_input("Vendedor")
        nombre_forma = c5.text_input("Nombre de la Forma / Trabajo")
        referencia_r = c6.text_input("Referencia (Solo para Rollos)")

        # --- LÓGICA PARA FORMAS (IMPRESAS Y BLANCAS) ---
        if "FORMAS" in op_tipo:
            st.markdown("### CONFIGURACIÓN DE FORMAS")
            f1, f2 = st.columns(2)
            cant_f = f1.number_input("Cantidad de Formas", 0)
            partes_n = f2.selectbox("Número de Partes", [1, 2, 3, 4, 5, 6])
            
            # Perforaciones
            perf_si = st.checkbox("¿Lleva Perforaciones?")
            perf_det = st.text_input("Defina Perforaciones", "N/A") if perf_si else "NO"
            
            # Numeración
            st.write("**Numeración:**")
            n1, n2, n3 = st.columns(3)
            n_del = n1.text_input("DEL:")
            n_al = n2.text_input("AL:")
            n_tipo = n3.selectbox("Tipo Numeración", ["MECANICA", "INKJET"])
            
            # Código de Barras
            cb_si = st.checkbox("¿Código de Barras?")
            cb_det = st.text_input("Tipo de Código de Barras", "N/A") if cb_si else "NO"

            # TABLA DINÁMICA DE PARTES (LA PARTE DEL DOBLE PARÉNTESIS)
            st.markdown("#### ESPECIFICACIONES POR PARTE")
            lista_detalles_partes = []
            for i in range(1, partes_n + 1):
                with st.expander(f"PARTE #{i}", expanded=True):
                    d1, d2, d3 = st.columns(3)
                    ancho = d1.text_input(f"Ancho Forma P{i}")
                    largo = d2.text_input(f"Largo Forma P{i}")
                    papel = d3.text_input(f"Tipo Papel P{i}")
                    
                    d4, d5, d6 = st.columns(3)
                    fondo = d4.text_input(f"Fondo P{i}")
                    gramaje = d5.text_input(f"Gramaje P{i}")
                    trafico_si = d6.checkbox(f"¿Tráfico P{i}?")
                    trafico_det = st.text_input(f"Defina Tráfico P{i}", "N/A") if trafico_si else "NO"
                    
                    t1, t2 = st.columns(2)
                    # Si es Formas Blancas, no pedimos tintas
                    t_frente = ""
                    t_respaldo = ""
                    if op_tipo == "FORMAS IMPRESAS":
                        t_frente = t1.text_input(f"Tintas FRENTE P{i} (Cuales)")
                        t_respaldo = t2.text_input(f"Tintas RESPALDO P{i} (Cuales)")
                    
                    lista_detalles_partes.append({
                        "parte": i, "ancho": ancho, "largo": largo, "papel": papel,
                        "fondo": fondo, "gramaje": gramaje, "trafico": trafico_det,
                        "t_frente": t_frente, "t_respaldo": t_respaldo
                    })
            
            st.markdown("#### PRESENTACIÓN Y ACABADO")
            p1, p2 = st.columns(2)
            presenta = p1.selectbox("Tipo Presentación", ["LIBRETAS TAPADURA", "BLOCK LICOM", "HOJAS SUELTAS", "PAQUETES", "TACOS"])
            terminado = p2.selectbox("Cosidas o Encoladas por", ["CABEZA", "IZQUIERDA", "PATA", "N/A"])

        # --- LÓGICA PARA ROLLOS ---
        else:
            st.markdown("### CONFIGURACIÓN DE ROLLOS")
            r1, r2, r3 = st.columns(3)
            material_r = r1.text_input("Material")
            gramaje_r = r2.text_input("Gramaje")
            ref_comercial = r3.text_input("Referencia Comercial")
            
            r4, r5, r6 = st.columns(3)
            cant_r = r4.number_input("Cantidad Solicitada", 0)
            core_r = r5.selectbox("Core", ["13MM", "19MM", "1 PULGADA", "40 MM", "2 PULGADAS", "3 PULGADAS"])
            tiene_imp = r6.selectbox("¿Lleva Impresión?", ["SI", "NO"])
            
            t_frente_r, t_respaldo_r = "", ""
            if tiene_imp == "SI":
                c_tintas = st.number_input("Cantidad de Tintas", 0)
                ct1, ct2 = st.columns(2)
                t_frente_r = ct1.text_input("Tintas FRENTE")
                t_respaldo_r = ct2.text_input("Tintas RESPALDO")
            
            r7, r8 = st.columns(2)
            u_bolsa = r7.number_input("Unidades por Bolsa", 0)
            u_caja = r8.number_input("Unidades por Caja", 0)
            obs_r = st.text_area("Observaciones")

        # --- BOTÓN DE GUARDADO ---
        if st.form_submit_button("🚀 GUARDAR ORDEN DE PRODUCCIÓN"):
            if not op_num:
                st.error("Falta el número de OP")
            else:
                # Construcción del Payload según el tipo
                if "FORMAS" in op_tipo:
                    payload = {
                        "op": op_num.upper(), "op_anterior": op_ant, "cliente": cliente, 
                        "vendedor": vendedor, "nombre_trabajo": nombre_forma, "tipo_orden": op_tipo,
                        "cantidad_formas": int(cant_f), "num_partes": partes_n,
                        "perforaciones_detalle": perf_det, "num_desde": n_del, "num_hasta": n_al,
                        "presentacion": presenta, "terminado_por": terminado, "tipo_numeracion": n_tipo,
                        "codigo_barras_detalle": cb_det, "detalles_partes_json": lista_detalles_partes,
                        "proxima_area": "IMPRESIÓN" if op_tipo == "FORMAS IMPRESAS" else "COLECTORAS"
                    }
                else:
                    payload = {
                        "op": op_num.upper(), "op_anterior": op_ant, "cliente": cliente,
                        "referencia": referencia_r, "vendedor": vendedor, "nombre_trabajo": nombre_forma,
                        "tipo_orden": "ROLLOS", "material": material_r, "gramaje_rollos": gramaje_r,
                        "ref_comercial": ref_comercial, "cantidad_rollos": int(cant_r),
                        "core": core_r, "tiene_impresion": tiene_imp, "tintas_frente_rollos": t_frente_r,
                        "tintas_respaldo_rollos": t_respaldo_r, "unidades_bolsa": int(u_bolsa),
                        "unidades_caja": int(u_caja), "observaciones": obs_r,
                        "proxima_area": "IMPRESIÓN" if tiene_imp == "SI" else "CORTE"
                    }
                
                try:
                    supabase.table("ordenes_planeadas").insert(payload).execute()
                    st.success("✅ ORDEN REGISTRADA EXITOSAMENTE")
                    time.sleep(1); st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

# ==========================================
# GESTIÓN DE ÁREAS (IMPRESIÓN, CORTE, ETC)
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.title(f"Área: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    cols = st.columns(4)
    
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols[idx % 4]:
            if m in activos:
                st.error(f"● {m} - {activos[m]['op']}")
                if st.button(f"Cerrar {m}", key=f"c_{m}"):
                    st.session_state.temp_m = activos[m]
            else:
                st.success(f"○ {m} - LIBRE")
                ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
                if ops:
                    sel = st.selectbox(f"Asignar OP a {m}", [o['op'] for o in ops], key=f"s_{m}")
                    if st.button(f"Iniciar {m}", key=f"i_{m}"):
                        d = next(o for o in ops if o['op'] == sel)
                        supabase.table("trabajos_activos").insert({
                            "maquina": m, "area": area_act, "op": d['op'], 
                            "trabajo": d['nombre_trabajo'], "hora_inicio": datetime.now().strftime("%H:%M")
                        }).execute()
                        st.rerun()

    if 'temp_m' in st.session_state:
        tm = st.session_state.temp_m
        with st.expander(f"FINALIZAR TAREA EN {tm['maquina']}", expanded=True):
            if st.button("🏁 COMPLETAR Y AVANZAR"):
                d_op = supabase.table("ordenes_planeadas").select("*").eq("op", tm['op']).single().execute().data
                tipo = d_op['tipo_orden']
                
                # Lógica de flujo
                n_area = "FINALIZADO"
                if tipo == "ROLLOS":
                    if area_act == "IMPRESIÓN": n_area = "CORTE"
                else: # FORMAS
                    if area_act == "IMPRESIÓN": n_area = "COLECTORAS"
                    elif area_act == "COLECTORAS": n_area = "ENCUADERNACIÓN"
                
                supabase.table("ordenes_planeadas").update({"proxima_area": n_area}).eq("op", tm['op']).execute()
                supabase.table("trabajos_activos").delete().eq("maquina", tm['maquina']).execute()
                del st.session_state.temp_m
                st.rerun()
