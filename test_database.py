from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database


class DatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.directorio = tempfile.TemporaryDirectory()
        self.db_path = Path(self.directorio.name) / "forensia-test.db"
        self.db_patch = patch.object(database, "DB_PATH", self.db_path)
        self.db_patch.start()
        database.crear_tablas()

    def tearDown(self) -> None:
        self.db_patch.stop()
        self.directorio.cleanup()

    def crear_evidencia(self) -> int:
        return database.guardar_evidencia(
            numero_evidencia="EV-TEST-001",
            responsable="Responsable inicial",
            ubicacion="Laboratorio",
            estado_custodia="Recibido",
            fecha_recepcion="2026-06-10",
            descripcion="Evidencia de prueba",
            archivo_nombre="evidencia.bin",
            archivo_tipo="application/octet-stream",
            archivo_tamano=4,
            hash_sha256="a" * 64,
            registro="REGISTRO DE PRUEBA",
        )

    def test_verificacion_queda_vinculada_a_la_evidencia(self) -> None:
        evidencia_id = self.crear_evidencia()

        verificacion_id = database.guardar_verificacion(
            evidencia_id=evidencia_id,
            hash_esperado="a" * 64,
            hash_obtenido="a" * 64,
            resultado="INTEGRIDAD CONSERVADA",
        )

        self.assertGreater(verificacion_id, 0)
        verificaciones = database.listar_verificaciones(evidencia_id)
        self.assertEqual(len(verificaciones), 1)
        self.assertEqual(verificaciones[0]["resultado"], "INTEGRIDAD CONSERVADA")
        self.assertIn(
            "VERIFICACION",
            [evento["tipo"] for evento in database.listar_eventos(evidencia_id)],
        )

    def test_movimiento_actualiza_custodia_y_conserva_historial(self) -> None:
        evidencia_id = self.crear_evidencia()

        movimiento_id = database.guardar_movimiento_custodia(
            evidencia_id=evidencia_id,
            responsable_nuevo="Responsable final",
            ubicacion_nueva="Deposito seguro",
            estado_nuevo="Archivado",
            motivo="Transferencia para resguardo",
        )

        self.assertGreater(movimiento_id, 0)
        evidencia = database.obtener_evidencia(evidencia_id)
        self.assertIsNotNone(evidencia)
        self.assertEqual(evidencia["responsable"], "Responsable final")
        self.assertEqual(evidencia["ubicacion"], "Deposito seguro")
        self.assertEqual(evidencia["estado_custodia"], "Archivado")

        movimientos = database.listar_movimientos_custodia(evidencia_id)
        self.assertEqual(len(movimientos), 1)
        self.assertEqual(movimientos[0]["responsable_anterior"], "Responsable inicial")
        self.assertEqual(movimientos[0]["responsable_nuevo"], "Responsable final")

    def test_movimiento_sin_cambios_es_rechazado(self) -> None:
        evidencia_id = self.crear_evidencia()

        with self.assertRaisesRegex(ValueError, "no contiene cambios"):
            database.guardar_movimiento_custodia(
                evidencia_id=evidencia_id,
                responsable_nuevo="Responsable inicial",
                ubicacion_nueva="Laboratorio",
                estado_nuevo="Recibido",
                motivo="Actualizacion sin cambios",
            )

        self.assertEqual(database.listar_movimientos_custodia(evidencia_id), [])


if __name__ == "__main__":
    unittest.main()
