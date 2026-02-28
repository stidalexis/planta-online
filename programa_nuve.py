import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V13", page_icon="🏭")

# --- CONEXIÓN SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES ORIGINALES (PROHIBIDO CAMBIAR) ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 15px; border-radius: 12px; text-align: center; color: #1B5E20; box-shadow: 0px 0px 15px rgba(0,230,118,0.5); margin-bottom:10px;}
    .card-parada { background-color: #FF5252; border: 2px solid #D32F2F; padding: 15px; border-radius: 12px; text-align: center; color: white; box-shadow: 0px 0px 15px rgba(255,82,82,0.5); margin-bottom:10px;}
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px; text-align: center; color: #9E9E9E; margin-bottom:10px;}
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN TÉCNICA ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- BARRA LATERAL (MENÚ ORIGINAL) ---
with st.sidebar:
    st.title("🏭 NUVE V13")
    menu = st.radio("MENÚ", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# ==========================================
# 1. MONITOR (VISUAL ORIGINAL)
# ==========================================
if menu == "🖥️ Monitor":
    st.title("Monitor en Tiempo Real")
    act = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").execute().data}
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:
                if m in act:
                    est = act[m].get('estado_maquina', 'PRODUCIENDO')
                    clase = "card-produccion" if est == 'PRODUCIENDO' else "card-parada"
                    st.markdown(f"<div class='{clase}'><b>{m}</b><br>{act[m]['op']}<br><small>{act[m]['trabajo']}</small></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'><b>{m}</b><br><small>LIBRE</small></div>", unsafe_allow_html=True)
    time.sleep(15); st.rerun()

# ==========================================
# 2. SEGUIMIENTO (CON VISUAL DE ARTE)
# ==========================================
elif menu == "🔍 Seguimiento":
    st.title("Seguimiento y Control de OP")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if res:
        df = pd.DataFrame(res)
        st.dataframe(df[['op', 'tipo_op', 'cliente', 'nombre_trabajo', 'proxima_area', 'estado']], use_container_width=True)
        
        sel_op = st.selectbox("Seleccione OP para ver detalles:", df['op'].tolist())
        det = df[df['op'] == sel_op].iloc[0]
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("**DATOS TÉCNICOS:**")
            st.json(det.to_dict())
        with c2:
            if det['url_arte']:
                st.write("**ARTE ADJUNTO:**")
                st.image(det['url_arte'], use_container_width=True)
                st.link_button("Descargar Arte Original", det['url_arte'])

# ==========================================
# 3. PLANIFICACIÓN (FORMULARIOS PDF COMPLETOS)
# ==========================================
elif menu == "📅 Planificación":
    st.title("📅 Creación de Órdenes de Producción")
    
    tipo_form = st.segmented_control("Seleccione Tipo de Formulario:", ["OP FORMAS", "OP ROLLOS"])
    
    if tipo_form:
        # --- SUBIDA DE ARTE (CON TRY/EXCEPT PARA STORAGE) ---
        archivo = st.file_uploader("🖼️ Cargar Arte del Trabajo", type=["pdf", "jpg", "png"])
        url_arte = None
        if archivo:
            if st.button("Subir y Validar Archivo"):
                try:
                    path = f"artes/{int(time.time())}_{archivo.name}"
                    supabase.storage.from_("artes").upload(path, archivo.getvalue(), {"content-type": archivo.type})
                    url_arte = supabase.storage.from_("artes").get_public_url(path)
                    st.session_state.url_actual = url_arte
                    st.success("✅ Arte cargado correctamente.")
                except Exception as e:
                    st.error(f"Error de Storage: {e}")

        with st.form("f_creacion", clear_on_submit=True):
            # --- SECCIÓN ENCABEZADO (COMÚN) ---
            c1, c2, c3 = st.columns(3)
            op_num = c1.text_input("OP No.") [cite: 13, 129]
            op_ant = c2.text_input("OP Anterior No.") [cite: 11, 127]
            f_orden = c3.date_input("Fecha de Orden") [cite: 17, 133]
            
            c4, c5 = st.columns(2)
            cliente = c4.text_input("Cliente") [cite: 20, 136]
            vendedor = c5.text_input("Vendedor") [cite: 21, 137]
            trabajo = st.text_input("Nombre de la Forma / Trabajo") [cite: 26]
            
            # --- FORMULARIO ESPECÍFICO FORMAS ---
            if tipo_form == "OP FORMAS": [cite: 12]
                st.divider()
                st.subheader("Configuración de Formas")
                f1, f2, f3 = st.columns(3)
                cant = f1.number_input("Cantidad Total", 0) [cite: 25]
                partes = f2.selectbox("# Partes", [1, 2, 3, 4, 5, 6]) [cite: 27]
                linea = f3.selectbox("Línea de Producción", ["Prensa 22", "Prensa 17", "Prensa 11", "FCFS sobre hojas"]) [cite: 30, 31, 32]
                
                # Tabla de las 6 partes (Datos de Papel) 
                st.write("**Datos de Papel por Parte:**")
                tabla_partes = []
                for p in range(1, partes + 1):
                    colp1, colp2, colp3, colp4 = st.columns(4)
                    tabla_partes.append({
                        "parte": p,
                        "color": colp1.text_input(f"Color Parte {p}"),
                        "gramos": colp2.text_input(f"Gramos P{p}"),
                        "clase": colp3.text_input(f"Clase P{p}"),
                        "impresion": colp4.selectbox(f"Impr. P{p}", ["Frente", "Respaldo", "Ambos"])
                    })
                
                n1, n2, n3 = st.columns(3)
                n_desde = n1.text_input("Numeración DEL:") [cite: 36]
                n_hasta = n2.text_input("Numeración AL:") [cite: 38]
                n_tipo = n3.multiselect("Tipo Numeración", ["Mecánica", "Inkjet", "Impacto", "Código de Barras"]) [cite: 58, 62, 66, 76]

            # --- FORMULARIO ESPECÍFICO ROLLOS ---
            else: [cite: 128]
                st.divider()
                st.subheader("Configuración de Rollos")
                r1, r2, r3 = st.columns(3)
                mat = r1.text_input("Material / Gramaje") [cite: 142]
                ref_com = r2.text_input("Referencia Comercial") [cite: 142]
                core = r3.selectbox("Core", ["13MM", "19MM", "1 PULG", "3 PULG"]) [cite: 142]
                
                e1, e2, e3 = st.columns(3)
                e_bolsa = e1.checkbox("Empaque en Bolsa") [cite: 143]
                cant_b = e2.number_input("Cantidad por Bolsa", 0) [cite: 148]
                e_caja = e3.checkbox("Empaque en Caja") [cite: 144]
                
                cant = st.number_input("Cantidad Total Rollos", 0) [cite: 140]
                trans = st.text_input("Transportadora") [cite: 145]

            obs = st.text_area("Observaciones para Producción") [cite: 54, 159]

            if st.form_submit_button("🚀 REGISTRAR ORDEN EN SISTEMA"):
                area_ini = "IMPRESIÓN" # Por defecto inician en impresión según flujo
                
                # Payload consolidado
                payload = {
                    "op": op_num.upper(), "tipo_op": tipo_form, "op_anterior": op_ant,
                    "fecha_orden": str(f_orden), "cliente": cliente, "vendedor": vendedor,
                    "nombre_trabajo": trabajo, "proxima_area": area_ini,
                    "url_arte": st.session_state.get('url_actual'),
                    "cantidad_total": int(cant) if 'cant' in locals() else 0
                }
                
                # Agregar datos específicos antes de subir
                if tipo_form == "OP FORMAS":
                    payload.update({"num_partes": partes, "linea_produccion": linea, "num_desde": n_desde, "num_hasta": n_hasta, "detalles_partes": tabla_partes})
                else:
                    payload.update({"referencia_comercial": ref_com, "core": core, "cant_bolsa": int(cant_b), "transportadora": trans})

                try:
                    supabase.table("ordenes_planeadas").insert(payload).execute()
                    st.success("✅ Orden Registrada y Sincronizada.")
                    st.session_state.url_actual = None
                    time.sleep(1); st.rerun()
                except Exception as e:
                    st.error(f"Error al insertar: {e}")

# ==========================================
# 4. ÁREAS DE PRODUCCIÓN (LÓGICA AUTOMÁTICA)
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_actual = menu.split(" ")[1].upper()
    st.title(f"Módulo de {area_actual}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_actual).execute().data}
    cols = st.columns(4)
    
    for idx, m in enumerate(MAQUINAS[area_actual]):
        with cols[idx % 4]:
            if m in activos:
                st.error(f"● {m} - {activos[m]['op']}")
                if st.button(f"Reportar {m}", key=f"btn_{m}"):
                    st.session_state.rep_maquina = activos[m]
            else:
                st.success(f"○ {m} - LIBRE")
                # Solo mostrar OPs que tengan esta área asignada
                ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_actual).execute().data
                if ops:
                    sel = st.selectbox(f"Asignar OP a {m}", [o['op'] for o in ops], key=f"sel_{m}")
                    if st.button(f"Iniciar {m}", key=f"go_{m}"):
                        d_op = next(o for o in ops if o['op'] == sel)
                        supabase.table("trabajos_activos").insert({
                            "maquina": m, "area": area_actual, "op": d_op['op'], 
                            "trabajo": d_op['nombre_trabajo'], "hora_inicio": datetime.now().strftime("%H:%M")
                        }).execute()
                        st.rerun()

    # Panel de Reporte (Parada de Emergencia y Entrega Parcial)
    if 'rep_maquina' in st.session_state:
        rm = st.session_state.rep_maquina
        with st.expander(f"FINALIZAR TAREA EN {rm['maquina']}", expanded=True):
            st.write(f"Trabajando en: **{rm['op']}**")
            operario = st.text_input("Nombre del Operario")
            parcial = st.checkbox("¿Es Entrega PARCIAL?")
            
            c1, c2 = st.columns(2)
            if c1.button("🏁 COMPLETAR Y AVANZAR"):
                # LÓGICA DE RUTAS AUTOMÁTICAS
                # Simplificación: Impresión -> Corte (Rollos) / Impresión -> Colectoras -> Encuadernación (Formas)
                det_op = supabase.table("ordenes_planeadas").select("*").eq("op", rm['op']).single().execute().data
                tipo = det_op['tipo_op']
                
                nueva_area = "FINALIZADO"
                if tipo == "OP ROLLOS" and area_actual == "IMPRESIÓN": nueva_area = "CORTE"
                elif tipo == "OP FORMAS":
                    if area_actual == "IMPRESIÓN": nueva_area = "COLECTORAS"
                    elif area_actual == "COLECTORAS": nueva_area = "ENCUADERNACIÓN"

                if not parcial:
                    supabase.table("ordenes_planeadas").update({"proxima_area": nueva_area, "estado": "En Proceso"}).eq("op", rm['op']).execute()
                
                supabase.table("trabajos_activos").delete().eq("maquina", rm['maquina']).execute()
                del st.session_state.rep_maquina
                st.rerun()

            if c2.button("🚨 PARADA DE EMERGENCIA"):
                supabase.table("trabajos_activos").update({"estado_maquina": "PARADA"}).eq("maquina", rm['maquina']).execute()
                st.rerun()
