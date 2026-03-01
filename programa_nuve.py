import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V28 - TOTAL", page_icon="🏭")

# --- CONEXIÓN A SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS CSS (DISEÑO TÁCTIL Y INDUSTRIAL) ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; font-size: 18px !important; width: 100%; }
    .title-area { background-color: #0D47A1; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 22px; margin-bottom: 20px; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 20px; border-radius: 15px; text-align: center; color: #1B5E20; font-weight: bold; font-size: 18px; margin-bottom: 10px; }
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 20px; border-radius: 15px; text-align: center; color: #9E9E9E; font-size: 16px; margin-bottom: 10px; }
    .info-box { background-color: #f8f9fa; border-left: 5px solid #0d47a1; padding: 10px; margin-bottom: 5px; border-radius: 4px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES ---
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

PRESENTACIONES = ["LIBRETAS TAPADURA", "BLOCK LICOM", "HOJAS SUELTAS", "PAQUETES", "TACOS", "CAJAS", "ROLLOS"]

# --- ESTADOS DE SESIÓN ---
if 'sel_tipo' not in st.session_state: st.session_state.sel_tipo = None
if 'detalle_op_id' not in st.session_state: st.session_state.detalle_op_id = None
if 'rep' not in st.session_state: st.session_state.rep = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🏭 NUVE V28")
    menu = st.radio("MÓDULOS", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# --- FUNCIONES AUXILIARES ---
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
            if 'id' in df_unit.columns: df_unit = df_unit.drop(columns=['id'])
            df_unit.to_excel(writer, index=False, sheet_name='DETALLE_OP')
    return output.getvalue()

# ==========================================
# 1. MONITOR (BLOQUEADO/SIN CAMBIOS)
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
                    st.markdown(f"<div class='card-produccion'>{m}<br>{act[m]['op']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='card-vacia'>{m}<br>LIBRE</div>", unsafe_allow_html=True)
    time.sleep(30); st.rerun()

# ==========================================
# 2. SEGUIMIENTO (BLOQUEADO/SIN CAMBIOS)
# ==========================================
elif menu == "🔍 Seguimiento":
    st.title("Seguimiento Histórico")
    res = supabase.table("ordenes_planeadas").select("*").order("created_at", desc=True).execute().data
    if res:
        df = pd.DataFrame(res)
        st.download_button("📥 Reporte General Excel", to_excel_limpio(df, "GENERAL"), "Reporte_Nuve.xlsx")
        st.divider()
        for index, row in df.iterrows():
            r1, r2, r3, r4, r5, r6 = st.columns([1, 2, 2, 2, 2, 1])
            r1.write(row['op'])
            r2.write(row['cliente'])
            r3.write(row['nombre_trabajo'])
            r4.write(row['tipo_orden'])
            color = "#FF9800" if row['proxima_area'] != "FINALIZADO" else "#4CAF50"
            r5.markdown(f"<span style='color:{color}; font-weight:bold;'>{row['proxima_area']}</span>", unsafe_allow_html=True)
            if r6.button("👁️", key=f"v_{row['op']}"): st.session_state.detalle_op_id = row['op']

        if st.session_state.detalle_op_id:
            d = df[df['op'] == st.session_state.detalle_op_id].iloc[0].to_dict()
            st.markdown("---")
            with st.expander(f"Ficha: {d['op']}", expanded=True):
                c1, c2, c3 = st.columns(3)
                with c1: st.info(f"Cliente: {d['cliente']}\n\nTrabajo: {d['nombre_trabajo']}")
                with c2: st.write(f"Tipo: {d['tipo_orden']}\n\nEstado: {d['proxima_area']}")
                with c3:
                    if d['historial_procesos']:
                        for h in d['historial_procesos']: st.caption(f"✅ {h['area']} - {h['operario']}")
                if st.button("Cerrar"): st.session_state.detalle_op_id = None; st.rerun()

# ==========================================
# 3. PLANIFICACIÓN (TOTAL - RESTAURADA 100%)
# ==========================================
elif menu == "📅 Planificación":
    st.title("Planificación de Producción")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📑 FORMAS IMPRESAS"): st.session_state.sel_tipo = "FORMAS IMPRESAS"
    if c2.button("📄 FORMAS BLANCAS"): st.session_state.sel_tipo = "FORMAS BLANCAS"
    if c3.button("🌀 ROLLOS IMPRESOS"): st.session_state.sel_tipo = "ROLLOS IMPRESOS"
    if c4.button("⚪ ROLLOS BLANCOS"): st.session_state.sel_tipo = "ROLLOS BLANCOS"

    if st.session_state.sel_tipo:
        t = st.session_state.sel_tipo
        with st.form("form_full_plan", clear_on_submit=True):
            st.subheader(f"Nueva Orden: {t}")
            f1, f2, f3 = st.columns(3)
            op_n = f1.text_input("OP Número *").upper()
            op_a = f2.text_input("OP Anterior")
            cli = f3.text_input("Cliente *")
            f4, f5 = st.columns(2)
            vend = f4.text_input("Vendedor")
            trab = f5.text_input("Nombre Trabajo")

            if "FORMAS" in t:
                g1, g2 = st.columns(2)
                cant_f = g1.number_input("Cantidad Formas", 0)
                partes = g2.selectbox("Número de Partes", [1,2,3,4,5,6])
                p1, p2 = st.columns(2)
                t_perf = p1.selectbox("¿Tiene Perforaciones?", ["NO", "SI"])
                perf_d = p1.text_area("Detalle Perforación") if t_perf == "SI" else "NO"
                t_barr = p2.selectbox("¿Tiene Código de Barras?", ["NO", "SI"])
                barr_d = p2.text_area("Detalle Barras") if t_barr == "SI" else "NO"
                
                lista_p = []
                for i in range(1, partes + 1):
                    st.markdown(f"**DETALLE PARTE {i}**")
                    d1, d2, d3, d4, d5, d6 = st.columns(6)
                    anc = d1.text_input(f"Ancho P{i}", key=f"anc_{i}")
                    lar = d2.text_input(f"Largo P{i}", key=f"lar_{i}")
                    pap = d3.text_input(f"Papel P{i}", key=f"pap_{i}")
                    gra = d4.text_input(f"Gramos P{i}", key=f"gra_{i}")
                    tf = d5.text_input(f"T. Frente P{i}", value="N/A", key=f"tf_{i}")
                    tr = d6.text_input(f"T. Resp P{i}", value="N/A", key=f"tr_{i}")
                    lista_p.append({"p":i, "anc":anc, "lar":lar, "papel":pap, "gramos":gra, "tf":tf, "tr":tr})
                pres = st.selectbox("Presentación", PRESENTACIONES)
                obs = st.text_area("Observaciones Formas")

            else: # ROLLOS
                r1, r2, r3 = st.columns(3)
                mat = r1.text_input("Material")
                gram = r2.text_input("Gramaje")
                ref_c = r3.text_input("Ref. Comercial")
                r4, r5, r6 = st.columns(3)
                cant_r = r4.number_input("Cantidad Rollos", 0)
                core = r5.selectbox("Core", ["13MM", "19MM", "1 PULGADA", "40 MM", "2 PULGADAS", "3 PULGADAS"])
                tf_r = r6.text_input("Tintas Frente", value="N/A")
                tr_r = r1.text_input("Tintas Respaldo", value="N/A") # Reaprovecho r1 para no saturar
                u_bol = st.number_input("Cant x Bolsa", 0)
                u_caj = st.number_input("Cant x Caja", 0)
                obs = st.text_area("Observaciones Rollos")

            if st.form_submit_button("🚀 GUARDAR PLANIFICACIÓN"):
                ruta = "IMPRESIÓN"
                if t == "ROLLOS BLANCOS": ruta = "CORTE"
                if t == "FORMAS BLANCAS": ruta = "COLECTORAS"
                payload = {"op": op_n, "op_anterior": op_a, "cliente": cli, "vendedor": vend, "nombre_trabajo": trab, "tipo_orden": t, "proxima_area": ruta}
                if "FORMAS" in t:
                    payload.update({"cantidad_formas": int(cant_f), "num_partes": partes, "perforaciones_detalle": perf_d, "codigo_barras_detalle": barr_d, "detalles_partes_json": lista_p, "presentacion": pres, "observaciones_formas": obs})
                else:
                    payload.update({"material": mat, "gramaje_rollos": gram, "ref_comercial": ref_c, "cantidad_rollos": int(cant_r), "core": core, "tintas_frente_rollos": tf_r, "tintas_respaldo_rollos": tr_r, "unidades_bolsa": int(u_bol), "unidades_caja": int(u_caj), "observaciones_rollos": obs})
                supabase.table("ordenes_planeadas").insert(payload).execute()
                st.session_state.sel_tipo = None; st.success("Guardado!"); time.sleep(1); st.rerun()

# ==========================================
# 4. PRODUCCIÓN TÁCTIL (BLOQUES EDITADOS)
# ==========================================
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.markdown(f"<div class='title-area'>PANEL TÁCTIL: {area_act}</div>", unsafe_allow_html=True)
    
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    
    cols = st.columns(3)
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols[idx % 3]:
            if m in activos:
                tr = activos[m]
                st.markdown(f"<div class='card-produccion'>🟡 {m}<br>OP: {tr['op']}</div>", unsafe_allow_html=True)
                c_b1, c_b2 = st.columns(2)
                if c_b1.button(f"🛑 PARADA", key=f"p_{m}"):
                    st.toast(f"Parada registrada en {m}")
                if c_b2.button(f"✅ FINALIZAR", key=f"f_{m}"):
                    st.session_state.rep = tr
            else:
                st.markdown(f"<div class='card-vacia'>⚪ {m}<br>LIBRE</div>", unsafe_allow_html=True)
                ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
                if ops:
                    sel = st.selectbox("Asignar OP", [o['op'] for o in ops], key=f"s_{m}")
                    if st.button(f"🚀 INICIAR {m}", key=f"str_{m}"):
                        d = next(o for o in ops if o['op'] == sel)
                        supabase.table("trabajos_activos").insert({"maquina": m, "area": area_act, "op": d['op'], "trabajo": d['nombre_trabajo'], "hora_inicio": datetime.now().isoformat()}).execute()
                        st.rerun()

    # --- CIERRES TÉCNICOS POR ÁREA ---
    if st.session_state.rep:
        r = st.session_state.rep
        st.divider()
        with st.form("cierre_tecnico_v28"):
            st.warning(f"### CIERRE TÉCNICO: {area_act} | OP {r['op']}")
            op_name = st.text_input("Operario Responsable *")
            
            # --- LÓGICA DE CAMPOS SEGÚN ÁREA ---
            if area_act == "IMPRESIÓN":
                
                c1, c2, c3 = st.columns(3)
                metros = c1.number_input("Metros Impresos", 0)
                bobinas = c2.number_input("Cant. Bobinas", 0)
                imgs = c3.number_input("Imágenes x Bobina", 0)
                c4, c5, c6 = st.columns(3)
                tinta = c4.number_input("Tinta Gastada (Kg)", 0.0)
                planchas = c5.number_input("Planchas Gastadas", 0)
                desp = c6.number_input("Desperdicio", 0.0)
                mot_d = st.selectbox("Motivo Desperdicio", ["Arranque", "Falla Máquina", "Papel Defectuoso"])
                obs_t = st.text_area("Observaciones")

            elif area_act == "CORTE":
                
                c1, c2, c3 = st.columns(3)
                varillas = c1.number_input("Total Varillas", 0)
                rollos_c = c2.number_input("Total Rollos Cortados", 0)
                imgs_v = c3.number_input("Imágenes x Varilla", 0)
                c4, c5 = st.columns(2)
                cajas = c4.number_input("Cantidad Cajas", 0)
                desp = c5.number_input("Desperdicio Corte", 0.0)
                mot_d = st.selectbox("Motivo Desperdicio", ["Mal Corte", "Núcleo Dañado", "Medida Errónea"])
                obs_t = st.text_area("Observaciones")

            elif area_act == "COLECTORAS":
                
                c1, c2, c3 = st.columns(3)
                formas_p = c1.number_input("Cant. Formas Procesadas", 0)
                u_caja = c2.number_input("Unidades por Caja", 0)
                cant_c = c3.number_input("Cantidad de Cajas", 0)
                desp = st.number_input("Desperdicio", 0.0)
                mot_d = st.selectbox("Motivo Desperdicio", ["Falla Recolección", "Descuadre", "Papel Arrugado"])
                obs_t = st.text_area("Observaciones")

            elif area_act == "ENCUADERNACIÓN":
                
                c1, c2, c3 = st.columns(3)
                prod_t = c1.number_input("Total Producto", 0)
                cajas_t = c2.number_input("Cantidad de Cajas", 0)
                cant_pc = c3.number_input("Cantidad por Caja", 0)
                pres_f = st.selectbox("Presentación Final", PRESENTACIONES)
                desp = st.number_input("Desperdicio", 0.0)
                mot_d = st.selectbox("Motivo Desperdicio", ["Mal Pegado", "Corte Final Erróneo", "Falla Cosido"])
                obs_t = st.text_area("Observaciones")

            if st.form_submit_button("🏁 FINALIZAR TAREA"):
                if not op_name:
                    st.error("Debe ingresar el operario")
                else:
                    inicio = datetime.fromisoformat(r['hora_inicio'])
                    fin = datetime.now()
                    duracion = str(fin - inicio).split('.')[0]
                    d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                    
                    # RUTA DE FLUJO
                    n_area = "FINALIZADO"
                    if "ROLLOS" in d_op['tipo_orden'] and area_act == "IMPRESIÓN": n_area = "CORTE"
                    elif "FORMAS" in d_op['tipo_orden']:
                        if area_act == "IMPRESIÓN": n_area = "COLECTORAS"
                        elif area_act == "COLECTORAS": n_area = "ENCUADERNACIÓN"
                    
                    # GUARDAR HISTORIAL TÉCNICO
                    h = d_op['historial_procesos'] if d_op['historial_procesos'] else []
                    h.append({
                        "area": area_act, "maquina": r['maquina'], "operario": op_name,
                        "fecha": fin.strftime("%d/%m/%Y %H:%M"), "duracion": duracion,
                        "datos_cierre": {"desperdicio": desp, "motivo": mot_d, "obs": obs_t}
                    })
                    
                    supabase.table("ordenes_planeadas").update({"proxima_area": n_area, "historial_procesos": h}).eq("op", r['op']).execute()
                    supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()
                    
                    st.session_state.rep = None; st.success("¡OP Actualizada!"); time.sleep(1); st.rerun()
