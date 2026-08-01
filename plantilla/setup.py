#!/usr/bin/env python3
"""Prepara un workspace generado en Windows, macOS o Linux.

Lee ``repos.yaml``, monta o actualiza ``main/``, activa el hook de Git,
recrea las carpetas locales y ejecuta el linter del método. Es idempotente
y no necesita dependencias externas aparte de Python y Git.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path


RAIZ = Path(__file__).resolve().parent


def ejecutar(*comando, cwd=RAIZ):
    return subprocess.run(
        [str(parte) for parte in comando],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def morir(mensaje):
    raise SystemExit(f"ERROR: {mensaje}")


def valor_config(texto, clave):
    patron = re.compile(rf"^\s*{re.escape(clave)}:\s*(.*?)\s*$")
    for linea in texto.splitlines():
        coincidencia = patron.match(linea)
        if coincidencia:
            valor = coincidencia.group(1).strip().strip("\"'")
            if valor.startswith("PENDIENTE"):
                return ""
            return valor.split("  #", 1)[0].strip()
    return ""


def es_repo_git(ruta):
    if not ruta.exists():
        return False
    resultado = ejecutar("git", "-C", ruta, "rev-parse", "--is-inside-work-tree")
    return resultado.returncode == 0


def main():
    print("\n=== Preparando el workspace ===\n")
    if shutil.which("git") is None:
        morir(
            "Git no está instalado. Instálalo desde https://git-scm.com "
            "y vuelve a ejecutar este programa."
        )

    version = ejecutar("git", "--version")
    if version.returncode:
        morir(version.stdout.strip())
    print(f"[1/5] {version.stdout.strip()}")

    repos = RAIZ / "repos.yaml"
    if not repos.is_file():
        morir("no encuentro repos.yaml junto a setup.py")
    configuracion = repos.read_text(encoding="utf-8")
    remoto = valor_config(configuracion, "remoto")
    ruta_local = valor_config(configuracion, "ruta_local")
    if not ruta_local:
        morir("repos.yaml no declara ruta_local")

    codigo = (RAIZ / ruta_local).resolve()
    print(f"[2/5] repo de código: {remoto or '(solo local)'} -> {codigo}")

    if es_repo_git(codigo):
        if remoto:
            print(f"[3/5] {ruta_local} ya existe: actualización desde origin/main.")
            actualizado = ejecutar(
                "git", "-C", codigo, "fetch", "origin", "main"
            )
            if actualizado.returncode == 0:
                rama = ejecutar(
                    "git", "-C", codigo, "switch", "main"
                )
                if rama.returncode:
                    rama = ejecutar(
                        "git", "-C", codigo, "switch", "-c", "main",
                        "--track", "origin/main"
                    )
                if rama.returncode == 0:
                    actualizado = ejecutar(
                        "git", "-C", codigo, "pull", "--ff-only", "origin", "main"
                    )
                else:
                    actualizado = rama
            if actualizado.returncode:
                morir(
                    f"no pude actualizar {ruta_local}:\n{actualizado.stdout.strip()}"
                )
        else:
            print(f"[3/5] {ruta_local} ya existe y no tiene remoto pendiente: se conserva.")
    elif codigo.exists():
        morir(f"{codigo} existe, pero no es un repositorio Git")
    elif remoto:
        print(f"[3/5] clonando el repo de código en {ruta_local}…")
        clonado = ejecutar("git", "clone", "--branch", "main", remoto, codigo)
        if clonado.returncode:
            morir(f"no pude clonar {remoto}:\n{clonado.stdout.strip()}")
    else:
        morir(
            f"falta {ruta_local} y repos.yaml todavía no contiene el remoto del código"
        )

    hook = (RAIZ / ".githooks").resolve()
    configurado = ejecutar(
        "git", "-C", codigo, "config", "core.hooksPath", hook
    )
    if configurado.returncode:
        morir(f"no pude activar el hook de Git:\n{configurado.stdout.strip()}")

    for nombre in ("worktrees", ".private", ".runtime"):
        (RAIZ / nombre).mkdir(exist_ok=True)
    print("[4/5] carpetas locales y hook de Git preparados.")

    linter = RAIZ / "docs" / "00-metodo" / "scripts" / "lint_metodo.py"
    comprobacion = ejecutar(sys.executable, linter)
    print("\n" + comprobacion.stdout.rstrip())
    if comprobacion.returncode:
        morir("el workspace no supera el linter del método")

    ultimo = ejecutar("git", "-C", codigo, "log", "--oneline", "-1")
    if ultimo.returncode:
        morir(f"no pude leer el último commit:\n{ultimo.stdout.strip()}")
    print(f"\n[5/5] último commit del código: {ultimo.stdout.strip()}")
    print("\n=== Workspace listo ===")
    print(
        "Los secretos de .private/ no viajan por Git; cópialos por un canal seguro."
    )


if __name__ == "__main__":
    main()
