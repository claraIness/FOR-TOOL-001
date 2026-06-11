from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


DB_PATH = Path(__file__).with_name("forensia.db")


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
                registro
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        evidencia_id = int(cursor.lastrowid)
        conexion.execute(
            """
            INSERT INTO eventos (evidencia_id, tipo, detalle)
            VALUES (?, ?, ?)
            """,
            (
                evidencia_id,
                "REGISTRO",
                f"Evidencia {numero_evidencia} registrada con hash SHA-256.",
            ),
        )
        return evidencia_id


def listar_evidencias() -> list[dict[str, Any]]:
    with conectar() as conexion:
        filas = conexion.execute(
            """
            SELECT
                id,
                numero_evidencia,
                responsable,
                estado_custodia,
                archivo_nombre,
                hash_sha256,
                creado_en
            FROM evidencias
            ORDER BY creado_en DESC, id DESC
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
            "SELECT * FROM evidencias WHERE id = ?",
            (evidencia_id,),
        ).fetchone()
    return dict(fila) if fila else None


def guardar_verificacion(
    *,
    evidencia_id: int | None,
    hash_esperado: str,
    hash_obtenido: str,
    resultado: str,
) -> int:
    with conectar() as conexion:
        cursor = conexion.execute(
            """
            INSERT INTO verificaciones (
                evidencia_id,
                hash_esperado,
                hash_obtenido,
                resultado
            )
            VALUES (?, ?, ?, ?)
            """,
            (evidencia_id, hash_esperado, hash_obtenido, resultado),
        )
        verificacion_id = int(cursor.lastrowid)
        conexion.execute(
            """
            INSERT INTO eventos (evidencia_id, tipo, detalle)
            VALUES (?, ?, ?)
            """,
            (
                evidencia_id,
                "VERIFICACION",
                f"Resultado de verificacion: {resultado}.",
            ),
        )
        return verificacion_id


def listar_verificaciones(evidencia_id: int) -> list[dict[str, Any]]:
    with conectar() as conexion:
        filas = conexion.execute(
            """
            SELECT hash_esperado, hash_obtenido, resultado, creado_en
            FROM verificaciones
            WHERE evidencia_id = ?
            ORDER BY creado_en DESC, id DESC
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
                motivo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            INSERT INTO eventos (evidencia_id, tipo, detalle)
            VALUES (?, ?, ?)
            """,
            (
                evidencia_id,
                "CUSTODIA",
                (
                    f"Custodia transferida de {evidencia['responsable']} a "
                    f"{responsable_nuevo}. Motivo: {motivo}."
                ),
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
                creado_en
            FROM movimientos_custodia
            WHERE evidencia_id = ?
            ORDER BY creado_en ASC, id ASC
            """,
            (evidencia_id,),
        ).fetchall()
    return [dict(fila) for fila in filas]


def listar_eventos(evidencia_id: int) -> list[dict[str, Any]]:
    with conectar() as conexion:
        filas = conexion.execute(
            """
            SELECT tipo, detalle, creado_en
            FROM eventos
            WHERE evidencia_id = ?
            ORDER BY creado_en ASC, id ASC
            """,
            (evidencia_id,),
        ).fetchall()
    return [dict(fila) for fila in filas]
