from __future__ import annotations

import hashlib
from datetime import date, datetime
from io import BytesIO

import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from database import (
    crear_tablas,
    existe_numero_evidencia,
    guardar_evidencia,
    listar_eventos,
    listar_evidencias,
    obtener_evidencia,
)


APP_NAME = "FOR-TOOL-001"
APP_SUBTITLE = "GENERADOR DE CADENA DE CUSTODIA"
EMPTY_REGISTRY = "AUN NO SE GENERO NINGUN REGISTRO"


def aplicar_estilos() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                linear-gradient(rgba(0, 255, 136, 0.025) 1px, transparent 1px),
                linear-gradient(90deg, rgba(179, 136, 255, 0.025) 1px, transparent 1px),
                radial-gradient(circle at top left, rgba(0, 255, 136, 0.12), transparent 32rem),
                #050506;
            background-size: 28px 28px, 28px 28px, auto, auto;
            color: #caffdf;
            font-family: Consolas, "Courier New", monospace;
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        .block-container {
            max-width: 1120px;
            padding-top: 32px;
        }

        .forensia-header {
            border-top: 1px solid rgba(0, 255, 136, 0.42);
            border-bottom: 1px solid rgba(0, 255, 136, 0.42);
            padding: 22px 0 18px;
            margin-bottom: 22px;
        }

        .eyebrow,
        .header-status,
        .section-title {
            color: #00f083;
            font-weight: 700;
            letter-spacing: 2px;
            text-shadow: 0 0 10px rgba(0, 240, 131, 0.34);
        }

        .tool-id {
            color: #9b70ff;
            font-size: clamp(22px, 3vw, 34px);
            letter-spacing: 5px;
            text-shadow: 0 0 18px rgba(155, 112, 255, 0.72);
            margin: 8px 0 0;
        }

        .header-status {
            text-align: right;
            font-size: 14px;
            letter-spacing: 3px;
        }

        .section-title {
            margin: 22px 0 14px;
            font-size: 15px;
        }

        .status-box {
            display: inline-block;
            padding: 10px 14px;
            margin: 8px 0 16px;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 1.6px;
        }

        .status-pending {
            color: #9b70ff;
            border: 1px solid rgba(155, 112, 255, 0.5);
            background: rgba(155, 112, 255, 0.08);
        }

        .status-ok {
            color: #00f083;
            border: 1px solid rgba(0, 255, 136, 0.42);
            background: rgba(0, 255, 136, 0.12);
        }

        .status-alert {
            color: #ffbf5c;
            border: 1px solid rgba(255, 191, 92, 0.58);
            background: rgba(255, 191, 92, 0.08);
        }

        .terminal-box {
            padding: 18px;
            border: 1px solid rgba(0, 255, 136, 0.42);
            background: rgba(5, 5, 6, 0.88);
            color: #00f083;
            white-space: pre-wrap;
            font-family: Consolas, "Courier New", monospace;
            font-size: 13px;
            line-height: 1.5;
        }

        label,
        .stTextInput label,
        .stDateInput label,
        .stFileUploader label,
        .stTextArea label {
            color: #00f083 !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            letter-spacing: 1.6px !important;
            text-transform: uppercase;
        }

        .stTextInput input,
        .stDateInput input,
        .stTextArea textarea {
            color: #00f083 !important;
            background: #050506 !important;
            border: 1px solid rgba(0, 255, 136, 0.36) !important;
            border-radius: 0 !important;
            font-family: Consolas, "Courier New", monospace;
        }

        .stButton button,
        .stDownloadButton button {
            color: #00f083 !important;
            background: rgba(0, 240, 131, 0.08) !important;
            border: 1px solid #00f083 !important;
            border-radius: 0 !important;
            font-family: Consolas, "Courier New", monospace;
            font-weight: 700 !important;
            letter-spacing: 1.7px;
            text-transform: uppercase;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def calcular_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def estado_html(texto: str, tipo: str) -> None:
    clases = {
        "pendiente": "status-pending",
        "correcto": "status-ok",
        "alerta": "status-alert",
    }
    clase = clases.get(tipo, "status-alert")
    st.markdown(
        f'<div class="status-box {clase}">{texto}</div>',
        unsafe_allow_html=True,
    )


def campos_minimos_faltantes(
    evidencia: str,
    responsable: str,
    archivo: bytes | None,
) -> list[str]:
    faltantes = []
    if not evidencia.strip():
        faltantes.append("NUMERO DE EVIDENCIA")
    if not responsable.strip():
        faltantes.append("RESPONSABLE")
    if archivo is None:
        faltantes.append("ARCHIVO")
    return faltantes


def armar_registro(
    evidencia: str,
    responsable: str,
    ubicacion: str,
    estado_custodia: str,
    fecha_recepcion: date | None,
    descripcion: str,
    archivo_nombre: str,
    archivo_tipo: str,
    archivo_tamano: int,
    hash_sha256: str,
) -> str:
    fecha_registro = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    fecha_recepcion_txt = (
        fecha_recepcion.strftime("%d/%m/%Y") if fecha_recepcion else "Sin informar"
    )

    return "\n".join(
        [
            "[ DOSSIER DE EVIDENCIA ]",
            "",
            "FOR-TOOL-001",
            "ESTADO: VERIFICADO",
            "CLASIFICACION: EVIDENCIA DIGITAL",
            "ALGORITMO: SHA256",
            "",
            "[ IDENTIFICACION ]",
            f"EXPEDIENTE        : {evidencia or 'Sin informar'}",
            f"RESPONSABLE       : {responsable or 'Sin informar'}",
            f"UBICACION         : {ubicacion or 'Sin informar'}",
            f"ESTADO            : {estado_custodia or 'Sin informar'}",
            f"RECEPCION         : {fecha_recepcion_txt}",
            f"DESCRIPCION       : {descripcion or 'Sin informar'}",
            f"FECHA DE REGISTRO : {fecha_registro}",
            "",
            "[ EVIDENCIA DIGITAL ]",
            f"ARCHIVO           : {archivo_nombre}",
            f"TIPO              : {archivo_tipo or 'No informado'}",
            f"TAMANO            : {archivo_tamano} bytes",
            "",
            "[ INTEGRIDAD ]",
            f"SHA256            : {hash_sha256}",
        ]
    )


def armar_lineas_pdf(registro: str) -> list[str]:
    linea_doble = "=" * 72
    linea_simple = "-" * 72
    bloques = registro.split("\n\n")
    lineas = [
        linea_doble,
        "FORENSIA // FOR-TOOL-001",
        "GENERADOR DE CADENA DE CUSTODIA",
        linea_doble,
        "",
    ]

    for bloque in bloques:
        if bloque.startswith("["):
            titulo, *contenido = bloque.splitlines()
            lineas.extend([titulo, linea_simple, *contenido, "", linea_doble, ""])
        else:
            lineas.extend([bloque, "", linea_doble, ""])

    lineas.extend(["FIN DEL REGISTRO // CADENA DE CUSTODIA DIGITAL", linea_doble])
    return lineas


def generar_pdf(registro: str) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    x = 36
    y = height - 42
    line_height = 12

    pdf.setFont("Courier", 9)

    for linea in armar_lineas_pdf(registro):
        partes = [linea[i : i + 92] for i in range(0, len(linea), 92)] or [""]
        for parte in partes:
            if y < 42:
                pdf.showPage()
                pdf.setFont("Courier", 9)
                y = height - 42
            pdf.drawString(x, y, parte)
            y -= line_height

    pdf.save()
    return buffer.getvalue()


def limpiar_estado() -> None:
    for clave in [
        "evidencia",
        "responsable",
        "ubicacion",
        "estado_custodia",
        "descripcion",
        "hash_original",
    ]:
        st.session_state[clave] = ""

    st.session_state.fecha_recepcion = date.today()
    st.session_state.hash_sha256 = ""
    st.session_state.registro = EMPTY_REGISTRY
    st.session_state.archivo_nombre = ""
    st.session_state.archivo_tipo = ""
    st.session_state.archivo_tamano = 0
    st.session_state.estado_texto = "SIN VERIFICAR"
    st.session_state.estado_tipo = "pendiente"
    st.session_state.verificacion_texto = "SIN VERIFICAR"
    st.session_state.verificacion_tipo = "pendiente"
    st.session_state.registro_verificacion = "SIN VERIFICACIONES"
    st.session_state.ultima_evidencia_id = None
    st.session_state.uploader_version += 1


def inicializar_estado() -> None:
    defaults = {
        "evidencia": "",
        "responsable": "",
        "ubicacion": "",
        "estado_custodia": "",
        "descripcion": "",
        "hash_original": "",
        "hash_sha256": "",
        "registro": EMPTY_REGISTRY,
        "archivo_nombre": "",
        "archivo_tipo": "",
        "archivo_tamano": 0,
        "estado_texto": "SIN VERIFICAR",
        "estado_tipo": "pendiente",
        "verificacion_texto": "SIN VERIFICAR",
        "verificacion_tipo": "pendiente",
        "registro_verificacion": "SIN VERIFICACIONES",
        "ultima_evidencia_id": None,
        "uploader_version": 0,
    }

    for clave, valor in defaults.items():
        st.session_state.setdefault(clave, valor)

    st.session_state.setdefault("fecha_recepcion", date.today())


def guardar_evidencia_actual(
    *,
    evidencia: str,
    responsable: str,
    ubicacion: str,
    estado_custodia: str,
    fecha_recepcion: date | None,
    descripcion: str,
    archivo_nombre: str,
    archivo_tipo: str,
    archivo_tamano: int,
) -> int | None:
    if not st.session_state.hash_sha256 or st.session_state.registro == EMPTY_REGISTRY:
        st.session_state.estado_texto = "ALERTA: PRIMERO CALCULA EL HASH"
        st.session_state.estado_tipo = "alerta"
        return None

    if not evidencia.strip() or not responsable.strip():
        st.session_state.estado_texto = "ALERTA: FALTAN DATOS MINIMOS PARA GUARDAR"
        st.session_state.estado_tipo = "alerta"
        return None

    if existe_numero_evidencia(evidencia):
        st.session_state.estado_texto = f"ALERTA: LA EVIDENCIA {evidencia.strip()} YA EXISTE"
        st.session_state.estado_tipo = "alerta"
        return None

    evidencia_id = guardar_evidencia(
        numero_evidencia=evidencia.strip(),
        responsable=responsable.strip(),
        ubicacion=ubicacion.strip(),
        estado_custodia=estado_custodia.strip(),
        fecha_recepcion=fecha_recepcion.isoformat() if fecha_recepcion else "",
        descripcion=descripcion.strip(),
        archivo_nombre=archivo_nombre,
        archivo_tipo=archivo_tipo,
        archivo_tamano=archivo_tamano,
        hash_sha256=st.session_state.hash_sha256,
        registro=st.session_state.registro,
    )
    st.session_state.ultima_evidencia_id = evidencia_id
    st.session_state.estado_texto = f"EVIDENCIA GUARDADA EN SQLITE // ID {evidencia_id}"
    st.session_state.estado_tipo = "correcto"
    return evidencia_id


def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon="FORENSIA", layout="wide")
    crear_tablas()
    inicializar_estado()
    aplicar_estilos()

    st.markdown(
        f"""
        <div class="forensia-header">
            <div class="eyebrow">FORENSIA / HERRAMIENTA DIGITAL</div>
            <div class="tool-id">{APP_NAME}</div>
            <div class="header-status">{APP_SUBTITLE}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_datos, col_archivo = st.columns(2)

    with col_datos:
        st.markdown('<div class="section-title">&gt; CARGANDO DATOS DE EVIDENCIA</div>', unsafe_allow_html=True)
        evidencia = st.text_input("Numero de evidencia", key="evidencia", placeholder="EV-2026-001")
        responsable = st.text_input("Responsable", key="responsable", placeholder="Nombre y apellido")
        ubicacion = st.text_input("Ubicacion", key="ubicacion", placeholder="Area, deposito o laboratorio")
        estado_custodia = st.text_input("Estado", key="estado_custodia", placeholder="Recibido / En analisis / Archivado")
        fecha_recepcion = st.date_input("Fecha de recepcion", key="fecha_recepcion")
        descripcion = st.text_input("Descripcion", key="descripcion", placeholder="Dispositivo, soporte o archivo analizado")

    with col_archivo:
        st.markdown('<div class="section-title">&gt; GESTION DE ARCHIVOS</div>', unsafe_allow_html=True)
        archivo = st.file_uploader(
            "Archivo",
            key=f"archivo_{st.session_state.uploader_version}",
        )

        if st.button("Calcular hash", use_container_width=True):
            archivo_bytes = archivo.getvalue() if archivo else None
            faltantes = campos_minimos_faltantes(evidencia, responsable, archivo_bytes)

            if faltantes:
                st.session_state.estado_texto = "DATOS MINIMOS PENDIENTES: " + ", ".join(faltantes)
                st.session_state.estado_tipo = "alerta"

            if archivo_bytes is None:
                st.session_state.estado_texto = "ERROR: ARCHIVO NO SELECCIONADO"
                st.session_state.estado_tipo = "alerta"
            else:
                hash_sha256 = calcular_sha256(archivo_bytes)
                st.session_state.hash_sha256 = hash_sha256
                st.session_state.archivo_nombre = archivo.name
                st.session_state.archivo_tipo = archivo.type or "No informado"
                st.session_state.archivo_tamano = len(archivo_bytes)
                st.session_state.ultima_evidencia_id = None
                st.session_state.registro = armar_registro(
                    evidencia=evidencia,
                    responsable=responsable,
                    ubicacion=ubicacion,
                    estado_custodia=estado_custodia,
                    fecha_recepcion=fecha_recepcion,
                    descripcion=descripcion,
                    archivo_nombre=st.session_state.archivo_nombre,
                    archivo_tipo=st.session_state.archivo_tipo,
                    archivo_tamano=st.session_state.archivo_tamano,
                    hash_sha256=hash_sha256,
                )

                if faltantes:
                    st.session_state.estado_texto = "HASH CALCULADO CON DATOS MINIMOS PENDIENTES"
                    st.session_state.estado_tipo = "alerta"
                else:
                    st.session_state.estado_texto = "HASH CALCULADO CORRECTAMENTE"
                    st.session_state.estado_tipo = "correcto"

        st.text_input(
            "Resultado SHA256",
            value=st.session_state.hash_sha256,
            placeholder="Pendiente de calculo",
            disabled=True,
        )

        if st.session_state.hash_sha256:
            st.code(st.session_state.hash_sha256, language=None)

    st.markdown('<div class="section-title">&gt; ESTADO DE INTEGRIDAD</div>', unsafe_allow_html=True)
    estado_html(st.session_state.estado_texto, st.session_state.estado_tipo)

    st.markdown('<div class="section-title">&gt; REGISTRO DE EVIDENCIA</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="terminal-box">{st.session_state.registro}</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">&gt; VERIFICACION DE INTEGRIDAD</div>', unsafe_allow_html=True)
    hash_original = st.text_input("Hash original", key="hash_original")
    archivo_verificar = st.file_uploader(
        "Archivo a verificar",
        key=f"archivo_verificar_{st.session_state.uploader_version}",
    )

    if st.button("Verificar integridad", use_container_width=True):
        if not hash_original.strip():
            st.session_state.verificacion_texto = "ALERTA: HASH ORIGINAL PENDIENTE"
            st.session_state.verificacion_tipo = "alerta"
        elif archivo_verificar is None:
            st.session_state.verificacion_texto = "ALERTA: ARCHIVO A VERIFICAR PENDIENTE"
            st.session_state.verificacion_tipo = "alerta"
        else:
            hash_nuevo = calcular_sha256(archivo_verificar.getvalue())
            if hash_original.strip().lower() == hash_nuevo.lower():
                st.session_state.verificacion_texto = "INTEGRIDAD CONSERVADA"
                st.session_state.verificacion_tipo = "correcto"
                resultado = "INTEGRIDAD CONSERVADA"
            else:
                st.session_state.verificacion_texto = "ALERTA: ARCHIVO MODIFICADO"
                st.session_state.verificacion_tipo = "alerta"
                resultado = "ARCHIVO MODIFICADO"

            st.session_state.registro_verificacion = "\n".join(
                [
                    "[ VERIFICACION DE INTEGRIDAD ]",
                    f"HASH ESPERADO : {hash_original.strip()}",
                    f"HASH OBTENIDO : {hash_nuevo}",
                    f"RESULTADO     : {resultado}",
                ]
            )

    estado_html(st.session_state.verificacion_texto, st.session_state.verificacion_tipo)
    st.markdown(
        f'<div class="terminal-box">{st.session_state.registro_verificacion}</div>',
        unsafe_allow_html=True,
    )

    col_limpiar, col_guardar, col_pdf = st.columns(3)
    with col_limpiar:
        st.button("Limpiar formulario", use_container_width=True, on_click=limpiar_estado)

    with col_guardar:
        if st.button("Guardar evidencia", use_container_width=True):
            guardar_evidencia_actual(
                evidencia=evidencia,
                responsable=responsable,
                ubicacion=ubicacion,
                estado_custodia=estado_custodia,
                fecha_recepcion=fecha_recepcion,
                descripcion=descripcion,
                archivo_nombre=st.session_state.archivo_nombre,
                archivo_tipo=st.session_state.archivo_tipo,
                archivo_tamano=st.session_state.archivo_tamano,
            )

    with col_pdf:
        if st.session_state.hash_sha256 and st.session_state.registro != EMPTY_REGISTRY:
            st.download_button(
                "Exportar PDF",
                data=generar_pdf(st.session_state.registro),
                file_name="FORENSIA-Informe.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.button("Exportar PDF", use_container_width=True, disabled=True)

    st.markdown('<div class="section-title">&gt; HISTORIAL SQLITE</div>', unsafe_allow_html=True)
    evidencias_guardadas = listar_evidencias()

    if evidencias_guardadas:
        st.dataframe(
            evidencias_guardadas,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": "ID",
                "numero_evidencia": "EVIDENCIA",
                "responsable": "RESPONSABLE",
                "estado_custodia": "ESTADO",
                "archivo_nombre": "ARCHIVO",
                "hash_sha256": "SHA256",
                "creado_en": "REGISTRADO",
            },
        )

        opciones = {
            f"{item['id']} // {item['numero_evidencia']} // {item['archivo_nombre']}": item["id"]
            for item in evidencias_guardadas
        }
        seleccion = st.selectbox(
            "Seleccionar evidencia para ver detalle",
            options=list(opciones.keys()),
        )
        evidencia_detalle = obtener_evidencia(opciones[seleccion])

        if evidencia_detalle:
            st.markdown('<div class="section-title">&gt; DETALLE DE EVIDENCIA</div>', unsafe_allow_html=True)
            col_meta, col_hash = st.columns(2)

            with col_meta:
                st.markdown(
                    "\n".join(
                        [
                            '<div class="terminal-box">',
                            f"ID                : {evidencia_detalle['id']}",
                            f"EVIDENCIA         : {evidencia_detalle['numero_evidencia']}",
                            f"RESPONSABLE       : {evidencia_detalle['responsable']}",
                            f"UBICACION         : {evidencia_detalle['ubicacion'] or 'Sin informar'}",
                            f"ESTADO            : {evidencia_detalle['estado_custodia'] or 'Sin informar'}",
                            f"RECEPCION         : {evidencia_detalle['fecha_recepcion'] or 'Sin informar'}",
                            f"REGISTRADO        : {evidencia_detalle['creado_en']}",
                            "</div>",
                        ]
                    ),
                    unsafe_allow_html=True,
                )

            with col_hash:
                st.markdown(
                    "\n".join(
                        [
                            '<div class="terminal-box">',
                            f"ARCHIVO           : {evidencia_detalle['archivo_nombre']}",
                            f"TIPO              : {evidencia_detalle['archivo_tipo'] or 'No informado'}",
                            f"TAMANO            : {evidencia_detalle['archivo_tamano']} bytes",
                            f"SHA256            : {evidencia_detalle['hash_sha256']}",
                            "</div>",
                        ]
                    ),
                    unsafe_allow_html=True,
                )

            st.markdown(
                f'<div class="terminal-box">{evidencia_detalle["registro"]}</div>',
                unsafe_allow_html=True,
            )

            eventos = listar_eventos(evidencia_detalle["id"])
            if eventos:
                st.markdown('<div class="section-title">&gt; EVENTOS DE CUSTODIA</div>', unsafe_allow_html=True)
                st.dataframe(
                    eventos,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "tipo": "TIPO",
                        "detalle": "DETALLE",
                        "creado_en": "FECHA",
                    },
                )
    else:
        st.markdown(
            '<div class="terminal-box">SIN EVIDENCIAS GUARDADAS</div>',
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
