from __future__ import annotations

import base64
import hashlib
import json
import textwrap
from datetime import date, datetime
from html import escape
from io import BytesIO
from pathlib import Path

import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from database import (
    actualizar_rol_usuario,
    crear_tablas,
    existe_numero_evidencia,
    generar_respaldo,
    guardar_evidencia,
    guardar_movimiento_custodia,
    guardar_verificacion,
    hash_desde_manifiesto,
    listar_eventos,
    listar_evidencias,
    listar_movimientos_custodia,
    listar_usuarios,
    listar_verificaciones,
    obtener_evidencia,
    registrar_usuario,
    restaurar_respaldo,
    validar_respaldo,
    verificar_cadena_eventos,
)


APP_NAME = "FOR-TOOL-001"
APP_SUBTITLE = "GENERADOR DE CADENA DE CUSTODIA"
EMPTY_REGISTRY = "AUN NO SE GENERO NINGUN REGISTRO"
FAVICON_PATH = Path(__file__).with_name("assets") / "forensia-favicon-transparent.png"
BRAND_MARK_PATH = Path(__file__).with_name("assets") / "forensia-brand-mark.png"


def imagen_data_uri(path: Path) -> str:
    contenido = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{contenido}"


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

        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        #MainMenu {
            display: none !important;
        }

        .block-container {
            max-width: 1240px;
            padding-top: 24px;
            padding-bottom: 56px;
        }

        .forensia-header {
            display: grid;
            grid-template-columns: 92px minmax(0, 1fr) minmax(240px, auto);
            align-items: center;
            gap: 22px;
            font-family: Consolas, "Courier New", monospace;
            border-top: 1px solid rgba(0, 255, 136, 0.42);
            border-bottom: 1px solid rgba(0, 255, 136, 0.42);
            padding: 16px 20px;
            margin-bottom: 18px;
            background: linear-gradient(90deg, rgba(0, 240, 131, 0.08), transparent 42%), rgba(5, 5, 6, 0.72);
            box-shadow: 0 18px 50px rgba(0, 0, 0, 0.28);
        }

        .brand-mark {
            width: 82px;
            height: 82px;
            object-fit: contain;
            filter: drop-shadow(0 0 14px rgba(0, 240, 131, 0.28));
        }

        .brand-copy {
            min-width: 0;
        }

        .eyebrow,
        .header-status,
        .section-title {
            color: #00f083;
            font-weight: 700;
            letter-spacing: 2px;
            text-shadow: 0 0 10px rgba(0, 240, 131, 0.34);
        }

        .eyebrow {
            font-size: 14px;
            line-height: 1.4;
        }

        .tool-id {
            color: #9b70ff;
            font-family: Consolas, "Courier New", monospace;
            font-size: 36px;
            font-weight: 400;
            line-height: 1;
            letter-spacing: 5px;
            text-shadow: 0 0 18px rgba(155, 112, 255, 0.72);
            margin: 8px 0 0;
        }

        .header-status {
            text-align: right;
            font-size: 14px;
            letter-spacing: 3px;
            line-height: 1.55;
        }

        .header-status small {
            display: block;
            margin-top: 7px;
            color: #637a70;
            font-size: 10px;
            letter-spacing: 1.5px;
            text-shadow: none;
        }

        .section-title {
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 24px 0 14px;
            font-size: 15px;
        }

        .section-title::after {
            content: "";
            height: 1px;
            flex: 1;
            background: linear-gradient(90deg, rgba(0, 255, 136, 0.42), transparent);
        }

        [data-baseweb="tab-list"] {
            gap: 8px;
            border-bottom: 1px solid rgba(0, 255, 136, 0.28);
            margin-top: 12px;
        }

        [data-baseweb="tab"] {
            color: #8bb99e !important;
            background: transparent !important;
            font-family: Consolas, "Courier New", monospace;
            font-weight: 700;
            letter-spacing: 1.7px;
        }

        [data-baseweb="tab"]:hover {
            color: #9b70ff !important;
            background: rgba(155, 112, 255, 0.08) !important;
        }

        [data-baseweb="tab"][aria-selected="true"] {
            color: #00f083 !important;
            background: rgba(0, 240, 131, 0.08) !important;
            text-shadow: 0 0 10px rgba(0, 240, 131, 0.34);
        }

        [data-baseweb="tab-highlight"] {
            background-color: #00f083 !important;
            box-shadow: 0 0 10px rgba(0, 240, 131, 0.55);
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
            min-height: 72px;
            padding: 20px;
            border: 1px solid rgba(0, 255, 136, 0.42);
            background: linear-gradient(135deg, rgba(0, 240, 131, 0.055), transparent 34%), rgba(5, 5, 6, 0.9);
            color: #00f083;
            white-space: pre-wrap;
            font-family: Consolas, "Courier New", monospace;
            font-size: 13px;
            line-height: 1.5;
            box-shadow: inset 0 1px 0 rgba(0, 255, 136, 0.08);
        }

        .action-separator {
            height: 18px;
            margin: 4px 0 14px;
            border-bottom: 1px solid rgba(155, 112, 255, 0.22);
            background: linear-gradient(90deg, transparent, rgba(155, 112, 255, 0.05), transparent);
        }

        .auth-box {
            max-width: 560px;
            margin: 48px auto 18px;
            padding: 28px;
            border: 1px solid rgba(155, 112, 255, 0.58);
            background: rgba(155, 112, 255, 0.07);
            text-align: center;
        }

        .auth-title {
            color: #9b70ff;
            font-size: 18px;
            font-weight: 700;
            letter-spacing: 2px;
            text-shadow: 0 0 12px rgba(155, 112, 255, 0.55);
        }

        .auth-detail {
            color: #caffdf;
            margin-top: 12px;
            line-height: 1.6;
        }

        .user-session {
            color: #00f083;
            border: 1px solid rgba(0, 255, 136, 0.36);
            border-left: 3px solid #00f083;
            background: linear-gradient(90deg, rgba(0, 240, 131, 0.1), rgba(0, 240, 131, 0.025));
            padding: 13px 16px;
            font-size: 12px;
            letter-spacing: 1px;
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
            border-radius: 4px !important;
            font-family: Consolas, "Courier New", monospace;
            box-shadow: inset 0 0 18px rgba(0, 240, 131, 0.035);
        }

        .stTextInput input:focus,
        .stDateInput input:focus,
        .stTextArea textarea:focus {
            border-color: #00f083 !important;
            box-shadow: 0 0 0 2px rgba(0, 240, 131, 0.12) !important;
        }

        [data-baseweb="select"] > div,
        [data-testid="stFileUploaderDropzone"] {
            color: #caffdf !important;
            background: linear-gradient(135deg, rgba(16, 19, 26, 0.98), rgba(5, 5, 6, 0.98)) !important;
            border: 1px solid rgba(155, 112, 255, 0.3) !important;
            border-radius: 4px !important;
        }

        .stButton button,
        .stDownloadButton button {
            color: #00f083 !important;
            background: linear-gradient(180deg, rgba(0, 240, 131, 0.11), rgba(0, 240, 131, 0.045)) !important;
            border: 1px solid #00f083 !important;
            border-radius: 3px !important;
            font-family: Consolas, "Courier New", monospace;
            font-weight: 700 !important;
            letter-spacing: 1.7px;
            text-transform: uppercase;
            transition: transform 120ms ease, box-shadow 120ms ease, background 120ms ease;
        }

        .stButton button:hover,
        .stDownloadButton button:hover {
            transform: translateY(-1px);
            background: rgba(0, 240, 131, 0.15) !important;
            box-shadow: 0 0 18px rgba(0, 255, 136, 0.2);
        }

        [data-testid="stDataFrame"] {
            border: 1px solid rgba(155, 112, 255, 0.24);
            box-shadow: 0 14px 36px rgba(0, 0, 0, 0.22);
        }

        hr {
            border-color: rgba(0, 255, 136, 0.24) !important;
        }

        @media (max-width: 760px) {
            .forensia-header {
                grid-template-columns: 64px 1fr;
                gap: 14px;
                padding: 14px;
            }

            .brand-mark {
                width: 58px;
                height: 58px;
            }

            .header-status {
                grid-column: 1 / -1;
                text-align: left;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def calcular_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def autenticacion_configurada() -> bool:
    try:
        auth = st.secrets["auth"]
        microsoft = auth["microsoft"]
        valores = [
            auth["redirect_uri"],
            auth["cookie_secret"],
            microsoft["client_id"],
            microsoft["client_secret"],
            microsoft["server_metadata_url"],
        ]
    except Exception:
        # Streamlit usa una excepcion propia cuando secrets.toml aun no existe.
        return False

    return all(
        isinstance(valor, str)
        and valor.strip()
        and "REEMPLAZAR" not in valor.upper()
        for valor in valores
    )


def dato_usuario(*claves: str, defecto: str = "No informado") -> str:
    for clave in claves:
        valor = st.user.get(clave)
        if valor:
            return str(valor)
    return defecto


def enmascarar_correo(email: str) -> str:
    if "@" not in email:
        return "correo protegido"
    usuario, dominio = email.split("@", 1)
    visible = usuario[:2] if len(usuario) > 1 else usuario[:1]
    return f"{visible}***@{dominio}"


def exigir_inicio_sesion() -> dict[str, str]:
    if not autenticacion_configurada():
        st.markdown(
            """
            <div class="auth-box">
                <div class="auth-title">AUTENTICACION PENDIENTE</div>
                <div class="auth-detail">
                    Configura Microsoft Entra antes de acceder a las evidencias.
                    Consulta AUTENTICACION.md para completar el registro seguro.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.code(".streamlit/secrets.toml.example -> .streamlit/secrets.toml")
        st.stop()

    if not st.user.is_logged_in:
        st.markdown(
            """
            <div class="auth-box">
                <div class="auth-title">ACCESO RESTRINGIDO</div>
                <div class="auth-detail">
                    Identificate con tu cuenta de Microsoft para ingresar a FORENSIA.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Iniciar sesion con Microsoft", use_container_width=True):
            st.login("microsoft")
        st.stop()

    return {
        "nombre": dato_usuario("name", "preferred_username", "email"),
        "email": dato_usuario("email", "preferred_username"),
        "id": dato_usuario("sub", "oid"),
    }


def mostrar_sesion(usuario: dict[str, object]) -> None:
    col_usuario, col_salida = st.columns([4, 1])
    with col_usuario:
        nombre_seguro = escape(str(usuario["nombre"]))
        email_seguro = escape(enmascarar_correo(str(usuario["email"])))
        rol_seguro = escape(str(usuario["rol"]))
        st.markdown(
            (
                '<div class="user-session">SESION ACTIVA // '
                f"{nombre_seguro} // {email_seguro} // ROL {rol_seguro}</div>"
            ),
            unsafe_allow_html=True,
        )
    with col_salida:
        if st.button("Cerrar sesion", use_container_width=True):
            st.logout()


def crear_firma_hash(
    *,
    evidencia: str,
    responsable: str,
    ubicacion: str,
    estado_custodia: str,
    fecha_recepcion: date | None,
    descripcion: str,
    archivo_nombre: str,
    archivo_tipo: str,
    archivo_bytes: bytes,
) -> str:
    contexto = {
        "evidencia": evidencia.strip(),
        "responsable": responsable.strip(),
        "ubicacion": ubicacion.strip(),
        "estado_custodia": estado_custodia.strip(),
        "fecha_recepcion": fecha_recepcion.isoformat() if fecha_recepcion else "",
        "descripcion": descripcion.strip(),
        "archivo_nombre": archivo_nombre,
        "archivo_tipo": archivo_tipo,
        "archivo_tamano": len(archivo_bytes),
        "hash_sha256": calcular_sha256(archivo_bytes),
    }
    serializado = json.dumps(contexto, ensure_ascii=True, sort_keys=True)
    return calcular_sha256(serializado.encode("utf-8"))


def hash_esta_vigente(
    *,
    evidencia: str,
    responsable: str,
    ubicacion: str,
    estado_custodia: str,
    fecha_recepcion: date | None,
    descripcion: str,
    archivo_nombre: str,
    archivo_tipo: str,
    archivo_bytes: bytes | None,
) -> bool:
    if not st.session_state.hash_sha256 or not st.session_state.firma_hash:
        return False
    if archivo_bytes is None:
        return False
    firma_actual = crear_firma_hash(
        evidencia=evidencia,
        responsable=responsable,
        ubicacion=ubicacion,
        estado_custodia=estado_custodia,
        fecha_recepcion=fecha_recepcion,
        descripcion=descripcion,
        archivo_nombre=archivo_nombre,
        archivo_tipo=archivo_tipo,
        archivo_bytes=archivo_bytes,
    )
    return firma_actual == st.session_state.firma_hash


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


def armar_informe_forense(
    *,
    evidencia: dict[str, object],
    eventos: list[dict[str, object]],
    verificaciones: list[dict[str, object]],
    movimientos: list[dict[str, object]],
    auditoria: dict[str, object],
    exportado_por: str,
    generado_en: datetime | None = None,
) -> list[tuple[str, str]]:
    momento = generado_en or datetime.now()
    secciones: list[tuple[str, str]] = [
        ("titulo", "INFORME FORENSE DE CADENA DE CUSTODIA"),
        ("meta", f"Herramienta: {APP_NAME}"),
        ("meta", f"Generado: {momento.strftime('%d/%m/%Y %H:%M:%S')}"),
        ("meta", f"Exportado por: {exportado_por}"),
        ("seccion", "IDENTIFICACION DE LA EVIDENCIA"),
        ("texto", f"ID interno: {evidencia['id']}"),
        ("texto", f"Numero de evidencia: {evidencia['numero_evidencia']}"),
        ("texto", f"Responsable actual: {evidencia['responsable']}"),
        ("texto", f"Ubicacion actual: {evidencia.get('ubicacion') or 'Sin informar'}"),
        ("texto", f"Estado actual: {evidencia.get('estado_custodia') or 'Sin informar'}"),
        ("texto", f"Fecha de recepcion: {evidencia.get('fecha_recepcion') or 'Sin informar'}"),
        ("texto", f"Descripcion: {evidencia.get('descripcion') or 'Sin informar'}"),
        ("texto", f"Registrado: {evidencia['creado_en']}"),
        ("texto", f"Autor del registro: {evidencia['autor']}"),
        ("seccion", "EVIDENCIA DIGITAL E INTEGRIDAD"),
        ("texto", f"Archivo: {evidencia['archivo_nombre']}"),
        ("texto", f"Tipo: {evidencia.get('archivo_tipo') or 'No informado'}"),
        ("texto", f"Tamano: {evidencia.get('archivo_tamano') or 0} bytes"),
        ("hash", f"SHA-256: {evidencia['hash_sha256']}"),
        ("seccion", "AUDITORIA ENCADENADA"),
        (
            "correcto" if auditoria["integra"] else "alerta",
            "CADENA INTEGRA" if auditoria["integra"] else "CADENA ALTERADA O INCOMPLETA",
        ),
        ("texto", f"Eventos registrados: {auditoria['total_eventos']}"),
        ("hash", f"Hash final de cadena: {auditoria['ultimo_hash'] or 'Sin eventos'}"),
    ]

    for error in auditoria["errores"]:
        secciones.append(("alerta", f"Alerta: {error}"))

    secciones.append(("seccion", "EVENTOS DE AUDITORIA"))
    if eventos:
        for evento in eventos:
            secciones.extend(
                [
                    (
                        "subtitulo",
                        f"Evento {evento['id']} // {evento['tipo']} // {evento['creado_en']}",
                    ),
                    ("texto", f"Autor: {evento['autor']}"),
                    ("texto", f"Detalle: {evento['detalle']}"),
                    ("hash", f"Hash anterior: {evento['hash_anterior']}"),
                    ("hash", f"Hash del evento: {evento['hash_evento']}"),
                ]
            )
    else:
        secciones.append(("texto", "Sin eventos registrados."))

    secciones.append(("seccion", "VERIFICACIONES DE INTEGRIDAD"))
    if verificaciones:
        for indice, verificacion in enumerate(verificaciones, start=1):
            secciones.extend(
                [
                    (
                        "subtitulo",
                        f"Verificacion {indice} // {verificacion['creado_en']} // {verificacion['resultado']}",
                    ),
                    ("texto", f"Autor: {verificacion['autor']}"),
                    ("hash", f"Hash esperado: {verificacion['hash_esperado']}"),
                    ("hash", f"Hash obtenido: {verificacion['hash_obtenido']}"),
                ]
            )
    else:
        secciones.append(("texto", "Sin verificaciones registradas."))

    secciones.append(("seccion", "HISTORIAL DE CUSTODIA"))
    if movimientos:
        for indice, movimiento in enumerate(movimientos, start=1):
            secciones.extend(
                [
                    ("subtitulo", f"Movimiento {indice} // {movimiento['creado_en']}"),
                    ("texto", f"Autor: {movimiento['autor']}"),
                    (
                        "texto",
                        f"Responsable: {movimiento['responsable_anterior']} -> {movimiento['responsable_nuevo']}",
                    ),
                    (
                        "texto",
                        f"Ubicacion: {movimiento['ubicacion_anterior'] or 'Sin informar'} -> "
                        f"{movimiento['ubicacion_nueva'] or 'Sin informar'}",
                    ),
                    (
                        "texto",
                        f"Estado: {movimiento['estado_anterior'] or 'Sin informar'} -> "
                        f"{movimiento['estado_nuevo'] or 'Sin informar'}",
                    ),
                    ("texto", f"Motivo: {movimiento['motivo']}"),
                ]
            )
    else:
        secciones.append(("texto", "Sin movimientos de custodia registrados."))

    secciones.extend(
        [
            ("seccion", "CIERRE DEL INFORME"),
            (
                "texto",
                "Este documento resume los registros almacenados por FORENSIA. "
                "La validez de la evidencia digital depende de conservar el archivo original, "
                "la base de datos y sus respaldos verificables.",
            ),
        ]
    )
    return secciones


def generar_pdf_forense(
    *,
    evidencia: dict[str, object],
    eventos: list[dict[str, object]],
    verificaciones: list[dict[str, object]],
    movimientos: list[dict[str, object]],
    auditoria: dict[str, object],
    exportado_por: str,
) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    ancho, alto = A4
    margen_x = 42
    margen_inferior = 48
    numero_pagina = 0
    y = 0.0

    def nueva_pagina() -> None:
        nonlocal numero_pagina, y
        if numero_pagina:
            pdf.showPage()
        numero_pagina += 1
        pdf.setFillColorRGB(0.0, 0.45, 0.25)
        pdf.rect(0, alto - 54, ancho, 54, fill=1, stroke=0)
        if BRAND_MARK_PATH.exists():
            pdf.drawImage(
                str(BRAND_MARK_PATH),
                margen_x,
                alto - 48,
                width=34,
                height=34,
                preserveAspectRatio=True,
                mask="auto",
            )
        pdf.setFillColorRGB(0.85, 1.0, 0.91)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(margen_x + 44, alto - 32, "FORENSIA // FOR-TOOL-001")
        pdf.setFont("Helvetica", 8)
        pdf.drawRightString(ancho - margen_x, alto - 32, "CADENA DE CUSTODIA DIGITAL")
        pdf.setFillColorRGB(0.25, 0.25, 0.3)
        pdf.drawString(margen_x, 24, f"Informe generado por {APP_NAME}")
        pdf.drawRightString(ancho - margen_x, 24, f"Pagina {numero_pagina}")
        y = alto - 78

    nueva_pagina()
    estilos = {
        "titulo": ("Helvetica-Bold", 16, (0.36, 0.17, 0.72), 24, 58),
        "seccion": ("Helvetica-Bold", 11, (0.0, 0.42, 0.23), 18, 72),
        "subtitulo": ("Helvetica-Bold", 9, (0.18, 0.18, 0.22), 15, 84),
        "meta": ("Helvetica", 8, (0.35, 0.35, 0.4), 12, 94),
        "texto": ("Helvetica", 8.5, (0.12, 0.12, 0.15), 12, 94),
        "hash": ("Courier", 7.3, (0.08, 0.26, 0.16), 10, 76),
        "correcto": ("Helvetica-Bold", 10, (0.0, 0.48, 0.25), 16, 84),
        "alerta": ("Helvetica-Bold", 10, (0.75, 0.12, 0.16), 16, 84),
    }

    for tipo, texto in armar_informe_forense(
        evidencia=evidencia,
        eventos=eventos,
        verificaciones=verificaciones,
        movimientos=movimientos,
        auditoria=auditoria,
        exportado_por=exportado_por,
    ):
        fuente, tamano, color, salto, ancho_linea = estilos[tipo]
        lineas = textwrap.wrap(
            str(texto),
            width=ancho_linea,
            replace_whitespace=False,
            break_long_words=True,
            break_on_hyphens=False,
        ) or [""]
        espacio_necesario = salto + (len(lineas) - 1) * (tamano + 3)
        if y - espacio_necesario < margen_inferior:
            nueva_pagina()
        pdf.setFont(fuente, tamano)
        pdf.setFillColorRGB(*color)
        for linea in lineas:
            pdf.drawString(margen_x, y, linea)
            y -= tamano + 3
        y -= max(3, salto - len(lineas) * (tamano + 3))

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
    st.session_state.firma_hash = ""
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
        "firma_hash": "",
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
    hash_vigente: bool,
    autor_usuario_id: int,
) -> int | None:
    if not st.session_state.hash_sha256 or st.session_state.registro == EMPTY_REGISTRY:
        st.session_state.estado_texto = "ALERTA: PRIMERO CALCULA EL HASH"
        st.session_state.estado_tipo = "alerta"
        return None

    if not hash_vigente:
        st.session_state.estado_texto = "ALERTA: DATOS O ARCHIVO CAMBIARON; RECALCULA EL HASH"
        st.session_state.estado_tipo = "alerta"
        return None

    if not evidencia.strip() or not responsable.strip():
        st.session_state.estado_texto = "ALERTA: FALTAN DATOS MINIMOS PARA GUARDAR"
        st.session_state.estado_tipo = "alerta"
        return None

    if fecha_recepcion and fecha_recepcion > date.today():
        st.session_state.estado_texto = "ALERTA: LA FECHA DE RECEPCION NO PUEDE SER FUTURA"
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
        autor_usuario_id=autor_usuario_id,
    )
    st.session_state.ultima_evidencia_id = evidencia_id
    st.session_state.estado_texto = f"EVIDENCIA GUARDADA EN SQLITE // ID {evidencia_id}"
    st.session_state.estado_tipo = "correcto"
    return evidencia_id


def mostrar_administracion_usuarios() -> None:
    st.markdown(
        '<div class="section-title">&gt; ADMINISTRACION DE USUARIOS</div>',
        unsafe_allow_html=True,
    )
    usuarios = listar_usuarios()
    st.dataframe(
        [
            {
                **item,
                "email": enmascarar_correo(item["email"]),
            }
            for item in usuarios
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": "ID",
            "nombre": "USUARIO",
            "email": "CORREO",
            "rol": "ROL",
            "creado_en": "CREADO",
            "ultimo_acceso": "ULTIMO ACCESO",
        },
    )
    opciones_usuario = {
        f"{item['nombre']} // {enmascarar_correo(item['email'])}": item
        for item in usuarios
    }
    with st.form("administrar_rol"):
        seleccion_usuario = st.selectbox(
            "Usuario",
            options=list(opciones_usuario.keys()),
        )
        usuario_seleccionado = opciones_usuario[seleccion_usuario]
        roles = ["ADMIN", "PERITO", "CONSULTA"]
        rol_nuevo = st.selectbox(
            "Rol",
            options=roles,
            index=roles.index(usuario_seleccionado["rol"]),
        )
        guardar_rol = st.form_submit_button(
            "Actualizar rol",
            use_container_width=True,
        )
    if guardar_rol:
        try:
            actualizar_rol_usuario(usuario_seleccionado["id"], rol_nuevo)
        except ValueError as error:
            st.error(str(error))
        else:
            st.success("Rol actualizado.")
            st.rerun()


def mostrar_respaldos(usuario: dict[str, object]) -> None:
    st.markdown(
        '<div class="section-title">&gt; RESPALDO Y RESTAURACION</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Solo administradores. El respaldo incluye evidencias, verificaciones, "
        "custodia y usuarios. Guarda juntos el archivo SQLite y su manifiesto."
    )

    if st.button("Preparar respaldo verificable", use_container_width=True):
        st.session_state.respaldo_preparado = generar_respaldo(
            creado_por=str(usuario["nombre"]),
        )

    respaldo = st.session_state.get("respaldo_preparado")
    if respaldo:
        metadatos = respaldo["metadatos"]
        st.success(
            "RESPALDO VERIFICADO // "
            f"{metadatos['tamano']} BYTES // SHA-256 {metadatos['hash_sha256']}"
        )
        fecha_archivo = datetime.now().strftime("%Y%m%d-%H%M%S")
        col_base, col_manifiesto = st.columns(2)
        with col_base:
            st.download_button(
                "Descargar base SQLite",
                data=respaldo["contenido"],
                file_name=f"FORENSIA-respaldo-{fecha_archivo}.db",
                mime="application/vnd.sqlite3",
                use_container_width=True,
            )
        with col_manifiesto:
            st.download_button(
                "Descargar manifiesto SHA-256",
                data=respaldo["manifiesto"],
                file_name=f"FORENSIA-respaldo-{fecha_archivo}.json",
                mime="application/json",
                use_container_width=True,
            )

    st.markdown(
        '<div class="section-title">&gt; RESTAURAR RESPALDO</div>',
        unsafe_allow_html=True,
    )
    st.warning(
        "La restauracion reemplaza los datos actuales. Antes de hacerlo, "
        "FORENSIA conserva automaticamente una copia de la base vigente."
    )
    archivo_respaldo = st.file_uploader(
        "Base SQLite de respaldo",
        type=["db", "sqlite", "sqlite3"],
        key="restaurar_base_sqlite",
    )
    archivo_manifiesto = st.file_uploader(
        "Manifiesto JSON del respaldo",
        type=["json"],
        key="restaurar_manifiesto",
    )

    validacion = None
    hash_esperado = ""
    if archivo_respaldo is not None and archivo_manifiesto is not None:
        try:
            hash_esperado = hash_desde_manifiesto(archivo_manifiesto.getvalue())
            validacion = validar_respaldo(
                archivo_respaldo.getvalue(),
                hash_esperado=hash_esperado,
            )
        except ValueError as error:
            st.error(str(error))
        else:
            conteos = validacion["conteos"]
            st.success(
                "RESPALDO APTO PARA RESTAURAR // "
                f"EVIDENCIAS {conteos['evidencias']} // "
                f"VERIFICACIONES {conteos['verificaciones']} // "
                f"EVENTOS {conteos['eventos']}"
            )

    confirmar = st.checkbox(
        "Confirmo que deseo reemplazar la base actual por este respaldo.",
        disabled=validacion is None,
    )
    if st.button(
        "Restaurar base verificada",
        use_container_width=True,
        disabled=validacion is None or not confirmar,
    ):
        try:
            resultado = restaurar_respaldo(
                archivo_respaldo.getvalue(),
                hash_esperado=hash_esperado,
            )
        except (OSError, ValueError) as error:
            st.error(f"No se pudo restaurar el respaldo: {error}")
        else:
            st.session_state.pop("respaldo_preparado", None)
            st.success(
                "RESTAURACION COMPLETADA // "
                f"SHA-256 {resultado['hash_sha256']}"
            )
            st.rerun()


def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon=str(FAVICON_PATH), layout="wide")
    aplicar_estilos()
    marca_uri = imagen_data_uri(BRAND_MARK_PATH)

    st.markdown(
        f"""
        <div class="forensia-header">
            <img class="brand-mark" src="{marca_uri}" alt="Identidad visual de FORENSIA">
            <div class="brand-copy">
                <div class="eyebrow">FORENSIA / HERRAMIENTA DIGITAL</div>
                <div class="tool-id">{APP_NAME}</div>
            </div>
            <div class="header-status">
                {APP_SUBTITLE}
                <small>INTEGRIDAD DIGITAL // SHA-256 // CUSTODIA TRAZABLE</small>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    identidad = exigir_inicio_sesion()
    crear_tablas()
    usuario = registrar_usuario(
        proveedor_id=identidad["id"],
        nombre=identidad["nombre"],
        email=identidad["email"],
    )
    mostrar_sesion(usuario)
    inicializar_estado()

    puede_operar = usuario["rol"] in {"ADMIN", "PERITO"}
    es_admin = usuario["rol"] == "ADMIN"
    if not puede_operar:
        st.info("ROL CONSULTA: acceso de solo lectura y descarga.")

    tab_registrar, tab_verificar, tab_historial = st.tabs(
        ["REGISTRAR", "VERIFICAR", "HISTORIAL"]
    )

    with tab_registrar:
        col_datos, col_archivo = st.columns(2)

        with col_datos:
            st.markdown('<div class="section-title">&gt; CARGANDO DATOS DE EVIDENCIA</div>', unsafe_allow_html=True)
            evidencia = st.text_input("Numero de evidencia", key="evidencia", placeholder="EV-2026-001")
            responsable = st.text_input("Responsable", key="responsable", placeholder="Nombre y apellido")
            ubicacion = st.text_input("Ubicacion", key="ubicacion", placeholder="Area, deposito o laboratorio")
            estado_custodia = st.text_input("Estado", key="estado_custodia", placeholder="Recibido / En analisis / Archivado")
            fecha_recepcion = st.date_input(
                "Fecha de recepcion",
                key="fecha_recepcion",
                max_value=date.today(),
            )
            descripcion = st.text_input("Descripcion", key="descripcion", placeholder="Dispositivo, soporte o archivo analizado")

        with col_archivo:
            st.markdown('<div class="section-title">&gt; GESTION DE ARCHIVOS</div>', unsafe_allow_html=True)
            archivo = st.file_uploader(
                "Archivo",
                key=f"archivo_{st.session_state.uploader_version}",
            )

            if st.button(
                "Calcular hash",
                use_container_width=True,
                disabled=not puede_operar,
            ):
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
                    st.session_state.firma_hash = crear_firma_hash(
                        evidencia=evidencia,
                        responsable=responsable,
                        ubicacion=ubicacion,
                        estado_custodia=estado_custodia,
                        fecha_recepcion=fecha_recepcion,
                        descripcion=descripcion,
                        archivo_nombre=archivo.name,
                        archivo_tipo=archivo.type or "No informado",
                        archivo_bytes=archivo_bytes,
                    )
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

        archivo_actual_bytes = archivo.getvalue() if archivo else None
        hash_vigente = hash_esta_vigente(
            evidencia=evidencia,
            responsable=responsable,
            ubicacion=ubicacion,
            estado_custodia=estado_custodia,
            fecha_recepcion=fecha_recepcion,
            descripcion=descripcion,
            archivo_nombre=archivo.name if archivo else "",
            archivo_tipo=(archivo.type or "No informado") if archivo else "",
            archivo_bytes=archivo_actual_bytes,
        )
        if st.session_state.hash_sha256 and not hash_vigente:
            st.session_state.estado_texto = "HASH OBSOLETO: CAMBIARON LOS DATOS O EL ARCHIVO"
            st.session_state.estado_tipo = "alerta"
        elif hash_vigente and st.session_state.estado_texto.startswith("HASH OBSOLETO"):
            st.session_state.estado_texto = "HASH VIGENTE"
            st.session_state.estado_tipo = "correcto"

        st.markdown('<div class="section-title">&gt; ESTADO DE INTEGRIDAD</div>', unsafe_allow_html=True)
        estado_html(st.session_state.estado_texto, st.session_state.estado_tipo)

        st.markdown('<div class="section-title">&gt; REGISTRO DE EVIDENCIA</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="terminal-box">{st.session_state.registro}</div>',
            unsafe_allow_html=True,
        )


    with tab_verificar:
        st.markdown('<div class="section-title">&gt; VERIFICACION DE INTEGRIDAD</div>', unsafe_allow_html=True)
        evidencias_para_verificar = listar_evidencias()
        opciones_verificacion = {
            f"{item['numero_evidencia']} // {item['archivo_nombre']}": item["id"]
            for item in evidencias_para_verificar
        }
        seleccion_verificacion = st.selectbox(
            "Evidencia registrada",
            options=list(opciones_verificacion.keys()),
            index=None,
            placeholder="Seleccionar evidencia",
        )
        evidencia_verificacion = (
            obtener_evidencia(opciones_verificacion[seleccion_verificacion])
            if seleccion_verificacion
            else None
        )
        hash_original = evidencia_verificacion["hash_sha256"] if evidencia_verificacion else ""
        st.text_input("Hash original", value=hash_original, disabled=True)
        archivo_verificar = st.file_uploader(
            "Archivo a verificar",
            key=f"archivo_verificar_{st.session_state.uploader_version}",
        )

        if st.button(
            "Verificar integridad",
            use_container_width=True,
            disabled=not puede_operar,
        ):
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
                verificacion_id = guardar_verificacion(
                    evidencia_id=evidencia_verificacion["id"],
                    hash_esperado=hash_original.strip(),
                    hash_obtenido=hash_nuevo,
                    resultado=resultado,
                    autor_usuario_id=usuario["id"],
                )
                st.session_state.verificacion_texto += f" // REGISTRO {verificacion_id}"

        estado_html(st.session_state.verificacion_texto, st.session_state.verificacion_tipo)
        st.markdown(
            f'<div class="terminal-box">{st.session_state.registro_verificacion}</div>',
            unsafe_allow_html=True,
        )


    with tab_registrar:
        st.markdown('<div class="action-separator"></div>', unsafe_allow_html=True)
        col_limpiar, col_guardar, col_pdf = st.columns(3)
        with col_limpiar:
            st.button("Limpiar formulario", use_container_width=True, on_click=limpiar_estado)

        with col_guardar:
            if st.button(
                "Guardar evidencia",
                use_container_width=True,
                disabled=not puede_operar,
            ):
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
                    hash_vigente=hash_vigente,
                    autor_usuario_id=usuario["id"],
                )

        with col_pdf:
            if hash_vigente and st.session_state.registro != EMPTY_REGISTRY:
                st.download_button(
                    "Exportar PDF",
                    data=generar_pdf(st.session_state.registro),
                    file_name="FORENSIA-Informe.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.button("Exportar PDF", use_container_width=True, disabled=True)


    with tab_historial:
        st.markdown('<div class="section-title">&gt; HISTORIAL SQLITE</div>', unsafe_allow_html=True)
        evidencias_guardadas = listar_evidencias()

        if evidencias_guardadas:
            evidencias_tabla = [
                {
                    **item,
                    "hash_sha256": f"{item['hash_sha256'][:12]}...{item['hash_sha256'][-8:]}",
                }
                for item in evidencias_guardadas
            ]
            st.dataframe(
                evidencias_tabla,
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
                    "autor": "AUTOR",
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
                                f"AUTOR             : {evidencia_detalle['autor']}",
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
                auditoria = verificar_cadena_eventos(evidencia_detalle["id"])
                st.markdown(
                    '<div class="section-title">&gt; AUDITORIA ENCADENADA</div>',
                    unsafe_allow_html=True,
                )
                if auditoria["integra"]:
                    estado_html(
                        f"CADENA INTEGRA // {auditoria['total_eventos']} EVENTOS // "
                        f"ANCLA {auditoria['ultimo_hash']}",
                        "correcto",
                    )
                else:
                    estado_html("CADENA ALTERADA O INCOMPLETA", "alerta")
                    for error in auditoria["errores"]:
                        st.error(error)

                if eventos:
                    eventos_tabla = [
                        {
                            **evento,
                            "hash_anterior": (
                                f"{evento['hash_anterior'][:12]}...{evento['hash_anterior'][-8:]}"
                                if evento["hash_anterior"]
                                else "SIN HASH"
                            ),
                            "hash_evento": (
                                f"{evento['hash_evento'][:12]}...{evento['hash_evento'][-8:]}"
                                if evento["hash_evento"]
                                else "SIN HASH"
                            ),
                        }
                        for evento in eventos
                    ]
                    st.markdown('<div class="section-title">&gt; EVENTOS DE CUSTODIA</div>', unsafe_allow_html=True)
                    st.dataframe(
                        eventos_tabla,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "id": "ID",
                            "tipo": "TIPO",
                            "detalle": "DETALLE",
                            "creado_en": "FECHA",
                            "autor": "AUTOR",
                            "hash_anterior": "HASH ANTERIOR",
                            "hash_evento": "HASH EVENTO",
                            "cadena_version": "VERSION",
                        },
                    )

                verificaciones = listar_verificaciones(evidencia_detalle["id"])
                if verificaciones:
                    st.markdown('<div class="section-title">&gt; VERIFICACIONES REGISTRADAS</div>', unsafe_allow_html=True)
                    st.dataframe(
                        verificaciones,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "hash_esperado": "HASH ESPERADO",
                            "hash_obtenido": "HASH OBTENIDO",
                            "resultado": "RESULTADO",
                            "creado_en": "FECHA",
                            "autor": "AUTOR",
                        },
                    )

                movimientos = listar_movimientos_custodia(evidencia_detalle["id"])
                if movimientos:
                    st.markdown('<div class="section-title">&gt; HISTORIAL DE CUSTODIA</div>', unsafe_allow_html=True)
                    st.dataframe(
                        movimientos,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "responsable_anterior": "RESPONSABLE ANTERIOR",
                            "responsable_nuevo": "RESPONSABLE NUEVO",
                            "ubicacion_anterior": "UBICACION ANTERIOR",
                            "ubicacion_nueva": "UBICACION NUEVA",
                            "estado_anterior": "ESTADO ANTERIOR",
                            "estado_nuevo": "ESTADO NUEVO",
                            "motivo": "MOTIVO",
                            "creado_en": "FECHA",
                            "autor": "AUTOR",
                        },
                    )

                st.markdown(
                    '<div class="section-title">&gt; INFORME FORENSE</div>',
                    unsafe_allow_html=True,
                )
                nombre_evidencia = "".join(
                    caracter if caracter.isalnum() or caracter in "-_" else "-"
                    for caracter in str(evidencia_detalle["numero_evidencia"])
                ).strip("-") or "evidencia"
                st.download_button(
                    "Descargar informe forense completo",
                    data=generar_pdf_forense(
                        evidencia=evidencia_detalle,
                        eventos=eventos,
                        verificaciones=verificaciones,
                        movimientos=movimientos,
                        auditoria=auditoria,
                        exportado_por=str(usuario["nombre"]),
                    ),
                    file_name=f"FORENSIA-{nombre_evidencia}-informe-forense.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

                st.markdown('<div class="section-title">&gt; REGISTRAR MOVIMIENTO DE CUSTODIA</div>', unsafe_allow_html=True)
                with st.form(f"custodia_{evidencia_detalle['id']}"):
                    responsable_nuevo = st.text_input(
                        "Nuevo responsable",
                        value=evidencia_detalle["responsable"],
                    )
                    ubicacion_nueva = st.text_input(
                        "Nueva ubicacion",
                        value=evidencia_detalle["ubicacion"] or "",
                    )
                    estado_nuevo = st.text_input(
                        "Nuevo estado",
                        value=evidencia_detalle["estado_custodia"] or "",
                    )
                    motivo = st.text_area("Motivo del movimiento")
                    registrar_movimiento = st.form_submit_button(
                        "Registrar movimiento",
                        use_container_width=True,
                        disabled=not puede_operar,
                    )

                if registrar_movimiento:
                    if not responsable_nuevo.strip() or not motivo.strip():
                        st.error("El nuevo responsable y el motivo son obligatorios.")
                    elif (
                        responsable_nuevo.strip() == evidencia_detalle["responsable"]
                        and ubicacion_nueva.strip() == (evidencia_detalle["ubicacion"] or "")
                        and estado_nuevo.strip() == (evidencia_detalle["estado_custodia"] or "")
                    ):
                        st.error("Debes modificar el responsable, la ubicacion o el estado.")
                    else:
                        guardar_movimiento_custodia(
                            evidencia_id=evidencia_detalle["id"],
                            responsable_nuevo=responsable_nuevo.strip(),
                            ubicacion_nueva=ubicacion_nueva.strip(),
                            estado_nuevo=estado_nuevo.strip(),
                            motivo=motivo.strip(),
                            autor_usuario_id=usuario["id"],
                        )
                        st.rerun()

        else:
            st.markdown(
                '<div class="terminal-box">SIN EVIDENCIAS GUARDADAS</div>',
                unsafe_allow_html=True,
            )

        if es_admin:
            mostrar_administracion_usuarios()
            mostrar_respaldos(usuario)


if __name__ == "__main__":
    main()
