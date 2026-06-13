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
        self.usuario = database.registrar_usuario(
            proveedor_id="usuario-admin",
            nombre="Perito administrador",
            email="admin@example.com",
        )

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
            autor_usuario_id=self.usuario["id"],
        )

    def test_primer_usuario_es_admin_y_los_siguientes_consulta(self) -> None:
        segundo = database.registrar_usuario(
            proveedor_id="usuario-consulta",
            nombre="Usuario consulta",
            email="consulta@example.com",
        )

        self.assertEqual(self.usuario["rol"], "ADMIN")
        self.assertEqual(segundo["rol"], "CONSULTA")

    def test_listado_de_evidencias_incluye_autor_sin_columnas_ambiguas(self) -> None:
        self.crear_evidencia()

        evidencias = database.listar_evidencias()

        self.assertEqual(len(evidencias), 1)
        self.assertEqual(evidencias[0]["autor"], "Perito administrador")

    def test_no_permite_quitar_el_ultimo_administrador(self) -> None:
        with self.assertRaisesRegex(ValueError, "al menos un administrador"):
            database.actualizar_rol_usuario(self.usuario["id"], "PERITO")

    def test_verificacion_queda_vinculada_a_la_evidencia(self) -> None:
        evidencia_id = self.crear_evidencia()

        verificacion_id = database.guardar_verificacion(
            evidencia_id=evidencia_id,
            hash_esperado="a" * 64,
            hash_obtenido="a" * 64,
            resultado="INTEGRIDAD CONSERVADA",
            autor_usuario_id=self.usuario["id"],
        )

        self.assertGreater(verificacion_id, 0)
        verificaciones = database.listar_verificaciones(evidencia_id)
        self.assertEqual(len(verificaciones), 1)
        self.assertEqual(verificaciones[0]["resultado"], "INTEGRIDAD CONSERVADA")
        self.assertEqual(verificaciones[0]["autor"], "Perito administrador")
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
            autor_usuario_id=self.usuario["id"],
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
        self.assertEqual(movimientos[0]["autor"], "Perito administrador")

    def test_movimiento_sin_cambios_es_rechazado(self) -> None:
        evidencia_id = self.crear_evidencia()

        with self.assertRaisesRegex(ValueError, "no contiene cambios"):
            database.guardar_movimiento_custodia(
                evidencia_id=evidencia_id,
                responsable_nuevo="Responsable inicial",
                ubicacion_nueva="Laboratorio",
                estado_nuevo="Recibido",
                motivo="Actualizacion sin cambios",
                autor_usuario_id=self.usuario["id"],
            )

        self.assertEqual(database.listar_movimientos_custodia(evidencia_id), [])


if __name__ == "__main__":
    unittest.main()
