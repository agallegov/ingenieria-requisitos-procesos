#!/usr/bin/env python3
"""Crea al principio el workspace visible donde vivirá toda la planificación empresarial.

Este comando no congela el diseño. Prepara ``<proyecto>-agents`` antes de
analizar o preguntar nada:

* proyecto nuevo: se crea con los directorios básicos;
* carpeta existente: se copia literalmente, incluido su estado git, sin tocar
  el original.

Los planos nacen en borrador dentro del propio workspace. A partir de ese
momento esa copia es la fuente de verdad que entrevista, visor y finalización
deben actualizar.

Schema v3: planificación empresarial (version 3).
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent


def morir(mensaje):
    raise SystemExit("iniciar_v3: %s" % mensaje)


def ejecutar(comando, cwd=None):
    return subprocess.run(
        comando,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def planos_iniciales(nombre, titulo, existente):
    """Planos canónicos v3 para planificación empresarial."""
    return {
        "version": 3,
        "proyecto": nombre,
        "titulo": titulo,
        "descripcion": "Borrador inicial; todavía no se ha completado la planificación empresarial.",
        "definicion": {
            "estado": "borrador",
            "modo": "entrevista" if not existente else "documentacion",
            "bloques_no_aplican": [],
            "supuestos": [],
            "riesgos": [],
        },
        "contrato": {"frase": "", "exito": []},
        "actores": [],
        "glosario": [],
        "estructura_organizativa": [],
        "flujos": [],
        "acciones": [],
        "entregables": [],
        "normas": [],
        "estados": [],
        "datos": [],
        "metricas": [],
        "cumplimiento": [],
        "presupuesto": {
            "moneda": "EUR",
            "items": [],
            "total_estimado": 0,
        },
        "proveedores": [],
        "distribucion": {
            "entregas": [],
            "permisos": {
                "acciones": [],
                "roles": [],
            },
            "avisos": [],
            "condiciones": [],
        },
        "calidad": [],
        "antecedentes": [],
        "fuera": [],
        "preguntas": [],
    }


def copiar_carpeta_literal(origen, destino):
    """Sustituye la carpeta vacía por una copia byte a byte del código del usuario."""
    if not origen.is_dir():
        morir("la carpeta de trabajo no existe: %s" % origen)
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(origen, destino, symlinks=True)
    if not (destino / ".git").exists():
        r = ejecutar(["git", "init", "-b", "main"], cwd=destino)
        if r.returncode:
            morir("no pude iniciar git en la copia local:\n%s" % r.stdout)


def dejar_repo_nuevo_minimo(destino):
    """Inicializa git con un README mínimo."""
    ejecutar(["git", "init", "-b", "main"], cwd=destino)
    readme = destino / "README.md"
    if not readme.exists():
        readme.write_text("# Proyecto empresarial\n\n", encoding="utf-8")
    ejecutar(["git", "add", "-A"], cwd=destino)
    ejecutar(["git", "commit", "-m", "Inicio: repo vacío con README"], cwd=destino)


def marcar_inicio(destino, existente):
    """Crea docs/05-trabajo/ESTADO.md con la posición actual de la planificación."""
    estado = destino / "docs" / "05-trabajo" / "ESTADO.md"
    siguiente = (
        "analizar profundamente la documentación existente ANTES de entrevistar y "
        "extraer todos los procesos actuales con evidencia"
        if existente
        else "entrevistar al usuario o, si se salta, proponer y completar todos los planos"
    )
    estado.write_text(
        "# ESTADO — planificación empresarial en curso\n\n"
        "## Posición actual\n\n"
        "- **Fase**: definición de la planificación; el diseño aún no está congelado.\n"
        "- **Workspace**: creado desde el principio; los planos canónicos ya viven aquí.\n"
        "- **Siguiente acción obligatoria**: %s.\n\n"
        "## Regla de salida\n\n"
        "No presentar para aprobación hasta pasar `validar.py --perfil revision` y "
        "`validar_web_v3.py`; no congelar hasta la aprobación explícita del usuario.\n"
        % siguiente,
        encoding="utf-8",
    )
    ejecutar(["git", "add", "docs/05-trabajo/ESTADO.md"], cwd=destino)
    ejecutar(["git", "commit", "-m", "Inicia planificación empresarial"], cwd=destino)


def main():
    ap = argparse.ArgumentParser(
        description="Crea inmediatamente <nombre>-agents para planificación empresarial (v3)."
    )
    ap.add_argument("--destino", required=True)
    ap.add_argument("--nombre", required=True)
    ap.add_argument("--titulo", required=True)
    fuente = ap.add_mutually_exclusive_group()
    fuente.add_argument("--carpeta", help="carpeta local existente; se COPIA, nunca se mueve")
    args = ap.parse_args()

    destino = Path(args.destino).expanduser().resolve()
    carpeta = Path(args.carpeta).expanduser().resolve() if args.carpeta else None
    existente = bool(carpeta)
    if not destino.name.endswith("-agents"):
        morir("el destino debe terminar en -agents")
    if destino.exists() and any(destino.iterdir()):
        morir("el destino ya existe y no está vacío: %s" % destino)
    if carpeta and (
        destino == carpeta
        or destino in carpeta.parents
        or carpeta in destino.parents
    ):
        morir("el workspace no puede contener ni sustituir la carpeta original")

    with tempfile.TemporaryDirectory(prefix="ingenieria-requisitos-inicio-v3-") as temporal:
        borrador = Path(temporal)
        (borrador / "planos.json").write_text(
            json.dumps(
                planos_iniciales(args.nombre, args.titulo, existente),
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        comando = [
            sys.executable,
            str(BASE / "bootstrap.py"),
            "--planos",
            str(borrador),
            "--destino",
            str(destino),
            "--tipo",
            "empresarial",
            "--compilar",
        ]
        r = ejecutar(comando)
        if r.returncode:
            morir("el bootstrap inicial falló:\n%s" % r.stdout)

    if carpeta:
        copiar_carpeta_literal(carpeta, destino / "main")
    elif not existente:
        dejar_repo_nuevo_minimo(destino / "main")

    # Mover planos de la ruta v2 (donde bootstrap.py los dejó) a la ruta v3
    origen_v2 = destino / "docs" / "02-flujos" / "planos"
    destino_v3 = destino / "docs" / "01-entregables" / "planos"
    if origen_v2.is_dir():
        # También mover especificaciones/
        espec_v2 = destino / "docs" / "02-flujos" / "planos" / "especificaciones"
        espec_v3 = destino / "docs" / "01-entregables" / "especificaciones"
        shutil.rmtree(destino_v3, ignore_errors=True)
        destino_v3.parent.mkdir(parents=True, exist_ok=True)
        origen_v2.rename(destino_v3)
        # Mover especificaciones si bootstrap puso plan/ allí
        plan_espec = destino / "docs" / "02-flujos" / "planos" / "especificaciones"
        if plan_espec.is_dir():
            shutil.rmtree(espec_v3, ignore_errors=True)
            plan_espec.rename(espec_v3)
        # Limpiar la carpeta v2 vacía
        v2_dir = destino / "docs" / "02-flujos"
        if v2_dir.exists() and not any(v2_dir.iterdir()):
            shutil.rmtree(v2_dir, ignore_errors=True)
        # Actualizar ESTADO.md con la ruta correcta
        estado = destino / "docs" / "05-trabajo" / "ESTADO.md"
        if estado.exists():
            contenido = estado.read_text(encoding="utf-8")
            contenido = contenido.replace("02-flujos/planos", "01-entregables/planos")
            contenido = contenido.replace("docs/02-flujos/", "docs/01-entregables/")
            estado.write_text(contenido, encoding="utf-8")

    marcar_inicio(destino, existente)

    planos = destino / "docs" / "01-entregables" / "planos" / "planos.json"
    print("Workspace de planificación listo: %s" % destino)
    print("Carpeta de trabajo: %s" % (destino / "main"))
    print("Planos canónicos: %s" % planos)
    if existente:
        print("Siguiente paso obligatorio: analizar main/ antes de hacer preguntas.")
    else:
        print("Siguiente paso: completar los planos por entrevista o autopropuesta.")
    print(
        'Revisión estable: cd %s && "%s" '
        "visor/validar.py --datos %s --perfil revision"
        % (destino, sys.executable, planos)
    )


if __name__ == "__main__":
    main()
