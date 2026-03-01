import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import io

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V26", page_icon="🏭")

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
    .info-box { background-color: #f8f9fa; border-left: 5px solid #0d47a1; padding: 10px; margin-bottom: 5px; border-radius: 4px; }
    </style>
    """, unsafe_allow_html=True)

MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

if 'sel_tipo' not in st.session_state: st.session_state.sel_tipo = None
if 'detalle_op_id' not in st.session_state: st.session_state.detalle_op_id = None

with st.sidebar:
    st.title("🏭 NUVE V26")
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

# --- SEGUIMIENTO ---
elif menu == "🔍 Seguimiento":
    st.title("Seguimiento y Registro Histórico")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    
    if res:
        df = pd.DataFrame(res)
        
        def to_excel_limpio(df_input, tipo=None):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                if tipo == "GENERAL":
                    df_f = df_input[df_input['tipo_orden'].str.contains("FORMAS", na=False)].dropna(axis=1, how='all')
                    df_r = df_input[df_input['tipo_orden'].str.contains("ROLLOS", na=False)].dropna(axis=1, how='all')
                    if not df_f.empty: df_f.to_excel(writer, index=False, sheet_name='FORMAS')
                    if not df_r.empty: df_r.to_excel(writer, index=False, sheet_name='ROLLOS')
                else:
                    df_unit = df_input.dropna(axis=1, how='all')
                    cols_to_drop = [c for c in ['id', 'detalles_partes_json'] if c in df_unit.columns]
                    df_unit.drop(columns=cols_to_drop).to_excel(writer, index=False, sheet_name='DETALLE_OP')
            return output.getvalue()

        st.download_button("📥 Descargar Reporte General", to_excel_limpio(df, "GENERAL"), "Reporte_General.xlsx")

        st.write("---")
        h1, h2, h3, h4, h5, h6 = st.columns([1, 2, 2, 2, 2, 1])
        h1.write("**OP**"); h2.write("**Cliente**"); h3.write("**Trabajo**"); h4.write("**Tipo**"); h5.write("**Ubicación**"); h6.write("**Ver**")
        st.divider()

        for index, row in df.iterrows():
            r1, r2, r3, r4, r5, r6 = st.columns([1, 2, 2, 2, 2, 1])
            r1.write(row['op'])
            r2.write(row['cliente'])
            r3.write(row['nombre_trabajo'])
            r4.write(row['tipo_orden'])
            color = "#FF9800" if row['proxima_area'] != "FINALIZADO" else "#4CAF50"
            r5.markdown(f"<span style='color:{color}; font-weight:bold;'>{row['proxima_area']}</span>", unsafe_allow_html=True)
            if r6.button("👁️", key=f"v_{row['op']}"):
                st.session_state.detalle_op_id = row['op']

        if st.session_state.detalle_op_id:
            d = df[df['op'] == st.session_state.detalle_op_id].iloc[0].to_dict()
            st.markdown("---")
            with st.container():
                st.subheader(f"📋 DETALLE TÉCNICO - OP: {d['op']}")
                st.download_button("📥 Descargar Ficha Excel", to_excel_limpio(pd.DataFrame([d])), f"OP_{d['op']}.xlsx")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("<div class='info-box'><b>COMERCIAL</b></div>", unsafe_allow_html=True)
                    st.write(f"**Cliente:** {d['cliente']}\n\n**Trabajo:** {d['nombre_trabajo']}")
                with c2:
                    st.markdown("<div class='info-box'><b>ESPECIFICACIONES</b></div>", unsafe_allow_html=True)
                    if "FORMAS" in d['tipo_orden']:
                        st.write(f"**Cantidad:** {d['cantidad_formas']} | **Partes:** {d['num_partes']}")
                        st.write(f"**Perforaciones:** {d['perforaciones_detalle']}")
                        st.write(f"**C. Barras:** {d['codigo_barras_detalle']}")
                    else:
                        st.write(f"**Material:** {d['material']} | **Core:** {d['core']}")
                        st.write(f"**Empaque:** Bolsa {d['unidades_bolsa']} / Caja {d['unidades_caja']}")
                with c3:
                    st.markdown("<div class='info-box'><b>BITÁCORA</b></div>", unsafe_allow_html=True)
                    if d['historial_procesos']:
                        for p in d['historial_procesos']:
                            st.caption(f"✅ {p['area']} ({p['operario']})")
                
                if "FORMAS" in d['tipo_orden'] and d['detalles_partes_json']:
                    st.write("**DETALLE DE PAPELES:**")
                    st.table(pd.DataFrame(d['detalles_partes_json']))

                if st.button("❌ Cerrar"):
                    st.session_state.detalle_op_id = None
                    st.rerun()

# --- PLANIFICACIÓN (CON LOGICA SI/NO RESTAURADA) ---
elif menu == "📅 Planificación":
    st.title("Nueva Orden de Producción")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📑 FORMAS IMPRESAS"): st.session_state.sel_tipo = "FORMAS IMPRESAS"
    if c2.button("📄 FORMAS BLANCAS"): st.session_state.sel_tipo = "FORMAS BLANCAS"
    if c3.button("🌀 ROLLOS IMPRESOS"): st.session_state.sel_tipo = "ROLLOS IMPRESOS"
    if c4.button("⚪ ROLLOS BLANCOS"): st.session_state.sel_tipo = "ROLLOS BLANCOS"

    if st.session_state.sel_tipo:
        t = st.session_state.sel_tipo
        with st.form("form_v26", clear_on_submit=True):
            st.subheader(f"Configurando: {t}")
            f1, f2, f3 = st.columns(3)
            op_n = f1.text_input("Número de OP")
            op_a = f2.text_input("OP Anterior")
            cli = f3.text_input("Cliente")
            f4, f5 = st.columns(2)
            vend = f4.text_input("Vendedor")
            trab = f5.text_input("Nombre Trabajo")

            if "FORMAS" in t:
                g1, g2 = st.columns(2)
                cant_f = g1.number_input("Cantidad Formas", 0)
                partes = g2.selectbox("Partes", [1,2,3,4,5,6])
                
                # --- AQUÍ RESTAURAMOS EL PREGUNTAR SI/NO ---
                st.markdown("---")
                p1, p2 = st.columns(2)
                tiene_perf = p1.selectbox("¿Tiene Perforaciones?", ["NO", "SI"])
                perf_txt = p1.text_area("Describa Perforación") if tiene_perf == "SI" else "NO"
                
                tiene_barr = p2.selectbox("¿Tiene Código de Barras?", ["NO", "SI"])
                barr_txt = p2.text_area("Describa Código de Barras") if tiene_barr == "SI" else "NO"
                st.markdown("---")

                lista_p = []
                for i in range(1, partes + 1):
                    st.markdown(f"**PARTE {i}**")
                    d1, d2, d3, d4 = st.columns(4)
                    anc = d1.text_input(f"Ancho P{i}", key=f"a_{i}")
                    lar = d2.text_input(f"Largo P{i}", key=f"l_{i}")
                    pap = d3.text_input(f"Papel P{i}", key=f"p_{i}")
                    gra = d4.text_input(f"Gramos P{i}", key=f"g_{i}")
                    tf, tr = "N/A", "N/A"
                    if t == "FORMAS IMPRESAS":
                        t1, t2 = st.columns(2)
                        tf = t1.text_input(f"Tintas Frente P{i}", key=f"tf_{i}")
                        tr = t2.text_input(f"Tintas Respaldo P{i}", key=f"tr_{i}")
                    lista_p.append({"p":i, "anc":anc, "lar":lar, "tf":tf, "tr":tr})
                
                pres = st.selectbox("Presentación", ["LIBRETAS TAPADURA", "BLOCK LICOM", "HOJAS SUELTAS", "PAQUETES", "TACOS"])
                obs = st.text_area("Observaciones Generales")

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
                r6, r7 = st.columns(2)
                ub = r6.number_input("Cant x Bolsa", 0)
                uc = r7.number_input("Cant x Caja", 0)
                obs = st.text_area("Observaciones")

            if st.form_submit_button("🚀 GUARDAR ORDEN"):
                ruta = "IMPRESIÓN"
                if t == "ROLLOS BLANCOS": ruta = "CORTE"
                if t == "FORMAS BLANCAS": ruta = "COLECTORAS"
                
                payload = {"op": op_n.upper(), "op_anterior": op_a, "cliente": cli, "vendedor": vend, "nombre_trabajo": trab, "tipo_orden": t, "proxima_area": ruta}
                
                if "FORMAS" in t:
                    payload.update({"cantidad_formas": int(cant_f), "num_partes": partes, "perforaciones_detalle": perf_txt, "codigo_barras_detalle": barr_txt, "detalles_partes_json": lista_p, "presentacion": pres, "observaciones_formas": obs})
                else:
                    payload.update({"material": mat, "gramaje_rollos": gram, "ref_comercial": ref_c, "cantidad_rollos": int(cant_r), "core": core, "tintas_frente_rollos": tf_r, "tintas_respaldo_rollos": tr_r, "unidades_bolsa": int(ub), "unidades_caja": int(uc), "observaciones_rollos": obs})
                
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.session_state.sel_tipo = None
                st.success(f"Guardado. Próxima área: {ruta}")
                time.sleep(1); st.rerun()

# --- MÓDULOS DE PRODUCCIÓN ---
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.title(f"Área: {area_act}")
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    cols = st.columns(4)
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols[idx % 4]:
            if m in activos:
                st.error(f"● {m} - {activos[m]['op']}")
                if st.button(f"Terminar {m}", key=f"c_{m}"): st.session_state.rep = activos[m]
            else:
                st.success(f"○ {m} - LIBRE")
                ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
                if ops:
                    sel = st.selectbox(f"Asignar", [o['op'] for o in ops], key=f"s_{m}")
                    if st.button(f"Iniciar", key=f"i_{m}"):
                        d = next(o for o in ops if o['op'] == sel)
                        supabase.table("trabajos_activos").insert({"maquina":m,"area":area_act,"op":d['op'],"trabajo":d['nombre_trabajo'],"hora_inicio":datetime.now().strftime("%H:%M")}).execute()
                        st.rerun()

    if 'rep' in st.session_state:
        r = st.session_state.rep
        with st.expander(f"CERRAR TAREA EN {r['maquina']}", expanded=True):
            op_name = st.text_input("Operario")
            if st.button("🏁 COMPLETAR"):
                d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                tipo = d_op['tipo_orden']
                n_area = "FINALIZADO"
                if "ROLLOS" in tipo and area_act == "IMPRESIÓN": n_area = "CORTE"
                elif "FORMAS" in tipo:
                    if area_act == "IMPRESIÓN": n_area = "COLECTORAS"
                    elif area_act == "COLECTORAS": n_area = "ENCUADERNACIÓN"
