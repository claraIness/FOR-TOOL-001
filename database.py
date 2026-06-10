from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).with_name("forensia.db")


def conectar() -> sqlite3.Connection:
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    return conexion


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
