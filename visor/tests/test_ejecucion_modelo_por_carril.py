"""Bug 065 — el lanzador y la regla 10: modelo por carril, revisión sin worktree, permisos.

Tres defectos de `ejecucion.py` vistos la noche del 25-08, uno por sección del contrato:

  A (R1/R2) `--modelo` era opcional y no había tabla: todo subagente salía con el modelo
            por defecto del harness (el más caro) y el recibo no guardaba el esfuerzo.
  B (R3)    revisar una unidad ya entregada cuyo worktree ya no existe no tenía camino:
            `lanzar --rol revisor` moría con «no figura en git worktree list».
  C (R4)    la ventana de solo lectura de la ficha no era a prueba de muertes: si el
            lanzador moría con ella abierta, la ficha se quedaba en 0444 PARA SIEMPRE
            (la ejecución siguiente leía 0444 como «modo previo» y lo re-congelaba), y
            `unidad.py cerrar` reventaba con un PermissionError pelado en vez de decir
            cómo salir.

Los tests de aquí son end-to-end sobre el launcher REAL (dobles de harness que graban su
argv), salvo los que interrogan a la tabla o a los ayudantes puros de `unidad.py`.
"""
import contextlib
import json
import os
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[2]
SCRIPTS = RAIZ / "plantilla/docs/00-metodo/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import repo_config  # noqa: E402  (el REAL, sin mutar)
import unidad as gestion_unidad  # noqa: E402

# Los ficheros del método que el launcher necesita a su lado dentro del workspace de prueba.
ACOMPANANTES = (
    "control_plane.py", "entrega.py", "lease.py", "workspace_paths.py", "repo_config.py",
)




# ===================================================== R1 · la tabla carril × rol
class TablaDeModelosTest(unittest.TestCase):
    """La tabla vive en `repo_config` y tiene una respuesta para cada carril y cada rol."""

    def test_el_constructor_sale_en_opus_en_todos_los_carriles(self):
        # Decisión de Nate del 25-08: «prefiero Opus para los subagentes».
        for carril in repo_config.CARRILES:
            with self.subTest(carril=carril):
                plan = repo_config.plan_de_modelo(carril, "constructor")
                self.assertEqual(plan.modelo, "claude-opus-5")

    def test_el_revisor_sale_en_un_modelo_distinto_del_constructor(self):
        # Regla 10: dos instancias del mismo modelo comparten puntos ciegos.
        for carril in repo_config.CARRILES:
            with self.subTest(carril=carril):
                constructor = repo_config.plan_de_modelo(carril, "constructor")
                revisor = repo_config.plan_de_modelo(carril, "revisor")
                self.assertNotEqual(revisor.modelo, constructor.modelo)
                self.assertEqual(revisor.modelo, "claude-fable-5")

    def test_lo_documental_y_el_lint_usan_el_modelo_pequeno(self):
        plan = repo_config.plan_de_modelo("normal", "constructor", documental=True)
        self.assertEqual(plan.modelo, "claude-haiku-4-5")

    def test_el_esfuerzo_sube_con_el_carril(self):
        # Regla 10: exprés y directo lo más barato; normal medio; completo y hotfix alto.
        self.assertEqual(repo_config.plan_de_modelo("directo", "constructor").esfuerzo, "bajo")
        self.assertEqual(repo_config.plan_de_modelo("expres", "constructor").esfuerzo, "bajo")
        self.assertEqual(repo_config.plan_de_modelo("normal", "constructor").esfuerzo, "medio")
        self.assertEqual(repo_config.plan_de_modelo("completo", "constructor").esfuerzo, "alto")
        self.assertEqual(repo_config.plan_de_modelo("hotfix", "constructor").esfuerzo, "alto")

    def test_el_acento_de_expres_no_abre_un_carril_distinto(self):
        self.assertEqual(
            repo_config.plan_de_modelo("Exprés", "constructor"),
            repo_config.plan_de_modelo("expres", "constructor"),
        )

    def test_un_carril_desconocido_no_se_inventa_un_modelo(self):
        with self.assertRaises(repo_config.RepoConfigError) as capturado:
            repo_config.plan_de_modelo("turbo", "constructor")
        self.assertIn("turbo", str(capturado.exception))




# ===================================================== R2 · el recibo guarda lo efectivo


class CierreMuestraElModeloTest(unittest.TestCase):
    """R2 — `unidad.py cerrar` enseña con qué modelo y esfuerzo se hizo cada cosa."""

    def recibo(self, rol, modelo, esfuerzo="", origen="tabla", motivo=""):
        return {"rol": rol, "modelo": modelo, "esfuerzo": esfuerzo,
                "modelo_origen": origen, "motivo_modelo": motivo,
                "resultado": "ok", "exit_code": 0, "lease": {"session_id": f"s-{rol}"}}

    def test_la_linea_nombra_modelo_y_esfuerzo_de_cada_rol(self):
        lineas = gestion_unidad.lineas_de_modelo([
            self.recibo("constructor", "claude-opus-5", "medio"),
            self.recibo("revisor", "claude-fable-5", "medio"),
        ])

        texto = " | ".join(lineas)
        self.assertIn("claude-opus-5", texto)
        self.assertIn("claude-fable-5", texto)
        self.assertIn("medio", texto)
        self.assertIn("constructor", texto)
        self.assertIn("revisor", texto)

    def test_la_excepcion_a_la_tabla_se_ve_con_su_motivo(self):
        lineas = gestion_unidad.lineas_de_modelo([
            self.recibo("constructor", "claude-sonnet-5", "medio",
                        origen="excepcion", motivo="la cuenta no tiene opus"),
        ])

        texto = " | ".join(lineas)
        self.assertIn("excepción", texto)
        self.assertIn("la cuenta no tiene opus", texto)

    def test_un_recibo_viejo_sin_esfuerzo_no_inventa_nada(self):
        lineas = gestion_unidad.lineas_de_modelo([
            {"rol": "constructor", "modelo": "opus", "resultado": "ok"},
        ])

        self.assertIn("opus", " | ".join(lineas))
        self.assertNotIn("esfuerzo", " | ".join(lineas))


class ComandoDeRevisionArrancaTest(unittest.TestCase):
    """R1 — la salida que ofrece el cierre tiene que seguir ARRANCANDO tras la tabla.

    `comando_revision` ofrecía `--modelo <modelo-distinto-del-constructor>`. Con la tabla
    puesta, `--modelo` es una excepción que exige `--motivo-modelo`: ese comando pegado tal
    cual moriría en el argparse, y el operador se quedaría sin salida justo donde el método
    le prometía una.
    """

    def test_la_salida_del_cierre_no_ofrece_un_modelo_a_medias(self):
        comando = gestion_unidad.comando_revision("001-demo")

        if "--modelo" in comando:
            self.assertIn("--motivo-modelo", comando)
        self.assertIn("--rol revisor", comando)
        self.assertNotIn("<", comando, f"la salida sigue teniendo huecos: {comando}")


# ===================================================== R3 · revisar sin worktree


# ===================================================== R4 · permisos de la ficha


class CerrarConLaFichaBloqueadaTest(unittest.TestCase):
    """R4, segunda mitad — `unidad.py` nombra `chmod u+w` en vez de reventar."""

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory(prefix="ficha-bloqueada-")
        self.addCleanup(self.temporal.cleanup)
        raiz = Path(self.temporal.name).resolve()
        # `fichero_unidad_seguro` confina toda escritura a la raíz del workspace: para el
        # test la raíz ES el temporal, y así ninguna prueba escribe dentro del repo.
        parche = mock.patch.object(gestion_unidad, "RAIZ", raiz)
        parche.start()
        self.addCleanup(parche.stop)
        self.ruta = raiz / "docs/05-trabajo/001-demo/especificacion.md"
        self.ruta.parent.mkdir(parents=True)
        self.ruta.write_text("---\nestado: en_obra\n---\n", encoding="utf-8")

    @unittest.skipIf(os.name == "nt", "los bits POSIX no se pueden exigir en Windows")
    def test_escribir_una_ficha_en_0444_dice_como_desbloquearla(self):
        self.ruta.chmod(0o444)
        self.addCleanup(self.ruta.chmod, 0o644)

        with self.assertRaises(gestion_unidad.ErrorFichaBloqueada) as capturado:
            gestion_unidad.escribir_fichero_unidad(self.ruta, "nuevo\n")

        mensaje = str(capturado.exception)
        self.assertIn("SALIDA:", mensaje)
        self.assertRegex(mensaje, r"chmod u\+w\s+\S")


if __name__ == "__main__":
    unittest.main()
