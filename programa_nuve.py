import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V14", page_icon="🏭")

# --- CONEXIÓN SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS VISUALES ORIGINALES ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; width: 100%; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 15px; border-radius: 12px; text-align: center; color: #1B5E20; box-shadow: 0px 0px 15px rgba(0,230,118,0.5); margin-bottom:10px;}
    .card-parada { background-color: #FF5252; border: 2px solid #D32F2F; padding: 15px; border-radius: 12px; text-align: center; color: white; box-shadow: 0px 0px 15px rgba(255,82,82,0.5); margin-bottom:10px;}
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px; text-align: center; color: #9E9E9E; margin-bottom:10px;}
    .title-area { background-color: #0D47A1; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE MÁQUINAS ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

# --- MENÚ LATERAL ---
with st.sidebar:
    st.title("🏭 NUVE V14")
    menu = st.radio("MENÚ", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# --- 1. MONITOR ---
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

# --- 2. SEGUIMIENTO ---
elif menu == "🔍 Seguimiento":
    st.title("Seguimiento de Órdenes")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if res:
        df = pd.DataFrame(res)
        st.dataframe(df[['op', 'tipo_op', 'cliente', 'nombre_trabajo', 'proxima_area', 'estado']], use_container_width=True)
        
        sel_op = st.selectbox("Detalle de OP:", df['op'].tolist())
        det = df[df['op'] == sel_op].iloc[0]
        st.json(det.to_dict())

# --- 3. PLANIFICACIÓN (FORMULARIOS PDF) ---
elif menu == "📅 Planificación":
    st.title("Nueva Orden de Producción")
    
    tipo_form = st.radio("Seleccione Tipo de Formulario:", ["OP FORMAS", "OP ROLLOS"], horizontal=True)

    with st.form("f_registro", clear_on_submit=True):
        st.subheader(f"DATOS DE {tipo_form}")
        c1, c2, c3 = st.columns(3)
        op_num = c1.text_input("Número de OP")
        op_ant = c2.text_input("OP Anterior No.")
        f_orden = c3.date_input("Fecha")
        
        c4, c5 = st.columns(2)
        cliente = c4.text_input("Cliente / Referencia")
        vendedor = c5.text_input("Vendedor")
        trabajo = st.text_input("Nombre de la Forma / Trabajo")

        if tipo_form == "OP FORMAS":
            st.markdown("---")
            f1, f2, f3 = st.columns(3)
            cant = f1.number_input("Cantidad Total", 0)
            partes = f2.selectbox("# Partes", [1, 2, 3, 4, 5, 6])
            linea = f3.selectbox("Línea", ["Prensa 22", "Prensa 17", "Prensa 11", "FCFS sobre hojas"])
            
            st.write("**Detalle de Partes:**")
            detalles_p = []
            for p in range(1, partes + 1):
                cp1, cp2, cp3 = st.columns(3)
                detalles_p.append({
                    "parte": p,
                    "color": cp1.text_input(f"Color P{p}"),
                    "gramos": cp2.text_input(f"Gramos P{p}"),
                    "impresion": cp3.selectbox(f"Impr P{p}", ["Frente", "Respaldo", "Ambos"])
                })
            
            n1, n2, n3 = st.columns(3)
            n_desde = n1.text_input("Numeración DEL:")
            n_hasta = n2.text_input("Numeración AL:")
            n_tipo = n3.selectbox("Tipo Numeración", ["Mecánica", "Inkjet", "Impacto"])
            
            payload = {
                "op": op_num.upper(), "tipo_op": "FORMAS", "op_anterior": op_ant,
                "fecha_orden": str(f_orden), "cliente": cliente, "vendedor": vendedor,
                "nombre_trabajo": trabajo, "cantidad_total": int(cant), "num_partes": partes,
                "linea_produccion": linea, "num_desde": n_desde, "num_hasta": n_hasta,
                "tipo_numeracion": n_tipo, "detalles_partes": detalles_p, "proxima_area": "IMPRESIÓN"
            }

        else: # OP ROLLOS
            st.markdown("---")
            r1, r2, r3 = st.columns(3)
            mat = r1.text_input("Material / Gramaje")
            ref_c = r2.text_input("Ref. Comercial")
            core = r3.selectbox("Core", ["13MM", "19MM", "1 PULG", "3 PULG"])
            
            e1, e2, e3 = st.columns(3)
            e_bolsa = e1.selectbox("¿Bolsa?", ["SI", "NO"])
            c_bolsa = e2.number_input("Cant x Bolsa", 0)
            e_caja = e3.selectbox("¿Caja?", ["SI", "NO"])
            
            c_caja = st.number_input("Cant x Caja", 0)
            trans = st.text_input("Transportadora")
            cant_r = st.number_input("Cantidad Total Rollos", 0)
            
            payload = {
                "op": op_num.upper(), "tipo_op": "ROLLOS", "op_anterior": op_ant,
                "fecha_orden": str(f_orden), "cliente": cliente, "vendedor": vendedor,
                "nombre_trabajo": trabajo, "material_gramaje": mat, "referencia_comercial": ref_c,
                "core": core, "empaque_bolsa": e_bolsa, "cant_bolsa": int(c_bolsa),
                "empaque_caja": e_caja, "cant_caja": int(c_caja), "transportadora": trans,
                "cantidad_total": int(cant_r), "proxima_area": "IMPRESIÓN"
            }

        if st.form_submit_button("REGISTRAR ORDEN"):
            try:
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.success("✅ Orden registrada"); time.sleep(1); st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# --- 4. MÓDULOS DE ÁREA ---
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.title(f"Área: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    cols = st.columns(4)
    
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols[idx % 4]:
            if m in activos:
                st.error(f"● {m} - {activos[m]['op']}")
                if st.button(f"Reportar {m}", key=f"r_{m}"):
                    st.session_state.rep = activos[m]
            else:
                st.success(f"○ {m} - LIBRE")
                ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
                if ops:
                    sel = st.selectbox(f"Asignar a {m}", [o['op'] for o in ops], key=f"s_{m}")
                    if st.button(f"Iniciar {m}", key=f"g_{m}"):
                        d = next(o for o in ops if o['op'] == sel)
                        supabase.table("trabajos_activos").insert({
                            "maquina": m, "area": area_act, "op": d['op'], 
                            "trabajo": d['nombre_trabajo'], "hora_inicio": datetime.now().strftime("%H:%M")
                        }).execute()
                        st.rerun()

    if 'rep' in st.session_state:
        rm = st.session_state.rep
        with st.expander(f"FINALIZAR EN {rm['maquina']}", expanded=True):
            operario = st.text_input("Operario")
            parcial = st.checkbox("¿Entrega Parcial?")
            c1, c2 = st.columns(2)
            
            if c1.button("🏁 TERMINAR"):
                # Lógica de flujo automático
                d_op = supabase.table("ordenes_planeadas").select("*").eq("op", rm['op']).single().execute().data
                tipo = d_op['tipo_op']
                
                n_area = "FINALIZADO"
                if tipo == "ROLLOS" and area_act == "IMPRESIÓN": n_area = "CORTE"
                elif tipo == "FORMAS":
                    if area_act == "IMPRESIÓN": n_area = "COLECTORAS"
                    elif area_act == "COLECTORAS": n_area = "ENCUADERNACIÓN"
                
                if not parcial:
                    supabase.table("ordenes_planeadas").update({"proxima_area": n_area}).eq("op", rm['op']).execute()
                
                supabase.table("trabajos_activos").delete().eq("maquina", rm['maquina']).execute()
                del st.session_state.rep
                st.rerun()
            
            if c2.button("🚨 PARADA"):
                supabase.table("trabajos_activos").update({"estado_maquina": "PARADA"}).eq("maquina", rm['maquina']).execute()
                st.rerun()
