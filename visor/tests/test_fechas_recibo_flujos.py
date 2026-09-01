"""Los recibos web de flujos usan instantes ISO 8601 con zona horaria.

El frontmatter conserva fechas simples, pero ``aprobacion.json`` lo escribe el visor con
hora y zona. Las dos copias que validan ese recibo tienen que aceptar ambos formatos sin
admitir texto arbitrario.
"""

import ast
import datetime
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent.parent.parent / "plantilla/docs/00-metodo/scripts"


def cargar_fecha_iso_valida(nombre):
    ruta = SCRIPTS / f"{nombre}.py"
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    nodo = next(
        item
        for item in arbol.body
        if isinstance(item, ast.FunctionDef) and item.name == "fecha_iso_valida"
    )
    espacio = {"datetime": datetime}
    exec(compile(ast.Module(body=[nodo], type_ignores=[]), str(ruta), "exec"), espacio)
    return espacio["fecha_iso_valida"]


class FechaReciboFlujosTest(unittest.TestCase):
    def test_linter_y_peticiones_aceptan_fecha_o_instante_con_zona(self):
        for nombre in ("lint_metodo", "peticion"):
            with self.subTest(script=nombre):
                validar = cargar_fecha_iso_valida(nombre)
                self.assertTrue(validar("2026-09-01"))
                self.assertTrue(validar("2026-09-01T20:29:36+00:00"))
                self.assertTrue(validar("2026-09-01T22:29:36+02:00"))
                self.assertFalse(validar("2026-99-99"))
                self.assertFalse(validar("ayer"))
                self.assertFalse(validar(None))


if __name__ == "__main__":
    unittest.main()
