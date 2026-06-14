from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


DB_PATH = Path(__file__).with_name("forensia.db")
ROLES_VALIDOS = {"ADMIN", "PERITO", "CONSULTA"}
TABLAS_REQUERIDAS = {
    "usuarios",
    "evidencias",
    "verificaciones",
    "eventos",
    "movimientos_custodia",
}
MAX_RESPALDO_BYTES = 200 * 1024 * 1024
HASH_INICIAL_CADENA = "0" * 64
VERSION_CADENA_EVENTOS = 1


@contextmanager
def conectar() -> Iterator[sqlite3.Connection]:
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    try:
        yield conexion
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def crear_tablas() -> None:
    with conectar() as conexion:
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proveedor_id TEXT NOT NULL UNIQUE,
                nombre TEXT NOT NULL,
                email TEXT NOT NULL,
                rol TEXT NOT NULL DEFAULT 'CONSULTA',
                creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ultimo_acceso TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK (rol IN ('ADMIN', 'PERITO', 'CONSULTA'))
            )
            """
        )
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS evidencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_evidencia TEXT NOT NULL,
                responsable TEXT NOT NULL,
                ubicacion TEXT,
                estado_custodia TEXT,
                fecha_recepcion TEXT,
                descripcion TEXT,
                archivo_nombre TEXT NOT NULL,
                archivo_tipo TEXT,
                archivo_tamano INTEGER,
                hash_sha256 TEXT NOT NULL,
                registro TEXT NOT NULL,
                creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS verificaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evidencia_id INTEGER,
                hash_esperado TEXT NOT NULL,
                hash_obtenido TEXT NOT NULL,
                resultado TEXT NOT NULL,
                creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (evidencia_id) REFERENCES evidencias(id)
            )
            """
        )
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evidencia_id INTEGER,
                tipo TEXT NOT NULL,
                detalle TEXT NOT NULL,
                creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (evidencia_id) REFERENCES evidencias(id)
            )
            """
        )
        conexion.execute(
            """
            CREATE TABLE IF NOT EXISTS movimientos_custodia (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evidencia_id INTEGER NOT NULL,
                responsable_anterior TEXT,
                responsable_nuevo TEXT NOT NULL,
                ubicacion_anterior TEXT,
                ubicacion_nueva TEXT,
                estado_anterior TEXT,
                estado_nuevo TEXT,
                motivo TEXT NOT NULL,
                creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (evidencia_id) REFERENCES evidencias(id)
            )
            """
        )
        _agregar_columna_si_falta(
            conexion,
            "evidencias",
            "autor_usuario_id",
            "INTEGER REFERENCES usuarios(id)",
        )
        _agregar_columna_si_falta(
            conexion,
            "evidencias",
            "eventos_ultimo_hash",
            "TEXT",
        )
        _agregar_columna_si_falta(
            conexion,
            "evidencias",
            "eventos_total",
            "INTEGER",
        )
        _agregar_columna_si_falta(
            conexion,
            "verificaciones",
            "autor_usuario_id",
            "INTEGER REFERENCES usuarios(id)",
        )
        _agregar_columna_si_falta(
            conexion,
            "eventos",
            "autor_usuario_id",
            "INTEGER REFERENCES usuarios(id)",
        )
        _agregar_columna_si_falta(conexion, "eventos", "hash_anterior", "TEXT")
        _agregar_columna_si_falta(conexion, "eventos", "hash_evento", "TEXT")
        _agregar_columna_si_falta(
            conexion,
            "eventos",
            "cadena_version",
            "INTEGER",
        )
        _agregar_columna_si_falta(
            conexion,
            "movimientos_custodia",
            "autor_usuario_id",
            "INTEGER REFERENCES usuarios(id)",
        )
        try:
            conexion.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_evidencias_numero
                ON evidencias (numero_evidencia)
                """
            )
        except sqlite3.IntegrityError:
            # Si la base local ya tiene duplicados, la app sigue funcionando
            # y la validacion manual evita nuevos registros duplicados.
            pass
        _migrar_cadenas_eventos_legadas(conexion)


def _agregar_columna_si_falta(
    conexion: sqlite3.Connection,
    tabla: str,
    columna: str,
    definicion: str,
) -> None:
    columnas = {
        fila["name"]
        for fila in conexion.execute(f"PRAGMA table_info({tabla})").fetchall()
    }
    if columna not in columnas:
        conexion.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")


def _hash_evento(
    *,
    evento_id: int,
    evidencia_id: int,
    tipo: str,
    detalle: str,
    creado_en: str,
    autor_usuario_id: int | None,
    hash_anterior: str,
) -> str:
    contenido = json.dumps(
        {
            "autor_usuario_id": autor_usuario_id,
            "creado_en": creado_en,
            "detalle": detalle,
            "evento_id": evento_id,
            "evidencia_id": evidencia_id,
            "hash_anterior": hash_anterior,
            "tipo": tipo,
            "version": VERSION_CADENA_EVENTOS,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def _registrar_evento(
    conexion: sqlite3.Connection,
    *,
    evidencia_id: int,
    tipo: str,
    detalle: str,
    autor_usuario_id: int | None,
) -> int:
    evidencia = conexion.execute(
        "SELECT eventos_ultimo_hash, eventos_total FROM evidencias WHERE id = ?",
        (evidencia_id,),
    ).fetchone()
    if evidencia is None:
        raise ValueError("La evidencia del evento no existe.")

    hash_anterior = evidencia["eventos_ultimo_hash"] or HASH_INICIAL_CADENA
    creado_en = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    cursor = conexion.execute(
        """
        INSERT INTO eventos (
            evidencia_id,
            tipo,
            detalle,
            creado_en,
            autor_usuario_id,
            hash_anterior,
            cadena_version
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            evidencia_id,
            tipo,
            detalle,
            creado_en,
            autor_usuario_id,
            hash_anterior,
            VERSION_CADENA_EVENTOS,
        ),
    )
    evento_id = int(cursor.lastrowid)
    hash_evento = _hash_evento(
        evento_id=evento_id,
        evidencia_id=evidencia_id,
        tipo=tipo,
        detalle=detalle,
        creado_en=creado_en,
        autor_usuario_id=autor_usuario_id,
        hash_anterior=hash_anterior,
    )
    conexion.execute(
        "UPDATE eventos SET hash_evento = ? WHERE id = ?",
        (hash_evento, evento_id),
    )
    conexion.execute(
        """
        UPDATE evidencias
        SET eventos_ultimo_hash = ?, eventos_total = COALESCE(eventos_total, 0) + 1
        WHERE id = ?
        """,
        (hash_evento, evidencia_id),
    )
    return evento_id


def _migrar_cadenas_eventos_legadas(conexion: sqlite3.Connection) -> None:
    evidencias = conexion.execute(
        """
        SELECT id, eventos_ultimo_hash, eventos_total
        FROM evidencias
        ORDER BY id
        """
    ).fetchall()
    for evidencia in evidencias:
        eventos = conexion.execute(
            """
            SELECT id, evidencia_id, tipo, detalle, creado_en, autor_usuario_id,
                   hash_anterior, hash_evento, cadena_version
            FROM eventos
            WHERE evidencia_id = ?
            ORDER BY id
            """,
            (evidencia["id"],),
        ).fetchall()
        if not eventos:
            if evidencia["eventos_ultimo_hash"] is None and evidencia["eventos_total"] is None:
                conexion.execute(
                    "UPDATE evidencias SET eventos_total = 0 WHERE id = ?",
                    (evidencia["id"],),
                )
            continue

        es_legada = (
            evidencia["eventos_ultimo_hash"] is None
            and evidencia["eventos_total"] is None
            and all(evento["hash_evento"] is None for evento in eventos)
        )
        if not es_legada:
            continue

        hash_anterior = HASH_INICIAL_CADENA
        for evento in eventos:
            hash_evento = _hash_evento(
                evento_id=int(evento["id"]),
                evidencia_id=int(evento["evidencia_id"]),
                tipo=evento["tipo"],
                detalle=evento["detalle"],
                creado_en=evento["creado_en"],
                autor_usuario_id=evento["autor_usuario_id"],
                hash_anterior=hash_anterior,
            )
            conexion.execute(
                """
                UPDATE eventos
                SET hash_anterior = ?, hash_evento = ?, cadena_version = ?
                WHERE id = ?
                """,
                (
                    hash_anterior,
                    hash_evento,
                    VERSION_CADENA_EVENTOS,
                    evento["id"],
                ),
            )
            hash_anterior = hash_evento

        conexion.execute(
            """
            UPDATE evidencias
            SET eventos_ultimo_hash = ?, eventos_total = ?
            WHERE id = ?
            """,
            (hash_anterior, len(eventos), evidencia["id"]),
        )


def registrar_usuario(*, proveedor_id: str, nombre: str, email: str) -> dict[str, Any]:
    proveedor_id = proveedor_id.strip()
    nombre = nombre.strip() or "Usuario Microsoft"
    email = email.strip()
    if not proveedor_id:
        raise ValueError("El proveedor no entrego un identificador de usuario.")

    with conectar() as conexion:
        usuario = conexion.execute(
            "SELECT * FROM usuarios WHERE proveedor_id = ?",
            (proveedor_id,),
        ).fetchone()
        if usuario is None:
            total = conexion.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
            rol = "ADMIN" if total == 0 else "CONSULTA"
            cursor = conexion.execute(
                """
                INSERT INTO usuarios (proveedor_id, nombre, email, rol)
                VALUES (?, ?, ?, ?)
                """,
                (proveedor_id, nombre, email, rol),
            )
            usuario_id = int(cursor.lastrowid)
        else:
            usuario_id = int(usuario["id"])
            conexion.execute(
                """
                UPDATE usuarios
                SET nombre = ?, email = ?, ultimo_acceso = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (nombre, email, usuario_id),
            )

        fila = conexion.execute(
            "SELECT id, proveedor_id, nombre, email, rol FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()
    return dict(fila)


def listar_usuarios() -> list[dict[str, Any]]:
    with conectar() as conexion:
        filas = conexion.execute(
            """
            SELECT id, nombre, email, rol, creado_en, ultimo_acceso
            FROM usuarios
            ORDER BY nombre COLLATE NOCASE, id
            """
        ).fetchall()
    return [dict(fila) for fila in filas]


def actualizar_rol_usuario(usuario_id: int, rol: str) -> None:
    rol = rol.strip().upper()
    if rol not in ROLES_VALIDOS:
        raise ValueError("Rol de usuario invalido.")

    with conectar() as conexion:
        actual = conexion.execute(
            "SELECT rol FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()
        if actual is None:
            raise ValueError("El usuario seleccionado no existe.")
        if actual["rol"] == "ADMIN" and rol != "ADMIN":
            administradores = conexion.execute(
                "SELECT COUNT(*) FROM usuarios WHERE rol = 'ADMIN'"
            ).fetchone()[0]
            if administradores <= 1:
                raise ValueError("Debe existir al menos un administrador.")
        conexion.execute(
            "UPDATE usuarios SET rol = ? WHERE id = ?",
            (rol, usuario_id),
        )


def guardar_evidencia(
    *,
    numero_evidencia: str,
    responsable: str,
    ubicacion: str,
    estado_custodia: str,
    fecha_recepcion: str,
    descripcion: str,
    archivo_nombre: str,
    archivo_tipo: str,
    archivo_tamano: int,
    hash_sha256: str,
    registro: str,
    autor_usuario_id: int,
) -> int:
    with conectar() as conexion:
        cursor = conexion.execute(
            """
            INSERT INTO evidencias (
                numero_evidencia,
                responsable,
                ubicacion,
                estado_custodia,
                fecha_recepcion,
                descripcion,
                archivo_nombre,
                archivo_tipo,
                archivo_tamano,
                hash_sha256,
                registro,
                autor_usuario_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                numero_evidencia,
                responsable,
                ubicacion,
                estado_custodia,
                fecha_recepcion,
                descripcion,
                archivo_nombre,
                archivo_tipo,
                archivo_tamano,
                hash_sha256,
                registro,
                autor_usuario_id,
            ),
        )
        evidencia_id = int(cursor.lastrowid)
        _registrar_evento(
            conexion,
            evidencia_id=evidencia_id,
            tipo="REGISTRO",
            detalle=f"Evidencia {numero_evidencia} registrada con hash SHA-256.",
            autor_usuario_id=autor_usuario_id,
        )
        return evidencia_id


def listar_evidencias() -> list[dict[str, Any]]:
    with conectar() as conexion:
        filas = conexion.execute(
            """
            SELECT
                evidencias.id,
                evidencias.numero_evidencia,
                evidencias.responsable,
                evidencias.estado_custodia,
                evidencias.archivo_nombre,
                evidencias.hash_sha256,
                evidencias.creado_en,
                COALESCE(u.nombre, 'REGISTRO LEGADO') AS autor
            FROM evidencias
            LEFT JOIN usuarios u ON u.id = evidencias.autor_usuario_id
            ORDER BY evidencias.creado_en DESC, evidencias.id DESC
            """
        ).fetchall()
    return [dict(fila) for fila in filas]


def existe_numero_evidencia(numero_evidencia: str) -> bool:
    with conectar() as conexion:
        fila = conexion.execute(
            """
            SELECT 1
            FROM evidencias
            WHERE lower(numero_evidencia) = lower(?)
            LIMIT 1
            """,
            (numero_evidencia.strip(),),
        ).fetchone()
    return fila is not None


def obtener_evidencia(evidencia_id: int) -> dict[str, Any] | None:
    with conectar() as conexion:
        fila = conexion.execute(
            """
            SELECT
                evidencias.*,
                COALESCE(u.nombre, 'REGISTRO LEGADO') AS autor
            FROM evidencias
            LEFT JOIN usuarios u ON u.id = evidencias.autor_usuario_id
            WHERE evidencias.id = ?
            """,
            (evidencia_id,),
        ).fetchone()
    return dict(fila) if fila else None


def guardar_verificacion(
    *,
    evidencia_id: int | None,
    hash_esperado: str,
    hash_obtenido: str,
    resultado: str,
    autor_usuario_id: int,
) -> int:
    with conectar() as conexion:
        cursor = conexion.execute(
            """
            INSERT INTO verificaciones (
                evidencia_id,
                hash_esperado,
                hash_obtenido,
                resultado,
                autor_usuario_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (evidencia_id, hash_esperado, hash_obtenido, resultado, autor_usuario_id),
        )
        verificacion_id = int(cursor.lastrowid)
        _registrar_evento(
            conexion,
            evidencia_id=evidencia_id,
            tipo="VERIFICACION",
            detalle=f"Resultado de verificacion: {resultado}.",
            autor_usuario_id=autor_usuario_id,
        )
        return verificacion_id


def listar_verificaciones(evidencia_id: int) -> list[dict[str, Any]]:
    with conectar() as conexion:
        filas = conexion.execute(
            """
            SELECT
                hash_esperado,
                hash_obtenido,
                resultado,
                verificaciones.creado_en,
                COALESCE(u.nombre, 'REGISTRO LEGADO') AS autor
            FROM verificaciones
            LEFT JOIN usuarios u ON u.id = verificaciones.autor_usuario_id
            WHERE evidencia_id = ?
            ORDER BY verificaciones.creado_en DESC, verificaciones.id DESC
            """,
            (evidencia_id,),
        ).fetchall()
    return [dict(fila) for fila in filas]


def guardar_movimiento_custodia(
    *,
    evidencia_id: int,
    responsable_nuevo: str,
    ubicacion_nueva: str,
    estado_nuevo: str,
    motivo: str,
    autor_usuario_id: int,
) -> int:
    with conectar() as conexion:
        evidencia = conexion.execute(
            """
            SELECT responsable, ubicacion, estado_custodia
            FROM evidencias
            WHERE id = ?
            """,
            (evidencia_id,),
        ).fetchone()
        if evidencia is None:
            raise ValueError("La evidencia seleccionada no existe.")

        valores_actuales = (
            evidencia["responsable"] or "",
            evidencia["ubicacion"] or "",
            evidencia["estado_custodia"] or "",
        )
        valores_nuevos = (
            responsable_nuevo.strip(),
            ubicacion_nueva.strip(),
            estado_nuevo.strip(),
        )
        if valores_actuales == valores_nuevos:
            raise ValueError("El movimiento no contiene cambios de custodia.")

        cursor = conexion.execute(
            """
            INSERT INTO movimientos_custodia (
                evidencia_id,
                responsable_anterior,
                responsable_nuevo,
                ubicacion_anterior,
                ubicacion_nueva,
                estado_anterior,
                estado_nuevo,
                motivo,
                autor_usuario_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidencia_id,
                evidencia["responsable"],
                responsable_nuevo,
                evidencia["ubicacion"],
                ubicacion_nueva,
                evidencia["estado_custodia"],
                estado_nuevo,
                motivo,
                autor_usuario_id,
            ),
        )
        conexion.execute(
            """
            UPDATE evidencias
            SET responsable = ?, ubicacion = ?, estado_custodia = ?
            WHERE id = ?
            """,
            (responsable_nuevo, ubicacion_nueva, estado_nuevo, evidencia_id),
        )
        _registrar_evento(
            conexion,
            evidencia_id=evidencia_id,
            tipo="CUSTODIA",
            detalle=(
                f"Custodia transferida de {evidencia['responsable']} a "
                f"{responsable_nuevo}. Motivo: {motivo}."
            ),
            autor_usuario_id=autor_usuario_id,
        )
        return int(cursor.lastrowid)


def listar_movimientos_custodia(evidencia_id: int) -> list[dict[str, Any]]:
    with conectar() as conexion:
        filas = conexion.execute(
            """
            SELECT
                responsable_anterior,
                responsable_nuevo,
                ubicacion_anterior,
                ubicacion_nueva,
                estado_anterior,
                estado_nuevo,
                motivo,
                movimientos_custodia.creado_en,
                COALESCE(u.nombre, 'REGISTRO LEGADO') AS autor
            FROM movimientos_custodia
            LEFT JOIN usuarios u ON u.id = movimientos_custodia.autor_usuario_id
            WHERE evidencia_id = ?
            ORDER BY movimientos_custodia.creado_en ASC, movimientos_custodia.id ASC
            """,
            (evidencia_id,),
        ).fetchall()
    return [dict(fila) for fila in filas]


def listar_eventos(evidencia_id: int) -> list[dict[str, Any]]:
    with conectar() as conexion:
        filas = conexion.execute(
            """
            SELECT
                eventos.id,
                tipo,
                detalle,
                eventos.creado_en,
                eventos.hash_anterior,
                eventos.hash_evento,
                eventos.cadena_version,
                COALESCE(u.nombre, 'REGISTRO LEGADO') AS autor
            FROM eventos
            LEFT JOIN usuarios u ON u.id = eventos.autor_usuario_id
            WHERE evidencia_id = ?
            ORDER BY eventos.creado_en ASC, eventos.id ASC
            """,
            (evidencia_id,),
        ).fetchall()
    return [dict(fila) for fila in filas]


def verificar_cadena_eventos(evidencia_id: int) -> dict[str, Any]:
    with conectar() as conexion:
        evidencia = conexion.execute(
            """
            SELECT eventos_ultimo_hash, eventos_total
            FROM evidencias
            WHERE id = ?
            """,
            (evidencia_id,),
        ).fetchone()
        if evidencia is None:
            raise ValueError("La evidencia seleccionada no existe.")

        eventos = conexion.execute(
            """
            SELECT id, evidencia_id, tipo, detalle, creado_en, autor_usuario_id,
                   hash_anterior, hash_evento, cadena_version
            FROM eventos
            WHERE evidencia_id = ?
            ORDER BY id
            """,
            (evidencia_id,),
        ).fetchall()

    errores: list[str] = []
    hash_anterior = HASH_INICIAL_CADENA
    for posicion, evento in enumerate(eventos, start=1):
        if evento["cadena_version"] != VERSION_CADENA_EVENTOS:
            errores.append(f"Evento {evento['id']}: version de cadena invalida.")
        if evento["hash_anterior"] != hash_anterior:
            errores.append(f"Evento {evento['id']}: enlace con el evento anterior roto.")
        hash_calculado = _hash_evento(
            evento_id=int(evento["id"]),
            evidencia_id=int(evento["evidencia_id"]),
            tipo=evento["tipo"],
            detalle=evento["detalle"],
            creado_en=evento["creado_en"],
            autor_usuario_id=evento["autor_usuario_id"],
            hash_anterior=evento["hash_anterior"] or "",
        )
        if evento["hash_evento"] != hash_calculado:
            errores.append(f"Evento {evento['id']}: contenido o hash alterado.")
        hash_anterior = evento["hash_evento"] or f"INVALIDO-{posicion}"

    if evidencia["eventos_total"] != len(eventos):
        errores.append("La cantidad de eventos no coincide con el anclaje de la evidencia.")
    hash_final = eventos[-1]["hash_evento"] if eventos else None
    if evidencia["eventos_ultimo_hash"] != hash_final:
        errores.append("El ultimo hash no coincide con el anclaje de la evidencia.")

    return {
        "integra": not errores,
        "total_eventos": len(eventos),
        "ultimo_hash": hash_final or "",
        "errores": errores,
    }


def calcular_hash_respaldo(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def _archivo_temporal_sqlite(contenido: bytes) -> Path:
    descriptor, nombre = tempfile.mkstemp(suffix=".db")
    ruta = Path(nombre)
    try:
        with os.fdopen(descriptor, "wb") as archivo:
            archivo.write(contenido)
    except Exception:
        ruta.unlink(missing_ok=True)
        raise
    return ruta


def validar_respaldo(
    contenido: bytes,
    *,
    hash_esperado: str | None = None,
) -> dict[str, Any]:
    if not contenido:
        raise ValueError("El respaldo esta vacio.")
    if len(contenido) > MAX_RESPALDO_BYTES:
        raise ValueError("El respaldo supera el limite de 200 MB.")

    hash_sha256 = calcular_hash_respaldo(contenido)
    if hash_esperado and hash_sha256.lower() != hash_esperado.strip().lower():
        raise ValueError("El hash SHA-256 del respaldo no coincide con el manifiesto.")

    ruta_temporal = _archivo_temporal_sqlite(contenido)
    try:
        conexion = sqlite3.connect(f"file:{ruta_temporal.as_posix()}?mode=ro", uri=True)
        conexion.row_factory = sqlite3.Row
        try:
            integridad = conexion.execute("PRAGMA integrity_check").fetchone()[0]
            if integridad != "ok":
                raise ValueError(f"SQLite informo un problema de integridad: {integridad}")

            tablas = {
                fila[0]
                for fila in conexion.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            faltantes = sorted(TABLAS_REQUERIDAS - tablas)
            if faltantes:
                raise ValueError(
                    "El archivo no es un respaldo valido de FORENSIA. "
                    f"Faltan tablas: {', '.join(faltantes)}."
                )

            conteos = {
                tabla: int(conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0])
                for tabla in sorted(TABLAS_REQUERIDAS)
            }
        finally:
            conexion.close()
    except sqlite3.DatabaseError as error:
        raise ValueError("El archivo no contiene una base SQLite valida.") from error
    finally:
        ruta_temporal.unlink(missing_ok=True)

    return {
        "hash_sha256": hash_sha256,
        "tamano": len(contenido),
        "conteos": conteos,
    }


def generar_respaldo(*, creado_por: str) -> dict[str, Any]:
    descriptor, nombre = tempfile.mkstemp(suffix=".db")
    os.close(descriptor)
    ruta_temporal = Path(nombre)
    try:
        origen = sqlite3.connect(DB_PATH)
        destino = sqlite3.connect(ruta_temporal)
        try:
            origen.backup(destino)
        finally:
            destino.close()
            origen.close()
        contenido = ruta_temporal.read_bytes()
    finally:
        ruta_temporal.unlink(missing_ok=True)

    validacion = validar_respaldo(contenido)
    creado_en = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifiesto = {
        "formato": "FORENSIA-BACKUP-1",
        "archivo": "forensia-respaldo.db",
        "creado_en_utc": creado_en,
        "creado_por": creado_por,
        **validacion,
    }
    return {
        "contenido": contenido,
        "hash_sha256": validacion["hash_sha256"],
        "manifiesto": json.dumps(
            manifiesto,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ).encode("utf-8"),
        "metadatos": manifiesto,
    }


def hash_desde_manifiesto(contenido: bytes) -> str:
    try:
        manifiesto = json.loads(contenido.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("El manifiesto JSON no es valido.") from error
    if manifiesto.get("formato") != "FORENSIA-BACKUP-1":
        raise ValueError("El manifiesto no pertenece a un respaldo FORENSIA compatible.")
    hash_sha256 = str(manifiesto.get("hash_sha256", "")).strip()
    if len(hash_sha256) != 64:
        raise ValueError("El manifiesto no contiene un hash SHA-256 valido.")
    return hash_sha256


def restaurar_respaldo(contenido: bytes, *, hash_esperado: str) -> dict[str, Any]:
    validacion = validar_respaldo(contenido, hash_esperado=hash_esperado)

    respaldo_actual = generar_respaldo(creado_por="PRE-RESTAURACION AUTOMATICA")
    directorio_respaldos = DB_PATH.parent / "respaldos"
    directorio_respaldos.mkdir(parents=True, exist_ok=True)
    marca_tiempo = datetime.now().strftime("%Y%m%d-%H%M%S")
    ruta_anterior = directorio_respaldos / f"forensia-antes-restauracion-{marca_tiempo}.db"
    ruta_anterior.write_bytes(respaldo_actual["contenido"])

    descriptor, nombre = tempfile.mkstemp(
        prefix="forensia-restauracion-",
        suffix=".db",
        dir=DB_PATH.parent,
    )
    ruta_nueva = Path(nombre)
    try:
        with os.fdopen(descriptor, "wb") as archivo:
            archivo.write(contenido)
            archivo.flush()
            os.fsync(archivo.fileno())
        os.replace(ruta_nueva, DB_PATH)
    finally:
        ruta_nueva.unlink(missing_ok=True)

    crear_tablas()
    return {
        **validacion,
        "respaldo_anterior": str(ruta_anterior),
    }
