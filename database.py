from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


DB_PATH = Path(__file__).with_name("forensia.db")
ROLES_VALIDOS = {"ADMIN", "PERITO", "CONSULTA"}


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
        conexion.execute(
            """
            INSERT INTO eventos (evidencia_id, tipo, detalle, autor_usuario_id)
            VALUES (?, ?, ?, ?)
            """,
            (
                evidencia_id,
                "REGISTRO",
                f"Evidencia {numero_evidencia} registrada con hash SHA-256.",
                autor_usuario_id,
            ),
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
        conexion.execute(
            """
            INSERT INTO eventos (evidencia_id, tipo, detalle, autor_usuario_id)
            VALUES (?, ?, ?, ?)
            """,
            (
                evidencia_id,
                "VERIFICACION",
                f"Resultado de verificacion: {resultado}.",
                autor_usuario_id,
            ),
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
        conexion.execute(
            """
            INSERT INTO eventos (evidencia_id, tipo, detalle, autor_usuario_id)
            VALUES (?, ?, ?, ?)
            """,
            (
                evidencia_id,
                "CUSTODIA",
                (
                    f"Custodia transferida de {evidencia['responsable']} a "
                    f"{responsable_nuevo}. Motivo: {motivo}."
                ),
                autor_usuario_id,
            ),
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
                tipo,
                detalle,
                eventos.creado_en,
                COALESCE(u.nombre, 'REGISTRO LEGADO') AS autor
            FROM eventos
            LEFT JOIN usuarios u ON u.id = eventos.autor_usuario_id
            WHERE evidencia_id = ?
            ORDER BY eventos.creado_en ASC, eventos.id ASC
            """,
            (evidencia_id,),
        ).fetchall()
    return [dict(fila) for fila in filas]
