import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, timedelta, time as time_cls 
import time
import io
from fpdf import FPDF
import pytz
import bcrypt
import qrcode

#  CONFIGURACION DE PAGINA 
st.set_page_config(layout="wide", page_title="SISTEMA C&B PAPELES V0.01 - TOTAL", page_icon="🏭")

#  CONEXION A SUPABASE 
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except Exception as e:
    st.error("Error de conexion a Base de Datos. Revisar los Secrets.")
    st.stop()
    
#  ESTILOS CSS (DISEÑO INDUSTRIAL Y TACTIL)
st.markdown("""
    <style>
    .stButton > button { height: 70px !important; border-radius: 15px; font-weight: bold; font-size: 20px !important; width: 100%; }
    .title-area { background-color: #0D47A1; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; font-size: 22px; margin-bottom: 20px; }
    
    /* MONITOR: Cartas con fondo vibrante y texto en NEGRO absoluto */
    .card-produccion { background-color: #00E676; border: 2px solid #00C853; padding: 20px; border-radius: 15px; text-align: center; color: #000000 !important; font-weight: bold; font-size: 18px; margin-bottom: 10px; }
    .card-vacia { background-color: #F5F5F5; border: 1px solid #E0E0E0; padding: 20px; border-radius: 15px; text-align: center; color: #000000 !important; font-size: 16px; margin-bottom: 10px; }
    
    .section-header { background-color: #F0F2F6; padding: 10px; border-radius: 8px; font-weight: bold; color: #0D47A1; margin-top: 15px; margin-bottom: 10px; border-left: 6px solid #0D47A1; }
    
    /* RADIOGRAFÍA: Cuadros blancos con texto en NEGRO */
    .metric-box { background-color: #ffffff; border: 1px solid #e0e0e0; padding: 12px; border-radius: 8px; margin-bottom: 5px; color: #000000 !important; line-height: 1.6; }
    .metric-box b { color: #000000 !important; }

    /* ESTILO PROFESIONAL PARA HISTORIAL EN PANTALLA */
    .historial-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        border-left: 5px solid #0D47A1;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .historial-header {
        display: flex;
        justify-content: space-between;
        font-weight: bold;
        color: #0D47A1;
        border-bottom: 1px solid #dee2e6;
        padding-bottom: 5px;
        margin-bottom: 10px;
    }
    .historial-tecnico {
        font-size: 0.9em;
        color: #333;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

#  CONSTANTES 
MAQUINAS = {
    "IMPRESIÓN": ["HR-22", "ATF-22", "HR-17", "DID-11", "HMT-22", "POLO-1", "POLO-2", "MTY-1", "MTY-2", "RYO-1", "FLX-1"],
    "CORTE": [f"COR-{i:02d}" for i in range(1, 15)],
    "COLECTORAS": ["COL-01", "COL-02"],
    "ENCUADERNACIÓN": ["JINNA", "KELLY", "VIVIANA", "ROSMIA", "ANGIE", "JOHANA.N", "MARTHA", "OLGA", "J0HANA.R", "ANY"],
    "REBOBINADORAS": ["REB-01", "REB-02", "REB-03"],
}

# RELACION INVERSA: dado el nombre de una maquina, saber a que area pertenece
MAQUINA_A_AREA = {maquina: area for area, lista in MAQUINAS.items() for maquina in lista}

# AREA -> ETIQUETA DE MENU (para construir el menu del maquinista segun su maquina)
AREA_A_MENU = {
    "IMPRESIÓN":      "🖨️ Impresión",
    "CORTE":          "✂️ Corte",
    "COLECTORAS":     "📥 Colectoras",
    "ENCUADERNACIÓN": "📕 Encuadernación",
    "REBOBINADORAS":  "🌀 Rebobinadoras",
}
PRESENTACIONES = ["BLOCK", "LIBRETA LICOM", "HOJAS SUELTAS", "PAQUETES", "TACOS", "CAJAS", "FAJILLAS", "FORMA CONTINUA"]
PRESENTACIONES2 = ["POR CABEZA", "IZQUIERDA", "DERECHA", "PATA", "N/A", ]
MOTIVOS_PARADA = ["Mantenimiento", "Falta de Material", "falta operario", "Limpieza", "Falla Electrica", "desayuno/desdcanso",]

#  USUARIOS ORGANIZADOS POR ROL 
def _es_hash_bcrypt(valor) -> bool:
    """Detecta si un valor guardado en 'clave' ya es un hash bcrypt (vs texto plano antiguo)."""
    return isinstance(valor, str) and valor.startswith(("$2a$", "$2b$", "$2y$"))


# Convierte una contrasena de texto plano en un hash seguro (bcrypt) para guardarla cifrada en la base de datos
def _hashear_clave(clave_texto: str) -> str:
    """Genera un hash bcrypt seguro a partir de una clave en texto plano."""
    return bcrypt.hashpw(clave_texto.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# Valida usuario y clave contra la tabla de usuarios en Supabase.
# Si la clave de ese usuario todavia estaba guardada sin cifrar (cuentas muy antiguas),
# la cifra automaticamente con bcrypt la primera vez que valida bien, sin que el usuario haga nada.
def validar_usuario_supabase(usuario_ingresado, clave_ingresada):
    """
    Valida usuario/clave contra Supabase usando hash bcrypt.
    Compatibilidad: si encuentra una clave antigua en texto plano que coincide,
    la migra automáticamente a hash bcrypt en ese mismo instante (sin pedirle
    nada al usuario ni requerir una migración manual aparte).
    """
    try:

# CONSULTA EN TABLA DE USUARIOS FILTRADA SOLO POR EL NOMBRE DE USUARIO
        respuesta = supabase.table("usuarios")\
            .select("*")\
            .eq("usuario", usuario_ingresado)\
            .execute()

        if not respuesta.data:
            return None

        fila_usuario = respuesta.data[0]
        clave_guardada = fila_usuario.get("clave", "") or ""

        if _es_hash_bcrypt(clave_guardada):
            try:
                coincide = bcrypt.checkpw(
                    clave_ingresada.encode("utf-8"),
                    clave_guardada.encode("utf-8")
                )
            except ValueError:
                coincide = False
            return fila_usuario if coincide else None

        if clave_guardada == clave_ingresada and clave_guardada != "":
            try:
                nuevo_hash = _hashear_clave(clave_ingresada)
                supabase.table("usuarios").update({"clave": nuevo_hash})\
                    .eq("usuario", usuario_ingresado).execute()
            except Exception:

# Si la migracion automatica falla, el login de hoy funciona igual;
                pass
            return fila_usuario

        return None
    except Exception as e:
        st.error(f"Error al conectar con la tabla de usuarios: {e}")
        return None

#  FUNCIONES AUXILIARES 
MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# Devuelve la fecha de creacion de una orden ya formateada como DD/MM/AAAA, lista para mostrar o imprimir
def _fecha_creacion_legible(row):
    """Devuelve la fecha de creacion de la OP en formato 'Mes DD del AAAA', en español (hora Colombia)."""
    raw = row.get('created_at') or row.get('fecha_creacion') or ''
    if not raw:
        return "-"
    fecha_dd_mm_aaaa = fmt_fecha_hora(raw, con_hora=False)  # 'DD/MM/AAAA' ya en hora Colombia
    try:
        dia, mes, anio = fecha_dd_mm_aaaa.split('/')
        return f"{MESES_ES.get(int(mes), mes)} {dia} del {anio}"
    except Exception:
        return fecha_dd_mm_aaaa or "-"

# Dibuja en el PDF la cajita con la fecha de creacion de la orden (se usa en rotulos y ordenes de produccion)
def dibujar_caja_fecha_creacion(pdf, row, x=145, y=4, w=63, h=16):
    """Escribe la fecha de creacion de la OP en la esquina opuesta al logo,
    solo como texto (sin caja ni fondo), a juego con el resto del encabezado.
    No mueve el cursor del PDF, lo deja igual que antes de llamarla."""
    x0, y0 = pdf.get_x(), pdf.get_y()

    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(x, y)
    pdf.set_font("Arial", "B", 8)
    pdf.cell(w, 5, "FECHA DE CREACIÓN", 0, 2, "R")
    pdf.set_x(x)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(w, 7, _fecha_creacion_legible(row), 0, 2, "R")

    pdf.set_xy(x0, y0)

# Escribe texto dentro de una celda del PDF reduciendo el tamano de letra si el texto no cabe, para que nunca se corte
def cell_fit(pdf, w, h, text, border=1):

    text = str(text)

    while pdf.get_string_width(text) > (w - 2):
        text = text[:-1]

    pdf.cell(w, h, text, border)

# Divide un texto largo en varias lineas para que quepa dentro del ancho (en mm) disponible en el PDF
def _lineas_ajustadas(pdf, texto, ancho_mm):
    """Parte un texto en lineas que caben dentro de ancho_mm con la fuente actual de pdf."""
    texto = str(texto) if texto is not None else ""
    if texto == "":
        return [""]
    palabras = texto.split(" ")
    lineas = []
    actual = ""
    for palabra in palabras:
        prueba = (actual + " " + palabra).strip() if actual else palabra
        if actual == "" or pdf.get_string_width(prueba) <= (ancho_mm - 2):
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas if lineas else [""]

# Dibuja una fila de celdas alineadas, tipo tabla, dentro del PDF
def fila_grid(pdf, celdas, h_linea=7):
    """
    Dibuja una fila de celdas lado a lado tipo grilla (como pdf.cell en serie),
    pero si el texto de una celda no cabe en una linea, en vez de salirse del
    recuadro pasa a la siguiente linea DENTRO de la misma celda. Toda la fila
    crece de alto segun la celda que mas lineas necesite.
    celdas: lista de dicts con: ancho, texto, negrita (bool), fill (bool), tam (pt, opcional)
    """
    x0, y0 = pdf.get_x(), pdf.get_y()

    listas_lineas = []
    for c in celdas:
        pdf.set_font("Arial", "B" if c.get("negrita") else "", c.get("tam", 10))
        listas_lineas.append(_lineas_ajustadas(pdf, c.get("texto", ""), c["ancho"]))

    n_lineas = max(len(l) for l in listas_lineas)
    alto_fila = n_lineas * h_linea

    x = x0
    for c, lineas in zip(celdas, listas_lineas):
        if c.get("fill"):
            pdf.set_fill_color(230, 230, 230)
            pdf.rect(x, y0, c["ancho"], alto_fila, "F")
        pdf.rect(x, y0, c["ancho"], alto_fila)
        pdf.set_font("Arial", "B" if c.get("negrita") else "", c.get("tam", 10))
        for i, linea in enumerate(lineas):
            pdf.set_xy(x + 1, y0 + (i * h_linea))
            pdf.cell(c["ancho"] - 2, h_linea, linea, border=0)
        x += c["ancho"]

    pdf.set_xy(x0, y0 + alto_fila)

# FUNCION DE HORARIOS
def hora_colombia():
    tz = pytz.timezone("America/Bogota")
    return datetime.now(tz)

# FUNCION CENTRAL DE FORMATO DE FECHAS: convierte cualquier fecha/hora que llegue de la base de datos
# (con o sin zona horaria, con o sin segundos) al formato unico DD/MM/AAAA HH:MM en hora Colombia
def fmt_fecha_hora(valor, con_hora=True):
    """
    Convierte CUALQUIER fecha/hora (string ISO con o sin zona horaria, en UTC,
    en Colombia, con microsegundos, etc.) al formato unico que debe usarse en
    TODO el programa: 'DD/MM/AAAA HH:MM' en hora Colombia, sin segundos.
    Si con_hora=False, devuelve solo 'DD/MM/AAAA'.
    Si el valor es vacio, None, o no se puede interpretar, lo devuelve tal cual
    (o '-' si esta vacio) para no romper nada que ya estuviera funcionando.
    """
    if valor is None or valor == "":
        return "-"
    if not isinstance(valor, (list, dict)):
        try:
            if pd.isna(valor):
                return "-"
        except (TypeError, ValueError):
            pass
    if isinstance(valor, (datetime,)):
        dt = valor
    else:
        try:
            texto = str(valor).strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(texto)
        except Exception:
            return valor
    try:
        tz_col = pytz.timezone("America/Bogota")
        if dt.tzinfo is None:
            dt = tz_col.localize(dt)
        else:
            dt = dt.astimezone(tz_col)
        return dt.strftime("%d/%m/%Y %H:%M") if con_hora else dt.strftime("%d/%m/%Y")
    except Exception:
        return valor

# Aplica fmt_fecha_hora a todas las columnas de fecha de una tabla (DataFrame) para mostrarla legible en pantalla
def formatear_fechas_df(df, columnas=None):
    """
    Aplica fmt_fecha_hora a las columnas de fecha de un DataFrame. Si no se
    especifican columnas, las detecta automaticamente por nombre (cualquier
    columna que contenga 'fecha', 'created_at', 'actualizacion', 'modificacion',
    'inicio', 'fin' o 'hora').
    """
    if df is None or len(df) == 0:
        return df
    if columnas is None:
        claves = ['fecha', 'created_at', 'actualizacion', 'modificacion', 'inicio', 'fin', 'hora']
        columnas = [c for c in df.columns if any(p in c.lower() for p in claves)]
    for c in columnas:
        if c in df.columns:
            df[c] = df[c].apply(fmt_fecha_hora)
    return df

# Consulta si la PLANTA ENTERA esta ACTIVA o DETENIDA (interruptor general que pausa el conteo de tiempos de todas las maquinas)
def get_planta_activa() -> bool:
    """Consulta si la planta está activa en Supabase. Cache 10 segundos."""
    cache_key = '_planta_activa_cache'
    cache_ts   = '_planta_activa_ts'
    ahora      = hora_colombia().timestamp()
    if cache_key in st.session_state and ahora - st.session_state.get(cache_ts, 0) < 10:
        return st.session_state[cache_key]
    try:
        res = supabase.table("configuracion_sistema").select("valor")\
              .eq("clave", "planta_activa").single().execute()
        activa = str(res.data.get("valor", "true")).lower() == "true"
    except:
        activa = True  
    st.session_state[cache_key] = activa
    st.session_state[cache_ts]  = ahora
    return activa

# Enciende o apaga el interruptor general de planta (solo lo usa el administrador, ej: para almuerzo general o corte de energia)
def set_planta_activa(estado: bool, usuario: str = "admin"):
    """Activa o desactiva la planta globalmente. Usa upsert por si la fila no existe."""
    supabase.table("configuracion_sistema").upsert({
        "id":         1,
        "clave":      "planta_activa",
        "valor":      "true" if estado else "false",
        "updated_at": hora_colombia().isoformat(),
        "updated_by": usuario
    }).execute()
    
    st.session_state.pop('_planta_activa_cache', None)
    st.session_state.pop('_planta_activa_ts', None)

# Consulta si un area especifica (Impresion, Corte, etc.) esta activa o detenida en este momento
def get_area_activa(area: str) -> bool:
    """Consulta si un AREA especifica esta activa (independiente del interruptor general). Cache 10 segundos."""
    cache_key = f'_area_activa_cache_{area}'
    cache_ts  = f'_area_activa_ts_{area}'
    ahora = hora_colombia().timestamp()
    if cache_key in st.session_state and ahora - st.session_state.get(cache_ts, 0) < 10:
        return st.session_state[cache_key]
    try:
        res = supabase.table("configuracion_sistema").select("valor")\
              .eq("clave", f"area_activa_{area}").single().execute()
        activa = str(res.data.get("valor", "true")).lower() == "true"
    except Exception:
# Si nunca se ha guardado un registro para esta area, se asume activa por defecto
        activa = True
    st.session_state[cache_key] = activa
    st.session_state[cache_ts]  = ahora
    return activa

# Enciende o apaga el interruptor de UN AREA especifica, sin afectar a las demas (solo administrador)
def set_area_activa(area: str, estado: bool, usuario: str = "admin"):
    """Activa o desactiva UN AREA especifica.
    NOTA TECNICA: la columna 'id' de esta tabla tiene un valor por defecto fijo
    en 1 (no es una secuencia autoincremental), porque originalmente solo se usaba
    para la fila de 'planta_activa'. Por eso aqui se calcula manualmente un id
    libre antes de insertar, en vez de confiar en el default de la base de datos."""
    clave = f"area_activa_{area}"
    payload = {
        "clave":      clave,
        "valor":      "true" if estado else "false",
        "updated_at": hora_colombia().isoformat(),
        "updated_by": usuario
    }
    try:
        existente = supabase.table("configuracion_sistema").select("id").eq("clave", clave).execute().data
        if existente:
# Ya existe esta clave -> solo actualizar, sin tocar el id
            supabase.table("configuracion_sistema").update(payload).eq("clave", clave).execute()
        else:
# Clave nueva -> calcular un id libre (max id actual + 1) en vez de usar el default roto
            todos_ids = supabase.table("configuracion_sistema").select("id").execute().data or []
            siguiente_id = max([fila.get("id", 0) or 0 for fila in todos_ids], default=0) + 1
            payload["id"] = siguiente_id
            supabase.table("configuracion_sistema").insert(payload).execute()
    except Exception as e:
        st.error(f"Error al guardar el estado del área {area}: {e}")

    st.session_state.pop(f'_area_activa_cache_{area}', None)
    st.session_state.pop(f'_area_activa_ts_{area}', None)

# FUNCION DE DURACION 
def calcular_duracion_laboral(inicio, fin, nombre_maquina=None, tiempo_pausa_segundos=0):
    """Calcula tiempo trabajado descontando pausas individuales y respetando estado de planta."""
    if nombre_maquina:
        if not obtener_estado_maquina(nombre_maquina):
            return "0:00:00"
        area_de_maquina = MAQUINA_A_AREA.get(nombre_maquina)
        if area_de_maquina and not get_area_activa(area_de_maquina):
            return "0:00:00"
    if not get_planta_activa():
        return "0:00:00"
    total = fin - inicio
    if total.total_seconds() < 0:
        return "0:00:00"
    
# Descontar pausas acumuladas 
    total_segundos = max(0, total.total_seconds() - tiempo_pausa_segundos)
    return str(timedelta(seconds=int(total_segundos)))
    
#  ROTULO DE CAJA 100x150mm CON QR
def generar_rotulo_pdf(row):
    tipo = (row.get('tipo_orden') or '').upper()
    if "FORMAS" in tipo:
        titulo = f"FORMAS {row.get('presentacion','-') or '-'}"
    elif "REBOBINADO" in tipo:
        titulo = "REBOBINADO - MATERIAL"
    else:
        titulo = f"ROLLO {row.get('material','-') or '-'}"

# GENERAR IMAGEN QR CON LA INFORMACION DE LA OP EN TEXTO PLANO
# LA CANTIDAD SE TOMA DE UN CAMPO DISTINTO SEGUN EL TIPO DE ORDEN
    if "FORMAS" in tipo:
        cantidad_total = row.get('cantidad_formas', '-') or '-'
    else:
        cantidad_total = row.get('cantidad_rollos', '-') or '-'

    texto_qr = (
        "ORDEN DE PRODUCCION\n"
        f"OP: {row.get('op','-')}\n"
        f"Cliente: {row.get('cliente','-') or '-'}\n"
        f"Trabajo: {row.get('nombre_trabajo','-') or '-'}\n"
        f"Referencia: {row.get('ref_comercial','-') or '-'}\n"
        f"Tipo: {row.get('tipo_orden','-') or '-'}\n"
        f"Unidades x Caja: {row.get('unidades_caja','-') or '-'}\n"
        f"Cantidad Total: {cantidad_total}"
    )
    qr_img = qrcode.make(texto_qr)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    qr_path_temp = f"/tmp/qr_{row.get('op','x')}.png"
    with open(qr_path_temp, "wb") as f_qr:
        f_qr.write(qr_buffer.getvalue())

    pdf = FPDF(orientation="P", unit="mm", format=(100, 150))
    pdf.add_page()
    pdf.set_margins(4, 4, 4)

# TITULO Y NUMERO DE OP
    pdf.set_font("Arial", "B", 22)
    pdf.set_xy(4, 8)
    pdf.cell(92, 11, titulo, align="C")

    pdf.set_font("Arial", "", 11)
    pdf.set_xy(4, 19)
    pdf.cell(92, 6, f"OP: {row.get('op','-')}", align="C")

    pdf.set_line_width(0.6)
    pdf.line(4, 28, 96, 28)

    y = 34
    def campo(label, valor, tam_valor=18):
        nonlocal y
        pdf.set_xy(4, y)
        pdf.set_font("Arial", "", 10)
        pdf.cell(92, 5, label)
        y += 6
        pdf.set_xy(4, y)
        pdf.set_font("Arial", "B", tam_valor)
        pdf.cell(92, 9, str(valor)[:40])
        y += 13

    campo("REFERENCIA COMERCIAL", row.get('ref_comercial', '') or '-')
    campo("UNIDADES POR CAJA", row.get('unidades_caja', '') or '-')

    pdf.line(4, y, 96, y)
    y += 6

# ZONA INFERIOR: IZQUIERDA INFO, DERECHA QR
    pdf.set_xy(4, y)
    pdf.set_font("Arial", "", 10)
    pdf.cell(58, 5, "NOMBRE TRABAJO")
    pdf.set_xy(4, y + 6)
    pdf.set_font("Arial", "B", 13)
    pdf.multi_cell(58, 7, str(row.get('nombre_trabajo', '') or '-')[:60])

    y2 = y + 28
    pdf.set_xy(4, y2)
    pdf.set_font("Arial", "", 10)
    pdf.cell(58, 5, "FECHA DE DESCARGA")
    pdf.set_xy(4, y2 + 6)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(58, 8, hora_colombia().strftime("%d/%m/%Y"))

    pdf.image(qr_path_temp, x=62, y=y + 3, w=34, h=34)
    pdf.set_xy(62, y + 38)
    pdf.set_font("Arial", "", 8)
    pdf.cell(34, 4, "INFORMACION OP", align="C")

    try:
        import os
        os.remove(qr_path_temp)
    except Exception:
        pass

    return bytes(pdf.output())

# GENERA EL PDF DE ORDEN DE PRODUCCION — version base/generica (encabezado y estructura comun del documento)
def generar_pdf_op(row):
    pdf = FPDF()
    pdf.add_page()
    
# ENCABEZADO INDUSTRIAL PDF CERTIFICADO 
    pdf.set_fill_color(13, 71, 161)
    pdf.rect(0, 0, 210, 40, 'F')

# LOGO CYB PAPELES
    pdf.image("logo_cb.png", 2, 2, 60)
    dibujar_caja_fecha_creacion(pdf, row)
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 20, f" CERTIFICADO DE PRODUCCION - OP: {row['op']}", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"TRABAJO: {row['nombre_trabajo']}", ln=True, align='C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(0.5)
    
#  SECCION DATOS DE VENTA PDF
    pdf.set_font("Arial", 'B', 11)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 8, " 1. INFORMACION GENERAL Y ORIGEN", ln=True, fill=True)
    pdf.set_font("Arial", '', 10)
    
    c1 = 100
    pdf.cell(c1, 7, f"Cliente: {row.get('cliente')}", border='B')
    pdf.cell(0, 7, f"Vendedor: {row.get('vendedor')}", border='B', ln=True)
    pdf.cell(c1, 7, f"Tipo de Orden: {row.get('tipo_orden')}", border='B')
    pdf.cell(0, 7, f"Fecha Creacion: {fmt_fecha_hora(row.get('created_at'), con_hora=False)}", border='B', ln=True)
    pdf.ln(5)

#  SECCION ESPECIFICACIONES PDF
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, " 2. ESPECIFICACIONES TECNICAS", ln=True, fill=True)
    pdf.set_font("Arial", '', 10)

    if "FORMAS" in row.get('tipo_orden', ''):
        pdf.cell(c1, 7, f"Cantidad: {row.get('cantidad_formas')}", border='B')
        pdf.cell(0, 7, f"Partes: {row.get('num_partes')}", border='B', ln=True)
        pdf.cell(c1, 7, f"Presentacion: {row.get('presentacion')}", border='B')
        pdf.cell(0, 7, f"Destino: {row.get('destino_formas', 'N/A')}", border='B', ln=True)
    else:
        pdf.cell(c1, 7, f"Material: {row.get('material')}", border='B')
        pdf.cell(0, 7, f"Gramaje: {row.get('gramaje_rollos')}g", border='B', ln=True)
        pdf.cell(c1, 7, f"Cantidad: {row.get('cantidad_rollos')}", border='B')
        pdf.cell(0, 7, f"Core: {row.get('core')}", border='B', ln=True)

    pdf.ln(5)

#  SECCION BITACORA TECNICA  
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 8, " 3. TRAZABILIDAD Y REGISTROS DE PLANTA", ln=True, fill=True)
    
    historial = row.get('historial_procesos', [])
    if not historial:
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 10, "Pendiente de procesamiento.", ln=True)
    else:
        for h in historial:
            pdf.ln(2)

# FILA DE TITULO DE AREA
            pdf.set_font("Arial", 'B', 10)
            pdf.set_fill_color(240, 245, 255)
            area_txt  = str(h.get('area','?')).encode('latin-1','replace').decode('latin-1')
            maq_txt   = str(h.get('maquina','?')).encode('latin-1','replace').decode('latin-1')
            op_txt    = str(h.get('operario') or h.get('usuario','N/A')).encode('latin-1','replace').decode('latin-1')
            aux_txt   = str(h.get('auxiliar','N/A')).encode('latin-1','replace').decode('latin-1')
            fecha_txt = str(h.get('fecha') or h.get('fin') or h.get('inicio',''))[:19].encode('latin-1','replace').decode('latin-1')
            dur_txt   = str(h.get('duracion','0:00:00')).encode('latin-1','replace').decode('latin-1')

            pdf.cell(0, 7, f" AREA: {area_txt} | MAQUINA: {maq_txt}", ln=True, fill=True, border=1)

# FILA DE RESPONSABLES POR OP
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(65, 6, f"Operador: {op_txt}", border='LR')
            pdf.cell(65, 6, f"Auxiliar: {aux_txt}", border='R')
            pdf.cell(0, 6, f"Fecha: {fecha_txt}", border='R', ln=True)

# FILA DE TIEMPOS TOMADOS POR OP
            pdf.cell(0, 6, f"Duracion del Proceso: {dur_txt}", border='LRB', ln=True)

# DATOS TECNICOS SALIDA JHSON
            pdf.set_font("Arial", '', 8)

            datos_c = h.get('datos_cierre', {})

            if datos_c:

                pdf.set_font("Arial", 'B', 7)
                pdf.set_fill_color(230,230,230)

# ENCABEZADOS TABLA
                pdf.cell(47,6,"OBJETO",1,0,'C',True)
                pdf.cell(48,6,"DATO",1,0,'C',True)
                pdf.cell(47,6,"OBJETO",1,0,'C',True)
                pdf.cell(48,6,"DATO",1,1,'C',True)

                pdf.set_font("Arial",'',8)

                items = list(datos_c.items())

                for i in range(0,len(items),2):

                    k1,v1 = items[i]
                    key1 = k1.replace("_"," ").upper()

                    if i+1 < len(items):
                        k2,v2 = items[i+1]
                        key2 = k2.replace("_"," ").upper()
                    else:
                        key2=""
                        v2=""

                    pdf.cell(47,6,key1,1)
                    pdf.cell(48,6,str(v1),1)
                    pdf.cell(47,6,key2,1)
                    pdf.cell(48,6,str(v2),1,1)
            
# BLOQUE OBSERVACIONES
            if h.get('observaciones'):
                pdf.set_font("Arial", 'I', 8)
                pdf.multi_cell(0, 5, f"OBSERVACIONES: {h['observaciones']}", border=1)
            else:
                pdf.cell(0, 1, "", ln=True, border='T')
            pdf.ln(2)

    pdf.ln(10)
    pdf.set_font("Arial", 'I', 7)
    pdf.cell(0, 10, f"DOCUMENTO OFICIAL C&B PAPELES - GENERADO AUTOMATICAMENTE - {hora_colombia().strftime('%d/%m/%Y %H:%M')}", align='C')
    
    return bytes(pdf.output())

# GENERA EL PDF DE ORDEN DE PRODUCCION — version para ROLLOS (impresos o blancos)
def generar_op_rollos(row):
    pdf = FPDF()
    pdf.add_page()

# LOGICA DE COLOR SEGUN ORDEN 
    tipo_op = row.get('tipo_origen', '').upper()

    if "NUEVA" in tipo_op:
        r, g, b = (40, 167, 69)      # VERDE
    elif "CAMBIOS" in tipo_op:
        r, g, b = (255, 0, 0)     # ROJO
    else:
        r, g, b = (13, 71, 161)     # AZUL

#  ENCABEZADO CON COLOR DINAMICO
    pdf.set_fill_color(r, g, b)
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.image("logo_cb.png", 2, 2, 60)
    dibujar_caja_fecha_creacion(pdf, row)
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 18, "ORDEN DE PRODUCCION - ROLLOS", 0, 1, "C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0,5,f"OP: {row['op']}   |   {row['tipo_origen']}",0,1,"C")
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

# INFORMACION GENERAL
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "1. INFORMACION DE LA ORDEN", 0, 1, fill=True)

    fila_grid(pdf, [
        {"ancho": 20, "texto": " Cliente: ", "negrita": True, "fill": True},
        {"ancho": 95, "texto": row.get('cliente',''), "negrita": False, "fill": False},
        {"ancho": 20, "texto": " Vendedor: ", "negrita": True, "fill": True},
        {"ancho": 55, "texto": row.get('vendedor',''), "negrita": False, "fill": False},
    ])
    fila_grid(pdf, [
        {"ancho": 20, "texto": " Trabajo: ", "negrita": True, "fill": True},
        {"ancho": 100, "texto": row.get('nombre_trabajo',''), "negrita": False, "fill": False},
        {"ancho": 25, "texto": " Tipo Orden: ", "negrita": True, "fill": True},
        {"ancho": 45, "texto": row.get('tipo_orden',''), "negrita": False, "fill": False},
    ])

#  ESPECIFICACIONES TECNICAS
    pdf.ln(4)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "2. ESPECIFICACIONES TECNICAS", 0, 1, fill=True)

    pdf.set_font("Arial", "B", 10); pdf.cell(20, 7, " Material: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(43, 7, f"{row.get('material','')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(20, 7, " Gramaje: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(43, 7, f"{row.get('gramaje_rollos','')} GRS", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(20, 7, " Core: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(44, 7, f"{row.get('core','')}", 1, 1) 
    pdf.set_font("Arial", "B", 10); pdf.cell(30, 7, " Cant. Rollos: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(33, 7, f"{row.get('cantidad_rollos','')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(30, 7, " Unid. Bolsa: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(33, 7, f"{row.get('unidades_bolsa','')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(30, 7, " Unid. Caja: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(34, 7, f"{row.get('unidades_caja','')}", 1, 1)
    pdf.set_font("Arial", "B", 10); pdf.cell(35, 7, " Ref. Comercial: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(100, 7, f"{row.get('ref_comercial','')}", 1, 0)
    trans = "SI" if row.get('transportadora_rollos') else "NO"
    pdf.set_font("Arial", "B", 10); pdf.cell(30, 7, " Transportadora: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(25, 7, f"{trans}", 1, 1) 
    pdf.set_font("Arial", "B", 10); pdf.cell(20, 8, "Impresión", 1, 0, 'C', fill=True)
    pdf.set_font("Arial", "B", 10); pdf.cell(27, 8, " Frente: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(65, 8, f"{row.get('tintas_frente_rollos', 'N/A')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(23, 8, " Respaldo: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(55, 8, f"{row.get('tintas_respaldo_rollos', 'N/A')}", 1, 1) 
    pdf.set_font("Arial", "B", 10); pdf.cell(25, 7, " Destino: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(165, 7, f"{row.get('destino_rollos','PLANTA')}", 1, 1)

# OBSERFVACIONES Y PERFORACIONES 
    pdf.ln(4); pdf.set_font("Arial", "B", 11); 
    pdf.cell(0, 8, "3. ADICIONALES Y OBSERVACIONES", 0, 1, fill=True)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, f"Perforaciones: {row.get('perforaciones_detalle', 'NO')}", 1, 1)
    pdf.set_text_color(255, 0, 0)
    pdf.multi_cell(0, 7, f"Observaciones: {row.get('observaciones_rollos','')}", 1)

# FIRMAS O SELLOS
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4); pdf.set_font("Arial", "B", 11); 
    pdf.cell(0, 8, "4. FIRMAS", 0, 1, fill=True)
    pdf.ln(1); pdf.set_font("Arial", "B", 6)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(63, 6, "COORDINADORA COMERCIAL", 1, 0, "C", fill=True) 
    pdf.cell(63, 6, "ASESOR", 1, 0, "C", fill=True) 
    pdf.cell(64, 6, "SUPERVISOR DE PRODUCCION", 1, 1, "C", fill=True)
    pdf.cell(63, 20, "", 1, 0); pdf.cell(63, 20, "", 1, 0); pdf.cell(64, 20, "", 1, 1)

# DATOS DE ESTIBAS 
    pdf.set_font("Arial", "", 11)
    y_est = pdf.get_y() + 2
    pdf.set_xy(10, y_est)
    pdf.set_fill_color(210, 210, 210); pdf.set_font("Arial", 'B', 11)
    pdf.cell(190, 5, "5 .REPORTE DE CAJAS POR ESTIBAS (PRODUCCIÓN)", 1, 1, 'C', True)
    
    w_e = 190 / 3
    pdf.set_font("Arial", '', 8)
    for i in range(4): 
        pdf.cell(w_e, 7, f" ESTIBA {i*3+1} | Cant:_________H:___________", 1, 0)
        pdf.cell(w_e, 7, f" ESTIBA {i*3+2} | Cant:_________H:___________", 1, 0)
        pdf.cell(w_e, 7, f" ESTIBA {i*3+3} | Cant:_________H:___________", 1, 1)

# OBSERVACIONES FINALIZADO
    pdf.set_font("Arial", "B", 8)
    pdf.cell(130, 8, "OBSERVACIONES FINALIZADO", 1, 0, "C"); pdf.cell(60, 8, "RECIBE", 1, 1, "C")
    pdf.set_font("Arial", "", 7)
    for _ in range(2):
        pdf.cell(130, 6, "", 1, 0); pdf.cell(60, 6, "", 1, 1)

# PIE
    pdf.set_font("Arial", "I", 6)
    pdf.cell(0, 5, f"SISTEMA C&B PAPELES - {hora_colombia().strftime('%d/%m/%Y %H:%M')}", 0, 1, "C")

    return bytes(pdf.output())


# GENERAR PDF FORMAS       
def generar_op_formas(row):
    pdf = FPDF()
    pdf.add_page()
    
    tipo_op = row.get('tipo_origen', '').upper()

# ENCABEZADO DINAMICO
    if "NUEVA" in tipo_op:
        r, g, b = (40, 167, 69)      # VERDE
    elif "CAMBIOS" in tipo_op:
        r, g, b = (255, 0, 0)     # ROJO
    else:
        r, g, b = (13, 71, 161)     # AZUL

# ENCABEZADO CON COLOR DINAMICO
    pdf.set_fill_color(r, g, b)
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.image("logo_cb.png", 2, 2, 60)
    dibujar_caja_fecha_creacion(pdf, row)

    pdf.set_text_color(255,255,255)
    pdf.set_font("Arial","B",16)
    pdf.cell(0,18,"ORDEN DE PRODUCCION - FORMAS",0,1,"C")
    pdf.set_font("Arial","B",12)
    pdf.cell(0,5,f"OP: {row['op']}   |   {row['tipo_origen']}",0,1,"C")
    pdf.set_text_color(0,0,0)
    pdf.ln(4)

#  INFORMACION DE LA ORDEN 
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "1. INFORMACION DE LA ORDEN", 0, 1, fill=True)
    fila_grid(pdf, [
        {"ancho": 25, "texto": " Cliente: ", "negrita": True, "fill": True},
        {"ancho": 70, "texto": row.get('cliente',''), "negrita": False, "fill": False},
        {"ancho": 25, "texto": " Vendedor: ", "negrita": True, "fill": True},
        {"ancho": 70, "texto": row.get('vendedor',''), "negrita": False, "fill": False},
    ])
    fila_grid(pdf, [
        {"ancho": 25, "texto": " Trabajo: ", "negrita": True, "fill": True},
        {"ancho": 70, "texto": row.get('nombre_trabajo',''), "negrita": False, "fill": False},
        {"ancho": 25, "texto": " Tipo Orden: ", "negrita": True, "fill": True},
        {"ancho": 70, "texto": row.get('tipo_orden',''), "negrita": False, "fill": False},
    ])
    fila_grid(pdf, [
        {"ancho": 25, "texto": " OP Anterior: ", "negrita": True, "fill": True},
        {"ancho": 70, "texto": row.get('op_anterior',''), "negrita": False, "fill": False},
        {"ancho": 25, "texto": " Fecha: ", "negrita": True, "fill": True},
        {"ancho": 70, "texto": fmt_fecha_hora(row.get('created_at'), con_hora=False), "negrita": False, "fill": False},
    ])

# ESPECIFICACIONES GENERALES Y ACABADOS 
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "2. ESPECIFICACIONES GENERALES Y ACABADOS", 0, 1, fill=True)
    pdf.set_font("Arial", "B", 10); pdf.cell(23, 7, " Cantidad: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(40, 7, f"{row.get('cantidad_formas','')}FORMAS", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(18, 7, " Partes: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(45, 7, f"{row.get('num_partes','')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(26, 7, " Presentación: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(38, 7, f"{row.get('presentacion','')}", 1, 1)
    pdf.set_font("Arial", "B", 10); pdf.cell(35, 7, " Numeración Del: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(60, 7, f"{row.get('num_id','NO')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(35, 7, " Numeración Al: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(60, 7, f"{row.get('num_fd','')}", 1, 1)
    pdf.set_font("Arial", "B", 10); pdf.cell(35, 7, " Código Barras: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(90, 7, f"{row.get('codigo_barras_detalle','')}", 1, 0)
    trans = "SI" if row.get('transportadora_formas') else "NO"
    pdf.set_font("Arial", "B", 10); pdf.cell(30, 7, " Transportadora: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(35, 7, f"{trans}", 1, 1)
    pdf.set_font("Arial", "B", 10); pdf.cell(25, 7, " Tipo Pegue: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(70, 7, f"{row.get('presentacion2', 'N/A')}", 1, 0)
    pdf.set_font("Arial", "B", 10); pdf.cell(25, 7, " Destino: ", 1, 0, fill=True)
    pdf.set_font("Arial", "", 10);  pdf.cell(70, 7, f"{row.get('destino_formas','NO APLICA')}", 1, 1)

# PERFORACIONES
    pdf.ln(4)
    pdf.set_font("Arial","B",11)
    pdf.cell(0,8,"3. PERFORACIONES",0,1,fill=True)
    pdf.set_font("Arial","",10)
    pdf.multi_cell(0,7,row.get("perforaciones_detalle","SIN PERFORACIONES"), 1)

# DETALLE TECNICO POR PARTE
    pdf.ln(4)
    pdf.set_font("Arial","B",11)
    pdf.cell(0,8,"4. DETALLE TECNICO POR PARTE",0,1,fill=True)
    pdf.set_font("Arial","B",8)
    pdf.set_fill_color(200,200,200)
    pdf.cell(4,7,"P",1,0,"C",True)
    pdf.cell(15,7,"ANCHO",1,0,"C",True)
    pdf.cell(15,7,"LARGO",1,0,"C",True)
    pdf.cell(28,7,"PAPEL",1,0,"C",True)
    pdf.cell(20,7,"COLOR",1,0,"C",True)
    pdf.cell(12,7,"GR",1,0,"C",True)
    pdf.cell(50,7,"T. FRENTE",1,0,"C",True)
    pdf.cell(23,7,"T. RESP",1,0,"C",True)
    pdf.cell(23,7,"OBS",1,1,"C",True)

    pdf.set_font("Arial","",7.5)
    partes = row.get("detalles_partes_json",[])
    for p in partes:
        cell_fit(pdf,4,7,p.get("p",""))
        cell_fit(pdf,15,7,p.get("anc",""))
        cell_fit(pdf,15,7,p.get("lar",""))
        cell_fit(pdf,28,7,p.get("papel",""))
        cell_fit(pdf,20,7,p.get("color_fondo",""))
        cell_fit(pdf,12,7,p.get("gramos",""))
        cell_fit(pdf,50,7,p.get("tf",""))
        cell_fit(pdf,23,7,p.get("tr",""))
        cell_fit(pdf,23,7,p.get("obs_parte","")) 
        pdf.ln()

# OBSERVACIONES GENERALES
    pdf.ln(5)
    pdf.set_font("Arial","B",11)
    pdf.set_text_color(255, 0, 0)
    pdf.cell(0,8,"5. OBSERVACIONES GENERALES",0,1,fill=True)
    pdf.set_font("Arial","",10)
    pdf.multi_cell(0,7,row.get("observaciones_formas",""), 1)

# FIRMAS
    pdf.ln(1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4); pdf.set_font("Arial", "B", 11); 
    pdf.cell(0, 8, "4. FIRMAS", 0, 1, fill=True)
    pdf.ln(1); pdf.set_font("Arial", "B", 6)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(63, 6, "COORDINADORA COMERCIAL", 1, 0, "C", fill=True) 
    pdf.cell(63, 6, "ASESOR", 1, 0, "C", fill=True) 
    pdf.cell(64, 6, "SUPERVISOR DE PRODUCCION", 1, 1, "C", fill=True)
    pdf.cell(63, 20, "", 1, 0); pdf.cell(63, 20, "", 1, 0); pdf.cell(64, 20, "", 1, 1)

    pdf.set_font("Arial","B",8)
    pdf.cell(130,8,"OBSERVACIONES",1,0,"C")
    pdf.cell(60,8,"RECIBE",1,1,"C")

    pdf.set_font("Arial", "B", 8)
    pdf.cell(130, 8, "OBSERVACIONES FINALIZADO", 1, 0, "C"); pdf.cell(60, 8, "RECIBE", 1, 1, "C")
    pdf.set_font("Arial", "", 7)
    for _ in range(2):
        pdf.cell(130, 6, "", 1, 0); pdf.cell(60, 6, "", 1, 1)

# PIE
    pdf.set_font("Arial", "I", 6)
    pdf.cell(0, 5, f"SISTEMA C&B PAPELES - {hora_colombia().strftime('%d/%m/%Y %H:%M')}", 0, 1, "C")

    return bytes(pdf.output())

# GENERA EL PDF DE ORDEN DE PRODUCCION — version para REBOBINADO
def generar_op_rebobinado(row):
    pdf = FPDF()
    pdf.add_page()
    
    tipo_op = row.get('tipo_origen', '').upper()

# ENCABEZADO 
    if "NUEVA" in tipo_op:
        r, g, b = (40, 167, 69)      # VERDE
    elif "CAMBIOS" in tipo_op:
        r, g, b = (255, 0, 0)     # ROJO
    else:
        r, g, b = (13, 71, 161)     # AZUL

#  ENCABEZADO CON COLOR DINAMICO
    pdf.set_fill_color(r, g, b)
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.image("logo_cb.png", 2, 2, 60)
    dibujar_caja_fecha_creacion(pdf, row)

    pdf.set_text_color(255,255,255)
    pdf.set_font("Arial","B",16)
    pdf.cell(0,18,"ORDEN DE PRODUCCION - REBOBINADO",0,1,"C")
    pdf.set_font("Arial","B",12)
    pdf.cell(0,5,f"OP: {row['op']}   |   {row['tipo_origen']}",0,1,"C")
    pdf.set_text_color(0,0,0)
    pdf.ln(4)

# INFORMACION GENERAL
    pdf.set_fill_color(230,230,230)
    pdf.set_font("Arial","B",11)
    pdf.cell(0,8,"1. INFORMACION GENERAL",0,1,fill=True)
    pdf.set_font("Arial","",10)

    fila_grid(pdf, [
        {"ancho": 95, "texto": f"Cliente: {row.get('cliente','')}", "negrita": False, "fill": False},
        {"ancho": 95, "texto": f"Vendedor: {row.get('vendedor','')}", "negrita": False, "fill": False},
    ])
    fila_grid(pdf, [
        {"ancho": 95, "texto": f"Trabajo: {row.get('nombre_trabajo','')}", "negrita": False, "fill": False},
        {"ancho": 95, "texto": f"OP Anterior: {row.get('op_anterior','N/A')}", "negrita": False, "fill": False},
    ])
    fila_grid(pdf, [
        {"ancho": 190, "texto": f"Fecha de Creacion: {fmt_fecha_hora(row.get('created_at'), con_hora=False)}", "negrita": False, "fill": False},
    ])

# DATOS TECNICOS DE ENTRADA Y OBJETIVO
    pdf.ln(4)
    pdf.set_font("Arial","B",11)
    pdf.cell(0,8,"2. DATOS TECNICOS Y OBJETIVO DEL PROCESO",0,1,fill=True)
    pdf.set_font("Arial","",10)

#  MATERIAL Y DIMENCIONES
    pdf.cell(63,7,f"Material Base: {row.get('material','')}",1)
    pdf.cell(63,7,f"Gramaje: {row.get('gramaje_rollos','')}g",1)
    pdf.cell(64,7,f"Referencia Comercial: {row.get('ancho_base','')}",1,1)

# CANTIDADES
    pdf.cell(95,7,f"Cantidad Rollos Solicitados: {row.get('cantidad_rollos','')}",1)
    pdf.cell(95,7,f"Tipo de Creacion: {row.get('tipo_creacion','NUEVA')}",1,1)

# OBJETIVO DE REBOBINADO (IMPRESION O PARA QUE )
    pdf.set_font("Arial","B",10)
    pdf.cell(190,7,"OBJETIVO PRINCIPAL DEL REBOBINADO:", "LTR", 1)
    pdf.set_font("Arial","",10)
    pdf.multi_cell(190,7, row.get('objetivo_rebobinado','No especificado'), "LRB")

# OBSERVACIONES DE PLANIFICACION
    pdf.ln(5)
    pdf.set_font("Arial","B",11)
    pdf.cell(0,8,"3. OBSERVACIONES ADICIONALES",0,1,fill=True)
    pdf.set_font("Arial","",10)
    pdf.multi_cell(0,7, row.get("observaciones_rollos","Sin observaciones adicionales"), 1)

# ESPACIO PARA ANOTACIONES DE PLANTA 
    pdf.ln(5)
    pdf.set_font("Arial","I",8)
    pdf.cell(0,5,"* Espacio reservado para el operario: verificar empalmes y diámetros finales.",0,1)

# PIE DE PAGINA
    pdf.ln(10)
    pdf.set_font("Arial","I",7)
    pdf.cell(0,10,f"SISTEMA C&B PAPELES - GENERADO: {hora_colombia().strftime('%d/%m/%Y %H:%M')}",0,1,"C")

    return bytes(pdf.output())

# RADIOGRAFIA TECNICA
@st.dialog("📋 RADIOGRAFÍA TÉCNICA DE LA ORDEN", width="large")
def modal_detalle_op(row):
    st.markdown(f"### OP: {row['op']} — {row['nombre_trabajo']}")
    st.write(f"🏭 **Estado en Planta:** `{row['proxima_area']}`")
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div class='section-header'>👤 DATOS GENERALES</div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class='metric-box'>
        👤 <b>Cliente:</b> {row.get('cliente')}<br>
        💼 <b>Vendedor:</b> {row.get('vendedor')}<br>
        📝 <b>Nombre trabajo:</b> {row.get('nombre_trabajo')}<br>
        📑 <b>referencia:</b> {row.get('ref_comercial')}<br>
        🔙 <b>orden anterior:</b> {row.get('op_anterior')}<br>
        📅 <b>Fecha:</b> {fmt_fecha_hora(row.get('created_at'), con_hora=False)}
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='section-header'>📐 ESPECIFICACIONES</div>", unsafe_allow_html=True)
        if "FORMAS" in row['tipo_orden']:
            st.markdown(f"""
            <div class='metric-box'>
            📦 <b>Cantidad:</b> {row.get('cantidad_formas')}<br>
            📑 <b>Partes:</b> {row.get('num_partes')}<br>
            🎨 <b>Presentación:</b> {row.get('presentacion')}<br>
            ⚠️ <b>Numeracion Desde:</b> {row.get('num_id')}<br>
            ⚠️ <b>Numeracion Hasta:</b> {row.get('num_fd')}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='metric-box'>
            📄 <b>Material:</b> {row.get('material')}<br>
            📏 <b>Gramaje:</b> {row.get('gramaje_rollos')}<br>
            📦 <b>unidades por caja:</b> {row.get('unidades_caja')}<br>
            🛍️ <b>unidades por bolsa:</b> {row.get('unidades_bolsa')}<br>
            📦 <b>Cantidad:</b> {row.get('cantidad_rollos')}
            </div>
            """, unsafe_allow_html=True)

    with col3:
        st.markdown("<div class='section-header'>⚙️ EXTRAS</div>", unsafe_allow_html=True)
        if "FORMAS" in row['tipo_orden']:
            st.markdown(f"""
            <div class='metric-box'>
            ✂️ <b>Perforación:</b> {row.get('perforaciones_detalle')}<br>
            🚚 <b>Transporte:</b> {row.get('transportadora_formas', 'NO')}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='metric-box'>
            🎨 <b>Tintas F:</b> {row.get('tintas_frente_rollos')}<br>
            🎨 <b>Tintas R:</b> {row.get('tintas_respaldo_rollos')}<br>
            🌀 <b>Core:</b> {row.get('core')}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div class='section-header'>📜 BITÁCORA DE PRODUCCIÓN PROFESIONAL</div>", unsafe_allow_html=True)
    hist = row.get('historial_procesos', [])
    if not hist:
        st.info("No hay registros de producción todavía.")
    else:
        for h in hist:

# TARJETA ESPECIAL PARA EDICIONES (no es un paso de produccion, es un cambio en los datos de la OP)
# Se usa startswith('EDIC') en vez de comparar el string completo, para que no falle
# por temas de codificacion de tildes (Ó) que a veces llegan distinto desde la base de datos.
            if (h.get('area') or '').strip().upper().startswith('EDIC') or (h.get('tipo') or '').strip().upper().startswith('EDIC'):
                motivo_edicion = (
                    h.get('observaciones')
                    or h.get('motivo')
                    or h.get('motivo_edicion')
                    or (h.get('nota', '').replace('Editado: ', '') if h.get('nota') else None)
                    or 'Sin motivo registrado'
                )
                with st.container():
                    st.markdown(f"""
                    <div class='historial-card'>
                        <div class='historial-header'>
                            <span>✏️ EDICIÓN DE LA ORDEN</span>
                            <span>📅 {h.get('fecha') or h.get('fin') or h.get('inicio') or 'Sin fecha'}</span>
                        </div>
                        <div class='historial-tecnico'>
                            <div>👤 <b>Editado por:</b> {h.get('operario') or h.get('usuario') or 'N/A'}</div>
                            <div>📝 <b>Motivo:</b> {motivo_edicion}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                continue

# DISENO DE TARGETAS DE DENTRADA
            with st.container():
                st.markdown(f"""
                <div class='historial-card'>
                    <div class='historial-header'>
                        <span>✅ {h['area']} — {h['maquina']}{' 🔄 ENTREGA PARCIAL' if h.get('tipo') == 'PARCIAL' else ''}</span>
                        <span>📅 {h.get('fecha') or h.get('fin') or h.get('inicio') or 'Sin fecha'}</span>
                    </div>
                    <div class='historial-tecnico'>
                        <div>👤 <b>Operario:</b> {h.get('operario') or h.get('usuario') or 'N/A'}</div>
                        <div>👥 <b>Auxiliar:</b> {h.get('auxiliar', 'N/A')}</div>
                        <div>⏱️ <b>Tiempo Proceso:</b> {h['duracion']}</div>
                        <div>📝 <b>Obs:</b> {h.get('observaciones', 'Sin observaciones')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
# VER DATOS DE CIERRE EN TABLA LIMPOA Y NO JHSON
                if h.get('datos_cierre'):
                    with st.expander("📊 Ver Datos Técnicos de Salida"):
                        df_datos = pd.DataFrame(list(h['datos_cierre'].items()), columns=['Parámetro', 'Valor'])
                        df_datos['Parámetro'] = df_datos['Parámetro'].str.replace('_', ' ').str.upper()
                        st.table(df_datos)

    st.divider()
    pdf_bytes = generar_pdf_op(row)
    st.download_button(label="🖨️ Descargar Certificado de Producción (PDF)", data=pdf_bytes, file_name=f"CERTIFICADO_{row['op']}.pdf", mime="application/pdf", use_container_width=True)

# ESTRUCTURA DE MENU  GENERAL 
if 'sel_tipo' not in st.session_state: st.session_state.sel_tipo = None
if 'rep' not in st.session_state: st.session_state.rep = None

# LOGIN PRINCIPAL  LOGUIN

if not st.session_state.get('autenticado'):
    st.title("🔐 Acceso al Sistema C&B PAPELES DE COLOMBIA S.A.S")
    
    with st.form("login_form"):
        user = st.text_input("Usuario")
        pw = st.text_input("Contraseña", type="password")
        boton_login = st.form_submit_button("Ingresar")
        
        if boton_login:
            datos_usuario = validar_usuario_supabase(user, pw)
            
            if datos_usuario:
                st.session_state['autenticado'] = True
                st.session_state['usuario_actual'] = datos_usuario['usuario']
                st.session_state['nombre_usuario'] = datos_usuario['nombre']
                st.session_state['rol'] = datos_usuario['rol']
                st.session_state['maquina_asignada'] = datos_usuario.get('maquina_asignada')
                st.success(f"Bienvenido {datos_usuario['nombre']}")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
    st.stop() 

# ESTRUCTURA DE MENU CON PERMISOS POR ROL
with st.sidebar:
    st.title("🏭 C&B PAPELES DE COLOMBIA S.A.S")
    
    rol = st.session_state.get('rol', 'operario').lower()
    
# DEFINICION DE PERMISOS SEGUN ROL
    if rol == 'admin':
        opciones_menu = ["🖥️ Monitor", "📆 Cronograma Impresión", "🔍 Seguimiento", "📅 Planificación", "🧐 Auditoría Ventas", "🖨️ Impresión", "✂️ Corte", "⏱️ Seguimiento Cortadoras", "📥 Colectoras", "📕 Encuadernación", "🌀 Rebobinadoras", "📦 Inventario", "📦 salida produccion P1", "📊 Reportes Admin", "🎨 Diseño y Pre-Prensa", "📦 Almacen/Despachos", "🛒 Mercado"]     
    elif rol == 'ventas':
        opciones_menu = ["🖥️ Monitor", "🔍 Seguimiento", "📅 Planificación"]
    elif rol == 'aud_ventas':
        opciones_menu = ["🖥️ Monitor", "🧐 Auditoría Ventas", "🔍 Seguimiento"]
    elif rol == 'jefe_log':
        opciones_menu = ["📦 salida produccion P1", "📊 Reportes Admin", "📦 Almacen/Despachos"]
    elif rol == 'patinador_log':
        opciones_menu = ["📦 Almacen/Despachos"]
    elif rol == 'aux_log':
        opciones_menu = ["📦 Almacen/Despachos"]
    elif rol == 'supervisor_imp':
        opciones_menu = ["🖥️ Monitor", "🖨️ Impresión", "📥 Colectoras", "📕 Encuadernación"]
    elif rol == 'supervisor_cor':
        opciones_menu = ["🖥️ Monitor", "✂️ Corte", "⏱️ Seguimiento Cortadoras"]
    elif rol == 'supervisor_enc':
        opciones_menu = ["🖥️ Monitor", "📕 Encuadernación"]
    elif rol == 'supervisor_reb':
        opciones_menu = ["🖥️ Monitor", "🌀 Rebobinadoras"]
    elif rol == 'patinador_roll':
        opciones_menu = ["📦 salida produccion P1"]
    elif rol == 'almacen':
        opciones_menu = ["📦 Almacen/Despachos"]
    elif rol == 'diseño':
        opciones_menu = ["🖥️ Monitor", "🎨 Diseño y Pre-Prensa", "🔍 Seguimiento"]
    elif rol in ('diseño1', 'diseño2', 'diseño3'):
        opciones_menu = ["🖥️ Monitor", "🎨 Diseño y Pre-Prensa", "🔍 Seguimiento"]
    elif rol == 'maquinista':
        mi_maquina = st.session_state.get('maquina_asignada')
        mi_area = MAQUINA_A_AREA.get(mi_maquina)
        mi_menu = AREA_A_MENU.get(mi_area)
        if mi_menu:
            opciones_menu = ["🖥️ Monitor", mi_menu]
        else:
            st.error("⛔ Este usuario no tiene una máquina asignada válida. Contacta al administrador.")
            opciones_menu = ["🖥️ Monitor"]
    else:

# OPERARIOS Y OTROS ROLES SI LOS DEJA DENTRAR
        opciones_menu = ["🖥️ Monitor"]

# 💬 MENSAJES SE AGREGA A TODOS LOS ROLES SIN EXCEPCION
    opciones_menu = opciones_menu + ["💬 Mensajes"]

# BADGE DE MENSAJES NO LEIDOS EN SIDEBAR
    try:
        _u = st.session_state.get('usuario_actual', '')
        _no_leidos = supabase.table("mensajes_internos")\
            .select("id", count="exact")\
            .eq("leido", False)\
            .eq("destinatario", _u)\
            .execute().count or 0
        if _no_leidos > 0:
            st.sidebar.info(f"💬 **{_no_leidos}** mensaje(s) sin leer")
    except Exception:
        pass

    menu = st.radio("SELECCIONE MÓDULO:", opciones_menu)
    
    st.divider()
    st.caption(f"Usuario: {st.session_state.get('usuario_actual')} | Rol: {rol}")
    
# BOTON DE CERRAR SESION
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    
    st.divider()
    st.info(f"Usuario: {st.session_state.get('nombre_usuario')}\n\nRol: {rol.upper()}")
    st.caption("Conectado a Supabase Cloud")

#  FUNCION PARA GESTION DE MAQUINAS   
def obtener_estado_maquina(nombre_maquina):
    try:
        res = supabase.table("estado_maquinas").select("estado").eq("maquina", nombre_maquina).execute()
        if res.data:
            return res.data[0]['estado']
        return True  # Si no existe en la tabla, asumimos que esta ON
    except:
        return True

# Cambia el estado ON/OFF de UNA maquina puntual (activa <-> fuera de servicio), usado por el administrador desde el Monitor
def cambiar_estado_maquina(nombre_maquina, nuevo_estado):
    try:
        supabase.table("estado_maquinas").upsert({
            "maquina": nombre_maquina,
            "estado": nuevo_estado,
            "ultima_modificacion": hora_colombia().isoformat()
        }).execute()
    except Exception as e:
        st.error(f"Error al cambiar estado: {e}")


# Calcula hace cuanto tiempo una maquina no tiene actividad, para sumar ese tiempo como "tiempo libre entre OPs" en las estadisticas
def obtener_ultima_actividad_maquina(nombre_maquina):
    """
    Busca en el historial de ordenes RECIENTES cual fue la ultima vez que esta
    maquina termino un paso de produccion (ultima fecha en historial_procesos).
    Esto reemplaza la logica anterior que buscaba en 'tiempos_muertos', la cual
    nunca podia arrancar porque dependia de un registro previo en esa misma tabla
    que nunca llegaba a crearse.
    Devuelve un datetime con zona horaria Colombia, o None si la maquina nunca ha trabajado.

    OPTIMIZACION: antes esta funcion traia el historial_procesos de TODAS las
    ordenes de TODA la historia de la empresa cada vez que alguien presionaba
    "INICIAR" en una maquina — con miles de ordenes historicas, eso volvia lenta
    esa accion tan frecuente. Ahora solo se piden las 400 ordenes creadas mas
    recientemente (mas que suficiente para encontrar la ultima actividad real de
    cualquier maquina, ya que ninguna maquina deberia llevar meses sin trabajar).
    """
    try:
        ops_data = (
            supabase.table("ordenes_planeadas")
            .select("historial_procesos")
            .order("created_at", desc=True)
            .limit(400)
            .execute().data or []
        )
    except Exception:
        return None

    tz = pytz.timezone("America/Bogota")
    ultima_fecha = None
    for o in ops_data:
        for paso in (o.get("historial_procesos") or []):
            if paso.get("maquina") == nombre_maquina and paso.get("fecha"):
                try:
                    f = datetime.strptime(paso["fecha"], "%d/%m/%Y %H:%M")
                    f = tz.localize(f)
                    if ultima_fecha is None or f > ultima_fecha:
                        ultima_fecha = f
                except Exception:
                    continue
    return ultima_fecha


# RUTA DE LA OP DESPUES DE SER REVISADA EN AUDITORIA VENTAS
# Es la misma logica que antes decidia la ruta inicial al crear la OP; ahora se usa
# despues de que el auditor de ventas la marca como revisada, no en el momento de crearla.
def ruta_despues_de_auditoria_ventas(tipo_orden):
    if tipo_orden == "FORMAS IMPRESAS":
        return "DISEÑO (AUDITORIA)"
    elif tipo_orden == "FORMAS BLANCAS":
        return "IMPRESIÓN"
    elif tipo_orden == "ROLLOS IMPRESOS":
        return "DISEÑO (AUDITORIA)"
    elif tipo_orden == "ROLLOS BLANCOS":
        return "CORTE"
    elif tipo_orden == "REBOBINADO":
        return "REBOBINADORAS"
    return "IMPRESIÓN"


# CALCULO DE TIEMPO EN AREA (desde que la OP entro al area actual hasta ahora o hasta que se cierra)
def _ultima_fecha_relevante_historial(historial):
    """
    Devuelve el datetime (hora Colombia) del ultimo paso 'real' del historial de una OP,
    ignorando las tarjetas de EDICION (esas no representan tiempo de ningun area, son
    solo un cambio de datos). Se usa como el momento en que la OP 'entro' a su area actual.
    """
    tz = pytz.timezone("America/Bogota")
    for h in reversed(historial or []):
        area_h = (h.get('area') or '').strip().upper()
        tipo_h = (h.get('tipo') or '').strip().upper()
        if area_h.startswith('EDIC') or tipo_h.startswith('EDIC'):
            continue
        raw = h.get('fecha') or h.get('fin') or h.get('inicio')
        if not raw:
            continue
        try:
            return tz.localize(datetime.strptime(raw, "%d/%m/%Y %H:%M"))
        except Exception:
            try:
                dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                return dt.astimezone(tz) if dt.tzinfo else tz.localize(dt)
            except Exception:
                continue
    return None


def calcular_tiempo_en_area(op_data):
    """
    Calcula cuanto tiempo lleva (o llevó) una OP en su area actual: desde el
    ultimo paso 'real' registrado en su historial (ignorando ediciones), o si
    todavía no tiene ningún paso, desde que se creó la OP. Se usa tanto para
    guardar cuanto duró un area al cerrarla (Diseño, Auditoria Ventas, etc.)
    como para mostrar en Trazabilidad cuánto lleva esperando una OP en el area
    donde está en este momento.
    Devuelve una tupla (segundos, texto 'H:MM:SS').
    """
    tz = pytz.timezone("America/Bogota")
    entrada = _ultima_fecha_relevante_historial(op_data.get('historial_procesos'))
    if entrada is None:
        raw_creacion = op_data.get('created_at') or op_data.get('fecha_creacion')
        if raw_creacion:
            try:
                dt = datetime.fromisoformat(str(raw_creacion).replace("Z", "+00:00"))
                entrada = dt.astimezone(tz) if dt.tzinfo else tz.localize(dt)
            except Exception:
                entrada = None
    if entrada is None:
        return 0, "N/A"
    segundos = max(0, (hora_colombia() - entrada).total_seconds())
    return segundos, str(timedelta(seconds=int(segundos)))


# RADIOGRAFIA COMPLETA DE UNA OP (vista de solo lectura con todos sus datos de creacion)
# Se usa tanto en Diseño y Pre-Prensa como en Auditoria Ventas, para revisar la orden
# antes de aprobarla o pasarla a la siguiente etapa.
def radiografia_completa_op(datos, mostrar_obs_auditoria1=True):
    st.markdown("### 📋 RADIOGRAFIA COMPLETA DE CREACION")

    with st.expander("🏢 INFORMACION COMERCIAL", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.write(f"**OP #:**\n{datos.get('op')}")
        c1.write(f"**OP ANTERIOR:**\n{datos.get('op_anterior')}")
        c2.write(f"**CLIENTE:**\n{datos.get('cliente')}")
        c2.write(f"**VENDEDOR:**\n{datos.get('vendedor')}")
        c3.write(f"**FECHA DE CREACION:**\n{fmt_fecha_hora(datos.get('created_at'))}")
        c3.write(f"**NOMBRE DEL TRABAJO:**\n{datos.get('nombre_trabajo')}")
        c4.write(f"**MATERIAL BASE:**\n{datos.get('material')}")
        c4.write(f"**GRAMAJE:**\n{datos.get('gramaje_rollos')}")

    with st.expander("⚙️ ESPECIFICACIONES TECNICAS", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown("**ADICIONALES ROLLOS**")
            st.write(f"**Tintas Frente:** {datos.get('tintas_frente_rollos')}")
            st.write(f"Tintas Respaldo: {datos.get('tintas_respaldo_rollos')}")
            st.write(f"Cantidad Solicitada: {datos.get('cantidad_rollos')}")
            st.write(f"Core: {datos.get('core')}")
        with c2:
            st.markdown("**ADICIONALES ROLLOS**")
            st.write(f"Referencia Comercial: {datos.get('ref_comercial')}")
            st.write(f"Unidades Por Bolsa: {datos.get('unidades_bolsa')}")
            st.write(f"Unidades Por Caja: {datos.get('unidades_caja')}")
            st.write(f"Repeticion : {datos.get('tipo_origen')}")
        with c3:
            st.markdown("**ADICIONALES FORMAS**")
            st.write(f"Perforaciones: {datos.get('perforaciones_detalle')}")
            st.write(f"Codigo De Barras: {datos.get('codigo_barras_detalle')}")
            st.write(f"Numeracion Inicial: {datos.get('num_id')}")
            st.write(f"Numeracion Final: {datos.get('num_fd')}")

        with c4:
            st.markdown("**ADICIONALES DE FORMAS**")
            st.write(f"Presentacion: {datos.get('presentacion')}")
            st.write(f"Encolada O Grapada Por: {datos.get('presentacion2', 0)}")
            st.write(f"Numero De Partes: {datos.get('num_partes', 0)}")
            st.write(f"Numero De Formas: {datos.get('cantidad_formas', 0)}")

    c_obs1, c_obs2 = st.columns(2)
    with c_obs1:
        st.info(f"**📝 OBSERVACIONES DE ROLLOS:**\n{datos.get('observaciones_rollos', 'Sin observaciones')}")
        st.info(f"**📝 OBSERVACIONES DE FORMAS:**\n{datos.get('observaciones_formas', 'Sin observaciones')}")
        if mostrar_obs_auditoria1:
            st.info(f"**📝 OBSERVACIONES DE AUDITORIA 1:**\n{datos.get('observaciones_diseno', 'Sin observaciones')}")
    with c_obs2:
        if datos.get('detalles_partes_json'):
            st.write("**📑 Estructura de Partes (Papel/Tintas):**")
            st.table(datos.get('detalles_partes_json'))
        else:
            st.write("**Tipo de Producto:** ROLLOS IMPRESOS")


# MODULO MONITOR 
if menu == "🖥️ Monitor":
    st.markdown("<div class='title-area'>🖥️ MONITOR DE PRODUCCIÓN EN TIEMPO REAL</div>", unsafe_allow_html=True)

#  INTERRUPTOR GLOBAL DE PLANTA (solo admin)
    if st.session_state.get('rol','').lower() == 'admin':
        planta_on = get_planta_activa()
        col_sw1, col_sw2, col_sw3 = st.columns([1, 2, 3])
        with col_sw1:
            nuevo_estado = st.toggle(
                "🏭 PLANTA ACTIVA" if planta_on else "⏸️ PLANTA DETENIDA",
                value=planta_on,
                key="toggle_planta"
            )
            if nuevo_estado != planta_on:
                set_planta_activa(nuevo_estado, st.session_state.get('nombre_usuario','admin'))
                accion = "▶️ PLANTA ACTIVADA" if nuevo_estado else "⏸️ PLANTA DETENIDA"
                st.toast(f"{accion} — todos los contadores {'corriendo' if nuevo_estado else 'congelados'}", icon="🏭")
                time.sleep(0.5)
                st.rerun()
        with col_sw2:
            if planta_on:
                st.success("✅ Planta activa — contadores corriendo")
            else:
                st.error("⏸️ Planta detenida — contadores congelados")
                try:
                    res_cfg = supabase.table("configuracion_sistema").select("updated_at,updated_by")\
                              .eq("clave","planta_activa").single().execute().data
                    if res_cfg:
                        st.caption(f"Detenida por **{res_cfg['updated_by']}** a las {str(res_cfg['updated_at'])[:16]}")
                except:
                    pass

        st.markdown("**⚙️ Interruptores por Área** (independientes del general — apagar una no afecta a las demás)")
        cols_areas = st.columns(len(MAQUINAS))
        for idx, area in enumerate(MAQUINAS.keys()):
            with cols_areas[idx]:
                area_on = get_area_activa(area)
                nuevo_area_st = st.toggle(
                    area if area_on else f"⏸️ {area}",
                    value=area_on,
                    key=f"toggle_area_{area}"
                )
                if nuevo_area_st != area_on:
                    set_area_activa(area, nuevo_area_st, st.session_state.get('nombre_usuario','admin'))
                    st.toast(f"Área {area} {'ACTIVADA' if nuevo_area_st else 'DESACTIVADA'}", icon="⚙️")
                    time.sleep(0.5)
                    st.rerun()
    else:
    
# Operarios solo ven el estado, no pueden cambiarlo
        if not get_planta_activa():
            st.error("⏸️ Planta detenida por administración — los contadores están en pausa")

        areas_apagadas = [a for a in MAQUINAS.keys() if not get_area_activa(a)]
        if areas_apagadas:
            st.warning(f"⏸️ Área(s) detenida(s) por administración: {', '.join(areas_apagadas)}")
    
#  TRAER ESTADOS DE MAQUINAS DE UN SOLO GOLPE 
    try:
        estados_db = supabase.table("estado_maquinas").select("maquina, estado").execute().data

        diccionario_estados = {item['maquina']: item['estado'] for item in estados_db}
    except Exception as e:
        st.error(f"Error al cargar estados: {e}")
        diccionario_estados = {}

# Traer datos de trabajos activos
    act_data = supabase.table("trabajos_activos").select("*").execute().data

# ALERTAS DE OP ESTANCADAS (Filtrando por ON/OFF)
    alertas = []
    for a in act_data:
        try:

# USA EL DICCIONARIO PARA NO BUSCAR EN LA SUPABASE
            if not diccionario_estados.get(a['maquina'], True):
                continue 
            
            inicio = datetime.fromisoformat(a["hora_inicio"].replace("Z", "+00:00"))

# PASA EL ESTADO ACTUAL ALA FUNCION 
            tiempo_texto = calcular_duracion_laboral(inicio, ahora, a['maquina'], a.get('tiempo_pausa', 0))
            
            h, m, s = map(int, tiempo_texto.split(':'))
            horas_laborales = h + m/60 + s/3600

            if horas_laborales > 4:  
                alertas.append(f"🚨 OP {a['op']} en {a['maquina']} lleva {round(horas_laborales,1)}h de trabajo activo")
        except Exception as e:
            print(f"Error en alerta: {e}")

    if alertas:
        st.error("🚨 ALERTAS DE PRODUCCIÓN:")
        for al in alertas:
            st.warning(al)

# ALERTAS DE 3+ DIAS (SOLO VISIBLES PARA ADMIN)
    if st.session_state.get('rol', '').lower() == 'admin':
        alertas_3d = []

# CASO 1: OP ACTIVA EN UNA MAQUINA QUE LLEVA 3+ DIAS SIN FINALIZARSE
        for a in act_data:
            try:
                if not diccionario_estados.get(a['maquina'], True):
                    continue
                inicio_a = datetime.fromisoformat(a["hora_inicio"].replace("Z", "+00:00"))
                dias_en_maquina = (hora_colombia() - inicio_a.astimezone(pytz.timezone("America/Bogota"))).days
                if dias_en_maquina >= 3:
                    alertas_3d.append(f"🕒 OP {a['op']} en {a['maquina']} lleva {dias_en_maquina} día(s) SIN FINALIZARSE en la máquina")
            except Exception as e:
                print(f"Error en alerta 3 dias (activa): {e}")

# CASO 2: OP CREADA HACE 3+ DIAS QUE NUNCA HA ENTRADO A NINGUNA MAQUINA
# OPTIMIZACION: se filtra "proxima_area != FINALIZADO" directo en la base de datos,
# en vez de traer TAMBIEN todas las ordenes finalizadas historicas solo para descartarlas despues.
        try:
            ops_espera = supabase.table("ordenes_planeadas").select(
                "op,cliente,nombre_trabajo,proxima_area,historial_procesos,created_at,fecha_creacion"
            ).neq("proxima_area", "FINALIZADO").execute().data or []
        except Exception:
            ops_espera = []

        ops_activas_ids = {str(a['op']) for a in act_data}
        for o in ops_espera:
            try:
                if (o.get('proxima_area') or '').upper() == "FINALIZADO":
                    continue
                if str(o.get('op')) in ops_activas_ids:
                    continue
                if o.get('historial_procesos'):
                    continue  # ya tuvo movimiento en algun momento, no aplica este caso
                raw_fecha = o.get('created_at') or o.get('fecha_creacion')
                if not raw_fecha:
                    continue
                dt_creacion = datetime.fromisoformat(str(raw_fecha).replace("Z", "")).replace(tzinfo=pytz.utc).astimezone(pytz.timezone("America/Bogota"))
                dias_sin_entrar = (hora_colombia() - dt_creacion).days
                if dias_sin_entrar >= 3:
                    alertas_3d.append(f"📋 OP {o.get('op')} ({o.get('cliente','')}) lleva {dias_sin_entrar} día(s) creada SIN ENTRAR a ninguna máquina")
            except Exception as e:
                print(f"Error en alerta 3 dias (creacion): {e}")

        if alertas_3d:
            st.markdown("---")
            with st.expander(f"🕒 {len(alertas_3d)} ALERTA(S) DE 3+ DÍAS — solo visibles para Admin", expanded=True):
                for al in alertas_3d:
                    st.warning(al)

# PREPARAR DATOS DE OPERACIONES 
# OPTIMIZACION: antes se traia "op,nombre_trabajo" de TODAS las ordenes de toda la
# historia solo para poder mostrar el nombre del trabajo en las tarjetas de maquinas
# activas. Ahora solo se piden los nombres de las OPs que realmente estan activas
# en alguna maquina en este momento (siempre son muy pocas).
    op_ids_activos = list({str(a['op']) for a in act_data}) if act_data else []
    if op_ids_activos:
        ops = supabase.table("ordenes_planeadas").select("op,nombre_trabajo").in_("op", op_ids_activos).execute().data or []
    else:
        ops = []
    map_ops = {o['op']: o['nombre_trabajo'] for o in ops}

    act = {}
    for a in act_data:
        op = a['op']
        a['nombre_trabajo'] = map_ops.get(op, "SIN NOMBRE")
        act[a['maquina']] = a
        
#  DIBUJAR INTERFAZ (Con logica de colores) 
    for area, maquinas in MAQUINAS.items():
        st.markdown(f"<div class='title-area'>{area}</div>", unsafe_allow_html=True)
        cols = st.columns(4)
        
        for idx, m in enumerate(maquinas):
            with cols[idx % 4]:

# Verificar si la maquina esta encendida en el diccionario
                esta_encendida = diccionario_estados.get(m, True)

                if not esta_encendida:

# TARJETA GRIS: Maquina apagada (Mantenimiento/etc)
                    st.markdown(
                        f"""<div style='background-color: #424242; color: #9E9E9E; padding: 20px; 
                        border-radius: 15px; text-align: center; border: 2px solid #212121;'>
                        <span style='font-size: 18px; font-weight: bold;'>{m}</span><br>
                        <span style='font-size: 14px;'>🚫 FUERA DE SERVICIO</span>
                        </div>""", 
                        unsafe_allow_html=True
                    )
                elif m in act:

# TARJETA  produccion
                    st.markdown(
                        f"<div class='card-produccion'>{m}<br>OP: {act[m]['op']}<br>{act[m]['nombre_trabajo']}</div>",
                        unsafe_allow_html=True
                    )
                else:

# TARJETA Libre
                    st.markdown(
                        f"<div class='card-vacia'>{m}<br>LIBRE</div>",
                        unsafe_allow_html=True
                    )

#  REFRESCO AUTOMATICO 
    try:
        from streamlit_autorefresh import st_autorefresh
        intervalo = st.select_slider(
            "🔄 Auto-refresco cada:",
            options=[15, 30, 60, 120],
            value=30,
            format_func=lambda x: f"{x} segundos"
        )
        st_autorefresh(interval=intervalo * 1000, key="monitor_refresh")
    except:
      
        col_ref = st.columns([3,1])[1]
        if col_ref.button("🔄 Actualizar ahora"):
            st.rerun()

# MODULO SEGUIMIENTO
elif menu == "🔍 Seguimiento":
    st.title("🔍 Seguimiento de Órdenes en Tiempo Real")
    
# TRAER TRABAJOS ACTIVOS (para saber que OP esta en que maquina)

    try:
        activos_res = supabase.table("trabajos_activos").select("op, maquina").execute()
        activos = activos_res.data or []
# DICCIONARIO DE OP EN MAQUINAS 
        op_en_maquina = {str(a['op']): a['maquina'] for a in activos}
    except Exception as e:
        st.error(f"Error al conectar con las tablas: {e}")
        op_en_maquina = {}

    busqueda = st.text_input("🔍 Filtrar por OP, Cliente, Trabajo o Vendedor:", "")

# OPTIMIZACION DE VELOCIDAD DE CARGA:
# Antes este modulo traia TODAS las OPs (activas + finalizadas de toda la historia) con select("*")
# y luego las separaba en Python. Eso significaba descargar y procesar tambien todas las OPs
# finalizadas historicas solo para mostrar la pestaña de pendientes. Ahora:
#  - Las PENDIENTES se piden directo filtradas en la base de datos (mucho mas liviano).
#  - Las FINALIZADAS solo traen, por defecto, las 200 mas recientes; si el usuario busca algo
#    especifico, la busqueda se hace directo en la base de datos sobre TODO el historico,
#    para no perder la posibilidad de encontrar una OP finalizada antigua.
    try:
        ordenes_pendientes = (
            supabase.table("ordenes_planeadas")
            .select("*")
            .neq("proxima_area", "FINALIZADO")
            .order("created_at", desc=True)
            .execute().data or []
        )
    except Exception as e:
        st.error(f"Error al cargar órdenes pendientes: {e}")
        ordenes_pendientes = []

    try:
        if busqueda:
            b_like = f"%{busqueda}%"
            ordenes_finalizadas = (
                supabase.table("ordenes_planeadas")
                .select("*")
                .eq("proxima_area", "FINALIZADO")
                .or_(f"op.ilike.{b_like},cliente.ilike.{b_like},nombre_trabajo.ilike.{b_like},vendedor.ilike.{b_like}")
                .order("created_at", desc=True)
                .execute().data or []
            )
        else:
            ordenes_finalizadas = (
                supabase.table("ordenes_planeadas")
                .select("*")
                .eq("proxima_area", "FINALIZADO")
                .order("created_at", desc=True)
                .limit(200)
                .execute().data or []
            )
    except Exception as e:
        st.error(f"Error al cargar órdenes finalizadas: {e}")
        ordenes_finalizadas = []

    if not ordenes_pendientes and not ordenes_finalizadas:
        st.warning("No hay órdenes registradas.")
    else:

# TABS DE SEGUIMIENTO: PENDIENTES / FINALIZADAS
        tab_pendientes, tab_finalizadas = st.tabs(["⏳ EN PROCESO / PENDIENTES", "✅ FINALIZADAS"])

        if not busqueda:
            st.caption(f"Mostrando las {len(ordenes_finalizadas)} órdenes finalizadas más recientes. Usa el buscador para encontrar cualquier OP histórica.")

# ALERTA DE OPs QUIETAS (5+ DIAS SIN MOVIMIENTO) — SOLO VISIBLE PARA ADMIN
        rol_seg_actual = st.session_state.get('rol', '').lower()
        if rol_seg_actual == 'admin':
            tz_col = pytz.timezone("America/Bogota")
            ahora_seg = hora_colombia()
            alertas_quietas = []
            for r in ordenes_pendientes:
                try:
                    ultima_dt = None
                    hist_r = r.get('historial_procesos') or []
                    if hist_r:
                        raw_ult = hist_r[-1].get('fecha') or hist_r[-1].get('fin') or hist_r[-1].get('inicio')
                        if raw_ult:
                            try:
                                ultima_dt = tz_col.localize(datetime.strptime(raw_ult, "%d/%m/%Y %H:%M"))
                            except Exception:
                                ultima_dt = None
                    if ultima_dt is None:
                        raw_creacion = r.get('created_at') or r.get('fecha_creacion')
                        if raw_creacion:
                            ultima_dt = datetime.fromisoformat(str(raw_creacion).replace("Z", "")).replace(tzinfo=pytz.utc).astimezone(tz_col)
                    if ultima_dt is None:
                        continue
                    dias_quieta = (ahora_seg - ultima_dt).days
                    if dias_quieta >= 5:
                        alertas_quietas.append(
                            f"🕒 OP {r.get('op')} ({r.get('cliente','')}) lleva {dias_quieta} día(s) SIN MOVIMIENTO — en espera de {r.get('proxima_area','SIN ÁREA')}"
                        )
                except Exception as e:
                    print(f"Error en alerta OP quieta: {e}")

            if alertas_quietas:
                with st.expander(f"🚨 {len(alertas_quietas)} OP(s) QUIETAS por 5+ días — solo visibles para Admin", expanded=True):
                    for al in alertas_quietas:
                        st.warning(al)

# SEPARA UNA LISTA DE ORDENES EN FORMAS / ROLLOS BLANCOS / REBOBINADO / ROLLOS IMPRESOS
        def _categoria_op(row):
            tipo = (row.get('tipo_orden') or '').upper()
            if "FORMAS" in tipo:
                return "FORMAS"
            elif "REBOBINADO" in tipo:
                return "REBOBINADO"
            elif "BLANCOS" in tipo:
                return "ROLLOS_BLANCOS"
            else:
                return "ROLLOS_IMPRESOS"

        def pintar_tarjeta_op(row):
            op_id = str(row['op'])
            area_destino = row.get('proxima_area', 'SIN ÁREA').upper()
            cliente = row.get('cliente', 'N/A')
            nombre_t = row.get('nombre_trabajo', 'SIN NOMBRE')
            vendedor = row.get('vendedor', 'N/A')
            lugar = row.get('tipo_origen', 'N/A')
           

# LOGICA DE FILTRADO
            if busqueda:
                b = busqueda.lower()
                
                if (b not in op_id.lower() and 
                    b not in cliente.lower() and 
                    b not in nombre_t.lower() and
                    b not in lugar.lower() and  
                    b not in area_destino.lower() and 
                    b not in vendedor.lower()):
                    return

# LOGICA DE ESTATUS MEJORADA
            if area_destino == "FINALIZADO":
                
                texto_estatus = "🔵 ORDEN FINALIZADA (BODEGA / DESPACHOS)"
                color_texto = "blue"
            elif op_id in op_en_maquina:
                
                maquina_nombre = op_en_maquina[op_id]
                texto_estatus = f"🟢 EN {area_destino} (PROCESANDO EN: {maquina_nombre})"
                color_texto = "green"
            else:
               
                texto_estatus = f"⏳ EN ESPERA DE {area_destino}"
                color_texto = "orange"

#  DISEÑO DE TARJETA 
            tipo_op = row.get('tipo_orden', '')
            if "FORMAS" in tipo_op:
                icono_tipo = "📄"
                etiqueta_tipo = "FORMAS"
                color_tipo = "#1565C0"
                borde_tipo = "#1565C0"
            elif "ROLLOS" in tipo_op:
                icono_tipo = "🌀"
                etiqueta_tipo = "ROLLOS"
                color_tipo = "#2E7D32"
                borde_tipo = "#2E7D32"
            elif "REBOBINADO" in tipo_op:
                icono_tipo = "🔄"
                etiqueta_tipo = "REBOBINADO"
                color_tipo = "#6A1B9A"
                borde_tipo = "#6A1B9A"
            else:
                icono_tipo = "📦"
                etiqueta_tipo = "OTRO"
                color_tipo = "#555"
                borde_tipo = "#555"
            
            fecha_raw = row.get('created_at') or row.get('fecha_creacion') or ''
            fecha_fmt = fmt_fecha_hora(fecha_raw, con_hora=False) if fecha_raw else ''
            if fecha_fmt == '-':
                fecha_fmt = ''
            titulo_unico = f"{icono_tipo} {etiqueta_tipo} | OP {op_id} | {cliente} | 💼 {vendedor} | 📅 {fecha_fmt} | {texto_estatus}"
            
            with st.expander(titulo_unico):
                st.write("Detalles internos de la OP...")
                st.markdown(f"### ESTATUS DE TRABAJO: :{color_texto}[{texto_estatus}]")
                
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.write("**👤 CLIENTE:**") 
                    st.info(cliente)
                    st.write("**📅 FECHA:**")
                    st.info(fmt_fecha_hora(row.get('created_at'), con_hora=False))
                    st.write("**🔙 ORDEN ANTERIOR:**")
                    st.info(row.get('op_anterior', '')[:10])
                with c2:
                    st.write("**🏗️ AREA ACTUAL:**")
                    st.info(area_destino)
                    st.write("**📦 CANTIDAD SOLICITADA:**")
                    st.info(row.get('cantidad_formas') if "FORMAS" in row.get('tipo_orden','') else row.get('cantidad_rollos','0'))
                    st.write("**📖 REFERENCIA COMERCIAL:**")
                    st.info(row.get('ref_comercial', ''))
                with c3:
                    st.write("**📝 NOMBRE DE TRABAJO:**")
                    st.info(nombre_t)
                    st.write("**⚙️ TIPO DE TRABAJO:**")
                    st.info(row.get('tipo_orden', 'N/A'))
                    st.write("**📋 OBSERVACIONES DE DISEÑO:**")
                    st.info(row.get('observaciones_diseno', 'N/A'))
                with c4:
                    st.write("**🛠️ ACCIONES Y ENLACES:**")


# BOTON DE READIOGRAFIA
                    if st.button(f"📋 VER RADIOGRAFIA OP {op_id}", key=f"btn_seg_{op_id}", use_container_width=True):
                        modal_detalle_op(row)

 # MOSTRAR      
                    link_arte = row.get('link_diseno')
                    num_ticket_seg = row.get('num_ticket')

                    if link_arte:
                        st.link_button("🎨 VER ARTE", link_arte, use_container_width=True)

# El ticket ya no es un link: es un numero que el vendedor ingresa al crear la OP (num_ticket).
# Se muestra en pantalla, debajo del link del arte, en vez del boton "VER TICKET" que ya no aplica.
                    if num_ticket_seg:
                        st.metric("🎫 TICKET", num_ticket_seg)

                    if not link_arte and not num_ticket_seg:
                        st.caption("Sin links adjuntos")

                st.divider()

#  BOTONES DE DESCARGA ORDEN EN PDF
                if st.session_state.get('rol') in ['admin', 'ventas', 'diseño']:
                    try:
                        tipo = row.get('tipo_orden', '')
                        if "FORMAS" in tipo:
                            pdf_data = generar_op_formas(row)
                        elif "ROLLOS" in tipo:
                            pdf_data = generar_op_rollos(row)
                        else:
                            pdf_data = generar_op_rebobinado(row)
                            
                        st.download_button(
                            label=f"📥 Descargar PDF Orden {op_id}",
                            data=pdf_data,
                            file_name=f"OP_{op_id}.pdf",
                            mime="application/pdf",
                            key=f"dl_pdf_{op_id}",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"No se pudo generar el PDF: {e}")

# BOTON DE DESCARGA DEL ROTULO PARA CAJAS (100x150mm con QR)
                    try:
                        st.download_button(
                            label=f"🏷️ Descargar Rótulo para Cajas {op_id}",
                            data=generar_rotulo_pdf(row),
                            file_name=f"rotulo_OP_{op_id}.pdf",
                            mime="application/pdf",
                            key=f"dl_rotulo_{op_id}",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"No se pudo generar el rótulo: {e}")

# RECORRIDO DE TARJETAS POR PESTAÑA, SEPARADAS EN FORMAS / ROLLOS BLANCOS / REBOBINADO / ROLLOS IMPRESOS
        with tab_pendientes:
            sub_formas_p, sub_rblancos_p, sub_rebob_p, sub_rimpresos_p = st.tabs(
                ["📄 Formas", "🌀 Rollos Blancos", "🔄 Rebobinado", "🌀 Rollos Impresos"]
            )
            pendientes_formas = [r for r in ordenes_pendientes if _categoria_op(r) == "FORMAS"]
            pendientes_rblancos = [r for r in ordenes_pendientes if _categoria_op(r) == "ROLLOS_BLANCOS"]
            pendientes_rebob = [r for r in ordenes_pendientes if _categoria_op(r) == "REBOBINADO"]
            pendientes_rimpresos = [r for r in ordenes_pendientes if _categoria_op(r) == "ROLLOS_IMPRESOS"]
            with sub_formas_p:
                if not pendientes_formas:
                    st.info("No hay órdenes de FORMAS pendientes o en proceso.")
                for row in pendientes_formas:
                    pintar_tarjeta_op(row)
            with sub_rblancos_p:
                if not pendientes_rblancos:
                    st.info("No hay órdenes de ROLLOS BLANCOS pendientes o en proceso.")
                for row in pendientes_rblancos:
                    pintar_tarjeta_op(row)
            with sub_rebob_p:
                if not pendientes_rebob:
                    st.info("No hay órdenes de REBOBINADO pendientes o en proceso.")
                for row in pendientes_rebob:
                    pintar_tarjeta_op(row)
            with sub_rimpresos_p:
                if not pendientes_rimpresos:
                    st.info("No hay órdenes de ROLLOS IMPRESOS pendientes o en proceso.")
                for row in pendientes_rimpresos:
                    pintar_tarjeta_op(row)

        with tab_finalizadas:
            sub_formas_f, sub_rblancos_f, sub_rebob_f, sub_rimpresos_f = st.tabs(
                ["📄 Formas", "🌀 Rollos Blancos", "🔄 Rebobinado", "🌀 Rollos Impresos"]
            )
            finalizadas_formas = [r for r in ordenes_finalizadas if _categoria_op(r) == "FORMAS"]
            finalizadas_rblancos = [r for r in ordenes_finalizadas if _categoria_op(r) == "ROLLOS_BLANCOS"]
            finalizadas_rebob = [r for r in ordenes_finalizadas if _categoria_op(r) == "REBOBINADO"]
            finalizadas_rimpresos = [r for r in ordenes_finalizadas if _categoria_op(r) == "ROLLOS_IMPRESOS"]
            with sub_formas_f:
                if not finalizadas_formas:
                    st.info("No hay órdenes de FORMAS finalizadas.")
                for row in finalizadas_formas:
                    pintar_tarjeta_op(row)
            with sub_rblancos_f:
                if not finalizadas_rblancos:
                    st.info("No hay órdenes de ROLLOS BLANCOS finalizadas.")
                for row in finalizadas_rblancos:
                    pintar_tarjeta_op(row)
            with sub_rebob_f:
                if not finalizadas_rebob:
                    st.info("No hay órdenes de REBOBINADO finalizadas.")
                for row in finalizadas_rebob:
                    pintar_tarjeta_op(row)
            with sub_rimpresos_f:
                if not finalizadas_rimpresos:
                    st.info("No hay órdenes de ROLLOS IMPRESOS finalizadas.")
                for row in finalizadas_rimpresos:
                    pintar_tarjeta_op(row)

# MODULO DE DISEÑO
elif menu == "🎨 Diseño y Pre-Prensa":
    st.title("🎨 Módulo de Diseño y Pre-Prensa")

# CONTROL DE ACCESO POR ETAPA: los roles diseño1/diseño2/diseño3 solo pueden
# INTERACTUAR con su propia pestaña (Auditoria/Pre-Prensa/Revision Final).
# Los roles 'admin' y 'diseño' (genérico) siguen viendo y usando las 3 pestañas,
# igual que antes, para no romper flujos existentes.
    _rol_diseno_actual = st.session_state.get('rol', '').lower()
    puede_tab1 = _rol_diseno_actual in ('admin', 'diseño', 'diseño1')
    puede_tab2 = _rol_diseno_actual in ('admin', 'diseño', 'diseño2')
    puede_tab3 = _rol_diseno_actual in ('admin', 'diseño', 'diseño3')

#  DEFINICION DE VENTANAS
    tab1, tab2, tab3 = st.tabs(["📋 1. AUDITORIA TECNICA", "🎞️ 2. PRE-PRENSA", "⚡ 3. REVISION FINAL PLANCHA"])

#  AUDITORIA
    with tab1:
      if not puede_tab1:
        st.warning("🔒 Tu usuario no tiene permiso para interactuar con esta etapa. Solo puedes ver/usar tu propia pestaña asignada.")
      else:
        st.subheader("🕵️ Revisión de Diseño")
        op_pendientes = supabase.table("ordenes_planeadas").select("*").ilike("proxima_area", "DISEÑO%").execute().data
        
        if op_pendientes:
            op_sel = st.selectbox("Seleccione OP:", [f"{o['op']} - {o['nombre_trabajo']} - {o['tipo_origen']}" for o in op_pendientes], key="aud_v5")
            op_id = op_sel.split(" - ")[0]
            datos_op = next((o for o in op_pendientes if str(o['op']) == str(op_id)), None)

            if datos_op:
                radiografia_completa_op(datos_op)
                st.divider()
                
                col_inputs = st.columns(2)
                with col_inputs[0]:
                    link_arte = st.text_input("LINK DEL ARTE (DRIVE):", value=datos_op.get('link_diseno', '') or "", key=f"link_arte_{op_id}")
                with col_inputs[1]:
                    st.metric("🎫 NÚMERO DE TICKET (asignado por ventas)", datos_op.get('num_ticket', 0) or 0)
                
                obs_dis = st.text_area("✍️ NOTAS PARA PRE-PRENSA:", value=datos_op.get('observaciones_diseno', '') or "", key=f"obs_dis_{op_id}")
                obs_dise = st.text_area("✍️ ESPECIFICACIONES PARA REVELAR PLANCHAS:", value=datos_op.get('observaciones_diseno2', '') or "", key=f"obs_dise_{op_id}")
                
                if st.button("✅ ENVIAR A PRE-PRENSA", use_container_width=True):
                    if link_arte:
                        _, tiempo_area_txt = calcular_tiempo_en_area(datos_op)
                        hist_dis = datos_op.get('historial_procesos') or []
                        hist_dis.append({
                            "area": "DISEÑO (AUDITORIA)",
                            "maquina": "—",
                            "tipo": "DISEÑO",
                            "operario": st.session_state.get('nombre_usuario', '?'),
                            "fecha": hora_colombia().strftime("%d/%m/%Y %H:%M"),
                            "duracion": tiempo_area_txt,
                            "tiempo_total_area": tiempo_area_txt,
                            "observaciones": obs_dis
                        })
                        update_data = {
                            "link_diseno": link_arte, 
                            "observaciones_diseno": obs_dis,
                            "observaciones_diseno2": obs_dise,  
                            "proxima_area": "PRE-PRENSA",
                            "historial_procesos": hist_dis
                        }
                        supabase.table("ordenes_planeadas").update(update_data).eq("op", op_id).execute()
                        st.success("Enviado a Pre-Prensa."); time.sleep(1); st.rerun()
                    else:
                        st.error("El link del ARTE es obligatorio.")

# PRE-PRENSA
    with tab2:
      if not puede_tab2:
        st.warning("🔒 Tu usuario no tiene permiso para interactuar con esta etapa. Solo puedes ver/usar tu propia pestaña asignada.")
      else:
        st.subheader("🎞️ Procesamiento de Archivos")
        op_pre = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", "PRE-PRENSA").execute().data

        if op_pre:
            op_sel_2 = st.selectbox("Seleccione OP:", [f"{o['op']} - {o['nombre_trabajo']} - {o['tipo_origen']}" for o in op_pre], key="pre_v5")
            op_id_2 = op_sel_2.split(" - ")[0]
            datos_op_2 = next((o for o in op_pre if str(o['op']) == str(op_id_2)), None)

            if datos_op_2:
               
                c1, c2 = st.columns(2)
                c1.link_button("🎨 ABRIR ARTE", datos_op_2.get('link_diseno', '#'), use_container_width=True)
                c2.metric("🎫 TICKET ASIGNADO", datos_op_2.get('num_ticket', 0))

                radiografia_completa_op(datos_op_2)
                
                if st.button("🚀 ENVIAR A REVISIÓN FINAL", use_container_width=True):
                    _, tiempo_area_txt2 = calcular_tiempo_en_area(datos_op_2)
                    hist_pre = datos_op_2.get('historial_procesos') or []
                    hist_pre.append({
                        "area": "PRE-PRENSA",
                        "maquina": "—",
                        "tipo": "DISEÑO",
                        "operario": st.session_state.get('nombre_usuario', '?'),
                        "fecha": hora_colombia().strftime("%d/%m/%Y %H:%M"),
                        "duracion": tiempo_area_txt2,
                        "tiempo_total_area": tiempo_area_txt2,
                        "observaciones": ""
                    })
                    supabase.table("ordenes_planeadas").update({
                        "proxima_area": "REVISION_FINAL",
                        "historial_procesos": hist_pre
                    }).eq("op", op_id_2).execute()
                    st.success("Enviado a Revisión Final."); time.sleep(1); st.rerun()

# REVISION FINAL CON PLANCHA 
    with tab3:
      if not puede_tab3:
        st.warning("🔒 Tu usuario no tiene permiso para interactuar con esta etapa. Solo puedes ver/usar tu propia pestaña asignada.")
      else:
        st.subheader("⚡ Control de Planchas y Salida")
        op_final = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", "REVISION_FINAL").execute().data

        if op_final:
            op_sel_3 = st.selectbox("Seleccione OP:", [f"{o['op']} - {o['nombre_trabajo']} - {o['tipo_origen']}" for o in op_final], key="final_v5")
            op_id_3 = op_sel_3.split(" - ")[0]
            datos_op_3 = next((o for o in op_final if str(o['op']) == str(op_id_3)), None)

            if datos_op_3:
                st.warning(f"**Ticket:** {datos_op_3.get('num_ticket')} | **DATOS DE PLANCHAS A REVELAR:** {datos_op_3.get('observaciones_diseno2')}")

# VER EL ARTE Y CORREGIR EL LINK SI QUEDO MAL CARGADO EN AUDITORIA TECNICA (tab1).
# Esta es la ULTIMA oportunidad de corregirlo antes de que la orden pase a Impresión;
# una vez en Impresión, el link ya no se puede editar desde este módulo.
                link_actual_3 = datos_op_3.get('link_diseno', '') or ''
                c_arte1, c_arte2 = st.columns([1, 2])
                with c_arte1:
                    st.link_button("🎨 VER ARTE", link_actual_3 or "#", use_container_width=True, disabled=not link_actual_3)
                with c_arte2:
                    link_arte_final = st.text_input(
                        "LINK DEL ARTE (corregir si quedó mal cargado):",
                        value=link_actual_3,
                        key=f"link_final_{op_id_3}"
                    )

                num_plancha = st.text_input("ESPESIFIQUE LAS PLANCHAS REVELADAS:", key=f"num_plancha_{op_id_3}")
                
                radiografia_completa_op(datos_op_3)

                if st.button("🏁 FINALIZAR Y ENVIAR A IMPRESIÓN", use_container_width=True):

                    _, tiempo_area_txt3 = calcular_tiempo_en_area(datos_op_3)
                    hist_rev = datos_op_3.get('historial_procesos') or []
                    hist_rev.append({
                        "area": "REVISION_FINAL",
                        "maquina": "—",
                        "tipo": "DISEÑO",
                        "operario": st.session_state.get('nombre_usuario', '?'),
                        "fecha": hora_colombia().strftime("%d/%m/%Y %H:%M"),
                        "duracion": tiempo_area_txt3,
                        "tiempo_total_area": tiempo_area_txt3,
                        "observaciones": f"Planchas reveladas: {num_plancha}" if num_plancha else ""
                    })

# Actualizamos a IMPRESION para que pase a la planta (incluye el link del arte,
# por si se corrigio aqui mismo antes de enviar)
                    supabase.table("ordenes_planeadas").update({
                        "proxima_area": "IMPRESIÓN",
                        "link_diseno": link_arte_final,
                        "historial_procesos": hist_rev
                    }).eq("op", op_id_3).execute()
                    st.success("Orden enviada a planta exitosamente."); time.sleep(1); st.rerun()
        else:
            st.info("No hay órdenes pendientes para revisión de plancha.")
            
# MODULO PLANIFICACION 
elif menu == "🧐 Auditoría Ventas":
    st.title("🧐 Auditoría de Ventas")
    st.caption("Toda OP nueva (Formas o Rollos, Impresas o Blancas, Rebobinado) pasa primero por aquí antes de seguir su ruta normal.")

    op_pendientes_av = supabase.table("ordenes_planeadas").select("*").eq("proxima_area", "AUDITORIA VENTAS").execute().data

    if not op_pendientes_av:
        st.info("No hay órdenes pendientes de auditoría de ventas en este momento.")
    else:
        op_sel_av = st.selectbox(
            "Seleccione OP a revisar:",
            [f"{o['op']} - {o['nombre_trabajo']} - {o.get('tipo_orden','')}" for o in op_pendientes_av],
            key="aud_ventas_sel"
        )
        op_id_av = op_sel_av.split(" - ")[0]
        datos_op_av = next((o for o in op_pendientes_av if str(o['op']) == str(op_id_av)), None)

        if datos_op_av:
            radiografia_completa_op(datos_op_av, mostrar_obs_auditoria1=False)
            st.divider()

            ruta_siguiente_av = ruta_despues_de_auditoria_ventas(datos_op_av.get('tipo_orden', ''))
            st.info(f"➡️ Al aprobarse, esta orden seguirá su ruta hacia: **{ruta_siguiente_av}**")

            if st.button("✅ MARCAR COMO REVISADO — CONTINUAR RUTA", use_container_width=True, key="btn_aprobar_aud_ventas"):
                _, tiempo_area_txt_av = calcular_tiempo_en_area(datos_op_av)
                hist_av = datos_op_av.get('historial_procesos') or []
                hist_av.append({
                    "area": "AUDITORIA VENTAS",
                    "maquina": "—",
                    "tipo": "AUDITORIA_VENTAS",
                    "operario": st.session_state.get('nombre_usuario', '?'),
                    "fecha": hora_colombia().strftime("%d/%m/%Y %H:%M"),
                    "duracion": tiempo_area_txt_av,
                    "tiempo_total_area": tiempo_area_txt_av
                })
                supabase.table("ordenes_planeadas").update({
                    "proxima_area": ruta_siguiente_av,
                    "historial_procesos": hist_av
                }).eq("op", op_id_av).execute()
                st.success(f"✅ OP {op_id_av} revisada. Continúa hacia {ruta_siguiente_av}.")
                time.sleep(1.2)
                st.rerun()

# MODULO PLANIFICACION 
elif menu == "📅 Planificación":
    st.title("Planificación de Órdenes 🌐")

# SI SE ACABA DE CREAR UNA OP, OFRECER DESCARGAR SU ROTULO PARA CAJAS
    if st.session_state.get('ultima_op_creada'):
        op_recien_creada = st.session_state['ultima_op_creada']
        st.success(f"✅ Orden {op_recien_creada.get('op')} creada correctamente.")
        c_rot1, c_rot2 = st.columns([3, 1])
        with c_rot1:
            st.download_button(
                "📥 Descargar Rótulo para Cajas (100x150mm)",
                data=generar_rotulo_pdf(op_recien_creada),
                file_name=f"rotulo_OP_{op_recien_creada.get('op')}.pdf",
                mime="application/pdf",
                key="dl_rotulo_nueva_op"
            )
        with c_rot2:
            if st.button("✖️ Cerrar aviso", key="cerrar_aviso_rotulo"):
                st.session_state['ultima_op_creada'] = None
                st.rerun()

# Estados donde la OP aún no ha sido procesada por ningún área
    ESTADOS_EDITABLES = [
        "AUDITORIA VENTAS", "DISEÑO (AUDITORIA)", "IMPRESIÓN", "CORTE", "REBOBINADORAS",
        "ESPERA DE AUDITORIA", "ESPERA DE CORTE", "ESPERA DE IMPRESIÓN"
    ]

    tab_nueva, tab_editar = st.tabs(["➕ Nueva / Repetición", "✏️ Editar OP Existente"])

    with tab_editar:
        st.markdown("<div class='section-header'>✏️ EDITAR ORDEN DE PRODUCCIÓN</div>", unsafe_allow_html=True)
        st.caption("Solo puedes editar OPs que aún no han sido tomadas por ningún área de producción.")

        col_b1, col_b2 = st.columns([3, 1])
        op_buscar_edit = col_b1.text_input("Número de OP a editar (Ej: FRI-101):", key="op_edit_buscar")

        if col_b2.button("🔍 Buscar", key="btn_buscar_edit"):
            if op_buscar_edit:
                res_edit = supabase.table("ordenes_planeadas").select("*")\
                    .eq("op", op_buscar_edit.upper().strip()).execute()
                if res_edit.data:
                    st.session_state['op_editar_data'] = res_edit.data[0]
                else:
                    st.error("❌ No se encontró esa OP.")
                    st.session_state.pop('op_editar_data', None)
            else:
                st.warning("Ingresa el número de OP.")

        op_edit = st.session_state.get('op_editar_data')

        if op_edit:
            estado_actual = op_edit.get('proxima_area', '')
            rol_actual    = st.session_state.get('rol', '').lower()

            # Verificar si es editable
            es_editable = estado_actual in ESTADOS_EDITABLES
            es_admin    = rol_actual == 'admin'

# Mostrar estado actual
            st.markdown(f"""
            <div class='metric-box'>
              <b>📋 OP:</b> {op_edit.get('op')} &nbsp;&nbsp;
              <b>👤 Cliente:</b> {op_edit.get('cliente')} &nbsp;&nbsp;
              <b>🏷️ Tipo:</b> {op_edit.get('tipo_orden')} &nbsp;&nbsp;
              <b>📍 Estado actual:</b> <code>{estado_actual}</code>
            </div>
            """, unsafe_allow_html=True)

            if not es_editable and not es_admin:
                st.error(f"🔒 Esta OP ya fue tomada por producción ({estado_actual}) y no se puede editar.")
                st.caption("Si necesitas hacer un cambio urgente, contacta al administrador.")

            else:
                if not es_editable and es_admin:
                    st.warning("⚠️ Esta OP ya está en producción. Como admin puedes editarla igualmente.")

                st.markdown("---")
                st.markdown("**Edita los campos que necesitas corregir:**")

                with st.form("form_editar_op"):
#  DATOS GENERALES 
                    st.markdown("**📋 Datos Generales**")
                    ec1, ec2, ec3 = st.columns(3)
                    nuevo_cliente  = ec1.text_input("Cliente:", value=op_edit.get('cliente', ''))
                    nuevo_vendedor = ec2.text_input("Vendedor:", value=op_edit.get('vendedor', ''))
                    nuevo_trabajo  = ec3.text_input("Nombre del Trabajo:", value=op_edit.get('nombre_trabajo', ''))

                    tipo_op = op_edit.get('tipo_orden', '')

#  FORMAS IMPRESAS / BLANCAS 
                    if "FORMAS" in tipo_op:
                        st.markdown("**📑 Datos de Formas**")
                        ef1, ef2, ef3, ef4 = st.columns(4)
                        nueva_cant    = ef1.number_input("Cantidad Formas:", value=int(op_edit.get('cantidad_formas', 0) or 0), min_value=0)
                        nuevo_partes  = ef2.selectbox("Número de Partes:", [1,2,3,4,5,6], index=int(op_edit.get('num_partes', 1) or 1) - 1)
                        nueva_pres    = ef3.selectbox("Presentación:", PRESENTACIONES, index=PRESENTACIONES.index(op_edit['presentacion']) if op_edit.get('presentacion') in PRESENTACIONES else 0)
                        nueva_pres2   = ef4.selectbox("Encolada o Grapada:", PRESENTACIONES2, index=PRESENTACIONES2.index(op_edit['presentacion2']) if op_edit.get('presentacion2') in PRESENTACIONES2 else 0)

                        ep1, ep2, ep3, ep4 = st.columns(4)
                        t_perf_e  = ep1.selectbox("¿Perforaciones?", ["NO","SI"], index=1 if op_edit.get('perforaciones_detalle') and op_edit.get('perforaciones_detalle') != 'NO' else 0)
                        perf_det_e= ep1.text_area("Detalle Perforación:", value=op_edit.get('perforaciones_detalle','') or '') if t_perf_e == "SI" else "NO"
                        t_barr_e  = ep2.selectbox("¿Código de Barras?", ["NO","SI"], index=1 if op_edit.get('codigo_barras_detalle') and op_edit.get('codigo_barras_detalle') != 'NO' else 0)
                        barr_det_e= ep2.text_area("Detalle Barras:", value=op_edit.get('codigo_barras_detalle','') or '') if t_barr_e == "SI" else "NO"
                        t_num_e   = ep3.selectbox("¿Numeración?", ["NO","SI"], index=1 if op_edit.get('num_id') and op_edit.get('num_id') != 'NO' else 0)
                        num_id_e  = ep3.text_input("Desde:", value=op_edit.get('num_id','') or '') if t_num_e == "SI" else "NO"
                        num_fd_e  = ep3.text_input("Hasta:", value=op_edit.get('num_fd','') or '') if t_num_e == "SI" else "NO"
                        nueva_trans_f = ep4.selectbox("¿Transportadora?", ["NO","SI"], index=1 if op_edit.get('transportadora_formas') else 0)
                        nuevo_dest_f  = ep4.text_input("Ciudad destino:", value=op_edit.get('destino_formas','') or '') if nueva_trans_f == "SI" else "NO"

# Partes de la forma
                        st.markdown("**📄 Detalle de Partes**")
                        rec_partes_e = op_edit.get('detalles_partes_json') or []
                        lista_p_e = []
                        for i in range(1, nuevo_partes + 1):
                            p_data_e = rec_partes_e[i-1] if i <= len(rec_partes_e) else {}
                            st.markdown(f"*Parte {i}*")
                            d1,d2,d3,d4,d5,d6 = st.columns(6)
                            anc_e = d1.text_input(f"Ancho P{i}",  key=f"ea_{i}", value=p_data_e.get('anc',''))
                            lar_e = d2.text_input(f"Largo P{i}",  key=f"el_{i}", value=p_data_e.get('lar',''))
                            pap_e = d3.text_input(f"Papel P{i}",  key=f"ep_{i}", value=p_data_e.get('papel',''))
                            fon_e = d4.text_input(f"Fondo P{i}",  key=f"ef_{i}", value=p_data_e.get('color_fondo',''))
                            gra_e = d5.text_input(f"Gramos P{i}", key=f"eg_{i}", value=p_data_e.get('gramos',''))
                            tra_e = d6.text_input(f"Tráfico P{i}",key=f"et_{i}", value=p_data_e.get('trafico',''))
                            tf_e, tr_e, obe_e = "N/A", "N/A", ""
                            if tipo_op == "FORMAS IMPRESAS":
                                t1e,t2e,t3e = st.columns(3)
                                tf_e  = t1e.text_input(f"Tintas Frente P{i}",   key=f"etf_{i}", value=p_data_e.get('tf',''))
                                tr_e  = t2e.text_input(f"Tintas Respaldo P{i}", key=f"etr_{i}", value=p_data_e.get('tr',''))
                                obe_e = t3e.text_input(f"Obs. Especial P{i}",   key=f"eob_{i}", value=p_data_e.get('obs_parte',''))
                            lista_p_e.append({"p":i,"anc":anc_e,"lar":lar_e,"papel":pap_e,"color_fondo":fon_e,"gramos":gra_e,"tf":tf_e,"tr":tr_e,"trafico":tra_e,"obs_parte":obe_e})

                        nuevas_obs = st.text_area("Observaciones Generales:", value=op_edit.get('observaciones_formas','') or '')

#  ROLLOS IMPRESOS / BLANCOS 
                    elif tipo_op in ["ROLLOS IMPRESOS", "ROLLOS BLANCOS"]:
                        st.markdown("**🌀 Datos de Rollos**")
                        er1, er2, er3 = st.columns(3)
                        nuevo_mat   = er1.text_input("Material Base:", value=op_edit.get('material','') or '')
                        nuevo_gram  = er2.number_input("Gramaje:", value=int(op_edit.get('gramaje_rollos', 0) or 0), min_value=0)
                        nuevo_ref   = er3.text_input("Referencia Comercial:", value=op_edit.get('ref_comercial','') or '')

                        er4, er5 = st.columns(2)
                        nueva_cant_r = er4.number_input("Cantidad Rollos:", value=int(op_edit.get('cantidad_rollos', 0) or 0), min_value=0)
                        cores = ["13MM","19MM","1 PULGADA","40 MM","2 PULGADAS","3 PULGADAS"," NINGUNO"]
                        nuevo_core   = er5.selectbox("Core / Centro:", cores, index=cores.index(op_edit['core']) if op_edit.get('core') in cores else 0)

                        if tipo_op == "ROLLOS IMPRESOS":
                            ct1, ct2 = st.columns(2)
                            nuevo_tf_r = ct1.text_input("Tintas Frente:", value=op_edit.get('tintas_frente_rollos','') or '')
                            nuevo_tr_r = ct2.text_input("Tintas Respaldo:", value=op_edit.get('tintas_respaldo_rollos','') or '')
                        else:
                            nuevo_tf_r, nuevo_tr_r = "N/A", "N/A"

                        er6, er7 = st.columns(2)
                        nueva_uds_b = er6.number_input("Unidades x Bolsa:", value=int(op_edit.get('unidades_bolsa', 0) or 0), min_value=0)
                        nueva_uds_c = er7.number_input("Unidades x Caja:",  value=int(op_edit.get('unidades_caja',  0) or 0), min_value=0)

                        nueva_trans_r = st.selectbox("¿Transportadora?", ["NO","SI"], index=1 if op_edit.get('transportadora_rollos') else 0)
                        nuevo_dest_r  = st.text_input("Ciudad destino:", value=op_edit.get('destino_rollos','') or '') if nueva_trans_r == "SI" else "NO"
                        nuevas_obs    = st.text_area("Observaciones:", value=op_edit.get('observaciones_rollos','') or '')

#  REBOBINADO 
                    elif tipo_op == "REBOBINADO":
                        st.markdown("**🌀 Datos de Rebobinado**")
                        eb1, eb2, eb3 = st.columns(3)
                        nuevo_mat     = eb1.text_input("Material / Papel:", value=op_edit.get('material','') or '')
                        nuevo_gram    = eb2.number_input("Gramaje:", value=int(op_edit.get('gramaje_rollos', 0) or 0), min_value=0)
                        nuevo_ancho   = eb3.text_input("Referencia Comercial:", value=op_edit.get('ancho_base','') or '')
                        eb4, eb5 = st.columns(2)
                        nueva_cant_r  = eb4.number_input("Cantidad Rollos:", value=int(op_edit.get('cantidad_rollos', 0) or 0), min_value=0)
                        nuevo_obj     = eb5.text_input("Objetivo del Rebobinado:", value=op_edit.get('objetivo_rebobinado','') or '')
                        nuevas_obs    = st.text_area("Observaciones:", value=op_edit.get('observaciones_rollos','') or '')

                    st.markdown("---")
# Este campo es obligatorio: el motivo queda guardado en el historial como una tarjeta especial de EDICION
                    nueva_obs_gral = st.text_area("📝 Motivo del cambio (queda registrado):",
                                        placeholder="Ej: Cliente solicitó cambio de cantidad...", key="motivo_edit")
                    btn_guardar_edit = st.form_submit_button("💾 GUARDAR CAMBIOS", use_container_width=True)

# Al presionar GUARDAR CAMBIOS: arma el payload segun el tipo de orden (Formas/Rollos/Rebobinado),
# actualiza la OP en Supabase y agrega la tarjeta de EDICION al historial_procesos para dejar trazabilidad
                    if btn_guardar_edit:
                        if not nueva_obs_gral.strip():
                            st.error("⚠️ Debes escribir el motivo del cambio.")
                        else:
                            try:
                                update_payload = {
                                    "cliente":        nuevo_cliente,
                                    "vendedor":       nuevo_vendedor,
                                    "nombre_trabajo": nuevo_trabajo,
                                }
                                if "FORMAS" in tipo_op:
                                    update_payload.update({
                                        "cantidad_formas":       nueva_cant,
                                        "num_partes":            nuevo_partes,
                                        "presentacion":          nueva_pres,
                                        "presentacion2":         nueva_pres2,
                                        "perforaciones_detalle": perf_det_e,
                                        "codigo_barras_detalle": barr_det_e,
                                        "num_id":                num_id_e,
                                        "num_fd":                num_fd_e,
                                        "transportadora_formas": True if nueva_trans_f == "SI" else None,
                                        "destino_formas":        nuevo_dest_f if nueva_trans_f == "SI" else None,
                                        "detalles_partes_json":  lista_p_e,
                                        "observaciones_formas":  nuevas_obs,
                                    })
                                elif tipo_op in ["ROLLOS IMPRESOS", "ROLLOS BLANCOS"]:
                                    update_payload.update({
                                        "material":              nuevo_mat,
                                        "gramaje_rollos":        nuevo_gram,
                                        "ref_comercial":         nuevo_ref,
                                        "cantidad_rollos":       nueva_cant_r,
                                        "core":                  nuevo_core,
                                        "tintas_frente_rollos":  nuevo_tf_r,
                                        "tintas_respaldo_rollos":nuevo_tr_r,
                                        "unidades_bolsa":        nueva_uds_b,
                                        "unidades_caja":         nueva_uds_c,
                                        "transportadora_rollos": True if nueva_trans_r == "SI" else None,
                                        "destino_rollos":        nuevo_dest_r if nueva_trans_r == "SI" else None,
                                        "observaciones_rollos":  nuevas_obs,
                                    })
                                elif tipo_op == "REBOBINADO":
                                    update_payload.update({
                                        "material":             nuevo_mat,
                                        "gramaje_rollos":       nuevo_gram,
                                        "ancho_base":           nuevo_ancho,
                                        "cantidad_rollos":      nueva_cant_r,
                                        "objetivo_rebobinado":  nuevo_obj,
                                        "observaciones_rollos": nuevas_obs,
                                    })

                                supabase.table("ordenes_planeadas").update(update_payload)\
                                    .eq("op", op_edit['op']).execute()

                                hist = op_edit.get('historial_procesos') or []
                                hist.append({
                                    "area":    "EDICIÓN",
                                    "maquina": "—",
                                    "tipo":    "EDICIÓN",
                                    "inicio":  hora_colombia().isoformat(),
                                    "fin":     hora_colombia().isoformat(),
                                    "fecha":   hora_colombia().strftime("%d/%m/%Y %H:%M"),
                                    "duracion":"0:00:00",
                                    "operario":      st.session_state.get('nombre_usuario','?'),
                                    "usuario":       st.session_state.get('nombre_usuario','?'),
                                    "observaciones": nueva_obs_gral,
                                    "nota":          f"Editado: {nueva_obs_gral}"
                                })
                                supabase.table("ordenes_planeadas").update({
                                    "historial_procesos": hist
                                }).eq("op", op_edit['op']).execute()

                                st.success(f"✅ OP {op_edit['op']} actualizada correctamente.")
                                st.session_state.pop('op_editar_data', None)
                                time.sleep(1.2)
                                st.rerun()

                            except Exception as e:
                                st.error(f"Error al guardar: {e}")

    with tab_nueva:
    
#  SELECTOR OTIGEN DE OP
        st.markdown("<div class='section-header'>📂 ORIGEN DE LA INFORMACIÓN</div>", unsafe_allow_html=True)
        origen = st.radio("¿Cómo desea ingresar la orden?", 
                        ["Nueva (Desde cero)", "Repetición Exacta", "Repetición con Cambios"], 
                        horizontal=True)
    
# VARIABLE PARA ALMACENAR DATOS RECUPERADOS
        datos_rec = {}
        
        if "Repetición" in origen:
            col_busq1, col_busq2 = st.columns([3, 1])
            op_a_buscar = col_busq1.text_input("Ingrese el número de OP Anterior para buscar (Ej: FRI-100):")
            if col_busq2.button("🔍 Buscar y Cargar"):
                if op_a_buscar:
                    try:
                        res_busq = supabase.table("ordenes_planeadas").select("*").eq("op", op_a_buscar.upper()).execute()
                        if res_busq.data:
                            datos_rec = res_busq.data[0]
                            st.success(f"✅ Datos de '{datos_rec['nombre_trabajo']}' cargados correctamente.")
                        else:
                            st.error("No se encontró la OP. Verifique el prefijo y número.")
                    except Exception as e:
                        st.error(f"Error en la base de datos: {e}")
                else:
                    st.warning("Por favor ingrese un número de OP.")

        st.divider()

# SELECTOR DE TIPO DE PRODUCTO
        c1, c2, c3, c4, c5 = st.columns(5)
        if c1.button("📑 FORMAS IMPRESAS"): st.session_state.sel_tipo = "FORMAS IMPRESAS"
        if c2.button("📄 FORMAS BLANCAS"): st.session_state.sel_tipo = "FORMAS BLANCAS"
        if c3.button("🌀 ROLLOS IMPRESOS"): st.session_state.sel_tipo = "ROLLOS IMPRESOS"
        if c4.button("⚪ ROLLOS BLANCOS"): st.session_state.sel_tipo = "ROLLOS BLANCOS"
        if c5.button("🌀 REBOBINADO"):st.session_state.sel_tipo = "REBOBINADO"

        if st.session_state.sel_tipo:
            t = st.session_state.sel_tipo
            prefijo = {"FORMAS IMPRESAS": "FRI-", "FORMAS BLANCAS": "FRB-", "ROLLOS IMPRESOS": "RI-", "ROLLOS BLANCOS": "RB-", "REBOBINADO": "RR-"}.get(t, "")
            p1, p2, p3, p4 = st.columns(4)

#  PERFORACIONES TODOS
            t_perf = p1.selectbox("¿Tiene Perforaciones?", ["NO","SI"], key="perf_select")

            if t_perf == "SI":
                perf_d = p1.text_area("Detalle Perforación", key="perf_det")
            else:
                perf_d = "NO"

#  SOLO PARA FORMAS   
            if "FORMAS" in t:


                if "partes_sel" not in st.session_state:
                    val_partes = int(datos_rec.get('num_partes', 1))
                    st.session_state.partes_sel = val_partes if 1 <= val_partes <= 6 else 1

                g1, g2, g3, g4 = st.columns(4)

                cant_f = g1.number_input(
                    "Cantidad Formas",
                    0,
                    value=int(datos_rec.get('cantidad_formas', 0))
                )

                st.session_state.partes_sel = g2.selectbox(
                    "Número de Partes",
                    [1,2,3,4,5,6],
                    index=st.session_state.partes_sel - 1
                )

                partes = st.session_state.partes_sel

                idx_pres = PRESENTACIONES.index(datos_rec['presentacion']) if datos_rec.get('presentacion') in PRESENTACIONES else 0
                pres = g3.selectbox("Presentación", PRESENTACIONES, index=idx_pres)

                pres_peg = g4.selectbox("Encolada o Grapada", PRESENTACIONES2)

                t_barr = p2.selectbox("¿Tiene Código de Barras?", ["NO","SI"], key="barr_select")

                if t_barr == "SI":
                    barr_d = p2.text_area("Detalle Barras", key="barr_det")
                else:
                    barr_d = "NO"


                t_num = p3.selectbox("¿Tiene Numeración?", ["NO","SI"], key="num_select")

                if t_num == "SI":
                    num_id = p3.text_input("Desde", key="num_desde")
                    num_fd = p3.text_input("Hasta", key="num_hasta")
                else:
                    num_id = "NO"
                    num_fd = "NO"
            else:
                barr_d = "NO"
                num_id = "NO"
                num_fd = "NO"

#  TRANSPORTADORA (TODOS) 
            t_trans_f = p4.selectbox("¿Transportadora?", ["NO","SI"], key="trans_select")

            if t_trans_f == "SI":
                dest_f = p4.text_area("Ciudad destino", key="dest_trans")
            else:
                dest_f = "NO"
            partes = st.session_state.get("partes_sel", 1)

# BOTON COPIAR PARTE 1 A TODAS
            if "FORMAS" in t and partes > 1:
                if st.button("📋 Copiar Parte 1 a todas las partes"):

                    for i in range(2, partes + 1):

                        st.session_state[f"a_{i}"] = st.session_state.get("a_1", "")
                        st.session_state[f"l_{i}"] = st.session_state.get("l_1", "")
                        st.session_state[f"p_{i}"] = st.session_state.get("p_1", "")
                        st.session_state[f"f_{i}"] = st.session_state.get("f_1", "")
                        st.session_state[f"g_{i}"] = st.session_state.get("g_1", "")
                        st.session_state[f"t_{i}"] = st.session_state.get("t_1", "")

                        st.session_state[f"tf_{i}"] = st.session_state.get("tf_1", "")
                        st.session_state[f"tr_{i}"] = st.session_state.get("tr_1", "")
                        st.session_state[f"obe_{i}"] = st.session_state.get("obe_1", "")

                    st.success("Partes copiadas correctamente")
                    st.rerun()
                    

            with st.form("form_plan", clear_on_submit=True):
                st.subheader(f"Nueva Orden: {t} (Prefijo: {prefijo})")
                
# SECCION: DATOS GENERALES 
                f1, f2, f3 = st.columns(3)
                op_input = f1.text_input("Número de Nueva OP (Solo número) *")
                
# SI ES REPETICION SUGERIR LA OP ANTERIOR BUSCADA
                val_op_ant = datos_rec.get('op', "") if "Repetición" in origen else ""
                op_a = f2.text_input("OP Anterior", value=val_op_ant)
                
                cli = f3.text_input("Cliente *", value=datos_rec.get('cliente', ""))
                
                f4, f5, f6 = st.columns(3)
                vend = f4.text_input("Vendedor", value=datos_rec.get('vendedor', ""))
                trab = f5.text_input("Nombre del Trabajo", value=datos_rec.get('nombre_trabajo', ""))
                num_ticket_creacion = f6.number_input("Número de Ticket", value=int(datos_rec.get('num_ticket', 0) or 0), min_value=0, step=1)

                if "FORMAS" in t:
                    lista_p = []
                    rec_partes = datos_rec.get('detalles_partes_json', [])

                    for i in range(1, partes + 1):

# INTEBNTAR TRAER DAROS  DE LA  PARTE SI EXSITE REPEETICION 
                        p_data = rec_partes[i-1] if i <= len(rec_partes) else {}
                        
                        st.markdown(f"**PARTE {i}**")
                        d1, d2, d3, d4, d5, d6 = st.columns(6)
                        anc = d1.text_input(f"Ancho P{i}", key=f"a_{i}", value=p_data.get('anc', ""))
                        lar = d2.text_input(f"Largo P{i}", key=f"l_{i}", value=p_data.get('lar', ""))
                        pap = d3.text_input(f"Papel P{i}", key=f"p_{i}", value=p_data.get('papel', ""))
                        fon = d4.text_input(f"Color Fondo P{i}", key=f"f_{i}", value=p_data.get('color_fondo', "")) 
                        gra = d5.text_input(f"Gramos P{i}", key=f"g_{i}", value=p_data.get('gramos', ""))
                        tra = d6.text_input(f"Tráfico P{i}", key=f"t_{i}", value=p_data.get('trafico', ""))
                        
                        tf, tr = "N/A", "N/A"
                        obe = ""
                        if t == "FORMAS IMPRESAS":
                            t1, t2, t3 = st.columns(3)
                            tf = t1.text_input(f"Tintas Frente P{i}", key=f"tf_{i}", value=p_data.get('tf', ""))
                            tr = t2.text_input(f"Tintas Respaldo P{i}", key=f"tr_{i}", value=p_data.get('tr', ""))
                            obe = t3.text_input(f"Obs. Especial P{i}", key=f"obe_{i}", value=p_data.get('obs_parte',""))
                        
                        lista_p.append({
                            "p": i,
                            "anc": anc,
                            "lar": lar,
                            "papel": pap,
                            "color_fondo": fon,
                            "gramos": gra,
                            "tf": tf,
                            "tr": tr,
                            "trafico": tra,
                            "obs_parte": obe
                        })
                    
                    obs = st.text_area("Observaciones Generales Formas", value=datos_rec.get('observaciones_formas', ""))
                elif t == "REBOBINADO":

                    r1, r2, r3 = st.columns(3)

                    mat = r1.text_input("Material / Papel")
                    gram = r2.number_input("Gramaje", 0)
                    ancho = r3.text_input("Referencia Comercial",)

                    r4, r5 = st.columns(2)

                    cant_r = r4.number_input("Cantidad Rollos Solicitada", 0)
                    objetivo = r5.text_input("Objetivo del Rebobinado")

                    obs = st.text_area("Observaciones Rebobinado")
                    
                else: 

#  SECCION: ROLLOS 
                    r1, r2, r3 = st.columns(3)
                    mat = r1.text_input("Material Base", value=datos_rec.get('material', ""))
                    gram = r2.number_input("Gramaje", 0, value=int(datos_rec.get('gramaje_rollos', 0)))
                    ref_c = r3.text_input("Referencia Comercial", value=datos_rec.get('ref_comercial', ""))
                    
                    r4, r5, r6 = st.columns(3)
                    cant_r = r4.number_input("Cantidad Rollos", 0, value=int(datos_rec.get('cantidad_rollos', 0)))
                    
                    cores = ["13MM", "19MM", "1 PULGADA", "40 MM", "2 PULGADAS", "3 PULGADAS", " NINGUNO"]
                    idx_core = cores.index(datos_rec['core']) if datos_rec.get('core') in cores else 0
                    core = r5.selectbox("Core / Centro", cores, index=idx_core)
                                    
                    tf_r, tr_r = "N/A", "N/A"
                    if t == "ROLLOS IMPRESOS":
                        ct1, ct2 = st.columns(2)
                        tf_r = ct1.text_input("Tintas Frente", value=datos_rec.get('tintas_frente_rollos', ""))
                        tr_r = ct2.text_input("Tintas Respaldo", value=datos_rec.get('tintas_respaldo_rollos', ""))
                    
                    r7, r8 = st.columns(2)
                    ub = r7.number_input("Unidades x Bolsa", 0, value=int(datos_rec.get('unidades_bolsa', 0)))
                    uc = r8.number_input("Unidades x Caja", 0, value=int(datos_rec.get('unidades_caja', 0)))
                    obs = st.text_area("Observaciones Generales Rollos", value=datos_rec.get('observaciones_rollos', ""))

#  ERROR SI TIENE CAMPOS SIN LLENAR 
                if st.form_submit_button("🚀 GUARDAR PLANIFICACIÓN"):

                    campos_faltantes = []

                    if not op_input:
                        campos_faltantes.append("Número OP")

                    if not cli:
                        campos_faltantes.append("Cliente")

                    if not vend:
                        campos_faltantes.append("Vendedor")

                    if not trab:
                        campos_faltantes.append("Nombre del Trabajo")

                    if campos_faltantes:
                        st.error("Faltan campos obligatorios: " + ", ".join(campos_faltantes))
                        st.stop()

                    op_final = f"{prefijo}{op_input.upper()}"

#  VALIDAR OP DUPLICADA
                    existe_op = supabase.table("ordenes_planeadas") \
                    .select("op") \
                    .eq("op", op_final) \
                    .execute()

                    if existe_op.data:
                        st.error(f"❌ La OP {op_final} ya existe. No se puede duplicar.")
                        st.stop()

# DEFINIR AREA INICIAL: TODA OP NUEVA PASA PRIMERO POR AUDITORIA VENTAS,
# sin importar su tipo (Formas/Rollos, Impresos/Blancos/Rebobinado).
# La ruta que le corresponda segun su tipo (ruta_despues_de_auditoria_ventas)
# se aplica solo cuando el Auditor de Ventas la marca como revisada.
                    ruta_inicial = "AUDITORIA VENTAS"

                    payload = {
                        "op": op_final,
                        "op_anterior": op_a,
                        "cliente": cli,
                        "vendedor": vend,
                        "nombre_trabajo": trab,
                        "tipo_orden": t,
                        "tipo_origen": origen,
                        "proxima_area": ruta_inicial,
                        "historial_procesos": [],
                        "creado_por": st.session_state.get('nombre_usuario', ''),
                        "num_ticket": int(num_ticket_creacion)
                    }

                    if "FORMAS" in t:
                        payload.update({
                            "cantidad_formas": int(cant_f),
                            "num_partes": partes,
                            "perforaciones_detalle": perf_d,
                            "codigo_barras_detalle": barr_d,
                            "num_id": num_id,    
                            "num_fd": num_fd, 
                            "tipo_origen": origen,   
                            "presentacion2": pres_peg, 
                            "transportadora_formas": True if t_trans_f == "SI" else None,
                            "destino_formas": dest_f if t_trans_f == "SI" else None,
                            "detalles_partes_json": lista_p,
                            "presentacion": pres,
                            "observaciones_formas": obs
                        })

                    elif t == "REBOBINADO":
                        payload.update({
                            "material": mat,
                            "gramaje_rollos": gram,
                            "ancho_base": ancho,
                            "tipo_origen": origen,
                            "cantidad_rollos": int(cant_r),
                            "objetivo_rebobinado": objetivo,
                            "observaciones_rollos": obs
                    })

                    else:
                        payload.update({
                            "material": mat,
                            "gramaje_rollos": gram,
                            "cantidad_rollos": int(cant_r),
                            "core": core,
                            "tintas_frente_rollos": tf_r,
                            "tintas_respaldo_rollos": tr_r,
                            "unidades_bolsa": int(ub),
                            "unidades_caja": int(uc),
                            "observaciones_rollos": obs,
                            "ref_comercial": ref_c,
                            "transportadora_rollos": True if t_trans_f == "SI" else None,
                            "destino_rollos": dest_f if t_trans_f == "SI" else None,
                        })

                    try:
                        supabase.table("ordenes_planeadas").insert(payload).execute()
                    except Exception:
                        payload.pop("creado_por", None)
                        supabase.table("ordenes_planeadas").insert(payload).execute()

                    st.session_state['ultima_op_creada'] = payload
                    st.success(f"Orden {op_final} registrada.")
                    st.session_state.sel_tipo = None

                    try:
                        existe_en_bodega = supabase.table("bodega_producto_terminado")\
                            .select("id, ref_comercial").eq("nombre_trabajo", trab).execute().data
                        if existe_en_bodega:
# YA EXISTE — no crear otro, solo actualizar la referencia si cambió
                            if ref_c and existe_en_bodega[0].get("ref_comercial") != ref_c:
                                try:
                                    supabase.table("bodega_producto_terminado")\
                                        .update({"ref_comercial": ref_c})\
                                        .eq("nombre_trabajo", trab).execute()
                                except Exception:
                                    pass
                        else:
# NO EXISTE — crear el registro por primera vez
                            tipo_b = "IMPRESO" if "IMPRESO" in (t or "").upper() else (
                                "REBOBINADO" if "REBOBINADO" in (t or "").upper() else "BLANCO"
                            )
                            registro_bodega_nuevo = {
                                "nombre_trabajo": trab,
                                "tipo_producto": tipo_b,
                                "stock_cajas": 0,
                                "stock_rollos": 0,
                                "ultima_actualizacion": hora_colombia().isoformat(),
                                "observaciones": "Creado automáticamente al generar la OP",
                                "ref_comercial": ref_c
                            }
                            try:
                                supabase.table("bodega_producto_terminado").insert(registro_bodega_nuevo).execute()
                            except Exception:
# Compatibilidad: si la columna ref_comercial aun no existe
                                registro_bodega_nuevo.pop("ref_comercial", None)
                                supabase.table("bodega_producto_terminado").insert(registro_bodega_nuevo).execute()
                    except Exception:
                        pass

                    time.sleep(1.5)
                    st.rerun()

# MODULO: BODEGA PRODUCTO TERMINADO 
elif menu == "📦 salida produccion P1":
    st.title("📦 Inventario de Producto Terminado")
    
    tab_mov, tab_inv = st.tabs(["🔄 Movimientos (Entrada/Salida)", "📊 Inventario Actual"])
    
    with tab_mov:
        st.subheader("🔄 Gestión de Movimientos")
        
# IDENTIFICAR PERMISOS SEGUN ROL
        rol_usuario = st.session_state.get('rol', '').lower()
        
# DEFINE QUIN PUEDE HACER QUE DENTRO DEL MODULO 
        puede_ingresar = rol_usuario in ['admin', 'patinador_roll' ] 
        puede_despachar = rol_usuario in ['admin', 'ventas']

#  SELECTOR DE OPERACION FILTRADO
        opciones_disponibles = []
        if puede_ingresar: opciones_disponibles.append("➕ ENTRADA (Ingreso)")
        if puede_despachar: opciones_disponibles.append("➖ SALIDA (Despacho)")

        if not opciones_disponibles:
            st.warning("⚠️ Tu rol no tiene permisos para registrar movimientos en bodega.")
        else:
            tipo_accion = st.radio("Seleccione operación:", opciones_disponibles, horizontal=True)
            
            productos_db = supabase.table("bodega_producto_terminado").select("*").execute().data
            nombres_existentes = sorted([p['nombre_trabajo'] for p in productos_db])

            with st.form("form_movimiento_separado"):
                col1, col2 = st.columns(2)
                
                with col1:

#  SI ES INGRESO SEJA CREAR SI ES SALIDA SOLO SELECCIONA DE LO YA EXISTENTE
                    if "ENTRADA" in tipo_accion:
                        nuevo_o_existente = st.checkbox("¿Es un producto nuevo en bodega?")
                        if nuevo_o_existente:
                            nom_trabajo = st.text_input("Nombre del Trabajo (NUEVO)").upper()
                        else:
                            nom_trabajo = st.selectbox("Seleccione Trabajo Existente:", [""] + nombres_existentes)
                    else:
                        st.info("ℹ️ Solo puede dar salida a productos que ya están en el inventario.")
                        nom_trabajo = st.selectbox("Seleccione Trabajo para Despacho:", [""] + nombres_existentes)
                    
                    tipo_prod = st.selectbox("Tipo de Producto:", ["BLANCO", "IMPRESO", "REBOBINADO"])
                
                with col2:
                    c_cajas = st.number_input("Cantidad de Cajas", min_value=0, step=1)
                    c_rollos = st.number_input("Cantidad de Rollos", min_value=0, step=1)
                    notas = st.text_input("Observaciones (Ej: Factura # o Cliente)")

# BOTON DINAMICO DE REGISTRO A INGRESOS
                texto_boton = "🚀 REGISTRAR ENTRADA" if "ENTRADA" in tipo_accion else "🚚 REGISTRAR SALIDA"
                btn_procesar = st.form_submit_button(texto_boton)

                if btn_procesar:
                    if not nom_trabajo or nom_trabajo == "":
                        st.error("Debe especificar el nombre del trabajo.")
                    elif c_cajas == 0 and c_rollos == 0:
                        st.warning("Ingrese una cantidad válida de cajas o rollos.")
                    else:
                        fecha_mov = hora_colombia().isoformat()
                        producto_actual = next((p for p in productos_db if p['nombre_trabajo'] == nom_trabajo), None)
                        
# LOGICA DE SUMA Y RESTA
                        es_entrada = "ENTRADA" in tipo_accion
                        factor = 1 if es_entrada else -1

# VALIDACION DE STOCK PARA SALIDAS
                        if not es_entrada:
                            if not producto_actual:
                                st.error("El producto no existe en inventario.")
                                st.stop()
                            if c_cajas > producto_actual.get('stock_cajas', 0):
                                st.error(f"❌ Stock insuficiente. Solo hay {producto_actual['stock_cajas']} cajas disponibles.")
                                st.stop()

# ACTUALIZAR O INSERTAR EN BODEGA ACTUAL
                        try:
                            if producto_actual:

# ACTUALIZAR EXISTENTE
                                nuevo_stk_cajas = producto_actual['stock_cajas'] + (c_cajas * factor)
                                nuevo_stk_rollos = producto_actual['stock_rollos'] + (c_rollos * factor)
                                
                                supabase.table("bodega_producto_terminado").update({
                                    "stock_cajas": nuevo_stk_cajas,
                                    "stock_rollos": nuevo_stk_rollos,
                                    "ultima_actualizacion": fecha_mov,
                                    "observaciones": notas  
                                }).eq("id", producto_actual['id']).execute()
                            
                            elif es_entrada:

# INSERTAR NUEVO (Solo si es entrada)
                                supabase.table("bodega_producto_terminado").insert({
                                    "nombre_trabajo": nom_trabajo,
                                    "tipo_producto": tipo_prod,
                                    "stock_cajas": c_cajas,
                                    "stock_rollos": c_rollos,
                                    "ultima_actualizacion": fecha_mov,
                                    "observaciones": notas
                                }).execute()

#  REGISTRAR SIEMPRE EN HISTORIAL 
                            supabase.table("bodega_historial").insert({
                                "nombre_trabajo": nom_trabajo,
                                "tipo_movimiento": "ENTRADA" if es_entrada else "SALIDA",
                                "cajas": c_cajas,
                                "rollos": c_rollos,
                                "fecha": fecha_mov,
                                "usuario": st.session_state.get('nombre_usuario', 'Sistema'),
                                "observaciones": notas
                            }).execute()

                            st.success(f"✅ {texto_boton} exitoso para: {nom_trabajo}")
                            time.sleep(1.2)
                            st.rerun()
                        
                        except Exception as e:
                            st.error(f"Error al procesar en base de datos: {e}")

# PESTAÑA DE INVENTARIO ACTUAL
    with tab_inv:
        st.subheader("📊 Existencias en Bodega")
        
        res_bodega = supabase.table("bodega_producto_terminado").select("*").order("nombre_trabajo").execute().data
        
        if res_bodega:
            df_bodega = pd.DataFrame(res_bodega)
            
            cols_esperadas = ['nombre_trabajo', 'ref_comercial', 'tipo_producto', 'stock_cajas', 'stock_rollos', 'ultima_actualizacion', 'observaciones']
            cols_finales = [c for c in cols_esperadas if c in df_bodega.columns]
            
            df_show = df_bodega[cols_finales].copy()
            df_show = formatear_fechas_df(df_show)
            
# RENOMBRAR COLUMBAS PARA VISUALIZACION 
            nombres_columnas = {
                'nombre_trabajo': 'TRABAJO',
                'ref_comercial': 'REFERENCIA',
                'tipo_producto': 'TIPO',
                'stock_cajas': 'CAJAS',
                'stock_rollos': 'ROLLOS',
                'ultima_actualizacion': 'ÚLT. MOVIMIENTO',
                'observaciones': 'OBSERVACIONES'
            }
            df_show.rename(columns=nombres_columnas, inplace=True)
            
# BUSCADOR RAPIDO
            busqueda_b = st.text_input("🔍 Filtrar inventario por nombre...")
            if busqueda_b:
                df_show = df_show[df_show['TRABAJO'].str.contains(busqueda_b.upper(), na=False)]
            
# MOSTRAR TABLAS 
            st.dataframe(df_show, use_container_width=True, hide_index=True)
            
# ALERTAS D ESTOCK BAJO 
            if 'CAJAS' in df_show.columns:
                bajo_stock = df_show[df_show['CAJAS'] <= 2]
                if not bajo_stock.empty:
                    st.warning(f"⚠️ Hay {len(bajo_stock)} productos con stock crítico (2 o menos cajas).")
        else:
            st.info("La bodega está vacía actualmente.")

# MODULO: REPORTES 
elif menu == "📊 Reportes Admin":
        st.title("📊 Panel de Control y Reportes")
        
        tab_historial, tab_muertos, tab_paradas, tab_traza, tab_movs = st.tabs([
            "📦 Historial de Bodega", 
            "⏳ Disponibilidad (Máquina Libre)", 
            "🛑 Reporte de Paradas (Fallas)",
            "🗂️ Trazabilidad de OPs",
            "🛠️ Movimientos del Sistema"
        ])
        
        with tab_historial:
            st.subheader("Historial de Movimientos de Bodega")
# OPTIMIZACION: por defecto solo trae los 500 movimientos mas recientes (mucho mas
# rapido); si se necesita revisar mas atras, el interruptor trae todo el historico.
            ver_todo_bodega = st.checkbox("Ver historial completo (puede tardar más)", key="ver_todo_bodega")
            q_h = supabase.table("bodega_historial").select("*").order("fecha", desc=True)
            if not ver_todo_bodega:
                q_h = q_h.limit(500)
            res_h = q_h.execute().data
            if res_h:
                if not ver_todo_bodega:
                    st.caption(f"Mostrando los {len(res_h)} movimientos más recientes.")
                df_h = pd.DataFrame(res_h)
                df_h = formatear_fechas_df(df_h)
                st.dataframe(df_h, use_container_width=True, hide_index=True)
            else:
                st.info("Sin registros en bodega.")

        with tab_muertos:
            st.subheader("⏳ Tiempo de Máquina Libre (Sin Órdenes)")

#  TOMA DE TIEMPOS DE MAQUIA LIBRE ENTRE UN AOP Y OTRA 
# OPTIMIZACION: mismo criterio — 500 mas recientes por defecto, con opcion de ver todo.
            ver_todo_muertos = st.checkbox("Ver historial completo (puede tardar más)", key="ver_todo_muertos")
            q_m = supabase.table("tiempos_muertos").select("*").order("fecha", desc=True)
            if not ver_todo_muertos:
                q_m = q_m.limit(500)
            res_m = q_m.execute().data
            if res_m:
                if not ver_todo_muertos:
                    st.caption(f"Mostrando los {len(res_m)} registros más recientes.")
                df_m = pd.DataFrame(res_m)

# LA TABLA GUARDA LA DURACION EN SEGUNDOS -> SE CONVIERTE A MINUTOS PARA MOSTRAR
                if 'duracion_segundos' in df_m.columns:
                    df_m['duracion_min'] = (df_m['duracion_segundos'].fillna(0) / 60).round(1)
                    total_libre = df_m['duracion_min'].sum()
                    st.metric("Total Tiempo Libre (Ocioso)", f"{total_libre:.1f} min")
                    df_m = df_m.drop(columns=['duracion_segundos'])
                df_m = formatear_fechas_df(df_m)
                st.dataframe(df_m, use_container_width=True, hide_index=True)
            else:
                st.info("No hay registros de tiempo libre.")

        with tab_paradas:
            st.subheader("🛑 Reporte de Fallas y Paradas Técnicas")

# AQUI S EMUESTRA PORQUE LA MAQUINA SE DERUBO 
# OPTIMIZACION: mismo criterio — 500 mas recientes por defecto, con opcion de ver todo.
            ver_todo_paradas = st.checkbox("Ver historial completo (puede tardar más)", key="ver_todo_paradas")
            q_p = supabase.table("paradas_maquina").select("*").order("fecha", desc=True)
            if not ver_todo_paradas:
                q_p = q_p.limit(500)
            res_p = q_p.execute().data
            if res_p:
                if not ver_todo_paradas:
                    st.caption(f"Mostrando los {len(res_p)} registros más recientes.")
                df_p = pd.DataFrame(res_p)

# LA TABLA GUARDA LA DURACION EN SEGUNDOS -> SE CONVIERTE A MINUTOS PARA MOSTRAR
                if 'duracion_segundos' in df_p.columns:
                    df_p['duracion_min'] = (df_p['duracion_segundos'].fillna(0) / 60).round(1)
                    total_parada = df_p['duracion_min'].sum()
                    st.metric("Total Tiempo Perdido por Fallas", f"{total_parada:.1f} min", delta_color="inverse")
                    df_p = df_p.drop(columns=['duracion_segundos'])
                
                df_p = formatear_fechas_df(df_p)
                st.dataframe(df_p, use_container_width=True, hide_index=True)
            else:
                st.info("No hay reportes de fallas técnicos.")

# TRAZABILIDAD COMPLETA DE OPs (desde que se crea hasta el ultimo paso) 
        with tab_traza:
            st.subheader("🗂️ Trazabilidad Completa de Órdenes de Producción")
            st.caption("Quién creó cada orden y cada paso por el que ha pasado en planta, con fechas y responsables.")

# SEPARA LAS ORDENES POR PREFIJO (RI-, RB-, FRI-, FRB-, RR-) PARA QUE SEA MAS FACIL
# BUSCAR UNA TRAZABILIDAD ESPECIFICA SIN TENER QUE VER TODAS MEZCLADAS
            sub_ri, sub_rb, sub_fri, sub_frb, sub_rr = st.tabs([
                "🌀 RI- (Rollos Impresos)", "⚪ RB- (Rollos Blancos)",
                "📑 FRI- (Formas Impresas)", "📄 FRB- (Formas Blancas)", "🔄 RR- (Rebobinado)"
            ])

            def _tab_trazabilidad_por_prefijo(prefijo, key_sufijo):
                busqueda_op = st.text_input(
                    f"🔎 Buscar por número de OP o nombre de cliente (dentro de {prefijo})",
                    key=f"busca_traza_{key_sufijo}"
                )

                todas_ops_traza = supabase.table("ordenes_planeadas").select("*").ilike("op", f"{prefijo}%").execute().data or []

                if busqueda_op:
                    b = busqueda_op.strip().lower()
                    todas_ops_traza = [
                        o for o in todas_ops_traza
                        if b in str(o.get("op", "")).lower() or b in str(o.get("cliente", "")).lower()
                    ]

                def _fecha_orden_traza(o):
                    return str(o.get("created_at") or o.get("fecha_creacion") or "")
                todas_ops_traza.sort(key=_fecha_orden_traza, reverse=True)

                if not busqueda_op:
                    st.info(f"Mostrando las 50 órdenes {prefijo} más recientes de {len(todas_ops_traza)}. Usa el buscador para ver cualquier OP histórica.")
                    todas_ops_traza = todas_ops_traza[:50]
                else:
                    st.caption(f"{len(todas_ops_traza)} orden(es) encontradas")

                for o in todas_ops_traza:
                    fecha_creacion_raw = o.get("created_at") or o.get("fecha_creacion") or ""
                    fecha_creacion_fmt = fmt_fecha_hora(fecha_creacion_raw) if fecha_creacion_raw else "Sin fecha"

# 'creado_por' solo existe en ordenes creadas despues de activar esta funcion
                    creador = o.get("creado_por") or "No registrado (orden anterior a esta función)"
                    estado_actual = o.get("proxima_area", "Sin estado")

                    with st.expander(f"📋 OP {o.get('op')} | {o.get('cliente','')} | Estado: {estado_actual}"):
                        c1, c2, c3 = st.columns(3)
                        c1.markdown(f"**Vendedor:** {o.get('vendedor','-')}")
                        c2.markdown(f"**Creado por:** {creador}")
                        c3.markdown(f"**Fecha creación:** {fecha_creacion_fmt}")
                        st.markdown(f"**Trabajo:** {o.get('nombre_trabajo','-')}  |  **Tipo:** {o.get('tipo_orden','-')}")

                        historial = o.get("historial_procesos") or []

# RESUMEN RAPIDO DE TIEMPOS POR AREA (areas ya completadas, en el orden que las paso)
# Esto responde "cuanto duro en el area anterior" sin tener que abrir la linea de tiempo completa de abajo.
                        resumen_tiempos = []
                        for h in historial:
                            area_h = (h.get('area') or '').strip().upper()
                            tipo_h = (h.get('tipo') or '').strip().upper()
                            if area_h.startswith('EDIC') or tipo_h.startswith('EDIC'):
                                continue
                            t_area = h.get('tiempo_total_area') or h.get('duracion') or '-'
                            resumen_tiempos.append(f"**{h.get('area','-')}**: {t_area}")
                        if resumen_tiempos:
                            st.success("📊 Tiempo que duró en cada área anterior:  " + "   |   ".join(resumen_tiempos))

    # TIEMPO EN EL AREA ACTUAL (si la orden todavia no ha finalizado, se calcula en vivo)
                        if estado_actual != "FINALIZADO":
                            _, tiempo_actual_area = calcular_tiempo_en_area(o)
                            st.info(f"⏳ Lleva **{tiempo_actual_area}** en el área actual (**{estado_actual}**)")

                        if not historial:
                            st.info("Esta orden todavía no tiene pasos de producción registrados.")
                        else:
                            st.markdown("**🔗 Línea de tiempo de producción:**")
                            for paso_idx, paso in enumerate(historial, start=1):
                                if (paso.get('area') or '').strip().upper().startswith('EDIC') or (paso.get('tipo') or '').strip().upper().startswith('EDIC'):
                                    motivo_edicion_traza = (
                                        paso.get('observaciones')
                                        or paso.get('motivo')
                                        or paso.get('motivo_edicion')
                                        or (paso.get('nota', '').replace('Editado: ', '') if paso.get('nota') else None)
                                        or 'Sin motivo registrado'
                                    )
                                    st.markdown(
                                        f"**{paso_idx}. ✏️ EDICIÓN DE LA ORDEN** — "
                                        f"Editado por: {paso.get('operario') or paso.get('usuario','-')}  |  "
                                        f"{paso.get('fecha','-')}"
                                    )
                                    st.caption(f"📝 Motivo: {motivo_edicion_traza}")
                                    st.divider()
                                    continue
                                st.markdown(
                                    f"**{paso_idx}. {paso.get('area','-')}** — Máquina: {paso.get('maquina','-')}  |  "
                                    f"Operario: {paso.get('operario','-')}  |  Auxiliar: {paso.get('auxiliar','-') or '-'}  |  "
                                    f"{paso.get('fecha','-')}  |  Duración trabajada: {paso.get('duracion','-')}  |  Tipo: {paso.get('tipo','-')}"
                                )
    # TIEMPO TOTAL QUE LA OP ESTUVO EN ESTA AREA (desde que entro hasta que salio, incluyendo esperas/pausas)
                                if paso.get("tiempo_total_area"):
                                    st.caption(f"⏱️ Tiempo total en el área: {paso['tiempo_total_area']}")
                                if paso.get("observaciones"):
                                    st.caption(f"📝 {paso['observaciones']}")
                                if paso.get("datos_cierre"):
                                    with st.expander(f"Ver datos técnicos del paso {paso_idx}"):
                                        df_paso = pd.DataFrame(list(paso["datos_cierre"].items()), columns=["Parámetro", "Valor"])
                                        df_paso["Parámetro"] = df_paso["Parámetro"].str.replace("_", " ").str.upper()
                                        st.table(df_paso)
                                st.divider()

# LLAMA LA FUNCION DE ARRIBA UNA VEZ POR CADA PESTAÑA, FILTRANDO POR SU PROPIO PREFIJO DE OP
            with sub_ri:
                _tab_trazabilidad_por_prefijo("RI-", "ri")
            with sub_rb:
                _tab_trazabilidad_por_prefijo("RB-", "rb")
            with sub_fri:
                _tab_trazabilidad_por_prefijo("FRI-", "fri")
            with sub_frb:
                _tab_trazabilidad_por_prefijo("FRB-", "frb")
            with sub_rr:
                _tab_trazabilidad_por_prefijo("RR-", "rr")

#  TAB NUEVA: MOVIMIENTOS DEL SISTEMA (coins, usuarios, etc) 
        with tab_movs:
            st.subheader("🛠️ Movimientos y Actividad del Sistema")

            sub_coins, sub_usuarios = st.tabs(["🪙 Movimientos de Coins", "👥 Usuarios del Sistema"])

            with sub_coins:
                st.caption("Cada vez que se asignan o descuentan coins a un trabajador, queda registrado aquí.")
                res_coins = supabase.table("monedas_historial").select("*").order("fecha", desc=True).execute().data or []
                if res_coins:
                    df_coins = pd.DataFrame(res_coins)
                    if 'cantidad' in df_coins.columns:
                        otorgados = df_coins[df_coins['cantidad'] > 0]['cantidad'].sum()
                        descontados = df_coins[df_coins['cantidad'] < 0]['cantidad'].sum()
                        c1, c2 = st.columns(2)
                        c1.metric("🟢 Total Coins Otorgados", f"+{otorgados}")
                        c2.metric("🔴 Total Coins Descontados", f"{descontados}")
                    df_coins = formatear_fechas_df(df_coins)
                    st.dataframe(df_coins, use_container_width=True, hide_index=True)
                else:
                    st.info("Sin movimientos de coins registrados todavía.")

            with sub_usuarios:
                st.caption("Listado de todos los usuarios con acceso al sistema (no se muestran contraseñas).")
                try:
                    res_usuarios = supabase.table("usuarios").select("usuario, nombre, rol, maquina_asignada").execute().data or []
                except Exception:
                    res_usuarios = supabase.table("usuarios").select("usuario, nombre, rol").execute().data or []
                if res_usuarios:
                    df_usuarios = pd.DataFrame(res_usuarios)
                    st.dataframe(df_usuarios, use_container_width=True, hide_index=True)
                    st.caption(f"Total de usuarios registrados: {len(res_usuarios)}")
                else:
                    st.info("No hay usuarios registrados.")


# MODULO ALMACEN/DESPACHOS: registra entradas y salidas de producto terminado hasta que sale despachado al cliente
elif menu == "📦 Almacen/Despachos":
    st.title("📦 Inventario de Productos Almacen")
    
    tab_mov, tab_inv = st.tabs(["🔄 Movimientos (Entrada/Salida)", "📊 Inventario Actual"])
    
    with tab_mov:
        st.subheader("🔄 Gestión de Movimientos")
        
# IDENTIFICAR PERMISOS SEGUN ROL
        rol_usuario = st.session_state.get('rol', '').lower()
        
# DEFINE QUIN PUEDE HACER QUE DENTRO DEL MODULO 
        puede_ingresar = rol_usuario in ['admin', 'jefe_log', 'patinador_log' ] 
        puede_despachar = rol_usuario in ['admin', 'jefe_log', 'patinador_log', 'aux_log']

#  SELECTOR DE OPERACION FILTRADO
        opciones_disponibles = []
        if puede_ingresar: opciones_disponibles.append("➕ ENTRADA DE MERCANCIA (Ingreso)")
        if puede_despachar: opciones_disponibles.append("➖ SALIDA DE MERCANCIA (Despacho)")

        if not opciones_disponibles:
            st.warning("⚠️ Tu rol no tiene permisos para registrar movimientos en bodega.")
        else:
            tipo_accion = st.radio("Seleccione operación:", opciones_disponibles, horizontal=True)
            
            productos_db = supabase.table("almacen_producto_terminado").select("*").execute().data
            nombres_existentes = sorted([p['nombre_trabajo'] for p in productos_db])

            with st.form("form_movimiento_separado"):
                col1, col2 = st.columns(2)
                
                with col1:

#  SI ES INGRESO SEJA CREAR SI ES SALIDA SOLO SELECCIONA DE LO YA EXISTENTE
                    if "ENTRADA" in tipo_accion:
                        nuevo_o_existente = st.checkbox("¿Es un producto nuevo en bodega?")
                        if nuevo_o_existente:
                            nom_trabajo = st.text_input("Nombre del Trabajo (NUEVO)").upper()
                        else:
                            nom_trabajo = st.selectbox("Seleccione Trabajo Existente:", [""] + nombres_existentes)
                    else:
                        st.info("ℹ️ Solo puede dar salida a productos que ya están en el inventario.")
                        nom_trabajo = st.selectbox("Seleccione Trabajo para Despacho:", [""] + nombres_existentes)
                    
                    tipo_prod = st.selectbox("Tipo de Producto:", ["BLANCO", "IMPRESO", "REBOBINADO", "ADHESIVO"])
                
                with col2:
                    c_cajas = st.number_input("Cantidad de Cajas", min_value=0, step=1)
                    c_rollos = st.number_input("Cantidad de Rollos", min_value=0, step=1)
                    notas = st.text_input("Observaciones (Ej: Factura # o Cliente)")

# BOTON DINAMICO DE REGISTRO A INGRESOS
                texto_boton = "🚀 REGISTRAR ENTRADA" if "ENTRADA" in tipo_accion else "🚚 REGISTRAR SALIDA"
                btn_procesar = st.form_submit_button(texto_boton)

                if btn_procesar:
                    if not nom_trabajo or nom_trabajo == "":
                        st.error("Debe especificar el nombre del trabajo.")
                    elif c_cajas == 0 and c_rollos == 0:
                        st.warning("Ingrese una cantidad válida de cajas o rollos.")
                    else:
                        fecha_mov = hora_colombia().isoformat()
                        producto_actual = next((p for p in productos_db if p['nombre_trabajo'] == nom_trabajo), None)
                        
# LOGICA DE SUMA Y RESTA
                        es_entrada = "ENTRADA" in tipo_accion
                        factor = 1 if es_entrada else -1

# VALIDACION DE STOCK PARA SALIDAS
                        if not es_entrada:
                            if not producto_actual:
                                st.error("El producto no existe en inventario.")
                                st.stop()
                            if c_cajas > producto_actual.get('stock_cajas', 0):
                                st.error(f"❌ Stock insuficiente. Solo hay {producto_actual['stock_cajas']} cajas disponibles.")
                                st.stop()

# ACTUALIZAR O INSERTAR EN BODEGA ACTUAL
                        try:
                            if producto_actual:

# ACTUALIZAR EXISTENTE
                                nuevo_stk_cajas = producto_actual['stock_cajas'] + (c_cajas * factor)
                                nuevo_stk_rollos = producto_actual['stock_rollos'] + (c_rollos * factor)
                                
                                supabase.table("almacen_producto_terminado").update({
                                    "stock_cajas": nuevo_stk_cajas,
                                    "stock_rollos": nuevo_stk_rollos,
                                    "ultima_actualizacion": fecha_mov,
                                    "observaciones": notas  
                                }).eq("id", producto_actual['id']).execute()
                            
                            elif es_entrada:

# INSERTAR NUEVO (Solo si es entrada)
                                supabase.table("almacen_producto_terminado").insert({
                                    "nombre_trabajo": nom_trabajo,
                                    "tipo_producto": tipo_prod,
                                    "stock_cajas": c_cajas,
                                    "stock_rollos": c_rollos,
                                    "ultima_actualizacion": fecha_mov,
                                    "observaciones": notas
                                }).execute()

#  REGISTRAR SIEMPRE EN HISTORIAL 
                            supabase.table("bodega_historial").insert({
                                "nombre_trabajo": nom_trabajo,
                                "tipo_movimiento": "ENTRADA" if es_entrada else "SALIDA",
                                "cajas": c_cajas,
                                "rollos": c_rollos,
                                "fecha": fecha_mov,
                                "usuario": st.session_state.get('nombre_usuario', 'Sistema'),
                                "observaciones": notas
                            }).execute()

                            st.success(f"✅ {texto_boton} exitoso para: {nom_trabajo}")
                            time.sleep(1.2)
                            st.rerun()
                        
                        except Exception as e:
                            st.error(f"Error al procesar en base de datos: {e}")

# PESTAÑA DE INVENTARIO ACTUAL
    with tab_inv:
        st.subheader("📊 Existencias en Bodega")
        
        res_bodega = supabase.table("almacen_producto_terminado").select("*").order("nombre_trabajo").execute().data
        
        if res_bodega:
            df_bodega = pd.DataFrame(res_bodega)
            
            cols_esperadas = ['nombre_trabajo', 'tipo_producto', 'stock_cajas', 'stock_rollos', 'ultima_actualizacion', 'observaciones']
            cols_finales = [c for c in cols_esperadas if c in df_bodega.columns]
            
            df_show = df_bodega[cols_finales].copy()
            df_show = formatear_fechas_df(df_show)
            
# RENOMBRAR COLUMBAS PARA VISUALIZACION 
            nombres_columnas = {
                'nombre_trabajo': 'TRABAJO',
                'tipo_producto': 'TIPO',
                'stock_cajas': 'CAJAS',
                'stock_rollos': 'ROLLOS',
                'ultima_actualizacion': 'ÚLT. MOVIMIENTO',
                'observaciones': 'OBSERVACIONES'
            }
            df_show.rename(columns=nombres_columnas, inplace=True)
            
# BUSCADOR RAPIDO
            busqueda_b = st.text_input("🔍 Filtrar inventario por nombre...")
            if busqueda_b:
                df_show = df_show[df_show['TRABAJO'].str.contains(busqueda_b.upper(), na=False)]
            
# MOSTRAR TABLAS 
            st.dataframe(df_show, use_container_width=True, hide_index=True)
            
# ALERTAS D ESTOCK BAJO 
            if 'CAJAS' in df_show.columns:
                bajo_stock = df_show[df_show['CAJAS'] <= 2]
                if not bajo_stock.empty:
                    st.warning(f"⚠️ Hay {len(bajo_stock)} productos con stock crítico (2 o menos cajas).")
        else:
            st.info("La bodega está vacía actualmente.")

elif menu == "⏱️ Seguimiento Cortadoras":
        st.header("⏱️ Seguimiento Horario de Cortadoras")
        
        maq_sel = st.selectbox("Seleccione la Máquina", MAQUINAS["CORTE"])
        
        t1, t2 = st.tabs(["📝 Registro", "📋 Historial"])
        
        with t1:
            with st.form("f_seg_hor", clear_on_submit=True):
                ca, cb, cc = st.columns(3)
                with ca:
                    op_s = st.text_input("OP")
                    nt_s = st.text_input("Nombre Trabajo")
                    tipo_p = st.text_input("Tipo de Papel / Material")
                    turno_s = st.selectbox("Turno", ["Dia", "Mañana", "Tarde", "Noche"])
                with cb:
                    m_r = st.number_input("Metros de Rollo", min_value=0, value=0)
                    med_r = st.text_input("Medida de Rollo")
                    u_c = st.number_input("Unid/Caja", min_value=0, value=0)
                    n_c = st.number_input("Número Cajas", min_value=0, value=0)
                with cc:
                    n_v = st.number_input("Varillas", min_value=0, value=0)
                    p_d = st.number_input("Desp. KG", min_value=0.0, value=0.0, step=0.1)
                    mot_d = st.text_input("Motivo Desp.")
                    obs = st.text_area("Observaciones")
                
# Campos de cierre de turno opcionales
                st.markdown("---")
                st.markdown("##### 📦 Datos de Cierre de Turno (Opcional)")
                col_x, col_y = st.columns(2)
                with col_x: 
                    c_t = st.number_input("TOTAL CAJAS TURNO", min_value=0, value=0)
                with col_y: 
                    v_t = st.number_input("TOTAL VARILLAS TURNO", min_value=0, value=0)
                
                if st.form_submit_button("🚀 Guardar Avance"):
                    if not op_s:
                        st.error("⚠️ El número de OP es obligatorio para registrar el avance.")
                    else:
                        try:
                            datos_insertar = {
                                "fecha": hora_colombia().strftime("%Y-%m-%d"), 
                                "hora_registro": hora_colombia().strftime("%H:%M"),
                                "turno": turno_s, 
                                "maquina": maq_sel, 
                                "op": str(op_s), 
                                "nombre_trabajo": nt_s,
                                "tipo_papel": tipo_p, 
                                "metros_rollo": m_r, 
                                "medida_rollo": med_r,
                                "unidades_por_caja": u_c, 
                                "num_varillas": n_v, 
                                "num_cajas": n_c,
                                "peso_desperdicio": p_d,
                                "motivo_desperdicio_seg": mot_d, 
                                "observaciones": obs,
                                "total_cajas_empacadas": c_t, 
                                "total_varillas_sacadas": v_t
                            }
                            
                            supabase.table("seguimiento_cortadoras").insert(datos_insertar).execute()
                            st.success(f"🎉 Avance de la máquina {maq_sel} guardado exitosamente en la nube.")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar en Supabase: {e}")
                            
        with t2:
            st.markdown(f"### Historial Reciente - {maq_sel}")
            try:
                query = supabase.table("seguimiento_cortadoras").select("*").eq("maquina", maq_sel)
                respuesta = query.order("id", desc=True).execute()
                
                if respuesta.data:
                    df_h = pd.DataFrame(respuesta.data)
                    df_h = formatear_fechas_df(df_h, columnas=['fecha'])
                    
                    columnas_visibles = ["fecha", "hora_registro", "turno", "op", "nombre_trabajo", "num_cajas", "num_varillas", "peso_desperdicio", "observaciones"]
                    
# Renombrar las columnas para que se vea estetico en pantalla
                    df_mostrar = df_h[columnas_visibles].rename(columns={
                        "fecha": "Fecha",
                        "hora_registro": "Hora",
                        "turno": "Turno",
                        "op": "OP",
                        "nombre_trabajo": "Trabajo",
                        "num_cajas": "Cajas",
                        "num_varillas": "Varillas",
                        "peso_desperdicio": "Desp. (KG)",
                        "observaciones": "Observaciones"
                    })
                    
                    st.dataframe(df_mostrar, use_container_width=True)
                else:
                    st.info("No hay registros previos para esta máquina.")
            except Exception as e:
                st.error(f"Error al cargar el historial: {e}")

#  CRONOGRAMA DE IMPRESIÓN ESTILO NOTION
elif menu == "📆 Cronograma Impresión":
    import streamlit.components.v1 as components
    import json

    st.markdown("<div class='title-area'>📆 CRONOGRAMA DE IMPRESIÓN</div>", unsafe_allow_html=True)
    st.caption("Arrastra las tarjetas al cronograma. Mueve o estira los bloques para ajustar. Todo se guarda solo.")

    lista_maquinas = ["ATF-22", "HR-22", "HAMILTON", "HR-17", "DIDDE 11", "MULTILYTH 1", "MULTILYTH 2"]

    qp = st.query_params
    if "crono_id" in qp:
        try:
            supabase.table("ordenes_planeadas").update({
                "fecha_inicio_cronograma": qp["crono_start"],
                "fecha_fin_cronograma":    qp["crono_end"],
                "maquina_cronograma":      qp["crono_maq"]
            }).eq("id", qp["crono_id"]).execute()
        except Exception as e:
            st.error(f"No se pudo guardar el cambio de cronograma: {e}")
        st.query_params.clear()
        st.rerun()

    try:
# OPTIMIZACION: el cronograma solo necesita ordenes que TODAVIA se puedan agendar/mover,
# no hace falta traer tambien anos de ordenes ya finalizadas (que antes se descargaban
# completas, con su historial_procesos, solo para descartarlas un renglon despues).
        todas_las_ops = supabase.table("ordenes_planeadas").select("*").neq("proxima_area", "FINALIZADO").execute().data or []
    except Exception as e:
        st.warning(f"No se pudieron cargar las órdenes planeadas: {e}")
        todas_las_ops = []

    # ALERTAS
    ahora_col = hora_colombia()
    alertas = []
    for op in todas_las_ops:
        if op.get("estado") == "Terminado" or op.get("proxima_area") == "FINALIZADO":
            continue
        fecha_fin_crono = op.get("fecha_fin_cronograma")
        if fecha_fin_crono:
            try:
                dt_fin_crono = datetime.fromisoformat(str(fecha_fin_crono).replace("Z","")).replace(tzinfo=pytz.utc).astimezone(pytz.timezone("America/Bogota"))
                if ahora_col > dt_fin_crono:
                    horas_retraso = int((ahora_col - dt_fin_crono).total_seconds() // 3600)
                    alertas.append(f"⏰ **OP {op.get('op')}** ({op.get('cliente','')}) — lleva **{horas_retraso}h de retraso**")
            except:
                pass
        fecha_creacion = op.get("fecha_creacion") or op.get("created_at")
        if fecha_creacion and not op.get("maquina_cronograma") and not op.get("excluir_cronograma"):
            try:
                dt_creacion = datetime.fromisoformat(str(fecha_creacion).replace("Z","")).replace(tzinfo=pytz.utc).astimezone(pytz.timezone("America/Bogota"))
                if (ahora_col - dt_creacion).days >= 3:
                    alertas.append(f"📋 **OP {op.get('op')}** — lleva **{(ahora_col - dt_creacion).days} dias sin asignar**")
            except:
                pass

    if alertas:
        with st.expander(f"🚨 {len(alertas)} ALERTA(S) — haz clic para ver", expanded=True):
            for a in alertas:
                st.warning(a)
    else:
        st.success("✅ Todo en orden")

# Separa las OPs que YA estan agendadas en el calendario de las que TODAVIA estan pendientes por asignar
    ops_agendadas  = [op for op in todas_las_ops if op.get("fecha_inicio_cronograma") and op.get("fecha_fin_cronograma") and op.get("maquina_cronograma")]
    ops_pendientes = [op for op in todas_las_ops if
                      not (op.get("fecha_inicio_cronograma") and op.get("maquina_cronograma"))
                      and op.get("proxima_area") != "FINALIZADO"
                      and op.get("estado") != "Terminado"
                      and not op.get("excluir_cronograma")]

# Construye los bloques (eventos) que dibuja el calendario, con su color segun el estado de la OP
    eventos_json = []
    for op in ops_agendadas:
        if op.get("proxima_area") == "FINALIZADO":
            color, etiqueta = "#4a4a4a", "FINALIZADA"
        elif op.get("estado") == "En Proceso":
            color, etiqueta = "#2563eb", "EN PROCESO"
        else:
            color, etiqueta = "#d97706", "PROGRAMADA"
        op_num    = str(op.get("op", "?")).replace('"', '').replace("'", "")
        cliente   = str(op.get("cliente", ""))[:14].replace('"', '').replace("'", "")
        titulo    = "OP " + op_num + " - " + cliente
        eventos_json.append({
            "id":              str(op["id"]),
            "resourceId":      op["maquina_cronograma"],
            "title":           titulo,
            "start":           str(op["fecha_inicio_cronograma"]),
            "end":             str(op["fecha_fin_cronograma"]),
            "backgroundColor": color,
            "borderColor":     color,
            "textColor":       "#ffffff",
            "extendedProps": {
                "cliente": cliente,
                "estado":  etiqueta,
                "db_id":   str(op["id"])
            }
        })

# Construye las tarjetas de OPs sin asignar que se muestran en la barra lateral, listas para arrastrar al calendario
    pendientes_json = []
    for op in ops_pendientes:
        card_color = "#2563eb" if op.get("estado") == "En Proceso" else "#d97706"
        op_num   = str(op.get("op", "?")).replace('"', '').replace("'", "")
        cliente  = str(op.get("cliente", ""))[:14].replace('"', '').replace("'", "")
        titulo   = "OP " + op_num + " - " + cliente
        pendientes_json.append({
            "id":    str(op["id"]),
            "title": titulo,
            "color": card_color,
            "extendedProps": {"cliente": cliente, "db_id": str(op["id"])}
        })

    recursos_json  = [{"id": m, "title": m} for m in lista_maquinas]
    eventos_str    = json.dumps(eventos_json,   ensure_ascii=True)
    recursos_str   = json.dumps(recursos_json,  ensure_ascii=True)
    pendientes_str = json.dumps(pendientes_json, ensure_ascii=True)
    supa_url = str(URL)
    supa_key = str(KEY)

# A partir de aqui se arma a mano el HTML/CSS/JS del calendario tipo Notion (libreria FullCalendar),
# que luego se incrusta en la pagina de Streamlit con components.html(). Aqui vive todo el "dibujo" del cronograma.
    html_cal = (
        "<!DOCTYPE html><html><head>"
        "<link href='https://cdn.jsdelivr.net/npm/fullcalendar-scheduler@6.1.11/index.global.min.css' rel='stylesheet'/>"
        "<script src='https://cdn.jsdelivr.net/npm/fullcalendar-scheduler@6.1.11/index.global.min.js'></script>"
        "<style>"
        # ESTILOS (CSS): tema oscuro para que el calendario combine con el resto de la aplicacion
        "* { box-sizing: border-box; margin: 0; padding: 0; }"
        "body { background: #191919; color: #e0e0e0; font-family: Segoe UI, sans-serif; display: flex; gap: 10px; padding: 10px; }"
        "#calendar-wrap { flex: 1; min-width: 0; }"
        "#sidebar { width: 185px; flex-shrink: 0; background: #1f1f1f; border: 1px solid #2e2e2e; border-radius: 10px; padding: 10px; display: flex; flex-direction: column; gap: 6px; overflow-y: auto; max-height: 560px; }"
        "#sidebar h3 { color: #aaa; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }"
        ".tarjeta { background: #2a2a2a; border: 1px solid #3a3a3a; border-radius: 8px; padding: 8px 10px; font-size: 12px; cursor: grab; color: #e0e0e0; transition: background 0.15s; margin-bottom: 4px; }"
        ".tarjeta:hover { background: #333; }"
        ".op-num { font-weight: 700; font-size: 12px; }"
        ".cli { color: #aaa; font-size: 11px; margin-top: 2px; }"
        ".est { font-size: 10px; color: #666; margin-top: 2px; }"
        ".no-pending { color: #555; font-size: 12px; text-align: center; margin-top: 20px; }"
        ".fc .fc-toolbar { background: #191919; padding: 8px 0; border-bottom: 1px solid #2e2e2e; }"
        ".fc .fc-toolbar-title { color: #e0e0e0; font-size: 15px; font-weight: 600; }"
        ".fc .fc-button { background: #2e2e2e !important; border: 1px solid #3e3e3e !important; color: #ccc !important; border-radius: 6px !important; font-size: 12px !important; padding: 4px 10px !important; }"
        ".fc .fc-button:hover { background: #3a3a3a !important; }"
        ".fc .fc-button-active { background: #444 !important; }"
        ".fc .fc-col-header-cell { background: #1f1f1f; border-color: #2e2e2e; }"
        ".fc .fc-col-header-cell-cushion { color: #aaa; font-size: 11px; text-decoration: none; padding: 5px; }"
        ".fc-datagrid-cell { background: #1f1f1f !important; border-color: #2a2a2a !important; }"
        ".fc .fc-datagrid-cell-cushion { color: #ccc; font-size: 12px; font-weight: 600; }"
        ".fc-timeline-slot { border-color: #2a2a2a !important; }"
        ".fc-timeline-lane { border-color: #2a2a2a !important; background: #191919; }"
        ".fc-event { border-radius: 6px !important; border: none !important; padding: 3px 7px !important; font-size: 12px !important; cursor: grab !important; }"
        ".fc .fc-timeline-now-indicator-line { border-color: #ef4444; }"
        "#toast { display: none; position: fixed; bottom: 18px; left: 50%; transform: translateX(-50%); background: #22c55e; color: #fff; padding: 8px 20px; border-radius: 20px; font-size: 13px; font-weight: 600; z-index: 9999; }"
        "#btn-guardar { display: none; position: fixed; bottom: 18px; right: 18px; background: #2563eb; color: #fff; border: none; border-radius: 10px; padding: 10px 20px; font-size: 13px; font-weight: 700; cursor: pointer; z-index: 9999; }"
        "#popup-quitar { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 10000; align-items: center; justify-content: center; }"
        "#tooltip { display: none; position: fixed; background: #2a2a2a; border: 1px solid #444; color: #eee; padding: 10px 14px; border-radius: 8px; font-size: 12px; z-index: 9998; pointer-events: none; max-width: 220px; line-height: 1.7; }"
        "</style></head><body>"
        "<div id='calendar-wrap'><div id='calendar'></div></div>"
        "<div id='sidebar'><h3>Sin asignar</h3><div id='lista-pendientes'></div></div>"
        "<div id='toast'></div>"
        "<button id='btn-guardar' onclick='ejecutarGuardado()'>Guardar cambios</button>"
        "<div id='popup-quitar'><div style='background:#2a2a2a;border:1px solid #444;border-radius:12px;padding:24px;max-width:300px;text-align:center;color:#eee;'>"
        "<div style='font-size:22px;margin-bottom:8px;'>🗑</div>"
        "<div style='font-weight:700;margin-bottom:6px;'>Quitar del cronograma?</div>"
        "<div id='popup-titulo' style='color:#d97706;font-size:13px;margin-bottom:16px;'></div>"
        "<div style='display:flex;gap:10px;justify-content:center;'>"
        "<button id='btn-cancelar-quitar' style='background:#3a3a3a;color:#ccc;border:1px solid #555;border-radius:8px;padding:8px 18px;cursor:pointer;'>Cancelar</button>"
        "<button id='btn-confirmar-quitar' style='background:#ef4444;color:#fff;border:none;border-radius:8px;padding:8px 18px;cursor:pointer;font-weight:700;'>Si, quitar</button>"
        "</div></div></div>"
        "<div id='tooltip'></div>"
        "<script>"
        # JAVASCRIPT: aqui vive toda la logica visual del calendario y el guardado automatico en Supabase
        # cada vez que se arrastra, redimensiona o quita una orden del cronograma
        "var eventos    = " + eventos_str + ";"
        "var recursos   = " + recursos_str + ";"
        "var pendientes = " + pendientes_str + ";"
        "var SUPA_URL   = '" + supa_url + "';"
        "var SUPA_KEY   = '" + supa_key + "';"
        "var tooltip    = document.getElementById('tooltip');"
        "var toast      = document.getElementById('toast');"
        "var cambiosPendientes = {};"
        "function showToast(msg) { toast.textContent = msg; toast.style.display = 'block'; setTimeout(function(){ toast.style.display = 'none'; }, 2500); }"
        "function actualizarBotonGuardar() { var n = Object.keys(cambiosPendientes).length; var btn = document.getElementById('btn-guardar'); if(n>0){ btn.style.display='block'; btn.textContent='Guardar cambios ('+n+')'; } else { btn.style.display='none'; } }"
        "function guardarEnSupabase(db_id, start, end, maquina) { cambiosPendientes[db_id] = {start:start, end:end, maquina:maquina}; actualizarBotonGuardar(); }"
        "async function ejecutarGuardado() { var ids = Object.keys(cambiosPendientes); var btn = document.getElementById('btn-guardar'); btn.textContent = 'Guardando...'; btn.disabled = true; var errores = 0; for(var i=0;i<ids.length;i++){ var id=ids[i]; var cam=cambiosPendientes[id]; try { var resp = await fetch(SUPA_URL+'/rest/v1/ordenes_planeadas?id=eq.'+encodeURIComponent(id), { method:'PATCH', headers:{'Content-Type':'application/json','apikey':SUPA_KEY,'Authorization':'Bearer '+SUPA_KEY,'Prefer':'return=minimal'}, body:JSON.stringify({fecha_inicio_cronograma:cam.start,fecha_fin_cronograma:cam.end,maquina_cronograma:cam.maquina}) }); if(resp.ok){ delete cambiosPendientes[id]; } else { errores++; } } catch(e){ errores++; } } btn.disabled=false; if(errores===0){ showToast('Todo guardado!'); btn.style.display='none'; } else { showToast('Error en '+errores+' cambios'); actualizarBotonGuardar(); } }"
        "async function quitarDelCronograma(db_id, ev) { showToast('Quitando...'); try { var resp = await fetch(SUPA_URL+'/rest/v1/ordenes_planeadas?id=eq.'+encodeURIComponent(db_id), { method:'PATCH', headers:{'Content-Type':'application/json','apikey':SUPA_KEY,'Authorization':'Bearer '+SUPA_KEY,'Prefer':'return=minimal'}, body:JSON.stringify({fecha_inicio_cronograma:null,fecha_fin_cronograma:null,maquina_cronograma:null}) }); if(resp.ok){ ev.remove(); showToast('OP devuelta a pendientes'); } else { showToast('Error al quitar'); } } catch(e){ showToast('Error de conexion'); } }"
        "async function excluirOP(event, db_id) { event.stopPropagation(); var resp = await fetch(SUPA_URL+'/rest/v1/ordenes_planeadas?id=eq.'+encodeURIComponent(db_id), { method:'PATCH', headers:{'Content-Type':'application/json','apikey':SUPA_KEY,'Authorization':'Bearer '+SUPA_KEY,'Prefer':'return=minimal'}, body:JSON.stringify({excluir_cronograma:true}) }); if(resp.ok){ var t=event.target.closest('.tarjeta'); if(t) t.remove(); showToast('OP retirada de pendientes'); } }"
        "document.addEventListener('mousemove', function(e){ tooltip.style.left=(e.clientX+15)+'px'; tooltip.style.top=(e.clientY+10)+'px'; });"
        "document.addEventListener('DOMContentLoaded', function(){"
        "  var lista = document.getElementById('lista-pendientes');"
        "  if(pendientes.length === 0){ lista.innerHTML = '<div class=\"no-pending\">Todas programadas</div>'; }"
        "  else { pendientes.forEach(function(p){"
        "    var div = document.createElement('div');"
        "    div.className = 'tarjeta';"
        "    var cc = p.color || '#d97706';"
        "    div.style.borderLeft = '3px solid '+cc;"
        "    div.setAttribute('data-event', JSON.stringify({id:p.id,title:p.title,duration:'02:00',backgroundColor:cc,borderColor:cc,textColor:'#fff',extendedProps:p.extendedProps}));"
        "    div.innerHTML = '<div style=\"display:flex;justify-content:space-between;align-items:center;\"><div class=\"op-num\" style=\"color:'+cc+'\">'+p.title.split(' - ')[0]+'</div><button onclick=\"excluirOP(event,\\''+p.id+'\\')\" style=\"background:none;border:none;color:#555;cursor:pointer;font-size:13px;\">x</button></div><div class=\"cli\">'+p.extendedProps.cliente+'</div><div class=\"est\">'+(cc==='#2563eb'?'En proceso':'Sin iniciar')+'</div>';"
        "    lista.appendChild(div);"
        "  }); }"
        "  var calEl = document.getElementById('calendar');"
        "  var cal = new FullCalendar.Calendar(calEl, {"
        "    schedulerLicenseKey: 'CC-Attribution-NonCommercial-NoDerivatives',"
        "    initialView: 'resourceTimelineDay',"
        "    locale: 'es',"
        "    height: 540,"
        "    nowIndicator: true,"
        "    editable: true,"
        "    droppable: true,"
        "    eventResizableFromStart: true,"
        "    slotDuration: '01:00:00',"
        "    slotLabelFormat: {hour:'2-digit',minute:'2-digit',hour12:false},"
        "    scrollTime: '06:00:00',"
        "    resourceAreaWidth: '13%',"
        "    resourceAreaHeaderContent: 'Maquina',"
        "    headerToolbar: {left:'prev,next today',center:'title',right:'resourceTimelineDay,resourceTimelineWeek,resourceTimelineMonth'},"
        "    buttonText: {today:'Hoy',day:'Dia',week:'Semana',month:'Mes'},"
        "    views: {"
        "      resourceTimelineDay: {slotDuration:'01:00:00',slotLabelFormat:{hour:'2-digit',minute:'2-digit',hour12:false}},"
        "      resourceTimelineWeek: {slotDuration:{days:1},slotLabelFormat:{weekday:'long',day:'2-digit',month:'short'}},"
        "      resourceTimelineMonth: {slotDuration:{days:7},slotLabelFormat:{day:'2-digit',month:'short'}}"
        "    },"
        "    resources: recursos,"
        "    events: eventos,"
        "    drop: function(info){ info.draggedEl.parentNode.removeChild(info.draggedEl); },"
        "    eventReceive: function(info){"
        "      var ev=info.event; var db_id=ev.extendedProps.db_id; var maq=ev.getResources()[0]?ev.getResources()[0].id:'';"
        "      var start=ev.start?ev.start.toISOString():''; var end=ev.end?ev.end.toISOString():'';"
        "      if(!end){ var tmp=new Date(ev.start); tmp.setHours(tmp.getHours()+2); end=tmp.toISOString(); }"
        "      guardarEnSupabase(db_id,start,end,maq);"
        "    },"
        "    eventChange: function(info){"
        "      var ev=info.event; var db_id=ev.extendedProps.db_id||ev.id; var maq=ev.getResources()[0]?ev.getResources()[0].id:'';"
        "      var start=ev.start?ev.start.toISOString():''; var end=ev.end?ev.end.toISOString():'';"
        "      guardarEnSupabase(db_id,start,end,maq);"
        "    },"
        "    eventClick: function(info){"
        "      var ev=info.event; var db_id=ev.extendedProps.db_id||ev.id;"
        "      var popup=document.getElementById('popup-quitar');"
        "      document.getElementById('popup-titulo').textContent=ev.title;"
        "      popup.style.display='flex';"
        "      document.getElementById('btn-confirmar-quitar').onclick=function(){ popup.style.display='none'; quitarDelCronograma(db_id,ev); };"
        "      document.getElementById('btn-cancelar-quitar').onclick=function(){ popup.style.display='none'; };"
        "    },"
        "    eventMouseEnter: function(info){"
        "      var p=info.event.extendedProps;"
        "      var s=info.event.start?info.event.start.toLocaleString('es-CO',{hour:'2-digit',minute:'2-digit',day:'2-digit',month:'short'}):'';"
        "      var e=info.event.end?info.event.end.toLocaleString('es-CO',{hour:'2-digit',minute:'2-digit',day:'2-digit',month:'short'}):'';"
        "      tooltip.innerHTML='<b style=\"color:#fff\">'+info.event.title+'</b><br>Cliente: '+p.cliente+'<br>Estado: '+p.estado+'<br>Inicio: '+s+'<br>Fin: '+e;"
        "      tooltip.style.display='block';"
        "    },"
        "    eventMouseLeave: function(){ tooltip.style.display='none'; }"
        "  });"
        "  cal.render();"
        "  new FullCalendar.ThirdPartyDraggable(document.getElementById('lista-pendientes'),{"
        "    itemSelector: '.tarjeta',"
        "    eventData: function(el){ return JSON.parse(el.getAttribute('data-event')); }"
        "  });"
        "});"
        "</script></body></html>"
    )

# Renderiza dentro de la pagina de Streamlit todo el HTML/CSS/JS armado arriba
    components.html(html_cal, height=620, scrolling=False)

# MODULO DE INVENTARIO CORES Y CAJAS
elif menu == "📦 Inventario":
    st.title("Gestión de Suministros (Cores y Cajas)")
    
    tab1, tab2 = st.tabs(["📥 Ingresar Stock", "📊 Ver Existencias"])
    
    with tab1:
        tipo_insumo = st.radio("¿Qué va a ingresar?", ["CORES", "CAJAS"], horizontal=True)
        tabla_db = "inventario_cores" if tipo_insumo == "CORES" else "inventario_cajas"
        col_nombre = "nombre_core" if tipo_insumo == "CORES" else "nombre_caja"
        
# TRAER DATOS DE LA TABLA SEGUN SELECCION 
        items_db = supabase.table(tabla_db).select("*").execute().data
        opciones = {item[col_nombre]: item['id'] for item in items_db}
        
        with st.form("entrada_suministros"):
            sel_item = st.selectbox(f"Seleccione {tipo_insumo[:-1]}", list(opciones.keys()))
            cant_n = st.number_input("Cantidad que ingresa (unidades)", min_value=1, step=1)
            
            if st.form_submit_button("Actualizar Stock Dentrada"):
                id_sel = opciones[sel_item]
                actual = next(i for i in items_db if i["id"] == id_sel)["stock_actual"]
                supabase.table(tabla_db).update({"stock_actual": actual + cant_n}).eq("id", id_sel).execute()
                st.success(f"Stock de {sel_item} actualizado a {actual + cant_n}")
                time.sleep(1)
                st.rerun()

        with st.form("salida_suministros"):
            sel_item = st.selectbox(f"Seleccione {tipo_insumo[:-1]}", list(opciones.keys()))
            cant_n = st.number_input("Cantidad que ingresa (unidades)", min_value=1, step=1)
            
            if st.form_submit_button("Actualizar Stock Salida"):
                id_sel = opciones[sel_item]
                actual = next(i for i in items_db if i["id"] == id_sel)["stock_actual"]
                supabase.table(tabla_db).update({"stock_actual": actual - cant_n}).eq("id", id_sel).execute()
                st.success(f"Stock de {sel_item} actualizado a {actual - cant_n}")
                time.sleep(1)
                st.rerun()

    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Cores")
            st.dataframe(formatear_fechas_df(pd.DataFrame(supabase.table("inventario_cores").select("*").execute().data)), use_container_width=True)
        with c2:
            st.subheader("Cajas")
            st.dataframe(formatear_fechas_df(pd.DataFrame(supabase.table("inventario_cajas").select("*").execute().data)), use_container_width=True)

#  VALIDACION DE ACCESO A AREAS DE PRODUCCION 
elif menu in ["🖨️ Impresión", "✂️ Corte", "📥 Colectoras", "📕 Encuadernación", "🌀 Rebobinadoras"]:
    rol_actual = st.session_state.get("rol", "operario").lower()

# DICCIONARIO DE PERMISOS UNIFICADO
    PERMISOS = {
        "admin": ["TODOS"],
        "ventas": ["TODOS"],
        "supervisor_imp": ["IMPRESIÓN", "COLECTORAS"],
        "supervisor_cor": ["CORTE"],
        "supervisor_reb": ["REBOBINADORAS"],
        "supervisor_enc": ["ENCUADERNACIÓN"]
    }
#

    area_act = menu.split(" ")[1].upper()
    
    permisos_del_usuario = PERMISOS.get(rol_actual, [])

    mi_maquina_asignada = None
    if rol_actual == "maquinista":
        mi_maquina_asignada = st.session_state.get("maquina_asignada")
        if MAQUINA_A_AREA.get(mi_maquina_asignada) != area_act:
            st.error("⛔ No tienes una máquina asignada en esta área. Contacta al administrador.")
            st.stop()
    elif "TODOS" not in permisos_del_usuario and area_act not in permisos_del_usuario:
        st.error(f"⛔ El rol '{rol_actual}' no tiene permiso para el área {area_act}")
        st.stop()

    st.markdown(f"<div class='title-area'>PANEL DE PRODUCCIÓN: {area_act}</div>", unsafe_allow_html=True)
    
    activos_data = supabase.table("trabajos_activos").select("*").eq("area", area_act).execute().data
    activos = {a['maquina']: a for a in activos_data}

# SI ES MAQUINISTA, SOLO VE SU MAQUINA. SI NO, VE TODAS LAS DEL AREA (supervisor/admin)
    maquinas_a_mostrar = [mi_maquina_asignada] if rol_actual == "maquinista" else MAQUINAS[area_act]

    cols = st.columns(3)
    for idx, m in enumerate(maquinas_a_mostrar):
        with cols[idx % 3]:
            if m in activos:
                tr = activos[m]

                st.markdown(f"<div class='card-produccion'>🟡 EN PROCESO<br>{m}<br>OP: {tr['op']}</div>", unsafe_allow_html=True)

 # LOGICA DE PARADAS TECNICAS 
                if not tr.get("pausado"):

# BOTON DE PARADA 
                    with st.popover("🚨 REGISTRAR PARADA"):
                        motivo_p = st.selectbox("Motivo de parada:", MOTIVOS_PARADA, key=f"mot_{m}")
                        if st.button("Confirmar Parada", key=f"btn_p_{m}", type="primary"):
                            supabase.table("trabajos_activos").update({
                                "pausado": True,
                                "inicio_pausa": hora_colombia().isoformat(),
                                "motivo_pausa": motivo_p 
                            }).eq("maquina", m).execute()
                            st.rerun()
                else:

# MOSTRAR PORQUE ESTA DETENIDA LA AMQUINA 
                    st.error(f"DETENIDA POR: {tr.get('motivo_pausa', 'Sin motivo')}")
                    if st.button(f"▶️ REANUDAR TRABAJO", key=f"r_{m}", type="secondary"):
                        try:
                            inicio_p = datetime.fromisoformat(tr["inicio_pausa"].replace("Z", "+00:00"))
                            ahora = hora_colombia()
                            pausa_segundos = (ahora - inicio_p).total_seconds()
            
# GUARDAR ENH LA TABLA DE TIEMPOS MUERTOS
                            registro_parada = {
                                "maquina": m,
                                "motivo": tr.get('motivo_pausa'),
                                "inicio": tr["inicio_pausa"],
                                "fin": ahora.isoformat(),
                                "duracion_segundos": pausa_segundos
                            }
                            try:
                                supabase.table("paradas_maquina").insert(registro_parada).execute()
                            except Exception:
                                try:
                                    registro_parada.pop("duracion_segundos", None)
                                    supabase.table("paradas_maquina").insert(registro_parada).execute()
                                except Exception:
                                    pass

# ACTUALIZAR EL REGISTRO DE ACTIVOS PARA IR TRABAJANO
                            nuevo_tiempo_acumulado = tr.get("tiempo_pausa", 0) + pausa_segundos
                            supabase.table("trabajos_activos").update({
                                "pausado": False,
                                "tiempo_pausa": nuevo_tiempo_acumulado,
                                "inicio_pausa": None,
                                "motivo_pausa": None
                            }).eq("maquina", m).execute()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

#  BOTON FINALIZAR SIEMPRE VERLO
                if st.button(f"✅ FINALIZAR TRABAJO", key=f"f_{m}"):
                    st.session_state.rep = tr
                    st.rerun()
            else:
                st.markdown(f"<div class='card-vacia'>⚪ DISPONIBLE<br>{m}</div>", unsafe_allow_html=True)
                ops_p = supabase.table("ordenes_planeadas").select("*").or_(f"proxima_area.eq.{area_act},estado_parcial.eq.ACTIVO EN {area_act}").execute().data
                if ops_p:
                    op_dict = {f"{o['op']} - {o['nombre_trabajo']}": o['op'] for o in ops_p}

                    sel_op_label = st.selectbox("Seleccionar OP", list(op_dict.keys()), key=f"s_{m}")
                    sel_op = op_dict[sel_op_label]
                    
                    if st.button(f"🚀 INICIAR {m}", key=f"str_{m}"):
                        ahora_iso = hora_colombia().isoformat()
    
# BUSCAR CUANDO TERMINO REALMENTE EL ULTIMO TRABAJO DE ESTA MAQUINA
                        fin_ultimo = obtener_ultima_actividad_maquina(m)
    
                        if fin_ultimo:
                            ocio_segundos = (hora_colombia() - fin_ultimo).total_seconds()
        
# GUARDA TIEMPO QUE ESTUVO LIBRE O SIN TRABAJO 
                            if ocio_segundos > 10: # Ignora solo dobles-clics/parpadeos, no huecos reales
                                registro_tiempo_libre = {
                                    "maquina": m,
                                    "motivo": "TIEMPO LIBRE (ENTRE OPs)",
                                    "inicio": fin_ultimo.isoformat(),
                                    "fin": ahora_iso,
                                    "duracion_segundos": ocio_segundos
                                }
                                try:
                                    supabase.table("tiempos_muertos").insert(registro_tiempo_libre).execute()
                                except Exception:

                                    try:
                                        registro_tiempo_libre.pop("duracion_segundos", None)
                                        supabase.table("tiempos_muertos").insert(registro_tiempo_libre).execute()
                                    except Exception:
                                        pass

# INICIAR TRABAJO NORMAL
                        registro_nuevo_trabajo = {
                            "maquina": m,
                            "area": area_act,
                            "op": sel_op,
                            "hora_inicio": ahora_iso,
                            "pausado": False,
                            "tiempo_pausa": 0,
                            "inicio_pausa": None,
                            "operario": st.session_state.get('nombre_usuario', 'Operario Planta')
                        }
                        try:
                            supabase.table("trabajos_activos").insert(registro_nuevo_trabajo).execute()
                        except Exception:
                            registro_nuevo_trabajo.pop("operario", None)
                            supabase.table("trabajos_activos").insert(registro_nuevo_trabajo).execute()
                        st.rerun()

    if st.session_state.rep and st.session_state.rep["area"] == area_act:
        r = st.session_state.rep
        st.divider()
        with st.form("cierre_tecnico_completo"):
            st.warning(f"### REGISTRO DE CIERRE: OP {r['op']}")

# SI ES MAQUINISTA, EL NOMBRE QUEDA AUTOMATICO CON SU PROPIO LOGIN (no se escribe a mano)
            if rol_actual == "maquinista":
                op_name = st.session_state.get('nombre_usuario', '')
                st.info(f"👤 Operario registrado automáticamente: **{op_name}**")
            else:
                op_name = st.text_input("Nombre del Operario *")
            auxiliar = st.text_input("Auxiliar")
            datos_c = {}
            
            if area_act == "IMPRESIÓN":
                c1, c2, c3 = st.columns(3)
                datos_c['marca_papel_i'] = c1.text_input("marca de papel",)
                datos_c['medida_papel'] = c2.number_input("medida de papel", 0)
                datos_c['metros_impresos'] = c3.number_input("Metros", 0)
                datos_c['imagenes_impresas'] = c1.number_input("n° imagenes ", 0)
                datos_c['desperdicio_kg'] = c2.number_input("Desperdicio Kg", 0)
                datos_c['planchas'] = c3.number_input("planchas gastadas", 0)

            elif area_act == "CORTE":
                c1, c2, c3 = st.columns(3)
                datos_c['tipo_papel'] = c1.text_input("Tipo de papel")
                datos_c['marca_papel_c'] = c2.text_input("Marca de papel")
                datos_c['ancho_bobina'] = c3.number_input("Ancho de bobina", 0)
                
                datos_c['imagenes_corte'] = c1.number_input("Imágenes/Bobina", 0)
                datos_c['gramos_bobinas'] = c2.number_input("Gramaje de bobina", 0)
                datos_c['rollos_finales'] = c3.number_input("Total Rollos cortados", 0)

                st.markdown("---")

# CNSUMO DE CAJAS Y CORES
                col_inv1, col_inv2 = st.columns(2)
                
                with col_inv1:
                    st.subheader("🌀 CONSUMO DE CORES")
                    cores_res = supabase.table("inventario_cores").select("id, nombre_core").execute().data
                    dict_cores = {c['nombre_core']: c['id'] for c in cores_res}
                    tubo_usado = st.selectbox("¿Qué TUBO/CORE utilizó?", ["Seleccione..."] + list(dict_cores.keys()))
                    if tubo_usado != "Seleccione...":
                        datos_c['id_tubo_inventario'] = dict_cores[tubo_usado]
                        datos_c['nombre_tubo'] = tubo_usado
                
                with col_inv2:
                    st.subheader("📦 CONSUMO DE CAJAS")
                    cajas_res = supabase.table("inventario_cajas").select("id, nombre_caja").execute().data
                    dict_cajas = {c['nombre_caja']: c['id'] for c in cajas_res}
                    caja_usada = st.selectbox("¿Qué CAJA utilizó?", ["Seleccione..."] + list(dict_cajas.keys()))
                    if caja_usada != "Seleccione...":
                        datos_c['id_caja_inventario'] = dict_cajas[caja_usada]
                        datos_c['nombre_caja'] = caja_usada

                st.markdown("---")

# CALCULOS AUTOMATICOS
                rollos = datos_c.get('rollos_finales', 0)
                imagenes = datos_c.get('imagenes_corte', 0)

                # Recuperar unidades_caja de la OP activa
                op_data_corte = supabase.table("ordenes_planeadas").select("unidades_caja").eq("op", r['op']).single().execute().data
                uds_caja_op = int(op_data_corte.get('unidades_caja', 0)) if op_data_corte else 0

                varillas_auto = int(rollos / imagenes) if imagenes > 0 else 0
                cajas_auto    = int(rollos / uds_caja_op) if uds_caja_op > 0 else 0

                datos_c['varillas_finales'] = varillas_auto
                datos_c['cajas_totales']    = cajas_auto

                col_r1, col_r2 = st.columns(2)
                col_r1.info(f"🔩 **Varillas calculadas:** {varillas_auto}  \n_(Rollos {rollos} ÷ Imágenes/Bobina {imagenes})_")
                col_r2.info(f"📦 **Cajas calculadas:** {cajas_auto}  \n_(Rollos {rollos} ÷ Uds/Caja OP: {uds_caja_op})_")

                f3 = st.columns(1)[0]
                datos_c['desperdicio'] = f3.number_input("Total desperdicio (Kg)", 0)

# COLECTORAS
            elif area_act == "COLECTORAS":
                c1, c2, c3 = st.columns(3) 
                datos_c['tipo_papel'] = c1.text_input("tipo de papel")
                datos_c['formas_colectadas'] = c2.number_input("total formas colectadas", 0)
                datos_c['partes'] = c3.number_input("total partes colectadas", 0)
                
                st.markdown("---")
                datos_c['destino_final'] = st.radio(
                    "¿Cuál es el siguiente paso?",
                    ["Enviar a Encuadernación", "Finalizar en Colectora"],
                    index=0
                )

# CONSUMO DE CAJAS EN COLECTORAS
                st.markdown("---")
                col_inv_col = st.columns(2)
                with col_inv_col[0]:
                    st.subheader("📦 CONSUMO DE CAJAS")
                    cajas_res = supabase.table("inventario_cajas").select("id, nombre_caja").execute().data
                    dict_cajas = {c['nombre_caja']: c['id'] for c in cajas_res}
                    caja_usada = st.selectbox("¿Qué CAJA utilizó?", ["Seleccione..."] + list(dict_cajas.keys()), key="inv_col")
                    if caja_usada != "Seleccione...":
                        datos_c['id_caja_inventario'] = dict_cajas[caja_usada]
                        datos_c['nombre_caja'] = caja_usada
                
                with col_inv_col[1]:
                    datos_c['cajas_totales'] = st.number_input("Total Cajas Empacadas", 0, key="cant_col")
                st.markdown("---")
                
                datos_c['formas_dañadas'] = c2.number_input("formas dañadas", 0)
                datos_c['tipo_pegado'] = c3.text_input("que tipo de pegue lleva")

            elif area_act == "ENCUADERNACIÓN":
                c1, c2, c3 = st.columns(3)
                datos_c['tipo_presentacion'] = c1.text_input("presentacion final")
                datos_c['unidades_caja'] = c2.number_input("cantidad por caja", 0)
                
#  CONSUMO DE CAJAS EN ENCUADERNACION
                st.markdown("---")
                col_inv_enc = st.columns(2)
                with col_inv_enc[0]:
                    st.subheader("📦 CONSUMO DE CAJAS")
                    cajas_res = supabase.table("inventario_cajas").select("id, nombre_caja").execute().data
                    dict_cajas = {c['nombre_caja']: c['id'] for c in cajas_res}
                    caja_usada = st.selectbox("¿Qué CAJA utilizó?", ["Seleccione..."] + list(dict_cajas.keys()), key="inv_enc")
                    if caja_usada != "Seleccione...":
                        datos_c['id_caja_inventario'] = dict_cajas[caja_usada]
                        datos_c['nombre_caja'] = caja_usada
                
                with col_inv_enc[1]:
                    datos_c['cajas_totales'] = st.number_input("Total Cajas Empacadas", 0, key="cant_enc")
                st.markdown("---")

                datos_c['tipo_pegado'] = c1.text_input("lugar de pegado")
                datos_c['desperdicio'] = c2.number_input("peso desperdicio", 0)
                datos_c['total_formas'] = c3.number_input("total formas procesadas", 0)

            elif area_act == "REBOBINADORAS":
                c1, c2, c3 = st.columns(3)
                datos_c['tipo_papel'] = c1.text_input("Tipo de papel")
                datos_c['ancho_entrada'] = c2.number_input("Gramaje", 0)
                datos_c['ancho_salida'] = c3.number_input("Ancho salida (si es un corte ponga las medidas)", 0)
                datos_c['metros_procesados'] = c1.number_input("Metros procesados", 0)
                datos_c['rollos_finales'] = c2.number_input("Rollos finales", 0)
                datos_c['empalmes'] = c3.number_input("Empalmes(defina un total o promedio)", 0)
                datos_c['desperdicio_kg'] = c1.number_input("Desperdicio Kg", 0)
                 
            obs_prod = st.text_area("Observaciones de producción / saldos ")

#  ENTREGA PARCIAL
            st.markdown("### 📦 ENTREGA PARCIAL (OPCIONAL)")
            cantidad_parcial = st.number_input("Cantidad parcial producida", 0)
            obs_parcial = st.text_input("Observación parcial")

            col_f1, col_f2 = st.columns(2)
            finalizar = col_f1.form_submit_button("🏁 FINALIZAR Y MOVER")
            parcial = col_f2.form_submit_button("📦 ENTREGA PARCIAL")

#  FINALIZAR TRABAJO ( LOGICA)
            if finalizar:

                if op_name:

                    inicio_raw = r['hora_inicio']

#  CONVERTIR A DATATIME (TODOS LOS MISMOS DATOS )
                    if isinstance(inicio_raw, str):
                        inicio = datetime.fromisoformat(inicio_raw.replace("Z", "+00:00"))
                    else:
                        inicio = inicio_raw

#  NORMALIZAR A ZONA HORARIA COLOMBIA
                    tz = pytz.timezone("America/Bogota")

                    if inicio.tzinfo is None:
                        inicio = tz.localize(inicio)
                    else:
                        inicio = inicio.astimezone(tz)

#  HORA ACTUAL CONSISTENTE
                    fin = hora_colombia()

#  CALCULAR DURACION
                    duracion = calcular_duracion_laboral(inicio, fin, r.get('maquina'), r.get('tiempo_pausa', 0))

#  LOGICA DE DESCUENTO DE INVENTARIO
                    if area_act == "CORTE" and 'id_tubo_inventario' in datos_c:
                        id_t = datos_c['id_tubo_inventario']
                        cant_gastar = datos_c.get('rollos_finales', 0)
                        if cant_gastar > 0:
                            stk = supabase.table("inventario_cores").select("stock_actual").eq("id", id_t).single().execute().data
                            if stk:
                                supabase.table("inventario_cores").update({"stock_actual": stk['stock_actual'] - cant_gastar}).eq("id", id_t).execute()
                                datos_c['info_inventario_tubo'] = f"Descontados {cant_gastar} tubos"

# DESCUENTO DE CAJAS GENERAL 
                    if 'id_caja_inventario' in datos_c:
                        id_cj = datos_c['id_caja_inventario']
                        cant_cj = datos_c.get('cajas_totales', 0)
                        if cant_cj > 0:
                            stk_cj = supabase.table("inventario_cajas").select("stock_actual").eq("id", id_cj).single().execute().data
                            if stk_cj:
                                nuevo_stock_caja = stk_cj['stock_actual'] - cant_cj
                                supabase.table("inventario_cajas").update({"stock_actual": nuevo_stock_caja}).eq("id", id_cj).execute()
                                datos_c['info_inventario_caja'] = f"Descontadas {cant_cj} de {datos_c.get('nombre_caja')}"

# DETENER OP  NO CUENTA TIEMPO DE LA OP PERO SI DE PARADA
                    d_op = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
                    tipo = d_op['tipo_orden']
                    n_area = "FINALIZADO"

#  RUTAS 
                    if tipo in ["FORMAS IMPRESAS", "FORMAS BLANCAS"]:
                        if area_act == "IMPRESIÓN":
                            if r['maquina'] in ["MTY-1", "MTY-2"]:

# LAS MAQUINAS MTY-1 Y MTY-2 NO PASAN POR COLECTORAS, VAN DIRECTO A ENCUADERNACIÓN
                                n_area = "ENCUADERNACIÓN"
                            else:
                                n_area = "COLECTORAS"
                        elif area_act == "COLECTORAS":
                            if datos_c.get('destino_final') == "Finalizar en Colectora":
                                n_area = "FINALIZADO"
                            else:
                                n_area = "ENCUADERNACIÓN"
                        elif area_act == "ENCUADERNACIÓN":
                            n_area = "FINALIZADO"

                    elif tipo == "ROLLOS IMPRESOS":
                        if area_act == "IMPRESIÓN":
                            n_area = "CORTE"
                        elif area_act == "CORTE":
                            n_area = "FINALIZADO"

                    elif tipo == "ROLLOS BLANCOS":
                        if area_act == "CORTE":
                            n_area = "FINALIZADO"

                    elif tipo == "REBOBINADO":
                        if area_act == "REBOBINADORAS":
                            n_area = "FINALIZADO"

                    hist = d_op.get('historial_procesos') or []
                    _, tiempo_area_prod = calcular_tiempo_en_area(d_op)
                    hist.append({
                        "area": area_act,
                        "maquina": r['maquina'],
                        "operario": op_name,
                        "auxiliar": auxiliar,
                        "fecha": fin.strftime("%d/%m/%Y %H:%M"),
                        "duracion": duracion,
                        "tiempo_total_area": tiempo_area_prod,
                        "tipo": "FINAL",
                        "datos_cierre": datos_c,
                        "observaciones": obs_prod
                    })

                    supabase.table("ordenes_planeadas").update({
                        "proxima_area": n_area,
                        "historial_procesos": hist,
                        "estado_parcial": None
                    }).eq("op", r['op']).execute()

                    supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()
                    st.session_state.rep = None
                    st.rerun()

#  ENTREGAS PARCIALES 
        if parcial:
            if cantidad_parcial <= 0:
                st.error("❌ Error: La cantidad parcial debe ser mayor a 0.")
                st.stop()
                
# Captura de tiempos
            inicio_raw = r['hora_inicio']
            if isinstance(inicio_raw, str):
                inicio = datetime.fromisoformat(inicio_raw.replace("Z", "+00:00"))
            else:
                inicio = inicio_raw
                
            tz = pytz.timezone("America/Bogota")
            if inicio.tzinfo is None:
                inicio = tz.localize(inicio)
            else:
                inicio = inicio.astimezone(tz)
                
            fin = hora_colombia()
            duracion = calcular_duracion_laboral(inicio, fin, r['maquina'], r.get('tiempo_pausa', 0))

# Preparar el nuevo historial — leer desde ordenes_planeadas, no desde trabajos_activos
            d_op_hist = supabase.table("ordenes_planeadas").select("*").eq("op", r['op']).single().execute().data
            hist = d_op_hist.get('historial_procesos') or [] if d_op_hist else []
            _, tiempo_area_parcial = calcular_tiempo_en_area(d_op_hist or {})
            
            datos_c['cantidad_parcial_entregada'] = cantidad_parcial
            if obs_parcial:
                datos_c['observacion_parcial'] = obs_parcial
                
# Recupera operario y auxiliar directamente del registro activo 'r'
            operario_actual = r.get('operario', 'Operario Planta')
            auxiliar_actual = r.get('auxiliar', '')
                
# Agrega al historial de forma segura
            hist.append({
                "area": area_act,
                "maquina": r['maquina'],
                "operario": operario_actual,
                "auxiliar": auxiliar_actual,
                "fecha": fin.strftime("%d/%m/%Y %H:%M"),
                "duracion": duracion,
                "tiempo_total_area": tiempo_area_parcial,
                "tipo": "PARCIAL",
                "datos_cierre": datos_c,
                "observaciones": obs_parcial if obs_parcial else f"Entrega parcial de {cantidad_parcial} unidades."
            })
            
#  CAMBIO CLAVE SIMULTANEO 
            d_op_p = supabase.table("ordenes_planeadas").select("tipo_orden").eq("op", r['op']).single().execute().data
            tipo_p = d_op_p['tipo_orden'] if d_op_p else ""

            n_area_parcial = "FINALIZADO"
            if tipo_p in ["FORMAS IMPRESAS", "FORMAS BLANCAS"]:
                if area_act == "IMPRESIÓN":
                    if r['maquina'] in ["MTY-1", "MTY-2"]:

# LAS MAQUINAS MTY-1 Y MTY-2 NO PASAN POR COLECTORAS, VAN DIRECTO A ENCUADERNACIÓN
                        n_area_parcial = "ENCUADERNACIÓN"
                    else:
                        n_area_parcial = "COLECTORAS"
                elif area_act == "COLECTORAS":
                    n_area_parcial = "ENCUADERNACIÓN"
            elif tipo_p == "ROLLOS IMPRESOS":
                if area_act == "IMPRESIÓN":
                    n_area_parcial = "CORTE"
                elif area_act == "CORTE":
                    n_area_parcial = "FINALIZADO"
            elif tipo_p == "ROLLOS BLANCOS":
                if area_act == "CORTE":
                    n_area_parcial = "FINALIZADO"
            elif tipo_p == "REBOBINADO":
                if area_act == "REBOBINADORAS":
                    n_area_parcial = "FINALIZADO"

            try:

# OP avanza a siguiente area Y queda visible en area origen
                supabase.table("ordenes_planeadas").update({
                    "proxima_area": n_area_parcial,
                    "estado_parcial": f"ACTIVO EN {area_act}",
                    "historial_procesos": hist
                }).eq("op", r['op']).execute()

# Maquina queda LIBRE
                supabase.table("trabajos_activos").delete().eq("maquina", r['maquina']).execute()

                st.success(f"✅ Parcial enviado a {n_area_parcial}. La máquina {r['maquina']} quedó libre y la OP sigue activa en {area_act}.")
                st.session_state.rep = None
                time.sleep(1.5)
                st.rerun()

            except Exception as e:
                st.error(f"Error al procesar la entrega parcial: {e}")

if st.session_state.get('rol') == 'admin':

# BLOQUE INTERRUPTORES DE MAQUINAS
    with st.expander("⚙️ INTERRUPTORES DE MÁQUINAS (ON/OFF)"):
        st.warning("Si apagas una máquina, el sistema no contará tiempos laborados para ella.")
        
        for area, lista_maquinas in MAQUINAS.items():
            st.subheader(f"Área: {area}")
            cols = st.columns(4) 
            for i, maq in enumerate(lista_maquinas):
                col_idx = i % 4
                with cols[col_idx]:
                    estado_actual = obtener_estado_maquina(maq)

# El interruptor (toggle)
                    nuevo_st = st.toggle(f"{maq}", value=estado_actual, key=f"switch_{maq}")
                    
                    if nuevo_st != estado_actual:
                        cambiar_estado_maquina(maq, nuevo_st)
                        st.toast(f"Máquina {maq} {'ACTIVADA' if nuevo_st else 'DESACTIVADA'}")
                        time.sleep(0.5) 
                        st.rerun() 

    st.divider()

#  BLOQUE ADMINISTRACION DE USUARIOS 
    with st.expander("➕ Panel de Administración de Usuarios"):
        st.info("Desde aquí se puede dar de alta nuevos operarios en la base de datos de Supabase.")
        
        c1, c2 = st.columns(2)
        with c1:
            nuevo_u = st.text_input("Usuario (Login)", key="admin_u")
            nuevo_p = st.text_input("Nueva Clave", type="password", key="admin_p")
        with c2:
            nuevo_n = st.text_input("Nombre Completo", key="admin_n")
            nuevo_r = st.selectbox("Rol", ["admin", "ventas", "aud_ventas", "supervisor_imp", "supervisor_cor", "supervisor_reb", "supervisor_enc",'diseño','diseño1','diseño2','diseño3', "patinador_roll", "almacen", "jefe_log", "patinador_log",'aux_log', "maquinista" ], key="admin_r")

# SI EL ROL ES MAQUINISTA, PEDIR A QUE MAQUINA ESPECIFICA QUEDA ASIGNADO
        nueva_maquina_asignada = None
        if nuevo_r == "maquinista":
            todas_las_maquinas = [m for lista in MAQUINAS.values() for m in lista]
            nueva_maquina_asignada = st.selectbox(
                "¿A qué máquina queda asignado este usuario?",
                todas_las_maquinas,
                key="admin_maquina"
            )
            st.caption(f"Este usuario solo podrá trabajar la máquina **{nueva_maquina_asignada}** "
                       f"(área {MAQUINA_A_AREA.get(nueva_maquina_asignada, '?')}).")

        if st.button("🚀 Crear Usuario en Sistema"):
            if nuevo_u and nuevo_p and nuevo_n:
                try:
                    supabase.table("usuarios").insert({
                        "usuario": nuevo_u,
                        "clave": _hashear_clave(nuevo_p),
                        "nombre": nuevo_n, 
                        "rol": nuevo_r,
                        "maquina_asignada": nueva_maquina_asignada
                    }).execute()
                    st.success(f"Usuario {nuevo_u} creado exitosamente.")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al insertar: {e}")
            else:
                st.warning("Por favor, completa todos los campos.")

#  FUNCIONES DE MERCADO DE AVATARES C&B  
def mercado_obtener_coins(usuario):
    """Retorna los coins actuales de un usuario."""
    try:
        res = supabase.table("monedas_usuarios").select("coins").eq("usuario", usuario).execute()
        if res.data:
            return res.data[0]['coins']
        
# Si no existe, crea registro con 0 coins
        supabase.table("monedas_usuarios").upsert({"usuario": usuario, "coins": 0}, on_conflict="usuario").execute()
        return 0
    except Exception as e:
        st.error(f"No se pudo consultar el saldo de coins: {e}")
        return 0

def mercado_ajustar_coins(usuario, cantidad, motivo, admin_who):
    """Suma o resta coins a un usuario y registra el movimiento."""
    try:
        coins_actuales = mercado_obtener_coins(usuario)
        nuevos_coins = max(0, coins_actuales + cantidad)
        supabase.table("monedas_usuarios").upsert({"usuario": usuario, "coins": nuevos_coins}, on_conflict="usuario").execute()
        # Registrar movimiento en historial
        supabase.table("monedas_historial").insert({
            "usuario": usuario,
            "cantidad": cantidad,
            "motivo": motivo,
            "admin": admin_who,
            "fecha": hora_colombia().isoformat()
        }).execute()
        return nuevos_coins
    except Exception as e:
        st.error(f"Error al ajustar coins: {e}")
        return None

# MODULO DE MENSAJES (chat interno entre usuarios y grupos de trabajo)
if menu == "💬 Mensajes":
    usuario_actual = st.session_state.get('usuario_actual', '')
    nombre_actual  = st.session_state.get('nombre_usuario', '')
    rol_actual_msg = st.session_state.get('rol', '')

    st.markdown("""
    <style>
    .burbuja-yo   {background:#2b5be7;color:white;border-radius:18px 18px 4px 18px;padding:10px 16px;margin:4px 0;max-width:75%;float:right;clear:both;font-size:15px;word-wrap:break-word;}
    .burbuja-otro {background:#2a2a2a;color:#f0f0f0;border-radius:18px 18px 18px 4px;padding:10px 16px;margin:4px 0;max-width:75%;float:left;clear:both;font-size:15px;word-wrap:break-word;}
    .hora-chat    {font-size:11px;color:#888;clear:both;margin-bottom:6px;}
    .hora-yo      {text-align:right;}
    .hora-otro    {text-align:left;}
    .nombre-otro  {font-size:12px;color:#aaa;margin-bottom:2px;clear:both;}
    .chat-area    {height:430px;overflow-y:auto;padding:12px 8px;border:1px solid #333;border-radius:8px;background:#111;margin-bottom:8px;}
    </style>""", unsafe_allow_html=True)

# ── CARGAR DATOS BASE ──────────────────────────────────────────────────────────
    try:
        todos_usuarios = supabase.table("usuarios").select("usuario,nombre,rol").execute().data or []
        mapa_nombre    = {u['usuario']: u['nombre'] for u in todos_usuarios}
        otros_usuarios = [u for u in todos_usuarios if u['usuario'] != usuario_actual]
    except Exception:
        todos_usuarios = []; mapa_nombre = {}; otros_usuarios = []

    try:
        mis_grupos = supabase.table("chat_grupos").select("*")\
            .ilike("miembros", f"%{usuario_actual}%").execute().data or []
    except Exception:
        mis_grupos = []

# ── CONSTRUIR LISTA DE CONVERSACIONES ─────────────────────────────────────────
    try:
        msgs_1a1 = supabase.table("mensajes_internos").select("*")\
            .or_(f"remitente.eq.{usuario_actual},destinatario.eq.{usuario_actual}")\
            .is_("grupo_id", "null").order("created_at", desc=True).execute().data or []
    except Exception:
        # compatibilidad: si grupo_id no existe aun, traer todos
        try:
            msgs_1a1 = supabase.table("mensajes_internos").select("*")\
                .or_(f"remitente.eq.{usuario_actual},destinatario.eq.{usuario_actual}")\
                .order("created_at", desc=True).execute().data or []
        except Exception:
            msgs_1a1 = []

    convs = {}  # {clave: {tipo, nombre, ultimo, hora, no_leidos}}
    for m in msgs_1a1:
        otro = m['destinatario'] if m['remitente'] == usuario_actual else m['remitente']
        if not otro or otro in ('TODOS', None):
            continue
        if otro not in convs:
            nl = sum(1 for x in msgs_1a1
                     if x.get('destinatario') == usuario_actual
                     and x.get('remitente') == otro
                     and not x.get('leido'))
            convs[otro] = {
                "tipo": "1a1",
                "nombre": mapa_nombre.get(otro, otro),
                "ultimo": m.get('cuerpo','')[:35],
                "hora": fmt_fecha_hora(m.get('created_at'), con_hora=False),
                "no_leidos": nl
            }
# OPTIMIZACION: antes se hacian 2 consultas a la base de datos POR CADA GRUPO
# (ultimo mensaje + contador de no leidos), asi que si el usuario estaba en 10
# grupos, cargar el modulo de Mensajes disparaba 20 consultas extra. Ahora se
# traen en UNA sola consulta todos los mensajes de todos los grupos del usuario,
# y el ultimo mensaje / contador de no leidos de cada grupo se calcula en Python.
    grupo_ids = [str(g['id']) for g in mis_grupos]
    msgs_por_grupo = {}
    if grupo_ids:
        try:
            msgs_grupos_todos = supabase.table("mensajes_internos")\
                .select("grupo_id,cuerpo,created_at,leido,remitente")\
                .in_("grupo_id", grupo_ids).order("created_at", desc=True).execute().data or []
            for m in msgs_grupos_todos:
                msgs_por_grupo.setdefault(str(m.get('grupo_id')), []).append(m)
        except Exception:
            msgs_por_grupo = {}

    for g in mis_grupos:
        gid = str(g['id'])
        msgs_g = msgs_por_grupo.get(gid, [])  # ya vienen ordenados desc por fecha
        ult_g = msgs_g[:1]
        nl_g = sum(1 for x in msgs_g if not x.get('leido') and x.get('remitente') != usuario_actual)
        convs[f"grupo_{gid}"] = {
            "tipo": "grupo", "gid": gid,
            "nombre": f"👥 {g['nombre']}",
            "ultimo": ult_g[0]['cuerpo'][:35] if ult_g else "Sin mensajes",
            "hora": fmt_fecha_hora(ult_g[0]['created_at'], con_hora=False) if ult_g else "",
            "no_leidos": nl_g
        }

# ── LAYOUT DOS COLUMNAS ────────────────────────────────────────────────────────
    col_lista, col_conv = st.columns([1, 3], gap="medium")

    with col_lista:
        st.markdown("### 💬 Chats")
        contacto_sel = st.session_state.get('chat_sel')

        if convs:
            for clave, info in sorted(convs.items(), key=lambda x: x[1].get('hora',''), reverse=True):
                badge   = f" 🔵{info['no_leidos']}" if info['no_leidos'] > 0 else ""
                activo  = "▶ " if contacto_sel == clave else ""
                preview = (info['ultimo'] or '')[:28]
                if st.button(f"{activo}**{info['nombre']}**{badge}\n_{preview}_",
                             key=f"conv_{clave}", use_container_width=True):
                    st.session_state['chat_sel'] = clave
                    st.rerun()
        else:
            st.caption("Sin conversaciones aún.")

        st.divider()

        # ── NUEVO CHAT 1 A 1 ──────────────────────────────────────────────────
        st.caption("Nuevo chat")
        ya_en_conv = {c for c in convs if not c.startswith("grupo_")}
        nuevos = {f"{u['nombre']} ({u['rol']})": u['usuario']
                  for u in otros_usuarios if u['usuario'] not in ya_en_conv}
        if nuevos:
            sel_nuevo = st.selectbox("", ["— elegir —"] + list(nuevos.keys()),
                                     key="nuevo_chat_sel", label_visibility="collapsed")
            if sel_nuevo != "— elegir —" and st.button("💬 Iniciar chat", use_container_width=True, key="btn_nc"):
                st.session_state['chat_sel'] = nuevos[sel_nuevo]
                st.rerun()

        # ── CREAR GRUPO ────────────────────────────────────────────────────────
        st.divider()
        st.caption("Nuevo grupo")
        with st.expander("👥 Crear grupo"):
            nom_g = st.text_input("Nombre del grupo:", key="nom_grp")
            miembros_g = st.multiselect(
                "Agregar miembros:",
                options=[u['usuario'] for u in otros_usuarios],
                format_func=lambda x: mapa_nombre.get(x, x),
                key="miembros_grp"
            )
            if st.button("Crear grupo", use_container_width=True, key="btn_crear_grp"):
                if nom_g.strip() and miembros_g:
                    todos_miembros = list(set(miembros_g + [usuario_actual]))
                    try:
                        res_g = supabase.table("chat_grupos").insert({
                            "nombre": nom_g.strip(),
                            "creado_por": usuario_actual,
                            "miembros": ",".join(todos_miembros)
                        }).execute()
                        nuevo_gid = str(res_g.data[0]['id'])
                        st.session_state['chat_sel'] = f"grupo_{nuevo_gid}"
                        st.success(f"Grupo '{nom_g}' creado.")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creando grupo: {e}")
                else:
                    st.warning("Pon un nombre y al menos un miembro.")

# COLUMNA DERECHA: muestra la conversacion seleccionada (chat individual o de grupo) y su historial de mensajes
    with col_conv:
        clave_activa = st.session_state.get('chat_sel')

        if not clave_activa:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.info("👈 Selecciona un chat o inicia uno nuevo.")

        else:
            es_grupo = str(clave_activa).startswith("grupo_")

            if es_grupo:
                gid_activo = clave_activa.replace("grupo_", "")
                info_grupo = next((g for g in mis_grupos if str(g['id']) == gid_activo), None)
                titulo_chat = f"👥 {info_grupo['nombre']}" if info_grupo else "Grupo"
                miembros_lista = (info_grupo['miembros'] or '').split(',') if info_grupo else []
                st.markdown(f"### {titulo_chat}")
                st.caption(f"Miembros: {', '.join(mapa_nombre.get(m,m) for m in miembros_lista if m)}")
                try:
                    conv = supabase.table("mensajes_internos").select("*")\
                        .eq("grupo_id", gid_activo).order("created_at").execute().data or []
                except Exception:
                    conv = []
            else:
                contacto_u = clave_activa
                titulo_chat = mapa_nombre.get(contacto_u, contacto_u)
                st.markdown(f"### 💬 {titulo_chat}")
                try:
                    conv = supabase.table("mensajes_internos").select("*")\
                        .or_(
                            f"and(remitente.eq.{usuario_actual},destinatario.eq.{contacto_u}),"
                            f"and(remitente.eq.{contacto_u},destinatario.eq.{usuario_actual})"
                        ).order("created_at").execute().data or []
                except Exception as e:
                    st.error(f"Error: {e}"); conv = []
                # Marcar leídos automáticamente
                ids_nl = [m['id'] for m in conv
                          if not m.get('leido') and m.get('remitente') == contacto_u]
                if ids_nl:
                    try:
                        for _id in ids_nl:
                            supabase.table("mensajes_internos").update({"leido": True}).eq("id", _id).execute()
                    except Exception:
                        pass

            # ── RENDERIZAR BURBUJAS ────────────────────────────────────────────
            html = '<div class="chat-area">'
            if not conv:
                html += '<div style="text-align:center;color:#666;padding:80px 0">Sin mensajes aún. ¡Escribe el primero!</div>'
            for m in conv:
                es_mio   = m['remitente'] == usuario_actual
                hora_txt = fmt_fecha_hora(m.get('created_at'))
                texto    = m.get('cuerpo','').replace('<','&lt;').replace('>','&gt;')
                if es_mio:
                    tick = " ✓✓" if m.get('leido') else " ✓"
                    html += f'<div class="burbuja-yo">{texto}</div><div class="hora-chat hora-yo">{hora_txt}{tick}</div>'
                else:
                    nombre_r = mapa_nombre.get(m['remitente'], m['remitente'])
                    prefijo  = f'<div class="nombre-otro">{nombre_r}</div>' if es_grupo else ''
                    html += f'{prefijo}<div class="burbuja-otro">{texto}</div><div class="hora-chat hora-otro">{hora_txt}</div>'
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)

            # ── CAJA ENVIAR ────────────────────────────────────────────────────
            with st.form(f"form_chat_{clave_activa}", clear_on_submit=True):
                cols_i = st.columns([5, 1])
                txt = cols_i[0].text_input("", placeholder="Escribe un mensaje...",
                                           label_visibility="collapsed", key=f"txt_{clave_activa}")
                enviar = cols_i[1].form_submit_button("Enviar ➤", use_container_width=True)
                if enviar and txt.strip():
                    nuevo = {
                        "remitente":        usuario_actual,
                        "remitente_nombre": nombre_actual,
                        "destinatario":     None if es_grupo else (clave_activa),
                        "destinatario_rol": None,
                        "asunto":           "chat",
                        "cuerpo":           txt.strip(),
                        "leido":            False
                    }
                    if es_grupo:
                        nuevo["grupo_id"] = gid_activo
                    try:
                        supabase.table("mensajes_internos").insert(nuevo).execute()
                    except Exception as e:
                        st.error(f"Error enviando: {e}")
                    st.rerun()



# MODULO MERCADO DE COINS (sistema de reconocimiento/puntos para los trabajadores)
if menu == "🛒 Mercado":
    usuario_actual = st.session_state.get('usuario_actual', '')
    nombre_actual  = st.session_state.get('nombre_usuario', '')
    rol_actual     = st.session_state.get('rol', '')

    st.markdown("<div class='title-area'>🪙 SISTEMA DE COINS — C&B PAPELES</div>", unsafe_allow_html=True)

    coins_usuario = mercado_obtener_coins(usuario_actual)

#  BARRA DE COINS 
    st.markdown(f"""
    <div style="background: linear-gradient(135deg,#1565C0,#0D47A1); border-radius:16px; 
                padding:18px 28px; display:flex; align-items:center; gap:16px; margin-bottom:20px;">
        <span style="font-size:2.5rem;">🪙</span>
        <div>
            <div style="color:#FFD700; font-size:1.8rem; font-weight:900; line-height:1;">{coins_usuario}</div>
            <div style="color:#90CAF9; font-size:0.9rem;">Coins disponibles — {nombre_actual}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# TABS PRINCIPALES
    if rol_actual == 'admin':
        tab_admin, tab_historial = st.tabs(
            ["⚙️ Panel Admin", "📜 Historial Monedas"]
        )
    else:
        tab_historial, = st.tabs(
            ["📜 Mi Historial"]
        )

# TAB  PANEL ADMIN
    if rol_actual == 'admin':
        with tab_admin:
            st.markdown("<div class='section-header'>⚙️ ADMINISTRACIÓN DEL MERCADO</div>", unsafe_allow_html=True)

# Asignar / quitar coins 
            with st.expander("🪙 Asignar o Quitar Coins a Trabajadores", expanded=True):
                st.info("Puedes dar coins como recompensa por buen desempeño, o descontarlos si es necesario.")
                
                try:
                    todos_usuarios = supabase.table("usuarios").select("usuario, nombre, rol").execute().data or []
                except Exception as e:
                    st.error(f"No se pudo cargar la lista de trabajadores: {e}")
                    todos_usuarios = []

                opciones_u = {f"{u['nombre']} ({u['usuario']}) — {u['rol']}": u['usuario'] for u in todos_usuarios}

                c1, c2, c3 = st.columns(3)
                with c1:
                    sel_u = st.selectbox("Seleccionar Trabajador", list(opciones_u.keys()), key="admin_sel_user")
                with c2:
                    cantidad_coins = st.number_input("Cantidad de Coins (+/-)", min_value=-9999, max_value=9999, value=10, step=5, key="admin_coins_amt")
                with c3:
                    motivo_coins = st.text_input("Motivo / Descripción", placeholder="Ej: Cumplimiento meta semana", key="admin_coins_mot")

                if sel_u:
                    u_key = opciones_u[sel_u]
                    coins_act = mercado_obtener_coins(u_key)
                    st.caption(f"Coins actuales de {sel_u.split('(')[0].strip()}: **{coins_act} 🪙**")

                if st.button("✅ Confirmar Asignación de Coins", use_container_width=True, key="btn_assign_coins"):
                    if not motivo_coins.strip():
                        st.warning("Por favor escribe un motivo antes de asignar coins.")
                    else:
                        u_key = opciones_u[sel_u]
                        nuevos = mercado_ajustar_coins(u_key, cantidad_coins, motivo_coins, st.session_state.get('usuario_actual'))
                        if nuevos is not None:
                            accion = "asignaron" if cantidad_coins > 0 else "descontaron"
                            st.success(f"✅ Se {accion} {abs(cantidad_coins)} coins a {sel_u.split('(')[0].strip()}. Saldo nuevo: {nuevos} 🪙")
                            time.sleep(1)
                            st.rerun()

#  Ver monederos de todos
            with st.expander("💰 Ver Coins de Todos los Trabajadores"):
                try:
                    monederos = supabase.table("monedas_usuarios").select("*").order("coins", desc=True).execute().data or []
                    if monederos:
                        df_coins = pd.DataFrame(monederos)
                        # Cruzar con nombres
                        nombres_map = {u['usuario']: u['nombre'] for u in todos_usuarios}
                        df_coins['nombre'] = df_coins['usuario'].map(nombres_map).fillna("Desconocido")
                        df_coins = df_coins[['nombre', 'usuario', 'coins']].rename(columns={
                            'nombre': 'Nombre', 'usuario': 'Usuario', 'coins': '🪙 Coins'
                        })
                        st.dataframe(df_coins, use_container_width=True, hide_index=True)
                    else:
                        st.info("Ningún trabajador tiene coins todavía.")
                except Exception as e:
                    st.error(f"Error: {e}")

# TAB  HISTORIAL (ADMIN ve todo, usuario ve lo suyo)
        with tab_historial:
            st.markdown("<div class='section-header'>📜 HISTORIAL DE MOVIMIENTOS DE COINS</div>", unsafe_allow_html=True)
            try:
                if rol_actual == 'admin':
                    hist_data = supabase.table("monedas_historial").select("*").order("fecha", desc=True).limit(200).execute().data or []
                else:
                    hist_data = supabase.table("monedas_historial").select("*").eq("usuario", usuario_actual).order("fecha", desc=True).limit(100).execute().data or []

                if hist_data:
                    df_hist = pd.DataFrame(hist_data)
                    df_hist = formatear_fechas_df(df_hist, columnas=['fecha'])
                    df_hist['Tipo'] = df_hist['cantidad'].apply(lambda x: "➕ Ingreso" if x > 0 else "➖ Gasto")
                    cols_show = ['fecha', 'usuario', 'cantidad', 'Tipo', 'motivo', 'admin'] if rol_actual == 'admin' else ['fecha', 'cantidad', 'Tipo', 'motivo']
                    col_names = {
                        'fecha': 'Fecha', 'usuario': 'Usuario', 'cantidad': '🪙 Coins',
                        'motivo': 'Descripción', 'admin': 'Asignado por'
                    }
                    df_show = df_hist[[c for c in cols_show if c in df_hist.columns]].rename(columns=col_names)
                    st.dataframe(df_show, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay movimientos registrados aún.")
            except Exception as e:
                st.error(f"Error al cargar historial: {e}")
    else:
        # Tab historial para no-admin
        with tab_historial:
            st.markdown("<div class='section-header'>📜 MI HISTORIAL DE COINS</div>", unsafe_allow_html=True)
            try:
                hist_data = supabase.table("monedas_historial").select("*").eq("usuario", usuario_actual).order("fecha", desc=True).limit(100).execute().data or []
                if hist_data:
                    df_hist = pd.DataFrame(hist_data)
                    df_hist = formatear_fechas_df(df_hist, columnas=['fecha'])
                    df_hist['Tipo'] = df_hist['cantidad'].apply(lambda x: "➕ Ingreso" if x > 0 else "➖ Gasto")
                    df_show = df_hist[['fecha', 'cantidad', 'Tipo', 'motivo']].rename(columns={
                        'fecha': 'Fecha', 'cantidad': '🪙 Coins', 'motivo': 'Descripción'
                    })
                    st.dataframe(df_show, use_container_width=True, hide_index=True)
                else:
                    st.info("Aún no tienes movimientos de coins.")
            except Exception as e:
                st.error(f"Error: {e}")
