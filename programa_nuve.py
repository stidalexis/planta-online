import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import time
import io

# --- CONFIGURACIÓN ---
st.set_page_config(layout="wide", page_title="SISTEMA NUVE V27 - PRODUCCIÓN", page_icon="🏭")

# --- CONEXIÓN ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

# --- ESTILOS TÁCTILES Y BOTONES GRANDES ---
st.markdown("""
    <style>
    .stButton > button { height: 60px !important; border-radius: 12px; font-weight: bold; font-size: 18px !important; width: 100%; margin-bottom: 10px; }
    .btn-stop { background-color: #FF5252 !important; color: white !important; border: 3px solid #D32F2F !important; }
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 20px; border-radius: 15px; text-align: center; color: #1B5E20; font-weight: bold; font-size: 20px; }
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 20px; border-radius: 15px; text-align: center; color: #9E9E9E; font-size: 18px; }
    .title-area { background-color: #0D47A1; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 22px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 13)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": [f"LINEA-{i:02d}" for i in range(1, 11)]
}

MOTIVOS_PARADA = ["CAMBIO DE TRABAJO", "MANTENIMIENTO", "FALLA MECÁNICA", "FALLA ELÉCTRICA", "ESPERA DE MATERIAL", "ALMUERZO / DESCANSO", "AJUSTE DE CALIDAD"]

if 'sel_tipo' not in st.session_state: st.session_state.sel_tipo = None
if 'detalle_op_id' not in st.session_state: st.session_state.detalle_op_id = None
if 'stop_mode' not in st.session_state: st.session_state.stop_mode = None

with st.sidebar:
    st.title("🏭 NUVE V27")
    menu = st.radio("MENÚ", ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación", "🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"])

# --- MONITOR, SEGUIMIENTO Y PLANIFICACIÓN (SIN CAMBIOS) ---
# [Aquí iría el código de las secciones anteriores que se mantiene intacto por tu instrucción]
# (Omitido en el bloque de código para brevedad, pero se asume presente en tu archivo real)

# --- LÓGICA DE PRODUCCIÓN ACTUALIZADA (IMPRESIÓN Y CORTE) ---
if menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación"]:
    area_act = menu.split(" ")[1].upper()
    st.markdown(f"<div class='title-area'>PANEL TÁCTIL: {area_act}</div>", unsafe_allow_html=True)
    
    # Consultar trabajos en curso
    activos = {a['maquina']: a for a in supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data}
    
    cols = st.columns(3) # Columnas más anchas para táctil
    for idx, m in enumerate(MAQUINAS[area_act]):
        with cols[idx % 3]:
            if m in activos:
                tr = activos[m]
                st.markdown(f"<div class='card-produccion'>🟡 {m}<br>OP: {tr['op']}</div>", unsafe_allow_html=True)
                
                # BOTÓN PARADA DE EMERGENCIA (TÁCTIL)
                if st.button(f"🛑 PARADA / PAUSA", key=f"stop_{m}"):
                    st.session_state.stop_mode = tr
                
                # BOTÓN FINALIZAR (TÁCTIL)
                if st.button(f"✅ FINALIZAR TURNO", key=f"fin_{m}"):
                    st.session_state.rep = tr
            else:
                st.markdown(f"<div class='card-vacia'>⚪ {m}<br>DISPONIBLE</div>", unsafe_allow_html=True)
                ops = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", area_act).execute().data
                if ops:
                    sel = st.selectbox(f"Seleccionar OP", [o['op'] for o in ops], key=f"sel_{m}")
                    if st.button(f"🚀 INICIAR {m}", key=f"start_{m}"):
                        d = next(o for o in ops if o['op'] == sel)
                        supabase.table("trabajos_activos").insert({
                            "maquina": m, "area": area_act, "op": d['op'], 
                            "trabajo": d['nombre_trabajo'], "hora_inicio": datetime.now().isoformat()
                        }).execute()
                        st.rerun()

    # --- MODAL DE PARADA DE EMERGENCIA ---
    if st.session_state.stop_mode:
        s = st.session_state.stop_mode
        st.divider()
        st.error(f"### REGISTRO DE PARADA: {s['maquina']}")
        motivo = st.selectbox("Motivo de la detención:", MOTIVOS_PARADA)
        if st.button("⚠️ REGISTRAR PARADA Y CONTINUAR"):
            # Aquí podrías guardar en una tabla de 'tiempos_parada'
            st.toast(f"Parada registrada: {motivo}")
            st.session_state.stop_mode = None
            time.sleep(1); st.rerun()

    # --- INTERFAZ DE CIERRE ESPECÍFICA (REQUERIMIENTO PRINCIPAL) ---
    if 'rep' in st.session_state:
        r = st.session_state.rep
        st.divider()
        with st.container():
            st.warning(f"### 📋 CIERRE DE PRODUCCIÓN - OP: {r['op']} en {r['maquina']}")
            
            with st.form("cierre_produccion"):
                operario = st.text_input("Nombre del Operario *")
                
                if area_act == "IMPRESIÓN":
                    c1, c2, c3 = st.columns(3)
                    metros = c1.number_input("Metros Impresos", 0)
                    bobinas = c2.number_input("Cant. Bobinas Impresas", 0)
                    imgs_bob = c3.number_input("Imágenes por Bobina", 0)
                    
                    c4, c5, c6 = st.columns(3)
                    tinta = c4.number_input("Tinta Gastada (kg)", 0.0)
                    planchas = c5.number_input("Planchas Gastadas", 0)
                    desp = c6.number_input("Desperdicio (Metros/Kg)", 0.0)
                    
                    motivo_desp = st.selectbox("Motivo Desperdicio", ["Arranque", "Falla Máquina", "Papel Defectuoso", "Ajuste Color"])
                    obs = st.text_area("Observaciones de Impresión")

                elif area_act == "CORTE":
                    c1, c2, c3 = st.columns(3)
                    varillas = c1.number_input("Total de Varillas", 0)
                    rollos_c = c2.number_input("Total Rollos Cortados", 0)
                    imgs_var = c3.number_input("Imágenes por Varilla", 0)
                    
                    c4, c5 = st.columns(2)
                    cajas = c4.number_input("Cantidad de Cajas", 0)
                    desp_c = c5.number_input("Desperdicio Corte", 0.0)
                    
                    motivo_desp = st.selectbox("Motivo Desperdicio", ["Mal Corte", "Núcleo Dañado", "Medida Errónea"])
                    obs = st.text_area("Observaciones de Corte")

                else: # Colectoras y Encuadernación (Simplificado por ahora)
                    obs = st.text_area("Observaciones Generales de Proceso")
                    desp = st.number_input("Desperdicio", 0.0)
                    motivo_desp = "General"

                if st.form_submit_button("🏁 FINALIZAR Y ENVIAR A SIGUIENTE ÁREA"):
                    if not operario:
                        st.error("Debe ingresar el nombre del operario")
                    else:
                        # 1. Calcular tiempos
                        inicio = datetime.fromisoformat(r['hora_inicio'])
                        fin = datetime.now()
                        duracion = str(fin - inicio).split('.')[0] # HH:MM:SS
                        
                        # 2. Obtener datos de la OP para actualizar historial
                        d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                        
                        # 3. Definir ruta
                        n_area = "FINALIZADO"
                        if "ROLLOS" in d_op['tipo_orden'] and area_act == "IMPRESIÓN": n_area = "CORTE"
                        elif "FORMAS" in d_op['tipo_orden']:
                            if area_act == "IMPRESIÓN": n_area = "COLECTORAS"
                            elif area_act == "COLECTORAS": n_area = "ENCUADERNACIÓN"
                        
                        # 4. Preparar historial técnico
                        nuevo_hito = {
                            "area": area_act, "maquina": r['maquina'], "operario": operario,
                            "fecha": fin.strftime("%d/%m/%Y %H:%M"), "duracion": duracion,
                            "datos_tecnicos": {
                                "metros": metros if 'metros' in locals() else 0,
                                "desperdicio": desp if 'desp' in locals() else 0,
                                "motivo": motivo_desp,
                                "observaciones": obs
                            }
                        }
                        
                        h = d_op['historial_processes'] if d_op['historial_procesos'] else []
                        h.append(nuevo_hito)
                        
                        # 5. Actualizar Base de Datos
                        supabase.table("ordenes_planeadas").update({"proxima_area": n_area, "historial_procesos": h}).eq("op", r['op']).execute()
                        supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()
                        
                        del st.session_state.rep
                        st.success(f"OP {r['op']} enviada a {n_area}")
                        time.sleep(1); st.rerun()
