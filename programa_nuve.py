import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V15", page_icon="🏭")

# --- CONEXIÓN ---
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

MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

with st.sidebar:
    st.title("🏭 NUVE V15")
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
                    clase = "card-produccion" if act[m]['estado_maquina'] == 'PRODUCIENDO' else "card-parada"
                    st.markdown(f"<div class='{clase}'><b>{m}</b><br>{act[m]['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'><b>{m}</b><br>LIBRE</div>", unsafe_allow_html=True)
    time.sleep(15); st.rerun()

# --- SEGUIMIENTO ---
elif menu == "🔍 Seguimiento":
    st.title("Seguimiento de Órdenes")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if res:
        df = pd.DataFrame(res)
        st.dataframe(df[['op', 'tipo_op', 'cliente', 'nombre_trabajo', 'proxima_area', 'estado']], use_container_width=True)
        sel_op = st.selectbox("Detalle de OP:", df['op'].tolist())
        det = df[df['op'] == sel_op].iloc[0]
        st.json(det.to_dict())

# --- PLANIFICACIÓN (FORMULARIOS PDF MEJORADOS) ---
elif menu == "📅 Planificación":
    st.title("Registro de Órdenes")
    tipo_form = st.radio("Tipo de OP:", ["OP FORMAS", "OP ROLLOS"], horizontal=True)

    with st.form("f_registro"):
        c1, c2 = st.columns(2)
        op_num = c1.text_input("Número de OP (Obligatorio)")
        op_ant = c2.text_input("OP Anterior No.")
        
        c3, c4 = st.columns(2)
        cliente = c3.text_input("Cliente / Referencia")
        vendedor = c4.text_input("Vendedor")
        trabajo = st.text_input("Nombre de la Forma / Trabajo")

        if tipo_form == "OP FORMAS":
            st.markdown("### ESPECIFICACIONES DE FORMAS")
            f1, f2 = st.columns(2)
            cant_total = f1.number_input("CANTIDAD TOTAL (Formas)", 0)
            num_partes = f2.selectbox("# PARTES", [1, 2, 3, 4, 5, 6])
            
            # TABLA DINÁMICA DE PARTES (DETALLES COMPLETOS PDF)
            st.write("**Detalles Técnicos por Parte:**")
            detalles_partes = []
            for i in range(1, num_partes + 1):
                with st.expander(f"Configuración Parte {i}", expanded=True):
                    col1, col2, col3, col4 = st.columns(4)
                    tipo_p = col1.text_input(f"Tipo Papel P{i}", placeholder="Ej: Bond, Químico")
                    color_p = col2.text_input(f"Color P{i}")
                    medida_p = col3.text_input(f"Medida P{i}")
                    trafico = col4.selectbox(f"Tráfico P{i}", ["CB", "CFB", "CF", "N/A"])
                    
                    col5, col6, col7 = st.columns(3)
                    tintas = col5.text_input(f"Tintas P{i}", placeholder="Ej: 2x1, 1x0")
                    fondo = col6.text_input(f"Fondo P{i}")
                    frente_resp = col7.selectbox(f"Impresión P{i}", ["Frente", "Respaldo", "Ambos"])
                    
                    detalles_partes.append({
                        "parte": i, "papel": tipo_p, "color": color_p, "medida": medida_p,
                        "trafico": trafico, "tintas": tintas, "fondo": fondo, "lado": frente_resp
                    })
            
            st.markdown("---")
            n1, n2, n3 = st.columns(3)
            n_desde = n1.text_input("Numeración DEL:")
            n_hasta = n2.text_input("Numeración AL:")
            n_tipo = n3.selectbox("Tipo Numeración", ["Mecánica", "Inkjet", "Impacto", "Código de Barras"])
            
            payload = {
                "op": op_num.upper(), "tipo_op": "FORMAS", "op_anterior": op_ant,
                "cliente": cliente, "vendedor": vendedor, "nombre_trabajo": trabajo,
                "cantidad_total": int(cant_total), "num_partes": num_partes,
                "num_desde": n_desde, "num_hasta": n_hasta, "tipo_numeracion": n_tipo,
                "detalles_partes": detalles_partes, "proxima_area": "IMPRESIÓN"
            }

        else: # OP ROLLOS
            st.markdown("### ESPECIFICACIONES DE ROLLOS")
            r1, r2, r3 = st.columns(3)
            mat = r1.text_input("Material")
            gram = r2.text_input("Gramaje")
            core = r3.selectbox("Core", ["13MM", "19MM", "1 PULG", "3 PULG"])
            
            ref_c = st.text_input("Referencia Comercial")
            
            e1, e2, e3 = st.columns(3)
            e_bolsa = e1.selectbox("Empaque Bolsa", ["SI", "NO"])
            c_bolsa = e2.number_input("Cant por Bolsa", 0)
            e_caja = e3.selectbox("Empaque Caja", ["SI", "NO"])
            
            c4, c5 = st.columns(2)
            c_caja = c4.number_input("Cant por Caja", 0)
            trans = c5.text_input("Transportadora")
            
            cant_r = st.number_input("CANTIDAD TOTAL (Rollos)", 0)
            obs = st.text_area("Observaciones Producción")
            
            payload = {
                "op": op_num.upper(), "tipo_op": "ROLLOS", "op_anterior": op_ant,
                "cliente": cliente, "vendedor": vendedor, "nombre_trabajo": trabajo,
                "material_gramaje": f"{mat} {gram}", "referencia_comercial": ref_c,
                "core": core, "empaque_bolsa": e_bolsa, "cant_bolsa": int(c_bolsa),
                "empaque_caja": e_caja, "cant_caja": int(c_caja), "transportadora": trans,
                "cantidad_total": int(cant_r), "observaciones_previas": obs, "proxima_area": "IMPRESIÓN"
            }

        if st.form_submit_button("🚀 GUARDAR ORDEN"):
            if not op_num:
                st.error("Debe ingresar un número de OP")
            else:
                try:
                    supabase.table("ordenes_planeadas").insert(payload).execute()
                    st.success("✅ Orden Guardada Correctamente")
                    time.sleep(1); st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

# --- ÁREAS DE PRODUCCIÓN (IMPRESIÓN, CORTE, ETC) ---
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.title(f"Módulo: {area_act}")
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    cols = st.columns(4)
    
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols[idx % 4]:
            if m in activos:
                st.error(f"● {m} - {activos[m]['op']}")
                if st.button(f"Gestionar {m}", key=f"btn_{m}"):
                    st.session_state.rep = activos[m]
            else:
                st.success(f"○ {m} - LIBRE")
                ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
                if ops:
                    sel = st.selectbox(f"OP para {m}", [o['op'] for o in ops], key=f"sel_{m}")
                    if st.button(f"Iniciar {m}", key=f"start_{m}"):
                        d = next(o for o in ops if o['op'] == sel)
                        supabase.table("trabajos_activos").insert({
                            "maquina": m, "area": area_act, "op": d['op'], 
                            "trabajo": d['nombre_trabajo'], "hora_inicio": datetime.now().strftime("%H:%M")
                        }).execute()
                        st.rerun()

    if 'rep' in st.session_state:
        rm = st.session_state.rep
        with st.expander(f"FINALIZAR TAREA: {rm['maquina']}", expanded=True):
            st.write(f"Trabajando en: **{rm['op']}**")
            parcial = st.checkbox("¿Es Entrega Parcial?")
            c1, c2 = st.columns(2)
            if c1.button("🏁 COMPLETAR"):
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
